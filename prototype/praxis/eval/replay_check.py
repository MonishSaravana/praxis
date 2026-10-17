"""Does a code change leave the offline replay (engine.replay, used by every evaluation) unchanged?

Model answers are not reproducible on a re-run: the Jev completion-check cache key includes random per-request asset
ids (verify/jev.py), so every re-run asks Jev again and gets slightly different answers. So this check feeds the engine
the answers recorded in a saved run log instead (`Recorded`, below): each model call is answered with the next
recorded answer of that model, after checking that the engine asked the same question (same tick and step for a
completion check, same candidate steps for "which step?"). If the engine is unchanged, it asks exactly the recorded
questions and writes the same log; anything else shows up as a mismatch or as a differing record.

  python -m praxis.eval.replay_check run --tag _recorded_pre     # before the change
  python -m praxis.eval.replay_check run --tag _recorded_post    # after it
  python -m praxis.eval.replay_check diff --tag _recorded_post --against _recorded_pre

`diff` compares the candidate logs with the saved runs (runs/<variant>/) and with the reference tag, and writes
results/live/checks/replay_unchanged.json. Only `wall` (write time), the run name/id and engine-config keys in the meta
record are ignored.

The clips are chosen so that, between them, every slow-path branch runs: completion checks with Opus escalation,
"which step?" with the mistake screen and its follow-up check, the order check, view requests, hints, verified
commits, the typed "which task?" check (incl. a recording that is never recognized) and open-set drafting.
"""
from __future__ import annotations

import collections
import copy
import json
import time
from dataclasses import replace
from pathlib import Path

from ..paths import CACHE, RESULTS, RUNS
from ..runlog import read_log
from ..verify.schema import MistakeReport, Verdict

CLIPS = {
    "fused_oracle": ["17_43_0", "10_47_0", "22_40_0", "1_143_0", "10_18_0", "17_49_0"],
    "fused": ["22_41_0", "7_19_0", "17_40_0"],
    "open_set_hint": ["18_101_full"],
}
OUT = RESULTS / "live" / "checks" / "replay_unchanged.json"
MISSING = object()
# fields the saved runs predate (they were logged before these commits)
KNOWN = {"action/detail.chip": "instruct actions carry the step's short name for the HUD chip since b0e9f8b "
                               "(2026-10-17 08:24); the saved fused_oracle (07:17) and fused (07:35) logs predate it",
         "action/detail.draft": "announce_task actions carry a draft flag since b780b5b (open-set drafting, 09:43); "
                                "the saved fused logs (07:35) predate it",
         "task_draft/cached": "the replay's open-set draft comes from the drafting response cache (the saved run made "
                              "the call)"}


class Recorded:
    """A verifier that answers from a saved run log: the next recorded answer of its model, in order."""

    def __init__(self, recs: list[dict], model: str):
        self.model = model
        self.verdicts = collections.deque(r for r in recs if r["kind"] == "verdict" and r["model"] == model)
        self.choices = collections.deque(r for r in recs if r["kind"] == "step_choice" and r.get("model") == model)
        self.tasks = collections.deque(r for r in recs if r["kind"] == "task_check" and r.get("model") == model)
        self.mismatches: list[dict] = []

    def _miss(self, what: str, **kw) -> None:
        self.mismatches.append({"call": what, **kw})

    def verify(self, req) -> Verdict:
        if not self.verdicts:
            self._miss("verify", t=req.t, node=req.node.id, why="no recorded answer left")
            return Verdict(step_status="in_progress", confidence=0.5, node_id=req.node.id, model=self.model,
                           error="replay: no recorded answer")
        r = self.verdicts.popleft()
        if abs(r["t"] - req.t) > 1e-6 or r["node"] != req.node.id:
            self._miss("verify", t=req.t, node=req.node.id, recorded_t=r["t"], recorded_node=r["node"])
        return Verdict(step_status=r["status"], confidence=r["confidence"],
                       mistake=MistakeReport(**r["mistake"]) if r["mistake"] else None, visibility=r["visibility"],
                       view_request=r["view_request"], node_id=r["node"], model=r["model"], role=r["role"],
                       prompt_version=r["prompt_version"], latency_ms=r["latency_ms"], input_tokens=r["input_tokens"],
                       output_tokens=r["output_tokens"], cost_usd=r["cost_usd"],
                       raw={"cached": r["cached"], "orig_cost_usd": r["orig_cost_usd"]}, error=r["error"])

    def choose_step(self, frames, options: dict, task: str, mistakes: dict | None = None) -> dict:
        if not self.choices:
            self._miss("choose_step", options=list(options), why="no recorded answer left")
            raise RuntimeError("replay: no recorded answer")
        r = self.choices.popleft()
        if list(options) != r.get("options") or (mistakes is not None) != (r.get("mistake_screen") is not None):
            self._miss("choose_step", options=list(options), recorded_t=r["t"], recorded_options=r.get("options"))
        if r.get("error"):
            raise RuntimeError(r["error"])
        out = {k: r[k] for k in ("probs", "choice", "latency_ms", "model", "cost_usd")}
        if r.get("mistake_screen") is not None:
            out["mistake"] = r["mistake_screen"]
        return out

    def choose_task(self, frames, options: dict) -> dict:
        if not self.tasks:
            self._miss("choose_task", why="no recorded answer left")
            raise RuntimeError("replay: no recorded answer")
        r = self.tasks.popleft()
        if r.get("error"):
            raise RuntimeError(r["error"])
        return {k: r[k] for k in ("probs", "choice", "latency_ms", "model", "cost_usd")}

    def left(self) -> int:
        return len(self.verdicts) + len(self.choices) + len(self.tasks)


def _cache_files() -> dict[str, int]:
    d = CACHE / "api"
    return {p.name: sum(1 for _ in p.glob("*.json")) for p in sorted(d.iterdir()) if p.is_dir()} if d.exists() else {}


def cache_spend(t0: float, t1: float) -> dict[str, float]:
    """Cost of every API response written to the response caches between unix times t0 and t1 (= the live calls a
    run made), read from the cached responses themselves."""
    from ..verify.common import cost_usd
    out: dict[str, float] = collections.defaultdict(float)
    for f in (CACHE / "api").glob("*/*.json"):
        if not t0 <= f.stat().st_mtime <= t1:
            continue
        d = json.loads(f.read_text())
        if "resp" in d:                       # Jev: raw response with token usage
            u = d["resp"].get("usage", {})
            c = cost_usd(f.parent.name, u.get("input_tokens", 0), u.get("output_tokens", 0))
        elif "meta" in d:                     # Claude verifier
            c = d["meta"].get("cost_usd", 0.0)
        else:                                 # Jev task check, drafts, judges
            c = d.get("cost_usd", d.get("_cost_usd", 0.0))
        out[f.parent.name] += c or 0.0
    return dict(out)


def run(tag: str) -> dict:
    """Replay CLIPS on their recorded answers under run names <variant><tag> (logs only)."""
    from ..data.cc4d import Clip, load_manifest
    from ..open_set import CONDITIONS, _SavingDrafter
    from ..paths import load_env
    from ..tasks.drafter import Drafter
    from . import harness
    from .run_all import VARIANTS, calibrators, engine_config
    load_env()
    before, t0 = _cache_files(), time.time()
    man = load_manifest()
    os_ = json.loads((RESULTS / "open_set" / "open_set.json").read_text())
    titles = dict(zip([f"cc4d_{r.lower().replace(' ', '')}" for r in man["heldout_recipes"]], man["heldout_recipes"]))
    rows = []
    for v, clips in CLIPS.items():
        if v == "open_set_hint":       # open_set.run()'s "hint" condition, same settings as results/open_set/
            over, vk, ek, det, oracle = ({"open_set_draft": True, "open_set_min_s": CONDITIONS["hint"][1],
                                          "open_set_max_wait_s": max(60.0, CONDITIONS["hint"][1])},
                                         "jev", "claude_strong", "learned", False)
            pool = man["heldout_type"]
        else:                          # eval/run_all.py run_variant(v)
            over, vk, ek, det, oracle, *_ = VARIANTS[v]
            pool = man["eval"]
        stack = harness.load_stack(detector=det)
        ecfg = engine_config(over)
        cals = {"primary": calibrators(vk), "escalation": calibrators(ek)}
        for cid in clips:
            c = Clip.from_json(next(x for x in pool if x["clip_id"] == cid))
            recs = read_log(RUNS / v / f"{cid}.jsonl")
            meta = recs[0]
            ver, esc = Recorded(recs, meta["verifier"]), Recorded(recs, meta["escalation"])
            st = dict(stack)
            st["recognizer"] = copy.deepcopy(stack["recognizer"])
            drafter = None
            if v == "open_set_hint":
                c = replace(c, end=min(c.end, c.start + os_["max_s"]))
                st["library"], st["evidence"] = dict(stack["library"]), dict(stack["evidence"])
                drafter = _SavingDrafter(Drafter(hint=f"making {titles.get(c.task_id, c.task_id)}"), save=False)
            harness.run_clip(c, st, f"{v}{tag}", ecfg, ver, esc, oracle_task=oracle, calibrators=cals, drafter=drafter)
            rows.append({"variant": v, "clip": cid, "mismatches": ver.mismatches + esc.mismatches,
                         "recorded_answers_unused": ver.left() + esc.left()})
    after = _cache_files()
    info = {"tag": tag, "wall_s": time.time() - t0, "clips": rows,
            "new_cache_files": {k: after.get(k, 0) - before.get(k, 0) for k in after if after.get(k, 0) != before.get(k, 0)},
            "spend_usd": sum(cache_spend(t0, time.time() + 1).values())}
    (RUNS / f"replay_check{tag}.json").write_text(json.dumps(info, indent=1))
    return info


def _flat(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, dict) and v:
            out.update(_flat(v, f"{prefix}{k}."))
        else:
            out[f"{prefix}{k}"] = v
    return out


def diff_logs(a: Path, b: Path) -> dict:
    """Record-by-record comparison of two run logs of the same clip (a = candidate, b = reference)."""
    A, B = read_log(a), read_log(b)
    ma, mb = _flat(A[0]), _flat(B[0])
    meta = sorted(k for k in set(ma) | set(mb) if k not in ("wall", "run_id", "run") and not k.startswith("engine.")
                  and ma.get(k, MISSING) != mb.get(k, MISSING))
    ra = [r for r in A if r["kind"] not in ("meta", "summary")]
    rb = [r for r in B if r["kind"] not in ("meta", "summary")]
    fields, examples, same = collections.Counter(), [], 0
    for i, (x, y) in enumerate(zip(ra, rb)):
        fx, fy = _flat(x), _flat(y)
        d = sorted(k for k in (set(fx) | set(fy)) - {"wall"} if fx.get(k, MISSING) != fy.get(k, MISSING))
        same += not d
        for k in d:
            fields[f"{x['kind']}/{k}"] += 1
        if d and len(examples) < 3 and any(f"{x['kind']}/{k}" not in KNOWN for k in d):
            examples.append({"index": i, "t": x["t"], "kind": x["kind"], "fields": d[:6]})
    sa = next((r for r in A if r["kind"] == "summary"), {})
    sb = next((r for r in B if r["kind"] == "summary"), {})
    return {"records": len(ra), "records_reference": len(rb), "identical_records": same,
            "field_differences": dict(fields), "examples": examples, "meta_differences": meta,
            "summary_differences": sorted(k for k in ("n_frames", "escalated_frames") if sa.get(k) != sb.get(k)),
            "engine_config_keys_added": sorted(k[7:] for k in set(ma) - set(mb) if k.startswith("engine.")),
            "engine_config_differences": sorted(k[7:] for k in set(ma) & set(mb) if k.startswith("engine.")
                                                and ma[k] != mb[k])}


def compare(tag: str, against: str) -> dict:
    """against: a tag ('_recorded_pre') or '' for the saved runs (runs/<variant>/)."""
    from ..data.cc4d import Clip, load_manifest
    from . import harness
    ev = {x["clip_id"]: x for x in load_manifest()["eval"]}
    rows, fields = [], collections.Counter()
    for v, clips in CLIPS.items():
        for cid in clips:
            a, b = RUNS / f"{v}{tag}" / f"{cid}.jsonl", RUNS / f"{v}{against}" / f"{cid}.jsonl"
            d = diff_logs(a, b)
            if cid in ev:          # eval metrics recomputed from each log (open-set clips are scored in open_set.py)
                c = Clip.from_json(ev[cid])
                sa, sb = harness.score_clip(c, a), harness.score_clip(c, b)
                d["score_differences"] = sorted(k for k in sa if sa[k] != sb.get(k))
            rows.append({"variant": v, "clip": cid, **d})
            fields.update(d["field_differences"])
    n = sum(r["records"] for r in rows)
    same = sum(r["identical_records"] for r in rows)
    return {"candidate": tag, "reference": against or "saved runs (runs/<variant>/)", "clips": len(rows),
            "records": n, "identical_records": same, "same_record_count": all(r["records"] == r["records_reference"]
                                                                              for r in rows),
            "field_differences": dict(fields), "unexplained_differences": sorted(k for k in fields if k not in KNOWN),
            "known_differences": {k: KNOWN[k] for k in fields if k in KNOWN},
            "eval_scores_identical": all(not r.get("score_differences") for r in rows),
            "meta_and_summary_identical": all(not r["meta_differences"] and not r["summary_differences"] for r in rows),
            "per_clip": rows}


def diff(tag: str, against: str, cached_attempt: str | None = None) -> dict:
    """cached_attempt: tag of a re-run on the response caches with live verifiers (no code change), the first way this
    check was tried. Its divergence from the saved runs, and what its cache misses cost, are recorded too."""
    runs = {t: json.loads((RUNS / f"replay_check{t}.json").read_text()) for t in (tag, against)
            if (RUNS / f"replay_check{t}.json").exists()}
    out = {"what": "offline replay (engine.replay, used by every evaluation) re-run on the model answers recorded in "
                   "the saved run logs; every logged record compared field by field, ignoring only the write time "
                   "('wall'), the run name/id and engine-config keys in the meta record",
           "why_recorded_answers": "the Jev completion-check cache key includes random per-request asset ids "
                                   "(verify/jev.py), so a cached re-run still asks Jev again and gets different answers",
           "clips": CLIPS,
           "runs": {t: {"mismatched_questions": sum(len(c["mismatches"]) for c in r["clips"]),
                        "recorded_answers_unused": sum(c["recorded_answers_unused"] for c in r["clips"]),
                        "new_cache_files": r["new_cache_files"], "wall_s": r["wall_s"],
                        "spend_usd": r.get("spend_usd", 0.0)} for t, r in runs.items()},
           "vs_saved_runs": compare(tag, ""),
           "vs_reference_tag": compare(tag, against),
           "reference_tag_vs_saved_runs": compare(against, "")}
    spend = sum(r["spend_usd"] for r in out["runs"].values())
    p = RUNS / f"replay_check{cached_attempt}.json" if cached_attempt else None
    if p and p.exists():
        info = json.loads(p.read_text())
        t1 = p.stat().st_mtime                      # written when that run ended
        cs = cache_spend(t1 - info["wall_s"] - 2.0, t1 + 1.0)
        c = compare(cached_attempt, "")
        out["cached_rerun_attempt"] = {
            "what": "the same clips re-run with live verifiers on the response caches, before any code change",
            "new_cache_files": info["new_cache_files"], "spend_usd": sum(cs.values()), "spend_by_cache": cs,
            "vs_saved_runs": {k: c[k] for k in ("records", "identical_records", "same_record_count",
                                                "eval_scores_identical")},
            "clips_with_identical_eval_scores": sum(1 for r in c["per_clip"] if r.get("score_differences") == []),
            "scored_clips": sum(1 for r in c["per_clip"] if "score_differences" in r)}
        spend += out["cached_rerun_attempt"]["spend_usd"]
    out["spend_usd"] = spend
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    return out


def main(argv: list[str] | None = None) -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "diff"])
    ap.add_argument("--tag", required=True)
    ap.add_argument("--against", default="")
    ap.add_argument("--cached-attempt", default=None)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        info = run(a.tag)
        print(json.dumps({"mismatches": sum(len(c["mismatches"]) for c in info["clips"]),
                          "unused": sum(c["recorded_answers_unused"] for c in info["clips"]),
                          "new_cache_files": info["new_cache_files"], "wall_s": info["wall_s"]}))
    else:
        o = diff(a.tag, a.against, a.cached_attempt)
        print(json.dumps(o["runs"]), json.dumps(o.get("cached_rerun_attempt")), o["spend_usd"])
        for k in ("vs_saved_runs", "vs_reference_tag", "reference_tag_vs_saved_runs"):
            r = o[k]
            print(k, {x: r[x] for x in ("clips", "records", "identical_records", "same_record_count",
                                        "unexplained_differences", "eval_scores_identical",
                                        "meta_and_summary_identical")}, r["field_differences"])


if __name__ == "__main__":
    main()

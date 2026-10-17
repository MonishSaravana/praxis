"""Is a re-run on the response caches reproducible? One eval clip runs several times, each in its own process, with the
live verifiers, exactly as eval/run_all.py runs it. The first run pays for its cache misses and caches the answers; every
later run must answer each model call from the caches and log the same records.

Until the Jev completion-check cache key became content-based (verify/jev.py; results/WHAT_DIDNT_WORK.md #18), those
checks never hit the cache: every re-run asked Jev again, paid again and logged different answers.

  python -m praxis.eval.rerun_check run --tag _rerun1     # then _rerun2, _rerun3: one process each
  python -m praxis.eval.rerun_check diff --tags _rerun1 _rerun2 _rerun3

`diff` compares each run with the one before it and writes results/live/checks/cached_rerun.json. Only `wall` (write
time) and, in the meta record, the run name/id are ignored.
"""
from __future__ import annotations

import collections
import json
import time

from ..paths import RESULTS, ROOT, RUNS
from ..runlog import read_log
from .replay_check import MISSING, _cache_files, cache_spend, diff_logs

OUT = RESULTS / "live" / "checks" / "cached_rerun.json"
HIT_FIELDS = {"cached", "cost_usd"}     # a cache hit logs cached=true and cost_usd=0 by design
KNOWN = {"verdict/cached": "a completion check answered from the response cache is logged with cached=true",
         "verdict/cost_usd": "... and cost_usd=0 (orig_cost_usd keeps what the first, live call cost)",
         "score/verifier_latency_ms": "the eval's latency metric counts live (uncached) calls only "
                                      "(harness.score_clip); verifier_latency_ms_all includes the cached answers"}


def checks(recs: list[dict]) -> dict:
    """Completion checks per model in a run log, and how many were answered from the response cache."""
    out = collections.defaultdict(collections.Counter)
    for r in recs:
        if r["kind"] == "verdict":
            out[r["model"]]["checks"] += 1
            out[r["model"]]["from_cache"] += bool(r["cached"])
    return {m: dict(c) for m, c in out.items()}


def run(variant: str, cid: str, tag: str, max_usd: float) -> dict:
    from ..data.cc4d import Clip, load_manifest
    from ..experiments import _budget, make_verifier
    from ..paths import load_env
    from . import harness
    from .run_all import VARIANTS, calibrators, engine_config
    load_env()
    over, vk, ek, det, oracle, *_ = VARIANTS[variant]
    budget = _budget(max_calls=400, max_usd=max_usd)
    ver, esc = make_verifier(vk, budget), make_verifier(ek, budget) if ek else None
    clip = Clip.from_json(next(x for x in load_manifest()["eval"] if x["clip_id"] == cid))
    stack, ecfg = harness.load_stack(detector=det), engine_config(over)
    before, t0 = _cache_files(), time.time()
    p = harness.run_clip(clip, stack, f"{variant}{tag}", ecfg, ver, esc, oracle_task=oracle,
                         calibrators={"primary": calibrators(vk), "escalation": calibrators(ek)})
    after = _cache_files()
    info = {"tag": tag, "variant": variant, "clip": cid, "log": str(p.relative_to(ROOT)), "wall_s": time.time() - t0,
            "completion_checks": checks(read_log(p)),
            "new_cache_files": {k: after.get(k, 0) - before.get(k, 0) for k in after if after.get(k, 0) != before.get(k, 0)},
            "spend_usd": sum(cache_spend(t0, time.time() + 1).values())}
    (RUNS / f"rerun_check{tag}.json").write_text(json.dumps(info, indent=1))
    return info


def verdict_diff(a: list[dict], b: list[dict], model: str) -> dict:
    """`model`'s completion-check records in two logs (a = candidate, b = reference), compared field by field."""
    va = [r for r in a if r["kind"] == "verdict" and r["model"] == model]
    vb = [r for r in b if r["kind"] == "verdict" and r["model"] == model]
    fields, same, same_but_hit = collections.Counter(), 0, 0
    for x, y in zip(va, vb):
        d = {k for k in (set(x) | set(y)) - {"wall"} if x.get(k, MISSING) != y.get(k, MISSING)}
        same += not d
        same_but_hit += d <= HIT_FIELDS
        fields.update(d)
    return {"checks": len(va), "checks_reference": len(vb), "identical": same,
            "identical_except_cache_hit_fields": same_but_hit, "differing_fields": dict(fields)}


def diff(tags: list[str], before: str | None) -> dict:
    """before: tag of a re-run on the caches made before the key fix (same variant), for its cache-hit counts."""
    from ..data.cc4d import Clip, load_manifest
    from . import harness
    runs = [json.loads((RUNS / f"rerun_check{t}.json").read_text()) for t in tags]
    v, cid = runs[0]["variant"], runs[0]["clip"]
    clip = Clip.from_json(next(x for x in load_manifest()["eval"] if x["clip_id"] == cid))
    model = read_log(ROOT / runs[0]["log"])[0]["verifier"]
    rows = []
    for ref, cand in zip(runs, runs[1:]):
        a, b = ROOT / cand["log"], ROOT / ref["log"]
        d = diff_logs(a, b)
        sa, sb = harness.score_clip(clip, a), harness.score_clip(clip, b)
        scores = sorted(k for k in sa if sa[k] != sb.get(k))
        found = list(d["field_differences"]) + [f"score/{k}" for k in scores] + d["meta_differences"] \
            + d["summary_differences"]
        rows.append({"run": cand["tag"], "reference": ref["tag"],
                     "verifier_checks": verdict_diff(read_log(a), read_log(b), model),
                     "log": {k: d[k] for k in ("records", "records_reference", "identical_records",
                                               "field_differences", "meta_differences", "summary_differences")},
                     "score_differences": scores,
                     "unexplained_differences": sorted(k for k in found if k not in KNOWN)})
    seen = {k for r in rows for k in list(r["log"]["field_differences"]) + [f"score/{s}" for s in r["score_differences"]]}
    out = {"what": "one eval clip re-run on the response caches with the live verifiers, one process per run, after "
                   "the Jev completion-check cache key was made content-based; each run compared record by record "
                   "with the one before it (write time and run name/id ignored)",
           "variant": v, "clip": cid, "verifier": model,
           "runs": {r["tag"]: {k: r[k] for k in ("log", "completion_checks", "new_cache_files", "spend_usd")}
                    for r in runs},
           "comparisons": rows, "known_differences": {k: KNOWN[k] for k in KNOWN if k in seen}}
    p = RUNS / f"{v}{before}" / f"{cid}.jsonl" if before else None
    if p and p.exists():
        out["before_fix"] = {"what": "the same clip re-run on the caches before the fix (results/live/checks/"
                                     "replay_unchanged.json, cached_rerun_attempt)",
                             "log": str(p.relative_to(ROOT)), "completion_checks": checks(read_log(p))}
    out["spend_usd"] = sum(r["spend_usd"] for r in runs)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    return out


def main(argv: list[str] | None = None) -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "diff"])
    ap.add_argument("--variant", default="fused_oracle")
    ap.add_argument("--clip", default="17_43_0")
    ap.add_argument("--tag", default="_rerun1")
    ap.add_argument("--tags", nargs="+", default=["_rerun1", "_rerun2", "_rerun3"])
    ap.add_argument("--before", default="_replay_pre")
    ap.add_argument("--max-usd", type=float, default=0.5)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        info = run(a.variant, a.clip, a.tag, a.max_usd)
        print(json.dumps({k: info[k] for k in ("completion_checks", "new_cache_files", "spend_usd", "wall_s")}))
    else:
        o = diff(a.tags, a.before)
        print(json.dumps({"runs": o["runs"], "before_fix": o.get("before_fix"), "spend_usd": o["spend_usd"]}, indent=1))
        for r in o["comparisons"]:
            print(r["run"], "vs", r["reference"], json.dumps(r["verifier_checks"]), json.dumps(r["log"]),
                  r["score_differences"], "unexplained:", r["unexplained_differences"])


if __name__ == "__main__":
    main()

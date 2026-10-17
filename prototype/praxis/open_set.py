"""Open-set drafting experiment (M5) on CaptainCook4D recipes that are NOT in Praxis's library.

The four held-out recipe types (2 recordings each) were never compiled and never trained on. For each recording:

1. Run the engine without the task for the first `max_s` seconds, with open-set drafting on: if the typed task
   check keeps answering "none of these" after 30 s, Praxis drafts a graph from what it has seen
   (`tasks/drafter.py`) and starts tracking it, announced as a draft. Recorded: whether a wrong library task was
   announced first, and when the draft happened.
2. Judge the draft against the dataset's own task graph for that recipe (`task_graphs/<recipe>.json`): does the
   title name the same procedure, and which reference steps does the draft cover? Claude Opus 5.5, fixed rubric,
   cached.
3. Step tracking with the draft: annotated steps are mapped to draft steps by the judge's matching. Frames in
   annotated steps after the draft count as correct only if the engine's current step is the matched draft step.

Two conditions: frames only, and frames plus the person's own description of the task (the recipe name, as if
Praxis had asked "what are you making?").
"""
from __future__ import annotations

import difflib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import numpy as np

from .data.cc4d import Clip, load_manifest
from .paths import DATA, RESULTS, RUNS
from .runlog import by_kind, read_log
from .verify.common import Budget, ResponseCache, cost_usd

JUDGE_VERSION = "draft-judge-v1"
JUDGE_SYSTEM = """You compare a drafted plan for a physical procedure against a reference procedure from a dataset.
1. title_match: does the drafted title name the same procedure as the reference? "yes", "partial" (same kind of
   thing but a clearly different variant), or "no".
2. matches: for EVERY reference step (by its number), give the number of the drafted step that describes the same
   action on the same thing, or -1 if no drafted step does. One drafted step may cover several reference steps.
   Wording and level of detail may differ; judge whether a coach following the draft would cover that action."""
OUT = RESULTS / "open_set"


def ref_steps(task_id: str) -> list[str]:
    g = json.loads((DATA / "raw" / "cc4d" / "ann" / "task_graphs" / f"{task_id.replace('cc4d_', '')}.json").read_text())
    out = []
    for k in sorted(g["steps"], key=int):
        s = g["steps"][k]
        if s in ("START", "END"):
            continue
        verb, _, desc = s.partition("-")        # "Verb-description"; some descriptions drop the verb
        desc = desc.strip()
        out.append(desc if not desc or desc.lower().startswith(verb.lower().strip()) else f"{verb.strip()} {desc}")
    return out


def judge_draft(title: str, steps: list[str], task_id: str, ref_title: str, model: str = "claude-opus-5-5") -> dict:
    import anthropic
    from .paths import load_env
    load_env()
    ref = ref_steps(task_id)
    user = (f"Reference procedure: {ref_title}\n" + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(ref))
            + f"\n\nDrafted plan: {title}\n" + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps)))
    cache = ResponseCache(f"draftjudge_{model}")
    key = ResponseCache.key(JUDGE_VERSION, model, user)
    hit = cache.get(key)
    if hit is None:
        client = anthropic.Anthropic(timeout=300, max_retries=2)
        schema = {"type": "object", "additionalProperties": False, "required": ["title_match", "matches"],
                  "properties": {"title_match": {"type": "string", "enum": ["yes", "partial", "no"]},
                                 "matches": {"type": "array", "items": {
                                     "type": "object", "additionalProperties": False, "required": ["ref", "draft"],
                                     "properties": {"ref": {"type": "integer"}, "draft": {"type": "integer"}}}}}}
        resp = client.messages.create(model=model, max_tokens=8000, system=JUDGE_SYSTEM,
                                      messages=[{"role": "user", "content": user}],
                                      output_config={"format": {"type": "json_schema", "schema": schema},
                                                     "effort": "medium"})
        hit = json.loads(next(b.text for b in resp.content if b.type == "text"))
        hit["_cost_usd"] = cost_usd(model, resp.usage.input_tokens, resp.usage.output_tokens)
        cache.put(key, hit)
    m = {int(x["ref"]) - 1: int(x["draft"]) - 1 if int(x["draft"]) > 0 else -1 for x in hit["matches"]}
    m = {i: m.get(i, -1) for i in range(len(ref))}
    covered = [i for i, d in m.items() if 0 <= d < len(steps)]
    used = {d for d in m.values() if 0 <= d < len(steps)}
    return {"title_match": hit["title_match"], "ref_steps": ref, "draft_steps": steps, "ref_to_draft": m,
            "step_recall": len(covered) / len(ref) if ref else None,
            "draft_precision": len(used) / len(steps) if steps else None,
            "cost_usd": hit.get("_cost_usd", 0.0)}


class _SavingDrafter:
    """Drafter that also saves each draft graph under results/open_set/drafts/ (one SigLIP2 for all threads)."""
    _lock = threading.Lock()

    def __init__(self, inner, save: bool = True):
        self.inner, self.save = inner, save       # save=False: replay checks (eval/replay_check.py) leave results alone

    def __call__(self, frames):
        from .tasks.compiler import embed_graph
        from .evidence import ZeroShotEvidence
        from .tasks.drafter import draft_task
        g = draft_task(frames, hint=self.inner.hint, model=self.inner.model)
        with self._lock:      # MPS is not safe to use from two threads at once
            if self.inner._sig is None:
                from .perception.backbones import SigLIP
                self.inner._sig = SigLIP()
            emb = embed_graph(g, self.inner._sig)
        if self.save:
            (OUT / "drafts").mkdir(parents=True, exist_ok=True)
            g.save(OUT / "drafts" / f"{g.task_id}.json")
        return g, ZeroShotEvidence(g, emb)


def _segment_ref_index(c: Clip, ref: list[str]) -> dict[str, int]:
    """Annotated segment step id -> index into the reference step list (by text)."""
    norm = [r.lower().strip() for r in ref]
    out = {}
    for s in c.segments:
        n = (s.name or "").lower().strip()
        if n in norm:
            out[s.step] = norm.index(n)
        else:
            best = difflib.get_close_matches(n, norm, n=1, cutoff=0.6)
            out[s.step] = norm.index(best[0]) if best else -1
    return out


def score(c: Clip, log_path, judged: dict, draft_ids: list[str]) -> dict:
    recs = read_log(log_path)
    tasks = by_kind(recs, "task")
    drafts = [r for r in recs if r["kind"] == "task_draft" and not r.get("error")]
    wrong_first = bool(tasks) and not tasks[0].get("task_id", "").startswith("draft_")
    res = {"clip": c.clip_id, "recipe": c.task_id, "announced_library_task_first": wrong_first,
           "first_task": tasks[0]["task_id"] if tasks else None, "t_first_task": tasks[0]["t"] if tasks else None,
           "t_draft": drafts[0]["t"] if drafts else None, "draft_title": drafts[0]["title"] if drafts else None,
           "draft_latency_s": drafts[0].get("latency_s") if drafts else None,
           "draft_confidence": drafts[0].get("confidence") if drafts else None}
    if not drafts or judged is None:
        return res
    seg_ref = _segment_ref_index(c, judged["ref_steps"])
    bel = [b for b in recs if b["kind"] == "belief" and b["t"] >= drafts[0]["t"]]
    n = ok = n_mappable = 0
    for b in bel:
        seg = next((s for s in c.segments if s.start <= b["t"] < s.end), None)
        if seg is None:
            continue
        ri = seg_ref.get(seg.step, -1)
        di = judged["ref_to_draft"].get(ri, -1) if ri >= 0 else -1
        n += 1
        n_mappable += di >= 0
        ok += di >= 0 and b["map"] == draft_ids[di]
    res.update({"title_match": judged["title_match"], "step_recall": judged["step_recall"],
                "draft_precision": judged["draft_precision"], "n_draft_steps": len(judged["draft_steps"]),
                "n_ref_steps": len(judged["ref_steps"]), "tracked_s": c.duration - drafts[0]["t"],
                "step_acc_after_draft": ok / n if n else None,
                "share_frames_with_mapped_step": n_mappable / n if n else None})
    return res


CONDITIONS = {"frames": (False, 30.0),        # name -> (the person's description given?, earliest draft time s)
              "frames_90s": (False, 90.0),
              "hint": (True, 30.0)}


def run(max_s: float = 240.0, workers: int = 4, conditions=tuple(CONDITIONS), only: list[str] | None = None,
        out_name: str = "open_set") -> dict:
    from .eval import harness
    from .eval.run_all import calibrators, engine_config
    from .experiments import _budget, make_verifier
    from .paths import load_env
    from .tasks.drafter import Drafter
    load_env()
    stack = harness.load_stack()
    budget = _budget(1500, 15.0)
    ver, esc = make_verifier("jev", budget), make_verifier("claude_strong", budget)
    cals = {"primary": calibrators("jev"), "escalation": calibrators("claude_strong")}
    man = load_manifest()
    clips = [Clip.from_json(x) for x in man["heldout_type"] if not only or x["clip_id"] in only]
    titles = dict(zip([f"cc4d_{r.lower().replace(' ', '')}" for r in man["heldout_recipes"]], man["heldout_recipes"]))
    rows, judge_cost = {}, 0.0

    def one(job):
        import copy
        cond, c = job
        cc = replace(c, end=min(c.end, c.start + max_s))
        st = dict(stack)
        st["recognizer"] = copy.deepcopy(stack["recognizer"])
        st["library"], st["evidence"] = dict(stack["library"]), dict(stack["evidence"])
        use_hint, min_s = CONDITIONS[cond]
        hint = f"making {titles.get(c.task_id, c.task_id)}" if use_hint else None
        ecfg = engine_config({"open_set_draft": True, "open_set_min_s": min_s, "open_set_max_wait_s": max(60.0, min_s)})
        p = harness.run_clip(cc, st, f"open_set_{cond}", ecfg, ver, esc, oracle_task=False, calibrators=cals,
                             drafter=_SavingDrafter(Drafter(hint=hint)))
        return cond, cc, p

    jobs = [(cond, c) for cond in conditions for c in clips]
    with ThreadPoolExecutor(workers) as ex:
        done = list(ex.map(one, jobs))
    for cond, cc, p in done:
        recs = read_log(p)
        d = [r for r in recs if r["kind"] == "task_draft" and not r.get("error")]
        judged = None
        ids = []
        if d:
            g = json.loads((OUT / "drafts" / f"{d[0]['task_id']}.json").read_text())
            ids = [n["id"] for n in g["nodes"]]
            judged = judge_draft(g["title"], [n["name"] for n in g["nodes"]], cc.task_id, titles.get(cc.task_id, cc.task_id))
            judge_cost += judged["cost_usd"]
        r = score(cc, p, judged, ids)
        if judged:
            r["judged"] = {k: judged[k] for k in ("ref_steps", "draft_steps", "ref_to_draft")}
        rows.setdefault(cond, []).append(r)

    def agg(rs):
        dr = [r for r in rs if r.get("t_draft") is not None]
        f = lambda k: [r[k] for r in dr if r.get(k) is not None]  # noqa: E731
        return {"n_clips": len(rs), "n_drafted": len(dr),
                "announced_library_task_first": sum(r["announced_library_task_first"] for r in rs),
                "title_yes": sum(r.get("title_match") == "yes" for r in dr),
                "title_partial": sum(r.get("title_match") == "partial" for r in dr),
                "step_recall_mean": float(np.mean(f("step_recall"))) if f("step_recall") else None,
                "draft_precision_mean": float(np.mean(f("draft_precision"))) if f("draft_precision") else None,
                "step_acc_after_draft_mean": float(np.mean(f("step_acc_after_draft"))) if f("step_acc_after_draft") else None,
                "t_draft_median_s": float(np.median(f("t_draft"))) if f("t_draft") else None,
                "draft_latency_median_s": float(np.median(f("draft_latency_s"))) if f("draft_latency_s") else None}

    drafts_cost = 0.0
    for p in sorted((OUT / "drafts").glob("*.json")):
        drafts_cost += json.loads(p.read_text())["compiler"].get("cost_usd", 0.0)
    out = {"max_s": max_s, "recipes": sorted(titles.values()),
           "trigger": "after the condition's earliest draft time, the typed task check answered 'none of these' twice "
                      "in a row, or nothing was recognized by max(60 s, earliest draft time)",
           "condition_settings": {k: {"description_given": v[0], "earliest_draft_s": v[1]} for k, v in CONDITIONS.items()
                                  if k in conditions},"conditions": {k: {"aggregate": agg(v), "per_clip": v} for k, v in rows.items()},
           "spend_usd": budget.usd + judge_cost, "engine_spend_usd": budget.usd, "judge_spend_usd": judge_cost,
           "drafts_cost_usd_all_saved": drafts_cost}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{out_name}.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    o = run()
    print(json.dumps({k: v["aggregate"] for k, v in o["conditions"].items()}, indent=1), o["spend_usd"])

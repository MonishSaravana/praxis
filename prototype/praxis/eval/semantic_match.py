"""Content-aware mistake scoring. Time-window matching (harness.MISTAKE_TOL_*) counts an alert as a hit if it lands
near ANY annotated error, even when it talks about something else. Here a judge model reads each time-matched
(alert, annotated error) pair and answers with a strict rubric whether the alert identifies the same problem.

Judge: Claude Opus 5.5, structured output, cached. Rubric:
  "yes"     the alert names the same problem as the annotation (same wrong action / tool / order / amount),
            even if worded differently
  "partial" same step and a related problem, but not the annotated one
  "no"      a different problem
Strict precision counts only "yes".
"""
from __future__ import annotations

import collections
import json

from ..data.cc4d import Clip, load_manifest
from ..paths import RESULTS, RUNS
from ..runlog import by_kind, read_log
from ..tasks.compiler import load_library
from ..verify.common import Budget, ResponseCache, cost_usd
from .harness import MISTAKE_TOL_AFTER, MISTAKE_TOL_BEFORE

JUDGE_VERSION = "mistake-judge-v1"
SYSTEM = """You grade a cooking coach. You get one alert the coach spoke to the person, and the annotated error(s)
from the dataset's ground truth for the step(s) happening at that moment. Decide whether the alert identifies the
SAME problem as an annotated error.
- "yes": the alert names the same problem (same wrong action, tool, order, ingredient or amount), even if worded
  differently or less specific.
- "partial": about the same step and a related problem, but not the annotated one.
- "no": a different problem, or a generic instruction that does not identify the annotated error.
Be strict. Answer with the label and one short reason."""


def judge_pairs(run: str, model: str = "claude-opus-5-5") -> dict:
    import anthropic
    from ..paths import load_env
    load_env()
    client = anthropic.Anthropic(timeout=60, max_retries=2)
    cache = ResponseCache(f"judge_{model}")
    budget = Budget(500, 5.0)
    lib = load_library()
    clips = {c["clip_id"]: Clip.from_json(c) for c in load_manifest()["eval"]}
    rows = []
    n_alerts = 0
    for cid, c in clips.items():
        p = RUNS / run / f"{cid}.jsonl"
        if not p.exists():
            continue
        g = lib[c.task_id]
        acts = [a for a in by_kind(read_log(p), "action") if a["action"] == "mistake"]
        n_alerts += len(acts)
        gts = c.mistakes()
        for a in acts:
            hits = [m for m in gts if m["start"] - MISTAKE_TOL_BEFORE <= a["t"] <= m["end"] + MISTAKE_TOL_AFTER]
            if not hits:
                continue
            ann = "\n".join(f"- step '{g.node(m['step']).name}': {', '.join(m['tags'])}: {m['description']}" for m in hits)
            alert_step = g.node(a["node"]).name if a.get("node") in g.ids else "?"
            user = f"Recipe: {g.title}\nCoach alert (about step '{alert_step}'): \"{a['text']}\"\nAnnotated error(s):\n{ann}"
            key = ResponseCache.key(JUDGE_VERSION, model, user)
            hit = cache.get(key)
            if hit is None:
                budget.check()
                resp = client.messages.create(
                    model=model, max_tokens=2048, system=SYSTEM, messages=[{"role": "user", "content": user}],
                    output_config={"format": {"type": "json_schema", "schema": {
                        "type": "object", "additionalProperties": False, "required": ["label", "reason"],
                        "properties": {"label": {"type": "string", "enum": ["yes", "partial", "no"]},
                                       "reason": {"type": "string"}}}}, "effort": "low"})
                hit = json.loads(next(b.text for b in resp.content if b.type == "text"))
                c_ = cost_usd(model, resp.usage.input_tokens, resp.usage.output_tokens)
                budget.add(c_)
                hit["_cost_usd"] = c_        # kept with the cached answer so tracked spend counts each call once
                cache.put(key, hit)
            rows.append({"clip": cid, "t": a["t"], "alert": a["text"], "annotated": [m["description"] for m in hits],
                         "annotated_tags": sorted({t for m in hits for t in m["tags"]}),
                         "label": hit["label"], "reason": hit["reason"]})
    yes = sum(r["label"] == "yes" for r in rows)
    part = sum(r["label"] == "partial" for r in rows)
    n_gt = sum(len(c.mistakes()) for c in clips.values() if (RUNS / run / f"{c.clip_id}.jsonl").exists())
    minutes = sum(c.duration for c in clips.values() if (RUNS / run / f"{c.clip_id}.jsonl").exists()) / 60.0
    res = {"run": run, "judge": model, "judge_version": JUDGE_VERSION, "n_alerts": n_alerts, "minutes": minutes,
           "strict_false_alarms_per_min": (n_alerts - yes) / minutes if minutes else None,
           "time_window_hits": len(rows), "semantic_yes": yes, "semantic_partial": part,
           "strict_precision": yes / n_alerts if n_alerts else None,
           "lenient_precision": (yes + part) / n_alerts if n_alerts else None,
           "strict_recall": yes / n_gt if n_gt else None, "n_gt_mistakes": n_gt,
           "yes_by_annotated_tag": dict(collections.Counter(t for r in rows if r["label"] == "yes" for t in r["annotated_tags"])),
           "pairs": rows, "spend_usd": budget.usd}
    (RESULTS / "l6").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l6" / f"mistake_semantic_{run}.json").write_text(json.dumps(res, indent=2))
    return res


if __name__ == "__main__":
    import sys
    for r in sys.argv[1:] or ["fused_oracle", "fused", "baseline_stateless"]:
        x = judge_pairs(r)
        print(r, {k: x[k] for k in ("n_alerts", "time_window_hits", "semantic_yes", "semantic_partial",
                                     "strict_precision", "lenient_precision", "strict_recall", "spend_usd")})

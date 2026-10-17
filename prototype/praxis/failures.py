"""Failure analysis helpers: pull categorized failure cases out of run logs + GT and save example frame strips
(results/figures/failures/*.jpg) for results/FAILURES.md. Categories:
  false_alarm      mistake alert with no GT error nearby
  missed_mistake   GT error with no alert (by error type)
  wrong_task       recognized the wrong procedure
  stuck_belief     long stretch where the MAP step != GT step inside annotated steps
  late_verify      verified a step long after its GT end
"""
from __future__ import annotations

import collections
import json

import cv2
import numpy as np

from .data.cc4d import Clip, load_manifest
from .eval.harness import MISTAKE_TOL_AFTER, MISTAKE_TOL_BEFORE
from .eval.metrics import frame_labels, predicted_labels
from .paths import FIGURES, RESULTS, RUNS
from .runlog import by_kind, read_log
from .tasks.compiler import load_library


def strip(clip: Clip, t: float, caption: str, out_name: str, n: int = 4, span: float = 6.0) -> str:
    cap = cv2.VideoCapture(clip.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    ims = []
    for k in np.linspace(-span, 0, n):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(max(0, clip.start + t + k) * fps))
        ok, bgr = cap.read()
        if ok:
            ims.append(cv2.resize(bgr, (320, 180)))
    cap.release()
    if not ims:
        return ""
    img = np.concatenate(ims, 1)
    bar = np.full((44, img.shape[1], 3), 255, np.uint8)
    cv2.putText(bar, caption[:150], (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 1, cv2.LINE_AA)
    out = FIGURES / "failures" / f"{out_name}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), np.concatenate([bar, img], 0), [cv2.IMWRITE_JPEG_QUALITY, 85])
    return str(out.relative_to(RESULTS.parent))


def analyze(run: str = "fused_oracle", max_examples: int = 3) -> dict:
    lib = load_library()
    cats: dict = collections.defaultdict(list)
    missed_by_tag = collections.Counter()
    caught_by_tag = collections.Counter()
    for cj in load_manifest()["eval"]:
        c = Clip.from_json(cj)
        p = RUNS / run / f"{c.clip_id}.jsonl"
        if not p.exists():
            continue
        recs = read_log(p)
        g = lib[c.task_id]
        acts = by_kind(recs, "action")
        alerts = [a for a in acts if a["action"] == "mistake"]
        gts = c.mistakes()
        for a in alerts:
            if not any(m["start"] - MISTAKE_TOL_BEFORE <= a["t"] <= m["end"] + MISTAKE_TOL_AFTER for m in gts):
                cats["false_alarm"].append({"clip": c.clip_id, "t": a["t"], "said": a["text"]})
        for m in gts:
            hit = any(m["start"] - MISTAKE_TOL_BEFORE <= a["t"] <= m["end"] + MISTAKE_TOL_AFTER for a in alerts)
            for tag in m["tags"]:
                (caught_by_tag if hit else missed_by_tag)[tag] += 1
            if not hit:
                cats["missed_mistake"].append({"clip": c.clip_id, "t": m["end"], "gt": f"{m['tags'][0]}: {m['description']}",
                                               "step": g.node(m["step"]).name})
        tasks = by_kind(recs, "task")
        if tasks and tasks[0]["task_id"] != c.task_id:
            cats["wrong_task"].append({"clip": c.clip_id, "t": tasks[0]["t"], "pred": tasks[0]["task_id"], "gt": c.task_id})
        times = np.arange(0.5, c.duration, 0.5)
        segs = [(s.start, s.end, s.step) for s in c.segments]
        gt = frame_labels(segs, times, "next")
        pred = predicted_labels(recs, times)
        inside = np.array([any(a <= t < b for a, b, _ in segs) for t in times])
        wrong = (gt != pred) & inside & (pred != "")
        run_len, best = 0, (0, 0.0)
        for t, w in zip(times, wrong):
            run_len = run_len + 1 if w else 0
            if run_len > best[0]:
                best = (run_len, float(t))
        if best[0] * 0.5 >= 20:
            i = int(best[1] / 0.5) - 1
            cats["stuck_belief"].append({"clip": c.clip_id, "t": best[1], "seconds": best[0] * 0.5,
                                         "gt": g.node(gt[i]).name if gt[i] in g.ids else gt[i],
                                         "pred": g.node(pred[i]).name if pred[i] in g.ids else pred[i]})
    out = {"run": run, "counts": {k: len(v) for k, v in cats.items()},
           "missed_by_error_type": dict(missed_by_tag), "caught_by_error_type": dict(caught_by_tag), "examples": {}}
    clips = {c["clip_id"]: Clip.from_json(c) for c in load_manifest()["eval"]}
    for k, v in cats.items():
        ex = []
        for i, e in enumerate(sorted(v, key=lambda e: -e.get("seconds", 0))[:max_examples]):
            cap = {"false_alarm": f"FALSE ALARM: said '{e.get('said', '')}'",
                   "missed_mistake": f"MISSED: {e.get('gt', '')} ({e.get('step', '')})",
                   "wrong_task": f"WRONG TASK: {e.get('pred')} (GT {e.get('gt')})",
                   "stuck_belief": f"STUCK {e.get('seconds')}s: thought '{e.get('pred')}', GT '{e.get('gt')}'"}.get(k, k)
            e["frames"] = strip(clips[e["clip"]], e["t"], cap, f"{k}_{i}")
            ex.append(e)
        out["examples"][k] = ex
    (RESULTS / "failures.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    import sys
    print(json.dumps(analyze(sys.argv[1] if len(sys.argv) > 1 else "fused_oracle")["counts"], indent=1))

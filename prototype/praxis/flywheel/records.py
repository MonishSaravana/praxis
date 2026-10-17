"""L7 · Training-ready session records (versioned schema).

Every session is exported as one self-describing record that a future in-house model can train on with no
re-processing: what was seen (clip ref + L1 feature refs), what each layer believed and decided, what the
verifier was asked and answered (typed), what the policy did, and the outcome / ground truth.

Schema praxis.record/1 (JSON):
{
  "schema": "praxis.record/1",
  "session": {run_id, run, created, engine config, model ids, prompt versions},
  "source": {dataset, recording, video, clip_start, clip_end, license},
  "task": {task_id, graph_version, recognized_at, oracle},
  "features": {"path": data/features/<clip>.npz, "keys": [...], "fps": 4, "window_s": 2, "window_stride_s": 1},
  "timeline": [ {t, belief:{map, map_p, entropy, top3}, fast:{boundary, grasp}, gt_step} ... ]   # 1 Hz
  "events": [ {t, kind, score} ],
  "verifier_calls": [ {t, node, question_set, frames_t:[...], model, prompt_version, verdict:{...},
                       calibrated_p_complete, latency_ms, cost_usd, gt:{complete, error}} ],
  "actions": [ {t, kind, text, node, detail} ],
  "tracks": [ {t, xy, visible, roi} ],
  "outcome": {gt_steps:[...], gt_mistakes:[...], completed_steps:[...]}
}
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from ..data.cc4d import Clip
from ..paths import FEATURES
from ..runlog import by_kind, read_log

SCHEMA = "praxis.record/1"


def gt_step_at(clip: Clip, t: float, shift: float = 0.0) -> str | None:
    for s in clip.segments:
        if s.start - shift <= t < s.end - shift:
            return s.step
    return None


def export(log_path: Path, clip: Clip, out_dir: Path) -> Path:
    recs = read_log(log_path)
    meta = recs[0]
    shift = meta.get("join_at") or 0.0
    tasks = by_kind(recs, "task")
    fast = {round(r["t"], 1): r for r in by_kind(recs, "fast")}
    timeline = []
    for b in by_kind(recs, "belief"):
        top = sorted(b["p"].items(), key=lambda kv: -kv[1])[:3]
        f = fast.get(round(b["t"], 1), {})
        timeline.append({"t": b["t"], "belief": {"map": b["map"], "map_p": b["map_p"], "entropy": b["entropy"], "top3": top,
                                                  "time_on_step": b["time_on_step"]},
                         "fast": {"boundary": f.get("boundary"), "grasp": f.get("grasp")},
                         "gt_step": gt_step_at(clip, b["t"], shift), "user": b.get("user")})
    mistakes = clip.mistakes()
    calls = []
    for v in by_kind(recs, "verdict"):
        seg = [s for s in clip.segments if s.step == v["node"]]
        gt_complete = bool(seg and v["t"] >= seg[0].end - shift)
        gt_err = any(m["step"] == v["node"] for m in mistakes)
        calls.append({"t": v["t"], "node": v["node"], "reason": v["reason"], "model": v["model"], "role": v["role"],
                      "prompt_version": v["prompt_version"],
                      "verdict": {k: v[k] for k in ("status", "confidence", "mistake", "visibility", "view_request")},
                      "calibrated_p_complete": v.get("p_complete_cal"), "latency_ms": v["latency_ms"],
                      "cost_usd": v.get("orig_cost_usd"), "frames_t": [v["t"] - 2, v["t"] - 1, v["t"]],
                      "gt": {"complete": gt_complete, "error": gt_err}})
    rec = {
        "schema": SCHEMA,
        "session": {"run_id": meta.get("run_id"), "run": meta.get("run"), "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "engine": meta.get("engine"), "detector": meta.get("detector"), "verifier": meta.get("verifier"),
                    "escalation": meta.get("escalation")},
        "source": {"dataset": clip.dataset, "recording": clip.recording, "video": Path(clip.video).name,
                   "clip_start": clip.start + shift, "clip_end": clip.end},
        "task": {"task_id": tasks[0]["task_id"] if tasks else None, "recognized_at": tasks[0]["t"] if tasks else None,
                 "oracle": tasks[0].get("oracle") if tasks else None, "gt_task_id": clip.task_id},
        "features": {"path": str((FEATURES / f"{clip.clip_id}.npz").relative_to(FEATURES.parents[1])),
                     "keys": ["t", "siglip", "dino", "window", "hands", "change"], "fps": 4, "window_s": 2, "window_stride_s": 1,
                     "time_offset_s": shift},
        "timeline": timeline,
        "events": [{"t": e["t"], "event": e["event"], "score": e["score"]} for e in by_kind(recs, "event")],
        "verifier_calls": calls,
        "actions": [{k: a.get(k) for k in ("t", "action", "text", "node", "detail")} for a in by_kind(recs, "action")],
        "tracks": [{k: r.get(k) for k in ("t", "xy", "visible", "roi")} for r in by_kind(recs, "tracks")],
        "outcome": {"gt_steps": [{"start": s.start - shift, "end": s.end - shift, "step": s.step, "has_error": s.has_error}
                                 for s in clip.segments],
                    "gt_mistakes": mistakes, "missing_steps": clip.missing_steps,
                    "completed_steps": sorted({c["node"] for c in by_kind(recs, "commit")})},
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{log_path.stem}.record.json"
    out.write_text(json.dumps(rec))
    return out

"""`praxis eval`: run the engine over eval clips (each run writes a JSONL log), then score the logs.

Scoring reads only (a) the dataset's ground truth and (b) the run logs.
"""
from __future__ import annotations

import json
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

from ..data.cc4d import Clip
from ..engine import Engine, EngineConfig, replay
from ..events.detector import HeuristicDetector, LearnedDetector
from ..io.sources import FileSource
from ..paths import CKPT, DATA, RUNS
from ..perception.extract import load_features
from ..runlog import RunLog, by_kind, read_log
from . import metrics as M

MISTAKE_TOL_BEFORE = 5.0     # an alert may precede the erroneous step's annotated start by this much
MISTAKE_TOL_AFTER = 10.0     # ... or follow its annotated end by this much


# ------------------------------------------------------------------------------------------- stack
def load_stack(detector: str = "learned", evidence: str = "probe") -> dict:
    from ..evidence import ProbeEvidence, ZeroShotEvidence
    from ..tasks.compiler import load_library
    from ..tasks.recognizer import TaskRecognizer
    lib = load_library()
    ev = {}
    for tid, g in lib.items():
        pp = CKPT / f"probe_{tid}.pkl"
        if evidence == "probe" and pp.exists():
            ev[tid] = ProbeEvidence.load(pp)
        else:
            z = np.load(DATA / "taskgraph_emb" / f"{tid}.npz")
            ev[tid] = ZeroShotEvidence(g, {k: z[k] for k in z.files})
    if (CKPT / "task_recognizer.pkl").exists():
        rec = TaskRecognizer.load(CKPT / "task_recognizer.pkl")
    else:   # zero-shot fallback: SigLIP2 frame vs each graph's title embedding
        tids = sorted(lib)
        te = np.concatenate([np.load(DATA / "taskgraph_emb" / f"{t}.npz")["task"] for t in tids])
        rec = TaskRecognizer(task_ids=tids, text_emb=te)
        rec.reset()
    det = LearnedDetector.load(CKPT / "l2_event_detector.pt") if detector == "learned" and (CKPT / "l2_event_detector.pt").exists() \
        else HeuristicDetector()
    thr = 0.5
    p = Path(__file__).resolve().parents[3] / "results" / "l2" / "l2_event_detector.json"
    if p.exists():
        r = json.loads(p.read_text())["train"]
        thr = r["thr"] if detector == "learned" else r["heuristic_thr"]
    return {"library": lib, "evidence": ev, "recognizer": rec, "detector": det, "boundary_thr": thr}


def decode_frames(clip: Clip, fps: float = 4.0, max_side: int = 640) -> list[np.ndarray]:
    return [f.rgb for f in FileSource(clip.video, fps=fps, start=clip.start, end=clip.end, max_side=max_side)]


# ------------------------------------------------------------------------------------------- run
def run_clip(clip: Clip, stack: dict, run_name: str, ecfg: EngineConfig, verifier=None, escalation=None,
             calibrator=None, dev_calibrator=None, oracle_task: bool = False, join_at: float | None = None,
             user=None, frames: list[np.ndarray] | None = None, point_tracker=None) -> Path:
    feats, _ = load_features(clip.clip_id)
    scores = stack["detector"].score(feats)
    t_first = 0.0
    if join_at is not None:      # mid-task join: drop everything before join_at
        m = feats.t >= join_at
        feats = replace(feats, t=feats.t[m] - join_at, frame=feats.frame[m], hands=feats.hands[m],
                        window=feats.window[m], change=feats.change[m])
        scores = {k: v[m] for k, v in scores.items()}
        t_first = join_at
    if frames is None:
        frames = decode_frames(clip)
    if join_at is not None:
        frames = frames[int(round(join_at * 4)):]
    out = RUNS / run_name / f"{clip.clip_id}{'' if join_at is None else f'_join{int(join_at)}'}.jsonl"
    meta = {"clip": clip.clip_id, "dataset": clip.dataset, "task_id": clip.task_id, "recording": clip.recording,
            "clip_start": clip.start + t_first, "clip_end": clip.end, "run": run_name, "join_at": join_at,
            "engine": {k: (v if isinstance(v, (int, float, str, bool, type(None))) else str(v)) for k, v in vars(ecfg).items()},
            "detector": getattr(stack["detector"], "name", "?"),
            "verifier": getattr(verifier, "model", None), "escalation": getattr(escalation, "model", None)}
    with RunLog(out, meta) as log:
        rec = stack["recognizer"]
        if rec is not None:
            rec.reset()
        eng = Engine(ecfg, stack["library"], stack["evidence"], None if oracle_task else rec, stack["detector"],
                     verifier, escalation, calibrator, dev_calibrator, log, task_id=clip.task_id if oracle_task else None,
                     user=user, point_tracker=point_tracker)
        info = replay(eng, feats, scores, frames)
        log.write("summary", float(feats.t[-1]) if len(feats.t) else 0.0, **info)
    return out


# ------------------------------------------------------------------------------------------- score
def score_clip(clip: Clip, log_path: Path, join_at: float = 0.0) -> dict:
    recs = read_log(log_path)
    shift = join_at or 0.0
    segs = [(s.start - shift, s.end - shift, s.step) for s in clip.segments if s.end - shift > 0]
    dur = (clip.end - clip.start) - shift
    times = np.arange(0.5, dur, 0.5)
    gt = M.frame_labels(segs, times, between="next")
    inside = np.array([any(a <= t < b for a, b, _ in segs) for t in times])
    pred = M.predicted_labels(recs, times)
    tasks = by_kind(recs, "task")
    t_rec = tasks[0]["t"] if tasks else None
    after = times >= (t_rec if t_rec is not None else 1e9)
    res: dict = {"clip": clip.clip_id, "task_id": clip.task_id, "minutes": dur / 60.0,
                 "recognized_task": tasks[0]["task_id"] if tasks else None, "t_recognize": t_rec,
                 "task_correct": (tasks[0]["task_id"] == clip.task_id) if tasks else False}
    res["step_acc"] = float(((gt == pred) & inside).sum() / max(1, inside.sum()))
    m = inside & after
    res["step_acc_after_recognition"] = float(((gt == pred) & m).sum() / max(1, m.sum())) if m.any() else None
    res["step_acc_incl_between"] = float((gt == pred).mean()) if len(gt) else None
    gt_end = {s: e for _, e, s in segs if e < dur - 1}
    res["transition_err_s"] = M.transition_timing_error(gt_end, recs)

    acts = by_kind(recs, "action")
    alerts = [a["t"] for a in acts if a["action"] == "mistake"]
    gts = [mk for mk in clip.mistakes() if mk["end"] - shift > 0]
    gwin = [(mk["start"] - shift, mk["end"] - shift) for mk in gts]
    tp, used, delays_end, delays_start = 0, set(), [], []
    for p in sorted(alerts):
        hit = [i for i, (a, b) in enumerate(gwin) if i not in used and a - MISTAKE_TOL_BEFORE <= p <= b + MISTAKE_TOL_AFTER]
        if hit:
            i = min(hit, key=lambda i: abs(p - gwin[i][1]))
            used.add(i)
            tp += 1
            delays_end.append(p - gwin[i][1])
            delays_start.append(p - gwin[i][0])
    fp, fn = len(alerts) - tp, len(gwin) - tp
    res["mistakes"] = {**M.prf(tp, fp, fn), "detect_minus_step_end_s": delays_end, "detect_minus_step_start_s": delays_start,
                       "n_alerts": len(alerts), "n_gt": len(gwin)}
    res["false_alarms_per_min"] = fp / max(1e-6, dur / 60.0)
    res["all_alerts_per_min"] = len(alerts) / max(1e-6, dur / 60.0)

    # feedback latency: GT step end -> "verified"/"mistake" about that step
    fb = []
    for a in acts:
        if a["action"] in ("verified", "mistake") and a.get("node") in gt_end:
            fb.append(a["t"] - gt_end[a["node"]])
    res["feedback_latency_s"] = fb
    ver = by_kind(recs, "verdict")
    live = [v for v in ver if not v.get("cached") and not v.get("error")]
    res["verifier_calls"] = len(ver)
    res["verifier_latency_ms"] = [v["latency_ms"] for v in live]
    res["verifier_latency_ms_all"] = [v["latency_ms"] for v in ver if not v.get("error")]
    res["verifier_errors"] = sum(1 for v in ver if v.get("error"))
    res["cost_usd"] = float(sum(v.get("orig_cost_usd", v.get("cost_usd", 0.0)) or 0.0 for v in ver))
    summ = by_kind(recs, "summary")
    if summ:
        res["frames"] = summ[0]["n_frames"]
        res["escalated_frames"] = summ[0]["escalated_frames"]
    res["n_view_requests"] = sum(1 for a in acts if a["action"] == "view_request")
    res["n_hints"] = sum(1 for a in acts if a["action"] == "hint")
    res["n_verified"] = sum(1 for a in acts if a["action"] == "verified")
    return res


def aggregate(rows: list[dict]) -> dict:
    def mean(k):
        xs = [r[k] for r in rows if r.get(k) is not None]
        return float(np.mean(xs)) if xs else None
    flat = lambda k: [x for r in rows for x in r.get(k, [])]
    tp = sum(r["mistakes"]["tp"] for r in rows)
    fp = sum(r["mistakes"]["fp"] for r in rows)
    fn = sum(r["mistakes"]["fn"] for r in rows)
    minutes = sum(r["minutes"] for r in rows)
    frames = sum(r.get("frames", 0) for r in rows)
    out = {
        "n_clips": len(rows), "minutes": minutes,
        "step_acc": mean("step_acc"), "step_acc_after_recognition": mean("step_acc_after_recognition"),
        "step_acc_incl_between": mean("step_acc_incl_between"),
        "transition_err_s": M.latency_summary(flat("transition_err_s")),
        "task_top1": float(np.mean([r["task_correct"] for r in rows])),
        "t_recognize_s": M.latency_summary([r["t_recognize"] for r in rows if r["t_recognize"] is not None and r["task_correct"]]),
        "mistakes": {**M.prf(tp, fp, fn), "detect_minus_step_end_s": M.latency_summary(flat("detect_minus_step_end_s") if False else
                                                                                      [x for r in rows for x in r["mistakes"]["detect_minus_step_end_s"]]),
                     "detect_minus_step_start_s": M.latency_summary([x for r in rows for x in r["mistakes"]["detect_minus_step_start_s"]]),
                     "share_caught_before_step_end": (float(np.mean([x < 0 for r in rows for x in r["mistakes"]["detect_minus_step_end_s"]]))
                                                      if tp else None)},
        "false_alarms_per_min": fp / max(1e-6, minutes),
        "alerts_per_min": sum(r["mistakes"]["n_alerts"] for r in rows) / max(1e-6, minutes),
        "feedback_latency_s": M.latency_summary(flat("feedback_latency_s")),
        "verifier_latency_ms_live": M.latency_summary(flat("verifier_latency_ms")),
        "verifier_calls": sum(r["verifier_calls"] for r in rows),
        "verifier_errors": sum(r["verifier_errors"] for r in rows),
        "escalated_frame_share": sum(r.get("escalated_frames", 0) for r in rows) / max(1, frames),
        "cost_usd": sum(r["cost_usd"] for r in rows),
        "cost_usd_per_video_min": sum(r["cost_usd"] for r in rows) / max(1e-6, minutes),
        "view_requests": sum(r["n_view_requests"] for r in rows),
        "hints": sum(r["n_hints"] for r in rows),
    }
    return out


def per_category(rows: list[dict]) -> dict:
    cats = sorted({r["task_id"] for r in rows})
    return {c: aggregate([r for r in rows if r["task_id"] == c]) for c in cats}

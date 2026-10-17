"""Experiment drivers. Each writes JSON under results/ and is reproducible from the README commands."""
from __future__ import annotations

import json
import time

import numpy as np

from .data.cc4d import Clip, load_manifest
from .paths import FEATURES, RESULTS


def _items(clips: list[Clip]):
    """(ClipFeatures, boundaries=step ends, onsets=step starts) for clips whose features exist."""
    from .perception.extract import load_features
    out = []
    for c in clips:
        if not (FEATURES / f"{c.clip_id}.npz").exists():
            continue
        f, _ = load_features(c.clip_id)
        dur = float(f.t[-1]) if len(f.t) else 0.0
        ends = [s.end for s in c.segments if 1.0 < s.end < dur - 1.0]
        starts = [s.start for s in c.segments if 1.0 < s.start < dur - 1.0]
        out.append((f, ends, starts))
    return out


def l2(epochs: int = 60) -> dict:
    """Train the event detector on train-split recordings; test on held-out videos and held-out procedure types.
    Head 2 ('onset') is trained on step starts: CaptainCook4D has no hand-object grasp labels, and a new step
    usually starts with picking something up, so onsets are our proxy for grasp events (documented)."""
    from .events.train import run
    man = load_manifest()
    tr = _items([Clip.from_json(c) for c in man["train"]])
    te_vid = _items([Clip.from_json(c) for c in man["eval"]])
    te_type = _items([Clip.from_json(c) for c in man["heldout_type"]])
    print(f"L2: train {len(tr)} recordings, test {len(te_vid)} held-out clips, {len(te_type)} held-out-type recordings", flush=True)
    res = run(tr, {"heldout_videos": te_vid, "heldout_procedure_types": te_type}, epochs=epochs)
    res["train_recordings"] = [f.clip_id for f, _, _ in tr]
    (RESULTS / "l2" / "l2_event_detector.json").write_text(json.dumps(res, indent=2, default=float))
    for k, v in res["test"].items():
        print(k, {m: round(v[m]["f1"], 3) for m in v})
    return res


def probes() -> dict:
    from .tasks.train_probes import fit_all
    return fit_all()



def run_baseline_clip(clip: Clip, baseline, graph, run_name: str, every_s: float = 5.0, mistake_conf: float = 0.7,
                      frames: list | None = None):
    """Stateless ablation: the same model, window by window, no task graph and no persistent state.
    Writes a run log in the engine's format (belief/action/verdict) so the same scorer applies."""
    from .eval.harness import decode_frames
    from .paths import RUNS
    from .runlog import RunLog
    frames = frames if frames is not None else decode_frames(clip)
    names = [n.name for n in graph.nodes]
    name2id = {n.name: n.id for n in graph.nodes}
    out = RUNS / run_name / f"{clip.clip_id}.jsonl"
    with RunLog(out, {"clip": clip.clip_id, "run": run_name, "task_id": clip.task_id, "baseline": baseline.model,
                      "every_s": every_s, "mistake_conf": mistake_conf}) as log:
        log.write("task", 0.0, task_id=clip.task_id, title=graph.title, oracle=True, posterior=None, n_steps=len(names))
        t = every_s
        n_frames = len(frames)
        while t <= clip.duration:
            idx = [int(round((t - k) * 4)) for k in (2, 1, 0)]
            fr = [frames[i] for i in idx if 0 <= i < n_frames]
            r = baseline.query(fr, graph.title, names, frame_ages=[2.0, 1.0, 0.0][-len(fr):])
            if "error" in r:
                log.write("verdict", t, node=None, reason="schedule", status="error", confidence=0.0, mistake=None,
                          visibility="ok", view_request=None, model=baseline.model, role="baseline", prompt_version="",
                          latency_ms=0.0, input_tokens=0, output_tokens=0, cost_usd=0.0, orig_cost_usd=0.0, cached=False,
                          error=r["error"])
            else:
                sid = name2id.get(r["current_step"], "")
                log.write("verdict", t, node=sid, reason="schedule", status="baseline", confidence=r["step_confidence"],
                          mistake={"description": r["mistake_description"], "correction": r["correction"]} if r["mistake"] else None,
                          visibility="ok", view_request=None, model=r["model"], role="baseline", prompt_version=r["prompt_version"],
                          latency_ms=r["latency_ms"], input_tokens=r["input_tokens"], output_tokens=r["output_tokens"],
                          cost_usd=0.0 if r.get("cached") else r["cost_usd"], orig_cost_usd=r["cost_usd"],
                          cached=r.get("cached", False), error=None, mistake_confidence=r["mistake_confidence"])
                t_out = t + r["latency_ms"] / 1000
                log.write("belief", t_out, p={sid or "none": r["step_confidence"]}, entropy=0.0, map=sid,
                          map_p=r["step_confidence"], time_on_step=0.0, completed=[])
                if r["mistake"] and r["mistake_confidence"] >= mistake_conf:
                    log.write("action", t_out, action="mistake", text=r["correction"] or r["mistake_description"], node=sid,
                              detail={"what": r["mistake_description"], "p": r["mistake_confidence"]})
            t += every_s
        log.write("summary", clip.duration, n_frames=n_frames, escalated_frames=3 * int(clip.duration // every_s), wall_s=0.0)
    return out



# ------------------------------------------------------------------------------------- verifier experiments
def _budget(max_calls=3000, max_usd=60.0):
    from .verify.common import Budget
    return Budget(max_calls, max_usd)


def make_verifier(kind: str, budget=None):
    budget = budget or _budget()
    if kind == "claude_fast":
        from .verify.claude import ClaudeVerifier
        return ClaudeVerifier("claude-haiku-5-5", budget, role="fast")
    if kind == "claude_sonnet":
        from .verify.claude import ClaudeVerifier
        return ClaudeVerifier("claude-sonnet-5-5", budget, role="fast")
    if kind == "claude_strong":
        from .verify.claude import ClaudeVerifier
        return ClaudeVerifier("claude-opus-5-5", budget, role="strong")
    if kind == "jev":
        from .verify.jev import JevVerifier
        return JevVerifier(budget)
    if kind == "distilled":
        from .flywheel.distill import DistilledVerifier
        return DistilledVerifier()
    raise ValueError(kind)


def build_check_sets(max_train_per_task: int = 5) -> dict:
    """GT-labeled routine checks: train-split (calibration, thresholds, student) and eval clips (comparisons)."""
    import collections
    from .eval.checks import build_checks, save_checks
    man = load_manifest()
    per = collections.Counter()
    train = []
    for c in man["train"]:
        from pathlib import Path as _P
        if _P(c["video"]).exists() and per[c["task_id"]] < max_train_per_task:
            per[c["task_id"]] += 1
            train.append(Clip.from_json(c))
    ev = [Clip.from_json(c) for c in man["eval"]]
    tr_checks = build_checks(train, max_per_clip=24)
    ev_checks = build_checks(ev, max_per_clip=12)
    save_checks(tr_checks, "train")
    save_checks(ev_checks, "eval")
    info = {"train_checks": len(tr_checks), "eval_checks": len(ev_checks), "train_recordings": [c.clip_id for c in train],
            "eval_pos_rate": float(np.mean([c.y_complete for c in ev_checks])),
            "eval_err_rate": float(np.mean([c.y_error for c in ev_checks]))}
    (RESULTS / "l5").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l5" / "check_sets.json").write_text(json.dumps(info, indent=2))
    return info


def run_checks(kind: str, split: str, limit: int = 0, workers: int = 4, crops: bool = False, degrade: str | None = None,
               subset: list[str] | None = None) -> list[dict]:
    from .eval.checks import load_checks, run_verifier_on_checks
    from .tasks.compiler import load_library
    checks = load_checks(split)
    if subset is not None:
        checks = [c for c in checks if c.check_id in set(subset)]
    if limit:
        checks = checks[:limit]
    tag = f"{kind}_{split}" + ("_crops" if crops else "") + (f"_{degrade}" if degrade else "")
    out = RESULTS.parent / "data" / "verdicts" / f"{tag}.jsonl"
    crops_fn = _crops_fn() if crops else None
    return run_verifier_on_checks(make_verifier(kind), checks, load_library(), out, workers=workers,
                                  crops_fn=crops_fn, degrade_mode=degrade)


def _crops_fn():
    """ROI crops from TAPNext++ tracks: seed a grid on the hands' working area 2 s before the check,
    track at 15 fps up to the check time, crop the tracked region from the full-resolution frame."""
    import cv2
    from .perception.backbones import Hands
    from .perception.tracks import PointTracker, crop, hand_box
    pt = PointTracker()

    def fn(ci, frames):
        cap = cv2.VideoCapture(ci.video)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        t0 = ci.t_abs - 2.0
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(max(0, t0) * fps))
        seq = []
        step = max(1, int(round(fps / 15)))
        for k in range(int(2.0 * fps) + 1):
            ok, bgr = cap.read()
            if not ok:
                break
            if k % step == 0:
                seq.append(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        cap.release()
        if len(seq) < 3:
            return []
        hands = Hands()
        hf, _ = hands.frame(seq[0], 0.0)
        hands.close()
        st = pt.seed(seq[0], hand_box(hf, seq[0].shape[:2]), 0.0)
        for i, f in enumerate(seq[1:]):
            st = pt.update(f, (i + 1) / 15)
        c = crop(seq[-1], st.roi if st else None)
        if c is None:   # tracking lost: fall back to the seeded working area
            x0, y0, x1, y1 = [int(v) for v in hand_box(hf, seq[0].shape[:2])]
            c = seq[-1][y0:y1, x0:x1]
        return [c] if c is not None and c.size else []
    return fn



# ------------------------------------------------------------------------------------- tracker tuning (train only)
def _probe_items(clips):
    from .tasks.train_probes import _labels
    out = {}
    for c in clips:
        p = FEATURES / f"{c.clip_id}.npz"
        if p.exists():
            z = np.load(p)
            out[c.clip_id] = (c, z)
    return out


def tune_tracker(max_s: float = 420.0) -> dict:
    """Leave-one-recording-out on the TRAIN split: fit step probes on the other train recordings of the recipe,
    replay the local-only engine on the held-out one, grid-search tracker temperatures by step accuracy."""
    import itertools
    from dataclasses import replace as dc_replace
    from .data.cc4d import RECIPES, recipe_steps, slug
    from .engine import EngineConfig
    from .eval.harness import run_clip, score_clip
    from .events.detector import HeuristicDetector
    from .evidence import ProbeEvidence
    from .state_tracker import TrackerConfig
    from .tasks.build_library import dataset_graph
    from .tasks.train_probes import _labels
    man = load_manifest()
    clips = [Clip.from_json(c) for c in man["train"]]
    have = {c.clip_id: c for c in clips if (FEATURES / f"{c.clip_id}.npz").exists()}
    grid = list(itertools.product([0.15, 0.3, 0.6, 1.0], [0.0, 1.0], [0.6, 0.8]))
    scores = {g: [] for g in grid}
    det = HeuristicDetector()
    for r in RECIPES:
        tid = slug(r)
        ids = [s["id"] for s in recipe_steps(r)[0]]
        rec = [c for c in have.values() if c.task_id == tid]
        if len(rec) < 2:
            continue
        g = dataset_graph(r)
        for held in rec:
            X, y = [], []
            for c in rec:
                if c.clip_id == held.clip_id:
                    continue
                z = np.load(FEATURES / f"{c.clip_id}.npz")
                X.append(np.concatenate([z["siglip"], z["window"]], 1).astype(np.float32)[::2])
                y.append(_labels(c, z["t"], ids)[::2])
            pe = ProbeEvidence.fit(ids, np.concatenate(X), np.concatenate(y))
            hc = dc_replace(held, end=min(held.end, max_s))
            stack = {"library": {tid: g}, "evidence": {tid: pe}, "recognizer": None, "detector": det}
            for gp in grid:
                lw, bw, cp = gp
                ecfg = EngineConfig(tracker_mode="local", use_verifier=False, recognize=False, commit_on_switch_p=cp,
                                    tracker=TrackerConfig(local_weight=lw, boundary_weight=bw))
                p = run_clip(hc, stack, "tune_tracker", ecfg, oracle_task=True, frames=[])
                scores[gp].append(score_clip(hc, p)["step_acc"])
        print(r, "done", flush=True)
    table = sorted(((float(np.mean(v)), k) for k, v in scores.items() if v), reverse=True)
    best = table[0][1]
    res = {"grid": [{"local_weight": k[0], "boundary_weight": k[1], "commit_on_switch_p": k[2], "mean_step_acc": m,
                     "n": len(scores[k])} for m, k in table],
           "best": {"local_weight": best[0], "boundary_weight": best[1], "commit_on_switch_p": best[2]},
           "protocol": "leave-one-recording-out over train-split recordings; local-only engine; first %ds" % int(max_s)}
    (RESULTS / "l4").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l4" / "tracker_tuning.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res["best"]), table[:3])
    return res



def framing_ablation(n: int = 100, kinds=("jev", "claude_fast", "claude_sonnet", "claude_strong")) -> dict:
    """Same n train-split checks, two evidence framings: 3 sharpest frames of the last 4 s vs temporal span."""
    import random
    from sklearn.metrics import roc_auc_score
    from .eval.checks import load_checks, run_verifier_on_checks
    from .tasks.compiler import load_library
    from .verify.calibration import raw_p_complete
    lib = load_library()
    tr = [c for c in load_checks("train") if c.task_id in lib]
    random.seed(0)
    sub = random.sample(tr, 200)[:n]
    res = {"n": n, "split": "train", "rows": []}
    for framing in ("recent3", "span"):
        for kind in kinds:
            out = RESULTS.parent / "data" / "verdicts" / f"framing_{framing}_{kind}.jsonl"
            rows = run_verifier_on_checks(make_verifier(kind), sub, lib, out, workers=6, framing=framing, log_every=0)
            rows = [r for r in rows if not r["verdict"].get("error")]
            p = np.array([raw_p_complete(r["verdict"]["step_status"], r["verdict"]["confidence"]) for r in rows])
            y = np.array([r["y_complete"] for r in rows])
            lat = [r["verdict"]["latency_ms"] for r in rows]
            cost = [r["verdict"]["raw"].get("orig_cost_usd", r["verdict"]["cost_usd"]) for r in rows]
            row = {"framing": framing, "verifier": kind, "model": rows[0]["verdict"]["model"] if rows else None, "n": len(rows),
                   "accuracy": float(((p >= 0.5) == (y == 1)).mean()), "auroc": float(roc_auc_score(y, p)),
                   "latency_ms_p50": float(np.median(lat)), "cost_usd_per_check": float(np.mean(cost))}
            res["rows"].append(row)
            print(row, flush=True)
    (RESULTS / "l5").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l5" / "framing_ablation.json").write_text(json.dumps(res, indent=2))
    return res


if __name__ == "__main__":
    import sys
    t0 = time.time()
    {"l2": l2, "probes": probes, "tune": tune_tracker}[sys.argv[1]]()
    print("done in", round(time.time() - t0), "s")

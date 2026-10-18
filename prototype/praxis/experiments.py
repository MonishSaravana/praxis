"""Experiment drivers. Each writes JSON under results/ and is reproducible from the README commands."""
from __future__ import annotations

import zlib

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
        for tol, vv in v.items():
            print(k, tol, {m: (round(vv[m]["precision"], 3), round(vv[m]["recall"], 3), round(vv[m]["f1"], 3)) for m in vv})
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
        from .verify.common import span_keyframes

        def frame_at(x):
            i = int(round(x * 4))
            return frames[i] if 0 <= i < n_frames else None
        while t <= clip.duration:
            fr, ts = span_keyframes(frame_at, t)       # same evidence selection as the engine's verifier
            r = baseline.query(fr, graph.title, names, frame_ages=[t - x for x in ts])
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


def make_verifier(kind: str, budget=None, role: str | None = None):
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
    if kind.startswith("openai:"):                      # openai:gpt-6-luna, or openai:gpt-6-luna@none (reasoning effort)
        from .verify.openai_vlm import OpenAIVerifier
        model, _, effort = kind.split(":", 1)[1].partition("@")
        return OpenAIVerifier(model, budget, effort=effort or "low", role=role or "fast")
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
    """ROI crops from TAPNext++ tracks: seed a grid on the hands' working area 1.6 s before the check,
    track at 10 fps up to the check time, crop the tracked region from the full-resolution frame."""
    import cv2
    from .perception.backbones import Hands
    from .perception.tracks import PointTracker, crop, hand_box
    pt = PointTracker()

    def fn(ci, frames):
        cap = cv2.VideoCapture(ci.video)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        t0 = ci.t_abs - 1.6
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(max(0, t0) * fps))
        seq = []
        step = max(1, int(round(fps / 10)))
        for k in range(int(1.6 * fps) + 1):
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
            st = pt.update(f, (i + 1) / 10)
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


def tune_tracker(max_s: float = 420.0, local_weights=(0.15, 0.3, 0.6, 1.0), boundary_weights=(0.0, 1.0),
                 commit_ps=(0.6, 0.8), out_name: str = "tracker_tuning") -> dict:
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
    grid = list(itertools.product(local_weights, boundary_weights, commit_ps))
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
                p = run_clip(hc, stack, f"tune_{out_name}", ecfg, oracle_task=True, frames=[])
                scores[gp].append(score_clip(hc, p)["step_acc"])
        print(r, "done", flush=True)
    table = sorted(((float(np.mean(v)), k) for k, v in scores.items() if v), reverse=True)
    best = table[0][1]
    res = {"grid": [{"local_weight": k[0], "boundary_weight": k[1], "commit_on_switch_p": k[2], "mean_step_acc": m,
                     "n": len(scores[k])} for m, k in table],
           "best": {"local_weight": best[0], "boundary_weight": best[1], "commit_on_switch_p": best[2]},
           "protocol": "leave-one-recording-out over train-split recordings; local-only engine; first %ds" % int(max_s)}
    (RESULTS / "l4").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l4" / f"{out_name}.json").write_text(json.dumps(res, indent=2))
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



def adaptive_detail(run_name: str = "fused") -> dict:
    """L6: does the time-on-step signal fire where GT shows struggle? Reported as an association, not as
    evidence that it helps users.
    (a) GT-only: per annotated step on eval clips, ratio = time from previous step end to this step end over the
        train-split duration prior; compare steps with GT errors vs without.
    (b) Engine: steps that received a 'hint' (expanded detail) in the run logs vs GT error / ratio."""
    from scipy.stats import mannwhitneyu
    from .runlog import by_kind, read_log
    from .tasks.compiler import load_library
    lib = load_library()
    man = load_manifest()
    rows = []
    for cj in man["eval"]:
        c = Clip.from_json(cj)
        g = lib[c.task_id]
        prev_end = 0.0
        for s in sorted(c.segments, key=lambda x: x.start):
            node = g.node(s.step)
            if not node.duration or s.start < 1.0:
                prev_end = max(prev_end, s.end)
                continue
            dur = s.end - max(prev_end, s.start - 60.0)
            prev_end = max(prev_end, s.end)
            tags = [e["tag"] for e in s.errors if e["tag"] != "Missing Step"]
            rows.append({"clip": c.clip_id, "step": s.step, "ratio": dur / node.duration.mean_s, "error": bool(s.has_error and tags),
                         "tags": tags})
    r_err = [r["ratio"] for r in rows if r["error"]]
    r_ok = [r["ratio"] for r in rows if not r["error"]]
    u = mannwhitneyu(r_err, r_ok, alternative="greater") if r_err and r_ok else None
    thr = 1.6
    slow = [r for r in rows if r["ratio"] > thr]
    res = {"gt_only": {"n_steps": len(rows), "median_ratio_error_steps": float(np.median(r_err)) if r_err else None,
                       "median_ratio_ok_steps": float(np.median(r_ok)) if r_ok else None,
                       "mannwhitney_p_error_slower": float(u.pvalue) if u else None,
                       "threshold": thr, "share_slow_steps_with_error": float(np.mean([r["error"] for r in slow])) if slow else None,
                       "share_all_steps_with_error": float(np.mean([r["error"] for r in rows])) if rows else None,
                       "median_ratio_by_error_type": {t: {"n": len(v), "median_ratio": float(np.median(v))} for t, v in
                                                      {t: [r["ratio"] for r in rows if t in r["tags"]] for t in
                                                       sorted({t for r in rows for t in r["tags"]})}.items() if v}}}
    hinted, total = [], []
    for cj in man["eval"]:
        c = Clip.from_json(cj)
        p = RESULTS.parent / "runs" / run_name / f"{c.clip_id}.jsonl"
        if not p.exists():
            continue
        acts = by_kind(read_log(p), "action")
        hints = {a["node"] for a in acts if a["action"] == "hint"}
        for s in c.segments:
            tags = [e["tag"] for e in s.errors if e["tag"] != "Missing Step"]
            e = bool(s.has_error and tags)
            total.append(e)
            if s.step in hints:
                hinted.append(e)
    if total:
        res["engine"] = {"run": run_name, "n_steps": len(total), "n_hinted_steps": len(hinted),
                         "error_rate_hinted_steps": float(np.mean(hinted)) if hinted else None,
                         "error_rate_all_steps": float(np.mean(total))}
    (RESULTS / "l6").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l6" / "adaptive_detail.json").write_text(json.dumps(res, indent=2))
    return res



def distill(teacher: str = "claude_strong", alpha_gt: float = 0.5) -> dict:
    """L7: train a local student on teacher verdicts (+GT) from TRAIN-split checks; evaluate on held-out eval-clip
    checks: agreement with the teacher, accuracy vs GT, latency, cost."""
    import time as _t
    import torch
    from .eval.verifier_eval import fit_calibrators, load
    from .flywheel.distill import DistilledVerifier, featurize, predict, train_student
    from .verify.calibration import raw_p_complete
    cal = fit_calibrators(teacher)
    tr = load(f"{teacher}_train")
    te = load(f"{teacher}_eval")
    Xtr, ktr = featurize(tr)
    Xte, kte = featurize(te)
    tr = [tr[i] for i in ktr]
    te = [te[i] for i in kte]
    p_raw = lambda rows: np.array([raw_p_complete(r["verdict"]["step_status"], r["verdict"]["confidence"]) for r in rows])
    yt_tr = cal[0](p_raw(tr)) if cal else p_raw(tr)
    yg_tr = np.array([r["y_complete"] for r in tr], float)
    m, info = train_student(Xtr, yt_tr, yg_tr, alpha=alpha_gt)
    DistilledVerifier.save(m, Xtr.shape[1], info=info)
    t0 = _t.perf_counter()
    ps = predict(m, Xte)
    lat_ms = (_t.perf_counter() - t0) * 1000 / max(1, len(Xte))
    # single-check latency (what the engine pays)
    t1 = _t.perf_counter()
    for i in range(min(50, len(Xte))):
        predict(m, Xte[i:i + 1])
    lat1 = (_t.perf_counter() - t1) * 1000 / max(1, min(50, len(Xte)))
    pt = cal[0](p_raw(te)) if cal else p_raw(te)
    y = np.array([r["y_complete"] for r in te])
    teacher_lat = [r["verdict"]["latency_ms"] for r in te]
    teacher_cost = [r["verdict"]["raw"].get("orig_cost_usd", r["verdict"]["cost_usd"]) for r in te]
    from sklearn.metrics import roc_auc_score
    res = {"teacher": teacher, "teacher_model": te[0]["verdict"]["model"] if te else None, "n_train": len(tr), "n_test": len(te),
           "alpha_gt": alpha_gt, "features": "SigLIP2 frame (mean of last 1 s) + V-JEPA 2 window + SigLIP2 end-state text emb + product",
           "agreement": float(((ps >= 0.5) == (pt >= 0.5)).mean()),
           "student_acc_vs_gt": float(((ps >= 0.5) == (y == 1)).mean()), "teacher_acc_vs_gt": float(((pt >= 0.5) == (y == 1)).mean()),
           "student_auroc": float(roc_auc_score(y, ps)) if len(set(y)) > 1 else None,
           "teacher_auroc": float(roc_auc_score(y, pt)) if len(set(y)) > 1 else None,
           "student_latency_ms_p50": float(lat1), "student_latency_ms_batched": float(lat_ms),
           "teacher_latency_ms_p50": float(np.median(teacher_lat)),
           "student_cost_per_1k_checks_usd": 0.0, "teacher_cost_per_1k_checks_usd": float(np.mean(teacher_cost) * 1000),
           "student_device": "cpu", "train_info": info}
    # confidence-gated routing: student answers when confident, teacher otherwise
    conf = np.abs(ps - 0.5) * 2
    for thr in (0.5, 0.7, 0.9):
        use_s = conf >= thr
        final = np.where(use_s, ps >= 0.5, pt >= 0.5)
        res[f"routed_conf{thr}"] = {"share_handled_locally": float(use_s.mean()), "acc_vs_gt": float((final == (y == 1)).mean()),
                                    "cost_per_1k_usd": float((~use_s).mean() * np.mean(teacher_cost) * 1000)}
    (RESULTS / "l7").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l7" / "distill.json").write_text(json.dumps(res, indent=2))
    return res



def crops_vs_full(n: int = 120, kind: str = "claude_strong") -> dict:
    """L1 point-tracking crops: same verifier, same eval checks, with vs without a TAPNext++ ROI crop."""
    import random
    from sklearn.metrics import roc_auc_score
    from .eval.checks import load_checks
    from .eval.verifier_eval import load
    from .verify.calibration import raw_p_complete
    from .tasks.compiler import load_library
    lib = load_library()
    ev = [c for c in load_checks("eval") if c.task_id in lib]
    fine = [c for c in ev if any(ch.kind in ("orientation", "alignment", "quantity", "part_identity")
                                 for ch in lib[c.task_id].node(c.node).checks)]
    random.seed(1)
    sub = random.sample(fine, min(n, len(fine)))
    ids = [c.check_id for c in sub]
    # phase 1: TAPNext++ crops computed sequentially (one tracker, one GPU stream) and cached as images
    import cv2 as _cv2
    crop_dir = RESULTS.parent / "data" / "checks" / "crops"
    crop_dir.mkdir(parents=True, exist_ok=True)
    fn = _crops_fn()
    from .eval.checks import cached_span_frames
    import time as _time
    t0 = _time.time()
    track_s = []
    for i, ci in enumerate(sub):
        f = crop_dir / f"{ci.check_id.replace(':', '_')}.png"
        if f.exists():
            continue
        fr, _ = cached_span_frames(ci)
        ts = _time.time()
        cs = fn(ci, fr)
        track_s.append(_time.time() - ts)
        if cs:
            _cv2.imwrite(str(f), _cv2.cvtColor(cs[0], _cv2.COLOR_RGB2BGR))
        else:
            f.write_bytes(b"")
        if (i + 1) % 10 == 0:
            print(f"  crops {i + 1}/{len(sub)} ({_time.time() - t0:.0f}s)", flush=True)

    def saved_crops(ci, frames):
        f = crop_dir / f"{ci.check_id.replace(':', '_')}.png"
        if not f.exists() or f.stat().st_size == 0:
            return []
        return [_cv2.cvtColor(_cv2.imread(str(f)), _cv2.COLOR_BGR2RGB)]
    # phase 2: verifier calls with the cached crops, in parallel
    from .eval.checks import run_verifier_on_checks
    from .tasks.compiler import load_library as _ll
    out = RESULTS.parent / "data" / "verdicts" / f"{kind}_eval_crops.jsonl"
    with_c = run_verifier_on_checks(make_verifier(kind), [c for c in ev if c.check_id in set(ids)], _ll(), out, workers=4,
                                    crops_fn=saved_crops)
    base = {r["check_id"]: r for r in load(f"{kind}_eval")}
    rows = [(r, base[r["check_id"]]) for r in with_c if r["check_id"] in base and not r["verdict"].get("error")]
    y = np.array([b["y_complete"] for _, b in rows])
    pc = np.array([raw_p_complete(r["verdict"]["step_status"], r["verdict"]["confidence"]) for r, _ in rows])
    pf = np.array([raw_p_complete(b["verdict"]["step_status"], b["verdict"]["confidence"]) for _, b in rows])
    ye = np.array([b["y_error"] for _, b in rows])
    dc = np.array([r["verdict"]["step_status"] == "deviation" for r, _ in rows])
    df = np.array([b["verdict"]["step_status"] == "deviation" for _, b in rows])
    res = {"verifier": kind, "n": len(rows), "subset": "eval checks whose node has orientation/alignment/quantity/part-identity checks",
           "full_frames": {"accuracy": float(((pf >= .5) == (y == 1)).mean()), "auroc": float(roc_auc_score(y, pf)),
                           "deviation_precision": float(ye[df].mean()) if df.any() else None, "n_deviation": int(df.sum())},
           "with_crops": {"accuracy": float(((pc >= .5) == (y == 1)).mean()), "auroc": float(roc_auc_score(y, pc)),
                          "deviation_precision": float(ye[dc].mean()) if dc.any() else None, "n_deviation": int(dc.sum())},
           "crop_rate": float(np.mean([r["n_crops"] > 0 for r, _ in rows])),
           "tokens_full": float(np.mean([b["verdict"]["input_tokens"] for _, b in rows])),
           "tokens_with_crops": float(np.mean([r["verdict"]["input_tokens"] for r, _ in rows])),
           "tapnext_seconds_per_crop_p50": float(np.median(track_s)) if track_s else None,
           "crop_protocol": "seed a 6x6 grid on the hands' working area 1.6 s before the check, track at 10 fps with "
                            "TAPNext++ (MPS), crop the tracked region (fallback: seeded hand area) from the full frame"}
    (RESULTS / "l5").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l5" / "crops_vs_full.json").write_text(json.dumps(res, indent=2))
    return res


def visual_uncertainty(n: int = 60, modes=("blur", "occlude", "crop_away"), conf_thr: float = 0.7) -> dict:
    """Degrade the view on mid-step eval checks (GT: person is on this step, in progress). Engine verifier (typed,
    may say 'view insufficient') vs stateless baseline (same model, must answer). Count view requests vs confident
    wrong calls."""
    import random
    from concurrent.futures import ThreadPoolExecutor
    from .eval.checks import degrade, load_checks, run_verifier_on_checks, span_frames
    from .tasks.compiler import load_library
    from .verify.claude import StatelessBaseline
    lib = load_library()
    mids = [c for c in load_checks("eval") if c.kind == "mid" and c.task_id in lib]
    random.seed(2)
    sub = random.sample(mids, min(n, len(mids)))
    budget = _budget(1500, 20.0)
    ver = make_verifier("claude_strong", budget)
    bl = StatelessBaseline("claude-opus-5-5", budget, effort="medium")
    res = {"n": len(sub), "conf_thr": conf_thr, "verifier": "claude-opus-5-5", "modes": {}}
    for mode in (None,) + tuple(modes):
        tag = mode or "none"
        out = RESULTS.parent / "data" / "verdicts" / f"uncert_engine_{tag}.jsonl"
        er = run_verifier_on_checks(ver, sub, lib, out, workers=4, degrade_mode=mode, log_every=0)

        def base_one(ci):
            fr, ages = span_frames(ci.video, ci.t_abs)
            if mode:
                fr = degrade(fr, mode, seed=zlib.crc32(ci.check_id.encode()) % 1000)
            g = lib[ci.task_id]
            r = bl.query(fr, g.title, [nd.name for nd in g.nodes], frame_ages=ages)
            return ci, r
        with ThreadPoolExecutor(4) as ex:
            br = list(ex.map(base_one, sub))
        rows_out = RESULTS.parent / "data" / "verdicts" / f"uncert_baseline_{tag}.jsonl"
        with rows_out.open("w") as fo:
            for ci, r in br:
                fo.write(json.dumps({"check_id": ci.check_id, "node_name": lib[ci.task_id].node(ci.node).name,
                                     "y_error": ci.y_error, "baseline": r}, default=str) + "\n")
        sweep = {}
        for thr in (0.5, 0.7, 0.9):
            sweep[str(thr)] = {
                "engine_confident_wrong": float(np.mean([r["verdict"]["visibility"] == "ok" and r["verdict"]["confidence"] >= thr
                                                         and r["verdict"]["step_status"] == "complete" for r in er])),
                "baseline_confident_wrong_step": float(np.mean([r.get("current_step") != lib[ci.task_id].node(ci.node).name
                                                                and r.get("step_confidence", 0) >= thr for ci, r in br if "error" not in r]))}
        e_view = np.mean([r["verdict"]["visibility"] == "insufficient" for r in er])
        e_wrong = np.mean([r["verdict"]["visibility"] == "ok" and r["verdict"]["confidence"] >= conf_thr and
                           r["verdict"]["step_status"] == "complete" for r in er])
        e_false_mistake = np.mean([r["verdict"]["step_status"] == "deviation" and r["verdict"]["confidence"] >= conf_thr and
                                   not r["y_error"] for r in er])
        name_of = lambda ci: lib[ci.task_id].node(ci.node).name
        b_ok = [(ci, r) for ci, r in br if "error" not in r]
        b_wrong = np.mean([r["current_step"] != name_of(ci) and r["step_confidence"] >= conf_thr for ci, r in b_ok])
        b_false_mistake = np.mean([r["mistake"] and r["mistake_confidence"] >= conf_thr and not ci.y_error for ci, r in b_ok])
        res["modes"][tag] = {"engine_view_request_rate": float(e_view), "engine_confident_wrong_rate": float(e_wrong),
                             "engine_confident_false_mistake_rate": float(e_false_mistake),
                             "baseline_confident_wrong_step_rate": float(b_wrong),
                             "baseline_confident_false_mistake_rate": float(b_false_mistake), "baseline_n": len(b_ok),
                             "threshold_sweep": sweep,
                             "baseline_mean_step_confidence": float(np.mean([r["step_confidence"] for _, r in b_ok])) if b_ok else None,
                             "baseline_step_accuracy": float(np.mean([r["current_step"] == name_of(ci) for ci, r in b_ok])) if b_ok else None}
        print(tag, res["modes"][tag], flush=True)
    res["spend_usd"] = budget.usd
    (RESULTS / "l5").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l5" / "visual_uncertainty.json").write_text(json.dumps(res, indent=2))
    return res



def join_mid_task(join_at: float = 90.0, window_s: float = 30.0, workers: int = 3, use_verifier: bool = True) -> dict:
    """L3b/L4: start the engine `join_at` seconds into each clip with no history. Compare the mid-task prior
    (uniform over steps, ancestors assumed done once localized) to naively assuming the task just started."""
    import copy
    from concurrent.futures import ThreadPoolExecutor
    from .eval import harness
    from .eval import metrics as M
    from .eval.run_all import calibrators, engine_config, eval_clips
    from .runlog import read_log
    stack = harness.load_stack()
    budget = _budget(1500, 10.0)
    ver = make_verifier("jev", budget) if use_verifier else None
    esc = make_verifier("claude_strong", budget) if use_verifier else None
    cals = {"primary": calibrators("jev"), "escalation": calibrators("claude_strong")}
    clips = [c for c in eval_clips() if c.duration >= join_at + 60]
    res = {"join_at_s": join_at, "window_s": window_s, "use_verifier": use_verifier, "n_clips": len(clips), "modes": {}}
    for mode, join_flag in (("mid_task_prior", True), ("assume_start", False)):
        ecfg = engine_config({"join_mid_task": join_flag, "use_verifier": use_verifier})

        def one(c):
            st = dict(stack)
            st["recognizer"] = copy.deepcopy(stack["recognizer"])
            p = harness.run_clip(c, st, f"join_{mode}", ecfg, ver, esc, oracle_task=True, join_at=join_at, calibrators=cals)
            recs = read_log(p)
            segs = [(s.start - join_at, s.end - join_at, s.step) for s in c.segments if s.end - join_at > 0]
            times = np.arange(0.5, window_s, 0.5)
            gt = M.frame_labels(segs, times, between="next")
            pred = M.predicted_labels(recs, times)
            inside = np.array([any(a <= t < b for a, b, _ in segs) for t in times])
            ok = gt == pred
            first = next((float(t) for t, o in zip(times, ok) if o), None)
            return {"clip": c.clip_id, "acc_first_window": float(ok.mean()),
                    "acc_first_window_inside": float(ok[inside].mean()) if inside.any() else None, "t_first_correct": first}
        with ThreadPoolExecutor(workers) as ex:
            rows = list(ex.map(one, clips))
        firsts = [r["t_first_correct"] for r in rows if r["t_first_correct"] is not None]
        res["modes"][mode] = {"acc_first_window": float(np.mean([r["acc_first_window"] for r in rows])),
                              "share_localized_within_window": len(firsts) / max(1, len(rows)),
                              "t_first_correct_s": M.latency_summary(firsts), "per_clip": rows}
        print(mode, {k: v for k, v in res["modes"][mode].items() if k != "per_clip"}, flush=True)
    res["spend_usd"] = budget.usd
    (RESULTS / "l3b").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l3b" / "join_mid_task.json").write_text(json.dumps(res, indent=2, default=float))
    return res


def recognition_summary(run: str = "fused") -> dict:
    """L3b from the full-engine run (recognition on): top-1, time to recognize, per procedure."""
    r = json.loads((RESULTS / "runs" / f"{run}.json").read_text())
    rows = r["per_clip"]
    t = [x["t_recognize"] for x in rows if x["task_correct"] and x["t_recognize"] is not None]
    res = {"run": run, "n_clips": len(rows), "top1": float(np.mean([x["task_correct"] for x in rows])),
           "recognized_any": float(np.mean([x["recognized_task"] is not None for x in rows])),
           "t_recognize_s": {"p50": float(np.median(t)) if t else None, "p95": float(np.percentile(t, 95)) if t else None,
                             "n": len(t)},
           "confusions": [{"clip": x["clip"], "gt": x["task_id"], "pred": x["recognized_task"]} for x in rows if not x["task_correct"]],
           "library_size": None}
    from .tasks.compiler import load_library
    res["library_size"] = len(load_library())
    (RESULTS / "l3b").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l3b" / "recognition.json").write_text(json.dumps(res, indent=2))
    return res



def dev_eval(designs: dict | None = None, max_s: float = 300.0, max_per_task: int = 3, workers: int = 3,
             out_name: str = "design_selection") -> dict:
    """Design selection on the TRAIN split (never the eval clips): leave-one-recording-out step probes, engine with
    the task given, first `max_s` seconds of each train recording. Compares engine designs by step accuracy, cost,
    and calls."""
    import copy
    from concurrent.futures import ThreadPoolExecutor
    from dataclasses import replace as dc_replace
    from .data.cc4d import RECIPES, recipe_steps, slug
    from .eval import harness
    from .eval.run_all import calibrators, engine_config
    from .evidence import ProbeEvidence
    from .tasks.compiler import load_library
    from .tasks.train_probes import _labels
    lib = load_library()
    man = load_manifest()
    clips = [Clip.from_json(c) for c in man["train"] if (FEATURES / f"{c['clip_id']}.npz").exists()]
    by_task: dict = {}
    for c in clips:
        by_task.setdefault(c.task_id, []).append(c)
    designs = designs or {
        "jev_localize": {"verifier": "jev", "esc": "claude_strong", "over": {}},
        "opus_localize": {"verifier": "jev", "esc": "claude_strong", "over": {}, "localizer": "claude_strong"},
        "no_localize": {"verifier": "jev", "esc": "claude_strong", "over": {"step_choice": False}},
    }
    jobs = []
    for r in RECIPES:
        tid = slug(r)
        rec = by_task.get(tid, [])[:max_per_task]
        if len(rec) < 2:
            continue
        ids = [s["id"] for s in recipe_steps(r)[0]]
        for held in rec:
            X, y = [], []
            for c in rec:
                if c.clip_id == held.clip_id:
                    continue
                z = np.load(FEATURES / f"{c.clip_id}.npz")
                X.append(np.concatenate([z["siglip"], z["window"]], 1).astype(np.float32)[::2])
                y.append(_labels(c, z["t"], ids)[::2])
            pe = ProbeEvidence.fit(ids, np.concatenate(X), np.concatenate(y))
            jobs.append((tid, dc_replace(held, end=min(held.end, max_s)), pe))
    base_stack = harness.load_stack()
    res = {"protocol": f"train-split recordings, leave-one-recording-out probes, first {max_s:.0f}s, task given",
           "n_recordings": len(jobs), "designs": {}}
    for name, d in designs.items():
        budget = _budget(3000, 15.0)
        ver = make_verifier(d["verifier"], budget)
        esc = make_verifier(d["esc"], budget) if d.get("esc") else None
        loc = make_verifier(d["localizer"], budget) if d.get("localizer") else None
        cals = {"primary": calibrators(d["verifier"]), "escalation": calibrators(d.get("esc"))}
        ecfg = engine_config(d["over"])

        def one(job):
            tid, c, pe = job
            st = dict(base_stack)
            st["evidence"] = {**base_stack["evidence"], tid: pe}
            st["recognizer"] = copy.deepcopy(base_stack["recognizer"])
            p = harness.run_clip(c, st, f"dev_{name}", ecfg, ver, esc, oracle_task=True, calibrators=cals, localizer=loc)
            return harness.score_clip(c, p)
        with ThreadPoolExecutor(workers) as ex:
            rows = list(ex.map(one, jobs))
        agg = harness.aggregate(rows)
        res["designs"][name] = {"step_acc": agg["step_acc"], "verifier_calls": agg["verifier_calls"], "cost_usd": agg["cost_usd"],
                                "false_alarms_per_min": agg["false_alarms_per_min"], "mistakes": agg["mistakes"],
                                "spend_usd": budget.usd}
        print(name, res["designs"][name], flush=True)
    (RESULTS / "dev").mkdir(parents=True, exist_ok=True)
    (RESULTS / "dev" / f"{out_name}.json").write_text(json.dumps(res, indent=2, default=float))
    return res



def l2_eval_existing() -> dict:
    """Evaluate the SAVED L2 checkpoint (the one every engine run used) with its saved thresholds on held-out eval clips
    and on procedure types never seen in training. No retraining."""
    from .events.detector import HeuristicDetector, LearnedDetector
    from .events.train import evaluate
    from .paths import CKPT
    p = RESULTS / "l2" / "l2_event_detector.json"
    res = json.loads(p.read_text())
    det = LearnedDetector.load(CKPT / "l2_event_detector.pt")
    heur = HeuristicDetector()
    thr, hthr = res["train"]["thr"], res["train"]["heuristic_thr"]
    man = load_manifest()
    sets = {"heldout_videos": _items([Clip.from_json(c) for c in man["eval"]]),
            "heldout_procedure_types": _items([Clip.from_json(c) for c in man["heldout_type"]])}
    res["test"] = {}
    for name, items in sets.items():
        res["test"][name] = {}
        for tol in (2.0, 5.0):
            res["test"][name][f"tol{int(tol)}s"] = {"learned": evaluate(det, items, thr, tol=tol),
                                                    "heuristic": evaluate(heur, items, hthr, tol=tol)}
    res["evaluated_checkpoint"] = "data/checkpoints/l2_event_detector.pt (same file all engine runs loaded)"
    p.write_text(json.dumps(res, indent=2, default=float))
    for k, v in res["test"].items():
        for tol, vv in v.items():
            print(k, tol, {m: (round(vv[m]["precision"], 3), round(vv[m]["recall"], 3), round(vv[m]["f1"], 3), vv[m]["n_clips"]) for m in vv})
    return res


if __name__ == "__main__":
    import sys
    t0 = time.time()
    {"l2": l2, "l2_eval": l2_eval_existing, "probes": probes, "tune": tune_tracker}[sys.argv[1]]()
    print("done in", round(time.time() - t0), "s")


# ------------------------------------------------------------------------------------- multi-task (train only)
def _lm_feature_rows(clips, lib, window_s: float, top_frac: float = 0.2, max_s: float = 600.0, texts=None):
    """Per second of each train recording: landmark off-task features for every CaptainCook4D library task as the
    hypothesised current task. y = 1 when it is the recording's own recipe (on-task)."""
    from .landmarks import Landmarks
    from .perception.extract import load_features
    cands = sorted(t for t in lib if t.startswith("cc4d_"))
    X, y, g, hit = [], [], [], []
    for gi, c in enumerate(clips):
        feats, _ = load_features(c.clip_id)
        lm = Landmarks(lib, texts=texts, window_s=window_s, top_frac=top_frac, non_task=[])
        tt = feats.t
        for sec in range(1, int(min(tt[-1], max_s)) + 1):
            sel = (tt > sec - 1) & (tt <= sec)
            if not sel.any():
                continue
            lm.update(feats.frame[sel])
            if sec < 5:
                continue
            s = lm.scores()
            hit.append(max((k for k in s if k in cands), key=s.get) == c.task_id)
            for t in cands:
                X.append(lm.features(t))
                y.append(int(t == c.task_id))
                g.append(gi)
    return np.array(X), np.array(y), np.array(g), float(np.mean(hit))


def fit_offtask(windows=(10.0, 20.0, 30.0, 60.0), top_frac: float = 0.2, max_s: float = 600.0, folds: int = 5) -> dict:
    """Off-task model for the tracker's away states, TRAIN split only, no model calls: P(not doing task T | landmark
    features for T), logistic on two features, balanced classes. Window choice, fixed before looking: the smallest
    window whose grouped-CV AUC is within 0.02 of the best."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from .landmarks import OffTaskModel, TextCache
    from .paths import CKPT
    from .tasks.compiler import load_library
    lib = load_library()
    man = load_manifest()
    clips = [Clip.from_json(c) for c in man["train"] if (FEATURES / f"{c['clip_id']}.npz").exists()
             and c["task_id"] in lib]
    texts = TextCache()
    res = {"protocol": f"train-split recordings ({len(clips)}), first {max_s:.0f}s, per second, each paired with every "
                       f"CaptainCook4D library task; grouped {folds}-fold CV by recording", "windows": {}}
    best = {}
    for w in windows:
        X, y, g, acc = _lm_feature_rows(clips, lib, w, top_frac, max_s, texts)
        p = np.zeros(len(y))
        for k in range(folds):
            te = (g % folds) == k
            m = LogisticRegression(class_weight="balanced").fit(X[~te], y[~te])
            p[te] = m.predict_proba(X[te])[:, 1]
        auc = float(roc_auc_score(y, p))
        m = LogisticRegression(class_weight="balanced").fit(X, y)
        res["windows"][str(int(w))] = {"cv_auc_on_vs_off": auc, "recipe_top1_per_second": acc, "n_rows": int(len(y)),
                                       "coef": m.coef_[0].tolist(), "intercept": float(m.intercept_[0])}
        best[w] = (auc, m)
        # every window's model is kept: the train-split engine sweep can trade detection latency against accuracy
        OffTaskModel(m.coef_[0].tolist(), float(m.intercept_[0]), w, top_frac,
                     {"cv_auc": auc, "split": "train", "n_recordings": len(clips)}).save(CKPT / f"offtask_landmarks_w{int(w)}.json")
        print(f"window {w:.0f}s  AUC {auc:.3f}  recipe top-1 {acc:.3f}", flush=True)
    top = max(a for a, _ in best.values())
    w = min(k for k, (a, _) in best.items() if a >= top - 0.02)
    auc, m = best[w]
    res["chosen_window_s"] = w
    OffTaskModel(m.coef_[0].tolist(), float(m.intercept_[0]), w, top_frac,
                 {"cv_auc": auc, "split": "train", "n_recordings": len(clips)}).save(CKPT / "offtask_landmarks.json")
    (RESULTS / "multitask").mkdir(parents=True, exist_ok=True)
    (RESULTS / "multitask" / "offtask_fit.json").write_text(json.dumps(res, indent=2))
    return res


def calibrate_openai(model: str = "gpt-6.1-sol", budget_usd: float = 3.5, workers: int = 6) -> dict:
    """Answer all TRAIN checks with an OpenAI model (hard budget) and fit its calibrators like the other tiers
    (eval/verifier_eval.fit_calibrators): data/verdicts/openai_<model>_train.jsonl -> checkpoints cal_/devcal_openai_<model>.pkl."""
    from .eval.checks import load_checks, run_verifier_on_checks
    from .eval.verifier_eval import fit_calibrators, load
    from .tasks.compiler import load_library
    from .verify.common import Budget
    kind = f"openai_{model}"
    checks = load_checks("train")
    budget = Budget(len(checks) + 10, budget_usd)
    rows = run_verifier_on_checks(make_verifier(f"openai:{model}", budget), checks, load_library(),
                                  RESULTS.parent / "data" / "verdicts" / f"{kind}_train.jsonl", workers=workers, log_every=100)
    ok = load(f"{kind}_train")
    cals = fit_calibrators(kind)
    from sklearn.metrics import roc_auc_score
    from .verify.calibration import raw_p_complete
    p = np.array([raw_p_complete(r["verdict"]["step_status"], r["verdict"]["confidence"]) for r in ok])
    y = np.array([r["y_complete"] for r in ok])
    res = {"model": model, "n": len(rows), "ok": len(ok), "accuracy": float(((p >= 0.5) == (y == 1)).mean()),
           "auroc": float(roc_auc_score(y, p)), "calibrators": cals is not None, "spend_usd": budget.usd}
    (RESULTS / "l5").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l5" / f"calibration_{kind}.json").write_text(json.dumps(res, indent=2))
    print(res, flush=True)
    return res

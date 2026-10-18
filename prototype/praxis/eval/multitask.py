"""SYNTHETIC multi-task benchmark (docs/MULTITASK.md). CaptainCook4D has one recipe per video, so multi-task sessions are
made by splicing recordings. The splices cut hard (the camera jumps), unlike real life where people walk between
stations, so switch latency here is not a real-life latency. Every result from this module is labeled SYNTHETIC.

Sequence kinds (cuts fall at annotated step boundaries, so "resume at the right step" has a defined answer):
  seq        A (first 300 s) -> B (first 300 s)                          switch latency, wrong / missed switches
  resume     A to a step boundary -> B (150 s) -> rest of A               + resume: did A come back, at the right step?
  interrupt  A to a step boundary -> 60 s of a recipe not in the library -> rest of A
                                                                          no switch to a library task; A resumed

Train-split splices (for choosing thresholds) use 3 folds by recording: a splice only joins recordings of one fold, and
runs with a recognizer and step probes refit without that fold, so no recording is ever scored by a model that saw it.
"""
from __future__ import annotations

import copy
import json
import pickle
import random
from dataclasses import replace
from pathlib import Path

import numpy as np

from ..data.cc4d import Clip, load_manifest
from ..engine import Engine, replay
from ..events.detector import ClipFeatures
from ..io.sources import FileSource
from ..paths import CKPT, FEATURES, RESULTS, RUNS
from ..perception.extract import load_features
from ..runlog import RunLog, by_kind, read_log
from . import metrics as M
from .harness import current_task, task_changes

OTHER = "__other__"          # a part showing a recipe that is not in the library


# ------------------------------------------------------------------------------------------- folds (train split)
def train_recordings(lib, version: str = "v1") -> list[tuple[Clip, int]]:
    """Train recordings with a fold each.
    v1: the 24 recordings the multi-task sweeps used (results/multitask/train_folds_v1.json, frozen so they reproduce).
    all: every train recording with features; fold = crc32(recording) mod 3, stable as more features are added."""
    import zlib
    man = load_manifest()
    clips = {c["clip_id"]: Clip.from_json(c) for c in man["train"] if c["task_id"] in lib}
    if version == "v1":
        fz = json.loads((RESULTS / "multitask" / "train_folds_v1.json").read_text())["recordings"]
        return [(clips[r["clip_id"]], r["fold"]) for r in fz]
    have = [c for c in clips.values() if (FEATURES / f"{c.clip_id}.npz").exists()]
    return [(c, zlib.crc32(c.recording.encode()) % 3) for c in sorted(have, key=lambda c: (c.task_id, c.clip_id))]


def fold_stack(base: dict, fold: int, version: str = "v1", probe: str = "frame+window") -> dict:
    """The stack with the recognizer and every recipe's step probe refit without fold `fold`'s recordings (cached).
    version picks the recording set (train_recordings)."""
    from ..data.cc4d import RECIPES, recipe_steps, slug
    from ..evidence import ProbeEvidence
    from ..tasks.recognizer import TaskRecognizer
    from ..tasks.train_probes import collect
    d = CKPT / (("folds" if version == "v1" else f"folds_{version}") + ("" if probe == "frame+window" else f"_{probe}"))
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"fold{fold}.pkl"
    if p.exists():
        rec, ev = pickle.loads(p.read_bytes())
    else:
        ids = {slug(r): [s["id"] for s in recipe_steps(r)[0]] for r in RECIPES}
        keep = [c for c, f in train_recordings(base["library"], version) if f != fold]
        data = collect(keep, ids)
        ev = {}
        for tid in ids:
            tr = [v for v in data.values() if v["task"] == tid]
            if tr:
                if probe == "frame":
                    from ..evidence import FrameProbeEvidence
                    X = np.concatenate([v["siglip"] for v in tr])
                    ev[tid] = FrameProbeEvidence.fit(ids[tid], X, np.concatenate([v["y"] for v in tr]))
                else:
                    X = np.concatenate([np.concatenate([v["siglip"], v["window"]], 1) for v in tr])
                    ev[tid] = ProbeEvidence.fit(ids[tid], X, np.concatenate([v["y"] for v in tr]))
        tasks = sorted(ids)
        X = np.concatenate([np.concatenate([v["siglip"], v["window"]], 1)[::2] for v in data.values()])
        y = np.concatenate([[tasks.index(v["task"])] * len(v["siglip"][::2]) for v in data.values()])
        rec = TaskRecognizer(task_ids=tasks).fit(X, y)
        p.write_bytes(pickle.dumps((rec, ev)))
    st = dict(base)
    st["evidence"] = {**base["evidence"], **ev}
    rec = copy.deepcopy(rec)
    for k, v in (("forget", 0.92), ("local_temp", 0.3)):        # same defaults as TaskRecognizer.load
        setattr(rec, k, v)
    rec.reset()
    st["recognizer"] = rec
    return st


# ------------------------------------------------------------------------------------------- splices
def _cut(clip: Clip, lo: float = 90.0, hi: float = 210.0, aim: float = 150.0) -> float | None:
    """A step boundary inside A: the annotated step end in [lo, hi] closest to `aim` (+0.5 s)."""
    ends = [s.end for s in clip.segments if lo <= s.end <= hi]
    return min(ends, key=lambda e: abs(e - aim)) + 0.5 if ends else None


def make_splices(split: str = "eval", seed: int = 0, n_seq: int = 6, n_resume: int = 10, n_interrupt: int = 6,
                 lib=None, version: str = "v1") -> list[dict]:
    """Splice specs (JSON-able). eval: from the 48 eval clips (+ held-out-type recordings for interruptions). train:
    within one fold of the train recordings (first 300 s of each)."""
    from ..tasks.compiler import load_library
    lib = lib or load_library()
    man = load_manifest()
    rng = random.Random(seed)
    if split == "eval":
        pool = [(Clip.from_json(c), 0) for c in man["eval"] if (FEATURES / f"{c['clip_id']}.npz").exists()]
    else:
        pool = train_recordings(lib, version)
    others = sorted((Clip.from_json(c) for c in man.get("heldout_type", []) if (FEATURES / f"{c['clip_id']}.npz").exists()),
                    key=lambda c: c.clip_id)
    others = others[0::2] if split == "train" else others[1::2]     # interruption footage: disjoint train / eval halves

    def dur(c):
        return min(300.0, c.duration)

    def pair(fold=None):
        while True:
            (a, fa), (b, fb) = rng.sample(pool, 2)
            if a.task_id != b.task_id and fa == fb:
                return a, b, fa

    def part(c, s0, s1, task=None):
        return {"clip": c.clip_id, "task_id": task or c.task_id, "s0": round(s0, 2), "s1": round(s1, 2)}
    out = []
    for i in range(n_seq):
        a, b, f = pair()
        out.append({"id": f"{split}_seq_{i:02d}", "kind": "seq", "fold": f,
                    "parts": [part(a, 0, dur(a)), part(b, 0, dur(b))]})
    i = 0
    while i < n_resume:
        a, b, f = pair()
        c = _cut(a)
        if c is None:
            continue
        out.append({"id": f"{split}_resume_{i:02d}", "kind": "resume", "fold": f,
                    "parts": [part(a, 0, c), part(b, 0, min(150.0, dur(b))), part(a, c, dur(a))]})
        i += 1
    i = 0
    while i < n_interrupt and others:
        (a, f) = rng.choice(pool)
        c = _cut(a)
        if c is None:
            continue
        x = rng.choice(others)
        out.append({"id": f"{split}_interrupt_{i:02d}", "kind": "interrupt", "fold": f,
                    "parts": [part(a, 0, c), part(x, 0, 60.0, OTHER), part(a, c, dur(a))]})
        i += 1
    return out


def _clips() -> dict[str, Clip]:
    man = load_manifest()
    return {c["clip_id"]: Clip.from_json(c) for k in ("eval", "train", "heldout_type") for c in man.get(k, [])}


def build(spec: dict, clips: dict[str, Clip], decode: bool = True):
    """Concatenate the parts' L1 features (and decoded frames, 1:1 with feature rows) on one timeline.
    Returns (features, frames, gt) with gt = [(t0, t1, task_id, [(start, end, step), ...]), ...] in splice time."""
    T = 0.0
    fs, frames, gt = [], [], []
    for p in spec["parts"]:
        c = clips[p["clip"]]
        f, _ = load_features(c.clip_id)
        m = (f.t >= p["s0"]) & (f.t < p["s1"])
        idx = np.where(m)[0]
        fs.append((f.t[m] - p["s0"] + T, f.frame[m], f.hands[m], f.window[m], f.change[m]))
        if decode:
            fr = [x.rgb for x in FileSource(c.video, fps=4.0, start=c.start + p["s0"], end=c.start + p["s1"], max_side=640)]
            fr = (fr + [fr[-1]] * len(idx))[:len(idx)] if fr else [np.zeros((360, 640, 3), np.uint8)] * len(idx)
            frames += fr
        segs = [(max(s.start, p["s0"]) - p["s0"] + T, min(s.end, p["s1"]) - p["s0"] + T, s.step) for s in c.segments
                if s.end > p["s0"] and s.start < p["s1"]] if p["task_id"] != OTHER else []
        gt.append((T, T + p["s1"] - p["s0"], p["task_id"], segs))
        T += p["s1"] - p["s0"]
    cat = [np.concatenate([x[i] for x in fs]) for i in range(5)]
    return ClipFeatures(spec["id"], *cat), frames, gt


def run_splice(spec: dict, stack: dict, run_name: str, ecfg, verifier=None, escalation=None, calibrators=None,
               localizer=None, clips=None, frames=None, oracle_first: bool = False, task_checker=None) -> Path:
    """oracle_first: the first part's task is given (no recognizer; used by the free away-state sweep)."""
    clips = clips or _clips()
    feats, fr, gt = build(spec, clips, decode=frames is None)
    frames = fr if frames is None else frames
    scores = stack["detector"].score(feats)
    out = RUNS / run_name / f"{spec['id']}.jsonl"
    meta = {"splice": spec, "label": "SYNTHETIC multi-task sequence (spliced CaptainCook4D recordings)", "run": run_name,
            "engine": {k: (v if isinstance(v, (int, float, str, bool, type(None))) else str(v)) for k, v in vars(ecfg).items()},
            "verifier": getattr(verifier, "model", None), "escalation": getattr(escalation, "model", None),
            "task_checker": getattr(task_checker, "model", None)}
    with RunLog(out, meta) as log:
        rec = None if oracle_first else stack["recognizer"]
        if rec is not None:
            rec.reset()
        eng = Engine(ecfg, stack["library"], stack["evidence"], rec, stack["detector"], verifier, escalation,
                     log=log, calibrators=calibrators, localizer=localizer, offtask=stack.get("offtask"),
                     task_id=spec["parts"][0]["task_id"] if oracle_first else None, task_checker=task_checker)
        info = replay(eng, feats, scores, frames)
        log.write("summary", float(feats.t[-1]) if len(feats.t) else 0.0, **info)
    return out


# ------------------------------------------------------------------------------------------- scoring
def score_splice(spec: dict, log_path: Path, settle_s: float = 60.0) -> dict:
    """Reads only the spec (ground truth) and the run log."""
    recs = read_log(log_path)
    clips = _clips()
    _, _, gt = build(spec, clips, decode=False)
    end = gt[-1][1]
    times = np.arange(0.5, end, 0.5)
    task_gt = np.empty(len(times), dtype=object)
    step_gt = np.empty(len(times), dtype=object)
    inside = np.zeros(len(times), bool)
    for t0, t1, task, segs in gt:
        m = (times >= t0) & (times < t1)
        task_gt[m] = task
        if segs:
            step_gt[m] = M.frame_labels(segs, times[m], between="next")
            inside[m] = np.array([any(a <= t < b for a, b, _ in segs) for t in times[m]])
    pred = M.predicted_labels(recs, times)
    cur = current_task(recs, times)
    ch = task_changes(recs)
    res = {"id": spec["id"], "kind": spec["kind"], "minutes": end / 60.0,
           "step_acc": float(((step_gt == pred) & inside).sum() / max(1, inside.sum())),
           "correct_task_share": float(np.mean([c == g for c, g in zip(cur, task_gt) if g != OTHER])),
           "first_task_correct": bool(ch and ch[0][1] == gt[0][2])}
    # switches: every change of current task after the first start, judged against what was playing then
    def playing(t):
        for t0, t1, task, _ in gt:
            if t0 <= t < t1:
                return task
        return gt[-1][2]
    later = ch[1:] if ch else []
    res["switches"] = len(later)
    res["wrong_switches"] = sum(1 for t, task in later if task is not None and task != playing(t))
    # latency at each boundary into a library task that differs from the previous part's task
    lat, missed = [], 0
    for (p0, p1, prev, _), (t0, t1, task, _) in zip(gt, gt[1:]):
        if task == OTHER or task == prev or cur[min(len(times) - 1, np.searchsorted(times, t0))] == task:
            continue                    # nothing to detect: never left that task
        hit = [t for t, k in ch if t0 <= t < t1 and k == task]
        if hit:
            lat.append(hit[0] - t0)
        else:
            missed += 1
    res["switch_latency_s"], res["missed_switches"] = lat, missed
    # resume (resume / interrupt kinds): A comes back at the return boundary; at which step?
    if spec["kind"] in ("resume", "interrupt"):
        a = spec["parts"][0]["task_id"]
        t_ret = gt[2][0]
        left = any(t < t_ret and k != a for t, k in ch[1:]) if ch else False
        back = [t for t, k in ch if t >= t_ret and k == a]
        res["left_a"] = left
        res["a_current_after_return"] = bool(cur[np.searchsorted(times, min(end - 0.5, t_ret + settle_s))] == a)
        # step right after return: the engine's step for A when A is current again (or at the return if A never left)
        t_chk = back[0] if (left and back) else (t_ret if not left else None)
        res["resumed"] = bool(left and back)
        res["resume_latency_s"] = (back[0] - t_ret) if (left and back) else None
        if t_chk is not None:
            bel = [r for r in by_kind(recs, "belief") if r["t"] >= t_chk and r.get("task_id", a) == a]
            g = clips[spec["parts"][0]["clip"]]
            ret_label = M.frame_labels([(s.start, s.end, s.step) for s in g.segments], np.array([spec["parts"][2]["s0"]]),
                                       between="next")[0]
            if bel:
                order = [s for s in _graph_order(a)]
                got = bel[0]["map"]
                res["resume_step_exact"] = got == ret_label
                res["resume_step_within1"] = (got in order and ret_label in order and
                                              abs(order.index(got) - order.index(ret_label)) <= 1)
                res["resume_step"], res["return_step_gt"] = got, ret_label
                # the person kept working while the switch back was being detected: also score against the step they
                # were on when A became current again (review point: restoring state vs tracking a moving person)
                now_label = M.frame_labels([(s.start, s.end, s.step) for s in g.segments],
                                           np.array([spec["parts"][2]["s0"] + (t_chk - t_ret)]), between="next")[0]
                res["resume_step_exact_at_resume"] = got == now_label
                res["resume_step_within1_at_resume"] = (got in order and now_label in order and
                                                        abs(order.index(got) - order.index(now_label)) <= 1)
        res["leave_warnings"] = sum(1 for x in by_kind(recs, "action") if x["action"] == "leave_warning")
        res["interruption_pauses"] = sum(1 for x in by_kind(recs, "task_state") if x.get("reason") == "interruption")
    rc = [r for r in by_kind(recs, "task_check") if not r.get("error")]
    res["task_checks"] = len(rc)
    ver = by_kind(recs, "verdict")
    sc = by_kind(recs, "step_choice") + rc
    res["verifier_calls"] = len(ver) + len(sc)
    res["cost_usd"] = float(sum(v.get("orig_cost_usd", v.get("cost_usd", 0.0)) or 0.0 for v in ver)
                            + sum(x.get("cost_usd", 0.0) or 0.0 for x in sc))
    return res


def _graph_order(task_id: str) -> list[str]:
    from ..tasks.compiler import load_library
    return [n.id for n in load_library()[task_id].nodes]


def aggregate(rows: list[dict]) -> dict:
    def mean(k, rs=rows):
        v = [r[k] for r in rs if r.get(k) is not None]
        return float(np.mean(v)) if v else None
    lat = [x for r in rows for x in r["switch_latency_s"]]
    rs = [r for r in rows if r["kind"] in ("resume", "interrupt")]
    res_rows = [r for r in rows if r["kind"] == "resume"]
    out = {"n": len(rows), "minutes": float(sum(r["minutes"] for r in rows)), "step_acc": mean("step_acc"),
           "correct_task_share": mean("correct_task_share"),
           "switch_latency_s": {"n": len(lat), "p50": float(np.median(lat)) if lat else None,
                                "p90": float(np.percentile(lat, 90)) if lat else None},
           "switches_detected": len(lat), "missed_switches": sum(r["missed_switches"] for r in rows),
           "wrong_switches": sum(r["wrong_switches"] for r in rows),
           "wrong_switches_per_hour": sum(r["wrong_switches"] for r in rows) / max(1e-6, sum(r["minutes"] for r in rows) / 60),
           "task_checks": sum(r["task_checks"] for r in rows), "verifier_calls": sum(r["verifier_calls"] for r in rows),
           "cost_usd": float(sum(r["cost_usd"] for r in rows))}
    if res_rows:
        out["resume"] = {"n": len(res_rows), "left_a": sum(r["left_a"] for r in res_rows),
                         "resumed": sum(r["resumed"] for r in res_rows),
                         "a_current_60s_after_return": sum(r["a_current_after_return"] for r in res_rows),
                         "step_exact": sum(bool(r.get("resume_step_exact")) for r in res_rows),
                         "step_within1": sum(bool(r.get("resume_step_within1")) for r in res_rows),
                         "step_exact_at_resume": sum(bool(r.get("resume_step_exact_at_resume")) for r in res_rows),
                         "step_within1_at_resume": sum(bool(r.get("resume_step_within1_at_resume")) for r in res_rows),
                         "resume_latency_s_p50": float(np.median([r["resume_latency_s"] for r in res_rows if r["resume_latency_s"] is not None]))
                         if any(r["resume_latency_s"] is not None for r in res_rows) else None}
    it = [r for r in rows if r["kind"] == "interrupt"]
    if it:
        out["interrupt"] = {"n": len(it), "switched_to_a_library_task": sum(r["wrong_switches"] > 0 for r in it),
                            "a_current_60s_after_return": sum(r["a_current_after_return"] for r in it),
                            "step_exact": sum(bool(r.get("resume_step_exact")) for r in it),
                            "step_within1": sum(bool(r.get("resume_step_within1")) for r in it),
                            "interruption_pauses": sum(r["interruption_pauses"] for r in it),
                            "leave_warnings": sum(r["leave_warnings"] for r in it)}
    return out


# ------------------------------------------------------------------------------------------- free away-state sweep
def _away_trace(recs: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    b = by_kind(recs, "belief")
    return np.array([r["t"] for r in b]), np.array([r.get("p_away", 0.0) for r in b])


def trigger_stats(traces: list[tuple[np.ndarray, np.ndarray, np.ndarray]], window_s: float, thr: float,
                  gap_s: float = 20.0, horizon_s: float = 60.0) -> dict:
    """Offline poor-fit trigger: mean P(away) over window_s >= thr, at most one per gap_s. traces: (t, p_away, off)
    with off = 1 when the person is not doing the given task. Detection: a trigger within horizon_s of an off-task
    stretch starting. False trigger: one fired while on-task."""
    det, n_starts, false, on_s, lat = 0, 0, 0, 0.0, []
    for t, p, off in traces:
        fired, last = [], -1e9
        for i in range(len(t)):
            m = (t > t[i] - window_s) & (t <= t[i])
            if m.sum() >= 0.8 * window_s and p[m].mean() >= thr and t[i] - last >= gap_s:
                fired.append(t[i])
                last = t[i]
        on_s += float((off == 0).sum())
        starts = [t[i] for i in range(1, len(t)) if off[i] and not off[i - 1]]
        n_starts += len(starts)
        for s0 in starts:
            hit = [f for f in fired if s0 <= f <= s0 + horizon_s]
            if hit:
                det += 1
                lat.append(hit[0] - s0)
        idx = {float(x): k for k, x in enumerate(t)}
        false += sum(1 for f in fired if off[idx[float(f)]] == 0)
    return {"window_s": window_s, "thr": thr, "detected": det, "starts": n_starts, "false_triggers": false,
            "false_per_hour": false / max(1e-6, on_s / 3600.0), "latency_p50": float(np.median(lat)) if lat else None}


def trigger_stats_backoff(traces, window_s: float, thr: float, gap_s: float = 20.0, horizon_s: float = 60.0,
                          backoff=(30.0, 60.0, 120.0)) -> dict:
    """Like trigger_stats, but with the engine's re-check schedule: a check fired while on-task is answered 'keep'
    (best case), so the next one waits 30, 60, then 120 s. Counts the typed checks that schedule would make on-task
    (false_per_hour) and the off-task stretches it catches within horizon_s. Landmark-lead re-checks (which skip the
    back-off) are not modeled."""
    det, n_starts, false, on_s, lat = 0, 0, 0, 0.0, []
    for t, p, off in traces:
        nxt, i, fired_off = -1e9, 0, []
        for k in range(len(t)):
            m = (t > t[k] - window_s) & (t <= t[k])
            if m.sum() < 0.8 * window_s or p[m].mean() < thr or t[k] < nxt:
                continue
            if off[k]:
                fired_off.append(t[k])
                nxt = t[k] + gap_s
            else:
                false += 1
                nxt = t[k] + backoff[min(i, len(backoff) - 1)]
                i += 1
        on_s += float((off == 0).sum())
        starts = [t[k] for k in range(1, len(t)) if off[k] and not off[k - 1]]
        n_starts += len(starts)
        for s0 in starts:
            hit = [f for f in fired_off if s0 <= f <= s0 + horizon_s]
            if hit:
                det += 1
                lat.append(hit[0] - s0)
    return {"window_s": window_s, "thr": thr, "detected": det, "starts": n_starts, "false_triggers": false,
            "false_per_hour": false / max(1e-6, on_s / 3600.0), "latency_p50": float(np.median(lat)) if lat else None,
            "schedule": "engine back-off after keep"}


def choose_trigger_with_backoff(sweep: str = "free_away_sweep_decoupled", max_per_hour: float = 6.0) -> dict:
    """Re-score the poor-fit trigger of a free sweep's chosen away config from its saved run logs, with the engine's
    back-off, then apply the same rule: most off-task stretches caught within 60 s, at most max_per_hour on-task checks."""
    from dataclasses import replace as _r
    from . import harness
    res = json.loads((RESULTS / "multitask" / f"{sweep}.json").read_text())
    ch = res["chosen_away"]
    key = [c["key"] for c in res["configs"] if all(c[k] == ch[k] for k in ("window", "away_enter", "away_return",
                                                                           "away_weight"))][0]
    lib = harness.load_stack()["library"]
    traces = []
    for c, f in train_recordings(lib):
        tt, pa = _away_trace(read_log(RUNS / f"mt_free/{key}" / f"{c.clip_id}.jsonl"))
        traces.append((tt, pa, np.zeros(len(tt))))
    clips = _clips()
    for sp in make_splices("train", seed=0, n_seq=6, n_resume=8, n_interrupt=4, lib=lib):
        tt, pa = _away_trace(read_log(RUNS / f"mt_free/{key}" / f"{sp['id']}.jsonl"))
        gt = build(sp, clips, decode=False)[2]
        a = sp["parts"][0]["task_id"]
        traces.append((tt, pa, np.array([0 if any(t0 <= x < t1 and task == a for t0, t1, task, _ in gt) else 1 for x in tt])))
    rows = [trigger_stats_backoff(traces, W, th) for W in (10.0, 20.0, 30.0) for th in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7)]
    ok = [x for x in rows if x["false_per_hour"] <= max_per_hour]
    best = max(ok, key=lambda x: (x["detected"], -(x["latency_p50"] or 1e9))) if ok else None
    res["triggers_with_backoff"], res["chosen_trigger"] = rows, best
    res["trigger_note"] = ("first counted with a trigger every 20 s while P(away) stayed high; the engine backs off "
                           "after a check confirms the task, so the rule is applied to the back-off schedule")
    (RESULTS / "multitask" / f"{sweep}.json").write_text(json.dumps(res, indent=1, default=float))
    return {"away": ch, "key": key, "trigger": best, "rows": rows}


def free_away_sweep(grid: dict | None = None, max_s: float = 300.0, workers: int = 4, mode: str = "joint",
                    out_name: str = "free_away_sweep", extra: dict | None = None) -> dict:
    """TRAIN split, no model calls. The task is given (first part's task for splices), local layers only, so P(away)
    depends only on landmarks and the tracker's away parameters. Picks, with rules fixed before looking:
      1. away parameters: highest AUC of P(away) for off-task vs on-task seconds over train splices + single-task train
         recordings, among configs whose task-given step accuracy on the single-task recordings is no more than 0.5
         points below the same engine without away states;
      2. the poor-fit trigger (window, threshold): most off-task stretches detected within 60 s, with at most 6 false
         triggers per on-task hour (one extra typed check per 10 minutes)."""
    import itertools
    from concurrent.futures import ThreadPoolExecutor
    from sklearn.metrics import roc_auc_score
    from ..landmarks import OffTaskModel
    from ..state_tracker import TrackerConfig
    from . import harness
    from .run_all import engine_config
    grid = grid or {"window": [30, 60], "away_enter": [0.005, 0.02], "away_return": [0.2, 0.5],
                    "away_weight": [0.1], "away_step_evidence": [False, True]}
    base = harness.load_stack()
    lib = base["library"]
    recs_tr = train_recordings(lib)
    splices = make_splices("train", seed=0, n_seq=6, n_resume=8, n_interrupt=4, lib=lib)
    clips = _clips()
    stacks = {f: fold_stack(base, f) for f in range(3)}
    gts = {sp["id"]: build(sp, clips, decode=False)[2] for sp in splices}

    def job(cfgkey, ecfg, stack, item):
        kind, x, f = item
        st = dict(stacks[f])
        st["offtask"] = stack["offtask"]
        if kind == "clip":
            c = replace(x, end=min(x.end, max_s))
            p = harness.run_clip(c, st, f"mt_free/{cfgkey}", ecfg, oracle_task=True, frames=[])
            r = harness.score_clip(c, p)
            t, pa = _away_trace(read_log(p))
            return {"kind": kind, "id": c.clip_id, "step_acc": r["step_acc"], "trace": (t, pa, np.zeros(len(t)))}
        p = run_splice(x, st, f"mt_free/{cfgkey}", ecfg, clips=clips, frames=[], oracle_first=True)
        t, pa = _away_trace(read_log(p))
        a = x["parts"][0]["task_id"]
        off = np.array([0 if any(t0 <= tt < t1 and task == a for t0, t1, task, _ in gts[x["id"]]) else 1 for tt in t])
        return {"kind": kind, "id": x["id"], "trace": (t, pa, off)}

    items = [("clip", c, f) for c, f in recs_tr] + [("splice", sp, sp["fold"]) for sp in splices]
    res = {"protocol": "train split, task given, local layers only, no model calls; 3 folds by recording "
                       "(recognizer + probes refit without the fold); first %ds of each recording" % int(max_s),
           "n_single": len(recs_tr), "n_splices": len(splices), "configs": []}
    # reference: no away states
    ref_cfg = engine_config({"use_verifier": False})
    with ThreadPoolExecutor(workers) as ex:
        ref = list(ex.map(lambda it: job("no_away", ref_cfg, base, it), [i for i in items if i[0] == "clip"]))
    ref_acc = float(np.mean([r["step_acc"] for r in ref]))
    res["no_away_step_acc"] = ref_acc
    for w, e, r_, aw, se in itertools.product(grid["window"], grid["away_enter"], grid["away_return"],
                                              grid["away_weight"], grid["away_step_evidence"]):
        key = f"{ {'factored': 'f_', 'decoupled': 'd_'}.get(mode, '') }w{w}_e{e}_r{r_}_aw{aw}_se{int(se)}"
        st = dict(base)
        st["offtask"] = OffTaskModel.load(CKPT / f"offtask_landmarks_w{w}.json")
        ecfg = engine_config({"use_verifier": False, **(extra or {})})
        ecfg.tracker.away_enter, ecfg.tracker.away_return, ecfg.tracker.away_weight = e, r_, aw
        ecfg.tracker.away_step_evidence = se
        ecfg.tracker.away_mode = mode
        with ThreadPoolExecutor(workers) as ex:
            rows = list(ex.map(lambda it: job(key, ecfg, st, it), items))
        acc = float(np.mean([x["step_acc"] for x in rows if x["kind"] == "clip"]))
        pa = np.concatenate([x["trace"][1] for x in rows])
        off = np.concatenate([x["trace"][2] for x in rows])
        auc = float(roc_auc_score(off, pa)) if off.any() and (off == 0).any() else None
        trig = [trigger_stats([x["trace"] for x in rows], W, th) for W in (10.0, 20.0, 30.0)
                for th in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7)]
        row = {"key": key, "away_mode": mode, "window": w, "away_enter": e, "away_return": r_, "away_weight": aw,
               "away_step_evidence": se,
               "step_acc": acc,
               "auc_p_away": auc, "triggers": trig}
        res["configs"].append(row)
        row["p_away_on"], row["p_away_off"] = float(pa[off == 0].mean()), float(pa[off == 1].mean()) if off.any() else None
        print(key, f"step_acc {acc:.3f} (no away {ref_acc:.3f})  AUC {auc:.3f}  P(away) on {row['p_away_on']:.3f} "
                   f"off {row['p_away_off']:.3f}", flush=True)
    ok = [c for c in res["configs"] if c["step_acc"] >= ref_acc - 0.005 and c["auc_p_away"] is not None]
    best = max(ok, key=lambda c: c["auc_p_away"]) if ok else None
    res["chosen_away"] = best and {k: best[k] for k in ("away_mode", "window", "away_enter", "away_return", "away_weight",
                                                         "away_step_evidence", "step_acc", "auc_p_away")}
    if best:
        okt = [x for x in best["triggers"] if x["false_per_hour"] <= 6.0]
        tb = max(okt, key=lambda x: (x["detected"], -(x["latency_p50"] or 1e9))) if okt else None
        res["chosen_trigger"] = tb
    (RESULTS / "multitask").mkdir(parents=True, exist_ok=True)
    (RESULTS / "multitask" / f"{out_name}.json").write_text(json.dumps(res, indent=1, default=float))
    return res


# ------------------------------------------------------------------------------------------- paid runs
def run_set(split: str, name: str, overrides: dict, budget_usd: float, escalate: bool = True, workers: int = 3,
            singles: bool = True, splices: bool = True, only: list[str] | None = None, tag: str = "",
            version: str = "v1", strong: str = "claude_strong", task_checker: str | None = None,
            budget_openai_usd: float = 0.0) -> dict:
    """Run the automatic multi-task engine over a split's splices (and, on train, the single-task recordings too),
    with model calls capped by a hard Budget. train: 3-fold stacks; eval: the normal stack. Writes
    results/multitask/<name><tag>.json. `overrides` are engine overrides (offtask_window picks the landmark model).
    strong: the strong tier (escalations); task_checker: who answers "which task?" (default: the fast tier). OpenAI
    models draw on their own cap (budget_openai_usd); spend_usd records the other calls only (OpenAI calls are tracked
    from their response cache)."""
    from concurrent.futures import ThreadPoolExecutor
    from ..experiments import _budget, make_verifier
    from . import harness
    from .run_all import calibrators, engine_config
    over = dict(overrides)
    win = over.pop("offtask_window", None)
    base = harness.load_stack(offtask_window=win)
    ecfg = engine_config({**over, "escalate": escalate})
    budget = _budget(max_calls=20000, max_usd=budget_usd)
    obudget = _budget(max_calls=20000, max_usd=budget_openai_usd)
    pick = lambda kind: obudget if kind.startswith("openai:") else budget      # noqa: E731
    ver = make_verifier("jev", budget)
    esc = make_verifier(strong, pick(strong), role="strong") if escalate else None
    tc = make_verifier(task_checker, pick(task_checker)) if task_checker else None
    cals = {"primary": calibrators("jev"), "escalation": calibrators(strong if escalate else None)}
    clips = _clips()
    stacks = {f: fold_stack(base, f, version) for f in range(3)} if split == "train" else {0: base}
    for st in stacks.values():
        st["offtask"] = base["offtask"]
    items = []
    if splices:
        items += [("splice", sp, sp["fold"] if split == "train" else 0)
                  for sp in make_splices(split, lib=base["library"], version=version)]
    if singles and split == "train":
        items += [("clip", replace(c, end=min(c.end, 300.0)), f) for c, f in train_recordings(base["library"], version)]
    if only:
        items = [it for it in items if (it[1]["id"] if it[0] == "splice" else it[1].clip_id) in only]
    run = f"mt_{name}{tag}"

    def one(it):
        kind, x, f = it
        st = dict(stacks[f])
        st["recognizer"] = copy.deepcopy(stacks[f]["recognizer"])
        if kind == "splice":
            return kind, score_splice(x, run_splice(x, st, run, ecfg, ver, esc, cals, clips=clips, task_checker=tc))
        return kind, harness.score_clip(x, harness.run_clip(x, st, run, ecfg, ver, esc, calibrators=cals,
                                                            task_checker=tc))
    with ThreadPoolExecutor(workers) as ex:
        out = list(ex.map(one, items))
    sp_rows = [r for k, r in out if k == "splice"]
    cl_rows = [r for k, r in out if k == "clip"]
    res = {"label": "SYNTHETIC multi-task sequences (spliced CaptainCook4D recordings)" if sp_rows else None,
           "split": split, "name": name, "overrides": overrides, "escalate": escalate,
           "splices": {"aggregate": aggregate(sp_rows), "rows": sp_rows} if sp_rows else None,
           "single_task": {"aggregate": harness.aggregate(cl_rows), "rows": cl_rows,
                           "wrong_switches": sum(r["wrong_switches"] for r in cl_rows),
                           "task_final_correct": float(np.mean([r["task_final_correct"] for r in cl_rows]))} if cl_rows else None,
           "strong": strong if escalate else None, "task_checker": task_checker or "jev",
           "spend_usd": budget.usd, "calls": budget.calls, "spend_usd_openai": obudget.usd, "calls_openai": obudget.calls}
    (RESULTS / "multitask").mkdir(parents=True, exist_ok=True)
    (RESULTS / "multitask" / f"{name}{tag}.json").write_text(json.dumps(res, indent=1, default=float))
    return res


def switch_sweep(away: dict, triggers: list[dict], variants: dict | None = None, budget_usd: float = 3.0,
                 workers: int = 3) -> dict:
    """TRAIN split, paid (Jev only: escalation off keeps this ~10x cheaper; the switch logic uses only Jev's typed
    checks). Every config runs the 24 single-task train recordings (first 300 s) and the 22 SYNTHETIC train splices,
    3-fold stacks. Stage A: default switch settings with each trigger candidate. Stage B: switch variants on the stage-A
    winner. A reference run uses the single-task engine (no multi-task) on the same items.
    Choice rule, fixed before running: among configs with no wrong switch on the single-task recordings and
    single-task step accuracy no more than 0.5 points below the reference, the highest minute-weighted step accuracy
    over single-task recordings + splices; ties -> fewer model calls. Writes results/multitask/train_switch_sweep.json
    and results/multitask/chosen.json. The budget is shared by all runs and is a hard cap."""
    base = {"multi_task": True, "offtask_window": away["window"], "tracker.away_mode": away.get("away_mode", "decoupled"),
            "tracker.away_enter": away["away_enter"], "tracker.away_return": away["away_return"],
            "tracker.away_weight": away["away_weight"]}
    variants = variants if variants is not None else {
        "no_lm_agree": {"switch_lm_agree": False},
        "strict_p0.8": {"switch_p": 0.8},
        "two_confirmations": {"switch_confirmations": 2},
        "resume_bias_x3": {"resume_bias": float(np.log(3))},
        "earlier_commit": {"recognize_thr": 0.8, "recognize_hold_s": 1.0},
    }
    left = [budget_usd]
    res = {"protocol": "train split, 3 folds by recording, automatic, Jev fast tier only (no Opus escalation), "
                       "24 single-task recordings (first 300 s) + 22 SYNTHETIC train splices", "base": base, "configs": {}}

    def one(key, over):
        if left[0] <= 0.01:
            res["configs"][key] = {"skipped": "budget"}
            return None
        r = run_set("train", f"train_sweep_{key}", over, budget_usd=left[0], escalate=False, workers=workers)
        left[0] -= r["spend_usd"]
        st, sp = r["single_task"], r["splices"]["aggregate"]
        m_st = st["aggregate"]["minutes"]
        acc = (st["aggregate"]["step_acc"] * m_st + sp["step_acc"] * sp["minutes"]) / (m_st + sp["minutes"])
        row = {"overrides": over, "step_acc_weighted": acc, "single_step_acc": st["aggregate"]["step_acc"],
               "single_wrong_switches": st["wrong_switches"], "single_task_top1": st["aggregate"]["task_top1"],
               "single_task_final_correct": st["task_final_correct"], "splices": sp, "calls": r["calls"],
               "spend_usd": r["spend_usd"]}
        res["configs"][key] = row
        print(key, json.dumps({k: v for k, v in row.items() if k not in ("splices", "overrides")}, default=float),
              f"spent so far {budget_usd - left[0]:.3f}", flush=True)
        return row

    ref = one("reference_single_task", {"multi_task": False})
    ref_acc = ref["single_step_acc"] if ref else None

    def ok(k):
        v = res["configs"].get(k, {})
        return "skipped" not in v and k != "reference_single_task" and v.get("single_wrong_switches") == 0 and \
            (ref_acc is None or v["single_step_acc"] >= ref_acc - 0.005)

    def best(keys):
        keys = [k for k in keys if ok(k)]
        return max(keys, key=lambda k: (round(res["configs"][k]["step_acc_weighted"], 4), -res["configs"][k]["calls"])) \
            if keys else None
    a_keys = []
    for tr in triggers:
        k = f"default_W{int(tr['window_s'])}_thr{tr['thr']}"
        one(k, {**base, "fit_window_s": tr["window_s"], "fit_thr": tr["thr"]})
        a_keys.append(k)
    win = best(a_keys)
    if win is None:     # amendment (written before stage A finished): explore the variants on the least-bad trigger
        done = [k for k in a_keys if "skipped" not in res["configs"].get(k, {"skipped": 1})]
        win = min(done, key=lambda k: (res["configs"][k]["single_wrong_switches"],
                                       -res["configs"][k]["step_acc_weighted"])) if done else None
        res["stage_a_note"] = "no stage-A config qualified; stage B ran on the one with fewer single-task wrong switches"
    res["stage_a_choice"] = win
    if win:
        trig = {k: res["configs"][win]["overrides"][k] for k in ("fit_window_s", "fit_thr")}
        for name, over in variants.items():
            one(f"{name}_W{int(trig['fit_window_s'])}_thr{trig['fit_thr']}", {**base, **trig, **over})
    final = best(list(res["configs"]))
    res["chosen"], res["reference_single_step_acc"] = final, ref_acc
    if final:
        (RESULTS / "multitask" / "chosen.json").write_text(json.dumps(
            {"overrides": res["configs"][final]["overrides"], "config": final,
             "chosen_from": "results/multitask/train_switch_sweep.json",
             "away_from": "results/multitask/free_away_sweep_decoupled.json"}, indent=2))
    res["spend_usd"] = budget_usd - left[0]
    (RESULTS / "multitask" / "train_switch_sweep.json").write_text(json.dumps(res, indent=1, default=float))
    return res


def switch_sweep_continue(budget_usd: float, workers: int = 4) -> dict:
    """Finish a switch sweep whose stage B did not run (results/multitask/train_switch_sweep.json): stage B on the
    stage-A config chosen by the amended rule, then the unchanged final choice rule, within budget_usd."""
    path = RESULTS / "multitask" / "train_switch_sweep.json"
    res = json.loads(path.read_text())
    base, cfgs = res["base"], res["configs"]
    ref_acc = cfgs["reference_single_task"]["single_step_acc"]
    a_keys = [k for k in cfgs if k.startswith("default_")]
    win = min(a_keys, key=lambda k: (cfgs[k]["single_wrong_switches"], -cfgs[k]["step_acc_weighted"]))
    res["stage_a_choice"] = win
    res["stage_a_note"] = ("no stage-A config qualified; stage B ran on the one with fewer single-task wrong switches "
                           "(rule amended before the second stage-A result was seen)")
    trig = {k: cfgs[win]["overrides"][k] for k in ("fit_window_s", "fit_thr")}
    variants = {"no_lm_agree": {"switch_lm_agree": False}, "strict_p0.8": {"switch_p": 0.8},
                "two_confirmations": {"switch_confirmations": 2}, "resume_bias_x3": {"resume_bias": float(np.log(3))},
                "earlier_commit": {"recognize_thr": 0.8, "recognize_hold_s": 1.0}}
    left = budget_usd
    for name, over in variants.items():
        key = f"{name}_W{int(trig['fit_window_s'])}_thr{trig['fit_thr']}"
        if key in cfgs:
            continue
        if left <= 0.01:
            cfgs[key] = {"skipped": "budget"}
            continue
        o = {**base, **trig, **over}
        r = run_set("train", f"train_sweep_{key}", o, budget_usd=left, escalate=False, workers=workers)
        left -= r["spend_usd"]
        st, sp = r["single_task"], r["splices"]["aggregate"]
        m_st = st["aggregate"]["minutes"]
        cfgs[key] = {"overrides": o, "step_acc_weighted": (st["aggregate"]["step_acc"] * m_st + sp["step_acc"] * sp["minutes"])
                     / (m_st + sp["minutes"]), "single_step_acc": st["aggregate"]["step_acc"],
                     "single_wrong_switches": st["wrong_switches"], "single_task_top1": st["aggregate"]["task_top1"],
                     "single_task_final_correct": st["task_final_correct"], "splices": sp, "calls": r["calls"],
                     "spend_usd": r["spend_usd"], "budget_cut": r["spend_usd"] >= left + r["spend_usd"] - 0.01}
        print(key, json.dumps({k: v for k, v in cfgs[key].items() if k not in ("splices", "overrides")}, default=float),
              flush=True)
    ok = [k for k, v in cfgs.items() if "skipped" not in v and k != "reference_single_task" and not v.get("budget_cut")
          and v["single_wrong_switches"] == 0 and v["single_step_acc"] >= ref_acc - 0.005]
    final = max(ok, key=lambda k: (round(cfgs[k]["step_acc_weighted"], 4), -cfgs[k]["calls"])) if ok else None
    res["chosen"], res["reference_single_step_acc"] = final, ref_acc
    res["spend_usd"] = res.get("spend_usd", 0.0) + (budget_usd - left)
    if final:
        (RESULTS / "multitask" / "chosen.json").write_text(json.dumps(
            {"overrides": cfgs[final]["overrides"], "config": final, "chosen_from": "results/multitask/train_switch_sweep.json",
             "away_from": "results/multitask/free_away_sweep_decoupled.json"}, indent=2))
    path.write_text(json.dumps(res, indent=1, default=float))
    return res


def switch_sweep_add(name: str, extra: dict, budget_usd: float, on: str | None = None, workers: int = 4) -> dict:
    """One more train config on top of config `on` (default: the current choice, else the stage-A choice), then the
    same final choice rule over every config. Used for options added after the sweep started (e.g. rewind_on_leave)."""
    path = RESULTS / "multitask" / "train_switch_sweep.json"
    res = json.loads(path.read_text())
    cfgs = res["configs"]
    on = on or res.get("chosen") or res["stage_a_choice"]
    o = {**cfgs[on]["overrides"], **extra}
    r = run_set("train", f"train_sweep_{name}", o, budget_usd=budget_usd, escalate=False, workers=workers)
    st, sp = r["single_task"], r["splices"]["aggregate"]
    m_st = st["aggregate"]["minutes"]
    cfgs[name] = {"overrides": o, "on": on, "step_acc_weighted": (st["aggregate"]["step_acc"] * m_st + sp["step_acc"] * sp["minutes"])
                  / (m_st + sp["minutes"]), "single_step_acc": st["aggregate"]["step_acc"],
                  "single_wrong_switches": st["wrong_switches"], "single_task_top1": st["aggregate"]["task_top1"],
                  "single_task_final_correct": st["task_final_correct"], "splices": sp, "calls": r["calls"],
                  "spend_usd": r["spend_usd"], "budget_cut": r["spend_usd"] >= budget_usd - 0.01}
    print(name, json.dumps({k: v for k, v in cfgs[name].items() if k not in ("splices", "overrides")}, default=float),
          flush=True)
    ref_acc = cfgs["reference_single_task"]["single_step_acc"]
    ok = [k for k, v in cfgs.items() if "skipped" not in v and k != "reference_single_task" and not v.get("budget_cut")
          and v["single_wrong_switches"] == 0 and v["single_step_acc"] >= ref_acc - 0.005]
    final = max(ok, key=lambda k: (round(cfgs[k]["step_acc_weighted"], 4), -cfgs[k]["calls"])) if ok else None
    res["chosen"] = final
    res["spend_usd"] = res.get("spend_usd", 0.0) + r["spend_usd"]
    if final:
        (RESULTS / "multitask" / "chosen.json").write_text(json.dumps(
            {"overrides": cfgs[final]["overrides"], "config": final, "chosen_from": "results/multitask/train_switch_sweep.json",
             "away_from": "results/multitask/free_away_sweep_decoupled.json"}, indent=2))
    path.write_text(json.dumps(res, indent=1, default=float))
    return res


SMOKE_ITEMS = ["7_1_full", "17_10_full", "train_resume_00"]
# away settings chosen by the free train sweep (results/multitask/free_away_sweep_decoupled.json); trigger provisional
PROVISIONAL = {"multi_task": True, "offtask_window": 20, "tracker.away_mode": "decoupled", "tracker.away_enter": 0.005,
               "tracker.away_return": 0.05, "tracker.away_weight": 0.3, "fit_window_s": 20.0, "fit_thr": 0.4}


def smoke(budget_usd: float = 0.50) -> dict:
    """Pipeline check with real model calls (full config: Jev + Opus escalation) on 2 train recordings and 1 train
    splice, provisional multi-task settings. Not a result: it checks that answers flow through the task set, the logs,
    scoring and cost accounting before the paid sweeps."""
    return run_set("train", "smoke", PROVISIONAL, budget_usd=budget_usd, escalate=True, workers=3, only=SMOKE_ITEMS)


# ------------------------------------------------------------------------------------------- more training video
def learning_curve(max_s: float = 300.0, workers: int = 4) -> dict:
    """Free check: do the small trained models get better with ~3x the training video? On the 24 'v1' train
    recordings, task given, local layers only (no model calls): step probes from the v1 fold models (each trained on
    the other 16 v1 recordings) vs the 'all' fold models (each trained on every train recording outside its fold,
    ~47). No recording is ever scored by a model that saw it."""
    from . import harness
    from .run_all import engine_config
    base = harness.load_stack()
    lib = base["library"]
    v1 = train_recordings(lib, "v1")
    fold_all = {c.clip_id: f for c, f in train_recordings(lib, "all")}
    stacks = {("v1", f): fold_stack(base, f, "v1") for f in range(3)}
    stacks.update({("all", f): fold_stack(base, f, "all") for f in range(3)})
    stacks.update({("all_frame", f): fold_stack(base, f, "all", probe="frame") for f in range(3)})
    ecfg = engine_config({"use_verifier": False})

    def one(item):
        version, c, f = item
        c = replace(c, end=min(c.end, max_s))
        st = dict(stacks[(version, f)])
        p = harness.run_clip(c, st, f"learning_curve_{version}", ecfg, oracle_task=True, frames=[])
        return version, c.clip_id, harness.score_clip(c, p)["step_acc"]
    items = [("v1", c, f) for c, f in v1] + [(v, c, fold_all[c.clip_id]) for v in ("all", "all_frame")
                                             for c, _ in v1 if c.clip_id in fold_all]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(one, items))
    by = {v: {cid: a for vv, cid, a in rows if vv == v} for v in ("v1", "all", "all_frame")}
    both = sorted(set(by["v1"]) & set(by["all"]))
    res = {"protocol": "train split, task given, local layers only, first %ds; same 24 recordings scored by fold "
                       "models trained on 16 (v1) vs ~47 (all) other train recordings" % int(max_s),
           "n": len(both), "step_acc_v1": float(np.mean([by["v1"][c] for c in both])),
           "step_acc_all": float(np.mean([by["all"][c] for c in both])),
           "step_acc_all_frame_only": float(np.mean([by["all_frame"][c] for c in both if c in by["all_frame"]])),
           "better": sum(by["all"][c] > by["v1"][c] + 1e-9 for c in both), "worse": sum(by["all"][c] < by["v1"][c] - 1e-9 for c in both),
           "per_recording": {c: [by["v1"][c], by["all"][c]] for c in both},
           "train_recordings_all": len(fold_all)}
    (RESULTS / "multitask").mkdir(parents=True, exist_ok=True)
    (RESULTS / "multitask" / "learning_curve.json").write_text(json.dumps(res, indent=1, default=float))
    print({k: v for k, v in res.items() if k != "per_recording"}, flush=True)
    return res


# ------------------------------------------------------------------------------------------- combined train test
COMBINED_PROTOCOL = """TRAIN split only (the 24 v1 recordings, first 300 s, automatic; the 22 v1 train splices), 3-fold stacks
(v1), the chosen multi-task configuration (results/multitask/chosen.json) on the current engine (switch-bar cap + streak
override, first instruction at start, instruction follows the belief). Written before any of these runs:
  A0  engine as it is now, Jev for everything, no strong tier
  A1  A0 + step list fix (also offer the local model's top 2 steps and the next open steps when asking "which step?")
  A2  A0 + rewind a left task's tracker to when P(away) rose
  keep the step list fix if mean(single-task step_acc, splice step_acc) rises by >= 0.005 and wrong switches (splices +
    single-task) do not increase; keep rewind if resume step within one (resume + interrupt splices, of 16) rises, mean
    step_acc drops by <= 0.01 and wrong switches do not increase
  B0  A0 + the kept fixes + gpt-6.1-sol answers "which task?" (recognition and re-checks), no strong tier
  B1  B0 + gpt-6.1-sol as the strong tier (escalated step checks, calibrated on the train checks)
Comparisons: A1/A2 vs A0 (engine fixes), B0 vs best A (Sol deciding the task), B1 vs B0 (Sol strong tier)."""


def candidate_recall(run: str, version: str = "v1") -> dict:
    """Share of the fast tier's "which step?" questions on the single-task recordings whose options held the annotated
    step (or the step being moved to, between steps)."""
    from ..tasks.compiler import load_library
    lib = load_library()
    hit = n = 0
    for c, _ in train_recordings(lib, version):
        p = RUNS / run / f"{c.clip_id}.jsonl"
        if not p.exists():
            continue
        for r in by_kind(read_log(p), "step_choice"):
            if r.get("error"):
                continue
            gt = M.frame_labels([(s.start, s.end, s.step) for s in c.segments], np.array([r["t"]]), between="next")[0]
            n += 1
            hit += gt in r.get("options", [])
    return {"n": n, "recall": hit / n if n else None}


def _summ(res: dict, run: str) -> dict:
    sp, st = res["splices"]["aggregate"], res["single_task"]["aggregate"]
    r16 = [x for x in res["splices"]["rows"] if x["kind"] in ("resume", "interrupt")]
    return {"single_step_acc": st["step_acc"], "single_task_top1": st["task_top1"],
            "single_task_final_correct": res["single_task"]["task_final_correct"],
            "single_wrong_switches": res["single_task"]["wrong_switches"], "single_alerts_per_min": st["alerts_per_min"],
            "single_false_alarms_per_min": st["false_alarms_per_min"],
            "splice_step_acc": sp["step_acc"], "splice_correct_task_share": sp["correct_task_share"],
            "splice_wrong_switches": sp["wrong_switches"], "splice_missed_switches": sp["missed_switches"],
            "switch_latency_p50_s": sp["switch_latency_s"]["p50"],
            "resume_within1_of16": sum(bool(x.get("resume_step_within1")) for x in r16),
            "resume_exact_of16": sum(bool(x.get("resume_step_exact")) for x in r16),
            "resumed_of10": sp.get("resume", {}).get("resumed"),
            "interrupt_switched_to_library_of6": sp.get("interrupt", {}).get("switched_to_a_library_task"),
            "candidate_recall_single": candidate_recall(run)["recall"],
            "spend_main_usd": res["spend_usd"], "spend_openai_usd": res.get("spend_usd_openai", 0.0)}


def combined_train_test(workers: int = 4, caps: dict | None = None) -> dict:
    from .run_all import multitask_overrides
    caps = caps or {"A": 0.60, "B_main": 0.60, "B0_openai": 2.50, "B1_openai": 3.50}
    base = multitask_overrides()
    fixes = {"A1": {"step_choice_local": 2, "step_choice_next": True}, "A2": {"rewind_on_leave": True}}
    out = {"protocol": COMBINED_PROTOCOL, "base_overrides": base, "fixes": fixes, "caps": caps, "runs": {}}
    save = lambda: (RESULTS / "multitask" / "combined_train.json").write_text(json.dumps(out, indent=1, default=float))  # noqa: E731
    for k, extra in [("A0", {}), *fixes.items()]:
        res = run_set("train", f"combined_{k}", {**base, **extra}, caps["A"], escalate=False, workers=workers)
        out["runs"][k] = _summ(res, f"mt_combined_{k}")
        save()
        print(k, out["runs"][k], flush=True)
    a0, a1, a2 = (out["runs"][k] for k in ("A0", "A1", "A2"))
    m = lambda r: (r["single_step_acc"] + r["splice_step_acc"]) / 2                   # noqa: E731
    ws = lambda r: r["single_wrong_switches"] + r["splice_wrong_switches"]           # noqa: E731
    keep = {"step_list": m(a1) - m(a0) >= 0.005 and ws(a1) <= ws(a0),
            "rewind": a2["resume_within1_of16"] > a0["resume_within1_of16"] and m(a2) >= m(a0) - 0.01 and ws(a2) <= ws(a0)}
    out["kept"] = keep
    best = {**base, **(fixes["A1"] if keep["step_list"] else {}), **(fixes["A2"] if keep["rewind"] else {})}
    out["best_overrides"] = best
    save()
    sol = "openai:gpt-6.1-sol"
    res = run_set("train", "combined_B0", best, caps["B_main"], escalate=False, workers=workers, task_checker=sol,
                  budget_openai_usd=caps["B0_openai"])
    out["runs"]["B0"] = _summ(res, "mt_combined_B0")
    save()
    print("B0", out["runs"]["B0"], flush=True)
    res = run_set("train", "combined_B1", best, caps["B_main"], escalate=True, workers=workers, strong=sol,
                  task_checker=sol, budget_openai_usd=caps["B1_openai"])
    out["runs"]["B1"] = _summ(res, "mt_combined_B1")
    out["spend_main_total_usd"] = sum(r["spend_main_usd"] for r in out["runs"].values())
    out["spend_openai_total_usd"] = sum(r["spend_openai_usd"] for r in out["runs"].values())
    save()
    print("B1", out["runs"]["B1"], flush=True)
    return out


SOL_FIX_PROTOCOL = """TRAIN split, same items, stacks and engine as the combined test (section 13); founder-approved
2026-10-18. Sol (gpt-6.1-sol) answers "which task?", no strong tier (as B0), plus the early-guess fix: no first task
before 10 s, and only after two typed answers in a row named it.
  C1  switch bar 0.8 (as chosen on Jev's answers)
  C2  switch bar 0.9
Written before the runs: choose the C with the fewest wrong switches (single-task + splices) among those whose mean
step accuracy (single-task, splices) is within 1 point of B0's; ties -> the higher right-task share on the splices.
Sol becomes the default task decider only if the chosen C has a higher mean step accuracy than A0 (Jev) and at most
one more wrong switch than A0 (3)."""


def sol_fix_test(workers: int = 4, caps: dict | None = None) -> dict:
    caps = caps or {"main": 0.40, "openai": 1.10}            # per run; two runs = $3.00 at most
    p = RESULTS / "multitask" / "combined_train.json"
    comb = json.loads(p.read_text())
    base = {**comb["best_overrides"], "recognize_min_s": 10.0, "recognize_agree": 2}
    out = {"protocol": SOL_FIX_PROTOCOL, "base_overrides": base, "caps_per_run": caps, "runs": {}}
    save = lambda: (RESULTS / "multitask" / "sol_fix_train.json").write_text(json.dumps(out, indent=1, default=float))  # noqa: E731
    for k, bar in (("C1", 0.8), ("C2", 0.9)):
        res = run_set("train", f"solfix_{k}", {**base, "switch_p": bar}, caps["main"], escalate=False, workers=workers,
                      task_checker="openai:gpt-6.1-sol", budget_openai_usd=caps["openai"])
        out["runs"][k] = _summ(res, f"mt_solfix_{k}")
        save()
        print(k, out["runs"][k], flush=True)
    m = lambda r: (r["single_step_acc"] + r["splice_step_acc"]) / 2                   # noqa: E731
    ws = lambda r: r["single_wrong_switches"] + r["splice_wrong_switches"]           # noqa: E731
    a0, b0 = comb["runs"]["A0"], comb["runs"]["B0"]
    ok = [k for k, r in out["runs"].items() if m(r) >= m(b0) - 0.01]
    chosen = min(ok, key=lambda k: (ws(out["runs"][k]), -out["runs"][k]["splice_correct_task_share"])) if ok else None
    out["chosen"] = chosen
    out["sol_default"] = bool(chosen and m(out["runs"][chosen]) > m(a0) and ws(out["runs"][chosen]) <= ws(a0) + 1)
    out["reference"] = {"A0": a0, "B0": b0}
    out["spend_main_total_usd"] = sum(r["spend_main_usd"] for r in out["runs"].values())
    out["spend_openai_total_usd"] = sum(r["spend_openai_usd"] for r in out["runs"].values())
    save()
    print("chosen", chosen, "sol_default", out["sol_default"], flush=True)
    return out

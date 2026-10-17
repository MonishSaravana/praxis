"""Evaluation metrics. Every function takes ground truth + a run log (or arrays derived only from it)."""
from __future__ import annotations

import numpy as np

from ..runlog import by_kind


# ----------------------------------------------------------------------------- step tracking
def frame_labels(gt_segments: list[tuple[float, float, str]], times: np.ndarray, between: str = "next") -> np.ndarray:
    """GT step id per time. Between annotated segments: 'next' -> upcoming step, 'none' -> ''."""
    segs = sorted(gt_segments)
    out = np.empty(len(times), dtype=object)
    for i, t in enumerate(times):
        lab = ""
        for s, e, k in segs:
            if s <= t < e:
                lab = k
                break
        if not lab and between == "next":
            nxt = [k for s, e, k in segs if s > t]
            lab = nxt[0] if nxt else "__done__"
        out[i] = lab
    return out


def predicted_labels(records: list[dict], times: np.ndarray) -> np.ndarray:
    """MAP step from the logged belief at each time (no belief yet -> '')."""
    bel = by_kind(records, "belief")
    bt = np.array([b["t"] for b in bel])
    out = np.empty(len(times), dtype=object)
    for i, t in enumerate(times):
        j = np.searchsorted(bt, t, side="right") - 1
        out[i] = bel[j]["map"] if j >= 0 else ""
    return out


def step_accuracy(gt: np.ndarray, pred: np.ndarray, inside_only: bool = True, gt_inside: np.ndarray | None = None) -> float:
    m = np.ones(len(gt), bool) if not inside_only or gt_inside is None else gt_inside
    m &= pred != ""
    return float((gt[m] == pred[m]).mean()) if m.any() else float("nan")


def transitions(labels: np.ndarray, times: np.ndarray) -> list[tuple[float, str, str]]:
    out = []
    for i in range(1, len(labels)):
        if labels[i] != labels[i - 1] and labels[i] and labels[i - 1]:
            out.append((float(times[i]), labels[i - 1], labels[i]))
    return out


def transition_timing_error(gt_ends: dict[str, float], records: list[dict]) -> list[float]:
    """|t_commit(step) - t_gt_end(step)| for every step the engine committed and GT has an end for."""
    errs = []
    for c in by_kind(records, "commit"):
        if c["node"] in gt_ends:
            errs.append(abs(c["t"] - gt_ends[c["node"]]))
    return errs


# ----------------------------------------------------------------------------- events (mistakes, boundaries)
def match_events(pred: list[float], gt: list[float], tol_before: float, tol_after: float) -> tuple[int, int, int, list[float]]:
    """Greedy one-to-one matching; a prediction p matches gt g if g - tol_before <= p <= g + tol_after.
    Returns tp, fp, fn and the delays (p - g) of matched pairs."""
    gt_left = sorted(gt)
    tp, delays = 0, []
    for p in sorted(pred):
        cands = [g for g in gt_left if g - tol_before <= p <= g + tol_after]
        if cands:
            g = min(cands, key=lambda g: abs(p - g))
            gt_left.remove(g)
            tp += 1
            delays.append(p - g)
    return tp, len(pred) - tp, len(gt_left), delays


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": 2 * p * r / (p + r) if p + r else 0.0}


# ----------------------------------------------------------------------------- latency
def pct(xs, q) -> float | None:
    xs = [x for x in xs if x is not None and np.isfinite(x)]
    return float(np.percentile(xs, q)) if xs else None


def latency_summary(xs: list[float]) -> dict:
    return {"n": len(xs), "p50": pct(xs, 50), "p95": pct(xs, 95), "mean": float(np.mean(xs)) if xs else None}

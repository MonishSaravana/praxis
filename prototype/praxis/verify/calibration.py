"""L5 · Confidence calibration (ours). Calibrated confidence is what lets the policy be precise.

A verifier's raw verdict is turned into a score s = P(step complete) in [0,1] (or P(deviation)). We fit
temperature (Platt on the logit) and isotonic maps on the train split and report expected calibration
error (ECE) before and after on held-out videos.
"""
from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression


def raw_p_complete(status: str, confidence: float) -> float:
    """Verdict -> raw P(step complete). in_progress/deviation with conf c -> 1-c."""
    c = float(np.clip(confidence, 0.0, 1.0))
    return c if status == "complete" else 1.0 - c


def ece(p: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    p, y = np.asarray(p, float), np.asarray(y, float)
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    e = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            e += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(e)


def reliability(p: np.ndarray, y: np.ndarray, bins: int = 10) -> dict:
    p, y = np.asarray(p, float), np.asarray(y, float)
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    rows = []
    for b in range(bins):
        m = idx == b
        rows.append({"lo": edges[b], "hi": edges[b + 1], "n": int(m.sum()),
                     "conf": float(p[m].mean()) if m.any() else None, "acc": float(y[m].mean()) if m.any() else None})
    return {"bins": rows}


@dataclass
class Calibrator:
    method: str = "isotonic"           # isotonic | temperature | none
    iso: IsotonicRegression | None = None
    platt: LogisticRegression | None = None

    def fit(self, p_raw: np.ndarray, y: np.ndarray) -> "Calibrator":
        p_raw = np.clip(np.asarray(p_raw, float), 1e-4, 1 - 1e-4)
        y = np.asarray(y, int)
        if len(np.unique(y)) < 2:
            self.method = "none"
            return self
        self.iso = IsotonicRegression(y_min=0.01, y_max=0.99, out_of_bounds="clip").fit(p_raw, y)
        logit = np.log(p_raw / (1 - p_raw))[:, None]
        self.platt = LogisticRegression(C=100.0).fit(logit, y)
        return self

    def __call__(self, p_raw) -> np.ndarray:
        p = np.clip(np.atleast_1d(np.asarray(p_raw, float)), 1e-4, 1 - 1e-4)
        if self.method == "isotonic" and self.iso is not None:
            return self.iso.predict(p)
        if self.method == "temperature" and self.platt is not None:
            return self.platt.predict_proba(np.log(p / (1 - p))[:, None])[:, 1]
        return p

    def save(self, path: Path) -> None:
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path: Path) -> "Calibrator":
        with open(path, "rb") as f:
            return pickle.load(f)

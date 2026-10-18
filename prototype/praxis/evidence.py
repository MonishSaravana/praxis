"""Local evidence for L4: per-frame log-likelihood of each task-graph node, in milliseconds.

ZeroShotEvidence  SigLIP2 frame embedding vs the node's compiled end-state / name text embedding.
                  Needs no video of the task at all (works on a freshly compiled graph).
ProbeEvidence     A linear probe over frozen L1 features (SigLIP2 frame + V-JEPA 2 window), trained on the
                  train split's videos of that task. This is the "task-graph library compounds" path: every
                  recorded session of a procedure makes local matching for that procedure better.

Both return hybrid-HMM scaled likelihoods  log p(x | k) = log p(k | x) - log p(k) + const.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from .tasks.schema import TaskGraph


class ZeroShotEvidence:
    name = "zeroshot"

    def __init__(self, graph: TaskGraph, emb: dict[str, np.ndarray], scale: float = 25.0):
        self.ids = graph.ids
        self.E = emb["end_state"] + 0.5 * emb["name"]
        self.E /= np.linalg.norm(self.E, axis=1, keepdims=True)
        self.scale = scale

    def loglik(self, frame_emb: np.ndarray, window_emb: np.ndarray | None = None) -> np.ndarray:
        s = frame_emb @ self.E.T                         # (n, K) cosine
        s = s - s.mean(-1, keepdims=True)
        lp = self.scale * s
        lp = lp - np.log(np.exp(lp - lp.max(-1, keepdims=True)).sum(-1, keepdims=True)) - lp.max(-1, keepdims=True)
        return lp.mean(0) if lp.ndim == 2 else lp


class ProbeEvidence:
    name = "probe"

    def __init__(self, ids: list[str], clf: LogisticRegression, scaler: StandardScaler, prior: np.ndarray):
        self.ids, self.clf, self.scaler, self.prior = ids, clf, scaler, prior

    @staticmethod
    def featurize(frame_emb: np.ndarray, window_emb: np.ndarray) -> np.ndarray:
        return np.concatenate([frame_emb, window_emb], -1)

    @classmethod
    def fit(cls, ids: list[str], X: np.ndarray, y: np.ndarray, C: float = 0.5) -> "ProbeEvidence":
        """X: (n, D) features of train-split frames; y: node index in ids (-1 = background, dropped)."""
        m = y >= 0
        scaler = StandardScaler().fit(X[m])
        clf = LogisticRegression(C=C, max_iter=2000, class_weight="balanced")
        clf.fit(scaler.transform(X[m]), y[m])
        prior = np.full(len(ids), 1e-3)
        cnt = np.bincount(y[m], minlength=len(ids)).astype(float)
        prior = np.maximum(cnt / cnt.sum(), 1e-3)
        return cls(ids, clf, scaler, prior)

    def loglik(self, frame_emb: np.ndarray, window_emb: np.ndarray) -> np.ndarray:
        X = self.featurize(np.atleast_2d(frame_emb), np.atleast_2d(window_emb))
        lp = np.full((len(X), len(self.ids)), np.log(1e-4))
        lp[:, self.clf.classes_] = self.clf.predict_log_proba(self.scaler.transform(X))
        lp = lp - np.log(self.prior)[None] * 0.0      # class_weight=balanced already flattens the prior
        return lp.mean(0)

    def save(self, path: Path) -> None:
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path: Path) -> "ProbeEvidence":
        with open(path, "rb") as f:
            return pickle.load(f)


class FrameProbeEvidence(ProbeEvidence):
    """ProbeEvidence on the SigLIP2 frame embedding alone (no V-JEPA 2 window): on held-out frames the frame-only
    probe scored 44.1% vs 42.1% for frame + window (results/l1/l1_quality_and_probes.json)."""
    name = "probe_frame"

    @staticmethod
    def featurize(frame_emb: np.ndarray, window_emb: np.ndarray) -> np.ndarray:
        return frame_emb

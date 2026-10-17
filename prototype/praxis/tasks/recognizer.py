"""L3b · Task recognizer (ours). "Looks like you're assembling a toy car. Want me to walk you through it?"

From the first seconds of video, and continuously after that, decide which procedure in the task-graph
library is happening.

Evidence per second:
  - a linear task probe over frozen L1 features (SigLIP2 frame + V-JEPA 2 window), trained on train-split
    videos (task-level labels only)
  - zero-shot SigLIP2 similarity between frames and each graph's title (works for graphs with no video yet)
Evidence accumulates as a running log-posterior with forgetting, so the recognizer keeps re-checking.
Recognition fires when the posterior stays above `threshold` for `hold_s`. Optionally the verifier
confirms the top candidate before Praxis speaks.

Open set: if the best library match stays weak, the engine routes to the drafting path (Claude names the
task and drafts a graph, flagged as draft; see tasks/compiler.py, draft=True).
"""
from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


@dataclass
class Recognition:
    t: float
    task_id: str | None
    posterior: dict[str, float]
    recognized: bool
    open_set: bool = False


@dataclass
class TaskRecognizer:
    task_ids: list[str]
    clf: LogisticRegression | None = None
    scaler: StandardScaler | None = None
    text_emb: np.ndarray | None = None          # (T, D) SigLIP2 text embedding of each graph title
    zs_scale: float = 20.0
    forget: float = 0.92                       # per-second decay of accumulated evidence
    local_temp: float = 0.3                    # temperature on the local probe's per-second log-prob
    threshold: float = 0.9
    hold_s: float = 2.0
    open_set_floor: float = 0.5                # if best posterior stays below this for a long time -> open set
    _acc: np.ndarray = field(default=None, repr=False)  # type: ignore[assignment]
    _above: float = 0.0
    _t0: float | None = None

    def reset(self) -> None:
        self._acc = np.zeros(len(self.task_ids))
        self._above = 0.0
        self._t0 = None

    def fit(self, X: np.ndarray, y: np.ndarray, C: float = 0.2) -> "TaskRecognizer":
        self.scaler = StandardScaler().fit(X)
        self.clf = LogisticRegression(C=C, max_iter=3000, class_weight="balanced").fit(self.scaler.transform(X), y)
        return self

    def frame_logprob(self, frame_emb: np.ndarray, window_emb: np.ndarray) -> np.ndarray:
        lp = np.zeros(len(self.task_ids))
        if self.clf is not None:
            X = np.concatenate([np.atleast_2d(frame_emb), np.atleast_2d(window_emb)], -1)
            p = np.full((len(X), len(self.task_ids)), 1e-4)
            p[:, self.clf.classes_] = self.clf.predict_proba(self.scaler.transform(X))
            lp += np.log(p / p.sum(1, keepdims=True)).mean(0)
        elif self.text_emb is not None:
            s = np.atleast_2d(frame_emb) @ self.text_emb.T
            z = self.zs_scale * (s - s.mean(-1, keepdims=True))
            lp += (z - np.log(np.exp(z).sum(-1, keepdims=True))).mean(0)
        return lp

    def update(self, t: float, frame_emb: np.ndarray, window_emb: np.ndarray, dt: float = 1.0) -> Recognition:
        if self._acc is None:
            self.reset()
        if self._t0 is None:
            self._t0 = t
        # per-second evidence: each frame contributes dt of a tempered log-prob; forgetting is per second, so the
        # local probe (trained on few recordings) cannot drown out a typed verifier answer
        self._acc = (self.forget ** dt) * self._acc + dt * self.local_temp * self.frame_logprob(frame_emb, window_emb)
        post = np.exp(self._acc - self._acc.max())
        post /= post.sum()
        k = int(post.argmax())
        self._above = self._above + dt if post[k] >= self.threshold else 0.0
        recognized = self._above >= self.hold_s
        open_set = (t - self._t0) > 20 and post[k] < self.open_set_floor
        return Recognition(t=t, task_id=self.task_ids[k], posterior={i: float(p) for i, p in zip(self.task_ids, post)},
                           recognized=recognized, open_set=open_set)

    def observe_verifier(self, probs: dict[str, float], weight: float = 3.0) -> None:
        """A typed 'which task is this?' answer from the verifier, as high-weight evidence."""
        if self._acc is None:
            self.reset()
        lp = np.array([np.log(max(probs.get(t, 0.0), 1e-3)) for t in self.task_ids])
        self._acc = self._acc + weight * (lp - lp.max())

    def posterior(self) -> dict[str, float]:
        post = np.exp(self._acc - self._acc.max())
        post /= post.sum()
        return {i: float(p) for i, p in zip(self.task_ids, post)}

    def save(self, path: Path) -> None:
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path: Path) -> "TaskRecognizer":
        with open(path, "rb") as f:
            r = pickle.load(f)
        for k, v in (("forget", 0.92), ("local_temp", 0.3)):   # current defaults for pickles from older code
            setattr(r, k, v)
        r.reset()
        return r

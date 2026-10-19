"""Landmarks: things and places tied to a task, and a few that aren't, scored on every frame in milliseconds.

Task landmarks are the `parts` of a compiled graph's nodes (the tortilla, the cucumber, the filter rack), plus
optional per-task anchors from configs/landmarks.json. Each is a SigLIP2 text embedding ("a photo of <part>"); every
frame's SigLIP2 embedding (already computed by L1) is matched against all of them with one matrix product.

A landmark counts in proportion to how few tasks share it (IDF over the library): "bowl", "microwave" or a
technician's toolbox appear everywhere and carry almost no weight; "tortilla" or "filter rack" carry a lot.

Per task, the score over the last `window_s` seconds is the IDF-weighted mean over its landmarks of the top
`top_frac` per-second matches (a landmark only needs to be in view some of the time). On train-split recordings
(30 s windows) this picks the right recipe 60% of the time against 12.5% chance (docs/MULTITASK.md).

Non-task landmarks (a baby, a door, a phone in hand) never belong to a task. With high P(away) they suggest an
interruption, not that the task ended. They can't be measured on CaptainCook4D (none appear), so the engine only
uses them when EngineConfig.nontask_landmarks is on.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import deque

import numpy as np

from .paths import CACHE, CONFIGS

PROMPT = "a photo of {}"


def config() -> dict:
    p = CONFIGS / "landmarks.json"
    return json.loads(p.read_text()) if p.exists() else {"non_task": [], "anchors": {}}


def task_landmarks(g, anchors: dict | None = None) -> list[str]:
    """The landmark phrases of a task graph: its nodes' parts (parenthetical notes dropped) plus its anchors."""
    out = set()
    for n in g.nodes:
        for p in n.parts:
            p = re.sub(r"\s*\(.*?\)", "", p.lower()).strip()
            if p:
                out.add(p)
    for a in (anchors if anchors is not None else config().get("anchors", {})).get(g.task_id, []):
        out.add(a.lower().strip())
    return sorted(out)


def lookalikes(library: dict, thr: float = 0.25, anchors: dict | None = None) -> dict[str, list[str]]:
    """Near-identical procedures: task pairs whose landmark sets overlap at least `thr` (Jaccard of part names, hyphens
    folded). Landmarks can't tell such tasks apart: the four ENIGMA-51 repair procedures name the same bench, tools and
    instruments, and what does differ is nearly one direction in SigLIP2's text space ("high voltage board" vs "low
    voltage board" cosine 0.97, "electric screwdriver" vs "screwdriver" 0.91). Repair pairs overlap 0.32-0.59, no two
    cooking recipes more than 0.14 (docs/MULTITASK.md section 16). Returns {task: [its look-alikes]}; tasks without any
    are left out."""
    fold = lambda p: re.sub(r"\s+", " ", p.replace("-", " ")).strip()      # noqa: E731
    sets = {tid: {fold(p) for p in task_landmarks(g, anchors)} for tid, g in library.items()}
    out: dict[str, list[str]] = {}
    for a, A in sets.items():
        for b, B in sets.items():
            if a != b and A and B and len(A & B) / len(A | B) >= thr:
                out.setdefault(a, []).append(b)
    return out


class TextCache:
    """SigLIP2 text embeddings of landmark phrases, cached on disk (cache/landmarks/) so replay never loads the text
    model once a phrase has been seen. encode: list[str] -> (n, D) array, e.g. SigLIP().texts or StudioCore.texts()."""

    def __init__(self, encode=None):
        self.dir = CACHE / "landmarks"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._encode = encode
        self.mem: dict[str, np.ndarray] = {}

    def _path(self, phrase: str):
        return self.dir / f"{hashlib.sha1(PROMPT.format(phrase).encode()).hexdigest()[:20]}.npy"

    def get(self, phrases: list[str]) -> np.ndarray:
        missing = [p for p in phrases if p not in self.mem and not self._path(p).exists()]
        if missing:
            if self._encode is None:
                from .perception.backbones import SigLIP
                self._encode = SigLIP().texts
            E = np.asarray(self._encode([PROMPT.format(p) for p in missing]), np.float32)
            for p, e in zip(missing, E):
                np.save(self._path(p), e)
                self.mem[p] = e
        for p in phrases:
            if p not in self.mem:
                self.mem[p] = np.load(self._path(p))
        E = np.stack([self.mem[p] for p in phrases]) if phrases else np.zeros((0, 1), np.float32)
        return E / np.maximum(np.linalg.norm(E, axis=1, keepdims=True), 1e-9)


class Landmarks:
    """Per-second landmark scores for every task in the library (and the non-task list)."""

    def __init__(self, library: dict, texts: TextCache | None = None, window_s: float = 30.0, top_frac: float = 0.2,
                 non_task: list[str] | None = None, anchors: dict | None = None):
        cfg = config()
        self.texts = texts or TextCache()
        self.window_s, self.top_frac = window_s, top_frac
        self.anchors = anchors if anchors is not None else cfg.get("anchors", {})
        self.non_task = list(non_task if non_task is not None else cfg.get("non_task", []))
        self.task_phrases: dict[str, list[str]] = {tid: task_landmarks(g, self.anchors) for tid, g in library.items()}
        self.buf: deque = deque(maxlen=max(1, int(round(window_s))))
        self._build()

    def _build(self) -> None:
        phrases = sorted({p for ps in self.task_phrases.values() for p in ps} | set(self.non_task))
        self.phrases = phrases
        self.pid = {p: i for i, p in enumerate(phrases)}
        self.E = self.texts.get(phrases)
        n = max(1, len(self.task_phrases))
        df = {p: sum(p in set(ps) for ps in self.task_phrases.values()) for p in phrases}
        self.idf = np.array([np.log(n / df[p]) if df[p] else 0.0 for p in phrases])
        self.tidx = {tid: np.array([self.pid[p] for p in ps], int) for tid, ps in self.task_phrases.items()}
        self.nidx = np.array([self.pid[p] for p in self.non_task], int)
        self.buf.clear()

    def add_task(self, task_id: str, g) -> None:
        """A task added during a session (pasted or drafted graph): rebuilds the phrase set and IDF; the window
        restarts."""
        self.task_phrases[task_id] = task_landmarks(g, self.anchors)
        self._build()

    # ------------------------------------------------------------------ per second
    def update(self, frame_emb: np.ndarray) -> None:
        """frame_emb: (n, D) SigLIP2 frame embeddings of the last second."""
        if len(frame_emb) == 0 or len(self.phrases) == 0:
            return
        X = np.atleast_2d(frame_emb).astype(np.float32)
        X = X / np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-9)
        self.buf.append((X @ self.E.T).max(0))

    def _top(self) -> np.ndarray | None:
        if not self.buf:
            return None
        B = np.stack(self.buf)                                  # (seconds, phrases)
        k = max(1, int(np.ceil(self.top_frac * len(B))))
        return np.sort(B, 0)[-k:].mean(0)

    def scores(self) -> dict[str, float]:
        top = self._top()
        if top is None:
            return {}
        out = {}
        for tid, idx in self.tidx.items():
            if len(idx) == 0:
                continue
            w = self.idf[idx]
            w = w if w.sum() > 0 else np.ones_like(w)
            out[tid] = float(top[idx] @ w / w.sum())
        return out

    def features(self, task_id: str) -> np.ndarray | None:
        """Off-task features for a hypothesised current task: (margin over the best other task, margin over the mean
        of the others). None until there is a score."""
        s = self.scores()
        if task_id not in s or len(s) < 2:
            return None
        others = [v for k, v in s.items() if k != task_id]
        return np.array([s[task_id] - max(others), s[task_id] - float(np.mean(others))])

    def top_tasks(self, n: int = 3) -> list[tuple[str, float]]:
        return sorted(self.scores().items(), key=lambda kv: -kv[1])[:n]

    def non_task_top(self) -> tuple[str | None, float]:
        """The best-matching non-task landmark over the last few seconds and its peak match."""
        if len(self.nidx) == 0 or not self.buf:
            return None, 0.0
        recent = np.stack(list(self.buf)[-5:])[:, self.nidx].max(0)
        i = int(recent.argmax())
        return self.non_task[i], float(recent[i])


class OffTaskModel:
    """P(the person is not doing task T right now | landmark features for T): a two-feature logistic model fit on
    train-split recordings (experiments.fit_offtask), each paired with every library task as a hypothesised current
    task (on-task when it is the recording's own recipe). Classes are balanced, so its odds are a likelihood ratio;
    the tracker's away_enter supplies the prior."""

    def __init__(self, coef: list[float], intercept: float, window_s: float = 30.0, top_frac: float = 0.2, info=None):
        self.coef, self.intercept = np.asarray(coef, float), float(intercept)
        self.window_s, self.top_frac, self.info = window_s, top_frac, info or {}

    def p_off(self, feats: np.ndarray | None) -> float | None:
        if feats is None:
            return None
        z = float(feats @ self.coef + self.intercept)
        return float(1.0 / (1.0 + np.exp(z)))                  # the model predicts on-task; P(off) = 1 - P(on)

    def save(self, path) -> None:
        path.write_text(json.dumps({"coef": self.coef.tolist(), "intercept": self.intercept, "window_s": self.window_s,
                                    "top_frac": self.top_frac, "info": self.info}, indent=2))

    @staticmethod
    def load(path) -> "OffTaskModel":
        d = json.loads(path.read_text())
        return OffTaskModel(d["coef"], d["intercept"], d.get("window_s", 30.0), d.get("top_frac", 0.2), d.get("info"))

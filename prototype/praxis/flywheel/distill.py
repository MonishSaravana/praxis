"""L7 · Distillation: the frontier verifier teaches a small local student for routine checks.

Student input (all local, all already computed by L1 every frame):
  SigLIP2 frame embedding at t, V-JEPA 2 window embedding at t, SigLIP2 text embedding of the node's
  expected end state, and their product (frame x end-state).
Target: the teacher's calibrated P(step complete), mixed with ground truth where it exists.
Output: DistilledVerifier, a drop-in Verifier (same Verdict schema), ~1 ms on CPU, $0 per check.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from ..paths import CKPT, DATA, FEATURES
from ..verify.schema import Verdict, VerifyRequest


def _feat_at(clip_id: str, t_rel: float, cache: dict) -> tuple[np.ndarray, np.ndarray] | None:
    if clip_id not in cache:
        p = FEATURES / f"{clip_id}.npz"
        if not p.exists():
            cache[clip_id] = None
        else:
            z = np.load(p)
            cache[clip_id] = (z["t"], z["siglip"].astype(np.float32), z["window"].astype(np.float32))
    if cache[clip_id] is None:
        return None
    t, s, w = cache[clip_id]
    i = int(np.searchsorted(t, t_rel, side="right") - 1)
    if i < 0:
        return None
    lo = max(0, i - 3)
    return s[lo:i + 1].mean(0), w[i]


def _text(task_id: str, node: str, ids_cache: dict) -> np.ndarray:
    if task_id not in ids_cache:
        from ..tasks.schema import TaskGraph
        from ..paths import TASKGRAPHS
        g = TaskGraph.load(TASKGRAPHS / f"{task_id}.json")
        z = np.load(DATA / "taskgraph_emb" / f"{task_id}.npz")
        ids_cache[task_id] = {n: z["end_state"][i] for i, n in enumerate(g.ids)}
    return ids_cache[task_id][node]


def featurize(rows: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    fc, tc, X, keep = {}, {}, [], []
    for i, r in enumerate(rows):
        f = _feat_at(r["clip_id"], r["t_rel"], fc)
        if f is None:
            continue
        s, w = f
        e = _text(r["task_id"], r["node"], tc)
        X.append(np.concatenate([s, w, e, s * e * 10]))
        keep.append(i)
    return np.array(X, np.float32), np.array(keep)


class Student(nn.Module):
    def __init__(self, d: int, h: int = 256, p: float = 0.3):
        super().__init__()
        self.net = nn.Sequential(nn.LayerNorm(d), nn.Dropout(p), nn.Linear(d, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, 1))

    def forward(self, x):
        return self.net(x).squeeze(-1)


def train_student(X: np.ndarray, y_teacher: np.ndarray, y_gt: np.ndarray | None = None, alpha: float = 0.5,
                  epochs: int = 300, lr: float = 1e-3, seed: int = 0) -> tuple[Student, dict]:
    torch.manual_seed(seed)
    m = Student(X.shape[1])
    opt = torch.optim.AdamW(m.parameters(), lr=lr, weight_decay=5e-2)
    xt = torch.from_numpy(X)
    yt = torch.from_numpy(y_teacher.astype(np.float32))
    yg = torch.from_numpy(y_gt.astype(np.float32)) if y_gt is not None else None
    t0 = time.time()
    for _ in range(epochs):
        m.train()
        logit = m(xt + 0.02 * torch.randn_like(xt))
        loss = F.binary_cross_entropy_with_logits(logit, yt)
        if yg is not None and alpha > 0:
            loss = (1 - alpha) * loss + alpha * F.binary_cross_entropy_with_logits(logit, yg)
        opt.zero_grad()
        loss.backward()
        opt.step()
    m.eval()
    return m, {"train_s": time.time() - t0, "n": len(X), "alpha_gt": alpha}


def predict(m: Student, X: np.ndarray) -> np.ndarray:
    with torch.no_grad():
        return torch.sigmoid(m(torch.from_numpy(X))).numpy()


class DistilledVerifier:
    """Drop-in Verifier: routine 'is this step complete?' from local features, no API call."""
    name = "distilled"
    model = "praxis-student-v0"

    def __init__(self, path: Path = CKPT / "student.pt"):
        ck = torch.load(path, map_location="cpu", weights_only=False)
        self.m = Student(ck["d"])
        self.m.load_state_dict(ck["state"])
        self.m.eval()
        self._tc: dict = {}

    def verify(self, req: VerifyRequest) -> Verdict:
        t0 = time.perf_counter()
        s, w = req.features["siglip"], req.features["window"]
        e = _text(req.graph.task_id, req.node.id, self._tc)
        x = np.concatenate([s, w, e, s * e * 10])[None].astype(np.float32)
        p = float(predict(self.m, x)[0])
        st = "complete" if p >= 0.5 else "in_progress"
        return Verdict(step_status=st, confidence=max(p, 1 - p), node_id=req.node.id, model=self.model, role="student",
                       prompt_version="student-v0", latency_ms=(time.perf_counter() - t0) * 1000, cost_usd=0.0,
                       raw={"p_complete": p})

    @staticmethod
    def save(m: Student, d: int, path: Path = CKPT / "student.pt", info: dict | None = None) -> None:
        torch.save({"state": m.state_dict(), "d": d, "info": info or {}}, path)


def load_rows(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]

"""Train the L2 event detector on train-split clips; evaluate on held-out videos and held-out procedure types.

Labels come from the datasets' step annotations: a boundary at every annotated step end, a grasp at every
fine-grained pick-up/take action start when the dataset has them.
"""
from __future__ import annotations

import json
import time

import numpy as np
import torch
import torch.nn.functional as F

from ..paths import CKPT, RESULTS
from .detector import EventNet, HeuristicDetector, LearnedDetector, boundary_f1, input_tensor, peaks, soft_targets


def make_xy(feats, boundaries: list[float], grasps: list[float]):
    x = input_tensor(feats)
    y = np.stack([soft_targets(feats.t, boundaries, 1.0), soft_targets(feats.t, grasps, 0.75)], 1)
    has_g = np.full(len(x), 1.0 if grasps else 0.0, np.float32)
    return x, y, has_g


def train(train_items, val_items=None, epochs: int = 60, seq_len: int = 480, lr: float = 1e-3, seed: int = 0,
          dev: str = "cpu", log_every: int = 10) -> tuple[LearnedDetector, dict]:
    """items: list of (ClipFeatures, boundaries, grasps)."""
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    data = [make_xy(f, b, g) for f, b, g in train_items]
    allx = np.concatenate([d[0] for d in data])
    mean, std = allx.mean(0), allx.std(0) + 1e-4
    f0 = train_items[0][0]
    net = EventNet(f0.frame.shape[1], f0.window.shape[1]).to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=1e-2)
    pos_frac = float(np.concatenate([d[1][:, 0] for d in data]).mean())
    pos_w = torch.tensor([(1 - pos_frac) / max(pos_frac, 1e-3), 4.0], device=dev)
    hist = []
    t0 = time.perf_counter()
    for ep in range(epochs):
        net.train()
        order = rng.permutation(len(data))
        tot = 0.0
        for i in order:
            x, y, hg = data[i]
            if len(x) > seq_len:
                s = rng.integers(0, len(x) - seq_len)
                x, y, hg = x[s:s + seq_len], y[s:s + seq_len], hg[s:s + seq_len]
            xx = torch.from_numpy((x - mean) / std)[None].to(dev)
            xx = xx + 0.05 * torch.randn_like(xx)
            yy = torch.from_numpy(y)[None].to(dev)
            logits = net(xx)
            lb = F.binary_cross_entropy_with_logits(logits[..., 0], yy[..., 0], pos_weight=pos_w[0])
            lg = F.binary_cross_entropy_with_logits(logits[..., 1], yy[..., 1], pos_weight=pos_w[1], reduction="none")
            lg = (lg * torch.from_numpy(hg)[None].to(dev)).mean()
            loss = lb + 0.5 * lg
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
            tot += float(loss)
        hist.append(tot / len(data))
        if log_every and (ep + 1) % log_every == 0:
            print(f"epoch {ep + 1}: loss {hist[-1]:.4f}", flush=True)
    det = LearnedDetector(net.cpu(), mean.astype(np.float32), std.astype(np.float32), "cpu")
    return det, {"loss": hist, "train_s": time.perf_counter() - t0, "n_train_clips": len(train_items)}


def evaluate(detector, items, thr: float, min_gap_s: float = 2.0, tol: float = 2.0) -> dict:
    tp = fp = fn = 0
    per = []
    t0 = time.perf_counter()
    n_frames = 0
    for f, b, _ in items:
        s = detector.score(f)["boundary"]
        n_frames += len(s)
        pred = [p for p, _ in peaks(f.t, s, thr, min_gap_s)]
        r = boundary_f1(pred, b, tol)
        tp, fp, fn = tp + r["tp"], fp + r["fp"], fn + r["fn"]
        per.append({"clip": f.clip_id, **r})
    dt = time.perf_counter() - t0
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": prec, "recall": rec, "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
            "tp": tp, "fp": fp, "fn": fn, "thr": thr, "tol_s": tol, "n_clips": len(items),
            "head_fps": n_frames / dt if dt > 0 else None, "per_clip": per}


def tune_threshold(detector, items, grid=None, min_gap_s: float = 2.0, tol: float = 2.0) -> float:
    grid = grid or [round(x, 2) for x in np.arange(0.1, 0.95, 0.05)]
    best = max(grid, key=lambda th: evaluate(detector, items, th, min_gap_s, tol)["f1"])
    return float(best)


def run(train_items, test_sets: dict[str, list], out_name: str = "l2_event_detector", epochs: int = 60) -> dict:
    det, info = train(train_items, epochs=epochs)
    thr = tune_threshold(det, train_items)
    heur = HeuristicDetector()
    hthr = tune_threshold(heur, train_items)
    res = {"train": info | {"thr": thr, "heuristic_thr": hthr}, "test": {}}
    for name, items in test_sets.items():
        res["test"][name] = {"learned": evaluate(det, items, thr), "heuristic": evaluate(heur, items, hthr)}
    CKPT.mkdir(parents=True, exist_ok=True)
    det.save(CKPT / f"{out_name}.pt")
    (RESULTS / "l2").mkdir(parents=True, exist_ok=True)
    with open(RESULTS / "l2" / f"{out_name}.json", "w") as f:
        json.dump(res, f, indent=2, default=float)
    return res

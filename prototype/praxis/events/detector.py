"""L2 · Event detector (ours, trained). "Something just finished — worth checking."

A small causal temporal conv net over frozen L1 features predicts, per timestep:
  - boundary: a procedure step just ended (labels: the dataset's step end timestamps)
  - grasp:    a part/tool was just picked up (labels: fine-grained 'take/pick' actions when available),
              used for early wrong-part warnings
It is task-agnostic (no step identities), trained with whole procedure types held out.

Baseline: HeuristicDetector — frame-difference / SSIM change score + peak picking.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

FPS = 4.0   # feature rate (frames/s) the detector runs at


@dataclass
class ClipFeatures:
    """L1 features of one clip on a common FPS timeline."""
    clip_id: str
    t: np.ndarray            # (N,)
    frame: np.ndarray        # (N, Df) per-frame embedding (SigLIP2 or DINOv2)
    hands: np.ndarray        # (N, 12)
    window: np.ndarray       # (N, Dw) V-JEPA 2 clip embedding of the window ending at t (held between updates)
    change: np.ndarray       # (N,) 1 - SSIM to previous frame (heuristic signal)


def input_tensor(f: ClipFeatures) -> np.ndarray:
    hands = f.hands.copy()
    dh = np.zeros_like(hands)
    dh[1:] = hands[1:] - hands[:-1]                         # hand motion
    return np.concatenate([f.frame, f.window, hands, dh * 10.0, f.change[:, None] * 10.0], 1).astype(np.float32)


class CausalBlock(nn.Module):
    def __init__(self, c: int, k: int, dil: int, p: float):
        super().__init__()
        self.pad = (k - 1) * dil
        self.conv = nn.Conv1d(c, c, k, dilation=dil)
        self.norm = nn.GroupNorm(1, c)
        self.drop = nn.Dropout(p)

    def forward(self, x):
        y = self.conv(F.pad(x, (self.pad, 0)))
        return x + self.drop(F.gelu(self.norm(y)))


class EventNet(nn.Module):
    """Causal dilated TCN. Receptive field ~ 2*sum(dilations)+1 steps (~16 s at 4 fps)."""

    def __init__(self, d_frame: int, d_window: int, hidden: int = 128, p: float = 0.2, heads: int = 2):
        super().__init__()
        self.d_frame, self.d_window = d_frame, d_window
        self.proj_frame = nn.Linear(d_frame, hidden)
        self.proj_window = nn.Linear(d_window, hidden)
        self.proj_rest = nn.Linear(12 + 12 + 1, hidden)
        self.inp_drop = nn.Dropout(p)
        self.blocks = nn.Sequential(*[CausalBlock(hidden, 3, d, p) for d in (1, 2, 4, 8, 16)])
        self.head = nn.Conv1d(hidden, heads, 1)

    def forward(self, x):                                   # x: (B, T, D)
        a, b = self.d_frame, self.d_frame + self.d_window
        h = self.proj_frame(x[..., :a]) + self.proj_window(x[..., a:b]) + self.proj_rest(x[..., b:])
        h = self.inp_drop(F.gelu(h)).transpose(1, 2)        # (B, H, T)
        return self.head(self.blocks(h)).transpose(1, 2)    # (B, T, heads) logits


def soft_targets(t: np.ndarray, events: list[float], sigma: float = 1.0) -> np.ndarray:
    y = np.zeros_like(t, dtype=np.float32)
    for e in events:
        y = np.maximum(y, np.exp(-0.5 * ((t - e) / sigma) ** 2))
    return y


def peaks(t: np.ndarray, score: np.ndarray, thr: float, min_gap_s: float) -> list[tuple[float, float]]:
    """Causal-friendly peak picking: local maxima above thr, at least min_gap_s apart (greedy by score)."""
    cand = [i for i in range(len(score)) if score[i] >= thr
            and (i == 0 or score[i] >= score[i - 1]) and (i == len(score) - 1 or score[i] > score[i + 1])]
    cand.sort(key=lambda i: -score[i])
    keep: list[int] = []
    for i in cand:
        if all(abs(t[i] - t[j]) >= min_gap_s for j in keep):
            keep.append(i)
    return sorted((float(t[i]), float(score[i])) for i in keep)


def boundary_f1(pred: list[float], gt: list[float], tol: float = 2.0) -> dict:
    """Greedy one-to-one matching within +-tol seconds."""
    gt_left = list(gt)
    tp = 0
    for p in sorted(pred):
        if not gt_left:
            break
        j = int(np.argmin([abs(p - g) for g in gt_left]))
        if abs(p - gt_left[j]) <= tol:
            tp += 1
            gt_left.pop(j)
    fp, fn = len(pred) - tp, len(gt) - tp
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": prec, "recall": rec, "f1": f1}


class LearnedDetector:
    name = "learned"

    def __init__(self, net: EventNet, mean: np.ndarray, std: np.ndarray, dev: str = "cpu"):
        self.net = net.to(dev).eval()
        self.mean, self.std, self.dev = mean, std, dev

    @torch.inference_mode()
    def score(self, f: ClipFeatures) -> dict[str, np.ndarray]:
        x = (input_tensor(f) - self.mean) / self.std
        out = torch.sigmoid(self.net(torch.from_numpy(x)[None].to(self.dev)))[0].cpu().numpy()
        return {"boundary": out[:, 0], "grasp": out[:, 1]}

    def save(self, path) -> None:
        torch.save({"state": self.net.state_dict(), "mean": self.mean, "std": self.std,
                    "d_frame": self.net.d_frame, "d_window": self.net.d_window,
                    "hidden": self.net.proj_frame.out_features}, path)

    @classmethod
    def load(cls, path, dev: str = "cpu") -> "LearnedDetector":
        ck = torch.load(path, map_location="cpu", weights_only=False)
        net = EventNet(ck["d_frame"], ck["d_window"], hidden=ck.get("hidden", ck["state"]["proj_frame.weight"].shape[0]))
        net.load_state_dict(ck["state"])
        return cls(net, ck["mean"], ck["std"], dev)


class HeuristicDetector:
    """Baseline: smoothed frame-change (1 - SSIM) relative to its running median."""
    name = "heuristic"

    def __init__(self, smooth_s: float = 1.0):
        self.k = max(1, int(smooth_s * FPS))

    def score(self, f: ClipFeatures) -> dict[str, np.ndarray]:
        c = np.convolve(f.change, np.ones(self.k) / self.k, mode="full")[: len(f.change)]   # causal smoothing
        med = np.array([np.median(c[max(0, i - 120): i + 1]) for i in range(len(c))])
        s = np.clip((c - med) / (np.abs(med) + 1e-3), 0, None)
        s = s / (1 + s)
        return {"boundary": s, "grasp": np.zeros_like(s)}

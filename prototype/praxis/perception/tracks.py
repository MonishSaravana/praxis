"""L1 · Point tracking with TAPNext++ (Google DeepMind, torch, frozen).

Used for four things:
  1. follow the part being worked on through hand occlusion (online, re-detects after occlusion)
  2. region-of-interest crops for the verifier: zoomed, high-res evidence for fine calls (orientation)
     at fewer tokens than a full frame
  3. a motion-completion signal: tracked points on a placed part stop moving
  4. simple physical state: in-plane rotation of the tracked point set (Procrustes)

Queries are seeded on a grid around the working area (the hands' bounding box from MediaPipe, or the
image centre when no hands are visible), and re-seeded whenever the engine starts a new step.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import cv2
import numpy as np
import torch

from ..paths import CACHE
from .backbones import device as _device

CKPT = CACHE / "models" / "tapnextpp_ckpt.pt"


@dataclass
class TrackState:
    t: float
    xy: np.ndarray          # (Q,2) display px
    visible: np.ndarray     # (Q,) bool
    speed: float            # median px/s of visible points since previous frame
    rotation_deg: float     # in-plane rotation of the point set since seeding
    roi: tuple[int, int, int, int] | None  # x0,y0,x1,y1 crop box in display px


class PointTracker:
    def __init__(self, n_side: int = 6, dev: str | None = None, half: bool = False):
        from tapnet.tapnextpp.votsp2026.model import TAPNextPP
        d = torch.device(dev) if dev else _device()
        self.model = TAPNextPP.from_checkpoint(str(CKPT), device=d, half_precision=half)
        self.n_side = n_side
        self.state = None
        self.seed_xy: np.ndarray | None = None
        self.prev: tuple[float, np.ndarray] | None = None
        self.last_ms = 0.0

    def seed(self, frame_rgb: np.ndarray, box: tuple[float, float, float, float], t: float) -> TrackState:
        """Start tracking a grid of points inside box=(x0,y0,x1,y1) (display px)."""
        x0, y0, x1, y1 = box
        xs = np.linspace(x0, x1, self.n_side)
        ys = np.linspace(y0, y1, self.n_side)
        q = np.stack(np.meshgrid(xs, ys), -1).reshape(-1, 2).astype(np.float32)
        self.state, self.prev = None, None
        self.seed_xy = q
        return self._step(frame_rgb, t, q)

    def update(self, frame_rgb: np.ndarray, t: float) -> TrackState | None:
        if self.seed_xy is None:
            return None
        return self._step(frame_rgb, t, None)

    def _step(self, frame_rgb: np.ndarray, t: float, q: np.ndarray | None) -> TrackState:
        t0 = time.perf_counter()
        bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        xy, vis, self.state = self.model.track_frame(bgr, query_points_xy=q, state=self.state)
        if self.model.device.type == "mps":
            torch.mps.synchronize()
        self.last_ms = (time.perf_counter() - t0) * 1000
        speed = 0.0
        if self.prev is not None:
            pt, pxy = self.prev
            m = vis & np.isfinite(xy).all(1)
            if m.any() and t > pt:
                speed = float(np.median(np.linalg.norm(xy[m] - pxy[m], axis=1)) / (t - pt))
        self.prev = (t, xy.copy())
        rot = _rotation_deg(self.seed_xy, xy, vis)
        roi = _roi(xy, vis, frame_rgb.shape[:2])
        return TrackState(t=t, xy=xy, visible=vis, speed=speed, rotation_deg=rot, roi=roi)


def _rotation_deg(a: np.ndarray | None, b: np.ndarray, vis: np.ndarray) -> float:
    if a is None or vis.sum() < 3:
        return 0.0
    A, B = a[vis] - a[vis].mean(0), b[vis] - b[vis].mean(0)
    u, _, vt = np.linalg.svd(A.T @ B)
    r = (u @ vt).T
    return float(np.degrees(np.arctan2(r[1, 0], r[0, 0])))


def _roi(xy: np.ndarray, vis: np.ndarray, hw: tuple[int, int], pad: float = 0.35, min_side: int = 96):
    if vis.sum() < 3:
        return None
    p = xy[vis]
    lo, hi = np.percentile(p, 10, 0), np.percentile(p, 90, 0)
    c, s = (lo + hi) / 2, max(float((hi - lo).max()) * (1 + 2 * pad), min_side)
    h, w = hw
    x0, y0 = int(max(0, c[0] - s / 2)), int(max(0, c[1] - s / 2))
    x1, y1 = int(min(w, c[0] + s / 2)), int(min(h, c[1] + s / 2))
    if x1 - x0 < 16 or y1 - y0 < 16:
        return None
    return x0, y0, x1, y1


def hand_box(hand_feat: np.ndarray, hw: tuple[int, int], grow: float = 1.8) -> tuple[float, float, float, float]:
    """Working-area box from the Hands feature vector (2 hands x [present,cx,cy,w,h,spread])."""
    h, w = hw
    boxes = []
    for k in range(2):
        f = hand_feat[k * 6:(k + 1) * 6]
        if f[0] > 0:
            cx, cy, bw, bh = f[1] * w, f[2] * h, f[3] * w, f[4] * h
            boxes.append((cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2))
    if not boxes:
        return (w * 0.3, h * 0.35, w * 0.7, h * 0.85)
    b = np.array(boxes)
    x0, y0, x1, y1 = b[:, 0].min(), b[:, 1].min(), b[:, 2].max(), b[:, 3].max()
    cx, cy, s = (x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0) * grow
    return (max(0, cx - s / 2), max(0, cy - s / 2), min(w, cx + s / 2), min(h, cy + s / 2))


def crop(frame_rgb: np.ndarray, roi: tuple[int, int, int, int] | None, scale_from: tuple[int, int] | None = None) -> np.ndarray | None:
    """Cut the ROI out of a (possibly higher-res) frame. scale_from = (h,w) of the frame the roi refers to."""
    if roi is None:
        return None
    x0, y0, x1, y1 = roi
    if scale_from:
        sy, sx = frame_rgb.shape[0] / scale_from[0], frame_rgb.shape[1] / scale_from[1]
        x0, x1, y0, y1 = int(x0 * sx), int(x1 * sx), int(y0 * sy), int(y1 * sy)
    return frame_rgb[y0:y1, x0:x1].copy()

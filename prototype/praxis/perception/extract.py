"""Offline L1 feature extraction for a clip -> data/features/<clip_id>.npz

Same encoders and same per-frame / per-window cadence the live engine uses, so offline eval matches
what runs online:
  4 fps:  SigLIP2 image embedding, DINOv2 (CLS + mean patch), MediaPipe hands, 1-SSIM change score
  1 Hz:   V-JEPA 2 embedding of the trailing 2 s window (8 frames @ 224)
"""
from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np

from ..io.sources import FileSource
from ..paths import FEATURES
from .backbones import DINOv2, Hands, SigLIP, VJEPA2


def ssim_small(a: np.ndarray, b: np.ndarray) -> float:
    a = cv2.resize(cv2.cvtColor(a, cv2.COLOR_RGB2GRAY), (64, 48)).astype(np.float32)
    b = cv2.resize(cv2.cvtColor(b, cv2.COLOR_RGB2GRAY), (64, 48)).astype(np.float32)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    mu_a, mu_b = cv2.GaussianBlur(a, (7, 7), 1.5), cv2.GaussianBlur(b, (7, 7), 1.5)
    sa = cv2.GaussianBlur(a * a, (7, 7), 1.5) - mu_a ** 2
    sb = cv2.GaussianBlur(b * b, (7, 7), 1.5) - mu_b ** 2
    sab = cv2.GaussianBlur(a * b, (7, 7), 1.5) - mu_a * mu_b
    m = ((2 * mu_a * mu_b + c1) * (2 * sab + c2)) / ((mu_a ** 2 + mu_b ** 2 + c1) * (sa + sb + c2))
    return float(m.mean())


class Extractor:
    def __init__(self, fps: float = 4.0, window_s: float = 2.0, stride_s: float = 1.0, vjepa_frames: int = 8,
                 vjepa_size: int = 224, use_vjepa: bool = True):
        self.fps, self.window_s, self.stride_s = fps, window_s, stride_s
        self.sig = SigLIP()
        self.dino = DINOv2()
        self.vj = VJEPA2(n_frames=vjepa_frames, size=vjepa_size) if use_vjepa else None

    def run(self, video: str | Path, clip_id: str, start: float = 0.0, end: float | None = None,
            out_dir: Path = FEATURES, overwrite: bool = False) -> Path:
        out = out_dir / f"{clip_id}.npz"
        if out.exists() and not overwrite:
            return out
        out_dir.mkdir(parents=True, exist_ok=True)
        t0 = time.perf_counter()
        src = FileSource(video, fps=self.fps, start=start, end=end, max_side=640)
        frames, ts = [], []
        for fr in src:
            frames.append(fr.rgb)
            ts.append(fr.t)
        t_dec = time.perf_counter() - t0
        hands = Hands()
        hf = np.stack([hands.frame(f, t)[0] for f, t in zip(frames, ts)]) if frames else np.zeros((0, 12))
        hands.close()
        t1 = time.perf_counter()
        sig = self.sig.images(frames)
        t2 = time.perf_counter()
        dino = self.dino.images(frames)
        t3 = time.perf_counter()
        change = np.zeros(len(frames), np.float32)
        for i in range(1, len(frames)):
            change[i] = 1.0 - ssim_small(frames[i - 1], frames[i])
        # V-JEPA on the trailing window, every stride_s; held constant in between (causal)
        n_win = int(self.window_s * self.fps)
        step = int(self.stride_s * self.fps)
        win_idx = list(range(n_win - 1, len(frames), step))
        if self.vj is not None and win_idx:
            emb = self.vj.clips([frames[i - n_win + 1: i + 1] for i in win_idx], batch=4)
        else:
            emb = np.zeros((len(win_idx), 1024), np.float32)
        t4 = time.perf_counter()
        window = np.zeros((len(frames), emb.shape[1] if len(emb) else 1024), np.float32)
        for j, i in enumerate(win_idx):
            window[i: (win_idx[j + 1] if j + 1 < len(win_idx) else len(frames))] = emb[j]
        np.savez_compressed(out, t=np.array(ts, np.float32), siglip=sig.astype(np.float16),
                            dino=dino.astype(np.float16), hands=hf.astype(np.float32), window=window.astype(np.float16),
                            window_t=np.array([ts[i] for i in win_idx], np.float32), change=change,
                            timing=np.array([t_dec, t1 - t0 - t_dec, t2 - t1, t3 - t2, t4 - t3], np.float32),
                            hw=np.array(frames[0].shape[:2] if frames else (0, 0)))
        return out


def load_features(clip_id: str, frame_key: str = "siglip"):
    from ..events.detector import ClipFeatures
    z = np.load(FEATURES / f"{clip_id}.npz")
    return ClipFeatures(clip_id=clip_id, t=z["t"], frame=z[frame_key].astype(np.float32), hands=z["hands"],
                        window=z["window"].astype(np.float32), change=z["change"]), z

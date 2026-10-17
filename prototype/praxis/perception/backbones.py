"""L1 · Perception (off-the-shelf, frozen, local).

Per-frame:  SigLIP2 (image+text, zero-shot matching) and DINOv2-small (dense visual features).
Per-window: V-JEPA 2 ViT-L (motion-aware clip embedding).
Per-frame:  MediaPipe hand landmarks (hand presence / position / motion).

All encoders are frozen; we only train small heads on top of them (L2, L3b, L7).
"""
from __future__ import annotations

import time
from functools import lru_cache

import numpy as np
import torch
import torch.nn.functional as F

from ..paths import CACHE  # noqa: F401  (sets HF_HOME)

_IMNET_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
_IMNET_STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)


def device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def _to_tensor(frames: list[np.ndarray] | np.ndarray, size: int, mean: torch.Tensor, std: torch.Tensor) -> torch.Tensor:
    """RGB uint8 frames -> normalized float tensor (N,3,size,size), short-side resize + center crop."""
    x = torch.from_numpy(np.stack(frames) if isinstance(frames, list) else frames).permute(0, 3, 1, 2).float() / 255.0
    h, w = x.shape[-2:]
    s = size / min(h, w)
    x = F.interpolate(x, size=(max(size, round(h * s)), max(size, round(w * s))), mode="bilinear", antialias=True, align_corners=False)
    h, w = x.shape[-2:]
    top, left = (h - size) // 2, (w - size) // 2
    x = x[..., top:top + size, left:left + size]
    return (x - mean) / std


class SigLIP:
    """Image + text embeddings in a shared space (zero-shot frame <-> expected-end-state matching)."""

    name = "google/siglip2-base-patch16-224"

    def __init__(self, dev: torch.device | None = None, dtype: torch.dtype = torch.float16):
        from transformers import AutoModel, AutoTokenizer
        self.dev = dev or device()
        self.dtype = dtype
        self.model = AutoModel.from_pretrained(self.name, torch_dtype=dtype).to(self.dev).eval()
        self.tok = AutoTokenizer.from_pretrained(self.name)
        self.mean = torch.tensor([0.5, 0.5, 0.5]).view(1, 3, 1, 1)
        self.std = torch.tensor([0.5, 0.5, 0.5]).view(1, 3, 1, 1)
        self.dim = self.model.config.text_config.hidden_size

    @torch.inference_mode()
    def images(self, frames: list[np.ndarray], batch: int = 32) -> np.ndarray:
        out = []
        for i in range(0, len(frames), batch):
            x = _to_tensor(frames[i:i + batch], 224, self.mean, self.std).to(self.dev, self.dtype)
            f = self.model.get_image_features(pixel_values=x)
            f = f.pooler_output if hasattr(f, "pooler_output") else f
            out.append(F.normalize(f.float(), dim=-1).cpu().numpy())
        return np.concatenate(out) if out else np.zeros((0, self.dim), np.float32)

    @torch.inference_mode()
    def texts(self, texts: list[str]) -> np.ndarray:
        t = self.tok([s.lower() for s in texts], padding="max_length", max_length=64, truncation=True, return_tensors="pt").to(self.dev)
        f = self.model.get_text_features(**t)
        f = f.pooler_output if hasattr(f, "pooler_output") else f
        return F.normalize(f.float(), dim=-1).cpu().numpy()


class DINOv2:
    name = "facebook/dinov2-small"

    def __init__(self, dev: torch.device | None = None, dtype: torch.dtype = torch.float16):
        from transformers import AutoModel
        self.dev = dev or device()
        self.dtype = dtype
        self.model = AutoModel.from_pretrained(self.name, torch_dtype=dtype).to(self.dev).eval()
        self.dim = self.model.config.hidden_size

    @torch.inference_mode()
    def images(self, frames: list[np.ndarray], batch: int = 32) -> np.ndarray:
        out = []
        for i in range(0, len(frames), batch):
            x = _to_tensor(frames[i:i + batch], 224, _IMNET_MEAN, _IMNET_STD).to(self.dev, self.dtype)
            h = self.model(pixel_values=x).last_hidden_state
            cls, patch_mean = h[:, 0], h[:, 1:].mean(1)
            out.append(torch.cat([cls, patch_mean], -1).float().cpu().numpy())
        return np.concatenate(out) if out else np.zeros((0, 2 * self.dim), np.float32)


class VJEPA2:
    """Motion-aware clip encoder. A window of `n_frames` frames -> one mean-pooled 1024-d embedding."""

    name = "facebook/vjepa2-vitl-fpc64-256"

    def __init__(self, dev: torch.device | None = None, dtype: torch.dtype = torch.float16,
                 n_frames: int = 16, size: int = 256):
        from transformers import VJEPA2Model
        self.dev = dev or device()
        self.dtype = dtype
        self.n_frames, self.size = n_frames, size
        self.model = VJEPA2Model.from_pretrained(self.name, torch_dtype=dtype).to(self.dev).eval()
        self.dim = self.model.config.hidden_size

    @torch.inference_mode()
    def clips(self, windows: list[list[np.ndarray]], batch: int = 2) -> np.ndarray:
        out = []
        for i in range(0, len(windows), batch):
            xs = []
            for w in windows[i:i + batch]:
                idx = np.linspace(0, len(w) - 1, self.n_frames).round().astype(int)
                xs.append(_to_tensor([w[j] for j in idx], self.size, _IMNET_MEAN, _IMNET_STD))
            x = torch.stack(xs).to(self.dev, self.dtype)            # (B,T,3,H,W)
            h = self.model.get_vision_features(x)                   # (B, tokens, 1024)
            out.append(h.mean(1).float().cpu().numpy())
        return np.concatenate(out) if out else np.zeros((0, self.dim), np.float32)


class Hands:
    """MediaPipe HandLandmarker (VIDEO mode). Per frame -> 2 hands x [present, cx, cy, w, h, spread]."""

    model_path = CACHE / "models" / "hand_landmarker.task"
    dim = 12

    def __init__(self):
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision
        self._mp = mp
        opts = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(self.model_path)),
            running_mode=vision.RunningMode.VIDEO, num_hands=2,
            min_hand_detection_confidence=0.4, min_hand_presence_confidence=0.4, min_tracking_confidence=0.4)
        self.det = vision.HandLandmarker.create_from_options(opts)
        self._last_ms = -1

    def frame(self, rgb: np.ndarray, t: float) -> tuple[np.ndarray, list[np.ndarray]]:
        ms = max(int(t * 1000), self._last_ms + 1)
        self._last_ms = ms
        img = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        res = self.det.detect_for_video(img, ms)
        feat = np.zeros(self.dim, np.float32)
        lms: list[np.ndarray] = []
        hands = sorted(zip(res.hand_landmarks, res.handedness), key=lambda h: h[1][0].category_name)
        for k, (lm, _hd) in enumerate(hands[:2]):
            p = np.array([[q.x, q.y] for q in lm], np.float32)
            lms.append(p)
            lo, hi = p.min(0), p.max(0)
            spread = float(np.linalg.norm(p[[4, 8, 12, 16, 20]] - p[0], axis=1).mean())
            feat[k * 6:(k + 1) * 6] = [1.0, *((lo + hi) / 2), *(hi - lo), spread]
        return feat, lms

    def close(self) -> None:
        self.det.close()


@lru_cache(maxsize=1)
def siglip() -> SigLIP:
    return SigLIP()


def bench(fn, n: int = 5) -> float:
    """median seconds per call"""
    fn()
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        if torch.backends.mps.is_available():
            torch.mps.synchronize()
        ts.append(time.perf_counter() - t0)
    return float(np.median(ts))

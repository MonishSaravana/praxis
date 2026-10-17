"""Shared plumbing for rented verifiers: image encoding, price table, response cache, budget guard."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import threading
from pathlib import Path

import numpy as np
from PIL import Image

from ..paths import CACHE

# USD per 1M tokens (input, output). Claude: claude-api skill table (cached 2026-10-06).
# Jev: docs.typesafe.ai/models ($0.042 / Mtok input, output free).
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-fable-5-1": (10.00, 50.00),
    "jev-1.14.0": (0.042, 0.0),
    "jev-1.13.0": (0.042, 0.0),
}


def cost_usd(model: str, in_tok: int, out_tok: int, cache_read: int = 0, cache_write: int = 0) -> float:
    pin, pout = PRICES.get(model, (0.0, 0.0))
    return (in_tok * pin + cache_write * pin * 1.25 + cache_read * pin * 0.1 + out_tok * pout) / 1e6


def to_jpeg(rgb: np.ndarray, max_side: int = 640, min_side: int = 0, quality: int = 85) -> bytes:
    im = Image.fromarray(rgb)
    w, h = im.size
    s = min(1.0, max_side / max(w, h))
    if min_side and min(w, h) * s < min_side:
        s = min_side / min(w, h)
    if s != 1.0:
        im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=quality, optimize=False, progressive=False)
    return buf.getvalue()


def b64(data: bytes) -> str:
    return base64.standard_b64encode(data).decode("ascii")


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    """Hard per-run cap on calls and spend, shared by every verifier in the process."""

    def __init__(self, max_calls: int, max_usd: float):
        self.max_calls, self.max_usd = max_calls, max_usd
        self.calls, self.usd = 0, 0.0
        self._lock = threading.Lock()

    def check(self) -> None:
        with self._lock:
            if self.calls >= self.max_calls or self.usd >= self.max_usd:
                raise BudgetExceeded(f"budget hit: {self.calls} calls, ${self.usd:.2f}")
            self.calls += 1

    def add(self, usd: float) -> None:
        with self._lock:
            self.usd += usd


class ResponseCache:
    """Content-addressed cache of raw API responses, so re-running an eval never re-spends.
    Cached hits are logged as such; latency metrics only use live (uncached) calls."""

    def __init__(self, name: str):
        self.dir = CACHE / "api" / name
        self.dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key(*parts) -> str:
        h = hashlib.sha256()
        for p in parts:
            h.update(p if isinstance(p, bytes) else json.dumps(p, sort_keys=True, default=str).encode())
        return h.hexdigest()[:32]

    def get(self, key: str) -> dict | None:
        f = self.dir / f"{key}.json"
        return json.loads(f.read_text()) if f.exists() else None

    def put(self, key: str, value: dict) -> None:
        (self.dir / f"{key}.json").write_text(json.dumps(value))


def stack_frames(frames: list[np.ndarray], height: int = 360) -> np.ndarray:
    """Side-by-side strip (used only for logging thumbnails)."""
    rs = []
    for f in frames:
        h, w = f.shape[:2]
        im = Image.fromarray(f).resize((round(w * height / h), height))
        rs.append(np.asarray(im))
    return np.concatenate(rs, 1)


def read_json_file(p: str | Path) -> dict:
    return json.loads(Path(p).read_text())

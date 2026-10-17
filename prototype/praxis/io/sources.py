"""L0 · Input (ours). Camera-agnostic frame sources.

Every downstream layer consumes `Frame` objects from a `FrameSource`; nothing above L0 knows
whether pixels came from a file, a webcam (e.g. an iPhone via Continuity Camera standing in for
a head-mounted view), or smart glasses.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Protocol

import cv2
import numpy as np


@dataclass
class Frame:
    t: float               # seconds since source start (media time for files, wall time for live)
    index: int             # index in the emitted stream (after fps resampling)
    rgb: np.ndarray        # HxWx3 uint8, RGB
    source_index: int = -1 # original frame index in the underlying stream


class FrameSource(Protocol):
    fps: float
    def __iter__(self) -> Iterator[Frame]: ...
    def close(self) -> None: ...


class FileSource:
    """Decode a video file, resampled to `fps`, optionally between [start, end) seconds."""

    def __init__(self, path: str | Path, fps: float = 4.0, start: float = 0.0,
                 end: float | None = None, max_side: int | None = 640):
        self.path = Path(path)
        self.fps = fps
        self.start, self.end = start, end
        self.max_side = max_side
        cap = cv2.VideoCapture(str(self.path))
        if not cap.isOpened():
            raise FileNotFoundError(self.path)
        self.native_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = self.n_frames / self.native_fps
        cap.release()

    def __iter__(self) -> Iterator[Frame]:
        cap = cv2.VideoCapture(str(self.path))
        end = self.end if self.end is not None else self.duration
        step = self.native_fps / self.fps
        first = int(round(self.start * self.native_fps))
        cap.set(cv2.CAP_PROP_POS_FRAMES, first)
        src_i, out_i, next_take = first, 0, float(first)
        try:
            while True:
                ok = cap.grab()
                if not ok:
                    break
                t = src_i / self.native_fps
                if t >= end:
                    break
                if src_i >= next_take - 1e-6:
                    ok, bgr = cap.retrieve()
                    if not ok:
                        break
                    yield Frame(t=t - self.start, index=out_i, rgb=_prep(bgr, self.max_side), source_index=src_i)
                    out_i += 1
                    next_take += step
                src_i += 1
        finally:
            cap.release()

    def close(self) -> None:
        pass


class WebcamSource:
    """Live camera (built-in, USB, or iPhone via Continuity Camera). Emits at most `fps` frames/s."""

    def __init__(self, device: int = 0, fps: float = 8.0, max_side: int | None = 640):
        self.device, self.fps, self.max_side = device, fps, max_side
        self.cap = cv2.VideoCapture(device)
        if not self.cap.isOpened():
            raise RuntimeError(f"camera {device} not available")

    def __iter__(self) -> Iterator[Frame]:
        t0 = time.perf_counter()
        i, period, last = 0, 1.0 / self.fps, -1e9
        while True:
            ok, bgr = self.cap.read()
            if not ok:
                break
            now = time.perf_counter() - t0
            if now - last < period:
                continue
            last = now
            yield Frame(t=now, index=i, rgb=_prep(bgr, self.max_side), source_index=i)
            i += 1

    def close(self) -> None:
        self.cap.release()


class MetaGlassesSource:
    """Stub. Smart-glasses camera adapter (see docs/GLASSES.md).

    Intended path: the glasses stream to a companion phone app via the vendor's device-access SDK;
    the phone forwards JPEG frames (+ timestamps) over a local socket to this process. Not tested on
    hardware, so it deliberately raises instead of pretending to work.
    """

    fps = 0.0

    def __init__(self, *args, **kwargs):
        raise NotImplementedError("MetaGlassesSource is a documented stub until tested on hardware; see docs/GLASSES.md")

    def __iter__(self) -> Iterator[Frame]:  # pragma: no cover
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover
        pass


def _prep(bgr: np.ndarray, max_side: int | None) -> np.ndarray:
    if max_side:
        h, w = bgr.shape[:2]
        s = max_side / max(h, w)
        if s < 1:
            bgr = cv2.resize(bgr, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    if bgr.ndim == 2:
        bgr = cv2.cvtColor(bgr, cv2.COLOR_GRAY2BGR)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def make_source(spec: str, **kw) -> FrameSource:
    """'webcam:0' | 'glasses:meta' | path/to/video.mp4"""
    if spec.startswith("webcam"):
        dev = int(spec.split(":")[1]) if ":" in spec else 0
        return WebcamSource(dev, **kw)
    if spec.startswith("glasses"):
        return MetaGlassesSource()
    return FileSource(spec, **kw)

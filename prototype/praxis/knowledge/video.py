"""Reference videos: a demonstration of a procedure -> one "what done looks like" keyframe per compiled step.

Local only ($0): sample the video every second, keep the sharpest frame per second (the drafter's sharpness
measure), embed frames with the SigLIP2 image tower, and align steps to time in order (dynamic programming: step i
comes after step i-1) by similarity to each step's embedded end-state text. The keyframe for a step is the
best-matching frame inside its aligned span. Untested on real maintenance video, so the admin page labels these
"auto-aligned, review" and a manager can clear any of them.
"""
from __future__ import annotations

import cv2
import numpy as np

from ..verify.common import sharpness
from .store import Org, now, write_json


def sample_frames(path, step_s: float = 1.0, max_side: int = 448, max_frames: int = 900):
    """(times, RGB frames): the sharpest of a few frames in each step_s window."""
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    dur = n / fps if n else 0
    step_s = max(step_s, dur / max_frames) if dur else step_s
    times, frames = [], []
    t = 0.0
    while t < dur:
        best, bt, bs = None, t, -1.0
        for dt in (0.0, step_s / 3, 2 * step_s / 3):
            cap.set(cv2.CAP_PROP_POS_MSEC, 1000 * (t + dt))
            ok, f = cap.read()
            if not ok:
                continue
            h, w = f.shape[:2]
            s = min(1.0, max_side / max(h, w))
            rgb = cv2.cvtColor(cv2.resize(f, (int(w * s), int(h * s))) if s < 1 else f, cv2.COLOR_BGR2RGB)
            sh = sharpness(rgb)
            if sh > bs:
                best, bt, bs = rgb, t + dt, sh
        if best is not None:
            times.append(round(bt, 2))
            frames.append(best)
        t += step_s
    cap.release()
    return times, frames


def align(sim: np.ndarray) -> list[tuple[int, int]]:
    """sim: (steps, frames). Monotonic segmentation of frames into len(steps) ordered spans maximizing the summed
    similarity of each frame to its step. Returns [(start, end_exclusive)] per step."""
    S, F = sim.shape
    if F < S:
        return [(min(i, F - 1), min(i, F - 1) + 1) for i in range(S)]
    cs = np.concatenate([np.zeros((S, 1)), np.cumsum(sim, 1)], 1)
    dp = np.full((S + 1, F + 1), -np.inf)
    back = np.zeros((S + 1, F + 1), dtype=int)
    dp[0, 0] = 0.0
    for i in range(1, S + 1):
        for j in range(i, F - (S - i) + 1):
            prev = dp[i - 1, i - 1:j] + (cs[i - 1, j] - cs[i - 1, i - 1:j])
            k = int(np.argmax(prev))
            dp[i, j], back[i, j] = prev[k], k + i - 1
    spans, j = [], F
    for i in range(S, 0, -1):
        k = back[i, j]
        spans.append((k, j))
        j = k
    return spans[::-1]


def reference_keyframes(org: Org, pid: str, v: int, video_hash: str, sig) -> dict:
    """Save one keyframe per step under the version's refs/ folder. sig: the SigLIP2 wrapper (images + texts)."""
    d = org.version_dir(pid, v)
    emb_p = d / "emb.npz"
    if not emb_p.exists():
        from .compile import embed_version
        embed_version(org, pid, v, sig)
    end = np.load(emb_p)["end_state"].astype(np.float32)
    times, frames = sample_frames(org.video_path(video_hash))
    if not frames:
        raise ValueError("could not read frames from the video")
    fe = np.asarray(sig.images(frames), np.float32)
    sim = end @ fe.T                                           # (steps, frames)
    spans = align(sim)
    from ..tasks.schema import TaskGraph
    g = TaskGraph.load(d / "graph.json")
    out_dir = d / "refs"
    out_dir.mkdir(parents=True, exist_ok=True)
    refs = {}
    for n, (a, b) in zip(g.nodes, spans):
        k = a + int(np.argmax(sim[g.ids.index(n.id), a:b]))
        cv2.imwrite(str(out_dir / f"{n.id}.jpg"), cv2.cvtColor(frames[k], cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
        refs[n.id] = {"t": times[k], "span_s": [times[a], times[b - 1]], "sim": round(float(sim[g.ids.index(n.id), k]), 4),
                      "video": video_hash, "file": f"{n.id}.jpg", "status": "auto-aligned, review"}
    meta = {"video": video_hash, "created": now(), "n_frames": len(frames), "refs": refs}
    write_json(out_dir / "refs.json", refs)
    write_json(out_dir / "meta.json", {k: x for k, x in meta.items() if k != "refs"})
    return refs

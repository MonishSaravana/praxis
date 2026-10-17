"""Routine verifier checks with ground truth: "is step k complete right now?" asked at known times.

For every annotated step segment (>= 6 s) we ask at two moments:
  mid  = segment midpoint                 -> GT complete = 0
  end  = 1.5 s after the annotated end    -> GT complete = 1
GT error = 1 when the dataset marks a (timed) error on that step.

Train-split checks fit calibration, tune policy thresholds and train the distilled student.
Eval-clip checks compare verifiers (Jev vs Claude), crops vs full frames, student vs teacher.
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass

import cv2
import numpy as np

from ..data.cc4d import Clip
from ..paths import DATA
from ..verify.schema import Verdict, VerifyRequest


@dataclass
class CheckItem:
    check_id: str
    clip_id: str
    task_id: str
    video: str
    t_abs: float          # seconds into the recording
    t_rel: float          # seconds into the clip
    node: str
    kind: str             # mid | end
    y_complete: int
    y_error: int
    error_tags: list[str]
    split: str


def build_checks(clips: list[Clip], min_seg_s: float = 6.0, max_per_clip: int = 24, seed: int = 0) -> list[CheckItem]:
    rng = np.random.default_rng(seed)
    out = []
    for c in clips:
        items = []
        for s in c.segments:
            if s.end - s.start < min_seg_s:
                continue
            tags = [e["tag"] for e in s.errors if e["tag"] != "Missing Step"]
            ye = int(bool(s.has_error and tags))
            mid = 0.5 * (s.start + s.end)
            items.append(CheckItem(f"{c.clip_id}:{s.step}:mid", c.clip_id, c.task_id, c.video, c.start + mid, mid, s.step, "mid", 0, ye, tags, c.split))
            te = s.end + 1.5
            if te < c.duration - 0.5:
                items.append(CheckItem(f"{c.clip_id}:{s.step}:end", c.clip_id, c.task_id, c.video, c.start + te, te, s.step, "end", 1, ye, tags, c.split))
        if len(items) > max_per_clip:
            items = [items[i] for i in sorted(rng.choice(len(items), max_per_clip, replace=False))]
        out += items
    return out


def frames_at(video: str, t_abs: float, n: int = 3, spacing: float = 1.0, max_side: int = 640) -> list[np.ndarray]:
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    out = []
    for k in reversed(range(n)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int((t_abs - k * spacing) * fps)))
        ok, bgr = cap.read()
        if not ok:
            continue
        h, w = bgr.shape[:2]
        s = min(1.0, max_side / max(h, w))
        if s < 1:
            bgr = cv2.resize(bgr, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
        out.append(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    cap.release()
    return out


def degrade(frames: list[np.ndarray], mode: str, seed: int = 0) -> list[np.ndarray]:
    """Visual-uncertainty test: remove the evidence the check needs."""
    rng = np.random.default_rng(seed)
    out = []
    for f in frames:
        h, w = f.shape[:2]
        g = f.copy()
        if mode == "blur":
            g = cv2.GaussianBlur(g, (0, 0), sigmaX=max(h, w) / 40)
        elif mode == "occlude":     # cover the central work area (where hands and parts usually are)
            g[int(h * 0.25):int(h * 0.95), int(w * 0.2):int(w * 0.8)] = (40, 40, 40)
        elif mode == "crop_away":   # look away: keep only a top corner strip, upscaled
            x0 = 0 if rng.random() < 0.5 else int(w * 0.6)
            g = cv2.resize(g[: int(h * 0.3), x0: x0 + int(w * 0.4)], (w, h), interpolation=cv2.INTER_LINEAR)
        out.append(g)
    return out


def run_verifier_on_checks(verifier, checks: list[CheckItem], library: dict, out_path, workers: int = 4,
                           crops_fn=None, degrade_mode: str | None = None, log_every: int = 25) -> list[dict]:
    """Ask `verifier` every check; write one JSON line per check with the verdict + GT."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = {}
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            r = json.loads(line)
            done[r["check_id"]] = r

    def one(ci: CheckItem) -> dict:
        if ci.check_id in done:
            return done[ci.check_id]
        g = library[ci.task_id]
        node = g.node(ci.node)
        frames = frames_at(ci.video, ci.t_abs)
        if degrade_mode:
            frames = degrade(frames, degrade_mode, seed=hash(ci.check_id) % 1000)
        crops = crops_fn(ci, frames) if crops_fn else []
        nxt = [n for n in node.successors]
        req = VerifyRequest(t=ci.t_rel, frames=frames, node=node, graph=g, checks=node.checks, crops=crops,
                            context={"frame_ages": [2.0, 1.0, 0.0][-len(frames):],
                                     "next_step": g.node(nxt[0]).name if nxt else None})
        v: Verdict = verifier.verify(req)
        return {**asdict(ci), "verdict": v.model_dump(), "n_crops": len(crops), "degrade": degrade_mode}

    rows = []
    t0 = time.time()
    with ThreadPoolExecutor(workers) as ex, out_path.open("a") as f:
        for i, r in enumerate(ex.map(one, checks)):
            if r["check_id"] not in done:
                f.write(json.dumps(r, default=str) + "\n")
                f.flush()
            rows.append(r)
            if log_every and (i + 1) % log_every == 0:
                print(f"  {i + 1}/{len(checks)} checks ({time.time() - t0:.0f}s)", flush=True)
    return rows


def save_checks(checks: list[CheckItem], name: str) -> None:
    p = DATA / "checks" / f"{name}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([asdict(c) for c in checks]))


def load_checks(name: str) -> list[CheckItem]:
    return [CheckItem(**d) for d in json.loads((DATA / "checks" / f"{name}.json").read_text())]

"""`praxis live`: the full engine on a live camera in real time.

FrameSource (webcam / Continuity Camera) -> L1 online (SigLIP2 + hands every frame, V-JEPA 2 every 2 s)
-> L2 on a rolling buffer -> Engine.tick each second -> spoken interventions (macOS `say`) + HUD.
Writes the JSONL run log and the raw camera video, so the session can be re-rendered (user/engineer view)
from the log afterwards, exactly like the offline clips.
"""
from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path

import cv2
import numpy as np

from .engine import Engine, EngineConfig
from .events.detector import ClipFeatures
from .io.sources import WebcamSource
from .paths import RUNS
from .perception.backbones import Hands, SigLIP, VJEPA2
from .perception.extract import ssim_small
from .runlog import RunLog


def say(text: str) -> None:
    subprocess.Popen(["say", "-r", "190", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_live(stack: dict, verifier=None, escalation=None, calibrator=None, dev_calibrator=None, task_id: str | None = None,
             device: int = 0, seconds: float = 120.0, name: str = "live", speak: bool = True,
             ecfg: EngineConfig | None = None) -> Path:
    out_dir = RUNS / name
    out_dir.mkdir(parents=True, exist_ok=True)
    log = RunLog(out_dir / "live.jsonl", {"mode": "live", "device": device, "task_id": task_id})
    src = WebcamSource(device, fps=4.0)
    sig, vj, hands = SigLIP(), VJEPA2(n_frames=8, size=224), Hands()
    eng = Engine(ecfg or EngineConfig(), stack["library"], stack["evidence"], stack["recognizer"], stack["detector"],
                 verifier, escalation, calibrator, dev_calibrator, log, task_id=task_id)
    spoken = 0
    writer = None
    buf_t, buf_rgb, buf_sig, buf_hand, buf_change, buf_win = [], [], [], [], [], []
    win = np.zeros(vj.dim, np.float32)
    lock = threading.Lock()

    def vjepa_job(frames):
        nonlocal win
        e = vj.clips([frames], batch=1)[0]
        with lock:
            win = e

    t_next_tick, t_next_win, job = 1.0, 2.0, None
    t_start = time.perf_counter()
    for fr in src:
        if fr.t > seconds:
            break
        if writer is None:
            h, w = fr.rgb.shape[:2]
            writer = cv2.VideoWriter(str(out_dir / "camera.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 4.0, (w, h))
        writer.write(cv2.cvtColor(fr.rgb, cv2.COLOR_RGB2BGR))
        buf_t.append(fr.t)
        buf_rgb.append(fr.rgb)
        buf_sig.append(sig.images([fr.rgb])[0])
        buf_hand.append(hands.frame(fr.rgb, fr.t)[0])
        buf_change.append(0.0 if len(buf_rgb) < 2 else 1 - ssim_small(buf_rgb[-2], buf_rgb[-1]))
        with lock:
            buf_win.append(win.copy())
        if fr.t >= t_next_win and len(buf_rgb) >= 8 and (job is None or not job.is_alive()):
            job = threading.Thread(target=vjepa_job, args=(buf_rgb[-8:],), daemon=True)
            job.start()
            t_next_win += 2.0
        if fr.t >= t_next_tick:
            f = ClipFeatures("live", np.array(buf_t), np.stack(buf_sig), np.stack(buf_hand), np.stack(buf_win), np.array(buf_change))
            sc = stack["detector"].score(f)
            m = (f.t > t_next_tick - 1.0) & (f.t <= t_next_tick)
            rows = {"t": f.t[m], "frame": f.frame[m], "window": f.window[m], "hands": f.hands[m],
                    "boundary": sc["boundary"][m], "grasp": sc["grasp"][m]}
            frames_t = np.array(buf_t)

            def frame_at(x):
                return buf_rgb[int(np.argmin(np.abs(frames_t - x)))]
            eng.tick(t_next_tick, rows, frame_at)
            log.flush()
            if speak:
                acts = [r for r in _actions(log)][spoken:]
                for a in acts:
                    if a["action"] in ("announce_task", "instruct", "mistake", "view_request", "hint", "done"):
                        say(a["text"])
                spoken += len(acts)
            t_next_tick += 1.0
            if len(buf_rgb) > 400:   # keep memory bounded (~100 s at 4 fps)
                for b in (buf_t, buf_rgb, buf_sig, buf_hand, buf_change, buf_win):
                    del b[:100]
    log.write("summary", time.perf_counter() - t_start, n_frames=eng.n_frames, escalated_frames=eng.n_escalated_frames,
              wall_s=time.perf_counter() - t_start)
    log.close()
    src.close()
    if writer:
        writer.release()
    return out_dir


def _actions(log: RunLog):
    import json
    with open(log.tmp_path if log.tmp_path.exists() else log.path) as f:
        for line in f:
            r = json.loads(line)
            if r["kind"] == "action":
                yield r

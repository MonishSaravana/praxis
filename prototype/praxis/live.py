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
from .io.sources import make_source
from .paths import RUNS
from .perception.backbones import Hands, SigLIP, VJEPA2
from .perception.extract import ssim_small
from .runlog import RunLog


def say(text: str) -> None:
    subprocess.Popen(["say", "-r", "190", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_live(stack: dict, verifier=None, escalation=None, calibrator=None, dev_calibrator=None, task_id: str | None = None,
             source: str = "webcam:0", seconds: float = 120.0, name: str = "live", speak: bool = True,
             ecfg: EngineConfig | None = None, calibrators: dict | None = None, localizer=None) -> Path:
    out_dir = RUNS / name
    out_dir.mkdir(parents=True, exist_ok=True)
    log = RunLog(out_dir / "live.jsonl", {"mode": "live", "source": source, "task_id": task_id,
                                          "verifier": getattr(verifier, "model", None),
                                          "escalation": getattr(escalation, "model", None)})
    src = make_source(source, fps=4.0)
    sig, vj, hands = SigLIP(), VJEPA2(n_frames=8, size=224), Hands()
    if stack.get("recognizer") is not None:
        stack["recognizer"].reset()
    eng = Engine(ecfg or EngineConfig(), stack["library"], stack["evidence"], None if task_id else stack["recognizer"],
                 stack["detector"], verifier, escalation, calibrator, dev_calibrator, log, task_id=task_id,
                 calibrators=calibrators, localizer=localizer)
    frame_ms, tick_ms, lags = [], [], []
    last_index = -1
    spoken = 0
    writer = None
    buf_t, buf_rgb, buf_sig, buf_hand, buf_change, buf_win = [], [], [], [], [], []
    win = np.zeros(vj.dim, np.float32)
    lock = threading.Lock()

    gpu = threading.Lock()     # MPS is not safe to encode from two threads at once (Metal assertion otherwise)

    def vjepa_job(frames):
        nonlocal win
        with gpu:
            e = vj.clips([frames], batch=1)[0]
        with lock:
            win = e

    t_next_tick, t_next_win, job = 1.0, 2.0, None
    t_start = time.perf_counter()
    for fr in src:
        if fr.t > seconds:
            break
        f0 = time.perf_counter()
        if writer is None:
            h, w = fr.rgb.shape[:2]
            writer = cv2.VideoWriter(str(out_dir / "camera.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 4.0, (w, h))
        bgr = cv2.cvtColor(fr.rgb, cv2.COLOR_RGB2BGR)
        for _ in range(max(1, fr.index - last_index)):    # repeat the frame over dropped slots: keeps a 4 fps timeline
            writer.write(bgr)
        last_index = fr.index
        buf_t.append(fr.t)
        buf_rgb.append(fr.rgb)
        with gpu:
            buf_sig.append(sig.images([fr.rgb])[0])
        buf_hand.append(hands.frame(fr.rgb, fr.t)[0])
        buf_change.append(0.0 if len(buf_rgb) < 2 else 1 - ssim_small(buf_rgb[-2], buf_rgb[-1]))
        with lock:
            buf_win.append(win.copy())
        if fr.t >= t_next_win and len(buf_rgb) >= 8 and (job is None or not job.is_alive()):
            job = threading.Thread(target=vjepa_job, args=(buf_rgb[-8:],), daemon=True)
            job.start()
            t_next_win += 1.0          # 1 Hz over the trailing 2 s, as in offline extraction
        frame_ms.append(1000 * (time.perf_counter() - f0))
        if fr.t >= t_next_tick:
            k0 = time.perf_counter()
            f = ClipFeatures("live", np.array(buf_t), np.stack(buf_sig), np.stack(buf_hand), np.stack(buf_win), np.array(buf_change))
            sc = stack["detector"].score(f)
            m = (f.t > t_next_tick - 1.0) & (f.t <= t_next_tick)
            rows = {"t": f.t[m], "frame": f.frame[m], "window": f.window[m], "hands": f.hands[m],
                    "boundary": sc["boundary"][m], "grasp": sc["grasp"][m]}
            frames_t = np.array(buf_t)

            def frame_at(x):
                return buf_rgb[int(np.argmin(np.abs(frames_t - x)))]
            eng.tick(t_next_tick, rows, frame_at)
            tick_ms.append(1000 * (time.perf_counter() - k0))
            lags.append((time.perf_counter() - t_start) - t_next_tick)    # how far behind the camera the tick finished
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
    def pq(x):
        return {"p50": float(np.percentile(x, 50)), "p95": float(np.percentile(x, 95)), "max": float(np.max(x))} if x else None
    log.write("summary", time.perf_counter() - t_start, n_frames=eng.n_frames, escalated_frames=eng.n_escalated_frames,
              wall_s=time.perf_counter() - t_start, frames_processed=len(frame_ms),
              dropped_frames=getattr(src, "dropped", None), l1_frame_ms=pq(frame_ms), tick_ms=pq(tick_ms),
              tick_lag_s=pq(lags), n_ticks=len(tick_ms))
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


def summarize(name: str) -> dict:
    """results/live/<name>.json from the saved live log: loop timing, dropped frames, what Praxis said, spend."""
    import json
    from .paths import RESULTS
    recs = [json.loads(l) for l in (RUNS / name / "live.jsonl").read_text().splitlines() if l.strip()]
    meta = next((r for r in recs if r["kind"] == "meta"), {})
    summ = [r for r in recs if r["kind"] == "summary"]
    ver = [r for r in recs if r["kind"] in ("verdict", "step_choice", "task_check")]
    from .paths import ROOT
    src_ = (meta.get("source") or "").replace(str(ROOT) + "/", "")
    out = {"name": name, "source": src_, "task_given": meta.get("task_id"),
           "summary": {k: v for k, v in (summ[-1] if summ else {}).items() if k not in ("kind", "wall")},
           "task_recognized": [{"t": r["t"], "task_id": r.get("task_id"), "title": r.get("title")} for r in recs
                               if r["kind"] == "task"],
           "actions": [{"t": r["t"], "action": r["action"], "text": r["text"]} for r in recs if r["kind"] == "action"],
           "model_calls": len(ver), "slowest_call_ms": max((r.get("latency_ms") or 0) for r in ver) if ver else None,
           "spend_usd": sum((r.get("cost_usd") or 0.0) for r in ver if not r.get("cached"))}
    (RESULTS / "live").mkdir(parents=True, exist_ok=True)
    (RESULTS / "live" / f"{name}.json").write_text(json.dumps(out, indent=2))
    return out


def render_replay(name: str, clip_id: str, t0: float, t1: float, view: str = "user") -> Path:
    """Render a replayed live session from its log over the source recording (replay time = media time - start)."""
    from .data.cc4d import Clip, load_manifest
    from .paths import RENDERS
    from .render.hud import render
    from .tasks.compiler import load_library
    c = [Clip.from_json(x) for x in load_manifest()["eval"] if x["clip_id"] == clip_id][0]
    names = {n.id: n.name for n in load_library()[c.task_id].nodes}
    out = RENDERS / f"live_replay_{view}.mp4"
    render(RUNS / name / "live.jsonl", c.video, out, view=view, start=c.start, t0=t0, t1=t1, dataset="CaptainCook4D",
           gt=[(s.start, s.end, s.step) for s in c.segments] if view == "user" else None, step_names=names,
           label="real model output · live mode on a recording replayed in real time (not a webcam)", end_seconds=2.5,
           crf=30)
    return out


def main(argv: list[str] | None = None) -> Path:
    """python -m praxis.live --source webcam:0 | replay:path.mp4@start_s  [--task ID] [--seconds N] [--no-speak]"""
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Run the full engine live on a camera, or on a recorded video replayed "
                                             "at wall-clock speed (frames the loop is too slow for are dropped).")
    ap.add_argument("--source", default="webcam:0")
    ap.add_argument("--task", default=None, help="task id; omit to let Praxis recognize the task")
    ap.add_argument("--seconds", type=float, default=120.0)
    ap.add_argument("--name", default="live")
    ap.add_argument("--no-speak", action="store_true")
    ap.add_argument("--no-verifier", action="store_true", help="local layers only (no API calls)")
    a = ap.parse_args(argv)
    from .eval import harness
    from .eval.run_all import calibrators, engine_config
    from .experiments import _budget, make_verifier
    from .paths import load_env
    load_env()
    stack = harness.load_stack()
    budget = _budget(300, 3.0)
    ver = None if a.no_verifier else make_verifier("jev", budget)
    esc = None if a.no_verifier else make_verifier("claude_strong", budget)
    cals = {"primary": calibrators(None if a.no_verifier else "jev"),
            "escalation": calibrators(None if a.no_verifier else "claude_strong")}
    out = run_live(stack, ver, esc, task_id=a.task, source=a.source, seconds=a.seconds, name=a.name,
                   speak=not a.no_speak, ecfg=engine_config({} if not a.no_verifier else {"use_verifier": False}),
                   calibrators=cals)
    res = summarize(a.name)
    print(json.dumps({"run_dir": str(out), "spend_usd": budget.usd, "summary": res["summary"]}, indent=1))
    return out


if __name__ == "__main__":
    main()

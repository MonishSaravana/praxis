"""One Studio session: frames from the browser -> the live engine (async slow path, never waiting on the network) ->
every run-log record streamed back to the browser as it is written.

The browser sends JPEG frames with their session time (camera: wall clock since start; upload: media time). The
engine runs at its evaluated 4 fps cadence; every received frame is also recorded to an H.264 MP4 on a fixed-rate
timeline (video time = session time), so the log lines up with it for replay and for the HUD render.
Nothing is kept unless the person presses Save: until then the session lives in sessions/.pending/<id>/.
"""
from __future__ import annotations

import json
import queue
import re
import shutil
import subprocess
import threading
import time
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from ..live import LiveRunner, _pq
from ..runlog import RunLog
from ..verify.common import Budget
from .core import SESSIONS, StudioCore, write_json

HEAVY = {"raw", "evidence", "frames", "thumb", "crops", "image", "posterior_raw"}
ENGINE_DT = 0.25            # the engine's evaluated 4 fps cadence
ASK_AFTER_S, ASK_LATEST_S = 30.0, 60.0


class Recorder:
    """Received frames -> H.264 MP4 at a fixed rate; gaps are filled with the previous frame."""

    def __init__(self, path: Path, fps: float = 8.0, max_w: int = 1280):
        self.path, self.fps, self.max_w = Path(path), fps, max_w
        self.proc, self.size, self.n, self.last = None, None, 0, None

    def add(self, t: float, bgr: np.ndarray) -> None:
        if self.proc is None:
            h, w = bgr.shape[:2]
            s = min(1.0, self.max_w / w)
            self.size = (int(w * s) // 2 * 2, int(h * s) // 2 * 2)
            self.proc = subprocess.Popen(
                ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s",
                 f"{self.size[0]}x{self.size[1]}", "-r", str(self.fps), "-i", "-", "-c:v", "libx264", "-preset",
                 "veryfast", "-crf", "24", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(self.path)],
                stdin=subprocess.PIPE)
        if (bgr.shape[1], bgr.shape[0]) != self.size:
            bgr = cv2.resize(bgr, self.size, interpolation=cv2.INTER_AREA)
        target = int(t * self.fps)
        try:
            while self.n < target:
                self.proc.stdin.write((self.last if self.last is not None else bgr).tobytes())
                self.n += 1
            if self.n == target:
                self.proc.stdin.write(bgr.tobytes())
                self.n += 1
        except (BrokenPipeError, ValueError):
            return
        self.last = bgr

    def close(self) -> None:
        if self.proc is not None:
            try:
                self.proc.stdin.close()
                self.proc.wait(timeout=120)
            except Exception:  # noqa: BLE001
                self.proc.kill()


class StudioSession:
    def __init__(self, core: StudioCore, cfg: dict, send):
        from ..engine import Engine
        from ..eval.run_all import calibrators
        from ..experiments import make_verifier
        self.core, self.cfg, self.send = core, cfg, send
        self.id = time.strftime("%Y%m%d_%H%M%S")
        self.dir = SESSIONS / ".pending" / self.id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.cap = float(cfg.get("cost_cap") or 1.0)
        self.budget = Budget(1_000_000, self.cap)
        self.use_opus = bool(cfg.get("escalation", True))
        ver = make_verifier("jev", self.budget)
        esc = make_verifier("claude_strong", self.budget) if self.use_opus else None
        cals = {"primary": calibrators("jev"), "escalation": calibrators("claude_strong" if self.use_opus else None)}
        self.stack = core.session_stack()
        self.models = {"fast": ver.model, "escalation": esc.model if esc else None}
        # status tracked from the records as they are written
        self.task_info: dict | None = None
        self.model_state = {"fast": "ok", "strong": "ok" if self.use_opus else "off"}
        self.err_streak = Counter()
        self.last_error = None
        self.cap_hit = False
        self.none_streak = 0
        self.asked = False
        self.draft_cost = 0.0
        self.flags: list[dict] = []
        self.t_last = 0.0
        self.stats = Counter()
        self.proc_lag: list[float] = []
        self.log = RunLog(self.dir / "live.jsonl",
                          {"mode": "studio", "session": self.id, "input": cfg.get("input"),
                           "source": cfg.get("source_label"), "task_mode": cfg.get("task_mode"),
                           "verifier": self.models["fast"], "escalation": self.models["escalation"],
                           "cost_cap_usd": self.cap, "label": "Praxis prototype v0 · real model output"},
                          listener=self._on_line)
        from ..landmarks import TextCache
        self.eng = Engine(core.engine_config(escalate=self.use_opus), self.stack["library"], self.stack["evidence"],
                          self.stack["recognizer"], self.stack["detector"], ver, esc, log=self.log, calibrators=cals,
                          offtask=self.stack.get("offtask"), texts=TextCache(core.texts().texts))
        self.runner = LiveRunner(self.stack, self.eng, core.encoders())
        self.rec = Recorder(self.dir / "camera.mp4")
        self._apply_task_choice()
        self.mail, self.mail_lock, self.wake = None, threading.Lock(), threading.Event()
        self.cmds: queue.Queue = queue.Queue()
        self.running, self.stopped = True, False
        self.t_start = time.time()
        self.thread = threading.Thread(target=self._loop, daemon=True, name=f"studio-{self.id}")
        self.thread.start()

    # ---------------------------------------------------------------- task choice
    def _drafter(self, hint: str):
        from ..tasks.drafter import Drafter
        enc = self.core.encoders()
        return Drafter(siglip=enc.sig, hint=hint, gpu_lock=enc.gpu)

    def _apply_task_choice(self) -> None:
        mode = self.cfg.get("task_mode", "auto")
        if mode in ("library", "paste") and self.cfg.get("task_id"):
            self.eng.start_task(0.0, self.cfg["task_id"], how="picked" if mode == "library" else "pasted")
        elif mode == "describe" and (self.cfg.get("description") or "").strip():
            self._describe(self.cfg["description"].strip(), t=0.0, at_s=4.0)

    def _describe(self, text: str, t: float, at_s: float = 0.0) -> None:
        from .tasks import match_library
        m = match_library(text, self.core.library())
        self.log.write("described", t, text=text, matched=m)
        if m:
            self.eng.start_task(t, m, how="described")
        else:
            self.eng.request_draft(self._drafter(text), at_s=at_s)

    # ---------------------------------------------------------------- browser -> session (any thread)
    def push_frame(self, t: float, jpeg: bytes) -> None:
        with self.mail_lock:
            if self.mail is not None:
                self.stats["replaced_before_processing"] += 1
            self.mail = (t, jpeg, time.perf_counter())
        self.stats["frames_in"] += 1
        self.wake.set()

    def flag(self, kind: str, note: str, t: float) -> None:
        self.cmds.put(("flag", kind, note, t))
        self.wake.set()

    def describe(self, text: str) -> None:
        self.cmds.put(("describe", text))
        self.wake.set()

    def task_answer(self, task_id: str, answer: str) -> None:
        self.cmds.put(("answer", task_id, answer, "tap"))
        self.wake.set()

    # ---------------------------------------------------------------- the session thread
    def _loop(self) -> None:
        next_slot = 0.0
        last_status = 0.0
        while self.running:
            self.wake.wait(timeout=0.5)
            self.wake.clear()
            try:
                while not self.cmds.empty():
                    self._do(self.cmds.get_nowait())
                with self.mail_lock:
                    item, self.mail = self.mail, None
                if item is not None:
                    t, jpeg, arrived = item
                    if t + 1e-6 < self.t_last:          # out of order: ignore
                        continue
                    bgr = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
                    if bgr is None:
                        continue
                    self.rec.add(t, bgr)
                    self.t_last = t
                    if t + 1e-6 >= next_slot:
                        while next_slot <= t + 1e-6:
                            next_slot += ENGINE_DT
                        h, w = bgr.shape[:2]
                        s = min(1.0, 640 / max(h, w))
                        small = cv2.resize(bgr, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA) if s < 1 else bgr
                        _, tick_t = self.runner.push(t, cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
                        self.stats["frames_engine"] += 1
                        if tick_t is not None:
                            self.proc_lag.append(time.perf_counter() - arrived)
                self._maybe_ask()
            except Exception as e:  # noqa: BLE001
                self.stats["errors"] += 1
                self.send({"type": "error", "message": f"engine: {e}"[:300]})
            now = time.time()
            if now - last_status >= 1.0:
                last_status = now
                self.send(self.status())

    def _do(self, cmd) -> None:
        if cmd[0] == "flag":
            _, kind, note, t = cmd
            f = {"t": round(float(t), 2), "kind": kind, "note": (note or "")[:300]}
            self.flags.append(f)
            self.log.write("flag", t, flag=kind, note=f["note"])
        elif cmd[0] == "describe":
            ans = self._typed_answer(cmd[1])
            if ans:                                     # "I'm done" / "coming back" to a pending "Coming back to ...?"
                self.eng.answer_resume(self.t_last, ans[0], ans[1], via="typed")
            else:
                self._describe(cmd[1], t=self.t_last)
        elif cmd[0] == "answer":
            self.eng.answer_resume(self.t_last, cmd[1], cmd[2], via=cmd[3])

    def _typed_answer(self, text: str) -> tuple[str, str] | None:
        """A short typed reply to the latest unanswered "Coming back to ...?" (multi-task)."""
        asked = [sl for sl in getattr(self.eng, "tasks", {}).values()
                 if sl.status == "paused" and sl.asked_at is not None and sl.answer is None]
        if not asked or len(text.split()) > 6:
            return None
        sl = max(asked, key=lambda x: x.asked_at)
        t = text.lower()
        if re.search(r"\b(done|finished|not coming back|no|nope|skip it|that's it)\b", t):
            return sl.task_id, "done"
        if re.search(r"\b(coming back|back later|later|yes|yeah|yep|will finish|not done)\b", t):
            return sl.task_id, "coming_back"
        return None

    def _maybe_ask(self) -> None:
        """Auto mode with an unknown task: ask what the person is doing instead of guessing (video-only drafts named
        0 of 7 unseen recipes; with the person's description, 5 of 7: results/open_set/)."""
        if (self.cfg.get("task_mode", "auto") == "auto" and not self.asked and self.eng.graph is None
                and self.t_last >= ASK_AFTER_S and (self.none_streak >= 2 or self.t_last >= ASK_LATEST_S)):
            self.asked = True
            self.log.write("ask_task", self.t_last)
            self.send({"type": "ask_task", "t": self.t_last})

    # ---------------------------------------------------------------- records -> browser
    def _on_line(self, line: str) -> None:
        r = json.loads(line)
        k = r["kind"]
        if k in ("verdict", "step_choice", "task_check", "task_draft"):
            role = "draft" if k == "task_draft" else (r.get("role") or ("strong" if r.get("reason") == "escalation" else "fast"))
            if r.get("error"):
                if "budget hit" in r["error"]:
                    self.cap_hit = True
                else:
                    self.err_streak[role] += 1
                    self.last_error = r["error"][:160]
                    if role in self.model_state and self.err_streak[role] >= 2:
                        self.model_state[role] = "offline"
            else:
                self.err_streak[role] = 0
                if role in self.model_state:
                    self.model_state[role] = "ok"
                if k == "task_draft" and not r.get("cached") and r.get("cost_usd"):
                    self.draft_cost += r["cost_usd"]
                    self.budget.add(r["cost_usd"])          # the session cap covers drafts too
            if k == "task_check" and not r.get("error"):
                self.none_streak = self.none_streak + 1 if r.get("choice") not in self.eng.lib else 0
        if k == "task":
            g = self.eng.lib.get(r["task_id"])
            # a drafted plan's step order is a guess (one straight line), so don't warn about skipped steps
            self.eng.cfg.order_check = not bool(getattr(g, "draft", False))
            self.task_info = {"task_id": r["task_id"], "title": r.get("title"), "t": r["t"],
                              "draft": bool(getattr(g, "draft", False)), "oracle": r.get("oracle")}
            if g is not None:
                self.send({"type": "graph", "task_id": g.task_id, "title": g.title, "draft": g.draft,
                           "nodes": [{"id": n.id, "name": n.name} for n in g.nodes]})
        if k == "task_state" and r.get("to") == "active" and (r.get("evidence") or {}).get("how") != "came_back":
            g = self.eng.lib.get(r["task_id"])            # multi-task: a paused task is current again
            if g is not None:
                self.task_info = {"task_id": r["task_id"], "title": g.title, "t": r["t"], "draft": bool(g.draft),
                                  "oracle": False, "how": "resumed"}
                self.send({"type": "graph", "task_id": g.task_id, "title": g.title, "draft": g.draft,
                           "nodes": [{"id": n.id, "name": n.name} for n in g.nodes]})
        if k == "action" and r.get("action") == "announce_task" and self.task_info is not None:
            self.task_info["how"] = (r.get("detail") or {}).get("how") or ("drafted" if self.task_info["draft"] else "recognized")
        self.send({"type": "rec", "r": {kk: v for kk, v in r.items() if kk not in HEAVY}})

    def status(self) -> dict:
        return {"type": "status", "session": self.id, "t": round(self.t_last, 2),
                "cost_usd": round(self.budget.usd, 4), "cost_cap_usd": self.cap,
                "cap_hit": self.cap_hit, "models": self.model_state, "last_error": self.last_error,
                "calls": self.budget.calls, "task": self.task_info,
                "frames_in": self.stats["frames_in"], "frames_engine": self.stats["frames_engine"],
                "replaced": self.stats["replaced_before_processing"],
                "lag_s": round(self.proc_lag[-1], 3) if self.proc_lag else None,
                "pending_calls": len(getattr(self.eng, "_jobs", []))}

    # ---------------------------------------------------------------- end
    def stop(self) -> dict:
        if self.stopped:
            return self.end_summary
        self.running = False
        self.wake.set()
        self.thread.join(timeout=30)
        self.runner.finish(self.t_last, timeout_s=8.0)
        self.eng.finish(self.t_last)                    # tasks still paused are closed as done enough (session end)
        self.log.write("summary", self.t_last, wall_s=round(time.time() - self.t_start, 2),
                       frames_in=self.stats["frames_in"], frames_engine=self.stats["frames_engine"],
                       replaced_before_processing=self.stats["replaced_before_processing"],
                       l1_frame_ms=_pq(self.runner.frame_ms), tick_ms=_pq(self.runner.tick_ms),
                       proc_lag_s=_pq(self.proc_lag), verifier_spend_usd=round(self.budget.usd - self.draft_cost, 5),
                       draft_spend_usd=round(self.draft_cost, 5), cost_cap_usd=self.cap, cap_hit=self.cap_hit,
                       async_stats=dict(self.eng.async_stats), flags=len(self.flags))
        self.log.close()
        self.rec.close()
        self.stopped = True
        acts = Counter()
        for line in (self.dir / "live.jsonl").read_text().splitlines():
            r = json.loads(line)
            if r["kind"] == "action":
                acts[r["action"]] += 1
        self.end_summary = {"type": "stopped", "session": self.id, "duration_s": round(self.t_last, 1),
                            "task": self.task_info, "actions": dict(acts), "flags": len(self.flags),
                            "cost_usd": round(self.budget.usd, 4)}
        return self.end_summary

    def save(self) -> str:
        from .summary import write_summary
        if not self.stopped:
            self.stop()
        title = (self.task_info or {}).get("title") or "no-task"
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "session"
        dest = SESSIONS / f"{self.id}_{slug}"
        shutil.move(str(self.dir), str(dest))
        g = self.eng.lib.get((self.task_info or {}).get("task_id")) if self.task_info else None
        if g is not None:
            g.save(dest / "taskgraph.json")
        write_json(dest / "flags.json", self.flags)
        write_json(dest / "config.json", {**{k: v for k, v in self.cfg.items() if k != "description_raw"},
                                          "models": self.models, "engine": "async live loop (praxis.live.LiveRunner)",
                                          "engine_fps": 1 / ENGINE_DT, "record_fps": self.rec.fps})
        write_json(dest / "cost.json", {"verifier_usd": round(self.budget.usd - self.draft_cost, 5),
                                        "draft_usd": round(self.draft_cost, 5),
                                        "compile_usd": self.cfg.get("compile_cost_usd", 0.0),
                                        "calls": self.budget.calls, "cap_usd": self.cap, "cap_hit": self.cap_hit})
        write_summary(dest, self.cfg, self.task_info, g)
        threading.Thread(target=_render_replay, args=(dest, g), daemon=True).start()
        return dest.name

    def discard(self) -> None:
        if not self.stopped:
            self.stop()
        shutil.rmtree(self.dir, ignore_errors=True)


def _render_replay(dest: Path, g) -> None:
    """HUD replay MP4 of a saved session with the existing renderer, drawn only from its run log."""
    from ..render.hud import render
    meta_p = dest / "session.json"
    meta = json.loads(meta_p.read_text())
    meta["replay"] = {"status": "rendering"}
    write_json(meta_p, meta)
    try:
        names = {n.id: n.name for n in g.nodes} if g is not None else None
        render(dest / "live.jsonl", dest / "camera.mp4", dest / "hud_replay.mp4", view="user", start=0.0, t0=0.0,
               dataset="Praxis Studio", step_names=names, label="real model output", crf=28)
        meta["replay"] = {"status": "ready", "file": "hud_replay.mp4"}
    except Exception as e:  # noqa: BLE001
        meta["replay"] = {"status": "error", "error": str(e)[:300]}
    write_json(meta_p, meta)

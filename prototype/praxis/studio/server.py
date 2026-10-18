"""Praxis Studio web server (FastAPI + one websocket per live session). Local only: binds to 127.0.0.1.

WebSocket /ws protocol
  browser -> server  text  {"type": "start", ...config} | {"type": "flag", "kind": "wrong"|"missed", "note", "t"}
                           | {"type": "task_answer", "task_id", "answer": "coming_back"|"done"}
                           {"type": "describe", "text"} | {"type": "stop"} | {"type": "save"} | {"type": "discard"}
                     bytes 8-byte little-endian float64 session time + one JPEG frame
  server -> browser  {"type": "started"|"graph"|"rec"|"status"|"ask_task"|"stopped"|"saved"|"discarded"|"error", ...}
Closing the tab before Save discards the session (saving is never automatic).
"""
from __future__ import annotations

import asyncio
import json
import re
import struct
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .core import SESSIONS, StudioCore

STATIC = Path(__file__).parent / "static"
app = FastAPI(title="Praxis Studio")
LABEL = "Praxis prototype v0 · real model output"
app.mount("/static", StaticFiles(directory=STATIC), name="static")
from .org_api import router as org_router  # noqa: E402  company profiles, uploads, admin page (studio/org_api.py)
app.include_router(org_router)
CORE: StudioCore | None = None
JOBS: dict = {}
SESSION_FILES = {"camera.mp4", "hud_replay.mp4", "SUMMARY.md", "live.jsonl", "taskgraph.json", "flags.json",
                 "config.json", "cost.json", "session.json"}


def core() -> StudioCore:
    global CORE
    if CORE is None:
        CORE = StudioCore()
    return CORE


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/status")
def status():
    c = core()
    return {"models": c.model_status(), "library": c.library(), "clips": c.dev_clips(),
            "defaults": {"cost_cap": 1.0, "escalation": True, "speech": True},
            "label": LABEL}


@app.post("/api/compile")
async def compile_instructions(body: dict):
    from .tasks import CompileJob
    text = (body.get("text") or "").strip()
    if len(text) < 20:
        raise HTTPException(400, "Paste the steps, recipe or manual text (at least a sentence or two).")
    job = CompileJob(core(), text, effort=body.get("effort", "medium"))
    JOBS[job.id] = job
    return job.status()


@app.get("/api/compile/{job_id}")
def compile_status(job_id: str):
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    return job.status()


# ------------------------------------------------------------------------------------------ saved sessions
def _session_dir(sid: str) -> Path:
    if not re.fullmatch(r"[0-9A-Za-z_\-]+", sid):
        raise HTTPException(400, "bad session id")
    d = SESSIONS / sid
    if not (d / "session.json").exists():
        raise HTTPException(404, "no such session")
    return d


@app.get("/api/sessions")
def sessions():
    out = []
    if SESSIONS.exists():
        for d in sorted(SESSIONS.iterdir(), reverse=True):
            p = d / "session.json"
            if d.is_dir() and not d.name.startswith(".") and p.exists():
                out.append(json.loads(p.read_text()))
    return out


@app.get("/api/sessions/{sid}")
def session_detail(sid: str):
    from .session import HEAVY
    d = _session_dir(sid)
    recs = []
    for line in (d / "live.jsonl").read_text().splitlines():
        r = json.loads(line)
        recs.append({k: v for k, v in r.items() if k not in HEAVY})
    graph = json.loads((d / "taskgraph.json").read_text()) if (d / "taskgraph.json").exists() else None
    nodes = [{"id": n["id"], "name": n["name"]} for n in graph["nodes"]] if graph else []
    return {"session": json.loads((d / "session.json").read_text()), "records": recs, "nodes": nodes,
            "graph_title": graph["title"] if graph else None,
            "flags": json.loads((d / "flags.json").read_text()) if (d / "flags.json").exists() else []}


@app.get("/files/{sid}/{name}")
def session_file(sid: str, name: str):
    d = _session_dir(sid)
    if name not in SESSION_FILES or not (d / name).exists():
        raise HTTPException(404, "no such file")
    if name.endswith(".md"):
        return PlainTextResponse((d / name).read_text())
    return FileResponse(d / name)


@app.get("/dev/video/{clip_id}")
def dev_video(clip_id: str):
    """Local CaptainCook4D recordings, to test the upload path without a file dialog."""
    p = core().dev_video(clip_id)
    if p is None:
        raise HTTPException(404, "clip not on this machine")
    return FileResponse(p, media_type="video/mp4")


# ------------------------------------------------------------------------------------------ live sessions
@app.websocket("/ws")
async def ws_live(ws: WebSocket):
    from .session import StudioSession
    await ws.accept()
    loop = asyncio.get_running_loop()
    out: asyncio.Queue = asyncio.Queue()

    def send(msg):                      # from any thread
        loop.call_soon_threadsafe(out.put_nowait, msg)

    async def sender():
        while True:
            msg = await out.get()
            await ws.send_text(msg if isinstance(msg, str) else json.dumps(msg, default=str))

    task = asyncio.create_task(sender())
    sess: StudioSession | None = None
    saved = False
    try:
        while True:
            m = await ws.receive()
            if m["type"] == "websocket.disconnect":
                break
            if m.get("bytes") is not None:
                b = m["bytes"]
                if sess is not None and not sess.stopped and len(b) > 8:
                    sess.push_frame(struct.unpack("<d", b[:8])[0], b[8:])
                continue
            msg = json.loads(m.get("text") or "{}")
            kind = msg.get("type")
            if kind == "start":
                if sess is not None and not sess.stopped:
                    await loop.run_in_executor(None, sess.discard)
                cfg = {k: v for k, v in msg.items() if k != "type"}
                if cfg.get("task_mode") == "paste" and cfg.get("job_id") in JOBS:
                    js = JOBS[cfg["job_id"]].status()
                    cfg["task_id"], cfg["compile_cost_usd"] = js["task_id"], js["cost_usd"]
                try:
                    if cfg.get("org_id"):           # a company profile: its approved procedures, locked mode
                        from .org_session import OrgStudioSession as Session
                    else:
                        Session = StudioSession
                    sess = await loop.run_in_executor(None, lambda: Session(core(), cfg, send))
                    saved = False
                    send({"type": "started", "session": sess.id, "models": sess.models, "cost_cap_usd": sess.cap})
                except Exception as e:  # noqa: BLE001
                    send({"type": "error", "message": f"could not start: {e}"[:300]})
            elif sess is None:
                continue
            elif kind == "flag":
                sess.flag(msg.get("kind", "wrong"), msg.get("note", ""), float(msg.get("t", sess.t_last)))
            elif kind == "describe":
                sess.describe((msg.get("text") or "").strip())
            elif kind == "task_answer":                  # tap on a paused-task chip: "Coming back" / "I'm done"
                sess.task_answer(str(msg.get("task_id") or ""), str(msg.get("answer") or ""))
            elif kind == "stop":
                send(await loop.run_in_executor(None, sess.stop))
            elif kind == "save":
                sid = await loop.run_in_executor(None, sess.save)
                saved = True
                send({"type": "saved", "id": sid})
            elif kind == "discard":
                await loop.run_in_executor(None, sess.discard)
                send({"type": "discarded"})
                sess = None
    except WebSocketDisconnect:
        pass
    finally:
        if sess is not None and not saved:
            await loop.run_in_executor(None, sess.discard)      # closing the tab never saves
        await asyncio.sleep(0.05)
        task.cancel()


def main(port: int = 8800, open_browser: bool = True) -> None:
    import threading
    import webbrowser

    import uvicorn
    print("Praxis Studio: loading the engine and models (about 20 s)...", flush=True)
    core()
    url = f"http://127.0.0.1:{port}"
    print(f"Praxis Studio ready: {url}", flush=True)
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning", ws_max_size=16 * 1024 * 1024)


if __name__ == "__main__":
    main()

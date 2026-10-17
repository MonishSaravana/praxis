"""SUMMARY.md and session.json for a saved Studio session, built only from its run log, flags and config, so Claude
(or anyone) can review what happened quickly. Each flag gets its context: what Praxis believed, said and asked around
that moment."""
from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

from ..runlog import by_kind, read_log
from .core import write_json


def _fmt_t(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:04.1f}"


def write_summary(dest: Path, cfg: dict, task: dict | None, graph) -> dict:
    recs = read_log(dest / "live.jsonl")
    meta = recs[0] if recs else {}
    summ = (by_kind(recs, "summary") or [{}])[-1]
    names = {n.id: n.name for n in graph.nodes} if graph is not None else {}
    actions = by_kind(recs, "action")
    beliefs = by_kind(recs, "belief")
    calls = [r for r in recs if r["kind"] in ("verdict", "step_choice", "task_check", "task_draft")]
    flags = by_kind(recs, "flag")
    duration = max((r["t"] for r in recs if r["kind"] != "summary"), default=0.0)
    counts = Counter(a["action"] for a in actions)
    by_model = Counter((r.get("model") or "?") for r in calls if not r.get("error"))
    errors = [r for r in calls if r.get("error")]
    cost = json.loads((dest / "cost.json").read_text()) if (dest / "cost.json").exists() else {}

    def step(nid):
        return names.get(nid, nid) if nid else "-"

    def call_line(r):
        if r["kind"] == "verdict":
            return (f"{_fmt_t(r['t'])} {r.get('model', '?')} {r.get('reason', '')}: {r.get('status')} "
                    f"(p={r.get('confidence', 0):.2f}, step '{step(r.get('node'))}')")
        if r["kind"] == "step_choice":
            return f"{_fmt_t(r['t'])} {r.get('model', '?')} which step? -> '{step(r.get('choice'))}'"
        if r["kind"] == "task_check":
            return f"{_fmt_t(r['t'])} {r.get('model', '?')} which task? -> {r.get('choice')}"
        return f"{_fmt_t(r['t'])} draft: {r.get('title')}"

    flag_ctx = []
    for f in flags:
        b = [x for x in beliefs if x["t"] <= f["t"]]
        b = b[-1] if b else None
        flag_ctx.append({
            "t": f["t"], "kind": f.get("flag"), "note": f.get("note", ""),
            "praxis_step": step(b["map"]) if b else None, "praxis_p": round(b["map_p"], 2) if b and "map_p" in b else None,
            "said_before": [f"{_fmt_t(a['t'])} {a['action']}: {a['text']}" for a in actions if f["t"] - 15 <= a["t"] <= f["t"]][-4:],
            "said_after": [f"{_fmt_t(a['t'])} {a['action']}: {a['text']}" for a in actions if f["t"] < a["t"] <= f["t"] + 8][:3],
            "model_answers": [call_line(r) for r in calls if f["t"] - 12 <= r["t"] <= f["t"] + 2 and not r.get("error")][-5:]})

    task = task or {}
    info = {
        "id": dest.name, "created": time.strftime("%Y-%m-%d %H:%M", time.localtime(meta.get("wall", time.time()))),
        "input": cfg.get("input"), "source": cfg.get("source_label"), "task_mode": cfg.get("task_mode"),
        "task": {"task_id": task.get("task_id"), "title": task.get("title"), "how": task.get("how"),
                 "draft": task.get("draft"), "started_at_s": task.get("t")},
        "duration_s": round(duration, 1), "actions": dict(counts), "flags": len(flags),
        "models": {"fast": meta.get("verifier"), "escalation": meta.get("escalation")},
        "calls_by_model": dict(by_model), "errors": len(errors), "cost": cost,
        "frames": {"received": summ.get("frames_in"), "engine": summ.get("frames_engine")},
        "files": {"video": "camera.mp4", "log": "live.jsonl", "graph": "taskgraph.json" if graph is not None else None,
                  "flags": "flags.json", "summary": "SUMMARY.md", "replay": "hud_replay.mp4"},
        "replay": {"status": "queued"}}
    write_json(dest / "session.json", info)

    L = [f"# Praxis Studio session {dest.name}", "",
         "Real engine output (`Praxis prototype v0`). Times are session time (m:ss).", "",
         f"- **Task:** {task.get('title') or 'none recognized'}"
         + (f" (`{task.get('task_id')}`, {task.get('how')}" + (", draft graph" if task.get("draft") else "")
            + f", started at {_fmt_t(task.get('t') or 0)})" if task.get("task_id") else ""),
         f"- **Input:** {cfg.get('input')} ({cfg.get('source_label') or '-'}); task mode: {cfg.get('task_mode')}",
         f"- **Duration:** {_fmt_t(duration)}",
         f"- **Models:** fast tier {meta.get('verifier')}; escalation {meta.get('escalation') or 'off'}. "
         f"Calls: {', '.join(f'{m} {n}' for m, n in by_model.most_common()) or 'none'}"
         + (f"; {len(errors)} errors (e.g. {errors[0]['error'][:100]})" if errors else ""),
         f"- **Cost:** ${cost.get('verifier_usd', 0) + cost.get('draft_usd', 0) + (cost.get('compile_usd') or 0):.3f} "
         f"(verifier ${cost.get('verifier_usd', 0):.3f}, draft ${cost.get('draft_usd', 0):.3f}, "
         f"compile ${cost.get('compile_usd') or 0:.3f}; cap ${cost.get('cap_usd', 0):.2f}"
         + ("; cap reached" if cost.get("cap_hit") else "") + ")",
         f"- **What Praxis did:** " + (", ".join(f"{k} {v}" for k, v in counts.most_common()) or "nothing"), ""]
    alerts = [a for a in actions if a["action"] in ("mistake", "view_request")]
    if alerts:
        L += ["## Alerts", ""] + [f"- {_fmt_t(a['t'])} **{a['action']}** (step '{step(a.get('node'))}'): {a['text']}"
                                  for a in alerts] + [""]
    if flag_ctx:
        L += ["## Flags", ""]
        for f in flag_ctx:
            label = {"wrong": "That's wrong", "missed": "It missed something"}.get(f["kind"], f["kind"])
            L.append(f"### {_fmt_t(f['t'])} · {label}" + (f": \"{f['note']}\"" if f["note"] else ""))
            L.append(f"- Praxis's current step: {f['praxis_step'] or '-'}" + (f" (p={f['praxis_p']})" if f["praxis_p"] is not None else ""))
            if f["said_before"]:
                L.append("- Said in the 15 s before: " + " · ".join(f["said_before"]))
            if f["said_after"]:
                L.append("- Said in the 8 s after: " + " · ".join(f["said_after"]))
            if f["model_answers"]:
                L.append("- Model answers around it: " + " · ".join(f["model_answers"]))
            L.append("")
    L += ["## Everything Praxis said", ""] + [f"- {_fmt_t(a['t'])} {a['action']}: {a['text']}" for a in actions] + [""]
    L += ["## Files", "", "`camera.mp4` (what the camera saw), `live.jsonl` (full run log), `hud_replay.mp4` (HUD "
          "drawn from the log), `taskgraph.json`, `flags.json`, `config.json`, `cost.json`.", ""]
    (dest / "SUMMARY.md").write_text("\n".join(L))
    return info

"""Showcase renders, drawn only from saved run logs (integrity rule #2). Selection is automated from the logs
plus ground truth, so every pick is reproducible:
  - step tracking: the window with the most verified/instructed steps and correct GT strip
  - caught mistake: a mistake alert that matched a GT error (true positive)
  - view request: a window containing a view request
  - failure: a false alarm or the window with the worst step tracking (clearly labeled)
Each pick is rendered in the user view; the step-tracking pick also in the engineer view.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .data.cc4d import Clip, load_manifest
from .eval.harness import MISTAKE_TOL_AFTER, MISTAKE_TOL_BEFORE
from .paths import RENDERS, RESULTS, RUNS
from .render.hud import render
from .runlog import by_kind, read_log
from .tasks.compiler import load_library


def _clips() -> dict[str, Clip]:
    return {c["clip_id"]: Clip.from_json(c) for c in load_manifest()["eval"]}


def _window(t: float, dur: float, before: float = 12.0, after: float = 18.0) -> tuple[float, float]:
    a = max(0.0, t - before)
    return a, min(dur, a + before + after)


def pick(run: str = "fused") -> dict:
    clips = _clips()
    picks: dict = {"tp_mistake": [], "view_request": [], "false_alarm": [], "tracking": [], "wrong_task": []}
    for cid, c in clips.items():
        p = RUNS / run / f"{cid}.jsonl"
        if not p.exists():
            continue
        recs = read_log(p)
        acts = by_kind(recs, "action")
        tasks = by_kind(recs, "task")
        gwin = [(m["start"], m["end"], m) for m in c.mistakes()]
        for a in acts:
            if a["action"] == "mistake":
                hit = [m for s, e, m in gwin if s - MISTAKE_TOL_BEFORE <= a["t"] <= e + MISTAKE_TOL_AFTER]
                (picks["tp_mistake"] if hit else picks["false_alarm"]).append(
                    {"run": run, "clip": cid, "t": a["t"], "text": a["text"], "gt": hit[0]["description"] if hit else None})
            if a["action"] == "view_request":
                picks["view_request"].append({"run": run, "clip": cid, "t": a["t"], "text": a["text"]})
        if tasks and tasks[0]["task_id"] != c.task_id:
            picks["wrong_task"].append({"run": run, "clip": cid, "t": tasks[0]["t"], "pred": tasks[0]["task_id"]})
        if tasks and tasks[0]["task_id"] == c.task_id:
            t_rec = tasks[0]["t"]
            n = sum(1 for a in acts if a["action"] in ("verified", "instruct") and t_rec <= a["t"] <= t_rec + 35)
            picks["tracking"].append({"run": run, "clip": cid, "t": t_rec, "n": n})
    picks["tracking"].sort(key=lambda x: (-x["n"], x["t"]))
    picks["tp_mistake"].sort(key=lambda x: x["t"])
    return picks


def render_pick(run: str, clip_id: str, t: float, name: str, view: str = "user", label: str = "real model output",
                before: float = 12.0, after: float = 18.0, gt_strip: bool = True) -> Path:
    c = _clips()[clip_id]
    g = load_library()[c.task_id]
    names = {n.id: n.name for n in g.nodes}
    t0, t1 = _window(t, c.duration, before, after)
    out = RENDERS / f"{name}_{view}.mp4"
    gt = [(s.start, s.end, s.step) for s in c.segments] if gt_strip else None
    render(RUNS / run / f"{clip_id}.jsonl", c.video, out, view=view, start=c.start, t0=t0, t1=t1,
           dataset="CaptainCook4D", gt=gt if view == "user" else None, step_names=names, label=label, end_seconds=2.5)
    return out


def main(run: str = "fused", fallback: str = "fused_oracle") -> dict:
    RENDERS.mkdir(parents=True, exist_ok=True)
    p = pick(run)
    pf = pick(fallback)
    made = {}
    if p["tracking"]:
        x = p["tracking"][0]     # starts just before "Task recognized"
        made["recognition_and_tracking"] = [
            str(render_pick(x["run"], x["clip"], x["t"], "showcase_recognition_tracking", "user", before=4, after=34)),
            str(render_pick(x["run"], x["clip"], x["t"], "showcase_recognition_tracking", "engineer", before=4, after=34))]
    tp = p["tp_mistake"] or pf["tp_mistake"]
    if tp:
        x = tp[0]
        made["caught_mistake"] = [str(render_pick(x["run"], x["clip"], x["t"], "showcase_caught_mistake", "user", before=14, after=14)),
                                  str(render_pick(x["run"], x["clip"], x["t"], "showcase_caught_mistake", "engineer", before=14, after=14))]
        if len(tp) > 1:
            y = tp[1]
            made["caught_mistake_2"] = [str(render_pick(y["run"], y["clip"], y["t"], "showcase_caught_mistake_2", "user",
                                                        before=14, after=14))]
    vr = p["view_request"] or pf["view_request"]
    if vr:
        x = vr[0]
        made["view_request"] = [str(render_pick(x["run"], x["clip"], x["t"], "showcase_view_request", "user", before=10, after=12))]
    fa = p["false_alarm"] or pf["false_alarm"]
    if fa:
        x = fa[0]
        made["failure_false_alarm"] = [str(render_pick(x["run"], x["clip"], x["t"], "failure_false_alarm", "user",
                                                       label="real model output · FAILURE CASE: false alarm", before=12, after=12))]
    if p["wrong_task"]:
        x = p["wrong_task"][0]
        made["failure_wrong_task"] = [str(render_pick(x["run"], x["clip"], x["t"], "failure_wrong_task", "user",
                                                      label="real model output · FAILURE CASE: wrong task", before=4, after=20))]
    (RESULTS / "renders_index.json").write_text(json.dumps({"run": run, "fallback": fallback,
                                                            "picks": {k: v[:5] for k, v in p.items()},
                                                            "fallback_picks": {k: v[:3] for k, v in pf.items()},
                                                            "rendered": made}, indent=2))
    for files in made.values():
        for f in files:
            sz = Path(f).stat().st_size / 1e6
            if sz > 24:
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f, "-c:v", "libx264", "-crf", "31",
                                "-preset", "slow", "-pix_fmt", "yuv420p", f + ".tmp.mp4"], check=True)
                Path(f + ".tmp.mp4").replace(f)
    return made


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))

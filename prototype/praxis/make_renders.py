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


def step_changes(run: str, c: Clip, window_s: float = 45.0, max_lag_s: float = 10.0) -> dict | None:
    """The window with the most annotated step changes the engine followed (its current step switched to the annotated
    next step within max_lag_s), ties broken by step accuracy inside the window. None if the task was misrecognized."""
    recs = read_log(RUNS / run / f"{c.clip_id}.jsonl")
    tasks = by_kind(recs, "task")
    if not tasks or tasks[0]["task_id"] != c.task_id:
        return None
    bel = [r for r in recs if r["kind"] == "belief"]
    segs = sorted(c.segments, key=lambda s: s.start)
    followed = [b.start for a, b in zip(segs, segs[1:])
                if any(b.start - 3 <= x["t"] <= b.start + max_lag_s and x["map"] == b.step for x in bel)]

    def gt_at(t):
        return next((s.step for s in segs if s.start <= t < s.end), None)

    best = None
    for T in followed:
        t0 = max(0.0, T - 8.0)
        n = sum(1 for u in followed if t0 + 2 <= u <= t0 + window_s - 6)
        bs = [x for x in bel if t0 <= x["t"] <= t0 + window_s and gt_at(x["t"]) is not None]
        acc = sum(x["map"] == gt_at(x["t"]) for x in bs) / len(bs) if bs else 0.0
        if best is None or (n, acc) > (best["n_changes_in_window"], best["window_step_acc"]):
            best = {"run": run, "clip": c.clip_id, "t": t0 + 8.0, "n_changes_in_window": n, "window_step_acc": acc,
                    "changes_followed": len(followed), "changes_annotated": len(segs) - 1}
    return best


def select(run: str = "fused", fallback: str = "fused_oracle") -> list[dict]:
    """The render jobs, chosen automatically from the saved logs and results (development clips excluded)."""
    p = pick(run)
    pf = pick(fallback)
    dev = set(json.loads((RESULTS / "dev_clips.json").read_text())["dev_clips"]) if (RESULTS / "dev_clips.json").exists() else set()
    for d in (p, pf):
        for k in d:
            d[k] = [x for x in d[k] if x["clip"] not in dev]
    # caught-mistake showcases: only alerts the strict judge confirmed (results/l6/mistake_semantic_<run>.json)
    tp = []
    for r_ in (run, fallback):
        sp = RESULTS / "l6" / f"mistake_semantic_{r_}.json"
        if sp.exists():
            for pr in json.loads(sp.read_text())["pairs"]:
                if pr["label"] == "yes" and pr["clip"] not in dev:
                    tp.append({"run": r_, "clip": pr["clip"], "t": pr["t"], "text": pr["alert"], "gt": pr["annotated"]})
    # rank tracking showcases by the clip's measured step accuracy after recognition (recognized within 40 s)
    rr = RESULTS / "runs" / f"{run}.json"
    if rr.exists():
        acc = {r_["clip"]: (r_.get("step_acc_after_recognition") or 0.0) for r_ in json.loads(rr.read_text())["per_clip"]}
        p["tracking"] = sorted([dict(x, step_acc_after_recognition=acc.get(x["clip"], 0.0)) for x in p["tracking"] if x["t"] <= 40],
                               key=lambda x: -x["step_acc_after_recognition"])
    jobs = []

    def job(kind, x, name, views, before, after, label="real model output", selection=""):
        jobs.append({"kind": kind, "name": name, "views": views, "before": before, "after": after, "label": label,
                     "selection": selection, **x})

    if p["tracking"]:     # starts just before "Task recognized"
        job("recognition_and_tracking", p["tracking"][0], "showcase_recognition_tracking", ["user", "engineer"], 4, 34,
            selection="highest step accuracy after recognition among clips recognized within 40 s")
    sc = [x for x in (step_changes(run, c) for cid, c in _clips().items()
                      if cid not in dev and (RUNS / run / f"{cid}.jsonl").exists()) if x]
    sc.sort(key=lambda x: (-x["n_changes_in_window"], -x["window_step_acc"]))
    if sc:
        job("step_tracking", sc[0], "showcase_step_tracking", ["user", "engineer"], 8, 37,
            selection="45 s window with the most annotated step changes the engine followed within 10 s (task "
                      "recognized by Praxis), ties broken by step accuracy in the window")
    if tp:
        job("caught_mistake", tp[0], "showcase_caught_mistake", ["user", "engineer"], 14, 14,
            selection="first mistake alert the strict judge rated 'yes' (matches an annotated error)")
        if len(tp) > 1:
            job("caught_mistake_2", tp[1], "showcase_caught_mistake_2", ["user"], 14, 14,
                selection="second mistake alert the strict judge rated 'yes'")
    vr = p["view_request"] or pf["view_request"]
    if vr:
        job("view_request", vr[0], "showcase_view_request", ["user"], 10, 12, selection="first view request")
    fa = p["false_alarm"] or pf["false_alarm"]
    if fa:
        job("failure_false_alarm", fa[0], "failure_false_alarm", ["user"], 12, 12,
            label="real model output · FAILURE CASE: false alarm",
            selection="first mistake alert with no annotated error within the matching window")
    if p["wrong_task"]:
        job("failure_wrong_task", p["wrong_task"][0], "failure_wrong_task", ["user"], 4, 20,
            label="real model output · FAILURE CASE: wrong task", selection="first clip whose first announced task was wrong")
    return jobs


def main(run: str = "fused", fallback: str = "fused_oracle", render_videos: bool = True, only: tuple = ()) -> dict:
    """render_videos=False only rewrites the index (the selection is deterministic given the same logs); `only`
    limits rendering to those kinds."""
    RENDERS.mkdir(parents=True, exist_ok=True)
    jobs = select(run, fallback)
    root = RESULTS.parent
    for j in jobs:
        c = _clips()[j["clip"]]
        j["window_s"] = list(_window(j["t"], c.duration, j["before"], j["after"]))
        j["task_id"] = c.task_id
        j["files"] = []
        for v in j["views"]:
            out = RENDERS / f"{j['name']}_{v}.mp4"
            if render_videos and (not only or j["kind"] in only):
                render_pick(j["run"], j["clip"], j["t"], j["name"], v, label=j["label"], before=j["before"], after=j["after"])
                if out.stat().st_size / 1e6 > 24:
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out), "-c:v", "libx264", "-crf", "31",
                                    "-preset", "slow", "-pix_fmt", "yuv420p", str(out) + ".tmp.mp4"], check=True)
                    Path(str(out) + ".tmp.mp4").replace(out)
            j["files"].append(str(out.relative_to(root)))
    (RESULTS / "renders_index.json").write_text(json.dumps({
        "run": run, "fallback": fallback,
        "note": "Every render is drawn from the saved run log named here (runs/<run>/<clip>.jsonl; the logs behind the "
                "renders are committed, the rest of runs/ is gitignored). Development clips (results/dev_clips.json) "
                "are excluded from selection.",
        "rendered": jobs}, indent=2))
    return {j["kind"]: j["files"] for j in jobs}


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))

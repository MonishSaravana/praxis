"""Assembly showcase on IndustReal (toy-car assembly). The official step labels were unreachable this weekend,
so these runs are QUALITATIVE ONLY: real model output, no ground truth, no metric is computed from them, and the
render is labeled "no ground truth on this clip". Local evidence is zero-shot (no IndustReal training data)."""
from __future__ import annotations

import json

from .data import industreal
from .data.cc4d import Clip
from .eval import harness
from .eval.run_all import calibrators, engine_config
from .experiments import _budget, make_verifier
from .paths import RENDERS, RESULTS, RUNS
from .perception.extract import Extractor
from .render.hud import render
from .tasks.compiler import load_library


def main(recordings: list[str] | None = None, render_s: float = 40.0) -> dict:
    clips = [Clip.from_json(c) for c in industreal.demo_clips()]
    if recordings:
        clips = [c for c in clips if c.recording in recordings]
    ex = Extractor()
    for c in clips:
        ex.run(c.video, c.clip_id, c.start, c.end)
    stack = harness.load_stack()
    budget = _budget(400, 6.0)
    ver, esc = make_verifier("jev", budget), make_verifier("claude_strong", budget)
    cals = {"primary": calibrators("jev"), "escalation": calibrators("claude_strong")}
    ecfg = engine_config({})
    out = {"note": "qualitative only: IndustReal labels unavailable; no metrics", "runs": {}}
    lib = load_library()
    for c in clips:
        p = harness.run_clip(c, stack, "industreal_demo", ecfg, ver, esc, oracle_task=False, calibrators=cals)
        from .runlog import by_kind, read_log
        recs = read_log(p)
        tasks = by_kind(recs, "task")
        acts = by_kind(recs, "action")
        out["runs"][c.clip_id] = {"recognized": tasks[0]["task_id"] if tasks else None, "t_recognize": tasks[0]["t"] if tasks else None,
                                  "actions": [{k: a[k] for k in ("t", "action", "text")} for a in acts][:40]}
        g = lib["industreal_assy"]
        names = {n.id: n.name for n in g.nodes}
        t_first = tasks[0]["t"] if tasks else 0.0
        render(p, c.video, RENDERS / f"assembly_{c.recording}_user.mp4", view="user", start=0.0, t0=max(0.0, t_first - 3),
               t1=min(c.duration, t_first - 3 + render_s), dataset="IndustReal (no ground truth on this clip)",
               step_names=names, end_seconds=2.5)
        render(p, c.video, RENDERS / f"assembly_{c.recording}_engineer.mp4", view="engineer", start=0.0,
               t0=max(0.0, t_first - 3), t1=min(c.duration, t_first - 3 + render_s),
               dataset="IndustReal (no ground truth on this clip)", step_names=names, end_seconds=1.5)
    out["spend_usd"] = budget.usd
    (RESULTS / "industreal_demo.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    from .paths import load_env
    load_env()
    print(json.dumps(main(["08_assy_2_4", "07_assy_2_3"]), indent=1)[:3000])

"""Policy demo (L6 personalization): the same clip, the same engine and model outputs, run with a fixed novice
profile and a fixed expert profile. Renders are labeled "policy demo": the user model changes phrasing and how
early expanded detail is offered; perception and verification are identical."""
from __future__ import annotations

import json

from .data.cc4d import Clip, load_manifest
from .eval import harness
from .eval.run_all import calibrators, engine_config
from .experiments import _budget, make_verifier
from .paths import RENDERS, RESULTS, RUNS
from .policy.user_model import UserModel
from .render.hud import render
from .runlog import by_kind, read_log
from .tasks.compiler import load_library


def main(clip_id: str, t0: float = 0.0, t1: float = 40.0) -> dict:
    c = [Clip.from_json(x) for x in load_manifest()["eval"] if x["clip_id"] == clip_id][0]
    stack = harness.load_stack()
    budget = _budget(300, 4.0)
    ver, esc = make_verifier("jev", budget), make_verifier("claude_strong", budget)
    cals = {"primary": calibrators("jev"), "escalation": calibrators("claude_strong")}
    g = load_library()[c.task_id]
    names = {n.id: n.name for n in g.nodes}
    out = {"clip": clip_id, "profiles": {}}
    for prof in ("novice", "expert"):
        p = harness.run_clip(c, stack, f"policy_demo_{prof}", engine_config({}), ver, esc, oracle_task=True,
                             user=UserModel(fixed_profile=prof), calibrators=cals)
        acts = by_kind(read_log(p), "action")
        out["profiles"][prof] = [{"t": a["t"], "action": a["action"], "text": a["text"]} for a in acts if t0 <= a["t"] <= t1]
        render(p, c.video, RENDERS / f"policy_demo_{prof}_user.mp4", view="user", start=c.start, t0=t0, t1=t1,
               dataset="CaptainCook4D", step_names=names, label=f"real model output · policy demo: {prof} profile")
    out["spend_usd"] = budget.usd
    (RESULTS / "policy_demo.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    import sys
    from .paths import load_env
    load_env()
    print(json.dumps(main(sys.argv[1]), indent=1)[:3000])

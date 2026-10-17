"""M3/M4 orchestration: run every experiment in dependency order (each stage is skipped if its result exists,
unless --force). Usage: python -m praxis.m3_run [stage ...]"""
from __future__ import annotations

import json
import sys
import time
import traceback

from .paths import RESULTS, load_env

STAGES = ["l2", "probes", "tune", "l5", "fused_oracle", "local_only", "fused", "verifier_only", "fused_heuristic_gate",
          "fused_no_escalation", "fused_claude_fast", "baseline", "recognition", "join", "adaptive", "distill",
          "fused_distilled", "uncertainty", "crops", "report"]

DONE_FILE = {"l2": "l2/l2_event_detector.json", "probes": "l1/l1_quality_and_probes.json", "tune": "l4/tracker_tuning.json",
             "l5": "l5/calibration.json", "baseline": "runs/baseline_stateless.json", "recognition": "l3b/recognition.json",
             "join": "l3b/join_mid_task.json", "adaptive": "l6/adaptive_detail.json", "distill": "l7/distill.json",
             "uncertainty": "l5/visual_uncertainty.json", "crops": "l5/crops_vs_full.json"}


def run_stage(s: str) -> None:
    from . import experiments as E
    from .eval import run_all as R
    if s == "l2":
        E.l2()
    elif s == "probes":
        E.probes()
    elif s == "tune":
        E.tune_tracker()
    elif s == "l5":
        from .eval.report_l5 import main
        print(json.dumps(main(), indent=1))
    elif s in R.VARIANTS:
        r = R.run_variant(s, workers=3)
        print(s, json.dumps({k: r["aggregate"][k] for k in ("step_acc", "false_alarms_per_min", "verifier_calls", "cost_usd")}))
    elif s == "baseline":
        r = R.run_baseline(workers=3)
        print("baseline", r["aggregate"]["step_acc"], r["spend_usd"])
    elif s == "recognition":
        print(E.recognition_summary("fused"))
    elif s == "join":
        E.join_mid_task()
    elif s == "adaptive":
        print(E.adaptive_detail("fused"))
    elif s == "distill":
        print(E.distill())
    elif s == "uncertainty":
        E.visual_uncertainty()
    elif s == "crops":
        print(E.crops_vs_full())
    elif s == "report":
        from .report import collect
        from .make_figures import main as figs
        collect()
        print(figs())


def main(stages: list[str], force: bool = False) -> None:
    load_env()
    for s in stages:
        f = DONE_FILE.get(s, f"runs/{s}.json")
        if not force and (RESULTS / f).exists() and s not in ("report",):
            print(f"[skip] {s} ({f} exists)", flush=True)
            continue
        t0 = time.time()
        print(f"[start] {s}", flush=True)
        try:
            run_stage(s)
            print(f"[done] {s} in {time.time() - t0:.0f}s", flush=True)
        except Exception:  # noqa: BLE001
            print(f"[FAILED] {s}\n{traceback.format_exc()}", flush=True)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args or STAGES, force="--force" in sys.argv)

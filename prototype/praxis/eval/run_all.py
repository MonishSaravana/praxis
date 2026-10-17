"""Engine variants for the evaluation (one place, so every variant differs only in config)."""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from ..data.cc4d import Clip, load_manifest
from ..engine import EngineConfig
from ..paths import CKPT, FEATURES, RESULTS, RUNS
from ..policy.policy import PolicyConfig
from ..state_tracker import TrackerConfig
from ..verify.calibration import Calibrator
from . import harness

VARIANTS = {
    # name: (engine overrides, verifier, escalation, detector, oracle_task)
    "fused": (dict(), "claude_fast", "claude_strong", "learned", False),
    "fused_oracle": (dict(), "claude_fast", "claude_strong", "learned", True),
    "fused_heuristic_gate": (dict(), "claude_fast", "claude_strong", "heuristic", True),
    "local_only": (dict(use_verifier=False), None, None, "learned", True),
    "verifier_only": (dict(tracker_mode="verifier", verify_every_s=5.0), "claude_fast", None, "learned", True),
    "fused_distilled": (dict(), "distilled", "claude_fast", "learned", True),
    "fused_jev": (dict(), "jev", "claude_strong", "learned", True),
}


def tuned_tracker() -> TrackerConfig:
    p = RESULTS / "l4" / "tracker_tuning.json"
    if p.exists():
        b = json.loads(p.read_text())["best"]
        return TrackerConfig(local_weight=b["local_weight"], boundary_weight=b["boundary_weight"])
    return TrackerConfig()


def tuned_policy() -> PolicyConfig:
    p = RESULTS / "l6" / "policy_thresholds.json"
    if p.exists():
        d = json.loads(p.read_text())["chosen"]
        return PolicyConfig(verify_conf=d["verify_conf"], mistake_conf=d["mistake_conf"])
    return PolicyConfig()


def commit_p() -> float:
    p = RESULTS / "l4" / "tracker_tuning.json"
    return json.loads(p.read_text())["best"]["commit_on_switch_p"] if p.exists() else 0.7


def engine_config(overrides: dict) -> EngineConfig:
    stack_thr = harness.load_stack()["boundary_thr"]
    base = EngineConfig(tracker=tuned_tracker(), policy=tuned_policy(), commit_on_switch_p=commit_p(), boundary_thr=stack_thr)
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def calibrators(kind: str | None):
    if not kind:
        return None, None
    p, q = CKPT / f"cal_{kind}.pkl", CKPT / f"devcal_{kind}.pkl"
    return (Calibrator.load(p) if p.exists() else None, Calibrator.load(q) if q.exists() else None)


def eval_clips(limit: int = 0, only: list[str] | None = None) -> list[Clip]:
    man = load_manifest()
    clips = [Clip.from_json(c) for c in man["eval"] if (FEATURES / f"{c['clip_id']}.npz").exists()]
    if only:
        clips = [c for c in clips if c.clip_id in only]
    return clips[:limit] if limit else clips


def run_variant(name: str, limit: int = 0, only: list[str] | None = None, workers: int = 3, budget_usd: float = 40.0) -> dict:
    from ..experiments import _budget, make_verifier
    over, vk, ek, det, oracle = VARIANTS[name]
    stack = harness.load_stack(detector=det)
    ecfg = engine_config(over)
    if det == "heuristic":
        ecfg.boundary_thr = stack["boundary_thr"]
    budget = _budget(max_calls=4000, max_usd=budget_usd)
    ver = make_verifier(vk, budget) if vk else None
    esc = make_verifier(ek, budget) if ek else None
    cal, dcal = calibrators(vk if vk != "distilled" else None)
    clips = eval_clips(limit, only)
    t0 = time.time()

    def one(c: Clip):
        import copy
        st = dict(stack)
        st["recognizer"] = copy.deepcopy(stack["recognizer"])
        p = harness.run_clip(c, st, name, ecfg, ver, esc, cal, dcal, oracle_task=oracle)
        return harness.score_clip(c, p)

    with ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(one, clips))
    res = {"variant": name, "config": {"engine_overrides": over, "verifier": vk, "escalation": ek, "detector": det,
                                       "oracle_task": oracle, "tracker": vars(ecfg.tracker), "policy": vars(ecfg.policy)},
           "aggregate": harness.aggregate(rows), "per_category": harness.per_category(rows), "per_clip": rows,
           "wall_s": time.time() - t0, "spend_usd": budget.usd, "calls": budget.calls}
    (RESULTS / "runs").mkdir(parents=True, exist_ok=True)
    (RESULTS / "runs" / f"{name}.json").write_text(json.dumps(res, indent=1, default=float))
    return res


def run_baseline(limit: int = 0, only: list[str] | None = None, every_s: float = 5.0, workers: int = 4) -> dict:
    from ..experiments import _budget, run_baseline_clip
    from ..tasks.compiler import load_library
    from ..verify.claude import StatelessBaseline
    lib = load_library()
    budget = _budget(max_calls=6000, max_usd=30.0)
    bl = StatelessBaseline("claude-haiku-5-5", budget)
    clips = eval_clips(limit, only)

    def one(c: Clip):
        p = run_baseline_clip(c, bl, lib[c.task_id], "baseline_stateless", every_s=every_s)
        return harness.score_clip(c, p)

    with ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(one, clips))
    res = {"variant": "baseline_stateless", "config": {"model": bl.model, "every_s": every_s, "mistake_conf": 0.7},
           "aggregate": harness.aggregate(rows), "per_category": harness.per_category(rows), "per_clip": rows,
           "spend_usd": budget.usd, "calls": budget.calls}
    (RESULTS / "runs").mkdir(parents=True, exist_ok=True)
    (RESULTS / "runs" / "baseline_stateless.json").write_text(json.dumps(res, indent=1, default=float))
    return res

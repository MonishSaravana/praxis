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
    "fused": (dict(), "jev", "claude_strong", "learned", False),
    "fused_oracle": (dict(), "jev", "claude_strong", "learned", True),
    "fused_heuristic_gate": (dict(), "jev", "claude_strong", "heuristic", True),
    "fused_claude_fast": (dict(), "claude_fast", "claude_strong", "learned", True),
    "local_only": (dict(use_verifier=False), None, None, "learned", True),
    "verifier_only": (dict(tracker_mode="verifier", verify_every_s=5.0), "jev", "claude_strong", "learned", True),
    "fused_distilled": (dict(), "distilled", "claude_strong", "learned", True),
    "fused_no_escalation": (dict(escalate=False), "jev", None, "learned", True),
}


def tuned_tracker() -> TrackerConfig:
    p = RESULTS / "l4" / "tracker_tuning.json"
    if p.exists():
        b = json.loads(p.read_text())["best"]
        return TrackerConfig(local_weight=b["local_weight"], boundary_weight=b["boundary_weight"])
    return TrackerConfig()


def tuned_policy() -> PolicyConfig:
    """Precision-first thresholds per verifier tier, chosen on train-split checks (results/l6/policy_thresholds.json)."""
    p = RESULTS / "l6" / "policy_thresholds.json"
    if p.exists():
        d = json.loads(p.read_text())
        fast = d.get("from_fast", {}).get("chosen", {})
        strong = d.get("from_strong", {}).get("chosen", {})
        by_role = {}
        if fast:
            by_role["fast"] = (fast["verify_conf"], fast["mistake_conf"])
            by_role["student"] = (fast["verify_conf"], fast["mistake_conf"])
        if strong:
            by_role["strong"] = (strong["verify_conf"], strong["mistake_conf"])
        c = d["chosen"]
        return PolicyConfig(verify_conf=c["verify_conf"], mistake_conf=c["mistake_conf"], by_role=by_role)
    return PolicyConfig()


def commit_p() -> float:
    p = RESULTS / "l4" / "tracker_tuning.json"
    return json.loads(p.read_text())["best"]["commit_on_switch_p"] if p.exists() else 0.7


def engine_config(overrides: dict) -> EngineConfig:
    stack_thr = harness.load_stack()["boundary_thr"]
    base = EngineConfig(tracker=tuned_tracker(), policy=tuned_policy(), commit_on_switch_p=commit_p(), boundary_thr=stack_thr)
    for k, v in overrides.items():
        if k.startswith("policy."):
            setattr(base.policy, k.split(".", 1)[1], v)
        elif k.startswith("tracker."):
            setattr(base.tracker, k.split(".", 1)[1], v)
        else:
            setattr(base, k, v)
    return base


def calibrators(kind: str | None):
    if not kind:
        return None, None
    p, q = CKPT / f"cal_{kind}.pkl", CKPT / f"devcal_{kind}.pkl"
    return (Calibrator.load(p) if p.exists() else None, Calibrator.load(q) if q.exists() else None)


def eval_clips(limit: int = 0, only: list[str] | None = None, need_features: bool = True) -> list[Clip]:
    man = load_manifest()
    clips = [Clip.from_json(c) for c in man["eval"] if not need_features or (FEATURES / f"{c['clip_id']}.npz").exists()]
    if only:
        clips = [c for c in clips if c.clip_id in only]
    return clips[:limit] if limit else clips


def run_variant(name: str, limit: int = 0, only: list[str] | None = None, workers: int = 3, budget_usd: float = 40.0,
                tag: str = "") -> dict:
    """tag: suffix for output names (smoke tests use tag='_smoke' so final results are never overwritten)."""
    from ..experiments import _budget, make_verifier
    over, vk, ek, det, oracle = VARIANTS[name]
    stack = harness.load_stack(detector=det)
    ecfg = engine_config(over)
    if det == "heuristic":
        ecfg.boundary_thr = stack["boundary_thr"]
    budget = _budget(max_calls=4000, max_usd=budget_usd)
    ver = make_verifier(vk, budget) if vk else None
    esc = make_verifier(ek, budget) if ek else None
    cals = {"primary": calibrators(vk if vk != "distilled" else None), "escalation": calibrators(ek)}
    clips = eval_clips(limit, only)
    t0 = time.time()

    def one(c: Clip):
        import copy
        st = dict(stack)
        st["recognizer"] = copy.deepcopy(stack["recognizer"])
        p = harness.run_clip(c, st, name + tag, ecfg, ver, esc, oracle_task=oracle, calibrators=cals)
        return harness.score_clip(c, p)

    with ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(one, clips))
    dev = set(json.loads((RESULTS / "dev_clips.json").read_text())["dev_clips"]) if (RESULTS / "dev_clips.json").exists() else set()
    res = {"variant": name, "aggregate_excl_dev_clips": harness.aggregate([r for r in rows if r["clip"] not in dev]),
           "dev_clips": sorted(dev),
           "config": {"engine_overrides": over, "verifier": vk, "escalation": ek, "detector": det,
                                       "oracle_task": oracle, "tracker": vars(ecfg.tracker), "policy": vars(ecfg.policy)},
           "aggregate": harness.aggregate(rows), "per_category": harness.per_category(rows), "per_clip": rows,
           "wall_s": time.time() - t0, "spend_usd": budget.usd, "calls": budget.calls}
    (RESULTS / "runs").mkdir(parents=True, exist_ok=True)
    (RESULTS / "runs" / f"{name}{tag}.json").write_text(json.dumps(res, indent=1, default=float))
    return res


def run_baseline(limit: int = 0, only: list[str] | None = None, every_s: float = 5.0, workers: int = 4,
                 model: str = "claude-opus-5-5", effort: str = "medium", name: str = "baseline_stateless") -> dict:
    from ..experiments import _budget, run_baseline_clip
    from ..tasks.compiler import load_library
    from ..verify.claude import StatelessBaseline
    lib = load_library()
    budget = _budget(max_calls=6000, max_usd=45.0)
    bl = StatelessBaseline(model, budget, effort=effort)
    clips = eval_clips(limit, only, need_features=False)

    def one(c: Clip):
        p = run_baseline_clip(c, bl, lib[c.task_id], name, every_s=every_s)
        return harness.score_clip(c, p)

    with ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(one, clips))
    dev = set(json.loads((RESULTS / "dev_clips.json").read_text())["dev_clips"]) if (RESULTS / "dev_clips.json").exists() else set()
    res = {"variant": name, "aggregate_excl_dev_clips": harness.aggregate([r for r in rows if r["clip"] not in dev]),
           "dev_clips": sorted(dev), "config": {"model": bl.model, "effort": effort, "every_s": every_s, "mistake_conf": 0.7},
           "aggregate": harness.aggregate(rows), "per_category": harness.per_category(rows), "per_clip": rows,
           "spend_usd": budget.usd, "calls": budget.calls}
    (RESULTS / "runs").mkdir(parents=True, exist_ok=True)
    (RESULTS / "runs" / f"{name}.json").write_text(json.dumps(res, indent=1, default=float))
    return res

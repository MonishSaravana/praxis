"""Assemble results/metrics.json (all headline numbers, each with its source file) from results/**.json.
RESULTS.md and CLAIMS.md quote these numbers; nothing is typed in by hand."""
from __future__ import annotations

import json
from pathlib import Path

from .paths import RESULTS


def _j(rel: str) -> dict | None:
    p = RESULTS / rel
    return json.loads(p.read_text()) if p.exists() else None


def _agg(name: str) -> dict | None:
    r = _j(f"runs/{name}.json")
    return r["aggregate"] if r else None


def collect() -> dict:
    m: dict = {"_sources": {}}

    def put(key, val, src):
        if val is not None:
            m[key] = val
            m["_sources"][key] = src

    put("data", {k: v for k, v in (_j("data/eval_manifest_summary.json") or {}).items() if k != "clips"} or None,
        "results/data/eval_manifest_summary.json")
    sp = _j("l1/l1_speed.json")
    put("l1_speed", sp, "results/l1/l1_speed.json")
    if sp:
        ms = {r["backbone"]: r["ms_per_item"] for r in sp["rows"]}
        f_sig = ms.get("siglip2-base-224 (image)")
        hands = ms.get("mediapipe-hands")
        vj = ms.get("vjepa2-vitl (8f@224)")
        # live fast path per frame at 4 fps: SigLIP2 (batch 1) + hands, plus one V-JEPA 2 window every 2 s
        # (amortized over 8 frames); L2 head and tracker update are <1 ms (results/l2 head_fps)
        sig1 = [r for r in sp["rows"] if r["backbone"].startswith("siglip2-base-224 (image)") and r["batch"] == 1]
        sig1 = sig1[0]["ms_per_item"] if sig1 else f_sig
        per_frame = sig1 + hands + vj / 8.0
        put("fast_path", {"per_frame_ms": per_frame, "max_fps": 1000.0 / per_frame,
                          "breakdown_ms": {"siglip2_frame": sig1, "hands": hands, "vjepa2_amortized": vj / 8.0},
                          "assumes": "SigLIP2 batch 1 + MediaPipe hands per frame; V-JEPA 2 (8 frames @224) every 2 s at "
                                     "4 fps; measured with nothing else running"}, "results/l1/l1_speed.json")
    q = _j("l1/l1_quality_and_probes.json")
    put("l1_quality", q.get("backbones") if q else None, "results/l1/l1_quality_and_probes.json")
    put("l2", _j("l2/l2_event_detector.json") and {k: v for k, v in _j("l2/l2_event_detector.json").items() if k != "train"} | {
        "train": {k: v for k, v in _j("l2/l2_event_detector.json")["train"].items() if k != "loss"}}, "results/l2/l2_event_detector.json")
    put("l3_compile", _j("l3/compile_summary.json"), "results/l3/compile_summary.json")
    put("l4_tuning_best", (_j("l4/tracker_tuning.json") or {}).get("best"), "results/l4/tracker_tuning.json")
    for v in ("fused", "fused_oracle", "fused_heuristic_gate", "local_only", "verifier_only", "fused_distilled",
              "fused_no_escalation", "fused_claude_fast", "baseline_stateless"):
        put(f"run_{v}", _agg(v), f"results/runs/{v}.json")
    for v, key in (("fused_oracle", "run_fused_oracle_excl"), ("baseline_stateless", "run_baseline_excl"), ("fused", "run_fused_excl")):
        r = _j(f"runs/{v}.json")
        put(key, r.get("aggregate_excl_dev_clips") if r else None, f"results/runs/{v}.json (aggregate_excl_dev_clips)")
    put("recognition", _j("l3b/recognition.json"), "results/l3b/recognition.json")
    put("join_mid_task", _j("l3b/join_mid_task.json"), "results/l3b/join_mid_task.json")
    put("verifier_compare", _j("l5/compare_jev_vs_claude_fast.json"), "results/l5/compare_jev_vs_claude_fast.json")
    put("calibration", _j("l5/calibration.json"), "results/l5/calibration.json")
    put("crops", _j("l5/crops_vs_full.json"), "results/l5/crops_vs_full.json")
    put("uncertainty", _j("l5/visual_uncertainty.json"), "results/l5/visual_uncertainty.json")
    put("policy_thresholds", (_j("l6/policy_thresholds.json") or {}).get("chosen"), "results/l6/policy_thresholds.json")
    put("adaptive_detail", _j("l6/adaptive_detail.json"), "results/l6/adaptive_detail.json")
    for v in ("fused_oracle", "fused", "baseline_stateless"):
        r = _j(f"l6/mistake_semantic_{v}.json")
        put(f"semantic_{v}", {k: r[k] for k in r if k != "pairs"} if r else None, f"results/l6/mistake_semantic_{v}.json")
    put("distillation", _j("l7/distill.json"), "results/l7/distill.json")
    put("spend", _j("spend.json"), "results/spend.json")
    (RESULTS / "metrics.json").write_text(json.dumps(m, indent=1, default=float))
    return m


if __name__ == "__main__":
    out = collect()
    print(sorted(k for k in out if not k.startswith("_")))

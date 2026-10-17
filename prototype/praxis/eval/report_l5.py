"""L5 summary: per-verifier scores, head-to-head on identical checks, calibration, policy thresholds."""
from __future__ import annotations

import json

from ..paths import RESULTS
from .verifier_eval import compare, score, tune_policy

KINDS = ("jev", "claude_fast", "claude_strong")


def main() -> dict:
    out = {}
    for k in KINDS:
        r = score(k)
        if r:
            out[k] = r
            (RESULTS / "l5" / f"verifier_{k}.json").write_text(json.dumps(r, indent=2))
    cmp = compare([k for k in KINDS if k in out])
    (RESULTS / "l5" / "compare_jev_vs_claude_fast.json").write_text(json.dumps(cmp, indent=2))
    cal = {k: {"model": v["model"], "n_eval": v["n"], "ece_raw": v["ece_raw"], "ece_calibrated": v.get("ece_calibrated"),
               "calibrator_train_n": v.get("calibrator_train_n"), "method": "isotonic (fit on train-split checks)",
               "reliability_raw": v["reliability_raw"], "reliability_calibrated": v.get("reliability_calibrated")}
           for k, v in out.items()}
    (RESULTS / "l5" / "calibration.json").write_text(json.dumps(cal, indent=2))
    # precision-first policy thresholds: verify from the fast tier, mistakes from the strong tier (mistakes escalate)
    pv = tune_policy("jev") if "jev" in out else {}
    pm = tune_policy("claude_strong") if "claude_strong" in out else {}
    chosen = {"verify_conf": max(pv.get("chosen", {}).get("verify_conf", 0.6), pm.get("chosen", {}).get("verify_conf", 0.6)),
              "mistake_conf": pm.get("chosen", {}).get("mistake_conf", 0.7)}
    pol = {"chosen": chosen, "from_fast": pv, "from_strong": pm,
           "note": "thresholds on calibrated probabilities, chosen on TRAIN-split checks for precision"}
    (RESULTS / "l6").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l6" / "policy_thresholds.json").write_text(json.dumps(pol, indent=2))
    return {"scores": {k: {m: v.get(m) for m in ("accuracy", "auroc", "ece_raw", "ece_calibrated")} for k, v in out.items()},
            "policy": chosen}


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))

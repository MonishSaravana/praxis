"""Score verifier runs on GT-labeled routine checks: accuracy, AUROC, calibration (ECE before/after), latency,
cost, and deviation precision/recall. Calibrators are fit on the TRAIN split of the same verifier only."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

from ..paths import CKPT, DATA, RESULTS
from ..verify.calibration import Calibrator, ece, raw_p_complete, reliability
from . import metrics as M

VERDICTS = DATA / "verdicts"


def load(tag: str) -> list[dict]:
    p = VERDICTS / f"{tag}.jsonl"
    rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []
    return [r for r in rows if not r["verdict"].get("error")]


def arrays(rows: list[dict]):
    p = np.array([raw_p_complete(r["verdict"]["step_status"], r["verdict"]["confidence"]) for r in rows])
    y = np.array([r["y_complete"] for r in rows])
    dev = np.array([r["verdict"]["step_status"] == "deviation" or r["verdict"].get("mistake") is not None for r in rows])
    pdev = np.array([r["verdict"]["confidence"] if r["verdict"]["step_status"] == "deviation" else 0.0 for r in rows])
    ye = np.array([r["y_error"] for r in rows])
    return p, y, dev, pdev, ye


def fit_calibrators(kind: str) -> tuple[Calibrator, Calibrator] | None:
    tr = load(f"{kind}_train")
    if len(tr) < 20:
        return None
    p, y, _, pdev, ye = arrays(tr)
    cal = Calibrator("isotonic").fit(p, y)
    dcal = Calibrator("isotonic").fit(pdev, ye)
    CKPT.mkdir(parents=True, exist_ok=True)
    cal.save(CKPT / f"cal_{kind}.pkl")
    dcal.save(CKPT / f"devcal_{kind}.pkl")
    return cal, dcal


def score(kind: str, split: str = "eval", tag: str | None = None) -> dict | None:
    rows = load(tag or f"{kind}_{split}")
    if not rows:
        return None
    p, y, dev, pdev, ye = arrays(rows)
    cals = fit_calibrators(kind)
    out: dict = {"verifier": kind, "tag": tag or f"{kind}_{split}", "n": len(rows),
                 "model": rows[0]["verdict"].get("model"),
                 "accuracy": float(((p >= 0.5) == (y == 1)).mean()),
                 "auroc": float(roc_auc_score(y, p)) if len(set(y)) > 1 else None,
                 "ece_raw": ece(p, y), "reliability_raw": reliability(p, y)}
    if cals:
        cal, dcal = cals
        pc = cal(p)
        out.update({"ece_calibrated": ece(pc, y), "accuracy_calibrated": float(((pc >= 0.5) == (y == 1)).mean()),
                    "reliability_calibrated": reliability(pc, y), "calibrator_train_n": len(load(f"{kind}_train"))})
    live = [r["verdict"]["latency_ms"] for r in rows if not r["verdict"]["raw"].get("cached")]
    allat = [r["verdict"]["latency_ms"] for r in rows]
    out["latency_ms"] = M.latency_summary(live if live else allat)
    out["latency_from_cache_logs"] = not bool(live)
    costs = [r["verdict"]["raw"].get("orig_cost_usd", r["verdict"].get("cost_usd", 0.0)) for r in rows]
    out["cost_usd_per_check"] = float(np.mean(costs))
    tp = int((dev & (ye == 1)).sum())
    fp = int((dev & (ye == 0)).sum())
    fn = int((~dev & (ye == 1)).sum())
    out["deviation_vs_gt_error"] = M.prf(tp, fp, fn)
    out["visibility_insufficient_rate"] = float(np.mean([r["verdict"]["visibility"] == "insufficient" for r in rows]))
    return out


def compare(kinds: list[str], split: str = "eval") -> dict:
    """Head-to-head on the SAME checks (intersection of check ids)."""
    sets = {k: {r["check_id"]: r for r in load(f"{k}_{split}")} for k in kinds}
    common = set.intersection(*(set(v) for v in sets.values())) if sets else set()
    res = {"n_common": len(common), "by_verifier": {}}
    for k in kinds:
        rows = [sets[k][c] for c in sorted(common)]
        if not rows:
            continue
        tmp = VERDICTS / f"_cmp_{k}.jsonl"
        tmp.write_text("\n".join(json.dumps(r) for r in rows))
        res["by_verifier"][k] = score(k, tag=f"_cmp_{k}")
        tmp.unlink()
    (RESULTS / "l5").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l5" / f"compare_{'_vs_'.join(kinds)}.json").write_text(json.dumps(res, indent=2))
    return res

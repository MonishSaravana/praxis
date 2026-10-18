"""Could another model replace Jev as the fast tier? (TRAIN split only.)

Jev answers two questions for the tracker on every engine run:
  completion  "is step X done?"            -> the 100 labeled train checks of the framing ablation (span framing);
                                              Jev's answers are already logged in data/verdicts/framing_span_jev.jsonl
  which step  "which of these steps now?"  -> real questions Jev answered in the train reference run
                                              (runs/mt_train_sweep_reference_single_task), with the identical frames
                                              re-decoded and the annotation at that moment as ground truth
A challenger answers the same items with the same prompt and schema; only the model changes.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

import numpy as np

from ..data.cc4d import Clip, load_manifest
from ..io.sources import FileSource
from ..paths import DATA, RESULTS, RUNS
from ..runlog import by_kind, read_log
from ..verify.common import span_keyframes

STEP_ITEMS = DATA / "bakeoff" / "which_step"


def _slug(kind: str) -> str:
    return re.sub(r"[^a-z0-9.]+", "_", kind.lower())


# ------------------------------------------------------------------------------------------- completion checks
def completion_checks(n: int = 100):
    from ..eval.checks import load_checks
    from ..tasks.compiler import load_library
    lib = load_library()
    tr = [c for c in load_checks("train") if c.task_id in lib]
    random.seed(0)
    return random.sample(tr, 200)[:n], lib            # exactly the framing ablation's items


def completion_metrics(rows: list[dict]) -> dict:
    from sklearn.metrics import roc_auc_score
    from ..verify.calibration import raw_p_complete
    rows = [r for r in rows if not r["verdict"].get("error")]
    p = np.array([raw_p_complete(r["verdict"]["step_status"], r["verdict"]["confidence"]) for r in rows])
    y = np.array([r["y_complete"] for r in rows])
    live = [r["verdict"]["latency_ms"] for r in rows if not r["verdict"]["raw"].get("cached")]
    cost = [r["verdict"]["raw"].get("orig_cost_usd", r["verdict"]["cost_usd"]) for r in rows]
    return {"n": len(rows), "accuracy": float(((p >= 0.5) == (y == 1)).mean()), "auroc": float(roc_auc_score(y, p)),
            "latency_ms_p50": float(np.median(live)) if live else None,
            "latency_ms_p95": float(np.percentile(live, 95)) if live else None,
            "cost_usd_per_check": float(np.mean(cost)), "model": rows[0]["verdict"]["model"] if rows else None}


def completion_test(kinds=("openai:gpt-6-luna",), budget_usd: float = 1.0, workers: int = 4) -> dict:
    from ..eval.checks import run_verifier_on_checks
    from ..experiments import _budget, make_verifier
    checks, lib = completion_checks()
    vd = DATA / "verdicts"
    res = {"jev (logged)": completion_metrics([json.loads(x) for x in (vd / "framing_span_jev.jsonl").read_text().splitlines()
                                               if json.loads(x)["check_id"] in {c.check_id for c in checks}])}
    budget = _budget(max_calls=len(checks) * len(kinds) + 10, max_usd=budget_usd)
    for kind in kinds:
        rows = run_verifier_on_checks(make_verifier(kind, budget), checks, lib, vd / f"fasttier_{_slug(kind)}.jsonl",
                                      workers=workers, framing="span", log_every=0)
        res[kind] = completion_metrics(rows)
        print("completion", kind, res[kind], flush=True)
    return {"completion": res, "spend_usd": budget.usd}


# ------------------------------------------------------------------------------------------- which step
def build_step_items(run: str = "mt_train_sweep_reference_single_task", per_recording: int = 5, seed: int = 0) -> list[dict]:
    """Sample Jev's "which step?" questions from a train run's logs; re-decode the identical frames (the clip decoded
    from its start at 4 fps, nearest frame to each keyframe time, as replay does); GT = the annotation at t."""
    import cv2
    man = load_manifest()
    clips = {c["clip_id"]: Clip.from_json(c) for c in man["train"]}
    rng = random.Random(seed)
    STEP_ITEMS.mkdir(parents=True, exist_ok=True)
    items = []
    for f in sorted((RUNS / run).glob("*_full.jsonl")):          # single-task recordings only (not splices)
        c = clips.get(f.stem)
        if c is None:
            continue
        recs = read_log(f)
        sc = [r for r in by_kind(recs, "step_choice") if not r.get("error")]
        if not sc:
            continue
        starts = [(r["t"], r["task_id"]) for r in recs if r["kind"] == "task"]

        def active(t):                      # the task the engine was tracking when it asked (automatic run)
            cur = None
            for ts, tid in starts:
                if ts <= t:
                    cur = tid
            return cur
        pick = rng.sample(sc, min(per_recording, len(sc)))
        tmax = max(r["t"] for r in pick) + 0.5
        fr, ft = [], []
        for x in FileSource(c.video, fps=4.0, start=c.start, end=min(c.end, c.start + tmax), max_side=640):
            fr.append(x.rgb)
            ft.append(x.t)
        ft = np.array(ft)
        for k, r in enumerate(pick):
            kf, kt = span_keyframes(lambda x: fr[int(np.argmin(np.abs(ft - x)))] if len(ft) and x >= ft[0] - 0.5 else None, r["t"])
            gt = next((s.step for s in c.segments if s.start <= r["t"] < s.end), "none")
            iid = f"{c.clip_id}_{k}"
            paths = []
            for j, im in enumerate(kf):
                p = STEP_ITEMS / f"{iid}_{j}.jpg"
                cv2.imwrite(str(p), cv2.cvtColor(im, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
                paths.append(p.name)
            items.append({"id": iid, "clip": c.clip_id, "task_id": c.task_id, "active_task": active(r["t"]),
                          "t": r["t"], "options": r["options"],
                          "gt": gt, "gt_offered": gt in r["options"] or gt == "none", "frames": paths,
                          "jev": {"choice": r["choice"], "probs": r["probs"], "latency_ms": r["latency_ms"],
                                  "cost_usd": r.get("cost_usd", 0.0)}})
    (STEP_ITEMS / "items.json").write_text(json.dumps(items, indent=1))
    return items


def _step_frames(it):
    import cv2
    return [cv2.cvtColor(cv2.imread(str(STEP_ITEMS / p)), cv2.COLOR_BGR2RGB) for p in it["frames"]]


def step_metrics(rows: list[dict]) -> dict:
    ok = [r for r in rows if "error" not in r]
    off = [r for r in ok if r["gt_offered"]]
    return {"n": len(ok), "errors": len(rows) - len(ok),
            "accuracy": float(np.mean([r["choice"] == r["gt"] for r in ok])) if ok else None,
            "accuracy_when_gt_offered": float(np.mean([r["choice"] == r["gt"] for r in off])) if off else None,
            "none_rate": float(np.mean([r["choice"] == "none" for r in ok])) if ok else None,
            "latency_ms_p50": float(np.median([r["latency_ms"] for r in ok])) if ok else None,
            "latency_ms_p95": float(np.percentile([r["latency_ms"] for r in ok], 95)) if ok else None,
            "cost_usd_per_call": float(np.mean([r.get("cost_usd") or 0.0 for r in ok])) if ok else None}


def step_test(kinds=("openai:gpt-6-luna",), budget_usd: float = 1.0, workers: int = 4) -> dict:
    from concurrent.futures import ThreadPoolExecutor
    from ..experiments import _budget, make_verifier
    from ..tasks.compiler import load_library
    lib = load_library()
    items = json.loads((STEP_ITEMS / "items.json").read_text())
    jev = [{**it["jev"], "gt": it["gt"], "gt_offered": it["gt_offered"]} for it in items]
    res = {"n_items": len(items), "candidate_recall": float(np.mean([it["gt_offered"] for it in items])),
           "jev (logged)": step_metrics(jev)}
    budget = _budget(max_calls=len(items) * len(kinds) + 10, max_usd=budget_usd)
    for kind in kinds:
        ver = make_verifier(kind, budget)

        def ask(it):
            try:
                g = lib[it["active_task"]]                     # the recipe the engine asked about (may be wrong)
                opts = {k: f"{g.node(k).name}: {g.node(k).end_state}" for k in it["options"]}   # the engine's wording
                a = ver.choose_step(_step_frames(it), opts, g.title)
                return {"choice": a["choice"], "latency_ms": a["latency_ms"], "cost_usd": a.get("cost_usd", 0.0),
                        "gt": it["gt"], "gt_offered": it["gt_offered"]}
            except Exception as e:  # noqa: BLE001
                return {"error": str(e)[:200], "gt": it["gt"], "gt_offered": it["gt_offered"]}
        with ThreadPoolExecutor(workers) as ex:
            rows = list(ex.map(ask, items))
        res[kind] = step_metrics(rows)
        print("which step", kind, res[kind], flush=True)
    return {"which_step": res, "spend_usd": budget.usd}


def patch_active_tasks(run: str = "mt_train_sweep_reference_single_task") -> None:
    """Add active_task to items built before it was recorded (no re-decoding)."""
    items = json.loads((STEP_ITEMS / "items.json").read_text())
    for it in items:
        recs = read_log(RUNS / run / f"{it['clip']}.jsonl")
        cur = None
        for r in recs:
            if r["kind"] == "task" and r["t"] <= it["t"]:
                cur = r["task_id"]
        it["active_task"] = cur
    (STEP_ITEMS / "items.json").write_text(json.dumps(items, indent=1))


def run(kinds=("openai:gpt-6-luna", "openai:gpt-6-sol"), budget_usd: float = 3.0, workers: int = 4) -> dict:
    a = completion_test(kinds, budget_usd / 2, workers)
    b = step_test(kinds, budget_usd / 2, workers)
    out = {"protocol": __doc__.strip(), **a, **b, "spend_usd": a["spend_usd"] + b["spend_usd"]}
    (RESULTS / "l5").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l5" / "fast_tier_bakeoff.json").write_text(json.dumps(out, indent=1, default=float))
    return out

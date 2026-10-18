"""Which model should answer "which task is this?" (TRAIN split; it drives recognition and multi-task switching).

Items: moments inside annotated steps of train-split recordings, a few per recipe, each with the same three keyframes
the engine would send (sharpest frame from ~8-6 s ago + the two sharpest of the last 3 s, verify.common.span_keyframes)
and the same options the engine offers (every library task's title + summary, plus "none").
Every model answers the same items; we report accuracy, the "none" rate, the confusions, latency and cost.
Building the items is free; answering them is paid (each model's cost is shown before running).
"""
from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

import numpy as np

from ..data.cc4d import Clip, load_manifest
from ..io.sources import FileSource
from ..paths import DATA, RESULTS
from ..verify.common import span_keyframes

ITEMS = DATA / "bakeoff" / "which_task"


def build_items(per_recipe: int = 15, seed: int = 0, min_t: float = 20.0, max_t: float = 600.0) -> list[dict]:
    """Sample moments (inside an annotated step, between min_t and max_t) from train recordings on disk; save the
    engine's three keyframes per moment as JPEGs. No model calls."""
    import cv2
    from ..tasks.compiler import load_library
    lib = load_library()
    man = load_manifest()
    rng = random.Random(seed)
    by: dict[str, list[Clip]] = {}
    for c in man["train"]:
        if c["task_id"] in lib and Path(c["video"]).exists():
            by.setdefault(c["task_id"], []).append(Clip.from_json(c))
    ITEMS.mkdir(parents=True, exist_ok=True)
    items = []
    for tid in sorted(by):
        recs = sorted(by[tid], key=lambda c: c.clip_id)
        for k in range(per_recipe):
            c = recs[k % len(recs)]                     # spread over recordings first
            segs = [s for s in c.segments if s.end > min_t and s.start < min(max_t, c.duration)]
            if not segs:
                continue
            s = rng.choice(segs)
            t = rng.uniform(max(s.start, min_t), min(s.end, max_t, c.duration))
            frames, times = [], []
            for f in FileSource(c.video, fps=4.0, start=c.start + max(0.0, t - 9.0), end=c.start + t + 0.25, max_side=640):
                frames.append(f.rgb)
                times.append(max(0.0, t - 9.0) + f.t)
            if not frames:
                continue
            ft = np.array(times)
            kf, kt = span_keyframes(lambda x: frames[int(np.argmin(np.abs(ft - x)))], t)
            iid = f"{tid.replace('cc4d_', '')}_{k:02d}"
            paths = []
            for j, fr in enumerate(kf):
                p = ITEMS / f"{iid}_{j}.jpg"
                cv2.imwrite(str(p), cv2.cvtColor(fr, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
                paths.append(p.name)
            items.append({"id": iid, "task_id": tid, "recording": c.recording, "clip": c.clip_id, "t": round(t, 2),
                          "step": s.step, "frames": paths, "frame_ages": [round(t - x, 2) for x in kt]})
    (ITEMS / "items.json").write_text(json.dumps(items, indent=1))
    return items


def _frames(it: dict) -> list[np.ndarray]:
    import cv2
    return [cv2.cvtColor(cv2.imread(str(ITEMS / p)), cv2.COLOR_BGR2RGB) for p in it["frames"]]


def run(kinds=("jev", "claude_sonnet", "claude_strong"), budget_usd: float = 2.2, workers: int = 4,
        out_name: str = "which_task_bakeoff") -> dict:
    """Ask every model the engine's "which task?" question on the saved items, under one shared hard budget."""
    from concurrent.futures import ThreadPoolExecutor
    from ..experiments import _budget, make_verifier
    from ..tasks.compiler import load_library
    lib = load_library()
    opts = {tid: f"{g.title}: {g.summary[:160]}" for tid, g in lib.items()}     # exactly the engine's options
    items = json.loads((ITEMS / "items.json").read_text())
    budget = _budget(max_calls=len(items) * len(kinds) + 10, max_usd=budget_usd)
    res = {"protocol": f"{len(items)} moments inside annotated steps of train-split recordings; the engine's three "
                       "keyframes and options (all library tasks + none)", "n_items": len(items), "models": {}}
    for kind in kinds:
        ver = make_verifier(kind, budget)

        def ask(it):
            try:
                a = ver.choose_task(_frames(it), opts)
                return {"id": it["id"], "truth": it["task_id"], "choice": a["choice"], "p": a["probs"].get(a["choice"]),
                        "p_truth": a["probs"].get(it["task_id"], 0.0), "latency_ms": a["latency_ms"],
                        "cost_usd": a.get("cost_usd", 0.0), "model": a.get("model")}
            except Exception as e:  # noqa: BLE001
                return {"id": it["id"], "truth": it["task_id"], "error": str(e)[:200]}
        with ThreadPoolExecutor(workers) as ex:
            rows = list(ex.map(ask, items))
        ok = [r for r in rows if "error" not in r]
        conf = Counter((r["truth"].replace("cc4d_", ""), r["choice"].replace("cc4d_", "")) for r in ok if r["choice"] != r["truth"])
        res["models"][kind] = {
            "model": ok[0]["model"] if ok else None, "n": len(ok), "errors": len(rows) - len(ok),
            "accuracy": float(np.mean([r["choice"] == r["truth"] for r in ok])) if ok else None,
            "none_rate": float(np.mean([r["choice"] == "none" for r in ok])) if ok else None,
            "accuracy_when_answering": float(np.mean([r["choice"] == r["truth"] for r in ok if r["choice"] != "none"]))
            if any(r["choice"] != "none" for r in ok) else None,
            "wrong_task_rate": float(np.mean([r["choice"] not in (r["truth"], "none") for r in ok])) if ok else None,
            "mean_p_truth": float(np.mean([r["p_truth"] for r in ok])) if ok else None,
            "latency_ms_p50": float(np.median([r["latency_ms"] for r in ok])) if ok else None,
            "cost_usd": float(sum(r["cost_usd"] or 0.0 for r in ok)),
            "top_confusions": conf.most_common(8), "rows": rows}
        print(kind, {k: v for k, v in res["models"][kind].items() if k not in ("rows",)}, flush=True)
    res["spend_usd"] = budget.usd
    (RESULTS / "l3b").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l3b" / f"{out_name}.json").write_text(json.dumps(res, indent=1, default=float))
    return res

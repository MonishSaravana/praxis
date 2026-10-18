"""Run the engine on ENIGMA-51 repair videos (first-person electrical-board repair) and score PROXIES only
(see data/enigma51.py): step accuracy against DERIVED step segments, and object consistency at annotated
interactions. Task given (the procedure), zero-shot local evidence (no video of these tasks was ever trained on),
L2 event detector as trained on cooking, Jev fast tier + gpt-6.1-sol strong tier (calibrated on cooking train checks).

Two steps because of the sandbox: features() needs the GPU (run outside it), run() needs the model APIs.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np

from ..data import enigma51 as E
from ..paths import FEATURES, RESULTS, RUNS


def video_path(vid: str):
    return E.RAW / "videos" / f"{vid}.mp4"


def features(vids=tuple(E.TEST_VIDEOS)) -> None:
    from ..perception.extract import Extractor
    ex = Extractor(stride_s=2.0)
    ann = E.annotations()["videos"]
    for vid in vids:
        if video_path(vid).exists():
            ex.run(video_path(vid), f"enigma_{vid}", 0.0, float(ann[vid]["duration_seconds"]))
            print("features", vid, flush=True)


def _stack():
    from ..evidence import ZeroShotEvidence
    from ..tasks.recognizer import TaskRecognizer
    from . import harness
    base = harness.load_stack()
    lib = E.library()
    ev, te = {}, []
    for tid, g in lib.items():
        z = np.load(E.GRAPHS / f"{tid}.npz")
        ev[tid] = ZeroShotEvidence(g, {k: z[k] for k in z.files})
        te.append(z["task"])
    rec = TaskRecognizer(task_ids=list(lib), text_emb=np.concatenate(te))
    rec.reset()
    return {"library": lib, "evidence": ev, "recognizer": rec, "detector": base["detector"],
            "boundary_thr": base["boundary_thr"], "offtask": None}


def run(vids=tuple(E.TEST_VIDEOS), strong: str = "openai:gpt-6.1-sol", budget_usd: float = 2.0,
        name: str = "enigma_task_given", minutes: float | None = None) -> dict:
    """Task given, one video at a time (full-length frames are large). Hard shared budget."""
    from ..experiments import _budget, make_verifier
    from .harness import decode_frames, run_clip
    from .run_all import calibrators, engine_config
    st = _stack()
    budget = _budget(max_calls=20000, max_usd=budget_usd)
    ver = make_verifier("jev", budget)
    esc = make_verifier(strong, budget, role="strong") if strong else None
    cals = {"primary": calibrators("jev"), "escalation": calibrators(strong)}
    ecfg = engine_config({})
    ann = E.annotations()
    rows = []
    for vid in vids:
        if not (FEATURES / f"enigma_{vid}.npz").exists():
            print("no features for", vid, flush=True)
            continue
        dur = float(ann["videos"][vid]["duration_seconds"])
        end = min(dur, minutes * 60) if minutes else dur
        clip = SimpleNamespace(clip_id=f"enigma_{vid}", dataset="ENIGMA-51", task_id=E.TEST_VIDEOS[vid],
                               recording=vid, video=str(video_path(vid)), start=0.0, end=end, duration=end,
                               segments=[], mistakes=lambda: [])
        frames = decode_frames(clip)
        p = run_clip(clip, st, name, ecfg, ver, esc, oracle_task=True, calibrators=cals, frames=frames)
        del frames
        rows.append(score(vid, p, end))
        print(json.dumps(rows[-1], default=float)[:400], flush=True)
    out_p = RESULTS / "enigma51" / f"{name}.json"
    prev = json.loads(out_p.read_text()) if out_p.exists() else {}
    new_vids = {r["video"] for r in rows}
    rows = [r for r in prev.get("rows", []) if r["video"] not in new_vids] + rows      # keep videos run earlier
    res = {"label": "ENIGMA-51 PROXY metrics (derived step segments; object consistency) - not human step labels",
           "strong": strong, "rows": rows,
           "mean_step_acc_derived": float(np.mean([r["step_acc_derived"] for r in rows])) if rows else None,
           "mean_object_consistency": float(np.mean([r["object_consistency"]["consistency"] for r in rows])) if rows else None,
           "mean_object_chance": float(np.mean([r["object_consistency"]["chance"] for r in rows])) if rows else None,
           "spend_usd": prev.get("spend_usd", 0.0) + budget.usd}
    # tracked spend: OpenAI calls are counted from their response cache; the rest (Jev) is recorded here, for the
    # videos of this call only, added to what earlier calls recorded
    from ..runlog import by_kind, read_log
    non_openai = prev.get("spend_usd_non_openai", 0.0)
    for r in [x for x in rows if x["video"] in new_vids]:
        for x in read_log(RUNS / name / f"enigma_{r['video']}.jsonl"):
            if x["kind"] in ("verdict", "step_choice", "task_check") and not str(x.get("model", "")).startswith("gpt-"):
                non_openai += (x.get("orig_cost_usd", x.get("cost_usd", 0.0)) or 0.0) if not x.get("cached") else 0.0
    res["spend_usd_non_openai"] = non_openai
    (RESULTS / "enigma51").mkdir(parents=True, exist_ok=True)
    (RESULTS / "enigma51" / f"{name}.json").write_text(json.dumps(res, indent=1, default=float))
    return res


def score(vid: str, log_path, end: float) -> dict:
    from ..eval import metrics as M
    from ..runlog import by_kind, read_log
    recs = read_log(log_path)
    g = E.library()[E.TEST_VIDEOS[vid]]
    inter = [x for x in E.interactions(vid) if x[0] <= end]
    segs = E.derived_segments(g, inter)
    times = np.arange(0.5, end, 0.5)
    pred = M.predicted_labels(recs, times)
    gt = np.array([next((s for a, b, s in segs if a <= t < b), "") for t in times], dtype=object)
    inside = gt != ""
    bel = by_kind(recs, "belief")
    bt = np.array([b["t"] for b in bel])

    def belief_at(t):
        j = np.searchsorted(bt, t, side="right") - 1
        return bel[j]["map"] if j >= 0 else None
    ver = by_kind(recs, "verdict")
    sc = by_kind(recs, "step_choice")
    return {"video": vid, "task_id": E.TEST_VIDEOS[vid], "minutes": end / 60, "n_steps": len(g.nodes),
            "derived_segments": len(segs), "step_acc_derived": float(((pred == gt) & inside).sum() / max(1, inside.sum())),
            "object_consistency": E.object_consistency(g, inter, belief_at),
            "commits": len(by_kind(recs, "commit")), "verifier_calls": len(ver) + len(sc),
            "strong_calls": sum(1 for v in ver if v.get("reason") == "escalation"),
            "mistake_alerts": sum(1 for a in by_kind(recs, "action") if a["action"] == "mistake"),
            "cost_usd": float(sum((v.get("orig_cost_usd", v.get("cost_usd", 0.0)) or 0.0) for v in ver)
                              + sum((x.get("cost_usd", 0.0) or 0.0) for x in sc))}

"""Train the fast local models on train-split recordings only:
  - ProbeEvidence per procedure (L4 local evidence): linear probe, frame -> step
  - TaskRecognizer (L3b): linear probe, frame -> procedure
and measure backbone quality: held-out frame-level step accuracy of a linear probe on SigLIP2 vs DINOv2
vs V-JEPA 2 (and combinations) -> results/l1/l1_quality.json. Together with l1_speed.json this is how the
per-frame and per-window backbones were picked.
"""
from __future__ import annotations

import json
import time

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from ..data.cc4d import Clip, load_manifest
from ..evidence import ProbeEvidence
from ..paths import CKPT, FEATURES, RESULTS
from .recognizer import TaskRecognizer


def _labels(clip: Clip, t: np.ndarray, ids: list[str]) -> np.ndarray:
    idx = {k: i for i, k in enumerate(ids)}
    y = np.full(len(t), -1)
    for s in clip.segments:
        if s.step in idx:
            y[(t >= s.start) & (t < s.end)] = idx[s.step]
    return y


def _load(clip_id: str) -> dict | None:
    p = FEATURES / f"{clip_id}.npz"
    if not p.exists():
        return None
    z = np.load(p)
    return {k: z[k].astype(np.float32) if z[k].dtype == np.float16 else z[k] for k in ("t", "siglip", "dino", "window", "hands")}


def collect(clips: list[Clip], ids_by_task: dict[str, list[str]], step: int = 2):
    out = {}
    for c in clips:
        z = _load(c.clip_id)
        if z is None or c.task_id not in ids_by_task:
            continue
        sl = slice(0, None, step)
        y = _labels(c, z["t"], ids_by_task[c.task_id])[sl]
        out[c.clip_id] = {"task": c.task_id, "y": y, **{k: z[k][sl] for k in ("siglip", "dino", "window", "t")}}
    return out


def fit_all(min_train_per_task: int = 1) -> dict:
    man = load_manifest()
    from ..data.cc4d import RECIPES, recipe_steps, slug
    ids = {slug(r): [s["id"] for s in recipe_steps(r)[0]] for r in RECIPES}   # == compiled graph node order
    train = collect([Clip.from_json(c) for c in man["train"]], ids)
    test = collect([Clip.from_json(c) for c in man["eval"]], ids)
    report: dict = {"n_train_recordings": {}, "probe_test_acc": {}, "backbones": {}}
    CKPT.mkdir(parents=True, exist_ok=True)
    # ---- per-task step probes (SigLIP2 frame + V-JEPA 2 window: the configured backbones)
    for tid in ids:
        tr = [v for v in train.values() if v["task"] == tid]
        report["n_train_recordings"][tid] = len(tr)
        if len(tr) < min_train_per_task:
            continue
        X = np.concatenate([np.concatenate([v["siglip"], v["window"]], 1) for v in tr])
        y = np.concatenate([v["y"] for v in tr])
        pe = ProbeEvidence.fit(ids[tid], X, y)
        pe.save(CKPT / f"probe_{tid}.pkl")
        te = [v for v in test.values() if v["task"] == tid]
        if te:
            Xt = np.concatenate([np.concatenate([v["siglip"], v["window"]], 1) for v in te])
            yt = np.concatenate([v["y"] for v in te])
            m = yt >= 0
            pred = pe.clf.predict(pe.scaler.transform(Xt[m]))
            report["probe_test_acc"][tid] = float((pred == yt[m]).mean())
    # ---- task recognizer
    tasks = sorted(ids)
    X = np.concatenate([np.concatenate([v["siglip"], v["window"]], 1)[::2] for v in train.values()])
    y = np.concatenate([[tasks.index(v["task"])] * len(v["siglip"][::2]) for v in train.values()])
    rec = TaskRecognizer(task_ids=tasks).fit(X, y)
    rec.save(CKPT / "task_recognizer.pkl")
    Xt = np.concatenate([np.concatenate([v["siglip"], v["window"]], 1) for v in test.values()])
    yt = np.concatenate([[tasks.index(v["task"])] * len(v["siglip"]) for v in test.values()])
    report["task_frame_acc_test"] = float((rec.clf.predict(rec.scaler.transform(Xt)) == yt).mean())
    # ---- backbone quality comparison (same linear probe, different inputs), pooled over tasks
    combos = {"siglip2": ["siglip"], "dinov2": ["dino"], "vjepa2": ["window"], "siglip2+vjepa2": ["siglip", "window"],
              "dinov2+vjepa2": ["dino", "window"]}
    for name, keys in combos.items():
        accs = []
        for tid in ids:
            tr = [v for v in train.values() if v["task"] == tid]
            te = [v for v in test.values() if v["task"] == tid]
            if not tr or not te:
                continue
            f = lambda vs: (np.concatenate([np.concatenate([v[k] for k in keys], 1) for v in vs]), np.concatenate([v["y"] for v in vs]))
            Xa, ya = f(tr)
            Xb, yb = f(te)
            ma, mb = ya >= 0, yb >= 0
            sc = StandardScaler().fit(Xa[ma])
            clf = LogisticRegression(C=0.5, max_iter=2000, class_weight="balanced").fit(sc.transform(Xa[ma]), ya[ma])
            accs.append(float((clf.predict(sc.transform(Xb[mb])) == yb[mb]).mean()))
        report["backbones"][name] = {"mean_heldout_step_acc": float(np.mean(accs)) if accs else None, "n_tasks": len(accs)}
        print(name, report["backbones"][name], flush=True)
    report["note"] = "linear probe on frozen features; train = official train-split recordings, test = the 48 eval clips"
    (RESULTS / "l1").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l1" / "l1_quality_and_probes.json").write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    t0 = time.time()
    r = fit_all()
    print(json.dumps({k: v for k, v in r.items() if k != "backbones"}, indent=1), time.time() - t0)

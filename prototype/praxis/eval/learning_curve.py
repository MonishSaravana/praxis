"""Learning curves: how the learned local layers change with more training recordings.

Retrains three layers on random subsets of the official train-split recordings and scores each on the same held-out
data the engine was evaluated on. Nothing here saves a checkpoint or touches the engine's results; it writes only
results/scaling/learning_curve.json. All local, $0 (teacher verdicts for the student are the cached ones).

  - L4 step probes: recordings per procedure -> held-out frame-level step accuracy (eval clips).
  - L2 event detector: total recordings -> step-boundary F1 on held-out videos and held-out procedure types.
  - L7 student: training recordings -> accuracy vs GT / AUROC / teacher agreement on the 469 held-out checks.

Usage: python -m praxis.eval.learning_curve [probes|detector|student|all]
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np

from ..data.cc4d import RECIPES, Clip, load_manifest, recipe_steps, slug
from ..paths import FEATURES, RESULTS

OUT = RESULTS / "scaling" / "learning_curve.json"
SEEDS = (0, 1, 2, 3, 4)


def _save(key: str, val) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    res = json.loads(OUT.read_text()) if OUT.exists() else {}
    res[key] = val
    OUT.write_text(json.dumps(res, indent=2, default=float))


def _train_clips(man) -> list[Clip]:
    return [c for c in (Clip.from_json(j) for j in man["train"]) if (FEATURES / f"{c.clip_id}.npz").exists()]


def probes() -> dict:
    from ..evidence import ProbeEvidence
    from ..tasks.train_probes import collect
    man = load_manifest()
    ids = {slug(r): [s["id"] for s in recipe_steps(r)[0]] for r in RECIPES}
    train = collect(_train_clips(man), ids)
    test = collect([Clip.from_json(c) for c in man["eval"]], ids)
    feat = lambda v: np.concatenate([v["siglip"], v["window"]], 1)
    rows = []
    for tid in ids:
        tr = [v for v in train.values() if v["task"] == tid]
        te = [v for v in test.values() if v["task"] == tid]
        Xt = np.concatenate([feat(v) for v in te])
        yt = np.concatenate([v["y"] for v in te])
        m = yt >= 0
        for k in range(1, len(tr) + 1):
            for seed in SEEDS:
                pick = np.random.default_rng(seed).permutation(len(tr))[:k]
                X = np.concatenate([feat(tr[i]) for i in pick])
                y = np.concatenate([tr[i]["y"] for i in pick])
                if len(set(y[y >= 0])) < 2:
                    continue
                pe = ProbeEvidence.fit(ids[tid], X, y)
                acc = float((pe.clf.predict(pe.scaler.transform(Xt[m])) == yt[m]).mean())
                rows.append({"task": tid, "k": k, "seed": seed, "n_train_avail": len(tr), "acc": acc})
                if k == len(tr):
                    break                                   # every seed picks the same full set
        print("probes", tid, len(tr), flush=True)
    res = {"desc": "held-out frame-level step accuracy of the per-procedure linear probe (SigLIP2 + V-JEPA 2) vs "
                   "number of train recordings of that procedure; random subsets, 5 seeds; eval clips only",
           "n_train_avail": {t: len([v for v in train.values() if v["task"] == t]) for t in ids}, "rows": rows}
    _save("probes", res)
    return res


def detector(sizes=(6, 12, 18, 24, 32, 40), seeds=(0, 1, 2), epochs: int = 60) -> dict:
    from ..events.train import evaluate, train, tune_threshold
    from ..experiments import _items
    man = load_manifest()
    tr = _items(_train_clips(man))
    sets = {"heldout_videos": _items([Clip.from_json(c) for c in man["eval"]]),
            "heldout_procedure_types": _items([Clip.from_json(c) for c in man["heldout_type"]])}
    rows = []
    for n in sizes:
        for seed in seeds:
            if n > len(tr):
                continue
            t0 = time.time()
            idx = np.random.default_rng(seed).permutation(len(tr))[:n]
            n_val = max(1, int(round(0.25 * n)))            # same 75/25 fit/val split as events.train.run
            val = [tr[i] for i in idx[:n_val]]
            fit = [tr[i] for i in idx[n_val:]]
            det, _ = train(fit, val, epochs=epochs, seed=seed, log_every=10_000)
            thr = tune_threshold(det, val)
            row = {"n_recordings": n, "seed": seed, "thr": thr, "train_s": time.time() - t0}
            for name, items in sets.items():
                for tol in (2.0, 5.0):
                    r = evaluate(det, items, thr, tol=tol)
                    row[f"{name}_tol{int(tol)}s"] = {k: r[k] for k in ("precision", "recall", "f1")}
            rows.append(row)
            print("detector", n, seed, round(row["heldout_videos_tol5s"]["f1"], 3),
                  round(row["heldout_procedure_types_tol5s"]["f1"], 3), round(row["train_s"]), "s", flush=True)
            if n == len(tr):
                break
    res = {"desc": "L2 event detector retrained on random subsets of train recordings (75% fit / 25% val for early "
                   "stopping and threshold); step-boundary F1 on held-out eval clips and held-out procedure types",
           "n_train_avail": len(tr), "rows": rows}
    _save("detector", res)
    return res


def student(fracs=(0.125, 0.25, 0.5, 0.75, 1.0)) -> dict:
    from sklearn.metrics import roc_auc_score
    from ..eval.verifier_eval import fit_calibrators, load
    from ..flywheel.distill import featurize, predict, train_student
    from ..verify.calibration import raw_p_complete
    teacher = "claude_strong"
    cal = fit_calibrators(teacher)
    tr, te = load(f"{teacher}_train"), load(f"{teacher}_eval")
    Xtr, ktr = featurize(tr)
    Xte, kte = featurize(te)
    tr, te = [tr[i] for i in ktr], [te[i] for i in kte]
    p_raw = lambda rows: np.array([raw_p_complete(r["verdict"]["step_status"], r["verdict"]["confidence"]) for r in rows])
    yt_tr = cal[0](p_raw(tr)) if cal else p_raw(tr)
    yg_tr = np.array([r["y_complete"] for r in tr], float)
    pt = cal[0](p_raw(te)) if cal else p_raw(te)
    y = np.array([r["y_complete"] for r in te])
    clips = sorted({r["clip_id"] for r in tr})
    clip_of = np.array([r["clip_id"] for r in tr])
    rows = []
    for f in fracs:
        n = max(1, int(round(f * len(clips))))
        for seed in SEEDS:
            pick = set(np.random.default_rng(seed).permutation(clips)[:n])
            m = np.isin(clip_of, list(pick))
            st, _ = train_student(Xtr[m], yt_tr[m], yg_tr[m], alpha=0.5, seed=seed)
            ps = predict(st, Xte)
            rows.append({"n_recordings": n, "n_checks": int(m.sum()), "seed": seed,
                         "acc_vs_gt": float(((ps >= 0.5) == (y == 1)).mean()),
                         "auroc": float(roc_auc_score(y, ps)),
                         "agreement": float(((ps >= 0.5) == (pt >= 0.5)).mean())})
            if n == len(clips):
                break
        print("student", n, flush=True)
    res = {"desc": "L7 student retrained on checks from random subsets of train recordings; scored on the same "
                   "held-out eval checks as results/l7/distill.json",
           "n_train_recordings": len(clips), "n_train_checks": len(tr), "n_test_checks": len(te),
           "teacher_acc_vs_gt": float(((pt >= 0.5) == (y == 1)).mean()),
           "teacher_auroc": float(roc_auc_score(y, pt)), "rows": rows}
    _save("student", res)
    return res


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    t0 = time.time()
    for name, fn in (("probes", probes), ("student", student), ("detector", detector)):
        if which in (name, "all"):
            fn()
    print("done in", round(time.time() - t0), "s")

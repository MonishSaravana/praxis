"""How well does Praxis track a procedure a company just compiled, and what helps? ($0: offline, local tracking only.)

Six CaptainCook4D pinwheels eval clips with human step labels; precomputed L1 features; task given (locked mode); no
verifier calls, so this isolates the local tracker. The company graph is the knowledge backend's compile of a recipe
card written from the dataset's public recipe text (company "Test Kitchen"), with its step ids mapped to the dataset's
step ids for scoring. Two questions:

  frames   a busy machine processes fewer frames: keep 100% / 40% / 15% (the two live runs processed 40% and 15%),
           thinned uniformly; a second with no frame runs no tick, like the live loop.
  refs     a company can upload a recording of someone doing the job. Train the procedure's local probe on 1 or 3
           reference recordings (pinwheels TRAIN clips, never the eval clips), labelled either by a person (the
           dataset's step labels) or automatically (frames aligned in order to the compiled steps' end-state text).

    python -m praxis.eval.company_tracking      -> results/backend/company_tracking.json
"""
from __future__ import annotations

import json
from dataclasses import replace
from graphlib import TopologicalSorter

import numpy as np

from ..data import cc4d
from ..data.cc4d import Clip, load_manifest
from ..engine import Engine, EngineConfig
from ..evidence import ProbeEvidence, ZeroShotEvidence
from ..knowledge.store import Org
from ..knowledge.video import align
from ..paths import RESULTS, RUNS
from ..perception.extract import load_features
from ..runlog import RunLog
from ..tasks.schema import TaskGraph
from . import harness
from . import metrics as M
from .run_all import commit_p, tuned_policy, tuned_tracker

TASK = "cc4d_pinwheels"


def company_graph(org_id: str = "test-kitchen-captaincook4d"):
    """The backend-compiled recipe-card graph with ids mapped to the dataset's step ids (the card listed the recipe's
    steps in this topological order), and its zero-shot evidence."""
    st, ed = cc4d.recipe_steps("Pinwheels")
    by = {s["id"]: s for s in st}
    ts = TopologicalSorter({s["id"]: set() for s in st})
    for a, b in ed:
        if a in by and b in by and a != b:
            ts.add(b, a)
    remap = {f"s{i + 1}": sid for i, sid in enumerate(ts.static_order())}
    org = Org(org_id)
    x = org.load_version(org.procedures()[0]["id"], 1)
    g = TaskGraph.model_validate(json.loads(x["graph"].model_dump_json()))
    for nd in g.nodes:
        nd.id = remap[nd.id]
        nd.successors = [remap[s] for s in nd.successors]
        nd.dataset_labels = [nd.id]
    g.start, g.task_id = [remap[s] for s in g.start], TASK
    z = np.load(x["emb"])
    emb = {k: z[k] for k in z.files}
    return g, ZeroShotEvidence(g, emb), emb


def run(stack, clip: Clip, graph, ev, keep: float, name: str) -> dict:
    feats, _ = load_features(clip.clip_id)
    if len(feats.t) and feats.t[-1] > clip.duration + 0.5:
        m = feats.t <= clip.duration
        feats = replace(feats, t=feats.t[m], frame=feats.frame[m], hands=feats.hands[m], window=feats.window[m],
                        change=feats.change[m])
    scores = stack["detector"].score(feats)
    if keep < 1.0:
        idx = np.unique(np.round(np.arange(0, len(feats.t), 1.0 / keep)).astype(int))
        idx = idx[idx < len(feats.t)]
        feats = replace(feats, t=feats.t[idx], frame=feats.frame[idx], hands=feats.hands[idx], window=feats.window[idx],
                        change=feats.change[idx])
        scores = {k: v[idx] for k, v in scores.items()}
    cfg = EngineConfig(tracker=tuned_tracker(), policy=tuned_policy(), commit_on_switch_p=commit_p(),
                       boundary_thr=stack["boundary_thr"])
    out = RUNS / "company_tracking" / name / f"{clip.clip_id}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with RunLog(out, {"clip": clip.clip_id, "keep": keep, "condition": name}) as log:
        eng = Engine(cfg, {TASK: graph}, {TASK: ev}, None, stack["detector"], None, None, None, None, log, task_id=TASK)
        t, tick = feats.t, 1.0
        while tick <= clip.duration + 1e-6:
            m = (t > tick - 1.0) & (t <= tick)
            if m.any():
                eng.tick(tick, {"t": t[m], "frame": feats.frame[m], "window": feats.window[m], "hands": feats.hands[m],
                                "boundary": scores["boundary"][m], "grasp": scores["grasp"][m]}, lambda _x: None)
            tick += 1.0
        eng.finish(clip.duration)
        log.write("summary", clip.duration, n_frames=int(len(t)), escalated_frames=0)
    r = harness.score_clip(clip, out)
    recs = [json.loads(line) for line in open(out)]
    r["commits"] = sum(q["kind"] == "commit" for q in recs)
    r["instructs"] = sum(q["kind"] == "action" and q.get("action") == "instruct" for q in recs)
    return r


def reference_probe(g, emb: dict, clips: list[Clip], labels: str) -> ProbeEvidence:
    E = emb["end_state"] + 0.5 * emb["name"]
    E = E / np.linalg.norm(E, axis=1, keepdims=True)
    X, y = [], []
    for c in clips:
        f, _ = load_features(c.clip_id)
        if labels == "human":
            lab = M.frame_labels([(s.start, s.end, s.step) for s in c.segments], f.t, between="none")
            yi = np.array([g.ids.index(v) if v in g.ids else -1 for v in lab])
        else:                                  # in-order alignment of frames to the compiled end states, no labels
            spans = align(E @ (f.frame / np.linalg.norm(f.frame, axis=1, keepdims=True)).T)
            yi = np.full(len(f.t), -1)
            for k, (a, b) in enumerate(spans):
                yi[a:b] = k
        X.append(ProbeEvidence.featurize(f.frame, f.window))
        y.append(yi)
    return ProbeEvidence.fit(g.ids, np.concatenate(X), np.concatenate(y))


def summarize(name: str, keep: float, res: list[dict]) -> dict:
    return {"condition": name, "frames_kept": keep, "step_acc": round(float(np.mean([r["step_acc"] for r in res])), 3),
            "per_clip": [round(r["step_acc"], 2) for r in res],
            "commits_mean": round(float(np.mean([r["commits"] for r in res])), 1),
            "instructs_mean": round(float(np.mean([r["instructs"] for r in res])), 1)}


def main() -> dict:
    stack = harness.load_stack()
    man = load_manifest()
    evals = [Clip.from_json(c) for c in man["eval"] if c["task_id"] == TASK]
    trains = [Clip.from_json(c) for c in man["train"] if c["task_id"] == TASK]
    g, zs, emb = company_graph()
    conds = {"built-in graph, trained on 6 labelled recordings": (stack["library"][TASK], stack["evidence"][TASK]),
             "company graph, document only (zero-shot)": (g, zs)}
    for n in (1, 3):
        for labels in ("automatic", "human"):
            conds[f"company graph + {n} reference recording(s), {labels} step labels"] = (g, reference_probe(g, emb, trains[:n], labels))
    rows = []
    for name, (graph, ev) in conds.items():
        keeps = (1.0, 0.4, 0.15) if "reference" not in name else (1.0, 0.4)
        for keep in keeps:
            res = [run(stack, c, graph, ev, keep, f"c{len(rows)}") for c in evals]
            rows.append(summarize(name, keep, res))
            print(json.dumps(rows[-1]), flush=True)
    out = {"label": "offline, local tracking only (no verifier), task given; 6 CaptainCook4D pinwheels eval clips with human "
                    "step labels; company graph = knowledge-backend compile of a recipe card; references = train clips",
           "eval_clips": [c.clip_id for c in evals], "reference_clips": [c.clip_id for c in trains[:3]], "rows": rows}
    (RESULTS / "backend").mkdir(parents=True, exist_ok=True)
    (RESULTS / "backend" / "company_tracking.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()

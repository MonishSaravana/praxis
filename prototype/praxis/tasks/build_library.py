"""Build the task-graph library for the eval procedures.

Inputs per procedure (all from the dataset's TRAIN split or its public recipe text, never test labels):
  - step list + ordering constraints (the dataset's published recipe task graph)
  - duration priors: lognormal moments of each step's duration over train-split recordings
  - mistake hints: error categories + descriptions annotated on train-split recordings
The compiler (L3) enriches these into typed nodes; duration priors are then overwritten with the fitted
train-split statistics (n > 0, source = dataset-train-split).
"""
from __future__ import annotations

import collections
import json

import numpy as np

from ..data import cc4d
from ..paths import RESULTS, TASKGRAPHS
from .compiler import compile_procedure, embed_graph, save_graph
from .schema import DurationPrior, TaskGraph


def train_stats(recipe: str) -> tuple[dict[str, list[float]], list[str]]:
    cs, err, sp, _ = cc4d._load()
    durs: dict[str, list[float]] = collections.defaultdict(list)
    hints: collections.Counter = collections.Counter()
    for rid, d in cs.items():
        if d["activity_name"] != recipe or sp.get(rid) != "train":
            continue
        segs, _ = cc4d.recording_segments(rid, cs, err)
        for s in segs:
            durs[s.step].append(s.end - s.start)
            for e in s.errors:
                desc = (e.get("description") or "").strip()
                if e["tag"] != "Missing Step" and desc and desc.lower() != "none":
                    hints[f"[{s.name}] {e['tag']}: {desc}"] += 1
    return durs, [h for h, _ in hints.most_common(40)]


def duration_prior(xs: list[float]) -> DurationPrior | None:
    xs = [x for x in xs if x > 0.5]
    if len(xs) < 2:
        return None
    return DurationPrior(mean_s=float(np.mean(xs)), std_s=float(np.std(xs, ddof=1)), n=len(xs), source="dataset-train-split")


def compile_recipe(recipe: str, model: str) -> TaskGraph:
    steps, edges = cc4d.recipe_steps(recipe)
    durs, hints = train_stats(recipe)
    src = f"Recipe: {recipe}.\n" + "\n".join(f"{i + 1}. {s['raw']}" for i, s in enumerate(steps))
    g = compile_procedure(cc4d.slug(recipe), "cooking", src, [{"id": s["id"], "name": s["name"]} for s in steps],
                          ordering=edges, mistake_hints=hints, model=model,
                          source=f"CaptainCook4D recipe text + task graph ({recipe}); mistake hints from train split")
    for n in g.nodes:
        dp = duration_prior(durs.get(n.id, []))
        if dp is not None:
            n.duration = dp
    return g


def build(model: str = "claude-fable-5-1", recipes: list[str] | None = None, overwrite: bool = False) -> dict:
    from ..perception.backbones import SigLIP
    sig = None
    out = {}
    for r in recipes or cc4d.RECIPES:
        tid = cc4d.slug(r)
        p = TASKGRAPHS / f"{tid}.json"
        if p.exists() and not overwrite:
            g = TaskGraph.load(p)
        else:
            try:
                g = compile_recipe(r, model)
            except Exception as e:  # strongest model refused / unavailable -> Opus fallback, recorded in the graph
                print(f"{r}: {model} failed ({type(e).__name__}: {str(e)[:120]}), falling back to claude-opus-5-5")
                g = compile_recipe(r, "claude-opus-5-5")
        sig = sig or SigLIP()
        save_graph(g, embed_graph(g, sig))
        out[tid] = {"title": g.title, "nodes": len(g.nodes), "mistakes": sum(len(n.mistakes) for n in g.nodes),
                    "checks": sum(len(n.checks) for n in g.nodes), "compiler": g.compiler,
                    "duration_priors_from_train": sum(1 for n in g.nodes if n.duration and n.duration.n > 0)}
        print(tid, json.dumps(out[tid]), flush=True)
    (RESULTS / "l3").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l3" / "compile_summary.json").write_text(json.dumps(out, indent=2))
    return out


def dataset_graph(recipe: str) -> TaskGraph:
    """Uncompiled graph straight from the dataset (ids, names, ordering, train-split duration priors).
    Used only until the L3 compiler has run (it has no instructions/checks/mistakes); flagged in `compiler`."""
    from .schema import Node
    steps, edges = cc4d.recipe_steps(recipe)
    durs, _ = train_stats(recipe)
    succ = {s["id"]: sorted({b for a, b in edges if a == s["id"]}) for s in steps}
    has_pred = {b for _, b in edges}
    nodes = [Node(id=s["id"], name=s["name"], instruction_novice=s["name"], instruction_expert=s["name"],
                  end_state=s["name"], successors=succ[s["id"]], duration=duration_prior(durs.get(s["id"], [])),
                  dataset_labels=[s["id"]]) for s in steps]
    return TaskGraph(task_id=cc4d.slug(recipe), title=recipe, domain="cooking", source="dataset step list (uncompiled)",
                     nodes=nodes, start=[s["id"] for s in steps if s["id"] not in has_pred] or [steps[0]["id"]],
                     compiler={"model": None, "note": "uncompiled dataset graph; replaced by L3 output once compiled"})

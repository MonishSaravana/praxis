"""L3 · Procedure compiler (ours; uses a frontier Claude model offline, results cached + committed).
Default: Claude Opus 5.5. The 9 graphs in the current library were compiled with Claude Fable 5.1
(`results/l3/compile_summary.json`); they are kept as compiled because every evaluation used them.

Instruction text (a manual, recipe, tutorial transcript, or a dataset's step list) -> typed TaskGraph.

The compiler is run once per procedure, offline. Its output is the reusable asset: L3b recognizes tasks
by matching against the library of compiled graphs, L4 tracks over their nodes, L5 asks their checks,
L6 speaks their instructions and corrections. Node end states are also embedded with the SigLIP2 text
encoder so L4 can do zero-shot local matching without any training video.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import anthropic
import numpy as np

from ..paths import TASKGRAPHS, load_env
from ..verify.common import cost_usd
from .schema import Check, DurationPrior, Mistake, Node, TaskGraph

PROMPT_VERSION = "compile-v1"

SYSTEM = """You compile procedures into typed task graphs for Praxis, a first-person (smart-glasses) coach
that watches a person do a physical task, tracks which step they are on, verifies steps from camera
frames, catches mistakes, and gives spoken guidance.

For each step produce:
- instruction_novice: one or two short spoken sentences for a first-timer (which part, where it goes, how).
- instruction_expert: a terse cue, max 6 words.
- substeps: 2-4 finer sub-steps, used when the person is struggling.
- parts: parts / tools / ingredients handled in this step.
- end_state: one sentence describing what the camera sees when the step is done (concrete, visual).
- view_hint: where the camera should look to verify it (e.g. "the underside of the chassis, front right").
- checks: 1-3 yes/no questions answerable from a first-person frame; "yes" means the check passes.
  kind is one of completion|orientation|part_identity|presence|alignment|quantity|other; roi names the
  region to zoom into for fine checks.
- mistakes: 1-4 realistic, visually detectable mistakes for this step. Each with type (wrong_part,
  wrong_orientation, wrong_order, missing_step, incomplete, wrong_quantity, technique, other), description,
  visual_cue (what a camera sees), correction (a specific spoken fix, e.g. "That wheel is on backwards,
  flip it before you screw it in."), and early_cue (an earlier visible sign, e.g. the wrong part being
  picked up) or "" if none.
- duration_guess_s: typical seconds for a novice.
Keep step ids exactly as given. Use the given ordering constraints for successors when provided;
otherwise infer a sensible partial order (a step's successors are steps that can start right after it).
Write everything in plain, friendly English. Be concrete; never invent steps that are not in the source."""


def _schema() -> dict:
    s = {"type": "string"}
    check = {"type": "object", "additionalProperties": False, "required": ["id", "question", "kind", "roi"],
             "properties": {"id": s, "question": s, "roi": s,
                            "kind": {"type": "string", "enum": ["completion", "orientation", "part_identity", "presence",
                                                                "alignment", "quantity", "other"]}}}
    mistake = {"type": "object", "additionalProperties": False,
               "required": ["id", "type", "description", "visual_cue", "correction", "early_cue"],
               "properties": {"id": s, "description": s, "visual_cue": s, "correction": s, "early_cue": s,
                              "type": {"type": "string", "enum": ["wrong_part", "wrong_orientation", "wrong_order",
                                                                 "missing_step", "incomplete", "wrong_quantity",
                                                                 "technique", "other"]}}}
    node = {"type": "object", "additionalProperties": False,
            "required": ["id", "name", "instruction_novice", "instruction_expert", "substeps", "parts", "end_state",
                         "view_hint", "checks", "mistakes", "successors", "duration_guess_s"],
            "properties": {"id": s, "name": s, "instruction_novice": s, "instruction_expert": s,
                           "substeps": {"type": "array", "items": s}, "parts": {"type": "array", "items": s},
                           "end_state": s, "view_hint": s, "checks": {"type": "array", "items": check},
                           "mistakes": {"type": "array", "items": mistake}, "successors": {"type": "array", "items": s},
                           "duration_guess_s": {"type": "number"}}}
    return {"type": "object", "additionalProperties": False, "required": ["title", "summary", "nodes", "start"],
            "properties": {"title": s, "summary": s, "nodes": {"type": "array", "items": node},
                           "start": {"type": "array", "items": s}}}


def compile_procedure(task_id: str, domain: str, source_text: str, steps: list[dict],
                      ordering: list[tuple[str, str]] | None = None, mistake_hints: list[str] | None = None,
                      model: str = "claude-opus-5-5", draft: bool = False, source: str = "", effort: str = "high",
                      on_progress=None) -> TaskGraph:
    """steps: [{"id": ..., "name": ...}] in nominal order. ordering: (before, after) edges if known.
    on_progress(n_chars): called as the graph streams in (Praxis Studio shows it as a progress indicator)."""
    load_env()
    client = anthropic.Anthropic(timeout=900, max_retries=2)
    user = [f"Task id: {task_id}\nDomain: {domain}\n\nSource procedure:\n{source_text}\n",
            "Steps (keep these ids):\n" + "\n".join(f"- {s['id']}: {s['name']}" for s in steps)]
    if ordering:
        user.append("Ordering constraints (before -> after):\n" + "\n".join(f"- {a} -> {b}" for a, b in ordering))
    if mistake_hints:
        user.append("Mistake types people commonly make on this kind of task (hints):\n" + "\n".join(f"- {m}" for m in mistake_hints))
    t0 = time.perf_counter()
    kw = dict(model=model, max_tokens=32000, system=SYSTEM,
              messages=[{"role": "user", "content": "\n\n".join(user)}],
              output_config={"format": {"type": "json_schema", "schema": _schema()}, "effort": effort})
    with client.messages.stream(**kw) as stream:
        if on_progress is not None:
            n = 0
            for chunk in stream.text_stream:
                n += len(chunk)
                on_progress(n)
        resp = stream.get_final_message()
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"compiler refusal for {task_id}")
    data = json.loads(next(b.text for b in resp.content if b.type == "text"))
    u = resp.usage
    usd = cost_usd(model, u.input_tokens, u.output_tokens)
    given = {s["id"] for s in steps}
    nodes = []
    for n in data["nodes"]:
        if n["id"] not in given:
            continue
        nodes.append(Node(
            id=n["id"], name=n["name"], instruction_novice=n["instruction_novice"], instruction_expert=n["instruction_expert"],
            substeps=n["substeps"], parts=n["parts"], end_state=n["end_state"], view_hint=n["view_hint"],
            checks=[Check(id=c["id"], question=c["question"], kind=c["kind"], roi=c["roi"] or None) for c in n["checks"]],
            mistakes=[Mistake(id=m["id"], type=m["type"], description=m["description"], visual_cue=m["visual_cue"],
                              correction=m["correction"], early_cue=m["early_cue"] or None) for m in n["mistakes"]],
            successors=[s for s in n["successors"] if s in given and s != n["id"]],
            duration=DurationPrior(mean_s=float(n["duration_guess_s"]), std_s=0.6 * float(n["duration_guess_s"]), n=0,
                                   source="compiler"),
            dataset_labels=[n["id"]]))
    order = {s["id"]: i for i, s in enumerate(steps)}
    nodes.sort(key=lambda n: order[n.id])          # node order == given step order (probes rely on it)
    missing = given - {n.id for n in nodes}
    if missing:
        err = RuntimeError(f"compiler dropped steps {missing}")
        err.usage, err.cost_usd, err.raw = u, usd, data      # callers can record the spend and inspect the output
        raise err
    if ordering:   # enforce known constraints exactly (the compiler only enriches)
        succ = {n.id: set() for n in nodes}
        for a, b in ordering:
            succ[a].add(b)
        for n in nodes:
            n.successors = sorted(succ[n.id])
    start = [s for s in data["start"] if s in given] or [steps[0]["id"]]
    if ordering:
        has_pred = {b for _, b in ordering}
        start = [s["id"] for s in steps if s["id"] not in has_pred]
    return TaskGraph(task_id=task_id, title=data["title"], domain=domain, summary=data["summary"], source=source,
                     draft=draft, nodes=nodes, start=start,
                     compiler={"model": model, "prompt_version": PROMPT_VERSION, "effort": effort, "cost_usd": usd,
                               "latency_s": time.perf_counter() - t0, "input_tokens": u.input_tokens,
                               "output_tokens": u.output_tokens})


def embed_graph(g: TaskGraph, siglip) -> dict[str, np.ndarray]:
    """SigLIP2 text embeddings of each node's end state and name (for zero-shot local matching in L4)."""
    end = siglip.texts([f"a first-person photo: {n.end_state}" for n in g.nodes])
    name = siglip.texts([f"a person's hands: {n.name}" for n in g.nodes])
    task = siglip.texts([f"a first-person video of someone doing this task: {g.title}"])
    return {"end_state": end, "name": name, "task": task}


def save_graph(g: TaskGraph, emb: dict | None = None, out_dir: Path = TASKGRAPHS) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{g.task_id}.json"
    g.save(p)
    if emb is not None:
        from ..paths import DATA
        (DATA / "taskgraph_emb").mkdir(parents=True, exist_ok=True)
        np.savez(DATA / "taskgraph_emb" / f"{g.task_id}.npz", **emb)
    return p


def load_library(out_dir: Path = TASKGRAPHS) -> dict[str, TaskGraph]:
    return {p.stem: TaskGraph.load(p) for p in sorted(out_dir.glob("*.json"))}

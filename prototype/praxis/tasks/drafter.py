"""L3 · Open-set drafting (ours). The person is doing something that isn't in the library: draft a light typed task
graph from what the camera has seen so far (and, if given, what the person says they are doing), so Praxis can
start tracking right away instead of staying silent.

A draft has steps, spoken instructions, visual end states (embedded for zero-shot local matching in L4), duration
guesses and one completion check per step. It has no mistake library: the offline compiler
(`tasks/compiler.py`) can enrich it later. Drafts are marked `draft=True` and announced as drafts.
"""
from __future__ import annotations

import hashlib
import json
import time

import numpy as np

from ..verify.common import ResponseCache, b64, cost_usd, sharpness, to_jpeg
from .schema import Check, DurationPrior, Node, TaskGraph

DRAFT_VERSION = "draft-v1"

SYSTEM = """You help Praxis, a first-person (smart-glasses) coach, with a task it has no plan for. You see a few
frames of what the person has done so far, oldest first. Identify the procedure and draft its steps from start to
finish, including the steps that haven't happened yet.

For each step give:
- name: a short imperative, at most 8 words.
- instruction_novice: one or two short spoken sentences for a first-timer.
- instruction_expert: a terse cue, at most 6 words.
- end_state: one concrete sentence describing what the camera sees when the step is done.
- duration_guess_s: typical seconds for a novice.

Use 5 to 20 steps in a typical order, at the level of detail a recipe card or manual would use. Only include
steps that are typical of this procedure. Set confidence (0 to 1) to how sure you are what the task is."""


def _schema() -> dict:
    s = {"type": "string"}
    step = {"type": "object", "additionalProperties": False,
            "required": ["name", "instruction_novice", "instruction_expert", "end_state", "duration_guess_s"],
            "properties": {"name": s, "instruction_novice": s, "instruction_expert": s, "end_state": s,
                           "duration_guess_s": {"type": "number"}}}
    return {"type": "object", "additionalProperties": False,
            "required": ["title", "domain", "summary", "confidence", "steps"],
            "properties": {"title": s, "summary": s, "confidence": {"type": "number"},
                           "domain": {"type": "string", "enum": ["cooking", "assembly", "maintenance", "other"]},
                           "steps": {"type": "array", "items": step}}}


def keyframes_for_draft(frame_at, t0: float, t1: float, n: int = 8) -> list[np.ndarray]:
    """The sharpest frame in each of n equal bins over [t0, t1] (temporal coverage, not just the latest moment)."""
    edges = np.linspace(t0, t1, n + 1)
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        cands = [f for f in (frame_at(x) for x in np.arange(a, b, 0.5)) if f is not None]
        if cands:
            out.append(max(cands, key=sharpness))
    return out


def draft_task(frames: list[np.ndarray], hint: str | None = None, model: str = "claude-opus-5-5",
               effort: str = "medium") -> TaskGraph:
    """frames: RGB keyframes, oldest first. hint: what the person said they are doing (optional)."""
    import anthropic
    from ..paths import load_env
    load_env()
    jpgs = [to_jpeg(f, max_side=640) for f in frames]
    user = [{"type": "text", "text": f"{len(jpgs)} frames from the person's head-mounted camera, oldest first."}]
    for j in jpgs:
        user.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64(j)}})
    user.append({"type": "text", "text": (f"The person says they are doing: {hint}\n" if hint else "")
                 + "Draft the task graph."})
    cache = ResponseCache(f"draft_{model}")
    key = ResponseCache.key(DRAFT_VERSION, model, effort, hint or "", [hashlib.sha256(j).hexdigest() for j in jpgs])
    hit = cache.get(key)
    if hit is None:
        client = anthropic.Anthropic(timeout=300, max_retries=2)
        t0 = time.perf_counter()
        with client.messages.stream(model=model, max_tokens=16000, system=SYSTEM,
                                    messages=[{"role": "user", "content": user}],
                                    output_config={"format": {"type": "json_schema", "schema": _schema()},
                                                   "effort": effort}) as stream:
            resp = stream.get_final_message()
        if resp.stop_reason == "refusal":
            raise RuntimeError("drafter refusal")
        data = json.loads(next(b.text for b in resp.content if b.type == "text"))
        u = resp.usage
        hit = {"data": data, "latency_s": time.perf_counter() - t0, "input_tokens": u.input_tokens,
               "output_tokens": u.output_tokens, "cost_usd": cost_usd(model, u.input_tokens, u.output_tokens)}
        cache.put(key, hit)
        cached = False
    else:
        cached = True
    d = hit["data"]
    steps = d["steps"]
    nodes = []
    for i, st in enumerate(steps):
        nid = f"d{i + 1}"
        g = max(float(st["duration_guess_s"]), 5.0)
        nodes.append(Node(id=nid, name=st["name"], instruction_novice=st["instruction_novice"],
                          instruction_expert=st["instruction_expert"], end_state=st["end_state"],
                          checks=[Check(id=f"{nid}c1", question=f"Is this step done: {st['name']}?", kind="completion")],
                          successors=[f"d{i + 2}"] if i + 1 < len(steps) else [],
                          duration=DurationPrior(mean_s=g, std_s=0.6 * g, n=0, source="draft")))
    tid = "draft_" + key[:10]
    return TaskGraph(task_id=tid, title=d["title"], domain=d["domain"], summary=d["summary"], draft=True,
                     source=f"open-set draft from {len(jpgs)} frames" + (f" + the person's description '{hint}'" if hint else ""),
                     nodes=nodes, start=["d1"],
                     compiler={"model": model, "prompt_version": DRAFT_VERSION, "effort": effort,
                               "cost_usd": hit["cost_usd"], "latency_s": hit["latency_s"], "cached": cached,
                               "input_tokens": hit["input_tokens"], "output_tokens": hit["output_tokens"],
                               "confidence": d["confidence"]})


class Drafter:
    """Engine hook: frames -> (draft graph, zero-shot evidence for it). Holds the SigLIP2 text encoder."""

    def __init__(self, siglip=None, hint: str | None = None, model: str = "claude-opus-5-5"):
        self._sig, self.hint, self.model = siglip, hint, model

    def __call__(self, frames: list[np.ndarray]):
        from ..evidence import ZeroShotEvidence
        from .compiler import embed_graph
        g = draft_task(frames, hint=self.hint, model=self.model)
        if self._sig is None:
            from ..perception.backbones import SigLIP
            self._sig = SigLIP()
        return g, ZeroShotEvidence(g, embed_graph(g, self._sig))

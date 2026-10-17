"""Telling Studio the task: match what the person typed to the library, or compile pasted instructions into a typed
task graph with the existing L3 compiler (Claude Opus 5.5), as a background job with progress. Compiled graphs are
cached by the text's hash under sessions/library/ (gitignored)."""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import threading
import time
import uuid

import numpy as np

from .core import USER_LIB, StudioCore

STOP = {"i", "im", "i'm", "am", "making", "make", "doing", "do", "a", "an", "the", "some", "with", "and", "of", "my",
        "to", "for", "cooking", "cook", "preparing", "prepare", "assembling", "assemble", "building", "build", "fried"}


def _tokens(s: str) -> set[str]:
    s = re.sub(r"\(.*?\)", " ", s.lower())
    return {w for w in re.findall(r"[a-z]+", s) if w not in STOP and len(w) > 2}


def match_library(text: str, library: list[dict]) -> str | None:
    """A library task the description clearly names, else None. Conservative: every content word of the title's
    main part must appear in the description, or the strings must be nearly identical."""
    d = _tokens(text)
    best, best_score = None, 0.0
    for t in library:
        core = _tokens(t["title"])
        if not core:
            continue
        overlap = len(core & d) / len(core)
        ratio = difflib.SequenceMatcher(None, " ".join(sorted(d)), " ".join(sorted(core))).ratio()
        score = max(overlap, ratio)
        if score > best_score:
            best, best_score = t["task_id"], score
    return best if best_score >= 0.8 else None


SPLIT_SYSTEM = """Split procedure instructions into steps for Praxis, a first-person (smart-glasses) coach that tracks
which step a person is on from camera frames. Return a short title, the domain, and the steps in order, each a short
imperative name of at most 8 words. Use the source's own steps when it has them; merge trivial sub-actions; drop
steps that aren't physical actions (e.g. "enjoy"). Use 3 to 20 steps."""


def _split_steps(text: str, model: str = "claude-opus-5-5") -> tuple[dict, float]:
    import anthropic
    from ..verify.common import cost_usd
    client = anthropic.Anthropic(timeout=120, max_retries=2)
    schema = {"type": "object", "additionalProperties": False, "required": ["title", "domain", "steps"],
              "properties": {"title": {"type": "string"},
                             "domain": {"type": "string", "enum": ["cooking", "assembly", "maintenance", "other"]},
                             "steps": {"type": "array", "items": {"type": "string"}}}}
    resp = client.messages.create(model=model, max_tokens=4000, system=SPLIT_SYSTEM,
                                  messages=[{"role": "user", "content": text}],
                                  output_config={"format": {"type": "json_schema", "schema": schema}, "effort": "low"})
    data = json.loads(next(b.text for b in resp.content if b.type == "text"))
    return data, cost_usd(model, resp.usage.input_tokens, resp.usage.output_tokens)


class CompileJob:
    """Pasted instructions -> steps (fast call) -> typed graph (L3 compiler, streamed) -> SigLIP2 text embeddings."""

    def __init__(self, core: StudioCore, text: str, effort: str = "medium"):
        self.core, self.text, self.effort = core, text.strip(), effort
        self.id = uuid.uuid4().hex[:8]
        self.key = hashlib.sha256(self.text.encode()).hexdigest()[:12]
        self.state, self.chars, self.error = "queued", 0, None
        self.t0 = time.time()
        self.t_done = None
        self.task_id = f"user_{self.key}"
        self.title, self.n_steps, self.cost_usd, self.cached = None, None, 0.0, False
        threading.Thread(target=self._run, daemon=True).start()

    def status(self) -> dict:
        return {"id": self.id, "state": self.state, "chars": self.chars, "error": self.error,
                "elapsed_s": round((self.t_done or time.time()) - self.t0, 1), "task_id": self.task_id,
                "title": self.title, "n_steps": self.n_steps, "cost_usd": round(self.cost_usd, 4), "cached": self.cached}

    def _run(self) -> None:
        from ..evidence import ZeroShotEvidence
        from ..tasks.compiler import compile_procedure, embed_graph
        try:
            if not self.text:
                raise ValueError("no instructions given")
            if self.task_id in self.core.user_graphs:          # same text compiled before: reuse it
                g = self.core.user_graphs[self.task_id]
                self.title, self.n_steps, self.cached = g.title, len(g.nodes), True
                self.state = "done"
                return
            self.state = "splitting"
            data, c1 = _split_steps(self.text)
            steps = [{"id": f"s{i + 1}", "name": n} for i, n in enumerate(data["steps"][:20])]
            if len(steps) < 2:
                raise ValueError("couldn't find at least two steps in the instructions")
            self.cost_usd += c1
            self.title = data["title"]
            self.state = "compiling"

            def prog(n):
                self.chars = n
            g = compile_procedure(self.task_id, data["domain"], self.text, steps, model="claude-opus-5-5",
                                  source="pasted instructions (Praxis Studio)", effort=self.effort, on_progress=prog)
            self.cost_usd += g.compiler.get("cost_usd", 0.0)
            g.compiler["split_cost_usd"] = c1
            self.state = "embedding"
            emb = embed_graph(g, self.core.texts())
            USER_LIB.mkdir(parents=True, exist_ok=True)
            g.save(USER_LIB / f"{g.task_id}.json")
            np.savez(USER_LIB / f"{g.task_id}.npz", **emb)
            (USER_LIB / f"{g.task_id}.source.txt").write_text(self.text)
            self.core.add_user_graph(g, ZeroShotEvidence(g, emb))
            self.title, self.n_steps = g.title, len(g.nodes)
            self.state = "done"
        except Exception as e:  # noqa: BLE001
            self.error, self.state = str(e)[:300], "error"
        finally:
            self.t_done = time.time()

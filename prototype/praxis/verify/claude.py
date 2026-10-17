"""L5 · ClaudeVerifier (rented, swappable) + StatelessBaseline.

ClaudeVerifier answers the typed checks of ONE task-graph node from a few keyframes (+ optional ROI
crops). The graph supplies the expected end state, the checks and the mistake library, so the model
makes a narrow, typed call instead of free-form narration.

StatelessBaseline is the ablation: the same model, shown the same frames, but with no task graph and
no state: just the task name and the flat list of step names, asked what is happening and whether
something is wrong. It is called on a fixed schedule because without state there is no notion of an
"event".
"""
from __future__ import annotations

import json
import time

import anthropic

from ..paths import load_env
from .common import Budget, ResponseCache, b64, cost_usd, to_jpeg
from .schema import MistakeReport, Verdict, VerifyRequest

PROMPT_VERSION = "verify-v2"
BASELINE_PROMPT_VERSION = "stateless-v1"

SYSTEM = """You are the verification module of Praxis, a first-person coaching system for physical tasks.
You receive a few first-person video frames (oldest first; the last frame is "now") and possibly zoomed
crops, plus ONE step of a known procedure with its expected end state, its checks and a library of
common mistakes. Judge only what is visible.

step_status:
- "complete": the step is finished: its expected end state is visible in the recent frames, or the person has
  clearly finished it and moved on (e.g. started the next step, put the tool down).
- "in_progress": the step is not finished yet (the person is still working on it, or has not started it).
- "deviation": the person is visibly making one of the listed mistakes, or something clearly wrong for this step.
confidence: your probability (0-1) that step_status is correct. Be calibrated: use mid values when unsure.
mistake_id: the matching id from the mistake library, "other" for a clear mistake not in the library, else "none".
visibility: "insufficient" if the region needed to judge this step is out of frame, occluded, or too blurry.
view_request: if visibility is insufficient, one short instruction telling the wearer where to look or what
to show (e.g. "Look down and to the right at the wheel hub"); else "".
Keep text fields short (under 20 words)."""

BASELINE_SYSTEM = """You watch first-person video frames (oldest first; the last frame is "now") of a person
doing a physical task. You are told the task and its list of steps. Say which step the person is on now,
whether they are making a mistake right now, and how confident you are. Judge only what is visible.
Keep text fields short (under 20 words)."""


def _verdict_schema(mistake_ids: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "step_status": {"type": "string", "enum": ["in_progress", "complete", "deviation"]},
            "confidence": {"type": "number"},
            "mistake_id": {"type": "string", "enum": ["none", "other", *mistake_ids]},
            "mistake_description": {"type": "string"},
            "correction": {"type": "string"},
            "visibility": {"type": "string", "enum": ["ok", "insufficient"]},
            "view_request": {"type": "string"},
        },
        "required": ["step_status", "confidence", "mistake_id", "mistake_description", "correction",
                     "visibility", "view_request"],
        "additionalProperties": False,
    }


def _baseline_schema(step_names: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "current_step": {"type": "string", "enum": [*step_names, "none_of_these"]},
            "step_confidence": {"type": "number"},
            "mistake": {"type": "boolean"},
            "mistake_confidence": {"type": "number"},
            "mistake_description": {"type": "string"},
            "correction": {"type": "string"},
        },
        "required": ["current_step", "step_confidence", "mistake", "mistake_confidence",
                     "mistake_description", "correction"],
        "additionalProperties": False,
    }


class _ClaudeBase:
    def __init__(self, model: str, budget: Budget, effort: str = "low", thinking_off: bool = True,
                 timeout_s: float = 30.0, img_side: int = 640, use_cache: bool = True):
        load_env()
        self.model = model
        self.client = anthropic.Anthropic(timeout=timeout_s, max_retries=2)
        self.budget = budget
        self.effort = effort
        self.thinking_off = thinking_off and model.startswith("claude-haiku")
        self.img_side = img_side
        self.cache = ResponseCache(model) if use_cache else None

    def _images(self, req: VerifyRequest) -> tuple[list[dict], list[bytes]]:
        blocks, raw = [], []
        n = len(req.frames)
        for i, f in enumerate(req.frames):
            jpg = to_jpeg(f, self.img_side)
            raw.append(jpg)
            ago = req.context.get("frame_ages", [None] * n)[i]
            label = f"Frame {i + 1}/{n}" + (f" ({ago:.1f}s ago)" if ago is not None else "") + (" = now" if i == n - 1 else "")
            blocks += [{"type": "text", "text": label},
                       {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64(jpg)}}]
        for j, c in enumerate(req.crops):
            jpg = to_jpeg(c, 512)
            raw.append(jpg)
            blocks += [{"type": "text", "text": f"Zoomed crop {j + 1} (tracked region, now)"},
                       {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64(jpg)}}]
        return blocks, raw

    def _call(self, system: str, content: list[dict], schema: dict, cache_key: str) -> tuple[dict, dict]:
        """Returns (parsed_json, meta). Uses the response cache when possible."""
        if self.cache is not None:
            hit = self.cache.get(cache_key)
            if hit is not None:
                return hit["parsed"], {**hit["meta"], "cached": True}
        self.budget.check()
        kw: dict = dict(model=self.model, max_tokens=1024 if self.thinking_off else 4096,
                        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                        messages=[{"role": "user", "content": content}],
                        output_config={"format": {"type": "json_schema", "schema": schema}, "effort": self.effort})
        if self.thinking_off:
            kw["thinking"] = {"type": "disabled"}
        t0 = time.perf_counter()
        resp = self.client.messages.create(**kw)
        lat = (time.perf_counter() - t0) * 1000
        if resp.stop_reason == "refusal":
            raise RuntimeError("refusal")
        text = next(b.text for b in resp.content if b.type == "text")
        parsed = json.loads(text)
        u = resp.usage
        cr = getattr(u, "cache_read_input_tokens", 0) or 0
        cw = getattr(u, "cache_creation_input_tokens", 0) or 0
        usd = cost_usd(self.model, u.input_tokens, u.output_tokens, cr, cw)
        self.budget.add(usd)
        meta = {"latency_ms": lat, "input_tokens": u.input_tokens + cr + cw, "output_tokens": u.output_tokens,
                "cost_usd": usd, "cached": False, "request_id": getattr(resp, "_request_id", None)}
        if self.cache is not None:
            self.cache.put(cache_key, {"parsed": parsed, "meta": meta})
        return parsed, meta


class ClaudeVerifier(_ClaudeBase):
    name = "claude"

    def __init__(self, model: str, budget: Budget, role: str = "fast", **kw):
        super().__init__(model, budget, effort=kw.pop("effort", "low" if role == "fast" else "medium"), **kw)
        self.role = role

    def verify(self, req: VerifyRequest) -> Verdict:
        node, g = req.node, req.graph
        nxt = req.context.get("next_step")
        lib = {m.id: m for m in node.mistakes}
        text = [f"Task: {g.title}.",
                f"Step being checked: {node.name}. Instruction: {node.instruction_novice}",
                f"Expected end state: {node.end_state}",
                f"Where to look: {node.view_hint or 'n/a'}"]
        if req.checks:
            text.append("Checks (yes = pass):\n" + "\n".join(f"- {c.question}" for c in req.checks))
        if lib:
            text.append("Mistake library:\n" + "\n".join(
                f"- {m.id}: {m.description} Looks like: {m.visual_cue}" + (f" Early sign: {m.early_cue}" if m.early_cue else "")
                for m in lib.values()))
        if nxt:
            text.append(f"Next step after this one: {nxt}")
        if req.context.get("time_on_step") is not None:
            text.append(f"Time on this step so far: {req.context['time_on_step']:.0f}s")
        img_blocks, raw = self._images(req)
        content = img_blocks + [{"type": "text", "text": "\n".join(text)}]
        key = ResponseCache.key(PROMPT_VERSION, self.model, self.effort, text, *raw)
        try:
            out, meta = self._call(SYSTEM, content, _verdict_schema(list(lib)), key)
        except Exception as e:  # network / refusal / budget -> abstain, never crash the engine
            return Verdict(step_status="in_progress", confidence=0.5, node_id=node.id, model=self.model, role=self.role,
                           prompt_version=PROMPT_VERSION, error=f"{type(e).__name__}: {e}"[:300])
        mistake = None
        mid = out.get("mistake_id", "none")
        if mid != "none":
            m = lib.get(mid)
            mistake = MistakeReport(type=m.type if m else "other", mistake_id=m.id if m else None,
                                    description=out.get("mistake_description") or (m.description if m else ""),
                                    correction=(m.correction if m else out.get("correction", "")))
        vis = out.get("visibility", "ok")
        return Verdict(step_status=out["step_status"], confidence=float(min(1, max(0, out["confidence"]))),
                       mistake=mistake, visibility=vis, view_request=(out.get("view_request") or None) if vis != "ok" else None,
                       node_id=node.id, model=self.model, role=self.role, prompt_version=PROMPT_VERSION,
                       latency_ms=meta["latency_ms"], input_tokens=meta["input_tokens"],
                       output_tokens=meta["output_tokens"], cost_usd=0.0 if meta.get("cached") else meta["cost_usd"],
                       raw={**out, "cached": meta.get("cached", False), "orig_cost_usd": meta["cost_usd"]})


class StatelessBaseline(_ClaudeBase):
    """Same model, no graph, no state. Returns a dict (not a Verdict) since it predicts the step itself."""
    name = "stateless"

    def query(self, frames, task_title: str, step_names: list[str], frame_ages: list[float] | None = None) -> dict:
        from .schema import VerifyRequest as _VR
        req = _VR(t=0.0, frames=frames, node=None, graph=None, checks=[], context={"frame_ages": frame_ages or [None] * len(frames)})  # type: ignore[arg-type]
        img_blocks, raw = self._images(req)
        text = f"Task: {task_title}.\nSteps:\n" + "\n".join(f"- {s}" for s in step_names)
        content = img_blocks + [{"type": "text", "text": text}]
        key = ResponseCache.key(BASELINE_PROMPT_VERSION, self.model, self.effort, text, *raw)
        try:
            out, meta = self._call(BASELINE_SYSTEM, content, _baseline_schema(step_names), key)
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}"[:300]}
        return {**out, **meta, "model": self.model, "prompt_version": BASELINE_PROMPT_VERSION}

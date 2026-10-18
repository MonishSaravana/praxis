"""OpenAI vision models as a verifier tier (Responses API over plain httpx; no extra package).

The same three typed questions the engine asks Jev, with Claude's prompts and output schemas (verify/claude.py), so a
comparison changes only the model: verify ("is step X done?"), choose_step ("which of these steps?") and choose_task
("which task?"). Shared hard Budget and on-disk response cache, like the other verifiers.
Prices are per 1M tokens (input, output), from developers.openai.com/api/docs/pricing (standard tier, 2026-10-17);
images are billed as input tokens, which the response's usage reports.
"""
from __future__ import annotations

import json
import os
import time

import httpx

from ..paths import load_env
from .common import Budget, ResponseCache, b64, to_jpeg

PRICES = {
    "gpt-6-luna": (0.10, 0.50),
    "gpt-6-sol": (2.00, 10.00),
    "gpt-6.1-sol": (2.00, 10.00),
    "gpt-6-astra": (10.00, 50.00),
    "gpt-5.4-mini": (0.75, 4.50),
    "gpt-5.4-nano": (0.20, 1.25),
}

TASK_SYSTEM = """You recognize which procedure a person is doing from first-person video frames (oldest first; the last
frame is "now"). Choose the one task from the list that the person is doing, or "none" if none of them fits or nothing
task-related is happening. Give your probability for that choice. Judge only what is visible."""


class OpenAIVerifier:
    name = "openai"

    def __init__(self, model: str, budget: Budget, effort: str | None = "low", img_side: int = 640,
                 timeout_s: float = 60.0, use_cache: bool = True, role: str = "fast"):
        load_env()
        self.model, self.budget, self.effort, self.img_side, self.role = model, budget, effort, img_side, role
        self.http = httpx.Client(base_url="https://api.openai.com/v1", timeout=timeout_s,
                                 headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
        self.cache = ResponseCache(model) if use_cache else None

    def _call(self, system: str, content: list[dict], schema: dict, name: str, cache_key: str) -> tuple[dict, dict]:
        if self.cache is not None:
            hit = self.cache.get(cache_key)
            if hit is not None:
                return hit["parsed"], {**hit["meta"], "cached": True}
        self.budget.check()
        body = {"model": self.model, "instructions": system,
                "input": [{"role": "user", "content": content}],
                "text": {"format": {"type": "json_schema", "name": name, "schema": schema, "strict": True}}}
        if self.effort and self.effort != "default":
            body["reasoning"] = {"effort": self.effort}
        t0 = time.perf_counter()
        r = self.http.post("/responses", json=body)
        if r.status_code == 400 and self.effort and "reasoning" in r.text:   # model without reasoning settings
            body.pop("reasoning")
            r = self.http.post("/responses", json=body)
        lat = (time.perf_counter() - t0) * 1000
        r.raise_for_status()
        d = r.json()
        text = d.get("output_text") or next(c["text"] for o in d.get("output", []) if o.get("type") == "message"
                                             for c in o.get("content", []) if c.get("type") == "output_text")
        parsed = json.loads(text)
        u = d.get("usage", {})
        pin, pout = PRICES.get(self.model, (0.0, 0.0))
        cached_in = (u.get("input_tokens_details") or {}).get("cached_tokens", 0) or 0
        in_tok, out_tok = u.get("input_tokens", 0), u.get("output_tokens", 0)
        usd = ((in_tok - cached_in) * pin + cached_in * pin * 0.1 + out_tok * pout) / 1e6
        self.budget.add(usd)
        meta = {"latency_ms": lat, "input_tokens": in_tok, "output_tokens": out_tok, "cost_usd": usd, "cached": False,
                "reasoning_tokens": (u.get("output_tokens_details") or {}).get("reasoning_tokens")}
        if self.cache is not None:
            self.cache.put(cache_key, {"parsed": parsed, "meta": meta})
        return parsed, meta

    def choose_task(self, frames, options: dict[str, str]) -> dict:
        n = len(frames)
        content, raw = [], []
        for i, f in enumerate(frames):
            jpg = to_jpeg(f, self.img_side)
            raw.append(jpg)
            content += [{"type": "input_text", "text": f"Frame {i + 1}/{n}" + (" = now" if i == n - 1 else "")},
                        {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64(jpg)}"}]
        ids = list(options)
        text = "Tasks:\n" + "\n".join(f"- {k}: {v}" for k, v in options.items())
        content.append({"type": "input_text", "text": text})
        schema = {"type": "object", "additionalProperties": False, "required": ["task", "probability"],
                  "properties": {"task": {"type": "string", "enum": [*ids, "none"]}, "probability": {"type": "number"}}}
        key = ResponseCache.key("choose_task-v1", self.model, self.effort, text, *raw)
        out, meta = self._call(TASK_SYSTEM, content, schema, "which_task", key)
        p = float(min(1.0, max(0.0, out["probability"])))
        rest = [k for k in [*ids, "none"] if k != out["task"]]
        probs = {k: (1 - p) / max(1, len(rest)) for k in rest}
        probs[out["task"]] = p
        return {"probs": probs, "choice": out["task"], "latency_ms": meta["latency_ms"], "model": self.model,
                "cost_usd": 0.0 if meta.get("cached") else meta["cost_usd"], "cached": bool(meta.get("cached")),
                "reasoning_tokens": meta.get("reasoning_tokens")}

    # ------------------------------------------------------------------ Jev's other two questions
    def _image_blocks(self, frames, ages=None) -> tuple[list[dict], list[bytes]]:
        n = len(frames)
        ages = ages or [None] * n
        blocks, raw = [], []
        for i, f in enumerate(frames):
            jpg = to_jpeg(f, self.img_side)
            raw.append(jpg)
            label = f"Frame {i + 1}/{n}" + (f" ({ages[i]:.1f}s ago)" if ages[i] is not None else "") + (" = now" if i == n - 1 else "")
            blocks += [{"type": "input_text", "text": label},
                       {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64(jpg)}"}]
        return blocks, raw

    def verify(self, req):
        from .claude import PROMPT_VERSION, SYSTEM, _verdict_schema, verify_text
        from .schema import MistakeReport, Verdict
        node = req.node
        lib = {m.id: m for m in node.mistakes}
        text = verify_text(req)
        blocks, raw = self._image_blocks(req.frames, req.context.get("frame_ages"))
        key = ResponseCache.key(PROMPT_VERSION, self.model, self.effort, text, *raw)
        try:
            out, meta = self._call(SYSTEM, blocks + [{"type": "input_text", "text": "\n".join(text)}],
                                   _verdict_schema(list(lib)), "step_check", key)
        except Exception as e:  # noqa: BLE001  network / budget -> abstain, never crash the engine
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
                       latency_ms=meta["latency_ms"], input_tokens=meta["input_tokens"], output_tokens=meta["output_tokens"],
                       cost_usd=0.0 if meta.get("cached") else meta["cost_usd"],
                       raw={**out, "cached": meta.get("cached", False), "orig_cost_usd": meta["cost_usd"]})

    def choose_step(self, frames, options: dict[str, str], task: str, mistakes: dict | None = None) -> dict:
        from .claude import STEP_SYSTEM
        blocks, raw = self._image_blocks(frames)
        ids = list(options)
        text = f"Task: {task}.\nCandidate steps:\n" + "\n".join(f"- {k}: {v}" for k, v in options.items())
        schema = {"type": "object", "additionalProperties": False, "required": ["step", "probability"],
                  "properties": {"step": {"type": "string", "enum": [*ids, "none"]}, "probability": {"type": "number"}}}
        key = ResponseCache.key("choose_step-v1", self.model, self.effort, text, *raw)
        out, meta = self._call(STEP_SYSTEM, blocks + [{"type": "input_text", "text": text}], schema, "which_step", key)
        p = float(min(1.0, max(0.0, out["probability"])))
        rest = [k for k in [*ids, "none"] if k != out["step"]]
        probs = {k: (1 - p) / max(1, len(rest)) for k in rest}
        probs[out["step"]] = p
        return {"probs": probs, "choice": out["step"], "latency_ms": meta["latency_ms"], "model": self.model,
                "cost_usd": 0.0 if meta.get("cached") else meta["cost_usd"], "cached": bool(meta.get("cached"))}

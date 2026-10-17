"""L5 · JevVerifier (rented, swappable): TypeSafe Jev `/v1/systemone`, typed questions with calibrated
probabilities. Image input is experimental (header `TypeSafe-Danger-Zone-Images: true`, Jev 1.13/1.14),
so `probe_images()` checks it actually works before the engine relies on it.

Our checks map onto Jev question types:
  step_complete  noul    "is this step's expected end state reached in the latest frame?"
  mistake        choice  {none, <mistake ids from the node's library>}  -> correction comes from the graph
  view_ok        noul    "is the region needed to verify this step clearly visible?"
"""
from __future__ import annotations

import json
import os
import time
import uuid

import httpx
import numpy as np

from ..paths import load_env
from .common import Budget, ResponseCache, b64, cost_usd, to_jpeg
from .schema import MistakeReport, Verdict, VerifyRequest

PROMPT_VERSION = "jev-v2"
BASE = "https://api.typesafe.ai"


def jev_key() -> str | None:
    load_env()
    return os.environ.get("TYPESAFE_API_KEY") or os.environ.get("JEV_API_KEY")


class JevClient:
    def __init__(self, model: str = "jev-1.14.0", timeout_s: float = 20.0):
        key = jev_key()
        if not key:
            raise RuntimeError("TYPESAFE_API_KEY / JEV_API_KEY not set")
        self.model = model
        self.http = httpx.Client(base_url=os.environ.get("TYPESAFE_BASE_URL", BASE), timeout=timeout_s,
                                 headers={"Authorization": f"Bearer {key}"})

    def system_one(self, state, questions: dict, assets: dict | None = None, images: bool = False,
                   retries: int = 3) -> tuple[dict, float]:
        body = {"state": state, "model": self.model, "questions": questions}
        if assets:
            body["assets"] = assets
        headers = {"TypeSafe-Danger-Zone-Images": "true"} if images else {}
        for attempt in range(retries + 1):
            t0 = time.perf_counter()
            r = self.http.post("/v1/systemone", json=body, headers=headers)
            lat = (time.perf_counter() - t0) * 1000
            if r.status_code in (429, 529, 500, 502, 503) and attempt < retries:
                time.sleep(float(r.headers.get("retry-after", 0.5 * 2 ** attempt)))
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"jev {r.status_code}: {r.text[:300]}")
            return r.json(), lat
        raise RuntimeError("jev: retries exhausted")

    def models(self) -> dict:
        return self.http.get("/v1/models").json()


def _asset(rgb: np.ndarray, max_side: int = 768) -> tuple[str, dict, bytes]:
    """Jev requires each side in [280, 1568] px."""
    jpg = to_jpeg(rgb, max_side=max_side, min_side=280)
    ref = f"img-{uuid.uuid4().hex[:12]}"
    return ref, {"type": "image", "format": "jpg", "data_base64": b64(jpg)}, jpg


def _stable_refs(obj, names: dict[str, str]):
    """Copy of `obj` with each asset ref replaced by its stable name, for response-cache keys: the refs are random
    per request, so a key built from them never matches and every re-run would ask Jev again."""
    if isinstance(obj, dict):
        return {k: _stable_refs(v, names) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stable_refs(v, names) for v in obj]
    return names.get(obj, obj) if isinstance(obj, str) else obj


class JevVerifier:
    name = "jev"

    def choose_step(self, frames, options: dict[str, str], task: str, mistakes: dict[str, str] | None = None) -> dict:
        """Typed localization: which of these candidate steps is the person doing now? -> probabilities.
        With `mistakes` (the likeliest step's mistake library), the same call also screens for a visible mistake
        (Jev answers all questions of a request in parallel, so this adds no latency)."""
        self.budget.check()
        assets, refs = {}, []
        for f in frames:
            ref, a, _ = _asset(f, 768)
            assets[ref] = a
            refs.append(ref)
        crit = dict(options)
        crit["none"] = "None of these steps (between steps, or something else)"
        q = {"step": {"type": "choice", "instructions": f"The person is doing this task: {task}. Which step are they doing "
                                                         "in the most recent `frames`?", "criteria": crit}}
        if mistakes:
            mc = {"none": "No mistake is visible"}
            mc.update(mistakes)
            q["mistake"] = {"type": "choice", "instructions": "Is the person visibly making one of these mistakes in `frames`?",
                            "criteria": mc}
        key = ResponseCache.key("choose_step-v1" if not mistakes else "choose_step-screen-v1", self.model, q,
                                [assets[r]["data_base64"][:4096] + str(len(assets[r]["data_base64"])) for r in refs])
        hit = self.cache.get(key) if self.cache else None
        if hit:
            resp, lat = hit["resp"], hit["latency_ms"]
        else:
            resp, lat = self.client.system_one({"frames": refs}, q, assets, images=True)
            if self.cache:
                self.cache.put(key, {"resp": resp, "latency_ms": lat})
        a = resp["answers"]["step"]
        u = resp.get("usage", {})
        usd = cost_usd(self.model, u.get("input_tokens", 0), 0)
        self.budget.add(usd)
        out = {"probs": {k: float(p) for k, p in a["probabilities"].items()}, "choice": a["choice"],
               "latency_ms": lat, "model": resp.get("model"), "cost_usd": usd}
        if "mistake" in resp["answers"]:
            m = resp["answers"]["mistake"]
            out["mistake"] = {"choice": m["choice"], "p": float(m["probabilities"].get(m["choice"], 0.0)),
                              "p_none": float(m["probabilities"].get("none", 0.0))}
        return out

    def choose_task(self, frames, options):
        key = ResponseCache.key("choose_task-v1", self.model, options, [to_jpeg(f, 768, 280)[-4096:] for f in frames])
        hit = self.cache.get(key) if self.cache else None
        if hit:
            return {**hit, "cached": True}
        self.budget.check()
        r = choose_task(self.client, frames, options)
        self.budget.add(r["cost_usd"])
        if self.cache:
            self.cache.put(key, r)
        return r

    def __init__(self, budget: Budget, model: str = "jev-1.14.0", use_cache: bool = True, img_side: int = 768):
        self.client = JevClient(model)
        self.model = model
        self.budget = budget
        self.img_side = img_side
        self.cache = ResponseCache(model) if use_cache else None

    def verify(self, req: VerifyRequest) -> Verdict:
        node = req.node
        assets, frames_state, raws, names = {}, [], [], {}
        ages = req.context.get("frame_ages", [None] * len(req.frames))
        for f, ago in zip(req.frames, ages):
            ref, a, jpg = _asset(f, self.img_side)
            assets[ref], names[ref] = a, f"img{len(raws)}"
            raws.append(jpg)
            frames_state.append({"seconds_ago": round(float(ago), 1) if ago is not None else None, "frame": ref})
        state: dict = {
            "task": req.graph.title,
            "step": {"name": node.name, "instruction": node.instruction_novice, "expected_end_state": node.end_state,
                     "where_to_look": node.view_hint},
            "frames": frames_state,
        }
        for j, c in enumerate(req.crops):
            ref, a, jpg = _asset(c, 512)
            assets[ref], names[ref] = a, f"img{len(raws)}"
            raws.append(jpg)
            state.setdefault("zoomed_crops", []).append(ref)
        last = f"frames[{len(frames_state) - 1}].frame"
        q: dict = {
            "step_complete": {"type": "noul",
                              "instructions": "Has the person finished `step`? Finished means `step.expected_end_state` is visible in the recent `frames`, or they clearly completed it and moved on.",
                              "criteria": {"true": "The step is finished as described",
                                           "false": "Not finished yet, or not done as described"}},
            "view_ok": {"type": "noul",
                        "instructions": f"Is the region needed to judge `step` (`step.where_to_look`) clearly visible in `{last}`?"},
        }
        if node.mistakes:
            crit = {"none": "No mistake is visible"}
            for m in node.mistakes:
                crit[m.id] = f"{m.description} Looks like: {m.visual_cue}"
            q["mistake"] = {"type": "choice", "instructions": "Which of these mistakes, if any, is the person making in `frames`?",
                            "criteria": crit}
        # keyed on content: each ref -> its position, whose JPEG bytes follow (the request sent keeps the random refs)
        key = ResponseCache.key(PROMPT_VERSION, self.model, _stable_refs(state, names), q, *raws)
        cached = self.cache.get(key) if self.cache else None
        try:
            if cached:
                resp, lat = cached["resp"], cached["latency_ms"]
            else:
                self.budget.check()
                resp, lat = self.client.system_one(state, q, assets, images=True)
                if self.cache:
                    self.cache.put(key, {"resp": resp, "latency_ms": lat})
        except Exception as e:
            return Verdict(step_status="in_progress", confidence=0.5, node_id=node.id, model=self.model, role="fast",
                           prompt_version=PROMPT_VERSION, error=f"{type(e).__name__}: {e}"[:300])
        ans = resp["answers"]
        p_done = float(ans["step_complete"]["noul"])
        p_view = float(ans["view_ok"]["noul"])
        mistake, status, conf = None, ("complete" if p_done >= 0.5 else "in_progress"), max(p_done, 1 - p_done)
        if "mistake" in ans and ans["mistake"]["choice"] != "none":
            m = next(m for m in node.mistakes if m.id == ans["mistake"]["choice"])
            pm = float(ans["mistake"]["probabilities"].get(m.id, 0.0))
            mistake = MistakeReport(type=m.type, mistake_id=m.id, description=m.description, correction=m.correction)
            if pm >= 0.5:
                status, conf = "deviation", pm
        usage = resp.get("usage", {})
        usd = cost_usd(self.model, usage.get("input_tokens", 0), usage.get("output_tokens", 0))
        if not cached:
            self.budget.add(usd)
        vis = "ok" if p_view >= 0.5 else "insufficient"
        return Verdict(step_status=status, confidence=conf, mistake=mistake, visibility=vis,
                       view_request=(f"Show me {node.view_hint}" if node.view_hint else "Can you show me that more closely?") if vis != "ok" else None,
                       node_id=node.id, model=resp.get("model", self.model), role="fast", prompt_version=PROMPT_VERSION,
                       latency_ms=lat, input_tokens=usage.get("input_tokens", 0), output_tokens=usage.get("output_tokens", 0),
                       cost_usd=0.0 if cached else usd,
                       raw={"p_complete": p_done, "p_view_ok": p_view, "mistake": ans.get("mistake"), "cached": bool(cached),
                            "orig_cost_usd": usd})


def choose_task(client_or_verifier, frames: list[np.ndarray], options: dict[str, str]) -> dict:
    """Typed choice over the task library: {'probs': {task_id: p}, 'latency_ms', 'cost_usd'}."""
    v = client_or_verifier
    client = v.client if hasattr(v, "client") else v
    assets, refs = {}, []
    for f in frames:
        ref, a, _ = _asset(f, 768)
        assets[ref] = a
        refs.append(ref)
    crit = {k: desc for k, desc in options.items()}
    crit["none"] = "None of these tasks, or nothing task-related is happening"
    q = {"task": {"type": "choice", "instructions": "Which task is the person in these first-person `frames` doing?",
                  "criteria": crit}}
    resp, lat = client.system_one({"frames": refs}, q, assets, images=True)
    a = resp["answers"]["task"]
    u = resp.get("usage", {})
    return {"probs": {k: float(p) for k, p in a["probabilities"].items()}, "choice": a["choice"],
            "confidence": a.get("confidence"), "latency_ms": lat, "model": resp.get("model"),
            "cost_usd": cost_usd(client.model, u.get("input_tokens", 0), 0)}


def probe_images(model: str = "jev-1.14.0") -> dict:
    """Does Jev image input work? Two synthetic images with an unambiguous answer each."""
    import cv2
    client = JevClient(model)
    out = {"model": model, "tests": []}
    for color, rgb in (("red", (255, 0, 0)), ("blue", (0, 0, 255))):
        img = np.full((320, 480, 3), 255, np.uint8)
        cv2.circle(img, (240, 160), 90, rgb, -1)
        ref, a, _ = _asset(img)
        q = {"is_red": {"type": "noul", "instructions": "Is the large circle in `photo` red?"},
             "color": {"type": "choice", "instructions": "What color is the circle in `photo`?",
                       "criteria": {"red": None, "green": None, "blue": None}}}
        try:
            resp, lat = client.system_one({"photo": ref}, q, {ref: a}, images=True)
            out["tests"].append({"truth": color, "latency_ms": lat, "answers": resp["answers"], "model": resp.get("model"),
                                 "usage": resp.get("usage")})
        except Exception as e:
            out["tests"].append({"truth": color, "error": str(e)[:300]})
    ok = [t for t in out["tests"] if "answers" in t]
    out["works"] = bool(ok) and all(t["answers"]["color"]["choice"] == t["truth"] for t in ok) and len(ok) == 2
    return out


if __name__ == "__main__":
    print(json.dumps(probe_images(), indent=2))

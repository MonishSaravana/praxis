"""Smoke tests for the rented parts once keys are set: Jev image input probe, one Claude verifier call."""
from __future__ import annotations

import json
import os
import time

import numpy as np

from .paths import RESULTS, load_env


def jev_probe() -> dict:
    from .verify.jev import JevClient, probe_images
    out = {"when": time.strftime("%Y-%m-%dT%H:%M:%S")}
    try:
        out["models"] = JevClient("jev-1.14.0").models()
    except Exception as e:  # noqa: BLE001
        out["models_error"] = str(e)[:300]
    for m in ("jev-1.14.0", "jev-1.13.0"):
        try:
            out[m] = probe_images(m)
        except Exception as e:  # noqa: BLE001
            out[m] = {"error": str(e)[:300]}
    (RESULTS / "l5").mkdir(parents=True, exist_ok=True)
    (RESULTS / "l5" / "jev_image_probe.json").write_text(json.dumps(out, indent=2))
    return out


def claude_ping() -> dict:
    import anthropic
    c = anthropic.Anthropic()
    out = {}
    for m in ("claude-haiku-5-5", "claude-opus-5-5", "claude-fable-5-1"):
        t0 = time.perf_counter()
        try:
            kw = dict(model=m, max_tokens=64, messages=[{"role": "user", "content": "Reply with the single word: ready"}])
            if m == "claude-haiku-5-5":
                kw["thinking"] = {"type": "disabled"}
            r = c.messages.create(**kw)
            out[m] = {"ok": True, "latency_ms": (time.perf_counter() - t0) * 1000,
                      "text": next((b.text for b in r.content if b.type == "text"), "")[:40]}
        except Exception as e:  # noqa: BLE001
            out[m] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
    return out


if __name__ == "__main__":
    load_env()
    print("keys:", {k: bool(os.environ.get(k)) for k in ("ANTHROPIC_API_KEY", "TYPESAFE_API_KEY", "JEV_API_KEY")})
    print(json.dumps(claude_ping(), indent=1))
    print(json.dumps(jev_probe(), indent=1, default=str)[:3000])

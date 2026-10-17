"""Shared, load-once state for Praxis Studio: the engine stack, the L1 encoders, the task library (built-in graphs plus
graphs compiled from pasted instructions), engine configuration, and which model keys are present."""
from __future__ import annotations

import copy
import json
import os
import threading
from pathlib import Path

import numpy as np

from ..paths import ROOT, load_env

SESSIONS = ROOT / "sessions"            # gitignored: personal video
USER_LIB = SESSIONS / "library"         # graphs compiled from pasted instructions (and their text embeddings)


class LockedTexts:
    """SigLIP2 text encoder behind the live loop's GPU lock (MPS must not be used from two threads at once)."""

    def __init__(self, sig, lock: threading.Lock):
        self.sig, self.lock = sig, lock

    def texts(self, texts: list[str]) -> np.ndarray:
        with self.lock:
            return self.sig.texts(texts)


class StudioCore:
    def __init__(self, preload: bool = True):
        load_env()
        from ..eval import harness
        self.stack = harness.load_stack()
        self._enc = None
        self._enc_lock = threading.Lock()
        self.user_graphs: dict = {}
        self.user_evidence: dict = {}
        self._load_user_library()
        if preload:
            self.encoders()

    # ---------------------------------------------------------------- models
    def encoders(self):
        with self._enc_lock:
            if self._enc is None:
                from ..live import Encoders
                self._enc = Encoders()
            return self._enc

    def texts(self) -> LockedTexts:
        enc = self.encoders()
        return LockedTexts(enc.sig, enc.gpu)

    @staticmethod
    def model_status() -> dict:
        """Which API keys are present (never their values)."""
        return {"jev": bool(os.environ.get("JEV_API_KEY") or os.environ.get("TYPESAFE_API_KEY")),
                "claude": bool(os.environ.get("ANTHROPIC_API_KEY"))}

    def engine_config(self, **overrides):
        """The evaluated live configuration (tuned tracker, policy thresholds, commit rule, L2 threshold) with the
        async slow path on."""
        from ..engine import EngineConfig
        from ..eval.run_all import commit_p, tuned_policy, tuned_tracker
        cfg = EngineConfig(tracker=tuned_tracker(), policy=tuned_policy(), commit_on_switch_p=commit_p(),
                           boundary_thr=self.stack["boundary_thr"], async_slow_path=True)
        for k, v in overrides.items():
            setattr(cfg, k, v)
        return cfg

    def session_stack(self) -> dict:
        """A per-session copy: its own recognizer state, and the library including pasted graphs."""
        st = dict(self.stack)
        st["recognizer"] = copy.deepcopy(self.stack["recognizer"])
        if st["recognizer"] is not None:
            st["recognizer"].reset()
        st["library"] = {**self.stack["library"], **self.user_graphs}
        st["evidence"] = {**self.stack["evidence"], **self.user_evidence}
        return st

    # ---------------------------------------------------------------- library
    def _load_user_library(self) -> None:
        from ..evidence import ZeroShotEvidence
        from ..tasks.schema import TaskGraph
        if not USER_LIB.exists():
            return
        for p in sorted(USER_LIB.glob("*.json")):
            emb = p.with_suffix(".npz")
            if not emb.exists():
                continue
            g = TaskGraph.load(p)
            z = np.load(emb)
            self.add_user_graph(g, ZeroShotEvidence(g, {k: z[k] for k in z.files}))

    def add_user_graph(self, g, evidence) -> None:
        self.user_graphs[g.task_id] = g
        self.user_evidence[g.task_id] = evidence

    def library(self) -> list[dict]:
        out = []
        for tid, g in {**self.stack["library"], **self.user_graphs}.items():
            out.append({"task_id": tid, "title": g.title, "domain": g.domain, "n_steps": len(g.nodes),
                        "source": "pasted" if tid in self.user_graphs else "built-in",
                        "trained": tid in self.stack["evidence"] and type(self.stack["evidence"][tid]).__name__ == "ProbeEvidence"})
        return sorted(out, key=lambda x: (x["source"] != "built-in", x["title"]))

    def graph(self, task_id: str):
        return {**self.stack["library"], **self.user_graphs}.get(task_id)

    # ---------------------------------------------------------------- local test clips (dev)
    @staticmethod
    def dev_clips() -> list[dict]:
        """Eval and held-out-recipe recordings on this machine, for testing the upload path without a file dialog."""
        from ..data.cc4d import Clip, load_manifest
        try:
            man = load_manifest()
        except FileNotFoundError:
            return []
        out = []
        for split in ("eval", "heldout_type"):
            for x in man.get(split, []):
                c = Clip.from_json(x)
                if Path(c.video).exists():
                    out.append({"clip_id": c.clip_id, "task_id": c.task_id, "split": split, "start": c.start,
                                "end": c.end, "url": f"/dev/video/{c.clip_id}"})
        return out

    @staticmethod
    def dev_video(clip_id: str) -> Path | None:
        from ..data.cc4d import Clip, load_manifest
        man = load_manifest()
        for split in ("eval", "heldout_type"):
            for x in man.get(split, []):
                if x["clip_id"] == clip_id:
                    p = Path(Clip.from_json(x).video)
                    return p if p.exists() else None
        return None


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, default=str))
    os.replace(tmp, path)

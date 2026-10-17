"""Timestamped JSONL run log. The renderer and the eval harness read ONLY from these files,
so every overlay and every metric traces back to something the pipeline actually emitted."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np

SCHEMA_VERSION = "praxis.runlog/1"


def _default(o: Any) -> Any:
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if hasattr(o, "model_dump"):
        return o.model_dump()
    if hasattr(o, "__dict__"):
        return o.__dict__
    return str(o)


class RunLog:
    """One file per run. Each line: {"kind": ..., "t": media_time_s, "wall": unix_s, ...}."""

    def __init__(self, path: str | Path, meta: dict | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = uuid.uuid4().hex[:12]
        self._f = self.path.open("w")
        self.write("meta", t=0.0, schema=SCHEMA_VERSION, run_id=self.run_id, **(meta or {}))

    def write(self, kind: str, t: float, **fields: Any) -> None:
        rec = {"kind": kind, "t": round(float(t), 4), "wall": round(time.time(), 4), **fields}
        self._f.write(json.dumps(rec, default=_default) + "\n")

    def flush(self) -> None:
        self._f.flush()

    def close(self) -> None:
        self._f.close()

    def __enter__(self) -> "RunLog":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def read_log(path: str | Path) -> list[dict]:
    with Path(path).open() as f:
        return [json.loads(line) for line in f if line.strip()]


def by_kind(records: list[dict], kind: str) -> list[dict]:
    return [r for r in records if r["kind"] == kind]

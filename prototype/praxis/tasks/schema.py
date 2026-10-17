"""L3 · Typed task graph schema (ours).

A procedure (manual, recipe, tutorial text, or a dataset's step list) compiles into a TaskGraph.
Every downstream layer consumes this type: L3b matches against a library of them, L4 tracks a belief
over their nodes, L5 asks their typed checks, L6 speaks their instructions and corrections.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

SCHEMA_VERSION = "praxis.taskgraph/1"

MistakeType = Literal["wrong_part", "wrong_orientation", "wrong_order", "missing_step",
                      "incomplete", "wrong_quantity", "technique", "other"]


class Check(BaseModel):
    """A verification check phrased as a typed yes/no question about the current view."""
    id: str
    question: str = Field(description="Yes/no question; 'yes' means the check passes")
    kind: Literal["completion", "orientation", "part_identity", "presence", "alignment", "quantity", "other"] = "completion"
    roi: str | None = Field(default=None, description="What region to zoom into, e.g. 'front-right wheel hub'")


class Mistake(BaseModel):
    id: str
    type: MistakeType
    description: str = Field(description="What the mistake looks like")
    visual_cue: str = Field(description="What a camera would see when this happens")
    correction: str = Field(description="Specific fix, spoken to the user")
    early_cue: str | None = Field(default=None, description="Earlier sign, e.g. wrong part picked up")


class DurationPrior(BaseModel):
    mean_s: float
    std_s: float
    n: int = 0                       # number of observed executions it was fit on (0 = model guess)
    source: str = "compiler"         # compiler | dataset-train-split


class Node(BaseModel):
    id: str
    name: str
    instruction_novice: str
    instruction_expert: str
    substeps: list[str] = Field(default_factory=list, description="Finer breakdown used when the user is struggling")
    parts: list[str] = Field(default_factory=list, description="Parts/tools/ingredients this step handles")
    end_state: str = Field(description="What the scene looks like when the step is done (embedded for local matching)")
    view_hint: str = Field(default="", description="Where to look to verify this step")
    checks: list[Check] = Field(default_factory=list)
    mistakes: list[Mistake] = Field(default_factory=list)
    successors: list[str] = Field(default_factory=list)
    duration: DurationPrior | None = None
    dataset_labels: list[str] = Field(default_factory=list, description="GT label ids this node maps to (eval only)")


class TaskGraph(BaseModel):
    schema_version: str = SCHEMA_VERSION
    task_id: str
    title: str
    domain: str
    summary: str = ""
    source: str = Field(description="What it was compiled from")
    draft: bool = False              # True when drafted open-set without a source document
    compiler: dict = Field(default_factory=dict)   # model id, prompt version, cost
    nodes: list[Node]
    start: list[str]

    # ---- helpers -------------------------------------------------------------------------
    def node(self, nid: str) -> Node:
        return self._index()[nid]

    def _index(self) -> dict[str, Node]:
        if not hasattr(self, "_idx_cache"):
            object.__setattr__(self, "_idx_cache", {n.id: n for n in self.nodes})
        return self._idx_cache  # type: ignore[attr-defined]

    @property
    def ids(self) -> list[str]:
        return [n.id for n in self.nodes]

    def predecessors(self) -> dict[str, list[str]]:
        pred: dict[str, list[str]] = {n.id: [] for n in self.nodes}
        for n in self.nodes:
            for s in n.successors:
                if s in pred:
                    pred[s].append(n.id)
        return pred

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "TaskGraph":
        return cls.model_validate(json.loads(Path(path).read_text()))

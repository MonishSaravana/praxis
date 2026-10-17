"""L5 · Verifier interface (typed, swappable).

    verify(frames, node, checks) -> Verdict

Any implementation (Jev, Claude, the stateless baseline, our distilled student) returns exactly this
type, so the state tracker and policy never know which model answered.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

import numpy as np
from pydantic import BaseModel, Field

from ..tasks.schema import Check, Node, TaskGraph

StepStatus = Literal["in_progress", "complete", "deviation"]


class MistakeReport(BaseModel):
    type: str
    mistake_id: str | None = None          # id from the node's mistake library when it matched one
    description: str
    correction: str


class Verdict(BaseModel):
    step_status: StepStatus
    confidence: float = Field(ge=0.0, le=1.0)
    mistake: MistakeReport | None = None
    visibility: Literal["ok", "insufficient"] = "ok"
    view_request: str | None = None
    # bookkeeping (filled by the implementation, never by the model)
    node_id: str = ""
    model: str = ""
    role: str = ""                          # fast | strong | baseline | student
    prompt_version: str = ""
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    raw: dict = Field(default_factory=dict)
    error: str | None = None


@dataclass
class VerifyRequest:
    """What the engine hands a verifier at an event."""
    t: float
    frames: list[np.ndarray]                # RGB keyframes, oldest -> newest
    node: Node                              # node being checked (current MAP step)
    graph: TaskGraph
    checks: list[Check]
    crops: list[np.ndarray] = field(default_factory=list)   # optional ROI crops (TAPNext tracks)
    context: dict = field(default_factory=dict)            # e.g. next node, belief summary, time on step
    features: dict = field(default_factory=dict)           # L1 features at t (for the distilled student)


class Verifier(Protocol):
    name: str

    def verify(self, req: VerifyRequest) -> Verdict: ...

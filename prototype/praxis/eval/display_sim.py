"""Replay the on-screen-instruction rule over a LOGGED run (no engine re-run): what the instruction chip would have
shown at every moment if the instruction had been said at the start (task known) and had followed a majority belief
held for `ticks` ticks, on top of the instructions the run actually gave. Verification timing in a real re-run could
shift slightly (the policy uses the announced step for its hesitation timer); this isolates the display rule."""
from __future__ import annotations

import numpy as np

from ..runlog import by_kind, read_log
from ..state_tracker import DONE


def shown_events(recs: list[dict], graph=None, follow_p: float | None = 0.5, ticks: int = 3,
                 speak_on_start: bool = True) -> list[tuple[float, str]]:
    """[(t, node)] instruction events. follow_p None = the run as logged (instructions only on commits)."""
    events = []
    acts = [a for a in by_kind(recs, "action") if a["action"] in ("instruct", "resume_task") and a.get("node")]
    bel = by_kind(recs, "belief")
    if follow_p is None:
        return [(a["t"], a["node"]) for a in acts]
    stream = sorted([(a["t"], 0, a) for a in acts] + [(b["t"], 1, b) for b in bel], key=lambda x: (x[0], x[1]))
    announced, cand, n = None, None, 0
    if speak_on_start and graph is not None and bel:
        first = bel[0]["map"] if bel[0]["map"] in graph.ids else graph.start[0]
        events.append((0.0, first))
        announced = first
    for t, kind, r in stream:
        if kind == 0:
            events.append((t, r["node"]))
            announced, cand, n = r["node"], None, 0
            continue
        m, p = r["map"], r.get("map_p", 0.0)
        if m == DONE or m == announced or m in set(r.get("completed", [])) or p < follow_p:
            cand, n = None, 0
            continue
        n = n + 1 if m == cand else 1
        cand = m
        if n >= ticks:
            events.append((t, m))
            announced, cand, n = m, None, 0
    return events


def shown_at(events: list[tuple[float, str]], t: float) -> str | None:
    cur = None
    for te, node in events:
        if te <= t:
            cur = node
        else:
            break
    return cur

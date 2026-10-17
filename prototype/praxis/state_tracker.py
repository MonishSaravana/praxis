"""L4 · State tracker (ours) — the core of the engine.

Question it answers, every second: "Which step of the task is the person on, how long have they
been on it, and how sure am I?"

Model: an explicit-duration hidden Markov model (a hidden semi-Markov model, HSMM) over the task
graph, filtered forward online.

    hidden state  s = (k, d)     k = active node of the task graph (or DONE), d = seconds spent in k
    tick (dt = 1 s):

    PREDICT   (k, d) -> (k, d+1)  with prob 1 - h_k(d)            keep working on k
              (k, d) -> (j, 0)    with prob h_k(d) * A_C[k, j]     finish k, start j
                 h_k(d)  hazard from node k's duration prior (lognormal fit to the dataset's train split):
                         a step that has run as long as it usually takes becomes likely to end.
                 A_C     graph-constrained transitions: j must be a successor of k whose predecessors
                         are all in the completed set C (plus a small skip probability for robustness).

    UPDATE    multiply in observation likelihoods (all optional, all tempered by a weight):
              local evidence   p(x_t | k)   per-frame visual match, ~ms, every frame      (L1)
              boundary         p(b_t | d)   "something just finished" from the event detector (L2)
              verifier verdict p(v | k)     typed, calibrated, high-weight, only at events  (L5)

    READ OUT  P(k) = sum_d alpha(k, d),  normalized entropy H/log K  (-> verify / ask for a view),
              MAP step, expected time-on-step E[d | k] (-> hesitation detection in L6).

Why it works: each signal alone is weak (frames are ambiguous, boundaries are noisy, the verifier is
slow and occasionally wrong). The graph says what can come next, the duration prior says when, and
Bayes' rule weighs each piece of evidence by how reliable it is. Uncertainty is explicit, so the
policy can choose to stay quiet, verify, or ask for a better view instead of guessing.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.stats import lognorm

from .tasks.schema import TaskGraph

DONE = "__done__"


@dataclass
class TrackerConfig:
    dt: float = 1.0                 # seconds per tick (= dwell bin width)
    max_dwell_s: float = 400.0      # dwell bins beyond this share the last bin
    local_weight: float = 1.0       # temperature on per-frame visual evidence
    boundary_weight: float = 1.0
    verifier_weight: float = 4.0    # verdicts count like several frames of evidence
    skip_prob: float = 0.03         # mass for jumping to any other open node (out-of-order work, missed steps)
    default_mean_s: float = 30.0    # duration prior when a node has none
    default_cv: float = 0.8


@dataclass
class Belief:
    t: float
    p: np.ndarray                   # P(k) over nodes + DONE, sums to 1
    ids: list[str]
    entropy: float                  # normalized to [0, 1]
    map_id: str
    map_p: float
    time_on_step: float             # E[d | MAP node], seconds
    completed: list[str] = field(default_factory=list)

    def top(self, n: int = 3) -> list[tuple[str, float]]:
        idx = np.argsort(-self.p)[:n]
        return [(self.ids[i], float(self.p[i])) for i in idx]

    def as_dict(self) -> dict:
        return {"t": self.t, "p": {i: round(float(v), 4) for i, v in zip(self.ids, self.p)},
                "entropy": round(self.entropy, 4), "map": self.map_id, "map_p": round(self.map_p, 4),
                "time_on_step": round(self.time_on_step, 2), "completed": list(self.completed)}


class StateTracker:
    def __init__(self, graph: TaskGraph, cfg: TrackerConfig | None = None, join_mid_task: bool = False):
        self.g = graph
        self.cfg = cfg or TrackerConfig()
        self.ids = graph.ids + [DONE]
        self.K = len(self.ids)
        self.D = int(self.cfg.max_dwell_s / self.cfg.dt)
        self.idx = {nid: i for i, nid in enumerate(self.ids)}
        self.pred = graph.predecessors()
        self.H = self._hazards()                       # (K, D)
        self.completed: set[str] = set()
        self.join_mid_task = join_mid_task
        self.t = 0.0
        self.alpha = np.zeros((self.K, self.D))
        if join_mid_task:
            # Joined partway through: any step could be active and we don't know for how long.
            self.alpha[:-1, : min(self.D, 30)] = 1.0
        else:
            for s in graph.start:
                self.alpha[self.idx[s], 0] = 1.0
        self.alpha /= self.alpha.sum()

    # ---------------------------------------------------------------- duration priors -> hazards
    def _hazards(self) -> np.ndarray:
        d = (np.arange(self.D) + 0.5) * self.cfg.dt
        H = np.zeros((self.K, self.D))
        for i, nid in enumerate(self.ids[:-1]):
            dur = self.g.node(nid).duration
            mean = dur.mean_s if dur else self.cfg.default_mean_s
            std = dur.std_s if dur and dur.std_s > 0 else self.cfg.default_cv * mean
            sigma = np.sqrt(np.log(1 + (std / mean) ** 2))
            dist = lognorm(s=sigma, scale=mean / np.sqrt(1 + (std / mean) ** 2))
            surv_lo = dist.sf(d - 0.5 * self.cfg.dt)
            surv_hi = dist.sf(d + 0.5 * self.cfg.dt)
            H[i] = np.clip((surv_lo - surv_hi) / np.maximum(surv_lo, 1e-12), 1e-4, 0.9)
            H[i, -1] = max(H[i, -1], 0.05)            # last bin: leave eventually
        H[-1] = 0.0                                    # DONE is absorbing
        return H

    # ---------------------------------------------------------------- graph-constrained transitions
    def _open(self, extra_done: str | None = None) -> list[str]:
        """Nodes that may start now: not completed, all predecessors completed."""
        done = self.completed | ({extra_done} if extra_done else set())
        return [n for n in self.g.ids if n not in done and all(p in done for p in self.pred[n])]

    def transitions(self) -> np.ndarray:
        """A[k, j] = P(next node j | leaving k), given the completed set."""
        A = np.zeros((self.K, self.K))
        for i, nid in enumerate(self.ids[:-1]):
            open_after = [n for n in self._open(extra_done=nid) if n != nid]
            succ = [s for s in self.g.node(nid).successors if s in open_after]
            if not open_after:
                A[i, -1] = 1.0                         # nothing left: task done
                continue
            nominal = succ or open_after
            for s in nominal:
                A[i, self.idx[s]] += (1 - self.cfg.skip_prob) / len(nominal)
            for s in open_after:
                A[i, self.idx[s]] += self.cfg.skip_prob / len(open_after)
            A[i] /= A[i].sum()
        A[-1, -1] = 1.0
        return A

    # ---------------------------------------------------------------- filter
    def predict(self) -> None:
        a, H = self.alpha, self.H
        leave = (a * H).sum(1)                         # mass finishing each node this tick
        stay = a * (1 - H)
        new = np.zeros_like(a)
        new[:, 1:] = stay[:, :-1]
        new[:, -1] += stay[:, -1]                      # last dwell bin absorbs
        new[:, 0] += leave @ self.transitions()
        self.alpha = new
        self.t += self.cfg.dt

    def observe_local(self, loglik: np.ndarray, weight: float | None = None) -> None:
        """Per-node log-likelihoods (length K-1 or K) from cheap local evidence."""
        w = self.cfg.local_weight if weight is None else weight
        ll = np.full(self.K, np.nan)
        ll[: len(loglik)] = loglik
        ll[np.isnan(ll)] = np.nanmin(ll[: len(loglik)]) if len(loglik) else 0.0
        self._update(np.exp(w * (ll - ll.max()))[:, None])

    def observe_boundary(self, p_boundary: float, recent_bins: int = 2) -> None:
        """Event detector says P(a step just ended). Supports states that just switched (d < recent_bins)."""
        p = float(np.clip(p_boundary, 0.02, 0.98)) ** self.cfg.boundary_weight
        q = float(np.clip(1 - p_boundary, 0.02, 0.98)) ** self.cfg.boundary_weight
        L = np.full((1, self.D), q)
        L[0, :recent_bins] = p
        self._update(L)

    def observe_verdict(self, node_id: str, status: str, confidence: float) -> None:
        """A typed verifier verdict about node `node_id`, as a high-weight observation."""
        c = float(np.clip(confidence, 0.05, 0.95))
        k = self.idx[node_id]
        L = np.full(self.K, 1 - c)
        if status in ("in_progress", "deviation"):
            L[k] = c                                   # still on this step
        elif status == "complete":
            L[:] = c                                   # moved past it ...
            L[k] = 1 - c                               # ... so not still working on it
            for p in self.pred.get(node_id, []):       # and not on anything before it
                L[self.idx[p]] = 1 - c
        self._update((L ** self.cfg.verifier_weight)[:, None])

    def observe_step_choice(self, probs: dict[str, float], weight: float = 1.0, floor: float = 0.05) -> None:
        """Verifier answer to 'which of these steps is happening?' as a likelihood over the candidates.
        Steps not offered as options keep a neutral likelihood (the question said nothing about them)."""
        offered = [k for k in probs if k in self.idx]
        if not offered:
            return
        none_p = probs.get("none", 0.0)
        L = np.full(self.K, max(none_p, floor))
        for k in offered:
            L[self.idx[k]] = max(probs[k], floor)
        self._update((L ** weight)[:, None])

    def _update(self, L: np.ndarray) -> None:
        a = self.alpha * L
        z = a.sum()
        self.alpha = a / z if z > 0 and np.isfinite(z) else self.alpha

    # ---------------------------------------------------------------- bookkeeping
    def mark_complete(self, node_id: str) -> None:
        """Commit a step as done (policy decides when). Mass on it moves to what can come next."""
        if node_id == DONE or node_id in self.completed:
            return
        self.completed.add(node_id)
        k = self.idx[node_id]
        moved = self.alpha[k].sum()
        self.alpha[k] = 0.0
        nxt = self.transitions()[k]
        self.alpha[:, 0] += moved * nxt
        # nodes that are now impossible (completed) keep zero mass
        for c in self.completed:
            self.alpha[self.idx[c]] = 0.0
        self.alpha /= self.alpha.sum()

    def assume_done_before(self, node_id: str) -> None:
        """Joining mid-task: once localized at `node_id`, treat its graph ancestors as completed."""
        stack, seen = list(self.pred.get(node_id, [])), set()
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            self.completed.add(n)
            stack += self.pred.get(n, [])
        for c in self.completed:
            self.alpha[self.idx[c]] = 0.0
        self.alpha /= self.alpha.sum()

    # ---------------------------------------------------------------- read out
    def belief(self) -> Belief:
        p = self.alpha.sum(1)
        nz = p[p > 0]
        ent = float(-(nz * np.log(nz)).sum() / np.log(max(2, self.K - len(self.completed))))
        k = int(p.argmax())
        dwell = self.alpha[k] / max(self.alpha[k].sum(), 1e-12)
        tos = float((dwell * (np.arange(self.D) + 0.5) * self.cfg.dt).sum())
        return Belief(t=self.t, p=p, ids=self.ids, entropy=min(1.0, ent), map_id=self.ids[k],
                      map_p=float(p[k]), time_on_step=tos, completed=sorted(self.completed))

    def expected_duration(self, node_id: str) -> float:
        dur = self.g.node(node_id).duration if node_id != DONE else None
        return dur.mean_s if dur else self.cfg.default_mean_s

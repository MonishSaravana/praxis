"""L6 · Intervention policy (ours).

Turns beliefs + verdicts into what the wearer actually experiences. False alarms are what would make
people hate this, so every spoken intervention passes a calibrated-confidence threshold tuned for
precision on the train split, plus a cooldown.

Actions:
  announce_task   "Looks like you're assembling a toy car. Want me to walk you through it?"
  instruct        next step, said as soon as the current one is verified (proactive coaching)
  verified        a subtle check pulse
  mistake         prominent card: what's wrong + the specific fix
  view_request    prominent card with a direction: ask to see what's missing instead of guessing
  hint            expanded detail (sub-steps, which part, where) when time on step >> typical
  (silence)       the default
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..state_tracker import DONE, Belief
from ..tasks.schema import Node, TaskGraph
from ..verify.schema import Verdict
from .user_model import UserModel


@dataclass
class PolicyConfig:
    verify_conf: float = 0.6        # calibrated P(complete) needed to say "verified" and advance
    mistake_conf: float = 0.7       # calibrated P(deviation) needed to interrupt with a mistake card
    view_conf: float = 0.5          # P(view insufficient) needed to ask for a better view
    hesitation_ratio: float = 1.6
    cooldown_s: float = 4.0         # min gap between prominent cards
    view_cooldown_s: float = 30.0
    view_entropy: float = 0.5       # view requests only when the step belief is genuinely uncertain
    entropy_verify: float = 0.85    # belief entropy above which we spend a verifier call
    verify_min_gap_s: float = 3.0
    escalate_band: tuple[float, float] = (0.3, 0.7)
    # per verifier tier (Verdict.role): (verify_conf, mistake_conf), tuned on train-split checks; overrides above
    by_role: dict = field(default_factory=dict)


@dataclass
class Action:
    t: float
    kind: str                       # announce_task | instruct | verified | mistake | view_request | hint | done
    text: str
    node_id: str | None = None
    detail: dict = field(default_factory=dict)


class Policy:
    def __init__(self, graph: TaskGraph, cfg: PolicyConfig | None = None, user: UserModel | None = None):
        self.g = graph
        self.cfg = cfg or PolicyConfig()
        self.user = user or UserModel()
        self.last_card_t = -1e9
        self.last_view_t = -1e9
        self.last_verify_t = -1e9
        self.flagged: set[tuple[str, str]] = set()   # (node, mistake id) already said
        self.hinted: set[str] = set()
        self.step_started_t: dict[str, float] = {}
        self.announced_step: str | None = None

    # ------------------------------------------------------------ phrasing
    def phrase(self, node: Node) -> str:
        p = self.user.profile
        return node.instruction_expert if p == "expert" else node.instruction_novice

    def start(self, t: float, step: str) -> list[Action]:
        node = self.g.node(step)
        self.announced_step = step
        self.step_started_t[step] = t
        return [Action(t, "instruct", self.phrase(node), step, {"profile": self.user.profile})]

    # ------------------------------------------------------------ when to spend a verifier call
    def should_verify(self, t: float, belief: Belief, boundary_peak: bool, grasp_peak: bool) -> str | None:
        if t - self.last_verify_t < self.cfg.verify_min_gap_s or belief.map_id == DONE:
            return None
        reason = None
        if boundary_peak:
            reason = "boundary"
        elif grasp_peak:
            reason = "grasp"
        elif belief.entropy > self.cfg.entropy_verify:
            reason = "uncertain"
        elif self._ratio(belief) > self.user.hesitation_threshold(self.cfg.hesitation_ratio) and belief.map_id not in self.hinted:
            reason = "hesitation"
        if reason:
            self.last_verify_t = t
        return reason

    def _ratio(self, belief: Belief) -> float:
        if belief.map_id == DONE:
            return 0.0
        node = self.g.node(belief.map_id)
        prior = node.duration.mean_s if node.duration else 30.0
        started = self.step_started_t.get(belief.map_id)
        tos = (belief.t - started) if started is not None else belief.time_on_step
        return tos / max(prior, 1e-3)

    def needs_escalation(self, v: Verdict, p_complete: float) -> bool:
        """Escalate to the strong verifier when the fast one is unsure (calibrated P(complete) in the band), reports a
        possible mistake (high-stakes: needs confirmation and a specific correction), or can't see."""
        lo, hi = self.cfg.escalate_band
        return v.step_status == "deviation" or v.mistake is not None or v.visibility == "insufficient" or lo <= p_complete <= hi

    # ------------------------------------------------------------ react to a calibrated verdict
    def on_verdict(self, t: float, v: Verdict, p_complete: float, p_deviation: float, belief: Belief) -> tuple[list[Action], bool]:
        """Returns (actions, commit_complete)."""
        acts: list[Action] = []
        node = self.g.node(v.node_id)
        card_ok = t - self.last_card_t >= self.cfg.cooldown_s
        verify_conf, mistake_conf = self.cfg.by_role.get(v.role, (self.cfg.verify_conf, self.cfg.mistake_conf))
        # 1) mistakes first: they are the highest-value intervention
        if v.step_status == "deviation" and v.mistake and p_deviation >= mistake_conf and card_ok:
            key = (node.id, v.mistake.mistake_id or v.mistake.description[:40])
            if key not in self.flagged:
                self.flagged.add(key)
                self.user.on_mistake()
                self.last_card_t = t
                acts.append(Action(t, "mistake", v.mistake.correction or v.mistake.description, node.id,
                                   {"what": v.mistake.description, "type": v.mistake.type,
                                    "mistake_id": v.mistake.mistake_id, "p": round(p_deviation, 3)}))
                return acts, False
        # 2) can't see: ask instead of guessing
        # ask only when not seeing actually blocks us: the tracker itself is unsure which step this is
        if v.visibility == "insufficient" and belief.entropy >= self.cfg.view_entropy and \
                t - self.last_view_t >= self.cfg.view_cooldown_s and card_ok:
            self.last_view_t = self.last_card_t = t
            acts.append(Action(t, "view_request", v.view_request or f"Can you show me {node.view_hint}?", node.id,
                               {"direction": direction_of(v.view_request or node.view_hint)}))
            return acts, False
        # 3) verified -> pulse + proactively announce what's next
        if v.step_status == "complete" and p_complete >= verify_conf:
            started = self.step_started_t.get(node.id, belief.t - belief.time_on_step)
            self.user.on_step_done(t - started, node.duration.mean_s if node.duration else 30.0)
            acts.append(Action(t, "verified", node.name, node.id, {"p": round(p_complete, 3)}))
            return acts, True
        return acts, False

    def after_commit(self, t: float, next_step: str | None) -> list[Action]:
        if next_step is None or next_step == DONE:
            return [Action(t, "done", "All steps complete. Nice work.")]
        return self.start(t, next_step)

    def hesitation(self, t: float, belief: Belief) -> list[Action]:
        """Expanded detail when someone is taking abnormally long on a step."""
        if belief.map_id == DONE or belief.map_id in self.hinted:
            return []
        r = self._ratio(belief)
        if r < self.user.hesitation_threshold(self.cfg.hesitation_ratio) or t - self.last_card_t < self.cfg.cooldown_s:
            return []
        node = self.g.node(belief.map_id)
        self.hinted.add(node.id)
        self.user.hints += 1
        parts = f" You'll need: {', '.join(node.parts[:3])}." if node.parts else ""
        subs = node.substeps or [node.instruction_novice]
        return [Action(t, "hint", subs[0], node.id, {"substeps": subs, "parts_line": parts.strip(),
                                                      "ratio": round(r, 2), "where": node.view_hint})]


def direction_of(text: str) -> str:
    t = (text or "").lower()
    for k, d in (("down and to the right", "down-right"), ("down and to the left", "down-left"),
                 ("up and to the right", "up-right"), ("up and to the left", "up-left"), ("down", "down"),
                 ("left", "left"), ("right", "right"), ("up", "up"), ("closer", "closer"), ("underside", "down"),
                 ("rotate", "rotate"), ("turn", "rotate")):
        if k in t:
            return d
    return "closer"

"""The Praxis engine: wires L0-L7 together at two speeds.

  fast path, every frame (ms):   L1 features -> L2 event scores -> L3b task evidence -> L4 local evidence
  slow path, only at events (s): L5 verifier (+ calibration, + escalation) -> L4 high-weight update -> L6 policy

Everything the engine decides is written to the JSONL run log (RunLog). The renderer and the eval harness
read only that log.

Two drivers use the same Engine.tick():
  replay(clip)   offline over precomputed L1 features + decoded frames (eval, renders)
  live(source)   real time from a FrameSource (webcam / file), computing L1 on the fly (praxis live)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import Callable

import numpy as np

from .events.detector import peaks
from .policy.policy import Action, Policy, PolicyConfig
from .policy.user_model import UserModel
from .runlog import RunLog
from .state_tracker import DONE, StateTracker, TrackerConfig
from .tasks.recognizer import TaskRecognizer
from .tasks.schema import TaskGraph
from .verify.calibration import Calibrator, raw_p_complete
from .verify.common import span_keyframes
from .verify.schema import Verdict, VerifyRequest


@dataclass
class EngineConfig:
    tracker_mode: str = "fused"         # fused | local | verifier   (L4 ablation)
    use_verifier: bool = True
    verify_every_s: float | None = None  # fixed-schedule calls (verifier-only ablation)
    boundary_thr: float = 0.5
    grasp_thr: float = 0.6
    min_gap_s: float = 2.0
    frames_per_call: int = 3
    frame_spacing_s: float = 1.0
    roi_crops: bool = False
    join_mid_task: bool = False
    start_prior_mass: float = 0.7       # belief mass on graph start nodes at recognition (rest uniform)
    recognize: bool = True              # False = task given (oracle), skip L3b
    commit_on_switch_p: float = 0.7     # implicit commit when belief confidently moves past a step
    escalate: bool = True
    order_check: bool = True            # stateful early warning for skipped prerequisites
    step_choice: bool = True            # uncertain belief -> typed "which step?" question to the fast verifier
    step_choice_k: int = 4
    step_choice_weight: float = 1.0
    mistake_screen: bool = True         # localization calls also screen the likeliest step's mistake library
    mistake_screen_p: float = 0.5
    screen_updates_tracker: bool = False   # screen-triggered verdicts drive mistake alerts only (train-split choice)
    order_min_p: float = 0.8
    order_unseen_mass: float = 0.3
    order_conf: float = 0.6
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    policy: PolicyConfig = field(default_factory=PolicyConfig)


class Engine:
    def __init__(self, cfg: EngineConfig, library: dict[str, TaskGraph], evidence: dict, recognizer: TaskRecognizer | None,
                 detector, verifier=None, escalation=None, calibrator: Calibrator | None = None,
                 dev_calibrator: Calibrator | None = None, log: RunLog | None = None, task_id: str | None = None,
                 user: UserModel | None = None, point_tracker=None, calibrators: dict | None = None, localizer=None):
        self.cfg, self.lib, self.evidence = cfg, library, evidence
        self.loc = localizer          # which verifier answers "which step?" (defaults to the fast verifier)
        self.rec, self.det = recognizer, detector
        self.ver, self.esc = verifier, escalation
        # calibrators per verifier tier: {"primary": (cal, devcal), "escalation": (cal, devcal)}
        self.cals = dict(calibrators or {})
        if calibrator is not None or dev_calibrator is not None:
            self.cals.setdefault("primary", (calibrator, dev_calibrator))
        self.log = log
        self.user = user or UserModel()
        self.pt = point_tracker
        self.task_id: str | None = None
        self.graph: TaskGraph | None = None
        self.tracker: StateTracker | None = None
        self.policy: Policy | None = None
        self.n_frames = 0
        self.n_escalated_frames = 0
        self.calls: list[dict] = []
        self._last_switch_map: str | None = None
        self._bscores: list[tuple[float, float]] = []
        self._gscores: list[tuple[float, float]] = []
        self._last_peak_t = -1e9
        self._last_grasp_t = -1e9
        self._last_sched = -1e9
        self._next_task_check = 4.0
        self._feat_now: dict = {}
        self._max_mass: dict[str, float] = {}
        self._order_flagged: set[str] = set()
        self._last_task_probs: dict[str, float] = {}
        self._last_choice: str | None = None
        self._choice_streak = 0
        if task_id is not None:
            self._start_task(0.0, task_id, oracle=True)

    # ------------------------------------------------------------------ helpers
    def _w(self, kind: str, t: float, **kw) -> None:
        if self.log:
            self.log.write(kind, t, **kw)

    def _start_task(self, t: float, task_id: str, oracle: bool = False, posterior: dict | None = None) -> list[Action]:
        self.task_id, self.graph = task_id, self.lib[task_id]
        self.tracker = StateTracker(self.graph, self.cfg.tracker, join_mid_task=self.cfg.join_mid_task)
        if not self.cfg.join_mid_task and self.cfg.start_prior_mass < 1.0:
            a = self.tracker.alpha
            a *= self.cfg.start_prior_mass
            a[:-1, :10] += (1 - self.cfg.start_prior_mass) / ((self.tracker.K - 1) * 10)
            self.tracker.alpha = a / a.sum()
        self.policy = Policy(self.graph, self.cfg.policy, self.user)
        ev = self.evidence.get(task_id)
        if ev is not None and list(ev.ids) != list(self.graph.ids):
            raise ValueError(f"evidence node order != graph node order for {task_id}")
        self._w("task", t, task_id=task_id, title=self.graph.title, oracle=oracle, posterior=posterior,
                n_steps=len(self.graph.nodes))
        acts = [Action(t, "announce_task", f"Looks like you're {activity_phrase(self.graph)}. Want me to walk you through it?",
                       None, {"oracle": oracle, "title": self.graph.title})]
        return acts

    def _emit(self, acts: list[Action]) -> None:
        for a in acts:
            self._w("action", a.t, action=a.kind, text=a.text, node=a.node_id, detail=a.detail,
                    step_index=self._step_index(), n_steps=len(self.graph.nodes) if self.graph else None)

    def _step_index(self) -> int | None:
        if not self.tracker:
            return None
        return len(self.tracker.completed)

    # ------------------------------------------------------------------ the tick (1 Hz)
    def tick(self, t: float, rows: dict[str, np.ndarray], frame_at: Callable[[float], np.ndarray | None]) -> None:
        """rows: L1 features for frames in (t-1, t]: keys frame(siglip), window, boundary, grasp, t."""
        n = len(rows["t"])
        if n == 0:
            return
        self.n_frames += n
        fe, we = rows["frame"], rows["window"]
        self._feat_now = {"siglip": fe.mean(0), "window": we[-1]}     # local features at t (for the distilled student)
        for tt, b in zip(rows["t"], rows["boundary"]):
            self._bscores.append((float(tt), float(b)))
        for tt, g in zip(rows["t"], rows["grasp"]):
            self._gscores.append((float(tt), float(g)))
        self._w("fast", t, boundary=float(rows["boundary"].max()), grasp=float(rows["grasp"].max()),
                hands=int((rows["hands"][:, 0] > 0).any() or (rows["hands"][:, 6] > 0).any()) if "hands" in rows else None)

        # L3b: which task?
        if self.graph is None:
            if self.rec is None:
                return
            r = None
            for i in range(n):
                r = self.rec.update(float(rows["t"][i]), fe[i], we[i], dt=1.0 / n)
            # slow path for L3b: a typed "which task is this?" verifier check at 4 s, then every 8 s until recognized
            if self.ver is not None and hasattr(self.ver, "choose_task") and t >= self._next_task_check:
                self._next_task_check = t + 6.0
                frames, _ = span_keyframes(frame_at, t)
                if frames:
                    opts = {tid: f"{g.title}: {g.summary[:160]}" for tid, g in self.lib.items()}
                    try:
                        ans = self.ver.choose_task(frames, opts)
                        self.rec.observe_verifier(ans["probs"])
                        self._last_task_probs = ans["probs"]
                        self._w("task_check", t, choice=ans["choice"], probs=ans["probs"], latency_ms=ans["latency_ms"],
                                model=ans["model"], cost_usd=ans["cost_usd"])
                        post = self.rec.posterior()
                        top = max(post, key=post.get)
                        ch = ans["choice"]
                        self._choice_streak = self._choice_streak + 1 if ch == self._last_choice else 1
                        self._last_choice = ch
                        if ch in self.lib and ch not in self.rec.task_ids:
                            # library task the local recognizer was never trained on (e.g. a newly compiled graph):
                            # recognized from two consecutive confident verifier answers
                            if ans["probs"].get(ch, 0.0) >= 0.8 and self._choice_streak >= 2:
                                r = replace(r, task_id=ch, posterior={**post, ch: ans["probs"][ch]}, recognized=True)
                                self._last_task_probs = ans["probs"]
                            else:
                                r = replace(r, posterior=post, recognized=False)
                        elif post[top] >= self.rec.threshold:
                            r = replace(r, task_id=top, posterior=post, recognized=True)
                        else:
                            r = replace(r, posterior=post, recognized=False)
                    except Exception as e:  # noqa: BLE001
                        self._w("task_check", t, error=str(e)[:200])
            if r.recognized and self.ver is not None and hasattr(self.ver, "choose_task") and \
                    self._last_task_probs.get(r.task_id, 0.0) < 0.5:
                r = replace(r, recognized=False)       # announce only what the latest verifier check also supports
            self._w("recognizer", t, top=r.task_id, posterior=r.posterior, recognized=r.recognized, open_set=r.open_set)
            if r.recognized:
                acts = self._start_task(t, r.task_id, posterior=r.posterior)
                start = self.tracker.belief().map_id
                acts += self.policy.start(t, start)
                self._emit(acts)
            return

        tr, pol = self.tracker, self.policy
        tr.predict()
        # L4 fast evidence
        if self.cfg.tracker_mode in ("fused", "local"):
            ev = self.evidence.get(self.task_id)
            if ev is not None:
                tr.observe_local(ev.loglik(fe, we))
            tr.observe_boundary(float(rows["boundary"].max()))
        belief = tr.belief()

        for nid, pk in zip(belief.ids, belief.p):
            if pk > self._max_mass.get(nid, 0.0):
                self._max_mass[nid] = float(pk)

        # implicit commit: belief confidently moved on from a step -> that step is done
        prev = self._last_switch_map
        if prev and belief.map_id != prev and prev != DONE and belief.map_p >= self.cfg.commit_on_switch_p \
                and prev not in tr.completed and self.cfg.tracker_mode != "verifier":
            tr.mark_complete(prev)
            belief = tr.belief()
            self._w("commit", t, node=prev, reason="belief_switch")
            if belief.map_id != DONE:
                self._check_order(t, belief, frame_at)
                self._emit(pol.start(t, belief.map_id))
        self._last_switch_map = belief.map_id

        # L2 peaks (causal: a peak is confirmed one frame after it)
        bpeak = self._causal_peak(self._bscores, self.cfg.boundary_thr, "_last_peak_t")
        gpeak = self._causal_peak(self._gscores, self.cfg.grasp_thr, "_last_grasp_t")
        if bpeak:
            self._w("event", t, event="boundary", score=bpeak)
        if gpeak:
            self._w("event", t, event="onset", score=gpeak)

        # L5 at events
        reason = None
        if self.cfg.use_verifier and self.ver is not None and belief.map_id != DONE:
            if self.cfg.verify_every_s:
                if t - self._last_sched >= self.cfg.verify_every_s:
                    reason, self._last_sched = "schedule", t
            else:
                reason = pol.should_verify(t, belief, bool(bpeak), bool(gpeak))
        if reason == "uncertain" and self.cfg.step_choice and hasattr(self.loc or self.ver, "choose_step"):
            self._localize(t, belief, frame_at)        # cheap typed "which step?" question first
            belief = tr.belief()
        elif reason:
            self._verify(t, belief, reason, frame_at)
            belief = tr.belief()

        # L6 hesitation -> expanded detail
        self._emit(pol.hesitation(t, belief))
        bd = belief.as_dict()
        bd.pop("t", None)
        self._w("belief", t, **bd, user=self.user.state())

    def _causal_peak(self, scores, thr, attr) -> float | None:
        if len(scores) < 3:
            return None
        (t1, s1), (t2, s2), (t3, s3) = scores[-3:]
        if s2 >= thr and s2 >= s1 and s2 > s3 and t2 - getattr(self, attr) >= self.cfg.min_gap_s:
            setattr(self, attr, t2)
            return s2
        return None

    # ------------------------------------------------------------------ slow path
    def _verify(self, t: float, belief, reason: str, frame_at, update_tracker: bool = True) -> None:
        tr, pol, g = self.tracker, self.policy, self.graph
        node = g.node(belief.map_id)
        # evidence: sharpest frame from ~8-6 s ago (context) + 2 sharpest of the last 3 s ("now");
        # head-mounted video is often motion-blurred, so frames are picked by sharpness
        frames, times = span_keyframes(frame_at, t)
        if not frames:
            return
        crops = []
        if self.cfg.roi_crops and self.pt is not None:
            c = self.pt(t)
            if c is not None:
                crops.append(c)
        nxt_ids = [n for n in node.successors if n not in tr.completed]
        req = VerifyRequest(t=t, frames=frames, node=node, graph=g, checks=node.checks, crops=crops,
                            context={"frame_ages": [t - x for x in times], "time_on_step": belief.time_on_step,
                                     "next_step": g.node(nxt_ids[0]).name if nxt_ids else None},
                            features=dict(self._feat_now))
        v = self.ver.verify(req)
        pc, pdv = self._calibrated(v, "primary")
        roles = [self._log_verdict(t, v, reason, pc)]
        # two-tier verification: the fast verifier handles clear cases; ambiguity, possible mistakes and
        # "can't see" go to the strong model before the wearer hears anything
        if self.cfg.escalate and self.esc is not None and v.error is None and pol.needs_escalation(v, pc):
            v2 = self.esc.verify(req)
            pc2, pdv2 = self._calibrated(v2, "escalation")
            roles.append(self._log_verdict(t, v2, "escalation", pc2))
            if v2.error is None:
                v, pc, pdv = v2, pc2, pdv2
        self.n_escalated_frames += len(frames)
        if v.error:
            return
        if update_tracker:
            tr.observe_verdict(node.id, "complete" if pc >= 0.5 else ("deviation" if v.step_status == "deviation" else "in_progress"),
                               pc if pc >= 0.5 else 1 - pc)
        t_out = t + sum(r["latency_ms"] for r in roles) / 1000.0    # when the user would actually hear it
        acts, commit = pol.on_verdict(t_out, v, pc, pdv, tr.belief())
        if not update_tracker:          # mistake screen: only mistake alerts may come out of it
            acts = [a for a in acts if a.kind == "mistake"]
            commit = False
        self._emit(acts)
        if commit:
            tr.mark_complete(node.id)
            self._w("commit", t_out, node=node.id, reason="verified", p=pc)
            b = tr.belief()
            self._last_switch_map = b.map_id
            self._emit(pol.after_commit(t_out, b.map_id))

    def _localize(self, t: float, belief, frame_at) -> None:
        """Belief is spread over several steps: ask the fast verifier which of the top candidates is happening."""
        frames, times = span_keyframes(frame_at, t)
        if not frames:
            return
        cands = [k for k, p in belief.top(self.cfg.step_choice_k) if k != DONE and p > 0.02]
        if len(cands) < 2:
            return
        opts = {k: f"{self.graph.node(k).name}: {self.graph.node(k).end_state}" for k in cands}
        top = self.graph.node(cands[0])
        screen = {m.id: f"{m.description} Looks like: {m.visual_cue}" for m in top.mistakes} if self.cfg.mistake_screen else None
        try:
            loc = self.loc or self.ver
            import inspect
            can_screen = "mistakes" in inspect.signature(loc.choose_step).parameters
            ans = loc.choose_step(frames, opts, self.graph.title, mistakes=screen) if screen and can_screen \
                else loc.choose_step(frames, opts, self.graph.title)
        except Exception as e:  # noqa: BLE001
            self._w("step_choice", t, error=str(e)[:200])
            return
        self.tracker.observe_step_choice(ans["probs"], weight=self.cfg.step_choice_weight)
        self.n_escalated_frames += len(frames)
        self._w("step_choice", t, options=cands, probs=ans["probs"], choice=ans["choice"], latency_ms=ans["latency_ms"],
                model=ans["model"], cost_usd=ans["cost_usd"], mistake_screen=ans.get("mistake"))
        # a positive mistake screen goes through the full verify path (fast verifier + strong-tier escalation +
        # calibrated, precision-tuned policy) before the wearer hears anything
        ms = ans.get("mistake")
        if ms and ms["choice"] != "none" and ms["p"] >= self.cfg.mistake_screen_p:
            b = self.tracker.belief()
            if b.map_id == cands[0]:
                self._verify(t, b, "mistake_screen", frame_at, update_tracker=self.cfg.screen_updates_tracker)

    def _check_order(self, t: float, belief, frame_at) -> None:
        """Stateful early warning: the person has started step j but a prerequisite of j was never seen.
        Confirmed by the verifier (is j really underway?) before the wearer hears anything."""
        if not self.cfg.order_check or self.cfg.join_mid_task or self.ver is None or belief.map_p < self.cfg.order_min_p:
            return
        if t - self.policy.last_card_t < self.policy.cfg.cooldown_s:
            return
        j = belief.map_id
        if j in self._order_flagged:
            return
        missing = [p for p in self.tracker.pred.get(j, []) if p not in self.tracker.completed
                   and self._max_mass.get(p, 0.0) < self.cfg.order_unseen_mass]
        if not missing:
            return
        frames, times = span_keyframes(frame_at, t)
        if not frames:
            return
        node = self.graph.node(j)
        req = VerifyRequest(t=t, frames=frames, node=node, graph=self.graph, checks=node.checks,
                            context={"frame_ages": [t - x for x in times]}, features=dict(self._feat_now))
        v = (self.esc or self.ver).verify(req)
        pc, _ = self._calibrated(v, "escalation" if self.esc else "primary")
        self._log_verdict(t, v, "order_check", pc)
        # 'in_progress' or 'deviation' on j with low P(complete) => j is underway now
        if v.error is None and v.visibility == "ok" and pc <= 0.5 and v.confidence >= self.cfg.order_conf:
            self._order_flagged.add(j)
            self.policy.last_card_t = t
            first = self.graph.node(missing[0])
            t_out = t + v.latency_ms / 1000.0
            self.user.on_mistake()
            self._emit([Action(t_out, "mistake", f"Hold on: it looks like you skipped '{first.name}'. "
                                                f"{first.instruction_expert} first.", j,
                               {"what": f"'{node.name}' started before '{first.name}'", "type": "wrong_order",
                                "mistake_id": "order", "missing": missing, "p": round(v.confidence, 3)})])

    def _calibrated(self, v: Verdict, which: str) -> tuple[float, float]:
        cal, dcal = self.cals.get(which, (None, None))
        cal = cal or Calibrator(method="none")
        dcal = dcal or Calibrator(method="none")
        pc = float(cal(raw_p_complete(v.step_status, v.confidence))[0])
        pdv = float(dcal(v.confidence if v.step_status == "deviation" else 0.0)[0])
        return pc, pdv

    def _log_verdict(self, t: float, v: Verdict, reason: str, pc: float | None = None) -> dict:
        rec = {"node": v.node_id, "reason": reason, "status": v.step_status, "confidence": v.confidence,
               "mistake": v.mistake.model_dump() if v.mistake else None, "visibility": v.visibility,
               "view_request": v.view_request, "model": v.model, "role": v.role, "prompt_version": v.prompt_version,
               "latency_ms": v.latency_ms, "input_tokens": v.input_tokens, "output_tokens": v.output_tokens,
               "cost_usd": v.cost_usd, "orig_cost_usd": v.raw.get("orig_cost_usd", v.cost_usd),
               "cached": v.raw.get("cached", False), "error": v.error,
               "p_complete_cal": pc}
        self.calls.append({"t": t, **rec})
        self._w("verdict", t, **rec)
        return rec


def activity_phrase(g: TaskGraph) -> str:
    """'making tomato mozzarella salad', 'assembling a construction-toy car'."""
    import re
    title = re.sub(r"\s*\(.*?\)", "", g.title)
    title = re.sub(r"(?i)\bindustreal\b\s*", "", title).strip()
    if g.domain == "assembly":
        title = re.sub(r"(?i)\s+assembly$", "", title)
        return f"assembling a {title.lower()}"
    verb = {"cooking": "making", "maintenance": "servicing"}.get(g.domain, "working on")
    return f"{verb} {title.lower()}"


# ---------------------------------------------------------------------- replay driver
def replay(engine: Engine, feats, scores: dict[str, np.ndarray], frames: list[np.ndarray], t_end: float | None = None) -> dict:
    """Run the engine over a clip's precomputed L1 features at 1 Hz ticks."""
    t = feats.t
    fps_t0 = time.perf_counter()
    frame_t = np.asarray(t)

    def frame_at(x: float):
        if len(frame_t) == 0 or x < frame_t[0] - 0.5:
            return None
        i = int(np.argmin(np.abs(frame_t - x)))
        return frames[i] if i < len(frames) else None

    end = t_end if t_end is not None else float(t[-1]) if len(t) else 0.0
    tick = 1.0
    while tick <= end + 1e-6:
        m = (t > tick - 1.0) & (t <= tick)
        rows = {"t": t[m], "frame": feats.frame[m], "window": feats.window[m], "hands": feats.hands[m],
                "boundary": scores["boundary"][m], "grasp": scores["grasp"][m]}
        engine.tick(tick, rows, frame_at)
        tick += 1.0
    wall = time.perf_counter() - fps_t0
    return {"wall_s": wall, "n_frames": engine.n_frames, "escalated_frames": engine.n_escalated_frames}


def peaks_of(t, s, thr, gap):
    return peaks(np.asarray(t), np.asarray(s), thr, gap)

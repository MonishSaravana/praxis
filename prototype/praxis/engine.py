"""The Praxis engine: wires L0-L7 together at two speeds.

  fast path, every frame (ms):   L1 features -> L2 event scores -> L3b task evidence -> L4 local evidence
  slow path, only at events (s): L5 verifier (+ calibration, + escalation) -> L4 high-weight update -> L6 policy

Everything the engine decides is written to the JSONL run log (RunLog). The renderer and the eval harness
read only that log.

Multi-task (EngineConfig.multi_task, docs/MULTITASK.md): the first recognized task is a belief, not a lock. The engine
keeps a task set (active / paused / done / done enough / retracted), each task with its own tracker and policy.
Landmarks drive the tracker's away states; sustained P(away) (a poor fit) re-runs the typed "which task?" check, which
can switch to another task (pausing the old one with its state), resume a paused one, or keep the current one. A task
left with steps to go gets one spoken reminder and a question ("Coming back to the burritos?"). A paused task is closed
as done enough only when the person says so ("I'm done", answer_resume) or the session ends (finish); never on a timer.

Two drivers use the same Engine.tick():
  replay(clip)   offline over precomputed L1 features + decoded frames (eval, renders)
  live(source)   real time from a FrameSource (webcam / file), computing L1 on the fly (praxis live)

The slow path runs inline or async. replay() runs model calls inline: a tick waits for its answers, so every
evaluation is synchronous and deterministic. Live mode sets EngineConfig.async_slow_path: model calls go to worker
threads and the fast path keeps ticking. An answer is folded in when it arrives (Engine.poll): the tracker applies it
at the tick its frames were taken and re-runs the filter forward over the fast-path inputs since then (_late), and
the policy acts on it at the time it arrived. Both modes run the same decision code; only the timing differs.
"""
from __future__ import annotations

import collections
import time
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field, replace
from functools import partial
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
    # open-set drafting (M5): if the typed task check keeps answering "none of these" after open_set_min_s, draft a
    # light graph from the last open_set_window_s of frames (tasks/drafter.py) and start tracking it as a draft
    open_set_draft: bool = False
    open_set_min_s: float = 20.0
    open_set_none_streak: int = 2
    open_set_window_s: float = 90.0
    open_set_max_wait_s: float = 60.0      # ...or nothing recognized by then
    join_mid_task: bool = False
    start_prior_mass: float = 0.7       # belief mass on graph start nodes at recognition (rest uniform)
    recognize: bool = True              # False = task given (oracle), skip L3b
    commit_on_switch_p: float = 0.7     # implicit commit when belief confidently moves past a step
    escalate: bool = True
    order_check: bool = True            # stateful early warning for skipped prerequisites
    step_choice: bool = True            # uncertain belief -> typed "which step?" question to the fast verifier
    step_choice_k: int = 4
    step_choice_local: int = 0          # also offer the per-frame (local evidence) model's top steps right now ...
    step_choice_next: bool = False      # ... and the next open steps (the tracker's top list missed the true step 30%
                                        # of the time on train: results/l5/fast_tier_bakeoff.json)
    step_choice_weight: float = 1.0
    mistake_screen: bool = True         # localization calls also screen the likeliest step's mistake library
    mistake_screen_p: float = 0.5
    screen_updates_tracker: bool = False   # screen-triggered verdicts drive mistake alerts only (train-split choice)
    order_min_p: float = 0.8
    order_unseen_mass: float = 0.3
    order_conf: float = 0.6
    # live mode (praxis.live): model calls run on worker threads while the fast path keeps ticking, and each answer is
    # folded in when it arrives. replay() leaves this off, so the evaluation stays synchronous and deterministic.
    async_slow_path: bool = False
    async_workers: int = 4
    # multi-task (docs/MULTITASK.md). The tracker's away states are TrackerConfig.away_*; with away states on, the
    # policy doesn't verify or coach while P(away) >= away_p. Thresholds are chosen on the train split.
    multi_task: bool = False
    switching: bool = True               # False (task given): re-checks only confirm interruptions; never switch
    away_p: float = 0.7                  # P(away) that counts as "away" (starts the leave timer)
    fit_window_s: float = 20.0           # poor fit = mean P(away) over this window ...
    fit_thr: float = 0.6                 # ... at or above this -> typed "which task?" re-check
    recheck_min_gap_s: float = 20.0      # at most one re-check per this
    recheck_backoff: tuple = (30.0, 60.0, 120.0)   # next re-check after one confirms the current task
    recheck_every_s: float | None = None # optional periodic re-check while a task is active
    switch_p: float = 0.6                # typed-check P(other task) needed to switch ...
    switch_per_step: float = 0.05        # ... plus this for each completed step of the current task ...
    switch_max_p: float = 0.9            # ... capped here (uncapped, 0.8 + 0.05 x 4 steps reached 1.0: a task with
                                         # progress could never be left)
    switch_streak_override: int = 2      # this many consecutive re-checks naming the same other task at >= switch_p
                                         # switch regardless of the per-step bar (recent evidence wins); 0 = off
    switch_lm_agree: bool = True         # ... and the landmarks score the other task at least as high
    switch_confirmations: int = 1        # consecutive re-checks that must name the same other task
    leave_after_s: float = 15.0          # away this long with steps left -> paused (interruption) + one reminder
    retract_fast_s: float = 45.0         # a task replaced this soon with no step done was a wrong guess ...
    retract_away: float = 0.5            # ... or one that fit poorly (mean P(away)) the whole time it was current
    resume_bias: float = 0.0             # log-prior bonus for paused tasks on a re-check (looking back at them)
    rewind_on_leave: bool = False        # a task left for another / an interruption rewinds its tracker to when P(away)
    rewind_p: float = 0.5                # ... last rose above rewind_p (minus rewind_lag_s): the frames since then
    rewind_lag_s: float = 10.0           # belonged to something else, so steps "done" meanwhile are undone
    nontask_landmarks: bool = False      # baby / door / phone etc. mean interruption: skip the re-check (unmeasured)
    nontask_thr: float = 0.12            # SigLIP2 cosine for a non-task landmark to count
    # what's on screen: say the first instruction as soon as the task is known, and let the instruction follow the
    # belief when another, not-yet-done step holds the majority for follow_ticks ticks (it used to change only on a
    # commit, so it lagged the belief: results/enigma51/doc_value.json). Fixed defaults, not tuned.
    speak_on_start: bool = True
    follow_belief_p: float = 0.5
    follow_ticks: int = 3                # 0 = off
    recognize_thr: float | None = None   # optional earlier first commit (a wrong guess can now be undone): recognizer
    recognize_hold_s: float | None = None  # posterior threshold / hold time; None = the recognizer's own (0.9 / 2 s)
    recognize_min_s: float = 0.0          # no first task before this time (the first typed check comes at 4 s)
    recognize_agree: int = 1              # typed "which task?" answers in a row that must name the task first
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    policy: PolicyConfig = field(default_factory=PolicyConfig)


@dataclass(eq=False)
class _Job:
    """A slow-path call out on a worker thread (async mode)."""
    kind: str                 # verify | localize | order | task | draft
    key: tuple                # at most one job per key in flight: one check per step, one "which step?", one task check
    t: float                  # tick of the request: its frames end here, and the tracker applies its answer here
    fut: Future
    ctx: dict
    ticks: int = 0            # ticks the loop ran while the call was out
    task_id: str | None = None   # the task it was asked about (answers about a task no longer active are dropped)


@dataclass(eq=False)
class TaskSlot:
    """One task in the session's task set, with everything needed to pause and resume it where it was."""
    task_id: str
    graph: TaskGraph
    tracker: StateTracker
    policy: Policy
    status: str = "active"            # active | paused | done | done_enough | retracted
    status_t: float = 0.0
    started_t: float = 0.0
    oracle: bool = False
    last_switch_map: str | None = None
    max_mass: dict = field(default_factory=dict)
    order_flagged: set = field(default_factory=set)
    away_hist: collections.deque = field(default_factory=collections.deque)   # (t, P(away)) over the fit window
    away_since: float | None = None
    interrupted: bool = False         # paused by a sustained away (still the engine's current task)
    warned: bool = False              # the one "before you go" reminder was said
    warned_at: float | None = None
    last_check: tuple | None = None   # (t, decision) of the latest typed re-check while this task was current
    history: collections.deque = field(default_factory=lambda: collections.deque(maxlen=180))   # (t, P(away), state)
    away_sum: float = 0.0             # P(away) summed over the seconds it was current (after the grace period)
    away_n: int = 0
    asked_at: float | None = None     # "Coming back to ...?" asked (latest pause)
    answer: str | None = None         # coming_back | done (the person's answer to it)


def _timed(call):
    """Worker-thread wrapper: (answer, exception, seconds). The exception is raised again where the answer is folded
    in, so it is handled exactly as on the inline path."""
    t0 = time.perf_counter()
    try:
        return call(), None, time.perf_counter() - t0
    except Exception as e:  # noqa: BLE001
        return None, e, time.perf_counter() - t0


def _choose_step(loc, frames, opts: dict, title: str, screen: dict | None) -> dict:
    """Typed "which step?" call; the mistake screen rides along when the localizer supports it."""
    import inspect
    can_screen = "mistakes" in inspect.signature(loc.choose_step).parameters
    return loc.choose_step(frames, opts, title, mistakes=screen) if screen and can_screen \
        else loc.choose_step(frames, opts, title)


class Engine:
    def __init__(self, cfg: EngineConfig, library: dict[str, TaskGraph], evidence: dict, recognizer: TaskRecognizer | None,
                 detector, verifier=None, escalation=None, calibrator: Calibrator | None = None,
                 dev_calibrator: Calibrator | None = None, log: RunLog | None = None, task_id: str | None = None,
                 user: UserModel | None = None, point_tracker=None, calibrators: dict | None = None, localizer=None,
                 drafter=None, offtask=None, texts=None, task_checker=None):
        self.cfg, self.lib, self.evidence = cfg, library, evidence
        self.drafter = drafter        # open-set: frames -> (draft TaskGraph, zero-shot evidence); see tasks/drafter.py
        self._none_streak = 0
        self._drafted = False
        self.loc = localizer          # which verifier answers "which step?" (defaults to the fast verifier)
        self.rec, self.det = recognizer, detector
        self.tc = task_checker or verifier     # who answers "which task?" (recognition and re-checks); default: fast tier
        if recognizer is not None and cfg.recognize_thr is not None:
            recognizer.threshold = cfg.recognize_thr
        if recognizer is not None and cfg.recognize_hold_s is not None:
            recognizer.hold_s = cfg.recognize_hold_s
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
        self._ll_now = None
        self._max_mass: dict[str, float] = {}
        self._order_flagged: set[str] = set()
        self._last_task_probs: dict[str, float] = {}
        self._last_choice: str | None = None
        self._choice_streak = 0
        self._last_r = None           # the recognizer's latest result (a late task-check answer is folded into it)
        # async slow path: worker threads, the calls in flight, and the journal of each tick's tracker inputs that a
        # late answer is replayed against
        self._pool: ThreadPoolExecutor | None = None
        self._jobs: list[_Job] = []
        self._journal: list[dict] = []
        self.async_stats: collections.Counter = collections.Counter()
        # multi-task: the task set, the active slot, landmarks + off-task model (drive the tracker's away states)
        self.tasks: dict[str, TaskSlot] = {}
        self.slot: TaskSlot | None = None
        self.offtask = offtask
        self.lm = None
        if offtask is not None and (cfg.multi_task or cfg.tracker.away_enter > 0):
            from .landmarks import Landmarks, TextCache
            texts = texts if texts is not None else TextCache()
            self.lm = Landmarks(library, texts=texts, window_s=offtask.window_s, top_frac=offtask.top_frac)
        self._p_off: float | None = None
        self._next_recheck = 0.0
        self._last_recheck = -1e9
        self._recheck_i = 0
        self._switch_cand: tuple[str, int] | None = None
        self._lead_checked: str | None = None
        self._strong_streak: tuple = (None, 0)
        self._t_last = 0.0
        self._away_ok_t = offtask.window_s if offtask is not None else 0.0   # landmark window full of this task
        self._follow: tuple = (None, 0)
        if task_id is not None:
            self._start_task(0.0, task_id, oracle=True)
            if cfg.speak_on_start:          # the task is known at the start: say the first instruction right away
                self._emit(self.policy.start(0.0, self.tracker.belief().map_id))

    # ------------------------------------------------------------------ helpers
    def _w(self, kind: str, t: float, **kw) -> None:
        if self.log:
            self.log.write(kind, t, **kw)

    def _start_task(self, t: float, task_id: str, oracle: bool = False, posterior: dict | None = None) -> list[Action]:
        self._stash()
        self.task_id, self.graph = task_id, self.lib[task_id]
        # per-task state keyed by step ids (a Studio session can switch tasks; at the first start these are empty)
        self._last_switch_map = None
        self._max_mass, self._order_flagged = {}, set()
        self.tracker = StateTracker(self.graph, self.cfg.tracker, join_mid_task=self.cfg.join_mid_task)
        self._journal = []
        if not self.cfg.join_mid_task and self.cfg.start_prior_mass < 1.0:
            a = self.tracker.alpha
            a *= self.cfg.start_prior_mass
            a[:-1, :10] += (1 - self.cfg.start_prior_mass) / ((self.tracker.K - 1) * 10)
            self.tracker.alpha = a / a.sum()
        self.policy = Policy(self.graph, self.cfg.policy, self.user)
        if self.slot is not None and self.lm is not None:     # a switch: the window still shows the previous task
            self._away_ok_t = t + self.lm.window_s
        self.slot = TaskSlot(task_id, self.graph, self.tracker, self.policy, status_t=t, started_t=t, oracle=oracle,
                             max_mass=self._max_mass, order_flagged=self._order_flagged)
        self.tasks[task_id] = self.slot
        self._recheck_i, self._switch_cand = 0, None
        self._follow = (None, 0)
        self._next_recheck = t + self.cfg.recheck_min_gap_s
        ev = self.evidence.get(task_id)
        if ev is not None and list(ev.ids) != list(self.graph.ids):
            raise ValueError(f"evidence node order != graph node order for {task_id}")
        self._w("task", t, task_id=task_id, title=self.graph.title, oracle=oracle, posterior=posterior,
                n_steps=len(self.graph.nodes))
        text = (f"Looks like you're {activity_phrase(self.graph)}. I don't have a plan for that yet, so I drafted one "
                f"from what I've seen. Tell me if a step looks off." if self.graph.draft else
                f"Looks like you're {activity_phrase(self.graph)}. Want me to walk you through it?")
        acts = [Action(t, "announce_task", text, None, {"oracle": oracle, "title": self.graph.title,
                                                        "draft": self.graph.draft})]
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
        if self.cfg.async_slow_path:
            self.poll(t)
            for j in self._jobs:
                j.ticks += 1
        self.n_frames += n
        fe, we = rows["frame"], rows["window"]
        self._feat_now = {"siglip": fe.mean(0), "window": we[-1]}     # local features at t (for the distilled student)
        for tt, b in zip(rows["t"], rows["boundary"]):
            self._bscores.append((float(tt), float(b)))
        for tt, g in zip(rows["t"], rows["grasp"]):
            self._gscores.append((float(tt), float(g)))
        self._w("fast", t, boundary=float(rows["boundary"].max()), grasp=float(rows["grasp"].max()),
                hands=int((rows["hands"][:, 0] > 0).any() or (rows["hands"][:, 6] > 0).any()) if "hands" in rows else None)
        self._t_last = t
        if self.lm is not None:                 # landmarks: one matrix product per second (fast path)
            self.lm.update(fe)
            self._log_landmarks(t)

        # L3b: which task?
        if self.graph is None:
            if self.rec is None:
                return
            r = None
            for i in range(n):
                r = self.rec.update(float(rows["t"][i]), fe[i], we[i], dt=1.0 / n)
            self._last_r = r
            # slow path for L3b: a typed "which task is this?" verifier check at 4 s, then every 6 s until recognized
            if self.tc is not None and hasattr(self.tc, "choose_task") and t >= self._next_task_check \
                    and not self._busy(("task",)):
                self._next_task_check = t + 6.0
                frames, _ = span_keyframes(frame_at, t)
                if frames:
                    opts = {tid: f"{g.title}: {g.summary[:160]}" for tid, g in self.lib.items()}
                    call = partial(self.tc.choose_task, frames, opts)
                    if self.cfg.async_slow_path:
                        self._submit("task", ("task",), t, call)        # poll() folds the answer in when it arrives
                    else:
                        r = self._task_answer(t, r, call)
            r = self._gate(r)
            self._w("recognizer", t, top=r.task_id, posterior=r.posterior, recognized=r.recognized, open_set=r.open_set)
            if (not r.recognized and self.cfg.open_set_draft and self.drafter is not None and not self._drafted
                    and t >= self.cfg.open_set_min_s and (self._none_streak >= self.cfg.open_set_none_streak
                                                          or t >= self.cfg.open_set_max_wait_s)):
                self._drafted = True
                from .tasks.drafter import keyframes_for_draft
                t0 = max(0.0, t - self.cfg.open_set_window_s)
                if self.cfg.async_slow_path:                            # poll() installs the draft when it arrives
                    self._submit("draft", ("draft",), t, partial(self.drafter, keyframes_for_draft(frame_at, t0, t)))
                else:
                    return self._draft_answer(t, lambda: self.drafter(keyframes_for_draft(frame_at, t0, t)))
            if r.recognized:
                self._start_recognized(t, r)
            return

        if self.cfg.multi_task and self.rec is not None:     # keep the task posterior current after commit (local)
            for i in range(n):
                self._last_r = self.rec.update(float(rows["t"][i]), fe[i], we[i], dt=1.0 / n)
        tr, pol = self.tracker, self.policy
        tr.predict()
        ops = [("predict",)]                    # this tick's tracker inputs (journaled in async mode)
        # L4 fast evidence
        if self.cfg.tracker_mode in ("fused", "local"):
            ev = self.evidence.get(self.task_id)
            if ev is not None:
                ll = ev.loglik(fe, we)
                self._ll_now = ll
                tr.observe_local(ll)
                ops.append(("local", ll))
            b = float(rows["boundary"].max())
            tr.observe_boundary(b)
            ops.append(("boundary", b))
        # off-task evidence for the away states: landmarks of this task vs the others
        self._p_off = None
        if self.lm is not None and self.offtask is not None and tr.cfg.away_enter > 0 and t >= self._away_ok_t:
            self._p_off = self.offtask.p_off(self.lm.features(self.task_id))
            if self._p_off is not None:
                tr.observe_away(self._p_off)
                ops.append(("away", self._p_off))
        belief = tr.belief()

        for nid, pk in zip(belief.ids, belief.p):
            if pk > self._max_mass.get(nid, 0.0):
                self._max_mass[nid] = float(pk)

        # implicit commit: belief confidently moved on from a step -> that step is done
        prev = self._last_switch_map
        if prev and belief.map_id != prev and prev != DONE and belief.map_p_on >= self.cfg.commit_on_switch_p \
                and prev not in tr.completed and self.cfg.tracker_mode != "verifier":
            tr.mark_complete(prev)
            ops.append(("commit", prev))
            belief = tr.belief()
            self._w("commit", t, node=prev, reason="belief_switch")
            if belief.map_id != DONE:
                self._check_order(t, belief, frame_at)
                self._emit(pol.start(t, belief.map_id))
        self._last_switch_map = belief.map_id
        self._follow_belief(t, belief)
        if self.cfg.async_slow_path:
            self._journal.append({"t": t, "ops": ops, "snap": self._snapshot(), "late": []})

        # multi-task: interruptions, leave reminders, re-checks, switches, timeouts
        if self.cfg.multi_task:
            self._task_set_tick(t, belief, frame_at)
            if self.tracker is not tr:          # switched to another task, or the task ended: it starts next tick
                return
            belief = tr.belief()
        # away from the task (an interruption confirmed, see _task_set_tick): don't verify or coach it. P(away) alone
        # doesn't stop coaching: on recipes whose landmarks are shared with others it runs high while on task.
        away = self.slot is not None and self.slot.interrupted

        # L2 peaks (causal: a peak is confirmed one frame after it)
        bpeak = self._causal_peak(self._bscores, self.cfg.boundary_thr, "_last_peak_t")
        gpeak = self._causal_peak(self._gscores, self.cfg.grasp_thr, "_last_grasp_t")
        if bpeak:
            self._w("event", t, event="boundary", score=bpeak)
        if gpeak:
            self._w("event", t, event="onset", score=gpeak)

        # L5 at events
        reason = None
        if self.cfg.use_verifier and self.ver is not None and belief.map_id != DONE and not away:
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
        if not away:
            self._emit(pol.hesitation(t, belief))
        bd = belief.as_dict()
        bd.pop("t", None)
        if self.cfg.multi_task:
            bd["task_id"] = self.task_id
        self._w("belief", t, **bd, user=self.user.state())
        if self.cfg.async_slow_path:
            self._prune()

    def _follow_belief(self, t: float, belief) -> None:
        """The on-screen instruction follows a confident belief change without waiting for a commit."""
        cfg, pol, tr = self.cfg, self.policy, self.tracker
        m = belief.map_id
        if not cfg.follow_ticks or m == DONE or m == pol.announced_step or m in tr.completed \
                or belief.map_p_on < cfg.follow_belief_p or (self.slot is not None and self.slot.interrupted):
            self._follow = (None, 0)
            return
        n = self._follow[1] + 1 if self._follow[0] == m else 1
        self._follow = (m, n)
        if n >= cfg.follow_ticks:
            self._emit(pol.start(t, m))
            self._follow = (None, 0)

    def _causal_peak(self, scores, thr, attr) -> float | None:
        if len(scores) < 3:
            return None
        (t1, s1), (t2, s2), (t3, s3) = scores[-3:]
        if s2 >= thr and s2 >= s1 and s2 > s3 and t2 - getattr(self, attr) >= self.cfg.min_gap_s:
            setattr(self, attr, t2)
            return s2
        return None

    # ------------------------------------------------------------------ multi-task: the task set
    def _stash(self) -> None:
        """Write the active task's per-task engine state back into its slot (before it is paused or replaced)."""
        sl = self.slot
        if sl is None:
            return
        sl.last_switch_map, sl.max_mass, sl.order_flagged = self._last_switch_map, self._max_mass, self._order_flagged

    def _activate(self, sl: TaskSlot) -> None:
        self.slot = sl
        self.task_id, self.graph, self.tracker, self.policy = sl.task_id, sl.graph, sl.tracker, sl.policy
        self._last_switch_map, self._max_mass, self._order_flagged = sl.last_switch_map, sl.max_mass, sl.order_flagged
        self._journal = []
        sl.away_hist.clear()
        sl.away_since, sl.interrupted = None, False
        sl.tracker.come_back()
        if self.lm is not None:
            self._away_ok_t = self._t_last + self.lm.window_s
        self._recheck_i, self._switch_cand = 0, None
        self._next_recheck = self._t_last + self.cfg.recheck_min_gap_s

    def _end_active(self) -> None:
        """No current task any more (done enough, or the person asked for a draft): back to recognizing."""
        self._stash()
        self.slot = None
        self.task_id = self.graph = self.tracker = self.policy = None
        self._journal = []
        if self.cfg.multi_task:
            self._next_task_check = self._t_last + 4.0

    def _set_status(self, t: float, sl: TaskSlot, to: str, reason: str, **evidence) -> None:
        b = sl.tracker.belief()
        extra = {"open_steps": [n.id for n in self._open_steps(sl)]} if to == "done_enough" else {}
        self._w("task_state", t, task_id=sl.task_id, title=sl.graph.title, **{"from": sl.status}, to=to, reason=reason,
                step_index=len(sl.tracker.completed), n_steps=len(sl.graph.nodes),
                at_step=b.map_id if b.map_id != DONE else None, p_away=round(b.p_away, 4), evidence=evidence or None,
                **extra)
        sl.status, sl.status_t = to, t

    def _open_steps(self, sl: TaskSlot) -> list:
        return [n for n in sl.graph.nodes if n.id not in sl.tracker.completed]

    def _next_node(self, sl: TaskSlot):
        b = sl.tracker.belief()
        if b.map_id != DONE and b.map_id not in sl.tracker.completed:
            return sl.graph.node(b.map_id)
        left = self._open_steps(sl)
        return left[0] if left else None

    def _reminder(self, sl: TaskSlot) -> str | None:
        """'Before you go...' for a task left with steps to go, at most once per task, and only once at least one
        step of it was done (a wrong guess or a task barely started gets no reminder)."""
        left = self._open_steps(sl)
        if sl.warned or not left or not sl.tracker.completed:
            return None
        sl.warned = True
        nxt = self._next_node(sl)
        what = _lower_first(nxt.instruction_expert or nxt.name)
        if len(left) == 1:
            return f"Before you go, one more step on the {task_short(sl.graph)}: {what}."
        return f"Before you go, {len(left)} steps are left on the {task_short(sl.graph)}. Next: {what}."

    def _leave(self, t: float, sl: TaskSlot, reason: str, to_task: str | None = None) -> bool:
        """The person left task sl: pause it with its state, or retract it if nothing of it was ever confirmed (a
        wrong first guess; kept in the set, resumable, but no chip and no reminder). Returns True if retracted."""
        self._stash()
        self._rewind(t, sl)
        fit_poor = sl.away_n > 0 and sl.away_sum / sl.away_n >= self.cfg.retract_away
        retract = not sl.tracker.completed and not sl.oracle and (t - sl.started_t < self.cfg.retract_fast_s or fit_poor)
        self._set_status(t, sl, "retracted" if retract else "paused", "wrong_guess" if retract else reason,
                         **({"to_task": to_task} if to_task else {}))
        sl.interrupted, sl.away_since = False, None
        stale = [j for j in self._jobs if j.kind in ("verify", "localize", "order") and j.task_id == sl.task_id]
        self._jobs = [j for j in self._jobs if j not in stale]
        self.async_stats["dropped_on_task_switch"] += len(stale)
        return retract

    def _rewind(self, t: float, sl: TaskSlot) -> None:
        """Roll the left task's tracker back to just before P(away) last rose above rewind_p (minus rewind_lag_s): its
        filter kept running on the new activity's frames until the switch was detected."""
        if not self.cfg.rewind_on_leave or not sl.history:
            return
        h = list(sl.history)
        k = len(h)
        while k > 0 and h[k - 1][1] >= self.cfg.rewind_p:
            k -= 1
        t0 = (h[k][0] if k < len(h) else t) - self.cfg.rewind_lag_s
        snap = next((x for x in reversed(h) if x[0] <= t0), h[0])
        before = set(sl.tracker.completed)
        sl.tracker.set_state(snap[2])
        sl.history.clear()
        self._w("rewind", t, task_id=sl.task_id, to_t=snap[0], undone=sorted(before - sl.tracker.completed))

    def _resume(self, t: float, sl: TaskSlot, reason: str) -> None:
        """Make a paused (or retracted, or done-enough) task current again, exactly where it was."""
        self._activate(sl)
        self._set_status(t, sl, "active", "resumed", how=reason)
        self._emit([self._resume_action(t, sl)])

    def _resume_action(self, t: float, sl: TaskSlot) -> Action:
        nxt = self._next_node(sl)
        if nxt is None:
            return Action(t, "resume_task", f"Back to the {task_short(sl.graph)}.", None, {"title": sl.graph.title})
        sl.policy.announced_step = nxt.id
        return Action(t, "resume_task", f"Back to the {task_short(sl.graph)}. Next: "
                                        f"{_lower_first(nxt.instruction_expert or nxt.name)}.",
                      nxt.id, {"title": sl.graph.title, "chip": nxt.name, "step_index": len(sl.tracker.completed)})

    def _switch(self, t: float, to: str, evidence: dict) -> None:
        """Another task is happening: pause (or retract) the current one, then resume `to` if it is in the set, else
        start it."""
        old = self.slot
        retracted = self._leave(t, old, "switch", to_task=to)
        prev = self.tasks.get(to)
        if prev is not None and prev is not old:
            q = None if retracted else self._leave_line(t, old, None)   # the task being left: "Coming back to ...?"
            self._activate(prev)
            self._set_status(t, prev, "active", "resumed", how="switch", check=evidence)
            a = self._resume_action(t, prev)                    # the paused chip shows where the other one stopped
            if q:
                a.text, a.detail["ask_resume"] = f"{a.text} {q}", old.task_id
            return self._emit([a])
        acts = self._start_task(t, to, posterior=evidence.get("probs"))
        new = self.graph
        a = acts[0]
        a.kind = "retract_task" if retracted else "switch_task"
        nxt = None if retracted else self._next_node(old)
        if retracted:
            a.text = f"My mistake, this looks like {activity_phrase(new)}, not the {task_short(old.graph)}."
        elif nxt is not None and old.tracker.completed:            # left with steps to go: name where it stopped
            old.warned = True
            q = self._leave_line(t, old, None)
            a.text = (f"Looks like you've moved on to {activity_phrase(new)}. I paused the {task_short(old.graph)} at: "
                      f"{_lower_first(nxt.instruction_expert or nxt.name)}.{' ' + q if q else ''}")
            a.detail["ask_resume"] = old.task_id
        else:
            a.text = f"Looks like you've moved on to {activity_phrase(new)}. I'll keep your place in the {task_short(old.graph)}."
        a.detail.update({"from": old.task_id, "from_title": old.graph.title, "evidence": evidence})
        acts += self.policy.start(t, self.tracker.belief().map_id)
        self._emit(acts)

    def _log_landmarks(self, t: float) -> None:
        top = self.lm.top_tasks(3)
        if not top:
            return
        nt, ns = self.lm.non_task_top()
        self._w("landmarks", t, top=[[k, round(v, 4)] for k, v in top],
                non_task=[nt, round(ns, 4)] if nt else None,
                p_off=None if self._p_off is None else round(self._p_off, 4))

    def _task_set_tick(self, t: float, belief, frame_at) -> None:
        cfg, sl = self.cfg, self.slot
        sl.away_hist.append((t, belief.p_away))
        if cfg.rewind_on_leave:
            sl.history.append((t, belief.p_away, sl.tracker.state()))
        if t >= self._away_ok_t:
            sl.away_sum, sl.away_n = sl.away_sum + belief.p_away, sl.away_n + 1
        while sl.away_hist and sl.away_hist[0][0] <= t - cfg.fit_window_s:
            sl.away_hist.popleft()
        if sl.status == "active" and belief.map_id == DONE and belief.map_p >= 0.9:
            self._set_status(t, sl, "done", "finished")
        # away from the current task: after leave_after_s, confirmed by the typed check ("none of these") or a
        # non-task landmark, it is paused (interruption) with one reminder and "Coming back to ...?"; coming back
        # resumes it. It stays paused (never closed on a timer) until the person answers "I'm done" or the session
        # ends. Without a typed check available, sustained P(away) alone confirms.
        if belief.p_away >= cfg.away_p:
            if sl.away_since is None:
                sl.away_since = t
            nt, ns = self.lm.non_task_top() if self.lm is not None else (None, 0.0)
            landmark = nt if cfg.nontask_landmarks and ns >= cfg.nontask_thr else None
            can_check = self.tc is not None and hasattr(self.tc, "choose_task")
            said_none = sl.last_check is not None and sl.last_check[1] == "none" and \
                sl.last_check[0] >= sl.away_since - cfg.recheck_min_gap_s
            if not sl.interrupted and sl.status == "active" and t - sl.away_since >= cfg.leave_after_s \
                    and (said_none or landmark or not can_check):
                sl.interrupted = True
                sl.tracker.frozen = True                # decoupled away mode: the step clock stops while away
                self._set_status(t, sl, "paused", "interruption", away_s=round(t - sl.away_since, 1), non_task=landmark,
                                 confirmed_by="task_check" if said_none else "landmark" if landmark else "p_away")
                line = self._leave_line(t, sl, self._reminder(sl))
                if line:
                    sl.warned_at = t
                    self._emit([Action(t, "leave_warning", line, None, {"title": sl.graph.title, "task_id": sl.task_id,
                                                                       "ask_resume": True})])
        elif belief.p_away < cfg.away_p - 0.2:          # hysteresis
            sl.away_since = None
            if sl.interrupted:
                sl.interrupted = False
                sl.tracker.frozen = False
                said = sl.warned_at is not None and sl.warned_at >= sl.status_t
                away_s = t - sl.status_t
                self._set_status(t, sl, "active", "resumed", how="came_back", paused_s=round(away_s, 1))
                if said or away_s >= 30.0:              # a short false alarm resumes silently
                    self._emit([self._resume_action(t, sl)])
        self._maybe_recheck(t, sl, frame_at)

    def _leave_line(self, t: float, sl: TaskSlot, reminder: str | None) -> str | None:
        """The leave moment: the reminder (once per task) plus "Coming back to the ...?", asked when the task was left
        with steps to go after at least one step of it was done. The question is logged as an `ask_resume` record; the
        answer comes from the person (answer_resume) or never (then the task stays paused until the session ends)."""
        if not self._open_steps(sl) or not sl.tracker.completed or sl.answer == "done":
            return reminder
        q = f"Coming back to the {task_short(sl.graph)}?"
        sl.asked_at, sl.answer = t, None
        self._w("ask_resume", t, task_id=sl.task_id, title=sl.graph.title, question=q,
                open_steps=[n.id for n in self._open_steps(sl)])
        return f"{reminder} {q}" if reminder else q

    # ------------------------------------------------------------------ the person's answers; session end
    def answer_resume(self, t: float, task_id: str, answer: str, via: str = "tap") -> None:
        """'Coming back' keeps the task paused with its state; "I'm done" closes it as done enough (logged with its open
        steps). If it was the current task (an interruption), Praxis goes back to recognizing what comes next."""
        sl = self.tasks.get(task_id)
        if sl is None or answer not in ("coming_back", "done"):
            return
        self._w("resume_answer", t, task_id=task_id, answer=answer, via=via, asked_at=sl.asked_at)
        sl.answer = answer
        if answer == "done" and sl.status in ("paused", "active", "retracted"):
            current = sl is self.slot
            if current:
                self._stash()
            self._set_status(t, sl, "done_enough", "user_done")
            if current:
                sl.interrupted = False
                self._end_active()

    def finish(self, t: float) -> None:
        """Session end: tasks still paused (including an interrupted current one) are closed as done enough."""
        for sl in list(self.tasks.values()):
            if sl.status == "paused":
                self._set_status(t, sl, "done_enough", "session_end")

    def _maybe_recheck(self, t: float, sl: TaskSlot, frame_at) -> bool:
        cfg = self.cfg
        # re-check which task this is: on a poor fit, after the task finished while others are paused, or periodically.
        # After a check confirms the current task, the next one waits (backoff) unless another task newly leads on
        # landmarks: other tasks' evidence can always call for a check.
        if self.tc is None or not hasattr(self.tc, "choose_task") or self._busy(("task",)) \
                or t - self._last_recheck < cfg.recheck_min_gap_s:
            return False
        fit = float(np.mean([p for _, p in sl.away_hist])) if len(sl.away_hist) >= 0.8 * cfg.fit_window_s else 0.0
        top = self.lm.top_tasks(1) if self.lm is not None else []
        lead = top[0][0] if top else None
        new_lead = lead is not None and lead != sl.task_id and lead != self._lead_checked
        due = t >= self._next_recheck
        reason = None
        if fit >= cfg.fit_thr and (due or new_lead):
            reason = "poor_fit"
        elif due and sl.status == "done" and any(o.status == "paused" for o in self.tasks.values()):
            reason = "resume"
        elif due and cfg.recheck_every_s and t - self._last_recheck >= cfg.recheck_every_s:
            reason = "periodic"
        if reason is None:
            return False
        if cfg.nontask_landmarks and self.lm is not None and reason == "poor_fit":
            nt, ns = self.lm.non_task_top()
            if nt and ns >= cfg.nontask_thr:            # baby, door, phone: an interruption, not another task
                self._next_recheck = t + cfg.recheck_min_gap_s
                self._w("recheck_skipped", t, reason="non_task_landmark", landmark=nt, score=round(ns, 4))
                return False
        frames, _ = span_keyframes(frame_at, t)
        if not frames:
            return False
        self._next_recheck, self._last_recheck, self._lead_checked = t + cfg.recheck_min_gap_s, t, lead
        opts = {tid: f"{g.title}: {g.summary[:160]}" for tid, g in self.lib.items()}   # same question as recognition
        call = partial(self.tc.choose_task, frames, opts)
        ctx = {"reason": reason, "fit": round(fit, 4)}
        if self.cfg.async_slow_path:
            self._submit("task", ("task",), t, call, **ctx)
        else:
            self._recheck_answer(t, call, **ctx)
        return True

    def _recheck_answer(self, t: float, call, reason: str, fit: float | None = None, t_now: float | None = None,
                        extra: dict | None = None) -> None:
        """A re-check's answer: keep the current task (and back off), switch to / resume another one, or, on 'none of
        these', count it as evidence of being away."""
        cfg = self.cfg
        try:
            ans = call()
        except Exception as e:  # noqa: BLE001
            return self._w("task_check", t, error=str(e)[:200], reason=reason, **(extra or {}))
        t_out = t + ans["latency_ms"] / 1000.0 if t_now is None else t_now
        probs, ch, cur = ans["probs"], ans["choice"], self.task_id
        raw = probs
        if cfg.resume_bias and any(o.status == "paused" and k == o.task_id for k in probs for o in self.tasks.values()):
            w = {k: v * (np.exp(cfg.resume_bias) if (o := self.tasks.get(k)) is not None and o.status == "paused" else 1.0)
                 for k, v in probs.items()}
            z = sum(w.values()) or 1.0
            probs = {k: v / z for k, v in w.items()}
            ch = max(probs, key=probs.get)
        if self.rec is not None:
            self.rec.observe_verifier(raw)
        self._last_task_probs = raw
        lm = self.lm.scores() if self.lm is not None else {}
        need = min(cfg.switch_max_p, cfg.switch_p + cfg.switch_per_step * len(self.tracker.completed))
        if ch != cur and ch not in self.lib:
            self._strong_streak = (None, 0)
        if ch == cur:
            self._strong_streak = (None, 0)
            decision = "keep"
            self._next_recheck = t_out + cfg.recheck_backoff[min(self._recheck_i, len(cfg.recheck_backoff) - 1)]
            self._recheck_i += 1
            self._switch_cand = None
        elif ch in self.lib:
            streak = self._switch_cand[1] + 1 if self._switch_cand and self._switch_cand[0] == ch else 1
            self._switch_cand = (ch, streak)
            strong = probs.get(ch, 0.0) >= cfg.switch_p
            self._strong_streak = (ch, self._strong_streak[1] + 1 if strong and self._strong_streak[0] == ch else int(strong))
            lm_ok = not cfg.switch_lm_agree or not lm or lm.get(ch, -1e9) >= lm.get(cur, -1e9)
            override = bool(cfg.switch_streak_override) and self._strong_streak[1] >= cfg.switch_streak_override
            ok = (probs.get(ch, 0.0) >= need or override) and lm_ok and streak >= cfg.switch_confirmations
            decision = "switch" if ok else ("hold_landmarks" if not lm_ok else "hold_confidence"
                                            if probs.get(ch, 0.0) < need else "hold_confirm")
        else:
            decision = "none"
            self._switch_cand = None
        if decision == "switch" and not cfg.switching:
            decision = "hold_task_given"                # the person said which task: never switch away from it
        self.slot.last_check = (t, decision)
        self._w("task_check", t, choice=ch, probs=probs, raw_probs=raw if raw is not probs else None,
                latency_ms=ans["latency_ms"], model=ans["model"],
                cost_usd=ans["cost_usd"], reason=reason, fit=fit, current=cur, decision=decision, need=round(need, 3),
                landmarks={k: round(v, 4) for k, v in sorted(lm.items(), key=lambda kv: -kv[1])[:3]} or None,
                **(extra or {}))
        if decision == "switch":
            self._switch(t_out, ch, {"p": round(probs.get(ch, 0.0), 3), "reason": reason, "fit": fit,
                                     "probs": {k: round(v, 3) for k, v in probs.items()}})
        elif self.tracker.cfg.away_enter > 0 and decision in ("none", "keep"):
            # a typed answer counts as one observation: "none of these" for being away, the current task for being on it
            self._observe(t, ("away", probs.get("none", 0.0) if decision == "none" else 1.0 - probs.get(cur, 0.0), 1.0))
            if decision == "keep" and self.slot.away_since is not None:
                self.slot.away_since = t_out        # doing it, says the check: the done-enough clock starts over

    # ------------------------------------------------------------------ slow path
    # Each slow-path call has a request half (main thread: pick frames, build the question), a call (the model calls;
    # a worker thread in async mode) and an answer half (main thread: log, tracker, policy). Inline, the three run in a
    # row; async, the answer half runs when poll() finds the call done.
    def _task_answer(self, t: float, r, call, **extra):
        """Fold a typed "which task?" answer into the recognizer. call() returns it, or raises the call's error."""
        try:
            ans = call()
            self.rec.observe_verifier(ans["probs"])
            self._last_task_probs = ans["probs"]
            self._w("task_check", t, choice=ans["choice"], probs=ans["probs"], latency_ms=ans["latency_ms"],
                    model=ans["model"], cost_usd=ans["cost_usd"], **extra)
            post = self.rec.posterior()
            top = max(post, key=post.get)
            ch = ans["choice"]
            self._choice_streak = self._choice_streak + 1 if ch == self._last_choice else 1
            self._last_choice = ch
            self._none_streak = self._none_streak + 1 if ch not in self.lib else 0
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
            self._w("task_check", t, error=str(e)[:200], **extra)
        return r

    def _gate(self, r):
        """Announce only what the latest verifier task check also supports; optionally not before recognize_min_s and
        only after recognize_agree typed answers in a row named the task (a confident checker guessing from the first
        frames)."""
        if r.recognized and self.tc is not None and hasattr(self.tc, "choose_task"):
            if self._last_task_probs.get(r.task_id, 0.0) < 0.5:
                r = replace(r, recognized=False)
            elif self.cfg.recognize_agree > 1 and not (self._last_choice == r.task_id
                                                       and self._choice_streak >= self.cfg.recognize_agree):
                r = replace(r, recognized=False)
        if r.recognized and r.t < self.cfg.recognize_min_s:
            r = replace(r, recognized=False)
        return r

    # ------------------------------------------------------------------ tasks chosen outside the engine (Studio)
    def start_task(self, t: float, task_id: str, graph=None, evidence=None, how: str = "picked") -> None:
        """Start (or switch to) a task the person chose: picked from the library, pasted instructions compiled to a
        graph, or matched from what they typed. Announces it and gives the first instruction right away. Answers still
        out for a previous task are dropped (they refer to its steps)."""
        if graph is not None:
            self.lib = {**self.lib, task_id: graph}
        if evidence is not None:
            self.evidence = {**self.evidence, task_id: evidence}
        stale = [j for j in self._jobs if j.kind in ("verify", "localize", "order")]
        self._jobs = [j for j in self._jobs if j not in stale]
        self.async_stats["dropped_on_task_switch"] += len(stale)
        self._drafted = True                     # a chosen task replaces open-set drafting
        if self.lm is not None and graph is not None:
            self.lm.add_task(task_id, graph)
        if self.cfg.multi_task and self.slot is not None and self.slot.task_id != task_id:
            self._leave(t, self.slot, "user_switch")
            old = self.tasks.get(task_id)
            if old is not None and old.status != "active" and graph is None:
                return self._resume(t, old, "user_switch")
        acts = self._start_task(t, task_id, oracle=True)
        acts[0].text = f"Got it: {activity_phrase(self.graph)}. I'll walk you through it."
        acts[0].detail["how"] = how
        acts += self.policy.start(t, self.tracker.belief().map_id)
        self._emit(acts)

    def request_draft(self, drafter, at_s: float = 0.0) -> None:
        """The person said what they are doing and it isn't in the library: draft a graph from the frames so far plus
        their description on the first tick at or after at_s (open-set path, `tasks/drafter.py`), so a description
        given at the start waits for a few seconds of video. Clears a task already running."""
        if self.rec is None:
            raise ValueError("drafting needs the recognizer path (engine started without a task)")
        self.drafter = drafter
        self.cfg.open_set_draft, self.cfg.open_set_min_s, self.cfg.open_set_max_wait_s = True, at_s, at_s
        self._drafted = False
        if self.graph is not None:
            self._jobs = [j for j in self._jobs if j.kind not in ("verify", "localize", "order")]
            if self.cfg.multi_task and self.slot is not None:
                self._leave(self._t_last, self.slot, "user_switch")
            self._end_active()

    def _start_recognized(self, t: float, r) -> None:
        old = self.tasks.get(r.task_id)
        if self.cfg.multi_task and old is not None and old.status in ("paused", "retracted", "done_enough"):
            return self._resume(t, old, "recognized")
        acts = self._start_task(t, r.task_id, posterior=r.posterior)
        start = self.tracker.belief().map_id
        acts += self.policy.start(t, start)
        self._emit(acts)

    def _draft_answer(self, t: float, call, t_now: float | None = None, **extra) -> None:
        """Install an open-set draft graph and start tracking it. call() returns (graph, evidence) or raises."""
        try:
            g, ev = call()
        except Exception as e:  # noqa: BLE001
            self._w("task_draft", t, error=str(e)[:200], **extra)
            return
        self.lib = {**self.lib, g.task_id: g}
        self.evidence = {**self.evidence, g.task_id: ev}
        if self.lm is not None:
            self.lm.add_task(g.task_id, g)
        self._w("task_draft", t, task_id=g.task_id, title=g.title, steps=[n.name for n in g.nodes],
                **{k: g.compiler.get(k) for k in ("model", "confidence", "cost_usd", "latency_s", "cached")}, **extra)
        ts = t if t_now is None else t_now
        acts = self._start_task(ts, g.task_id)
        acts += self.policy.start(ts, self.tracker.belief().map_id)
        self._emit(acts)

    def _verify(self, t: float, belief, reason: str, frame_at, update_tracker: bool = True,
                frames: list | None = None, times: list | None = None) -> None:
        tr, pol, g = self.tracker, self.policy, self.graph
        node = g.node(belief.map_id)
        if self._busy(("verify", node.id)):
            return self._skip(t, "verify", node.id)
        # evidence: sharpest frame from ~8-6 s ago (context) + 2 sharpest of the last 3 s ("now");
        # head-mounted video is often motion-blurred, so frames are picked by sharpness
        if frames is None:
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
        call = partial(self._verify_call, req, reason, pol)
        ctx = {"node": node, "reason": reason, "n_frames": len(frames), "update_tracker": update_tracker}
        if self.cfg.async_slow_path:
            return self._submit("verify", ("verify", node.id), t, call, **ctx)
        self._verify_answer(t, call(), **ctx)

    def _verify_call(self, req: VerifyRequest, reason: str, pol: Policy) -> list[tuple]:
        """The model calls of one completion check: the fast verifier, then the strong one when the policy says so.
        Returns [(verdict, reason, calibrated P(complete), P(deviation)), ...]."""
        v = self.ver.verify(req)
        pc, pdv = self._calibrated(v, "primary")
        chain = [(v, reason, pc, pdv)]
        # two-tier verification: the fast verifier handles clear cases; ambiguity, possible mistakes and
        # "can't see" go to the strong model before the wearer hears anything
        if self.cfg.escalate and self.esc is not None and v.error is None and pol.needs_escalation(v, pc):
            v2 = self.esc.verify(req)
            pc2, pdv2 = self._calibrated(v2, "escalation")
            chain.append((v2, "escalation", pc2, pdv2))
        return chain

    def _verify_answer(self, t: float, chain: list[tuple], node, reason: str, n_frames: int, update_tracker: bool,
                       t_now: float | None = None, extra: dict | None = None) -> None:
        """Act on a completion check's verdicts. t: the tick its frames were taken. t_now: when the answer arrived
        (async); inline, the wearer hears it after the calls' latency."""
        tr, pol = self.tracker, self.policy
        roles = [self._log_verdict(t, v, why, pc, extra) for v, why, pc, _ in chain]
        v, _, pc, pdv = chain[-1] if len(chain) > 1 and chain[-1][0].error is None else chain[0]
        self.n_escalated_frames += n_frames
        if v.error:
            return
        if update_tracker:
            self._observe(t, ("verdict", node.id, "complete" if pc >= 0.5 else
                              ("deviation" if v.step_status == "deviation" else "in_progress"), pc if pc >= 0.5 else 1 - pc))
        t_out = t + sum(r["latency_ms"] for r in roles) / 1000.0 if t_now is None else t_now
        acts, commit = pol.on_verdict(t_out, v, pc, pdv, tr.belief())
        if not update_tracker:          # mistake screen: only mistake alerts may come out of it
            acts = [a for a in acts if a.kind == "mistake"]
            commit = False
        self._emit(acts)
        if commit and node.id not in tr.completed:     # async: the belief may have moved past it meanwhile
            self._observe(t, ("commit", node.id))
            self._w("commit", t_out, node=node.id, reason="verified", p=pc)
            b = tr.belief()
            self._last_switch_map = b.map_id
            self._emit(pol.after_commit(t_out, b.map_id))

    def _localize(self, t: float, belief, frame_at) -> None:
        """Belief is spread over several steps: ask the fast verifier which of the top candidates is happening."""
        if self._busy(("localize",)):
            return self._skip(t, "localize")
        frames, times = span_keyframes(frame_at, t)
        if not frames:
            return
        cands = [k for k, p in belief.top(self.cfg.step_choice_k) if k != DONE and p > 0.02]
        extra = []
        if self.cfg.step_choice_local and self._ll_now is not None:
            ids = self.graph.ids
            extra += [ids[i] for i in np.argsort(-np.asarray(self._ll_now))[: self.cfg.step_choice_local]]
        if self.cfg.step_choice_next and belief.map_id != DONE:
            extra += [n for n in self.graph.node(belief.map_id).successors if n not in self.tracker.completed]
        cands += [k for k in extra if k not in cands and k not in self.tracker.completed]
        if len(cands) < 2:
            return
        opts = {k: f"{self.graph.node(k).name}: {self.graph.node(k).end_state}" for k in cands}
        top = self.graph.node(cands[0])
        screen = {m.id: f"{m.description} Looks like: {m.visual_cue}" for m in top.mistakes} if self.cfg.mistake_screen else None
        call = partial(_choose_step, self.loc or self.ver, frames, opts, self.graph.title, screen)
        ctx = {"cands": cands, "frames": frames, "times": times}
        if self.cfg.async_slow_path:
            return self._submit("localize", ("localize",), t, call, **ctx)
        self._localize_answer(t, call, frame_at=frame_at, **ctx)

    def _localize_answer(self, t: float, call, cands: list[str], frames: list, times: list, frame_at=None,
                         t_now: float | None = None, extra: dict | None = None) -> None:
        try:
            ans = call()
        except Exception as e:  # noqa: BLE001
            self._w("step_choice", t, error=str(e)[:200], **(extra or {}))
            return
        b = self._observe(t, ("choice", ans["probs"], self.cfg.step_choice_weight))
        self.n_escalated_frames += len(frames)
        self._w("step_choice", t, options=cands, probs=ans["probs"], choice=ans["choice"], latency_ms=ans["latency_ms"],
                model=ans["model"], cost_usd=ans["cost_usd"], mistake_screen=ans.get("mistake"), **(extra or {}))
        # a positive mistake screen goes through the full verify path (fast verifier + strong-tier escalation +
        # calibrated, precision-tuned policy) before the wearer hears anything; it looks at the same frames
        ms = ans.get("mistake")
        if ms and ms["choice"] != "none" and ms["p"] >= self.cfg.mistake_screen_p and b.map_id == cands[0]:
            self._verify(t, b, "mistake_screen", frame_at, update_tracker=self.cfg.screen_updates_tracker,
                         frames=frames, times=times)

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
        if self._busy(("order", j)):
            return self._skip(t, "order", j)
        frames, times = span_keyframes(frame_at, t)
        if not frames:
            return
        node = self.graph.node(j)
        req = VerifyRequest(t=t, frames=frames, node=node, graph=self.graph, checks=node.checks,
                            context={"frame_ages": [t - x for x in times]}, features=dict(self._feat_now))
        call = partial(self._order_call, req)
        if self.cfg.async_slow_path:
            return self._submit("order", ("order", j), t, call, j=j, missing=missing)
        self._order_answer(t, call(), j, missing)

    def _order_call(self, req: VerifyRequest) -> tuple[Verdict, float]:
        v = (self.esc or self.ver).verify(req)
        return v, self._calibrated(v, "escalation" if self.esc else "primary")[0]

    def _order_answer(self, t: float, res: tuple, j: str, missing: list[str], t_now: float | None = None,
                      extra: dict | None = None) -> None:
        v, pc = res
        self._log_verdict(t, v, "order_check", pc, extra)
        # 'in_progress' or 'deviation' on j with low P(complete) => j is underway now
        if not (v.error is None and v.visibility == "ok" and pc <= 0.5 and v.confidence >= self.cfg.order_conf):
            return
        t_out = t + v.latency_ms / 1000.0 if t_now is None else t_now
        if j in self._order_flagged or t_out - self.policy.last_card_t < self.policy.cfg.cooldown_s:
            return                      # async: flagged, or another card went out, while the call was out
        self._order_flagged.add(j)
        self.policy.last_card_t = t if t_now is None else t_now
        first, node = self.graph.node(missing[0]), self.graph.node(j)
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

    def _log_verdict(self, t: float, v: Verdict, reason: str, pc: float | None = None, extra: dict | None = None) -> dict:
        rec = {"node": v.node_id, "reason": reason, "status": v.step_status, "confidence": v.confidence,
               "mistake": v.mistake.model_dump() if v.mistake else None, "visibility": v.visibility,
               "view_request": v.view_request, "model": v.model, "role": v.role, "prompt_version": v.prompt_version,
               "latency_ms": v.latency_ms, "input_tokens": v.input_tokens, "output_tokens": v.output_tokens,
               "cost_usd": v.cost_usd, "orig_cost_usd": v.raw.get("orig_cost_usd", v.cost_usd),
               "cached": v.raw.get("cached", False), "error": v.error,
               "p_complete_cal": pc}
        self.calls.append({"t": t, **rec})
        self._w("verdict", t, **rec, **(extra or {}))
        return rec

    # ------------------------------------------------------------------ tracker updates from the slow path
    def _observe(self, t: float, op: tuple):
        """Apply a slow-path observation that belongs to tick t; returns the belief at t right after it. Inline, t is
        the current tick. Async, the answer is late: it goes in at tick t and the filter is re-run forward (_late)."""
        if not self.cfg.async_slow_path:
            self._apply(op)
            return self.tracker.belief()
        return self._late(t, op)

    def _apply(self, op: tuple) -> None:
        tr, k = self.tracker, op[0]
        if k == "predict":
            tr.predict()
        elif k == "local":
            tr.observe_local(op[1])
        elif k == "boundary":
            tr.observe_boundary(op[1])
        elif k == "commit":
            tr.mark_complete(op[1])
        elif k == "verdict":
            tr.observe_verdict(op[1], op[2], op[3])
        elif k == "choice":
            tr.observe_step_choice(op[1], weight=op[2])
        elif k == "away":
            tr.observe_away(op[1], op[2] if len(op) > 2 else None)

    def _late(self, t: float, op: tuple):
        """Async: an answer about tick t arrived after later ticks ran. Insert it at tick t and re-run the filter
        forward over the journaled inputs since then (fast-path evidence, commits, other late answers). The filter is
        predict-then-multiply, so this gives the state it would have reached had the answer come at once (with the
        commits that were made meanwhile). Returns the belief at tick t right after the answer."""
        tr = self.tracker
        i = next((k for k, e in enumerate(self._journal) if e["t"] == t), None)
        if i is None:                   # tick no longer journaled (should not happen): apply to the current state
            self._apply(op)
            return tr.belief()
        e = self._journal[i]
        e["late"].append(op)
        self._restore(e["snap"])
        for o in e["late"]:
            self._apply(o)
        b = tr.belief()
        for e2 in self._journal[i + 1:]:
            for o in e2["ops"]:
                self._apply(o)
            e2["snap"] = self._snapshot()
            for o in e2["late"]:
                self._apply(o)
        return b

    def _snapshot(self) -> tuple:
        return self.tracker.state()

    def _restore(self, s: tuple) -> None:
        self.tracker.set_state(s)

    def _prune(self) -> None:
        """Keep the journal back to the oldest call in flight that may still update the tracker."""
        keep = min((j.t for j in self._jobs if j.kind in ("verify", "localize") and j.task_id == self.task_id),
                   default=None)
        self._journal = [] if keep is None else [e for e in self._journal if e["t"] >= keep]

    # ------------------------------------------------------------------ async slow path (live mode)
    def poll(self, t: float) -> int:
        """Async mode: fold in every answer that has arrived, at media time t (praxis.live calls this after every
        frame; tick() calls it first). Returns how many answers were folded in."""
        done = sorted((j for j in self._jobs if j.fut.done()), key=lambda j: j.t)
        for j in done:
            self._jobs.remove(j)
            self._fold(j, t)
        if done:
            self._prune()
        return len(done)

    def close(self, t: float, timeout_s: float = 20.0) -> None:
        """Async mode: wait (at most timeout_s) for calls still out, fold in what came back, stop the workers."""
        if self._pool is None:
            return
        wait([j.fut for j in self._jobs], timeout=timeout_s)
        for j in sorted((j for j in self._jobs if j.fut.done()), key=lambda j: j.t):
            self._jobs.remove(j)
            self._fold(j, t, final=True)
        self.async_stats["unfinished_at_close"] += len(self._jobs)
        self._jobs = []
        self._pool.shutdown(wait=False, cancel_futures=True)
        self._pool = None

    def _submit(self, kind: str, key: tuple, t: float, call, **ctx) -> None:
        if self._pool is None:
            self._pool = ThreadPoolExecutor(self.cfg.async_workers, thread_name_prefix="praxis-slow")
        self._jobs.append(_Job(kind, key, t, self._pool.submit(_timed, call), ctx, task_id=self.task_id))
        self.async_stats[f"submitted_{kind}"] += 1

    def _busy(self, key: tuple) -> bool:
        return any(j.key == key for j in self._jobs)

    def _skip(self, t: float, kind: str, node: str | None = None) -> None:
        """Async: the same question is still out (e.g. an Opus escalation on this step); don't ask it twice."""
        self.async_stats[f"skipped_{kind}"] += 1
        self._w("slow_skip", t, what=kind, node=node)

    @staticmethod
    def _answer_of(j: _Job):
        res, err, _ = j.fut.result()

        def call():
            if err is not None:
                raise err
            return res
        return call

    @staticmethod
    def _landing(j: _Job, t_now: float) -> dict:
        """Logged with every async answer: when it was applied (media time), how long its calls took, and how many
        ticks the loop ran meanwhile."""
        return {"applied_t": round(float(t_now), 3), "call_s": round(j.fut.result()[2], 3), "ticks_during_call": j.ticks}

    def _fold(self, j: _Job, t_now: float, final: bool = False) -> None:
        self.async_stats[f"folded_{j.kind}"] += 1
        call, extra = self._answer_of(j), self._landing(j, t_now)
        if j.kind in ("verify", "localize", "order") and j.task_id != self.task_id:
            self.async_stats["dropped_task_not_active"] += 1          # about a task that was paused meanwhile
            return
        if j.kind == "task" and j.ctx.get("reason") and self.cfg.multi_task and self.graph is not None and not final:
            return self._recheck_answer(j.t, call, t_now=t_now, extra=extra, **j.ctx)
        if j.kind == "verify":
            self._verify_answer(j.t, call(), t_now=t_now, extra=extra, **j.ctx)
        elif j.kind == "localize":
            self._localize_answer(j.t, call, t_now=t_now, extra=extra, **j.ctx)
        elif j.kind == "order":
            self._order_answer(j.t, call(), t_now=t_now, extra=extra, **j.ctx)
        elif self.graph is None and not final:          # still looking for the task: same steps as the inline tick
            if j.kind == "task":
                r = self._gate(self._task_answer(j.t, self._last_r, call, **extra))
                self._w("recognizer", t_now, top=r.task_id, posterior=r.posterior, recognized=r.recognized,
                        open_set=r.open_set)
                if r.recognized:
                    self._start_recognized(t_now, r)
            else:
                self._draft_answer(j.t, call, t_now=t_now, **extra)
        else:       # a task check or draft that came back after a task started (or at the end): logged, not applied
            self.async_stats["ignored_late"] += 1
            kind = "task_check" if j.kind == "task" else "task_draft"
            extra["ignored"] = "session ended" if final and self.graph is None else "a task had already started"
            try:
                ans = call()
            except Exception as e:  # noqa: BLE001
                return self._w(kind, j.t, error=str(e)[:200], **extra)
            if j.kind == "task":
                self._w(kind, j.t, choice=ans["choice"], probs=ans["probs"], latency_ms=ans["latency_ms"],
                        model=ans["model"], cost_usd=ans["cost_usd"], **extra)
            else:
                g = ans[0]
                self._w(kind, j.t, task_id=g.task_id, title=g.title,
                        **{k: g.compiler.get(k) for k in ("model", "confidence", "cost_usd", "latency_s", "cached")}, **extra)


def task_short(g: TaskGraph) -> str:
    """'breakfast burritos', 'construction-toy car'."""
    import re
    title = re.sub(r"\s*\(.*?\)", "", g.title)
    title = re.sub(r"(?i)\bindustreal\b\s*", "", title).strip()
    title = re.sub(r"(?i)\s+assembly$", "", title)
    return title.lower()


def _lower_first(s: str) -> str:
    s = (s or "").strip().rstrip(".")           # callers end the sentence themselves
    return s[:1].lower() + s[1:] if s and not s[:2].isupper() else s


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
    engine.finish(end)                  # session end: paused tasks are closed as done enough (no user in replay)
    wall = time.perf_counter() - fps_t0
    return {"wall_s": wall, "n_frames": engine.n_frames, "escalated_frames": engine.n_escalated_frames}


def peaks_of(t, s, thr, gap):
    return peaks(np.asarray(t), np.asarray(s), thr, gap)

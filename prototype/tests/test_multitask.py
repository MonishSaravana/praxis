"""Multi-task engine (docs/MULTITASK.md): poor fit -> typed re-check -> switch / retract / resume with the paused
task's state intact; interruptions pause with one reminder + "Coming back to ...?" and resume on return; a paused task
closes only on "I'm done" or at session end, never on a timer."""
import numpy as np

from praxis.engine import Engine, EngineConfig
from praxis.policy.policy import PolicyConfig
from praxis.runlog import RunLog, read_log
from praxis.state_tracker import TrackerConfig
from praxis.tasks.schema import DurationPrior, Node, TaskGraph
from praxis.verify.schema import Verdict


def chain(tid, n=4, mean=60.0):
    nodes = [Node(id=f"{tid}{i}", name=f"Step {i} of {tid}", instruction_novice=f"do {i}", instruction_expert=f"Do {tid} {i}",
                  end_state="", successors=[f"{tid}{i + 1}"] if i < n - 1 else [],
                  duration=DurationPrior(mean_s=mean, std_s=20.0)) for i in range(n)]
    return TaskGraph(task_id=tid, title=f"Task {tid.upper()}", domain="cooking", source="unit", nodes=nodes,
                     start=[f"{tid}0"])


class FakeLM:
    """Landmarks stand-in: the test sets which task 'is in view'."""
    window_s = 5.0

    def __init__(self):
        self.view = "a"

    def update(self, fe): pass
    def add_task(self, tid, g): pass
    def scores(self): return {"a": 0.3 if self.view == "a" else 0.1, "b": 0.3 if self.view == "b" else 0.1}
    def features(self, tid): s = self.scores(); return np.array([s[tid] - max(v for k, v in s.items() if k != tid)] * 2)
    def top_tasks(self, n=3): return sorted(self.scores().items(), key=lambda kv: -kv[1])[:n]
    def non_task_top(self): return None, 0.0


class FakeOff:
    window_s, top_frac = 5.0, 0.2

    def p_off(self, f):
        return None if f is None else (0.05 if f[0] > 0 else 0.95)


class FakeVer:
    model = "fake"

    def __init__(self):
        self.task_answer = "a"
        self.task_calls = 0

    def verify(self, req):
        return Verdict(step_status="in_progress", confidence=0.6, node_id=req.node.id, model="fake", role="fast",
                       latency_ms=1.0)

    def choose_task(self, frames, opts):
        self.task_calls += 1
        probs = {k: (0.9 if k == self.task_answer else 0.1 / max(1, len(opts))) for k in opts}
        probs["none"] = 0.9 if self.task_answer == "none" else 0.01
        return {"probs": probs, "choice": self.task_answer, "latency_ms": 100.0, "model": "fake", "cost_usd": 0.0001}


def make(tmp_path, name="mt"):
    lib = {"a": chain("a"), "b": chain("b")}
    cfg = EngineConfig(multi_task=True, step_choice=False, order_check=False, recognize=False,
                       policy=PolicyConfig(entropy_verify=1.01, hesitation_ratio=1e9),
                       tracker=TrackerConfig(away_enter=0.02, away_return=0.1, away_weight=1.0),
                       fit_window_s=10.0, fit_thr=0.6, recheck_min_gap_s=10.0, leave_after_s=8.0)
    ver = FakeVer()
    eng = Engine(cfg, lib, {}, None, None, ver, log=RunLog(tmp_path / f"{name}.jsonl"), offtask=FakeOff())
    eng.lm = FakeLM()
    eng._start_task(0.0, "a")
    return eng, ver


def rows(t):
    return {"t": t - np.array([0.75, 0.5, 0.25, 0.0]), "frame": np.zeros((4, 8)), "window": np.zeros((4, 8)),
            "hands": np.zeros((4, 12)), "boundary": np.zeros(4), "grasp": np.zeros(4)}


def frame_at(x):
    return np.zeros((48, 64, 3), np.uint8)


def run(eng, t0, t1):
    for t in range(t0, t1):
        eng.tick(float(t), rows(t), frame_at)


def recs(eng, kind):
    eng.log.flush()
    return [r for r in read_log(eng.log.tmp_path) if r["kind"] == kind]


def test_wrong_first_guess_is_retracted_and_replaced(tmp_path):
    eng, ver = make(tmp_path)
    run(eng, 1, 10)
    assert eng.task_id == "a" and eng.tracker.belief().p_away < 0.5
    eng.lm.view, ver.task_answer = "b", "b"            # it was task b all along
    run(eng, 10, 60)
    assert eng.task_id == "b"
    st = recs(eng, "task_state")
    assert st[0]["task_id"] == "a" and st[0]["to"] == "retracted" and st[0]["reason"] == "wrong_guess"
    acts = [r["action"] for r in recs(eng, "action")]
    assert "retract_task" in acts and "leave_warning" not in acts
    assert any(r["reason"] == "poor_fit" and r["decision"] == "switch" for r in recs(eng, "task_check"))


def test_switch_pauses_with_state_and_resume_restores_it(tmp_path):
    eng, ver = make(tmp_path)
    run(eng, 1, 5)
    eng.tracker.mark_complete("a0")                    # one step of a done
    tr_a = eng.tracker
    run(eng, 5, 10)
    eng.lm.view, ver.task_answer = "b", "b"
    run(eng, 10, 60)
    assert eng.task_id == "b" and eng.tasks["a"].status == "paused"
    sw = [r for r in recs(eng, "action") if r["action"] == "switch_task"]
    assert len(sw) == 1 and sw[0]["text"] == ("Looks like you've moved on to making task b. I paused the task a at: do a 1. "
                                         "Coming back to the task a?")
    eng.lm.view, ver.task_answer = "a", "a"            # back to a
    run(eng, 60, 120)
    assert eng.task_id == "a" and eng.tracker is tr_a and eng.tracker.completed == {"a0"}
    res = [r for r in recs(eng, "action") if r["action"] == "resume_task"]
    assert res and res[-1]["text"] == "Back to the task a. Next: do a 1."
    assert eng.tasks["b"].status == "paused"           # nothing of b done, but it fit while it was current: a real task


def test_interruption_pauses_once_reminds_once_and_resumes(tmp_path):
    eng, ver = make(tmp_path)
    run(eng, 1, 5)
    eng.tracker.mark_complete("a0")
    eng.lm.view, ver.task_answer = "none", "none"     # baby: neither task in view, the check says none
    eng.lm.scores = lambda: {"a": 0.1, "b": 0.3}      # landmarks fit a worse than b, but the check never names b
    run(eng, 5, 40)
    st = recs(eng, "task_state")
    assert [s["reason"] for s in st] == ["interruption"] and eng.task_id == "a"
    lw = [r for r in recs(eng, "action") if r["action"] == "leave_warning"]
    assert len(lw) == 1 and lw[0]["text"] == ("Before you go, 3 steps are left on the task a. Next: do a 1. "
                                              "Coming back to the task a?")
    ask = recs(eng, "ask_resume")
    assert len(ask) == 1 and ask[0]["open_steps"] == ["a1", "a2", "a3"]
    assert all(r["decision"] == "none" for r in recs(eng, "task_check"))
    del eng.lm.scores
    eng.lm.view = "a"
    run(eng, 40, 70)
    st = recs(eng, "task_state")
    assert st[-1]["to"] == "active" and st[-1]["reason"] == "resumed"
    assert recs(eng, "action")[-1]["action"] == "resume_task"


def test_confirmed_task_backs_off_and_paused_task_never_times_out(tmp_path):
    eng, ver = make(tmp_path)
    eng.tracker.cfg.away_weight = 0.2
    eng.lm.scores = lambda: {"a": 0.1, "b": 0.3}      # poor landmark fit, but the check keeps confirming a
    run(eng, 1, 80)
    keeps = [r for r in recs(eng, "task_check") if r["decision"] == "keep"]
    assert len(keeps) >= 2 and keeps[1]["t"] - keeps[0]["t"] >= 30 and eng.task_id == "a"
    del eng.lm.scores
    eng.tracker.mark_complete("a0")
    eng.lm.view, ver.task_answer = "b", "b"
    run(eng, 80, 1500)                                 # 23 minutes: no timer closes the paused task
    assert eng.task_id == "b" and eng.tasks["a"].status == "paused"
    sw = [r for r in recs(eng, "action") if r["action"] == "switch_task"][0]
    assert sw["text"].endswith("Coming back to the task a?") and sw["detail"]["ask_resume"] == "a"
    eng.finish(1500.0)                                 # session end
    st = [r for r in recs(eng, "task_state") if r["task_id"] == "a"][-1]
    assert st["to"] == "done_enough" and st["reason"] == "session_end" and st["open_steps"] == ["a1", "a2", "a3"]


def test_im_done_closes_a_paused_task_and_coming_back_keeps_it(tmp_path):
    eng, ver = make(tmp_path, "answers")
    run(eng, 1, 5)
    eng.tracker.mark_complete("a0")
    eng.lm.view, ver.task_answer = "none", "none"
    eng.lm.scores = lambda: {"a": 0.1, "b": 0.3}
    run(eng, 5, 40)
    assert eng.slot.interrupted
    eng.answer_resume(40.0, "a", "coming_back")
    assert eng.task_id == "a" and eng.tasks["a"].status == "paused" and eng.tasks["a"].answer == "coming_back"
    eng.answer_resume(41.0, "a", "done", via="typed")
    assert eng.task_id is None and eng.tasks["a"].status == "done_enough"
    st = recs(eng, "task_state")[-1]
    assert st["reason"] == "user_done" and st["open_steps"] == ["a1", "a2", "a3"]
    assert [r["answer"] for r in recs(eng, "resume_answer")] == ["coming_back", "done"]


def test_switch_needs_more_confidence_after_more_steps(tmp_path):
    eng, ver = make(tmp_path)
    eng.cfg.switch_p, eng.cfg.switch_per_step = 0.6, 0.2
    eng.cfg.switch_max_p, eng.cfg.switch_streak_override = 1.0, 0      # the per-step bar alone
    for n in ("a0", "a1"):
        eng.tracker.mark_complete(n)                   # need = 0.6 + 2 * 0.2 = 1.0 > 0.9
    eng.lm.view, ver.task_answer = "b", "b"
    run(eng, 1, 60)
    assert eng.task_id == "a"
    assert any(r["decision"] == "hold_confidence" for r in recs(eng, "task_check"))


def test_async_recheck_switches_when_the_answer_arrives(tmp_path):
    eng, ver = make(tmp_path, "async")
    eng.cfg.async_slow_path = True
    run(eng, 1, 10)
    eng.lm.view, ver.task_answer = "b", "b"
    for t in range(10, 60):
        eng.tick(float(t), rows(t), frame_at)
        for j in list(eng._jobs):
            j.fut.result(timeout=10)
    eng.close(60.0)
    assert eng.task_id == "b"
    chk = [r for r in recs(eng, "task_check") if r.get("decision") == "switch"]
    assert chk and "applied_t" in chk[0]


def test_task_given_never_switches_and_interruption_needs_the_check(tmp_path):
    eng, ver = make(tmp_path, "given")
    eng.cfg.switching = False
    eng.lm.view, ver.task_answer = "b", "b"            # landmarks and the check both say b, but the task was given
    run(eng, 1, 60)
    assert eng.task_id == "a" and not eng.slot.interrupted
    assert any(r["decision"] == "hold_task_given" for r in recs(eng, "task_check"))
    ver.task_answer = "none"                           # now the check says nothing task-related is happening
    run(eng, 60, 100)
    assert eng.slot.interrupted and eng.tracker.frozen
    st = [r for r in recs(eng, "task_state") if r["reason"] == "interruption"]
    assert st and st[0]["evidence"]["confirmed_by"] == "task_check"


def test_studio_typed_answers_go_to_the_latest_open_question():
    from types import SimpleNamespace
    from praxis.studio.session import StudioSession
    a = SimpleNamespace(task_id="a", status="paused", asked_at=10.0, answer=None)
    b = SimpleNamespace(task_id="b", status="paused", asked_at=50.0, answer=None)
    fake = SimpleNamespace(eng=SimpleNamespace(tasks={"a": a, "b": b}))
    ask = lambda text: StudioSession._typed_answer(fake, text)   # noqa: E731
    assert ask("I'm done") == ("b", "done")
    assert ask("coming back later") == ("b", "coming_back")
    assert ask("making cucumber raita") is None                  # a task description, not an answer
    b.answer = "coming_back"
    assert ask("done with it") == ("a", "done")


def test_resume_bias_prefers_the_paused_task():
    from praxis.engine import TaskSlot  # noqa: F401
    import tempfile, pathlib
    eng, ver = make(pathlib.Path(tempfile.mkdtemp()), "bias")
    eng.cfg.resume_bias = float(np.log(4))
    run(eng, 1, 5)
    eng.tracker.mark_complete("a0")
    eng.lm.view, ver.task_answer = "b", "b"
    run(eng, 5, 60)
    assert eng.task_id == "b" and eng.tasks["a"].status == "paused"
    # back at a, but the check prefers a third library task: a 0.3 vs c 0.6 -> with the bias a wins
    eng.lib = {**eng.lib, "c": chain("c")}
    ver.choose_task = lambda frames, opts: {"probs": {"a": 0.3, "b": 0.05, "c": 0.6, "none": 0.05}, "choice": "c",
                                            "latency_ms": 1.0, "model": "fake", "cost_usd": 0.0}
    eng.lm.view = "a"
    run(eng, 60, 120)
    assert eng.task_id == "a"


def test_rewind_on_leave_undoes_progress_made_on_the_other_task(tmp_path):
    eng, ver = make(tmp_path, "rewind")
    eng.cfg.rewind_on_leave, eng.cfg.rewind_lag_s = True, 1.0     # the fake landmarks react at once
    run(eng, 1, 10)
    eng.tracker.mark_complete("a0")
    eng.lm.view, ver.task_answer = "b", "b"
    run(eng, 10, 13)
    eng.tracker.mark_complete("a1")                    # "progress" made while actually doing b
    run(eng, 13, 60)
    assert eng.task_id == "b" and eng.tasks["a"].tracker.completed == {"a0"}
    rw = recs(eng, "rewind")
    assert rw and rw[0]["undone"] == ["a1"]


def test_a_task_with_many_steps_done_can_still_be_left():
    import tempfile, pathlib
    eng, ver = make(pathlib.Path(tempfile.mkdtemp()), "cap")
    eng.cfg.switch_p, eng.cfg.switch_per_step, eng.cfg.switch_streak_override = 0.8, 0.05, 0
    for n in ("a0", "a1", "a2"):
        eng.tracker.mark_complete(n)                   # uncapped: 0.8 + 3 x 0.05 = 0.95 > the check's 0.9
    eng.lm.view, ver.task_answer = "b", "b"
    run(eng, 1, 60)
    assert eng.task_id == "b"                          # capped at switch_max_p 0.9


def test_repeated_strong_answers_override_the_per_step_bar():
    import tempfile, pathlib
    eng, ver = make(pathlib.Path(tempfile.mkdtemp()), "streak")
    eng.cfg.switch_p, eng.cfg.switch_per_step, eng.cfg.switch_max_p = 0.8, 0.2, 0.99
    for n in ("a0", "a1"):
        eng.tracker.mark_complete(n)                   # need = 0.99 > 0.9
    eng.lm.view, ver.task_answer = "b", "b"
    run(eng, 1, 100)
    assert eng.task_id == "b"
    dec = [r["decision"] for r in recs(eng, "task_check")]
    assert dec[:2] == ["hold_confidence", "switch"]


def test_recognition_gate_min_time_and_agreeing_answers(tmp_path):
    from praxis.tasks.recognizer import Recognition
    eng, ver = make(tmp_path, "gate")
    r = Recognition(t=4.0, task_id="b", posterior={"a": 0.05, "b": 0.95}, recognized=True)
    eng._last_task_probs, eng._last_choice, eng._choice_streak = {"b": 0.9}, "b", 1
    assert eng._gate(r).recognized                                   # defaults: unchanged behavior
    eng.cfg.recognize_agree, eng.cfg.recognize_min_s = 2, 10.0
    assert not eng._gate(r).recognized                               # one answer, and before 10 s
    eng._choice_streak = 2
    assert not eng._gate(r).recognized                               # two answers, still before 10 s
    r.t = 10.0
    assert eng._gate(r).recognized
    eng._last_choice = "a"
    assert not eng._gate(r).recognized                               # the answers named another task

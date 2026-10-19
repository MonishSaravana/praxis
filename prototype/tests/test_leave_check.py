"""Leave checks (EngineConfig.leave_check): a completion check on the step the belief is leaving, so steps get
verified without the L2 event detector (which never fires on workbench repair)."""
import numpy as np

from praxis.engine import Engine, EngineConfig
from praxis.policy.policy import PolicyConfig
from praxis.runlog import RunLog, read_log
from praxis.verify.schema import Verdict

from test_async_slow_path import Gated, chain, frame_at, rows


class Broken(Gated):
    def verify(self, req):
        self.calls += 1
        return Verdict(step_status="in_progress", confidence=0.0, node_id=req.node.id, model="fake", role="fast",
                       latency_ms=1.0, error="network")


def engine(tmp_path, name, ver, async_=False, **kw):
    cfg = EngineConfig(step_choice=False, order_check=False, async_slow_path=async_,
                       policy=PolicyConfig(entropy_verify=1.01, hesitation_ratio=1e9), **kw)   # no other triggers
    return Engine(cfg, {"t": chain()}, {}, None, None, ver, log=RunLog(tmp_path / f"{name}.jsonl"), task_id="t")


def move(E, node, p=1.0):
    """Put the belief on `node` (p of the mass; the rest stays where it was)."""
    tr = E.tracker
    a = tr.alpha * (1 - p)
    a[tr.idx[node], 0] += p
    tr.alpha = a / a.sum()


def run(E, at=4, node="s1", p=1.0, ticks=8):
    for t in range(1, ticks + 1):
        if t == at:
            move(E, node, p)
        E.tick(float(t), rows(t), frame_at)
    E.log.close()
    return read_log(E.log.path)


def kinds(rs, k):
    return [r for r in rs if r["kind"] == k]


def test_off_by_default_asks_nothing(tmp_path):
    ver = Gated("complete", 0.95, open_=True)
    rs = run(engine(tmp_path, "off", ver))
    assert ver.calls == 0 and [c["reason"] for c in kinds(rs, "commit")] == ["belief_switch"]


def test_commit_mode_verifies_the_step_left(tmp_path):
    ver = Gated("complete", 0.95, open_=True)
    E = engine(tmp_path, "commit", ver, leave_check="commit")
    rs = run(E)
    v = kinds(rs, "verdict")
    assert [(x["t"], x["node"], x["reason"]) for x in v] == [(4.0, "s0", "leave")]
    assert ("verified", "s0") in [(a["action"], a["node"]) for a in kinds(rs, "action")]
    assert E.tracker.completed == {"s0"}


def test_commit_mode_without_gate_commits_even_if_not_done(tmp_path):
    E = engine(tmp_path, "nogate", Gated("in_progress", 0.9, open_=True), leave_check="commit")
    rs = run(E)
    assert E.tracker.completed == {"s0"} and "verified" not in [a["action"] for a in kinds(rs, "action")]


def test_gate_holds_the_commit_when_the_check_says_not_done(tmp_path):
    E = engine(tmp_path, "held", Gated("in_progress", 0.9, open_=True), leave_check="commit", leave_gate=True)
    rs = run(E)
    assert "s0" not in E.tracker.completed
    assert [h["node"] for h in kinds(rs, "commit_held")] == ["s0"] and not kinds(rs, "commit")
    assert [(v["node"], v["status"]) for v in kinds(rs, "verdict")] == [("s0", "in_progress")]


def test_gate_commits_on_a_done_answer(tmp_path):
    E = engine(tmp_path, "gated", Gated("complete", 0.95, open_=True), leave_check="commit", leave_gate=True)
    rs = run(E)
    c = kinds(rs, "commit")
    assert E.tracker.completed == {"s0"} and len(c) == 1 and c[0]["checked"] and c[0]["reason"] == "verified"
    acts = [(a["action"], a["node"]) for a in kinds(rs, "action")]
    assert ("verified", "s0") in acts and ("instruct", "s1") in acts


def test_gate_falls_back_to_the_commit_when_the_check_fails(tmp_path):
    E = engine(tmp_path, "broken", Broken(), leave_check="commit", leave_gate=True)
    rs = run(E)
    assert E.tracker.completed == {"s0"} and kinds(rs, "commit")[0]["reason"] == "belief_switch"


def test_any_mode_checks_an_unconfident_leave_and_commits_only_if_verified(tmp_path):
    for status, done in (("complete", True), ("in_progress", False)):
        ver = Gated(status, 0.95, open_=True)
        E = engine(tmp_path, f"any_{status}", ver, leave_check="any", leave_gate=True, commit_on_switch_p=0.99)
        rs = run(E, at=7, p=0.9, ticks=10)            # MAP moves to s1 (held s0 >= 5 s) but below the commit bar
        assert [(v["node"], v["reason"]) for v in kinds(rs, "verdict")] == [("s0", "leave")]
        assert ("s0" in E.tracker.completed) == done


def test_one_leave_check_per_step_per_window(tmp_path):
    ver = Gated("in_progress", 0.9, open_=True)
    E = engine(tmp_path, "window", ver, leave_check="commit", leave_gate=True)
    for t in range(1, 13):
        if t in (4, 8):                               # leaves s0 twice within leave_recheck_s
            move(E, "s1")
        E.tick(float(t), rows(t), frame_at)
    E.log.close()
    rs = read_log(E.log.path)
    assert ver.calls == 1 and "s0" not in E.tracker.completed       # the second leave stays held, no second call


def test_async_gate_commits_when_the_answer_arrives(tmp_path):
    ver = Gated("complete", 0.95)
    E = engine(tmp_path, "async", ver, async_=True, leave_check="commit", leave_gate=True)
    for t in range(1, 9):
        if t == 4:
            move(E, "s1")
        E.tick(float(t), rows(t), frame_at)
        if t == 5:
            assert not E.tracker.completed            # held while the call is out
            ver.go.set()
            for j in E._jobs:
                j.fut.result(timeout=10)
            assert E.poll(5.5) == 1
    E.log.close()
    rs = read_log(E.log.path)
    c = kinds(rs, "commit")
    assert E.tracker.completed == {"s0"} and [x["t"] for x in c] == [5.5] and c[0]["checked"]
    assert np.isclose(E.tracker.alpha.sum(), 1.0)


def test_jev_step_question_served_from_cache_without_budget(monkeypatch):
    """A cached "which step?" answer needs no budget (dry runs with a zero budget reproduce cached runs) and isn't
    billed again."""
    from praxis.verify import jev
    from praxis.verify.common import Budget, BudgetExceeded
    step = {"answers": {"step": {"choice": "s0", "probabilities": {"s0": 0.9, "none": 0.1}}},
            "usage": {"input_tokens": 1000}, "model": "jev-1.14.0"}

    class Client:
        def __init__(self, model):
            self.calls = 0

        def system_one(self, state, q, assets=None, images=False):
            self.calls += 1
            return step, 10.0

    class Cache:
        def __init__(self):
            self.d = {}

        def get(self, k):
            return self.d.get(k)

        def put(self, k, v):
            self.d[k] = v
    monkeypatch.setattr(jev, "JevClient", Client)
    frames = [np.full((48, 64, 3), 7, np.uint8)]
    live = jev.JevVerifier(Budget(10, 1.0), use_cache=False)
    live.cache = Cache()
    live.choose_step(frames, {"s0": "step 0"}, "t")
    assert live.budget.calls == 1 and live.budget.usd > 0
    dry = jev.JevVerifier(Budget(0, 0.0), use_cache=False)
    dry.cache = live.cache
    assert dry.choose_step(frames, {"s0": "step 0"}, "t")["choice"] == "s0"
    assert dry.budget.calls == 0 and dry.budget.usd == 0.0 and dry.client.calls == 0
    try:
        dry.choose_step(frames, {"s0": "step 0", "s1": "step 1"}, "t")     # not cached: a real call, over budget
        raise AssertionError("expected BudgetExceeded")
    except BudgetExceeded:
        pass

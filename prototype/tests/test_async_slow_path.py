"""Async slow path (live mode): the loop never waits on a model call, and a late answer, applied at the tick its
frames were taken, leaves the tracker exactly where the inline path leaves it."""
import threading
import time

import numpy as np

from praxis.engine import Engine, EngineConfig
from praxis.policy.policy import PolicyConfig
from praxis.runlog import RunLog, read_log
from praxis.tasks.schema import DurationPrior, Node, TaskGraph
from praxis.verify.schema import Verdict


def chain(n=4, mean=60.0):
    nodes = [Node(id=f"s{i}", name=f"step {i}", instruction_novice=f"do {i}", instruction_expert=f"{i}", end_state="",
                  successors=[f"s{i + 1}"] if i < n - 1 else [], duration=DurationPrior(mean_s=mean, std_s=20.0))
             for i in range(n)]
    return TaskGraph(task_id="t", title="t", domain="test", source="unit", nodes=nodes, start=["s0"])


class Gated:
    """Fake verifier: answers once `go` is set (the inline engine gets it pre-set)."""
    model = "fake"

    def __init__(self, status="in_progress", conf=0.8, open_=False):
        self.go, self.status, self.conf, self.calls = threading.Event(), status, conf, 0
        if open_:
            self.go.set()

    def verify(self, req):
        self.calls += 1
        self.go.wait(10)
        return Verdict(step_status=self.status, confidence=self.conf, node_id=req.node.id, model="fake", role="fast",
                       latency_ms=1.0)


def engine(tmp_path, name, ver, async_):
    g = chain()
    cfg = EngineConfig(step_choice=False, order_check=False, async_slow_path=async_,
                       policy=PolicyConfig(entropy_verify=1.01, hesitation_ratio=1e9))   # verify only at boundary peaks
    return Engine(cfg, {"t": g}, {}, None, None, ver, log=RunLog(tmp_path / f"{name}.jsonl"), task_id="t")


def rows(t, peak=False):
    b = np.array([0.0, 0.0, 0.9, 0.1]) if peak else np.zeros(4)
    return {"t": t - np.array([0.75, 0.5, 0.25, 0.0]), "frame": np.zeros((4, 8)), "window": np.zeros((4, 8)),
            "hands": np.zeros((4, 12)), "boundary": b, "grasp": np.zeros(4)}


def frame_at(x):
    return np.zeros((48, 64, 3), np.uint8)


def run_pair(tmp_path, status, conf, peaks=(3,)):
    """Same inputs to an inline and an async engine; the async answer is released after tick 6, folded in at 6.5."""
    a, b = Gated(status, conf, open_=True), Gated(status, conf)
    A, B = engine(tmp_path, "inline", a, False), engine(tmp_path, "async", b, True)
    for t in range(1, 9):
        A.tick(float(t), rows(t, t in peaks), frame_at)
        k0 = time.perf_counter()
        B.tick(float(t), rows(t, t in peaks), frame_at)
        assert time.perf_counter() - k0 < 2.0, "the async tick waited on the model call"
        if t == 6:
            b.go.set()
            for j in B._jobs:
                j.fut.result(timeout=10)
            assert B.poll(6.5) == 1
    A.log.close()
    B.log.close()
    return A, B, read_log(A.log.path), read_log(B.log.path)


def test_late_answer_matches_inline_filter(tmp_path):
    A, B, ra, rb = run_pair(tmp_path, "in_progress", 0.8)
    assert np.array_equal(A.tracker.alpha, B.tracker.alpha)
    v = [r for r in rb if r["kind"] == "verdict"]
    assert len(v) == 1 and v[0]["t"] == 3.0 and v[0]["applied_t"] == 6.5 and v[0]["ticks_during_call"] == 3
    # beliefs logged after the fold agree with the inline engine's
    bel = lambda rs: {r["t"]: r["p"] for r in rs if r["kind"] == "belief"}   # noqa: E731
    assert bel(ra)[7.0] == bel(rb)[7.0] and bel(ra)[8.0] == bel(rb)[8.0]
    assert bel(ra)[4.0] != bel(rb)[4.0]          # ... and before it the async engine had not seen the answer yet


def test_late_completion_commits_retroactively_and_speaks_on_arrival(tmp_path):
    A, B, ra, rb = run_pair(tmp_path, "complete", 0.95)
    assert A.tracker.completed == B.tracker.completed == {"s0"}
    assert np.array_equal(A.tracker.alpha, B.tracker.alpha)
    acts = [(r["t"], r["action"], r["node"]) for r in rb if r["kind"] == "action"]
    assert (6.5, "verified", "s0") in acts and (6.5, "instruct", "s1") in acts
    assert [r["t"] for r in rb if r["kind"] == "commit"] == [6.5]


class GatedTask(Gated):
    def choose_task(self, frames, options):
        self.calls += 1
        self.go.wait(10)
        return {"probs": {"t": 0.9, "none": 0.1}, "choice": "t", "latency_ms": 1.0, "model": "fake", "cost_usd": 0.0}


def test_task_check_answer_is_folded_in_when_it_arrives(tmp_path):
    from praxis.tasks.recognizer import TaskRecognizer
    starts = {}
    for name, async_ in (("inline", False), ("async", True)):
        ver = GatedTask(open_=not async_)
        cfg = EngineConfig(step_choice=False, order_check=False, async_slow_path=async_)
        rec = TaskRecognizer(task_ids=["t"], text_emb=np.ones((1, 8)))
        E = Engine(cfg, {"t": chain()}, {}, rec, None, ver, log=RunLog(tmp_path / f"task_{name}.jsonl"))
        for t in range(1, 7):
            E.tick(float(t), rows(t), frame_at)
            if async_ and t == 4:                  # the check went out at 4 s; its answer lands at 4.3 s
                assert E.graph is None
                ver.go.set()
                E._jobs[0].fut.result(timeout=10)
                assert E.poll(4.3) == 1
        E.log.close()
        starts[name] = [r["t"] for r in read_log(E.log.path) if r["kind"] == "task"]
    assert starts == {"inline": [4.0], "async": [4.3]}


def test_same_check_is_not_asked_twice_while_out(tmp_path):
    b = Gated()
    B = engine(tmp_path, "dedup", b, True)
    for t in range(1, 8):
        B.tick(float(t), rows(t, t in (3, 6)), frame_at)    # second boundary peak while the first call is still out
    b.go.set()
    B.close(8.0)
    B.log.close()
    recs = read_log(B.log.path)
    assert b.calls == 1 and B.async_stats["skipped_verify"] == 1
    assert [(r["t"], r["what"], r["node"]) for r in recs if r["kind"] == "slow_skip"] == [(6.0, "verify", "s0")]
    assert len([r for r in recs if r["kind"] == "verdict"]) == 1

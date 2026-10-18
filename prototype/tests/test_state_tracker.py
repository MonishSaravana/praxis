import numpy as np

from praxis.state_tracker import DONE, StateTracker, TrackerConfig
from praxis.tasks.schema import DurationPrior, Node, TaskGraph


def chain(n=4, mean=10.0):
    nodes = []
    for i in range(n):
        nodes.append(Node(id=f"s{i}", name=f"step {i}", instruction_novice="", instruction_expert="",
                          end_state="", successors=[f"s{i+1}"] if i < n - 1 else [],
                          duration=DurationPrior(mean_s=mean, std_s=3.0)))
    return TaskGraph(task_id="t", title="t", domain="test", source="unit", nodes=nodes, start=["s0"])


def test_duration_prior_moves_belief_forward():
    tr = StateTracker(chain())
    for _ in range(12):
        tr.predict()
    b = tr.belief()
    assert b.p[tr.idx["s0"]] < 0.6 and b.p[tr.idx["s1"]] > 0.3


def test_local_evidence_and_verdict():
    g = chain()
    tr = StateTracker(g)
    ll = np.array([0.0, 2.0, 0.0, 0.0])
    for _ in range(5):
        tr.predict()
        tr.observe_local(ll)
    assert tr.belief().map_id == "s1"
    tr.observe_verdict("s1", "complete", 0.9)
    tr.mark_complete("s0")
    tr.mark_complete("s1")
    assert tr.belief().map_id == "s2"


def test_completed_steps_get_no_mass_and_done_absorbs():
    tr = StateTracker(chain(2))
    for n in ("s0", "s1"):
        tr.mark_complete(n)
    assert tr.belief().map_id == DONE


def test_join_mid_task_localizes():
    tr = StateTracker(chain(5), join_mid_task=True)
    ll = np.array([0, 0, 0, 3.0, 0])
    for _ in range(3):
        tr.predict()
        tr.observe_local(ll)
    b = tr.belief()
    assert b.map_id == "s3"
    tr.assume_done_before("s3")
    assert set(tr.completed) == {"s0", "s1", "s2"}


# ---------------------------------------------------------------- away states (multi-task)
def test_away_off_is_the_single_task_tracker():
    g = chain()
    a, b = StateTracker(g), StateTracker(g, TrackerConfig(away_enter=0.0))
    ll = np.array([0.0, 1.0, 0.0, 0.0])
    for _ in range(20):
        for tr in (a, b):
            tr.predict()
            tr.observe_local(ll)
            tr.observe_boundary(0.3)
            tr.observe_away(0.9)            # no-op without away states
    assert np.array_equal(a.alpha, b.alpha) and not b.away.any() and b.belief().p_away == 0.0


def test_off_task_evidence_moves_mass_away_and_freezes_the_step():
    tr = StateTracker(chain(mean=20.0), TrackerConfig(away_enter=0.02, away_return=0.1))
    for _ in range(6):
        tr.predict()
    pos = tr.belief().p.copy()
    for _ in range(40):                     # 40 s of "not this task"
        tr.predict()
        tr.observe_away(0.95)
    b = tr.belief()
    assert b.p_away > 0.9
    assert abs(b.p[tr.idx["s0"]] - pos[tr.idx["s0"]]) < 0.15     # where you are barely moves while away
    for _ in range(15):                     # back on task
        tr.predict()
        tr.observe_away(0.05)
    assert tr.belief().p_away < 0.2


def test_step_evidence_leaves_the_away_share_alone():
    tr = StateTracker(chain(), TrackerConfig(away_enter=0.05))
    for _ in range(5):
        tr.predict()
    before = tr.belief().p_away
    tr.observe_local(np.array([0.0, 3.0, 0.0, 0.0]))
    tr.observe_verdict("s0", "in_progress", 0.8)
    assert abs(tr.belief().p_away - before) < 1e-9


def test_none_answer_counts_for_away_and_state_roundtrips():
    tr = StateTracker(chain(), TrackerConfig(away_enter=0.05))
    for _ in range(5):
        tr.predict()
    s = tr.state()
    p0 = tr.belief().p_away
    tr.observe_step_choice({"s0": 0.05, "s1": 0.05, "none": 0.9})
    assert tr.belief().p_away > p0
    tr.mark_complete("s0")
    assert tr.away[tr.idx["s0"]].sum() == 0.0 and abs(tr.alpha.sum() + tr.away.sum() - 1) < 1e-9
    tr.set_state(s)
    assert abs(tr.belief().p_away - p0) < 1e-12 and tr.completed == set()


def test_factored_away_freezes_steps_and_reads_out():
    cfg = TrackerConfig(away_enter=0.02, away_return=0.1, away_mode="factored")
    tr = StateTracker(chain(mean=20.0), cfg)
    for _ in range(6):
        tr.predict()
    pos = tr.belief().p.copy()
    for _ in range(40):
        tr.predict()
        tr.observe_away(0.95)
    b = tr.belief()
    assert b.p_away > 0.9 and abs(b.p[tr.idx["s0"]] - pos[tr.idx["s0"]]) < 0.15
    tr.observe_step_choice({"s0": 0.05, "s1": 0.05, "none": 0.9})
    assert tr.belief().p_away > 0.9
    s = tr.state()
    for _ in range(15):
        tr.predict()
        tr.observe_away(0.05)
    assert tr.belief().p_away < 0.2
    tr.set_state(s)
    assert tr.belief().p_away > 0.9


def test_decoupled_away_leaves_steps_alone_until_frozen():
    g = chain(mean=20.0)
    a, b = StateTracker(g), StateTracker(g, TrackerConfig(away_enter=0.02, away_return=0.1, away_mode="decoupled"))
    ll = np.array([0.0, 1.0, 0.0, 0.0])
    for _ in range(10):
        for tr in (a, b):
            tr.predict()
            tr.observe_local(ll)
        b.observe_away(0.9)
    assert np.allclose(a.alpha, b.alpha) and b.belief().p_away > 0.5
    b.frozen = True
    before = b.alpha.copy()
    for _ in range(30):
        b.predict()
        b.observe_local(ll)
    assert np.array_equal(before, b.alpha)

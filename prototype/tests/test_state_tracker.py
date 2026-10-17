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

"""Jev completion checks are cached by content: two verify() calls on the same frames and node look up the same
response-cache key, although each request names its images with fresh random refs. No network: the client is a fake."""
import numpy as np

from praxis.tasks.schema import Mistake, Node, TaskGraph
from praxis.verify import jev
from praxis.verify.common import Budget
from praxis.verify.schema import VerifyRequest

ANSWER = {"answers": {"step_complete": {"noul": 0.9}, "view_ok": {"noul": 0.8},
                      "mistake": {"choice": "none", "probabilities": {"none": 0.95, "shell": 0.05}}},
          "usage": {"input_tokens": 2000, "output_tokens": 0}, "model": "jev-1.14.0"}


class FakeClient:
    """Stands in for JevClient: records each request, answers without the network."""

    def __init__(self, model):
        self.model, self.sent = model, []

    def system_one(self, state, questions, assets=None, images=False):
        self.sent.append((state, assets))
        return ANSWER, 12.0


class Cache:
    """In-memory ResponseCache that records every key looked up; hits=False makes every lookup miss."""

    def __init__(self, hits=True):
        self.hits, self.store, self.asked = hits, {}, []

    def get(self, key):
        self.asked.append(key)
        return self.store.get(key) if self.hits else None

    def put(self, key, value):
        self.store[key] = value


def verifier(monkeypatch, cache):
    monkeypatch.setattr(jev, "JevClient", FakeClient)
    v = jev.JevVerifier(Budget(10, 1.0), use_cache=False)      # no cache dir on disk; the fake records keys
    v.cache = cache
    return v


def request(step="crack the eggs"):
    rng = np.random.default_rng(0)
    node = Node(id="s1", name=step, instruction_novice="Crack two eggs into the bowl",
                instruction_expert="Eggs in", end_state="two eggs in the bowl, no shell", view_hint="the bowl",
                mistakes=[Mistake(id="shell", type="technique", description="Shell fell into the bowl",
                                  visual_cue="white flecks in the egg", correction="Fish the shell out")])
    g = TaskGraph(task_id="t", title="omelet", domain="cooking", source="unit", nodes=[node], start=["s1"])
    frames = [rng.integers(0, 256, (360, 480, 3), dtype=np.uint8) for _ in range(3)]
    crop = rng.integers(0, 256, (300, 300, 3), dtype=np.uint8)
    return VerifyRequest(t=10.0, frames=frames, node=node, graph=g, checks=[], crops=[crop],
                         context={"frame_ages": [7.5, 1.0, 0.0]})


def test_same_frames_and_node_same_key(monkeypatch):
    cache = Cache(hits=False)
    v = verifier(monkeypatch, cache)
    v.verify(request())
    v.verify(request())
    assert len(cache.asked) == 2 and cache.asked[0] == cache.asked[1]
    # the requests sent to Jev are unchanged: fresh random refs each time, each naming one of the request's assets
    (s1, a1), (s2, a2) = v.client.sent
    assert set(a1).isdisjoint(a2)
    for s, a in ((s1, a1), (s2, a2)):
        assert [f["frame"] for f in s["frames"]] + s["zoomed_crops"] == list(a)


def test_key_follows_content(monkeypatch):
    cache = Cache(hits=False)
    v = verifier(monkeypatch, cache)
    v.verify(request())
    changed = request()
    changed.frames[-1][:40] = 0                                  # a different "now" frame
    swapped = request()
    swapped.frames[0], swapped.frames[1] = swapped.frames[1], swapped.frames[0]
    no_crop = request()
    no_crop.crops = []
    for r in (changed, swapped, no_crop, request(step="whisk the eggs")):
        v.verify(r)
    assert len(set(cache.asked)) == 5


def test_second_call_answered_from_cache(monkeypatch):
    v = verifier(monkeypatch, Cache())
    a, b = v.verify(request()), v.verify(request())
    assert len(v.client.sent) == 1
    assert b.raw["cached"] and not a.raw["cached"] and b.cost_usd == 0.0
    assert (b.step_status, b.confidence, b.visibility, b.latency_ms) == (a.step_status, a.confidence, a.visibility,
                                                                         a.latency_ms)

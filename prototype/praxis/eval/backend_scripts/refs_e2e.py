"""$0 end-to-end check of reference-video marking through the product code (knowledge/refs.py, the same functions the
admin page calls): upload a pinwheels TRAIN recording to company Test Kitchen, compute its features with Studio's
encoders, (a) automatic marks, (b) marks taken from the dataset's human step labels (standing in for a manager's
clicks), train the approved version's local tracker, then score it offline on the 6 eval clips (local only)."""
import json, shutil, sys
import numpy as np
from praxis.data.cc4d import Clip, load_manifest
from praxis.eval import company_tracking as CT
from praxis.eval import harness
from praxis.knowledge import refs
from praxis.knowledge.parse import file_sha256
from praxis.knowledge.store import Org
from praxis.live import Encoders
org = Org("test-kitchen-captaincook4d")
p = org.procedures()[0]; pid, v = p["id"], p["approved_version"]
man = load_manifest()
ref = next(Clip.from_json(c) for c in man["train"] if c["task_id"] == "cc4d_pinwheels")
src = __import__("pathlib").Path(ref.video)
h = file_sha256(src)
org.add_video(src, f"pinwheels reference ({ref.clip_id}).mp4", h)
enc = Encoders()
f = refs.video_features(org, h, enc)
print("features", len(f["t"]), "frames for", round(float(f["t"][-1]), 1), "s of video", flush=True)
# the dataset ids are recipe step ids; the company graph uses s1..s17 -> map with the same order company_tracking uses
g_ds, _, _ = CT.company_graph()                       # ids remapped to dataset ids, same node order as the company graph
from praxis.tasks.schema import TaskGraph
g_co = TaskGraph.load(org.version_dir(pid, v) / "graph.json")
ds_to_co = {a.id: b.id for a, b in zip(g_ds.nodes, g_co.nodes)}
human = {}
for s in sorted(ref.segments, key=lambda s: s.start):
    k = ds_to_co.get(s.step)
    if k and k not in human:
        human[k] = round(float(s.start - ref.start), 2)
auto = refs.auto_marks(org, pid, v, f)
stack = harness.load_stack()
evals = [Clip.from_json(c) for c in man["eval"] if c["task_id"] == "cc4d_pinwheels"]
out = {}
for name, marks, source in (("automatic marks", auto, "automatic"), ("human-label marks", human, "person")):
    refs.save_marks(org, pid, v, h, marks, source)
    meta = refs.train_local(org, pid, v, enc)
    probe = refs.load_probe(org, pid, v); probe.ids = list(g_ds.ids)      # same order; dataset ids for scoring
    res = [CT.run(stack, c, g_ds, probe, 1.0, f"e2e_{source}") for c in evals]
    out[name] = {"step_acc": round(float(np.mean([r["step_acc"] for r in res])), 3), "per_clip": [round(r["step_acc"], 2) for r in res],
                 "marked_steps": len(marks), "frames": meta["frames"], "steps_covered": meta["steps_covered"]}
    print("ROW", name, json.dumps(out[name]), flush=True)
json.dump({"reference": ref.clip_id, "rows": out}, open(sys.argv[1], "w"), indent=2)
print("left trained on: human-label marks (the approved version now uses it live)")

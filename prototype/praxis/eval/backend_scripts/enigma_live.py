"""Approved ENIGMA-51 maintenance test: Studio session on repair video 141 (high-voltage board, manual screwdriver),
company 'ENIGMA repair lab' locked to its backend-compiled procedure, real verifiers (Jev + Opus escalations),
session cap $0.90 (whole test cap $1.30). Video read in order at 4 fps, frames sent at real-time pace like the browser."""
import collections, json, sys, time
import cv2
from praxis.knowledge.store import Org
from praxis.studio.core import SESSIONS, StudioCore
from praxis.studio.org_session import OrgStudioSession
VIDEO = "/Users/monishsaravana/work/praxis/data/raw/enigma51/videos/141.mp4"
org = Org("enigma-repair-lab")
assert org.settings()["locked"] and org.settings()["assigned"]
core = StudioCore()
cap = cv2.VideoCapture(VIDEO)
fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
dur = (cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) / fps
msgs = []
sess = OrgStudioSession(core, {"org_id": org.id, "input": "upload", "source_label": "ENIGMA-51 video 141 (high-voltage repair)",
                               "task_mode": "auto", "escalation": True, "cost_cap": 0.90, "speech": False}, msgs.append)
print("session", sess.id, "mode", sess.cfg["task_mode"], "duration_s", round(dur, 1), flush=True)
t0, k, i = time.time(), 0, 0
while True:
    target = int(round(k * 0.25 * fps))
    ok = True
    while i < target and ok:
        ok = cap.grab(); i += 1
    ok, f = cap.read(); i += 1
    if not ok:
        break
    h, w = f.shape[:2]
    s = 960 / max(h, w)
    f = cv2.resize(f, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    sess.push_frame(k * 0.25, cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, 80])[1].tobytes())
    if k % 240 == 0:
        st = sess.status()
        print(f"t={k*0.25:7.1f} cost=${st['cost_usd']:.4f} calls={st['calls']} lag={st['lag_s']} engine_frames={st['frames_engine']}", flush=True)
    k += 1
    time.sleep(max(0, t0 + k * 0.25 - time.time()))
end = sess.stop()
sid = sess.save()
recs = [json.loads(l) for l in open(SESSIONS / sid / "live.jsonl")]
summ = next(r for r in recs if r["kind"] == "summary")
g = sess.view.graphs[next(iter(sess.view.graphs))]
names = {n.id: n.name for n in g.nodes}
print("RESULT", json.dumps({
    "session": sid, "duration_s": end["duration_s"], "cost_usd": end["cost_usd"], "cap_hit": summ.get("cap_hit"),
    "frames_in": summ["frames_in"], "frames_engine": summ["frames_engine"],
    "l1_frame_ms_p50": round(summ["l1_frame_ms"]["p50"]), "proc_lag_s_p50": round(summ["proc_lag_s"]["p50"], 2),
    "commits": [(round(r["t"], 1), r.get("node"), names.get(r.get("node")), r.get("reason")) for r in recs if r["kind"] == "commit"],
    "actions": [(round(r["t"], 1), r["action"], r.get("node"), (r.get("text") or "")[:80]) for r in recs if r["kind"] == "action"],
    "safety_banners": [(round(r["t"], 1), r.get("node"), r.get("text", "")[:80]) for r in recs if r["kind"] == "org_safety"],
    "belief_map_counts": collections.Counter(names.get(b.get("map"), b.get("map")) for b in recs if b["kind"] == "belief").most_common(10),
    "verdicts": collections.Counter((r.get("reason"), r.get("role")) for r in recs if r["kind"] == "verdict").most_common(),
}, default=str), flush=True)
time.sleep(90)
print("DONE", flush=True)

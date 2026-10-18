"""The company-backend flow end to end on ENIGMA-51 repair videos (founder-approved 2026-10-18).

A company profile ("ENIGMA repair lab", sessions/orgs/enigma-repair-lab) gets the four written procedures through the
upload/ingest path; each is compiled through the backend's compile endpoint (its own estimate first), reviewed against
its document, approved, and the profile is locked with all four assigned. Praxis then runs on each repair video with
the job set by its assigned procedure (a work order; no recognition from video), using only the profile's approved
procedures. Related footage only: each procedure is tested on its own ENIGMA video, no cooking footage.

Scoring is PROXY (data/enigma51.py): derived step segments from object interactions, and the 66 doc_value moments
re-judged blind against the reference steps derived from the script-compiled graphs (independent of the backend's
graphs). Accuracy is what counts here; speed is not reported except as a footnote.
"""
from __future__ import annotations

import json
import time
from types import SimpleNamespace

import numpy as np

from ..data import enigma51 as E
from ..paths import RESULTS, RUNS

ORG = "enigma-repair-lab"
VIDEO_DOC = {"141": "high-voltage-screwdriver", "107": "high-voltage-electric-screwdriver",
             "144": "low-voltage-electric-screwdriver", "53": "low-voltage-screwdriver"}
RUN = "enigma_backend"
_SIG = None


def texts():
    """SigLIP2 text encoder (CPU is fine for a few hundred phrases); the backend's own Studio core loads every model."""
    global _SIG
    if _SIG is None:
        from ..perception.backbones import SigLIP
        _SIG = SigLIP()
    return _SIG


def _org():
    from ..knowledge.store import Org
    return Org(ORG)


def _doc(o, name):
    d = next(x for x in o.documents() if x["name"] == name)
    return d["versions"][-1]["hash"]


def _api():
    from ..studio import org_api
    org_api._texts = texts                  # same endpoint code; only the text encoder is the light one
    return org_api


def compile_all(cap_usd: float = 1.10, poll_s: float = 3.0) -> dict:
    """Compile every uploaded procedure not compiled yet, through the compile endpoint, with the backend ledger capped
    at what it holds now + cap_usd."""
    from ..knowledge import budget as B
    from ..knowledge.compile import plan
    from ..knowledge.ingest import load_sections
    api = _api()
    led = B.LedgerBudget()
    B._B = B.LedgerBudget(max_usd=led.usd + cap_usd)
    start = B._B.usd
    o = _org()
    done = {v["doc_hash"] for p in o.procedures() for v in p["versions"]}
    out = {}
    for name in VIDEO_DOC.values():
        h = _doc(o, name)
        if h in done:
            out[name] = "compiled before"
            continue
        _, secs, _ = load_sections(o, h)
        sid = secs[0].id
        p = plan(o, h, sid)
        st = api.compile_section(ORG, h, sid, {"confirm_usd": p["estimate"]["upper_usd"], "domain": "maintenance"})
        job = api.JOBS[st["id"]]
        while job.state not in ("done", "error"):
            time.sleep(poll_s)
        out[name] = {"estimate_usd": p["estimate"]["total_usd"], **job.status()}
        print(name, json.dumps(out[name], default=str)[:300], flush=True)
    out["spend_usd"] = B._B.usd - start
    print("compile spend", round(out["spend_usd"], 4), flush=True)
    return out


def approve_and_assign(by: str = "review 2026-10-18 (checked against each document)") -> dict:
    """Approve the latest version of every compiled procedure (embedding its end states), then lock the profile with
    all approved procedures assigned (through the same endpoints the admin page uses)."""
    api = _api()
    o = _org()
    for p in o.procedures():
        if not p.get("approved_version"):
            api.procedure_approve(ORG, p["id"], {"version": p["versions"][-1]["version"], "by": by})
    ids = [p["id"] for p in _org().procedures() if p.get("approved_version")]
    return api.org_settings(ORG, {"locked": True, "assigned": ids})


def proc_for(vid: str) -> dict:
    o = _org()
    return next(p for p in o.procedures() if p["versions"][-1]["doc_name"] == VIDEO_DOC[vid])


def run(vids=("141", "107", "144", "53"), openai_usd: float = 7.0, verifier: str = "openai:gpt-6.1-sol") -> dict:
    """Option A (founder-approved): gpt-6.1-sol answers both "is this step done?" and "which step now?" (it led Jev on
    both in the train-split tests: 85% vs 58% on 100 completion checks, 41% vs 33% on 116 engine step questions);
    no escalation tier (Sol is the strongest checker measured; Opus 82%). Task given by the assigned procedure."""
    from ..experiments import _budget, make_verifier
    from ..perception.extract import load_features  # noqa: F401  (features exist: data/features/enigma_<vid>.npz)
    from ..studio.org_session import runtime_library
    from .enigma_eval import video_path
    from .harness import decode_frames, load_stack, run_clip
    from .run_all import calibrators, engine_config
    o = _org()
    s = o.settings()
    graphs, evidence, info = runtime_library(o, texts(), s["assigned"] if s["locked"] else None)
    base = load_stack()
    st = {**base, "library": graphs, "evidence": evidence, "recognizer": None, "offtask": None}
    ob = _budget(max_calls=6000, max_usd=openai_usd)
    ver = make_verifier(verifier, ob)
    cals = {"primary": calibrators(verifier), "escalation": (None, None)}
    ecfg = engine_config({"escalate": False})
    ann = E.annotations()
    for vid in vids:
        p = proc_for(vid)
        tid = p["task_id"]
        if tid not in graphs:
            print("not approved / assigned yet:", p["id"], flush=True)
            continue
        dur = float(ann["videos"][vid]["duration_seconds"])
        clip = SimpleNamespace(clip_id=f"enigma_{vid}", dataset="ENIGMA-51", task_id=tid, recording=vid,
                               video=str(video_path(vid)), start=0.0, end=dur, duration=dur, segments=[],
                               mistakes=lambda: [])
        frames = decode_frames(clip)
        run_clip(clip, st, RUN, ecfg, ver, None, oracle_task=True, calibrators=cals, frames=frames)
        del frames
        print("ran", vid, p["id"], "openai so far", round(ob.usd, 3), flush=True)
    return {"spend_openai_usd": ob.usd, "calls": ob.calls}


# ------------------------------------------------------------------------------------------- technician questions
# (procedure document, a word in the step's name where the question comes up, question, reference answer written from
# the company's document before any answer was seen)
QUESTIONS = [
    ("high-voltage-screwdriver", "power board", "What voltage do I set on the power supply?",
     "5 volts: turn the current knob until the green LED lights, then set the voltage knob to 5 V."),
    ("high-voltage-screwdriver", "power board", "Which LEDs on the board should come on?", "The red and the green LEDs."),
    ("high-voltage-screwdriver", "soldering iron", "What temperature should the soldering iron be at?",
     "200 degrees, set with the yellow UP button."),
    ("high-voltage-screwdriver", "front", "How long do I hold the iron on each resistor pin?",
     "5 seconds on each pin (first pin, then second), with the resistor held in pliers."),
    ("high-voltage-screwdriver", "lower iron", "What temperature do I turn the iron down to before switching it off?",
     "The minimum, 160 degrees, with the yellow DOWN button."),
    ("high-voltage-electric-screwdriver", "battery", "What do I do with the screwdriver before fixing the board?",
     "Connect the battery to the electric screwdriver."),
    ("high-voltage-electric-screwdriver", "front", "Which component am I heating, and how?",
     "The capacitor: hold it with pliers and touch each of its pins with the soldering iron for 5 seconds."),
    ("high-voltage-electric-screwdriver", "probe", "Where does the probe's ground clip go?",
     "On test point 1 (the probe tip then checks test point 2, and the others up to 7)."),
    ("high-voltage-electric-screwdriver", "probe", "Which oscilloscope channel do I use?",
     "Channel 2, activated with the CH2 MENU button (blue outline)."),
    ("high-voltage-electric-screwdriver", "charger", "What do I do with the screwdriver battery at the end?",
     "Disconnect it, connect it to the battery charger and turn the charger on with the socket switch."),
    ("low-voltage-electric-screwdriver", "red led", "Which LED should come on when the board is powered?",
     "The red LED."),
    ("low-voltage-electric-screwdriver", "display", "How many screws hold the display?",
     "4 screws on the back of the board, removed with the electric screwdriver, then the display comes off."),
    ("low-voltage-electric-screwdriver", "desolder", "Which capacitor do I desolder?", "The black capacitor."),
    ("low-voltage-electric-screwdriver", "test points", "After Auto Set on test point 2, what do I do next?",
     "Repeat the same checks (probe tip on the point, Auto Set, look at the display) for test points 3 to 7."),
    ("low-voltage-electric-screwdriver", "log", "Where do I write down the results?", "In the log."),
    ("low-voltage-screwdriver", "display", "What do I take off after removing the board from the workbench?",
     "Unscrew the 4 screws on the back of the board and remove the display."),
    ("low-voltage-screwdriver", "power", "After switching the supply on, what do I adjust first?",
     "The current knob, until the green LED lights up; then the voltage knob to 5 volts."),
    ("low-voltage-screwdriver", "desolder", "What holds the capacitor while I heat it?", "Pliers."),
    ("low-voltage-screwdriver", "oscilloscope", "What do I press after putting the probe on a test point?",
     "The Auto Set button on the oscilloscope, then look at the display."),
    ("low-voltage-screwdriver", "red button", "What do I press on panel A when I'm finished?",
     "The two red buttons."),
]
QJUDGE = """You grade answers a smart-glasses assistant gave a technician during a repair. You get the question, the
answer written from the company's procedure, and the assistant's answer. "correct": it gives the reference's facts
(numbers, parts, actions) and contradicts nothing; "partial": nothing wrong but a key fact is missing; "wrong": it
contradicts the reference, answers about a different board or procedure, or says the documents don't cover it."""


def _node_for(g, word: str):
    w = word.lower()
    return next((n for n in g.nodes if w in n.name.lower()), None)


def ask_all(answer_cap_usd: float = 0.40, judge_cap_usd: float = 0.10) -> dict:
    """Ask each question through the backend's ask endpoint (admin path: the procedure's step as context), then a
    blind judge from another model family (gpt-6.1-sol) grades it against the reference."""
    from ..experiments import _budget
    from ..knowledge import budget as B
    from ..verify.common import ResponseCache
    from ..verify.openai_vlm import OpenAIVerifier
    api = _api()
    B._B = B.LedgerBudget(max_usd=B.LedgerBudget().usd + answer_cap_usd)
    start = B._B.usd
    jb = _budget(max_calls=60, max_usd=judge_cap_usd)
    judge = OpenAIVerifier("gpt-6.1-sol", jb, effort="low")
    o = _org()
    rows = []
    for doc, word, q, ref in QUESTIONS:
        p = next((x for x in o.procedures() if x["versions"][-1]["doc_name"] == doc and x.get("approved_version")), None)
        if p is None:
            rows.append({"doc": doc, "question": q, "skipped": "procedure not approved"})
            continue
        g = o.load_version(p["id"], p["approved_version"])["graph"]
        n = _node_for(g, word) or g.nodes[0]
        r = api.ask(ORG, {"question": q, "proc_id": p["id"], "version": p["approved_version"], "node": n.id,
                          "use_model": True})
        text = f"Question: {q}\nReference answer (from the procedure): {ref}\nAssistant's answer: {r['answer']}"
        schema = {"type": "object", "additionalProperties": False, "required": ["grade"],
                  "properties": {"grade": {"type": "string", "enum": ["correct", "partial", "wrong"]}}}
        out, _ = judge._call(QJUDGE, [{"type": "input_text", "text": text}], schema, "grade",
                             ResponseCache.key("backend_qa_judge-v1", text))
        rows.append({"doc": doc, "step": f"{n.id} {n.name}", "question": q, "reference": ref, "answer": r["answer"],
                     "source": r.get("source"), "citations": [c.get("where") for c in r.get("citations", [])],
                     "answer_cost_usd": r.get("cost_usd", 0.0), "grade": out["grade"]})
        print(rows[-1]["grade"], "|", q, "|", r["answer"][:120], flush=True)
    gr = [r["grade"] for r in rows if "grade" in r]
    res = {"label": "Technician questions answered from the company's uploaded procedures through the backend's ask "
                    "endpoint (Opus 5.5, retrieval over all four documents); blind-judged by gpt-6.1-sol against "
                    "reference answers written from the documents before any answer was seen",
           "n": len(gr), **{k: gr.count(k) for k in ("correct", "partial", "wrong")}, "rows": rows,
           "spend_backend_usd": B._B.usd - start, "spend_judge_openai_usd": jb.usd}
    p = RESULTS / "enigma51" / "backend_flow.json"
    cur = json.loads(p.read_text()) if p.exists() else {}
    cur["questions"] = res
    p.write_text(json.dumps(cur, indent=1, default=float))
    return res


# ------------------------------------------------------------------------------------------- scoring
def _graphs() -> dict:
    o = _org()
    return {x["proc_id"]: x["graph"] for x in o.library().values()}


def score_runs() -> dict:
    """Per video: step accuracy against step segments derived for the backend's own graph (PROXY), and object
    consistency at the annotated interactions; calls and cost from the run log."""
    from ..eval import metrics as M
    from ..runlog import by_kind, read_log
    gs = _graphs()
    rows = []
    for vid in VIDEO_DOC:
        p = RUNS / RUN / f"enigma_{vid}.jsonl"
        if not p.exists():
            continue
        g = gs[proc_for(vid)["id"]]
        recs = read_log(p)
        end = recs[-1]["t"]
        inter = [x for x in E.interactions(vid) if x[0] <= end]
        segs = E.derived_segments(g, inter)
        times = np.arange(0.5, end, 0.5)
        pred = M.predicted_labels(recs, times)
        gt = np.array([next((s for a, b, s in segs if a <= t < b), "") for t in times], dtype=object)
        inside = gt != ""
        bel = by_kind(recs, "belief")
        bt = np.array([b["t"] for b in bel])

        def belief_at(t):
            j = np.searchsorted(bt, t, side="right") - 1
            return bel[j]["map"] if j >= 0 else None
        ver, sc = by_kind(recs, "verdict"), by_kind(recs, "step_choice")
        cost = sum((x.get("orig_cost_usd", x.get("cost_usd", 0.0)) or 0.0) for x in ver + sc)
        rows.append({"video": vid, "procedure": proc_for(vid)["id"], "minutes": end / 60, "n_steps": len(g.nodes),
                     "derived_segments": len(segs),
                     "step_acc_derived": float(((pred == gt) & inside).sum() / max(1, inside.sum())),
                     "object_consistency": E.object_consistency(g, inter, belief_at),
                     "commits": len(by_kind(recs, "commit")), "completion_checks": len(ver), "step_questions": len(sc),
                     "instructions": sum(1 for a in by_kind(recs, "action") if a["action"] == "instruct"),
                     "mistake_alerts": sum(1 for a in by_kind(recs, "action") if a["action"] == "mistake"),
                     "cost_usd": cost})
    return {"rows": rows,
            "mean_step_acc_derived": float(np.mean([r["step_acc_derived"] for r in rows])) if rows else None}


def _shown(recs, t):
    from ..runlog import by_kind
    ins = [a for a in by_kind(recs, "action") if a["action"] in ("instruct", "resume_task") and a["t"] <= t]
    return {"answer": ins[-1]["text"], "node": ins[-1].get("node")} if ins else None


def _believed(recs, t, g):
    from ..runlog import by_kind
    bel = [b for b in by_kind(recs, "belief") if b["t"] <= t]
    if not bel or bel[-1]["map"] not in g.ids:
        return None
    n = g.node(bel[-1]["map"])
    return {"answer": n.instruction_expert or n.name, "node": n.id}


def judge_moments(cap_usd: float = 0.40, workers: int = 4) -> dict:
    """The 66 doc_value moments: the instruction Praxis shows (logged; the display rule is in the engine now) and the
    step it believes, each judged blind against the reference step from the SCRIPT-compiled graph's derived labels
    (independent of the backend's graph). The general-assistant arms are read from doc_value.json, not re-run."""
    from concurrent.futures import ThreadPoolExecutor
    from ..runlog import read_log
    from ..verify.common import Budget
    from .doc_value import ITEMS, _judge
    lib, gs = E.library(), _graphs()
    items = json.loads((ITEMS / "items.json").read_text())
    jb = Budget(len(items) * 2 + 10, cap_usd)
    logs = {v: read_log(RUNS / RUN / f"enigma_{v}.jsonl") for v in VIDEO_DOC if (RUNS / RUN / f"enigma_{v}.jsonl").exists()}

    def one(it):
        out = {"id": it["id"], "video": it["video"]}
        if it["video"] not in logs:
            return {**out, "shown": {"grade": "not_run"}, "believed": {"grade": "not_run"}}
        recs, g = logs[it["video"]], gs[proc_for(it["video"])["id"]]
        for arm, a in (("shown", _shown(recs, it["t"])), ("believed", _believed(recs, it["t"], g))):
            out[arm] = {**(a or {}), "grade": _judge(jb, it, a["answer"], lib[it["task_id"]])["grade"] if a else "no_answer"}
        return out
    with ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(one, items))
    prev = json.loads((RESULTS / "enigma51" / "doc_value.json").read_text())
    pv = {r["id"]: r for r in prev["rows"]}
    post = {r["id"]: r for r in (prev.get("praxis_shown_postfix") or {}).get("rows", [])}
    ran = [r for r in rows if r["shown"]["grade"] != "not_run"]
    ids = {r["id"] for r in ran}

    def table(grades):
        return {"n": len(grades), **{k: grades.count(k) for k in ("correct", "adjacent", "wrong", "no_answer")}}
    res = {"label": "same 66 moments as doc_value (PROXY reference steps from object-interaction labels and the "
                    "script-compiled graphs); Praxis runs on procedures compiled through the company backend, "
                    "gpt-6.1-sol as checker", "videos": sorted(logs), "n": len(ran),
           "table": {"backend_praxis_shown": table([r["shown"]["grade"] for r in ran]),
                     "backend_praxis_believed": table([r["believed"]["grade"] for r in ran]),
                     "earlier_praxis_shown_postfix": table([post[i]["grade"] for i in ids if i in post]),
                     "earlier_praxis_believed": table([pv[i]["praxis_believed"]["grade"] for i in ids]),
                     "general+doc": table([pv[i]["general+doc"]["grade"] for i in ids]),
                     "general": table([pv[i]["general"]["grade"] for i in ids])},
           "rows": rows, "spend_judge_usd": jb.usd}
    p = RESULTS / "enigma51" / "backend_flow.json"
    cur = json.loads(p.read_text()) if p.exists() else {}
    cur["moments"] = res
    cur["runs"] = score_runs()
    cur["spend_usd_non_openai"] = cur.get("spend_usd_non_openai", 0.0) + jb.usd    # judge (Anthropic); OpenAI from cache
    p.write_text(json.dumps(cur, indent=1, default=float))
    return res

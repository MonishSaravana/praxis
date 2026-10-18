"""What does the company's written procedure buy? (ENIGMA-51 repair videos; PROXY labels, see data/enigma51.py.)

Same moments of the same first-person repair videos, three assistants answer "what should the technician do now?":
  general       a frontier vision model sees the recent frames and is told only "a technician is repairing an
                electrical board at a workbench" (a standalone assistant out of the box; a stand-in, not any
                specific product)
  general+doc   the same model with the full written procedure pasted into every request, no memory between
                requests (what document retrieval on a standalone device gives you)
  praxis        the instruction Praxis is showing at that moment (procedure compiled into a task graph + state
                tracking), read from its run log

A blind judge (a different model family from the general assistant) compares each answer with the procedure step the
technician is on (DERIVED from object-interaction labels) and its neighbours: correct / adjacent step / wrong.
Moments: 5 s into each derived step segment, plus its midpoint when the segment is longer than 40 s.
"""
from __future__ import annotations

import json
import random

import numpy as np

from ..data import enigma51 as E
from ..paths import DATA, RESULTS, RUNS
from ..runlog import by_kind, read_log
from ..verify.common import ResponseCache, span_keyframes

ITEMS = DATA / "enigma51" / "doc_value"
CONTEXT = "A technician is repairing an electrical board at a workbench in a lab."
ASK = ("You are the assistant in a technician's smart glasses. The frames are first-person, oldest first; the last one "
       "is now. {ctx} In one short sentence, say exactly what the technician should do now to continue the job.")
JUDGE_SYSTEM = """You grade a smart-glasses assistant. You get the step of a written repair procedure the technician is
actually on, the steps just before and after it, and the assistant's instruction. Decide whether the instruction tells
the technician to do the reference step: the same physical action on the same object, whatever the wording
(parameters like voltages or temperatures must not contradict the procedure). Answer "correct", "adjacent" (it names the step just before or just after instead)
or "wrong" (anything else, including vague or generic advice)."""


def build_items(per_long: float = 40.0) -> list[dict]:
    """Moments + the engine's three keyframes at each (free; decoding only)."""
    import cv2
    from ..io.sources import FileSource
    ITEMS.mkdir(parents=True, exist_ok=True)
    lib, ann = E.library(), E.annotations()
    items = []
    for vid, tid in E.TEST_VIDEOS.items():
        g = lib[tid]
        order = [n.id for n in g.nodes]
        segs = E.derived_segments(g, E.interactions(vid, ann))
        for a, b, sid in segs:
            ts = [a + 5.0] + ([0.5 * (a + b)] if b - a > per_long else [])
            for t in ts:
                if t >= b:
                    continue
                frames, times = [], []
                for f in FileSource(str(E.RAW / "videos" / f"{vid}.mp4"), fps=4.0, start=max(0.0, t - 9.0), end=t + 0.25,
                                    max_side=640):
                    frames.append(f.rgb)
                    times.append(max(0.0, t - 9.0) + f.t)
                ft = np.array(times)
                kf, _ = span_keyframes(lambda x: frames[int(np.argmin(np.abs(ft - x)))], t)
                iid = f"{vid}_{int(t)}"
                paths = []
                for j, im in enumerate(kf):
                    p = ITEMS / f"{iid}_{j}.jpg"
                    cv2.imwrite(str(p), cv2.cvtColor(im, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
                    paths.append(p.name)
                k = order.index(sid)
                items.append({"id": iid, "video": vid, "task_id": tid, "t": round(t, 2), "step": sid,
                              "prev": order[k - 1] if k > 0 else None, "next": order[k + 1] if k + 1 < len(order) else None,
                              "frames": paths})
    (ITEMS / "items.json").write_text(json.dumps(items, indent=1))
    return items


def _frames(it):
    import cv2
    return [cv2.cvtColor(cv2.imread(str(ITEMS / p)), cv2.COLOR_BGR2RGB) for p in it["frames"]]


def _general(model: str, budget, it, doc: str | None) -> dict:
    """One stateless request to an OpenAI vision model (with or without the written procedure)."""
    from ..verify.common import b64, to_jpeg
    from ..verify.openai_vlm import OpenAIVerifier
    v = OpenAIVerifier(model, budget, effort="low")
    content, raw = [], []
    for i, f in enumerate(_frames(it)):
        jpg = to_jpeg(f, 640)
        raw.append(jpg)
        content += [{"type": "input_text", "text": f"Frame {i + 1}/3" + (" = now" if i == 2 else "")},
                    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64(jpg)}"}]
    ctx = CONTEXT + (f"\n\nThe written procedure for this job:\n{doc}" if doc else "")
    content.append({"type": "input_text", "text": ASK.format(ctx=ctx)})
    schema = {"type": "object", "additionalProperties": False, "required": ["instruction"],
              "properties": {"instruction": {"type": "string"}}}
    key = ResponseCache.key("doc_value-v1", model, bool(doc), ctx, *raw)
    out, meta = v._call("You are a helpful smart-glasses assistant for technicians. Judge only what is visible.",
                        content, schema, "instruction", key)
    return {"answer": out["instruction"], "latency_ms": meta["latency_ms"], "cost_usd": meta["cost_usd"],
            "cached": meta.get("cached", False)}


def _praxis_answer(it, run: str) -> dict | None:
    p = RUNS / run / f"enigma_{it['video']}.jsonl"
    if not p.exists():
        return None                                # no Praxis run on this video yet
    recs = read_log(p)
    ins = [a for a in by_kind(recs, "action") if a["action"] in ("instruct", "resume_task") and a["t"] <= it["t"]]
    if not ins:
        return None
    return {"answer": ins[-1]["text"], "node": ins[-1].get("node")}


def _praxis_believed(it, run: str, g) -> dict | None:
    """The instruction for the step Praxis believes the technician is on at that moment (what it would say if it
    spoke then; the replay never speaks a first instruction when the task is given at the start)."""
    p = RUNS / run / f"enigma_{it['video']}.jsonl"
    if not p.exists():
        return None
    bel = [b for b in by_kind(read_log(p), "belief") if b["t"] <= it["t"]]
    if not bel or bel[-1]["map"] not in g.ids:
        return None
    n = g.node(bel[-1]["map"])
    return {"answer": n.instruction_expert or n.name, "node": n.id}


def _judge(budget, it, answer: str, g) -> dict:
    from ..verify.claude import ClaudeVerifier
    j = ClaudeVerifier("claude-opus-5-5", budget, role="strong")

    def step(sid):
        # the short step name only (written from the SOP by the split stage): Praxis's own instruction text comes from
        # the same compiled graph, so showing the graph's instruction wording would favour Praxis on wording alone
        return "(none)" if sid is None else g.node(sid).name
    text = (f"Reference step (the technician is on this one): {step(it['step'])}\nStep just before: {step(it['prev'])}\n"
            f"Step just after: {step(it['next'])}\n\nAssistant's instruction: {answer}")
    schema = {"type": "object", "additionalProperties": False, "required": ["grade"],
              "properties": {"grade": {"type": "string", "enum": ["correct", "adjacent", "wrong"]}}}
    key = ResponseCache.key("doc_value_judge-v2", text)
    out, meta = j._call(JUDGE_SYSTEM, [{"type": "text", "text": text}], schema, key)
    return {"grade": out["grade"], "cost_usd": meta["cost_usd"], "cached": meta.get("cached", False)}


def run(model: str = "gpt-6.1-sol", praxis_run: str = "enigma_task_given", openai_budget: float = 2.0,
        judge_budget: float = 1.5, workers: int = 4) -> dict:
    from concurrent.futures import ThreadPoolExecutor
    from ..verify.common import Budget
    lib = E.library()
    items = json.loads((ITEMS / "items.json").read_text())
    docs = {tid: (E.RAW / "ENIGMA-51_procedures" / f).read_text() for tid, (f, _, _) in E.PROCS.items()}
    ob, jb = Budget(len(items) * 2 + 10, openai_budget), Budget(len(items) * 3 + 10, judge_budget)
    rng = random.Random(0)

    def one(it):
        g = lib[it["task_id"]]
        out = {"id": it["id"], "video": it["video"], "step": it["step"]}
        logged = (RUNS / praxis_run / f"enigma_{it['video']}.jsonl").exists()
        answers = {"general": _general(model, ob, it, None), "general+doc": _general(model, ob, it, docs[it["task_id"]]),
                   "praxis": _praxis_answer(it, praxis_run), "praxis_believed": _praxis_believed(it, praxis_run, g)}
        out["praxis_logged"] = logged
        for name in rng.sample(list(answers), len(answers)):        # judge order shuffled; the judge never sees names
            a = answers[name]
            if name.startswith("praxis") and not logged:
                out[name] = {"grade": "not_run"}
                continue
            out[name] = {**(a or {}), "grade": _judge(jb, it, a["answer"], g)["grade"] if a else "no_answer"}
        return out
    with ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(one, items))
    res = {"label": "ENIGMA-51 repair videos; PROXY reference steps derived from object-interaction labels; "
                    "'general' is a stand-in for a standalone assistant, not a specific product",
           "assistant_model": model, "judge": "claude-opus-5-5", "n": len(rows), "conditions": {}}
    def summ(rs, c):
        gr = [r[c]["grade"] for r in rs]
        lat = [r[c]["latency_ms"] for r in rs if r[c].get("latency_ms") and not r[c].get("cached")]
        return {"n": len(gr), "correct": gr.count("correct") / len(gr), "adjacent": gr.count("adjacent") / len(gr),
                "wrong": gr.count("wrong") / len(gr), "no_answer": gr.count("no_answer") / len(gr),
                "latency_ms_p50": float(np.median(lat)) if lat else None} if gr else None
    matched = [r for r in rows if r["praxis_logged"]]
    res["conditions"] = {c: summ(rows, c) for c in ("general", "general+doc")}
    res["matched_subset"] = {"videos": sorted({r["video"] for r in matched}), "n": len(matched),
                             **{c: summ(matched, c) for c in ("general", "general+doc", "praxis", "praxis_believed")}}
    res["rows"] = rows
    prev_p = RESULTS / "enigma51" / "doc_value.json"           # spend accumulates over re-runs (cached calls cost $0)
    prev = json.loads(prev_p.read_text()) if prev_p.exists() else {}
    res["spend_openai_usd"] = prev.get("spend_openai_usd", 0.0) + ob.usd
    res["spend_judge_usd"] = prev.get("spend_judge_usd", 0.0) + jb.usd
    res["spend_usd_non_openai"] = res["spend_judge_usd"]   # OpenAI calls are counted from their response cache
    (RESULTS / "enigma51").mkdir(parents=True, exist_ok=True)
    (RESULTS / "enigma51" / "doc_value.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({"all": res["conditions"], "matched": res["matched_subset"]}, indent=1), flush=True)
    return res


def report(run: str = "enigma_task_given") -> dict:
    """The table for all moments (Praxis-shown first, since that is what a user sees) and why Praxis showed nothing."""
    res = json.loads((RESULTS / "enigma51" / "doc_value.json").read_text())
    rows = res["rows"]
    out = {"n": len(rows), "table": {}}
    for c in ("praxis", "praxis_believed", "general", "general+doc"):
        gr = [r[c]["grade"] for r in rows if r[c]["grade"] != "not_run"]
        out["table"][c] = {"n": len(gr), **{k: gr.count(k) for k in ("correct", "adjacent", "wrong", "no_answer")}}
    first, why = {}, []
    for vid in sorted({r["video"] for r in rows}):
        recs = read_log(RUNS / run / f"enigma_{vid}.jsonl")
        ins = [a["t"] for a in by_kind(recs, "action") if a["action"] in ("instruct", "resume_task")]
        com = [c["t"] for c in by_kind(recs, "commit")]
        first[vid] = {"first_instruction_s": ins[0] if ins else None, "first_commit_s": com[0] if com else None}
    for r in rows:
        if r["praxis"]["grade"] == "no_answer":
            t = float(r["id"].split("_")[1])
            f = first[r["video"]]
            why.append({"moment": r["id"], "t": t, **f,
                        "reason": "before Praxis's first instruction: with the task given at the start, the replay speaks "
                                  "its first instruction only after its first step commit"
                        if f["first_instruction_s"] is None or t < f["first_instruction_s"] else "other"})
    out["first_instruction_by_video"] = first
    out["nothing_shown"] = why
    return out

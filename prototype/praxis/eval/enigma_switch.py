"""SYNTHETIC multi-task sessions on REPAIR footage (ENIGMA-51, first-person electrical-board repair), scored with
DERIVED step labels (data/enigma51.py: object interactions aligned to the steps, not human step labels). Every result
from this module is labeled SYNTHETIC + PROXY.

Each session starts on job A's procedure, given the way a work order would set it; switching is automatic.
  resume     A to a step end -> 150 s of the start of another board-repair job B -> 300 s more of A
  interrupt  A to a step end -> 90 s of a cooking recipe that is not in the library -> 300 s more of A
The cut is the first derived step end at or after 360 s (+0.5 s), so "resumed at the right step" has an
answer: the derived step at the cut. Pairs are fixed: 141->107 (same board, other screwdriver), 107->144 (other board,
same screwdriver), 144->53 (same board, other screwdriver), 53->141 (other board).

The splices cut hard (the camera jumps); real switches are gradual, so latencies here are not real-life latencies.
Library: the four repair procedures plus the cooking library (as in Studio, where every compiled task sits together).
Engine: the multi-task configuration chosen on the cooking train split (results/multitask/chosen.json) and the
current defaults (switch-bar cap + streak override, first instruction at start, instruction follows the belief);
Jev fast tier, gpt-6.1-sol answers "which task?", no strong-tier step checks. No user answers in replay.
"""
from __future__ import annotations

import json

import numpy as np

from ..data import enigma51 as E
from ..data.cc4d import Clip, load_manifest
from ..events.detector import ClipFeatures
from ..io.sources import FileSource
from ..paths import FEATURES, RESULTS, RUNS
from ..perception.extract import load_features
from ..runlog import by_kind, read_log
from . import metrics as M
from .enigma_eval import video_path
from .harness import current_task, task_changes

OTHER = "__other__"
PAIRS = {"141": "107", "107": "144", "144": "53", "53": "141"}
CUT_AFTER = 360.0
B_S, X_S, REST_S = 150.0, 90.0, 300.0
RUN = "enigma_switch"


# ------------------------------------------------------------------------------------------- ground truth
def _segs(vid: str, ann=None) -> list[tuple[float, float, str]]:
    g = E.library()[E.TEST_VIDEOS[vid]]
    return E.derived_segments(g, E.interactions(vid, ann))


def cut_point(vid: str, ann=None) -> float:
    return round(min(b for _, b, _ in _segs(vid, ann) if b >= CUT_AFTER) + 0.5, 2)


def interrupt_footage() -> list[Clip]:
    """Cooking recordings of recipes outside the library, the eval half (as the cooking splices use)."""
    man = load_manifest()
    others = sorted((Clip.from_json(c) for c in man.get("heldout_type", []) if (FEATURES / f"{c['clip_id']}.npz").exists()),
                    key=lambda c: c.clip_id)
    return others[1::2]


def specs() -> list[dict]:
    ann = E.annotations()
    xs = interrupt_footage()
    out = []
    for i, (a, b) in enumerate(PAIRS.items()):
        c = cut_point(a, ann)
        A = lambda s0, s1: {"src": "enigma", "id": a, "task_id": E.TEST_VIDEOS[a], "s0": s0, "s1": s1}
        out.append({"id": f"enigma_resume_{a}_{b}", "kind": "resume", "cut": c,
                    "parts": [A(0.0, c), {"src": "enigma", "id": b, "task_id": E.TEST_VIDEOS[b], "s0": 0.0, "s1": B_S},
                              A(c, c + REST_S)]})
        x = xs[i % len(xs)]
        out.append({"id": f"enigma_interrupt_{a}", "kind": "interrupt", "cut": c,
                    "parts": [A(0.0, c), {"src": "cc4d", "id": x.clip_id, "task_id": OTHER, "s0": 0.0, "s1": X_S},
                              A(c, c + REST_S)]})
    return out


def build(spec: dict, decode: bool = True):
    """Concatenate the parts' L1 features (and decoded frames, 1:1 with feature rows) on one timeline. Returns
    (features, frames, gt) with gt = [(t0, t1, task_id, [(start, end, step), ...]), ...] in session time."""
    ann = E.annotations()
    clips = {c["clip_id"]: Clip.from_json(c) for c in load_manifest().get("heldout_type", [])}
    T, fs, frames, gt = 0.0, [], [], []
    for p in spec["parts"]:
        if p["src"] == "enigma":
            fid, video, v0 = f"enigma_{p['id']}", str(video_path(p["id"])), 0.0
            segs_all = _segs(p["id"], ann)
        else:
            c = clips[p["id"]]
            fid, video, v0, segs_all = c.clip_id, c.video, c.start, []
        f, _ = load_features(fid)
        m = (f.t >= p["s0"]) & (f.t < p["s1"])
        n = int(m.sum())
        fs.append((f.t[m] - p["s0"] + T, f.frame[m], f.hands[m], f.window[m], f.change[m]))
        if decode:
            fr = [x.rgb for x in FileSource(video, fps=4.0, start=v0 + p["s0"], end=v0 + p["s1"], max_side=640)]
            frames += (fr + [fr[-1]] * n)[:n] if fr else [np.zeros((360, 640, 3), np.uint8)] * n
        segs = [(max(a, p["s0"]) - p["s0"] + T, min(b, p["s1"]) - p["s0"] + T, s) for a, b, s in segs_all
                if b > p["s0"] and a < p["s1"]]
        gt.append((T, T + p["s1"] - p["s0"], p["task_id"], segs))
        T += p["s1"] - p["s0"]
    cat = [np.concatenate([x[i] for x in fs]) for i in range(5)]
    return ClipFeatures(spec["id"], *cat), frames, gt


# ------------------------------------------------------------------------------------------- stack and run
def stack() -> dict:
    """Cooking stack (offtask landmark model of the chosen window) + the four repair procedures with zero-shot
    evidence; no recognizer (the first task is given; later tasks come from the typed "which task?" check)."""
    from ..evidence import ZeroShotEvidence
    from . import harness
    from .run_all import multitask_overrides
    win = multitask_overrides().get("offtask_window")
    base = harness.load_stack(offtask_window=win)
    lib, ev = dict(base["library"]), dict(base["evidence"])
    for tid, g in E.library().items():
        z = np.load(E.GRAPHS / f"{tid}.npz")
        lib[tid], ev[tid] = g, ZeroShotEvidence(g, {k: z[k] for k in z.files})
    return {**base, "library": lib, "evidence": ev, "recognizer": None}


def engine_cfg():
    from .run_all import engine_config, multitask_overrides
    over = {k: v for k, v in multitask_overrides().items() if k != "offtask_window"}
    return engine_config({**over, "multi_task": True, "switching": True, "escalate": False})


def run_one(spec: dict, st: dict, ecfg, verifier=None, task_checker=None, calibrators=None, run_name: str = RUN):
    from ..engine import Engine, replay
    from ..runlog import RunLog
    feats, frames, gt = build(spec)
    scores = st["detector"].score(feats)
    out = RUNS / run_name / f"{spec['id']}.jsonl"
    meta = {"splice": spec, "label": "SYNTHETIC multi-task session (spliced ENIGMA-51 repair videos); PROXY labels",
            "run": run_name, "engine": {k: (v if isinstance(v, (int, float, str, bool, type(None))) else str(v))
                                        for k, v in vars(ecfg).items()},
            "verifier": getattr(verifier, "model", None), "task_checker": getattr(task_checker, "model", None)}
    with RunLog(out, meta) as log:
        eng = Engine(ecfg, st["library"], st["evidence"], None, st["detector"], verifier, None, log=log,
                     calibrators=calibrators, offtask=st.get("offtask"), task_checker=task_checker,
                     task_id=spec["parts"][0]["task_id"])
        info = replay(eng, feats, scores, frames)
        log.write("summary", float(feats.t[-1]) if len(feats.t) else 0.0, **info)
    del frames
    return out


# ------------------------------------------------------------------------------------------- scoring
def _order(task_id: str) -> list[str]:
    return [n.id for n in E.library()[task_id].nodes]


def _within1(order, a, b) -> bool:
    return a in order and b in order and abs(order.index(a) - order.index(b)) <= 1


def score(spec: dict, log_path, settle_s: float = 60.0) -> dict:
    """Reads only the spec (ground truth) and the run log. Step ids repeat across the repair graphs (s1..s20), so a
    step counts only when the engine's current task is also the one playing."""
    recs = read_log(log_path)
    _, _, gt = build(spec, decode=False)
    end = gt[-1][1]
    times = np.arange(0.5, end, 0.5)
    task_gt = np.empty(len(times), dtype=object)
    step_gt = np.empty(len(times), dtype=object)
    inside = np.zeros(len(times), bool)
    for t0, t1, task, segs in gt:
        m = (times >= t0) & (times < t1)
        task_gt[m] = task
        if segs:
            step_gt[m] = M.frame_labels(segs, times[m], between="next")
            inside[m] = np.array([any(a <= t < b for a, b, _ in segs) for t in times[m]])
    pred = M.predicted_labels(recs, times)
    cur = current_task(recs, times)
    ch = task_changes(recs)
    a = spec["parts"][0]["task_id"]
    t_x0, t_ret = gt[1][0], gt[2][0]
    okA = np.array([g == a for g in task_gt]) & inside
    res = {"id": spec["id"], "kind": spec["kind"], "minutes": end / 60.0, "task_a": a, "middle": spec["parts"][1]["task_id"],
           "step_acc": float(((step_gt == pred) & (cur == task_gt) & inside).sum() / max(1, inside.sum())),
           "step_acc_job_a": float(((step_gt == pred) & (cur == task_gt) & okA).sum() / max(1, okA.sum())),
           "step_acc_job_a_first_part": None,
           "correct_task_share": float(np.mean([c == g for c, g in zip(cur, task_gt) if g != OTHER]))}
    m1 = okA & (times < t_x0)
    res["step_acc_job_a_first_part"] = float(((step_gt == pred) & (cur == task_gt) & m1).sum() / max(1, m1.sum()))

    def playing(t):
        for t0, t1, task, _ in gt:
            if t0 <= t < t1:
                return task
        return gt[-1][2]
    later = ch[1:] if ch else []
    res["task_changes"] = [[round(t, 1), k] for t, k in later]
    res["switches"] = len(later)
    res["wrong_switches"] = sum(1 for t, k in later if k is not None and k != playing(t))
    res["wrong_switches_detail"] = [[round(t, 1), k, playing(t)] for t, k in later if k is not None and k != playing(t)]
    # the middle part
    mid = spec["parts"][1]["task_id"]
    if mid != OTHER:
        hit = [t for t, k in ch if t_x0 <= t < t_ret and k == mid]
        res["switch_detected"] = bool(hit)
        res["switch_latency_s"] = round(hit[0] - t_x0, 1) if hit else None
    else:
        st = [x for x in by_kind(recs, "task_state") if x.get("reason") == "interruption" and x["task_id"] == a]
        res["interruption_paused"] = any(t_x0 <= x["t"] < t_ret + 30 for x in st)
        res["interruption_pause_latency_s"] = next((round(x["t"] - t_x0, 1) for x in st if t_x0 <= x["t"] < t_ret + 30), None)
        res["interruption_pauses_outside"] = sum(1 for x in st if not (t_x0 <= x["t"] < t_ret + 30))
    # back to A: when A is current again, at which step
    left = any(t_x0 <= t < t_ret + settle_s and k != a for t, k in later) or \
        any(t < t_x0 and k != a for t, k in later)
    back = [t for t, k in ch if t >= t_ret and k == a]
    res["left_a"] = left
    res["a_current_60s_after_return"] = bool(cur[np.searchsorted(times, min(end - 0.5, t_ret + settle_s))] == a)
    res["resumed"] = bool(left and back)
    res["resume_latency_s"] = round(back[0] - t_ret, 1) if (left and back) else None
    t_chk = back[0] if (left and back) else (t_ret if not left else None)
    order = _order(a)
    segA = _segs(spec["parts"][0]["id"])
    ret_label = M.frame_labels(segA, np.array([spec["cut"]]), between="next")[0]
    res["return_step_gt"] = ret_label
    if t_chk is not None:
        bel = [r for r in by_kind(recs, "belief") if r["t"] >= t_chk and r.get("task_id", a) == a]
        if bel:
            got = bel[0]["map"]
            now_label = M.frame_labels(segA, np.array([spec["cut"] + (t_chk - t_ret)]), between="next")[0]
            res.update({"resume_step": got, "resume_step_exact": got == ret_label,
                        "resume_step_within1": _within1(order, got, ret_label), "step_gt_at_resume": now_label,
                        "resume_step_exact_at_resume": got == now_label,
                        "resume_step_within1_at_resume": _within1(order, got, now_label)})
    # what the person heard / saw
    acts = by_kind(recs, "action")
    ra = [x for x in acts if x["action"] == "resume_task" and x["t"] >= t_ret and (x.get("detail") or {}).get("title")
          == E.library()[a].title]
    res["resume_line"] = ra[0]["text"] if ra else None
    res["resume_line_step"] = ra[0]["node"] if ra else None
    res["resume_line_step_exact"] = (ra[0]["node"] == ret_label) if ra else None
    res["resume_line_step_within1"] = _within1(order, ra[0]["node"], ret_label) if ra else None
    asks = by_kind(recs, "ask_resume")
    res["coming_back_asked"] = [[round(x["t"], 1), x["task_id"], playing(x["t"])] for x in asks]
    res["switch_lines"] = [[round(x["t"], 1), x["action"], x["text"]] for x in acts
                           if x["action"] in ("switch_task", "retract_task", "leave_warning", "resume_task")]
    rc = [r for r in by_kind(recs, "task_check") if not r.get("error")]
    res["task_checks"] = len(rc)
    res["task_check_errors"] = sum(1 for r in by_kind(recs, "task_check") if r.get("error"))
    res["task_checks_by_part"] = [sum(1 for r in rc if t0 <= r["t"] < t1) for t0, t1, _, _ in gt]
    ver = by_kind(recs, "verdict")
    sc = by_kind(recs, "step_choice") + rc
    res["verifier_calls"] = len(ver) + len(sc)
    res["cost_usd"] = float(sum(v.get("orig_cost_usd", v.get("cost_usd", 0.0)) or 0.0 for v in ver)
                            + sum(x.get("cost_usd", 0.0) or 0.0 for x in sc))
    return res


def aggregate(rows: list[dict]) -> dict:
    def mean(k, rs):
        v = [r[k] for r in rs if r.get(k) is not None]
        return float(np.mean(v)) if v else None
    rr = [r for r in rows if r["kind"] == "resume"]
    ir = [r for r in rows if r["kind"] == "interrupt"]
    mins = sum(r["minutes"] for r in rows)
    out = {"n": len(rows), "minutes": mins, "step_acc": mean("step_acc", rows),
           "step_acc_job_a": mean("step_acc_job_a", rows), "correct_task_share": mean("correct_task_share", rows),
           "wrong_switches": sum(r["wrong_switches"] for r in rows),
           "wrong_switches_per_hour": sum(r["wrong_switches"] for r in rows) / max(1e-6, mins / 60),
           "task_checks": sum(r["task_checks"] for r in rows), "cost_usd": float(sum(r["cost_usd"] for r in rows))}
    if rr:
        lat = [r["switch_latency_s"] for r in rr if r["switch_latency_s"] is not None]
        out["resume"] = {"n": len(rr), "switch_detected": sum(r["switch_detected"] for r in rr),
                         "switch_latency_s": lat, "resumed": sum(r["resumed"] for r in rr),
                         "a_current_60s_after_return": sum(r["a_current_60s_after_return"] for r in rr),
                         "resume_step_exact": sum(bool(r.get("resume_step_exact")) for r in rr),
                         "resume_step_within1": sum(bool(r.get("resume_step_within1")) for r in rr),
                         "resume_line_step_exact": sum(bool(r.get("resume_line_step_exact")) for r in rr),
                         "resume_line_step_within1": sum(bool(r.get("resume_line_step_within1")) for r in rr),
                         "coming_back_asked": sum(bool(r["coming_back_asked"]) for r in rr),
                         "wrong_switches": sum(r["wrong_switches"] for r in rr)}
    if ir:
        out["interrupt"] = {"n": len(ir), "switched_to_a_library_task": sum(r["wrong_switches"] > 0 for r in ir),
                            "paused_as_interruption": sum(r["interruption_paused"] for r in ir),
                            "a_current_60s_after_return": sum(r["a_current_60s_after_return"] for r in ir),
                            "resume_step_exact": sum(bool(r.get("resume_step_exact")) for r in ir),
                            "resume_step_within1": sum(bool(r.get("resume_step_within1")) for r in ir),
                            "coming_back_asked": sum(bool(r["coming_back_asked"]) for r in ir)}
    return out


def run(budget_usd: float = 1.0, workers: int = 2, only: list[str] | None = None, free: bool = False,
        run_name: str = RUN) -> dict:
    """free=True: no model calls at all (wiring check; local evidence + landmarks only)."""
    from concurrent.futures import ThreadPoolExecutor
    from ..experiments import _budget, make_verifier
    from .run_all import calibrators
    sp = [s for s in specs() if not only or s["id"] in only]
    st, ecfg = stack(), engine_cfg()
    budget = _budget(max_calls=5000, max_usd=budget_usd)
    ver = None if free else make_verifier("jev", budget)
    tc = None if free else make_verifier("openai:gpt-6.1-sol", budget)
    cals = {"primary": calibrators("jev"), "escalation": (None, None)}

    def one(s):
        return score(s, run_one(s, st, ecfg, ver, tc, cals, run_name))
    with ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(one, sp))
    for r in rows:
        print(json.dumps({k: r.get(k) for k in ("id", "step_acc_job_a", "switch_latency_s", "interruption_paused",
                                                 "resumed", "resume_step", "return_step_gt", "wrong_switches",
                                                 "task_checks", "cost_usd")}, default=float), flush=True)
    res = {"label": "SYNTHETIC multi-task sessions (spliced ENIGMA-51 repair videos); PROXY step labels (derived from "
                    "object interactions), not human step labels", "protocol": __doc__.strip(), "free": free,
           "aggregate": aggregate(rows), "rows": rows, "spend_usd": budget.usd, "calls": budget.calls}
    if not free:
        non_openai = 0.0          # tracked spend: OpenAI calls are counted from their cache; Jev is recorded here
        for s in sp:
            for x in read_log(RUNS / run_name / f"{s['id']}.jsonl"):
                if x["kind"] in ("verdict", "step_choice", "task_check") and not str(x.get("model", "")).startswith("gpt-"):
                    non_openai += (x.get("orig_cost_usd", x.get("cost_usd", 0.0)) or 0.0) if not x.get("cached") else 0.0
        res["spend_usd_non_openai"] = non_openai
    if not free:              # a free wiring check is not a result
        (RESULTS / "enigma51").mkdir(parents=True, exist_ok=True)
        (RESULTS / "enigma51" / f"{run_name}.json").write_text(json.dumps(res, indent=1, default=float))
    return res

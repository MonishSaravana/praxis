"""Step verification without the cooking event detector: leave checks (EngineConfig.leave_check), measured.

Why: on ENIGMA-51 repair video the L2 event detector (trained on CaptainCook4D) never fires (boundary scores <= 0.76
vs the 0.8 threshold, grasp <= 0.42 vs 0.6), and the only other completion-check trigger (hesitation) is pre-empted
by the "which step?" question whenever the belief is spread and then switched off by the hint for that step. So
repair steps were tracked but never checked. A leave check asks "is this step done?" about the step the belief is
leaving, which needs no detector.

Scoring (reads only run logs and reference labels):
  completion checks   verdicts asked by a completion trigger (boundary, grasp, hesitation, leave, schedule), each
                      with its final answer (the strong tier's when it escalated)
  verdict accuracy    the answer (calibrated P(complete) >= 0.5 = "done") against the reference at the check's time:
                      cooking = human step segments (done = the step's segment has ended); ENIGMA = PROXY segments
                      derived from object interactions (data/enigma51.py), order-aware for steps with no segment
  verified steps      "verified" pulses the wearer sees, and how many the reference agrees were done
  marked done         every commit (verified or not) and whether the reference says the step was done then

Runs: cooking TRAIN (24 v1 recordings, first 300 s, 3-fold stacks) task given and automatic (the chosen automatic
configuration, results/multitask/sol_fix_train.json C2), and the 4 ENIGMA repair videos on the company-backend
procedures (eval/enigma_backend.py). dry=True runs cache-only (a zero budget): free, and its misses estimate the cost.
"""
from __future__ import annotations

import copy
import json
from collections import Counter
from dataclasses import replace

from ..paths import RESULTS, RUNS, TASKGRAPHS
from ..runlog import by_kind, read_log

COMPLETION = ("boundary", "grasp", "hesitation", "leave", "schedule")
OUT = RESULTS / "verification"
SOL = "openai:gpt-6.1-sol"
VARIANTS = {                     # written before any run (2026-10-18)
    "V0": {},                                                       # the engine as it was
    "V1": {"leave_check": "commit"},                                # check the step at each implicit commit
    "V2": {"leave_check": "commit", "leave_gate": True},            # ... and the commit waits for the answer
    "V3": {"leave_check": "any", "leave_gate": True},               # ... and every leave of a step held >= 5 s
}
PROTOCOL = """Cooking TRAIN first (24 v1 recordings, first 300 s; 3-fold stacks; Jev answers checks, no strong tier).
Two modes: task given (single-task engine) and automatic (the chosen automatic configuration C2: multi-task engine,
gpt-6.1-sol answers "which task?"; single recordings and the 22 v1 train splices). A variant passes if, against V0 in
BOTH modes: step accuracy (single recordings; automatic also the splices) drops by at most 0.5 point, false alarms per
minute do not rise, and wrong task switches (automatic) do not rise. Among the variants that pass, the default is
the one with the most verified steps the human labels confirm (task given + automatic single recordings); ties -> the
fewer checks. If none passes, leave checks stay off. ENIGMA (repair) is then measured with V0 and the chosen variant:
the backend procedures, gpt-6.1-sol answering everything (as the backend run), PROXY labels."""


# ------------------------------------------------------------------------------------------- labels
def proxy_label(segs, ids):
    """ENIGMA: f(node, t) -> 1 done / 0 not done / None unknown, from derived PROXY segments [(start, end, node)]
    on a procedure in order. A step without a segment is done once a later step's segment has started, and not done
    while an earlier step's segment is still running."""
    sd = {s: (a, b) for a, b, s in segs}
    pos = {n: i for i, n in enumerate(ids)}

    def f(n, t):
        if n not in pos:
            return None
        if n in sd:
            return int(t >= sd[n][1])
        k = pos[n]
        if any(pos[s] > k and a <= t for a, b, s in segs):
            return 1
        if any(pos[s] < k and b > t for a, b, s in segs):
            return 0
        return None
    return f


def human_label(segs):
    """Cooking: done once the step's human segment has ended; unknown for a step not in the recording window."""
    sd = {s: (a, b) for a, b, s in segs}

    def f(n, t):
        return int(t >= sd[n][1]) if n in sd else None
    return f


# ------------------------------------------------------------------------------------------- scoring
def checks(recs: list[dict]) -> list[dict]:
    """Completion checks in a run log, each with its final answer."""
    ver = by_kind(recs, "verdict")
    out = []
    for i, v in enumerate(ver):
        if v["reason"] not in COMPLETION:
            continue
        fin = v
        nx = ver[i + 1] if i + 1 < len(ver) else None
        if nx and nx["reason"] == "escalation" and nx["t"] == v["t"] and nx["node"] == v["node"] and not nx.get("error"):
            fin = nx
        out.append({"t": v["t"], "node": v["node"], "reason": v["reason"], "p": fin.get("p_complete_cal"),
                    "error": fin.get("error"), "model": fin.get("model")})
    return out


def score(recs: list[dict], label, ids: set | None = None) -> dict:
    """Verification metrics of one run log against a reference label f(node, t)."""
    cs = [c for c in checks(recs) if ids is None or c["node"] in ids]
    ok = [c for c in cs if not c["error"] and c["p"] is not None]
    lab = [(c, label(c["node"], c["t"])) for c in ok]
    lab = [(c, y) for c, y in lab if y is not None]
    conf = Counter(("said_done" if c["p"] >= 0.5 else "said_not") + ("|done" if y else "|not_done") for c, y in lab)
    acts = [a for a in by_kind(recs, "action") if a["action"] == "verified" and (ids is None or a.get("node") in ids)]
    vy = [label(a["node"], a["t"]) for a in acts]
    com = [c for c in by_kind(recs, "commit") if ids is None or c["node"] in ids]
    cy = [label(c["node"], c["t"]) for c in com]
    return {"completion_checks": len(cs), "by_reason": dict(Counter(c["reason"] for c in cs)),
            "check_errors": len(cs) - len(ok), "labeled": len(lab),
            "verdict_accuracy": (conf["said_done|done"] + conf["said_not|not_done"]) / len(lab) if lab else None,
            "confusion": dict(conf),
            "verified": len(acts), "steps_verified": len({a["node"] for a in acts}),
            "verified_right": vy.count(1), "verified_wrong": vy.count(0), "verified_unknown": vy.count(None),
            "marked_done": len(com), "marked_done_right": cy.count(1), "marked_done_wrong": cy.count(0),
            "marked_done_by": dict(Counter(("checked_" if c.get("checked") else "") + c["reason"] for c in com)),
            "commits_held": len(by_kind(recs, "commit_held"))}


def total(rows: list[dict]) -> dict:
    keys = ("completion_checks", "check_errors", "labeled", "verified", "steps_verified", "verified_right",
            "verified_wrong", "verified_unknown", "marked_done", "marked_done_right", "marked_done_wrong",
            "commits_held")
    out = {k: sum(r[k] for r in rows) for k in keys}
    conf = Counter()
    for r in rows:
        conf.update(r["confusion"])
    out["confusion"] = dict(conf)
    out["verdict_accuracy"] = ((conf["said_done|done"] + conf["said_not|not_done"]) / out["labeled"]
                               if out["labeled"] else None)
    out["by_reason"] = dict(sum((Counter(r["by_reason"]) for r in rows), Counter()))
    return out


def misses(run: str) -> dict:
    """Calls a dry run could not answer from the cache (each would be a paid call), by kind."""
    n = Counter()
    for p in sorted((RUNS / run).glob("*.jsonl")):
        for r in read_log(p):
            e = str(r.get("error") or "")
            if "budget hit" in e:
                n[f"{r['kind']}:{r.get('model') or '?'}"] += 1
    return dict(n)


# ------------------------------------------------------------------------------------------- cooking TRAIN
def _c2() -> dict:
    return {**json.loads((RESULTS / "multitask" / "sol_fix_train.json").read_text())["base_overrides"], "switch_p": 0.9}


def _clip_label(clip, end: float):
    segs = [(s.start - clip.start, s.end - clip.start, s.step) for s in clip.segments if s.start - clip.start < end]
    return human_label(segs)


def train_given(name: str, overrides: dict, budget_usd: float, workers: int = 4, dry: bool = False) -> dict:
    """Task given, single-task engine (fused_oracle's configuration), Jev, no strong tier; 24 v1 train recordings,
    first 300 s, 3-fold stacks."""
    from concurrent.futures import ThreadPoolExecutor
    from ..experiments import _budget, make_verifier
    from . import harness
    from .multitask import fold_stack, train_recordings
    from .run_all import calibrators, engine_config
    base = harness.load_stack()
    ecfg = engine_config({"escalate": False, **overrides})
    budget = _budget(max_calls=0 if dry else 20000, max_usd=0.0 if dry else budget_usd)
    ver = make_verifier("jev", budget)
    cals = {"primary": calibrators("jev"), "escalation": (None, None)}
    stacks = {f: fold_stack(base, f) for f in range(3)}
    items = [(replace(c, end=min(c.end, 300.0)), f) for c, f in train_recordings(base["library"])]
    run = f"vc_given_{name}" + ("_dry" if dry else "")

    def one(it):
        c, f = it
        st = dict(stacks[f])
        st["recognizer"] = copy.deepcopy(stacks[f]["recognizer"])
        p = harness.run_clip(c, st, run, ecfg, ver, None, calibrators=cals, oracle_task=True)
        r = harness.score_clip(c, p)
        r["verification"] = score(read_log(p), _clip_label(c, c.end - c.start))
        return r
    with ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(one, items))
    res = {"label": "cooking TRAIN, task given (human step labels)", "name": name, "overrides": overrides, "dry": dry,
           "aggregate": harness.aggregate(rows), "verification": total([r["verification"] for r in rows]),
           "rows": rows, "spend_usd_non_openai": budget.usd, "calls": budget.calls,
           "misses": misses(run) if dry else None}
    _save(f"train_given_{name}" + ("_dry" if dry else ""), res)
    return res


def train_auto(name: str, overrides: dict, budget_usd: float, budget_openai_usd: float, workers: int = 4,
               dry: bool = False) -> dict:
    """Automatic, the chosen configuration C2 (multi-task engine; Jev; gpt-6.1-sol answers "which task?"; no strong
    tier): 24 v1 single recordings (first 300 s) + 22 v1 train splices, through multitask.run_set."""
    from ..data.cc4d import Clip, load_manifest
    from ..tasks.schema import TaskGraph
    from .multitask import run_set
    tag = "_dry" if dry else ""
    res = run_set("train", f"vc_auto_{name}", {**_c2(), **overrides}, 0.0 if dry else budget_usd, escalate=False,
                  workers=workers, task_checker=SOL, budget_openai_usd=0.0 if dry else budget_openai_usd, tag=tag)
    run = f"mt_vc_auto_{name}{tag}"
    man = load_manifest()
    clips = {c["clip_id"]: Clip.from_json(c) for c in man["train"]}
    vrows = []
    for r in res["single_task"]["rows"]:
        c = clips[r["clip"]]
        recs = read_log(RUNS / run / f"{c.clip_id}.jsonl")
        ids = set(TaskGraph.load(TASKGRAPHS / f"{c.task_id}.json").ids)
        v = score(recs, _clip_label(c, recs[-1]["t"]), ids)      # checks on the true recipe's steps only
        vrows.append({"clip": c.clip_id, **v})
    out = {"label": "cooking TRAIN, automatic (human step labels; verification on the single recordings)",
           "name": name, "overrides": overrides, "dry": dry, "run": run,
           "single_task": res["single_task"]["aggregate"], "single_wrong_switches": res["single_task"]["wrong_switches"],
           "splices": res["splices"]["aggregate"], "verification": total(vrows), "verification_rows": vrows,
           "spend_usd_main": res["spend_usd"], "spend_usd_openai": res["spend_usd_openai"],
           "misses": misses(run) if dry else None}
    _save(f"train_auto_{name}{tag}", out)
    return out


# ------------------------------------------------------------------------------------------- ENIGMA repair
def enigma(variants: dict[str, dict], openai_usd: float, dry: bool = False, vids=("141", "107", "144", "53")) -> dict:
    """The 4 ENIGMA repair videos on the company-backend procedures, set up as enigma_backend.run (task given by the
    assigned procedure, gpt-6.1-sol answers both questions, no strong tier), every variant on the same decoded frames.
    One Budget across all variants: a hard total cap. PROXY labels."""
    from types import SimpleNamespace
    from ..data import enigma51 as E
    from ..experiments import _budget, make_verifier
    from ..studio.org_session import runtime_library
    from . import enigma_backend as B
    from .enigma_eval import video_path
    from .harness import decode_frames, load_stack, run_clip
    from .run_all import calibrators, engine_config
    o = B._org()
    s = o.settings()
    graphs, evidence, _ = runtime_library(o, B.texts(), s["assigned"] if s["locked"] else None)
    st = {**load_stack(), "library": graphs, "evidence": evidence, "recognizer": None, "offtask": None}
    ob = _budget(max_calls=0 if dry else 20000, max_usd=0.0 if dry else openai_usd)
    ver = make_verifier(SOL, ob)
    cals = {"primary": calibrators(SOL), "escalation": (None, None)}
    ann = E.annotations()
    runs = {n: f"enigma_verify_{n}" + ("_dry" if dry else "") for n in variants}
    for vid in vids:
        tid = B.proc_for(vid)["task_id"]
        dur = float(ann["videos"][vid]["duration_seconds"])
        clip = SimpleNamespace(clip_id=f"enigma_{vid}", dataset="ENIGMA-51", task_id=tid, recording=vid,
                               video=str(video_path(vid)), start=0.0, end=dur, duration=dur, segments=[],
                               mistakes=lambda: [])
        frames = decode_frames(clip)
        for n, ov in variants.items():
            run_clip(clip, st, runs[n], engine_config({"escalate": False, **ov}), ver, None, oracle_task=True,
                     calibrators=cals, frames=frames)
            print("ran", vid, n, "openai so far", round(ob.usd, 4), flush=True)
        del frames
    return {n: score_enigma(n, runs[n], dry=dry, spend={"openai_usd_all_variants": ob.usd, "calls": ob.calls})
            for n in variants}


def score_enigma(name: str, run: str, dry: bool = False, spend: dict | None = None) -> dict:
    from ..data import enigma51 as E
    from . import enigma_backend as B
    gs = B._graphs()
    rows = []
    for vid in B.VIDEO_DOC:
        p = RUNS / run / f"enigma_{vid}.jsonl"
        if not p.exists():
            continue
        recs = read_log(p)
        g = gs[B.proc_for(vid)["id"]]
        inter = [x for x in E.interactions(vid) if x[0] <= recs[-1]["t"]]
        segs = E.derived_segments(g, inter)
        rows.append({"video": vid, "minutes": recs[-1]["t"] / 60, "proxy_steps": len(segs),
                     **score(recs, proxy_label(segs, g.ids))})
    tracking = B.score_runs(run)
    res = {"label": "ENIGMA-51 repair, company-backend procedures, gpt-6.1-sol; PROXY step labels from object "
                    "interactions (not human step labels)", "name": name, "run": run, "dry": dry,
           "verification": total(rows), "rows": rows, "tracking": tracking, "spend": spend,
           "misses": misses(run) if dry else None}
    _save(f"enigma_{name}" + ("_dry" if dry else ""), res)
    return res


def judge_shown(name: str, run: str, cap_usd: float, dry: bool = False, workers: int = 4) -> dict:
    """The 66 doc_value moments: the instruction on screen in `run`, judged blind (Opus) against the reference step of
    the SCRIPT-compiled graph, exactly as enigma_backend.judge_moments. Judge answers are cached by text, so a moment
    whose instruction didn't change costs nothing. dry: cache only (misses come back as "not_judged")."""
    from concurrent.futures import ThreadPoolExecutor
    from ..data import enigma51 as E
    from ..verify.common import Budget
    from .doc_value import ITEMS, _judge
    from .enigma_backend import VIDEO_DOC, _shown
    lib = E.library()
    items = json.loads((ITEMS / "items.json").read_text())
    jb = Budget(0 if dry else len(items) + 10, 0.0 if dry else cap_usd)
    logs = {v: read_log(RUNS / run / f"enigma_{v}.jsonl") for v in VIDEO_DOC if (RUNS / run / f"enigma_{v}.jsonl").exists()}
    base = {r["id"]: r for r in json.loads((RESULTS / "enigma51" / "backend_flow.json").read_text())["moments"]["rows"]}

    def one(it):
        if it["video"] not in logs:
            return {"id": it["id"], "video": it["video"], "grade": "not_run"}
        a = _shown(logs[it["video"]], it["t"])
        g = "no_answer"
        if a:
            try:
                g = _judge(jb, it, a["answer"], lib[it["task_id"]])["grade"]
            except Exception:  # noqa: BLE001  (dry run: not in the judge's cache)
                g = "not_judged"
        b = base.get(it["id"], {}).get("shown", {})
        return {"id": it["id"], "video": it["video"], "node": (a or {}).get("node"), "grade": g,
                "changed": (a or {}).get("answer") != b.get("answer"), "backend_grade": b.get("grade")}
    with ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(one, items))
    ran = [r for r in rows if r["grade"] != "not_run"]
    grades = [r["grade"] for r in ran]
    res = {"label": "same 66 moments as doc_value / backend_flow (PROXY reference steps); on-screen instruction of run "
                    f"{run}, judged blind by Opus 5.5", "name": name, "run": run, "dry": dry, "n": len(ran),
           **{k: grades.count(k) for k in ("correct", "adjacent", "wrong", "no_answer", "not_judged")},
           "changed_moments": sum(r["changed"] for r in ran),
           "backend_run": {k: [r["backend_grade"] for r in ran].count(k) for k in ("correct", "adjacent", "wrong")},
           "rows": rows, "spend_usd_non_openai": jb.usd}
    _save(f"enigma_shown_{name}" + ("_dry" if dry else ""), res)
    return res


def _save(stem: str, res: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{stem}.json").write_text(json.dumps(res, indent=1, default=float))

"""Compile one procedure from one section (paid: Claude Opus 5.5 through the existing L3 compiler), cached by the
section text's content hash, then attach knowledge cards (local) and SigLIP2 end-state embeddings (local).

Only that section's text is sent, never the whole document. Steps come from the manual's own numbering when it has
3-20 numbered steps (free); otherwise one small split call names them (the Studio split prompt). Every call checks
the backend budget against a worst-case cost first and records its real cost after.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil

import numpy as np

from ..verify.common import cost_usd
from .budget import LedgerBudget, backend_budget, estimate_tokens
from .cards import procedure_cards, safety_suggested, step_cards_aligned, step_cards_numbered
from .ingest import load_sections
from .sections import section_text, step_names
from .store import Org, now, read_json, slug, write_json

MODEL = "claude-opus-5-5"
MAX_SECTION_CHARS = 40000
# measured on Studio's one Opus 5.5 compile so far (sessions/library/user_548ff7ad579f.json, effort medium):
# 9 steps, 687 source chars -> 2291 input tokens, 5602 output tokens, $0.121; its split call cost $0.0056
OVERHEAD_IN, OUT_PER_STEP, OUT_BASE = 2000, 650, 500


def _section(org: Org, h: str, sid: str):
    lines, secs, _ = load_sections(org, h)
    sec = next((s for s in secs if s.id == sid), None)
    if sec is None:
        raise KeyError(f"no section {sid}")
    return lines, sec


def plan(org: Org, h: str, sid: str, effort: str = "medium") -> dict:
    """What compiling this section would send and cost, before anything is sent."""
    lines, sec = _section(org, h, sid)
    src = section_text(lines, sec)
    local = 3 <= len(sec.steps) <= 20 and sec.n_runs <= 1     # several numbered runs: let the split call name steps
    n = len(sec.steps) if local else int(min(max(len(src) / 400, 4), 15))
    src_tok = estimate_tokens(len(src))
    c_in, c_out = OVERHEAD_IN + src_tok + 15 * n, OUT_PER_STEP * n + OUT_BASE
    est = cost_usd(MODEL, c_in, c_out)
    s_in, s_out = (300 + src_tok, 700) if not local else (0, 0)
    est_split = cost_usd(MODEL, s_in, s_out)
    cached = (org.dir / "compile_cache" / f"{content_key(src, local and step_names(sec.steps), effort)}.json").exists()
    return {"section": sec.title, "pages": [sec.page_start, sec.page_end], "chars_sent": len(src),
            "doc_chars_total": sum(len(x.text) + 1 for x in lines), "steps_from": "manual numbering" if local else "split call (Opus 5.5, effort low)",
            "n_steps": n, "too_long": len(src) > MAX_SECTION_CHARS, "cached": cached,
            "estimate": {"split_usd": round(est_split, 4), "compile_usd": round(est, 4),
                         "total_usd": 0.0 if cached else round(est + est_split, 4),
                         "upper_usd": 0.0 if cached else round(1.5 * (est + est_split), 4),
                         "compile_tokens": {"input": c_in, "output": c_out}, "model": MODEL, "effort": effort},
            "preview": src[:1200]}


def content_key(src: str, steps, effort: str, domain: str = "maintenance") -> str:
    from ..tasks.compiler import PROMPT_VERSION
    return hashlib.sha256(json.dumps([PROMPT_VERSION, MODEL, effort, src, steps or None, domain]).encode()).hexdigest()[:20]


def proc_id_for(org: Org, h: str, sec_title: str) -> str:
    doc = org.doc_meta(h).get("doc_name", "doc")
    return slug(f"{doc}-{sec_title}", 58)


def compile_section(org: Org, h: str, sid: str, effort: str = "medium", texts=None, budget: LedgerBudget | None = None,
                    on_progress=None, proc_id: str | None = None, domain: str = "maintenance") -> tuple[str, int]:
    """Compile one section into a new (unapproved) version of its procedure. Returns (proc_id, version)."""
    from ..paths import load_env
    from ..tasks.compiler import compile_procedure
    load_env()
    budget = budget or backend_budget()
    say = on_progress or (lambda *_: None)
    lines, sec = _section(org, h, sid)
    src = section_text(lines, sec)
    if len(src) > MAX_SECTION_CHARS:
        raise ValueError(f"section is {len(src)} characters; pick a smaller section (max {MAX_SECTION_CHARS})")
    meta = org.doc_meta(h)
    local = 3 <= len(sec.steps) <= 20 and sec.n_runs <= 1     # several numbered runs: let the split call name steps
    steps = step_names(sec.steps) if local else None
    key = content_key(src, steps, effort, domain)
    cache_p = org.dir / "compile_cache" / f"{key}.json"
    pid = proc_id or proc_id_for(org, h, sec.title)
    task_id = f"org-{org.id}-{pid}"[:80]
    split_cost = 0.0
    hit = read_json(cache_p)
    if hit is not None:
        from ..tasks.schema import TaskGraph
        g = TaskGraph.model_validate(hit["graph"])
        steps, split_cost, cached = hit["steps"], 0.0, True
    else:
        cached = False
        src_tok = estimate_tokens(len(src))
        split_p = cache_p.with_suffix(".split.json")
        if steps is None and split_p.exists():               # split before, compile failed: don't pay twice
            steps = read_json(split_p)["steps"]
        if steps is None:
            from ..studio.tasks import _split_steps
            budget.ensure(cost_usd(MODEL, 300 + src_tok, 4000), "the step-split call")
            budget.check()
            say("splitting", 0)
            data, split_cost = _split_steps(src)
            budget.record_usd("split steps", MODEL, split_cost, org=org.id, detail={"section": sec.title})
            steps = [{"id": f"s{i + 1}", "name": n} for i, n in enumerate(data["steps"][:20])]
            write_json(split_p, {"steps": steps, "split": data, "cost_usd": split_cost, "created": now()})
            if len(steps) < 2:
                raise ValueError("couldn't find at least two steps in this section")
        budget.ensure(cost_usd(MODEL, int(1.3 * (OVERHEAD_IN + src_tok + 15 * len(steps))), 32000), "the compile call")
        budget.check()
        say("compiling", 0)
        try:
            g = compile_procedure(task_id, domain, src, steps, model=MODEL, effort=effort,
                                  source="", on_progress=lambda n: say("compiling", n))
        except RuntimeError as e:                            # a finished call that failed validation still cost money
            if getattr(e, "usage", None) is not None:
                budget.record_usd("compile procedure (failed: dropped steps)", MODEL, e.cost_usd, e.usage.input_tokens,
                                  e.usage.output_tokens, org=org.id, detail={"section": sec.title, "error": str(e)[:200]})
                write_json(cache_p.with_suffix(".failed.json"), {"error": str(e), "raw": e.raw, "steps": steps,
                                                                 "created": now()})
            raise
        c = g.compiler
        budget.record_usd("compile procedure", MODEL, c["cost_usd"], c["input_tokens"], c["output_tokens"], org=org.id,
                          detail={"section": sec.title, "latency_s": round(c["latency_s"], 1), "effort": effort})
        g.compiler["split_cost_usd"] = split_cost
        write_json(cache_p, {"graph": json.loads(g.model_dump_json()), "steps": steps, "created": now()})
    g.task_id = task_id
    pages = f"p. {sec.page_start}" + (f"–{sec.page_end}" if sec.page_end != sec.page_start else "")
    g.source = (f"{meta.get('filename')} (v{meta.get('version')}), section '{sec.title}'"
                + (f", {pages}" if meta.get("paged") else ""))
    say("cards", 0)
    cards = step_cards_numbered(lines, sec.steps) if local else step_cards_aligned(lines, sec, g.nodes)
    cards = {n.id: cards.get(n.id, []) for n in g.nodes}
    cards["_procedure"] = procedure_cards(lines, sec)
    review = {"safety": [], "safety_suggested": safety_suggested(cards, g.nodes), "notes": "", "edited": False}
    v = org.new_version(pid, g.title, {"doc_name": meta.get("doc_name"), "doc_hash": h, "doc_version": meta.get("version"),
                                       "section_id": sid, "section_title": sec.title,
                                       "pages": [sec.page_start, sec.page_end], "paged": bool(meta.get("paged")),
                                       "content_hash": key, "cached": cached,
                                       "cost_usd": 0.0 if cached else round(g.compiler.get("cost_usd", 0) + split_cost, 5),
                                       "steps_from": "manual numbering" if local else "split call",
                                       "chars_sent": len(src), "parent": None})
    g.compiler.update({"org": org.id, "proc_id": pid, "proc_version": v, "content_hash": key, "cached": cached})
    d = org.version_dir(pid, v)
    d.mkdir(parents=True, exist_ok=True)
    g.save(d / "graph.json")
    g.save(d / "graph.compiled.json")
    write_json(d / "cards.json", cards)
    write_json(d / "review.json", review)
    (d / "source.txt").write_text(src)
    if texts is not None:
        say("embedding", 0)
        embed_version(org, pid, v, texts)
    return pid, v


def embed_version(org: Org, pid: str, v: int, texts) -> None:
    from ..tasks.compiler import embed_graph
    from ..tasks.schema import TaskGraph
    d = org.version_dir(pid, v)
    emb = embed_graph(TaskGraph.load(d / "graph.json"), texts)
    np.savez(d / "emb.npz", **emb)


EDITABLE = ("name", "instruction_novice", "instruction_expert", "end_state", "view_hint")


def edit_version(org: Org, pid: str, v: int, edits: dict, texts=None) -> int:
    """Apply a manager's edits. An approved version is never changed: edits to it make a new draft version
    (parent = v). Returns the version that holds the edits."""
    from ..tasks.schema import Check, TaskGraph
    p = org.proc(pid)
    ver = next(x for x in p["versions"] if x["version"] == v)
    target = v
    if ver.get("approved"):
        target = org.new_version(pid, p["title"], {**{k: x for k, x in ver.items() if k not in
                                                      ("version", "created", "approved", "approved_at", "approved_by")},
                                                   "parent": v, "cached": True, "cost_usd": 0.0, "edited_from": v})
        shutil.copytree(org.version_dir(pid, v), org.version_dir(pid, target), dirs_exist_ok=True)
    d = org.version_dir(pid, target)
    g = TaskGraph.load(d / "graph.json")
    cards = read_json(d / "cards.json", {})
    review = read_json(d / "review.json", {})
    changed_text = False
    for nid, ne in (edits.get("nodes") or {}).items():
        n = next((x for x in g.nodes if x.id == nid), None)
        if n is None:
            continue
        for k in EDITABLE:
            if k in ne and isinstance(ne[k], str) and ne[k].strip() != getattr(n, k):
                setattr(n, k, ne[k].strip()[:500])
                changed_text |= k in ("name", "end_state")
        if isinstance(ne.get("checks"), list):
            qs = [q.strip()[:300] for q in ne["checks"] if isinstance(q, str) and q.strip()]
            old = {c.question: c for c in n.checks}
            n.checks = [old.get(q) or Check(id=f"{nid}c{i + 1}", question=q, kind="completion") for i, q in enumerate(qs)]
    if isinstance(edits.get("title"), str) and edits["title"].strip():
        g.title = edits["title"].strip()[:120]
    for nid, cs in (edits.get("cards") or {}).items():
        if nid in cards and isinstance(cs, list):
            cards[nid] = [c for c in cs if isinstance(c, dict) and c.get("text")]
    if isinstance(edits.get("safety"), list):
        review["safety"] = [x for x in edits["safety"] if x in g.ids]
    if isinstance(edits.get("notes"), str):
        review["notes"] = edits["notes"][:2000]
    review["edited"] = True
    g.compiler["proc_version"] = target
    g.save(d / "graph.json")
    write_json(d / "cards.json", cards)
    write_json(d / "review.json", review)
    if changed_text or target != v:
        if texts is not None:
            embed_version(org, pid, target, texts)
        elif changed_text and (d / "emb.npz").exists():
            (d / "emb.npz").unlink()             # stale: recomputed when the procedure is next loaded with an encoder
    return target


def find_section_like(org: Org, h: str, title: str) -> str | None:
    """The section in a (new) document version whose title matches an old one (for recompiling after a revision)."""
    _, secs, _ = load_sections(org, h)
    norm = lambda s: re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()       # noqa: E731
    exact = [s for s in secs if norm(s.title) == norm(title)]
    if exact:
        return exact[0].id
    bare = lambda s: re.sub(r"^[0-9. ]+", "", norm(s))                    # noqa: E731
    loose = [s for s in secs if bare(s.title) == bare(title) and bare(title)]
    return loose[0].id if loose else None


def refresh_cards(org: Org, pid: str, v: int, force: bool = False) -> dict:
    """Re-extract one version's knowledge cards from its source section (local, $0), keeping manual edits out of
    it: only for versions not edited by hand. Safety flags a manager set are kept."""
    from ..tasks.schema import TaskGraph
    p = org.proc(pid)
    info = next(x for x in p["versions"] if x["version"] == v)
    d = org.version_dir(pid, v)
    review = read_json(d / "review.json", {})
    if review.get("edited") and not force:
        raise ValueError("this version was edited by hand; its cards are kept")
    lines, sec = _section(org, info["doc_hash"], info["section_id"])
    g = TaskGraph.load(d / "graph.json")
    local = info.get("steps_from") == "manual numbering"
    cards = step_cards_numbered(lines, sec.steps) if local else step_cards_aligned(lines, sec, g.nodes)
    cards = {n.id: cards.get(n.id, []) for n in g.nodes}
    cards["_procedure"] = procedure_cards(lines, sec)
    review["safety_suggested"] = safety_suggested(cards, g.nodes)
    write_json(d / "cards.json", cards)
    write_json(d / "review.json", review)
    return cards

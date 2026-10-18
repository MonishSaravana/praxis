"""Questions during a job ("what's the torque?", "why do I close the valve first?").

1. The current step's knowledge cards first: a spec, part, warning, tool or figure question that a card answers is
   answered locally from the card's quote with its page ($0, no network).
2. Otherwise retrieve the top-k chunks from the company's local index and send only those excerpts plus the current
   step to Claude, which must answer from them, cite the excerpt ids, or say the documents don't cover it.
3. Answers are cached by (question, step, excerpts, model). With no key or no budget left, the excerpts themselves
   are returned with their pages instead of a model answer.
"""
from __future__ import annotations

import hashlib
import json
import re
import time

from .budget import LedgerBudget, backend_budget, estimate_tokens
from .ingest import searcher
from .store import Org, now, read_json, write_json

QA_VERSION = "qa-v1"
SYSTEM = """You answer a maintenance technician's question in the middle of a job, for Praxis, a hands-free coach that
speaks through smart glasses. Use only the numbered excerpts from the company's own documents and the current step.
- Answer in one or two short spoken sentences (at most 40 words). For a spec, say the number and unit first.
- List the ids of the excerpts you used.
- If the excerpts do not contain the answer, set answerable to false and say the company's documents don't cover it
  and to check with a supervisor. Never guess a spec, torque, part number or safety step."""
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["answer", "used", "answerable"],
          "properties": {"answer": {"type": "string"}, "used": {"type": "array", "items": {"type": "string"}},
                         "answerable": {"type": "boolean"}}}
INTENTS = [
    (re.compile(r"\b(torque|tighten|how tight|n\s*·?\s*m|ft[\s.-]*lbs?)\b", re.I), ("spec", "torque")),
    (re.compile(r"\b(pressure|psi|bar)\b", re.I), ("spec", "pressure")),
    (re.compile(r"\b(temperature|temp|how hot)\b", re.I), ("spec", "temperature")),
    (re.compile(r"\b(how much|volume|capacity|litres?|liters?|quarts?)\b", re.I), ("spec", "volume")),
    (re.compile(r"\b(gap|clearance|how (?:far|deep|long)|dimension|mm)\b", re.I), ("spec", "dimension")),
    (re.compile(r"\b(voltage|volts?|amps?|current)\b", re.I), ("spec", "electrical")),
    (re.compile(r"\b(part (?:number|no)|p/?n|which part|what part|order)\b", re.I), ("part", "")),
    (re.compile(r"\b(warning|danger|caution|safe|safety|lock ?out|tag ?out|loto|hazard)\b", re.I), ("warning|safety", "")),
    (re.compile(r"\b(tools?|socket|wrench|spanner|what do i need)\b", re.I), ("tool", "")),
    (re.compile(r"\b(figure|diagram|picture|drawing)\b", re.I), ("figure", "")),
]


def card_answer(question: str, step: dict | None, paged: bool = True) -> dict | None:
    """A local answer from the current step's cards, or None if no card fits the question."""
    if not step:
        return None
    cards = list(step.get("cards") or []) + list(step.get("procedure_cards") or [])
    for rx, (kinds, label) in INTENTS:
        if not rx.search(question):
            continue
        hits = [c for c in cards if c["kind"] in kinds.split("|") and (not label or c["label"].startswith(label))]
        if hits:
            c = hits[0]
            where = f"page {c['page']}" if paged and c.get("page") else "the procedure"
            head = c["label"].split(": ", 1)[-1] if c["kind"] == "spec" else ""
            text = (f"{head}. " if head else "") + f"The manual says: {c['text']}"
            return {"answer": text, "source": "card", "cost_usd": 0.0, "cached": False, "answerable": True,
                    "citations": [{"page": c.get("page"), "label": c["label"], "where": where}], "latency_ms": 0}
    return None


def answer(org: Org, question: str, step: dict | None = None, k: int = 5, model: str | None = None,
           effort: str = "low", budget: LedgerBudget | None = None, mode: str | None = None, query_emb=None,
           allow_model: bool = True) -> dict:
    """step: {"task": title, "name", "instruction", "cards": [...], "procedure_cards": [...], "doc": hash} or None."""
    t0 = time.perf_counter()
    q = " ".join(question.split())[:500]
    if not q:
        raise ValueError("empty question")
    docs = {d["current"]: d for d in org.documents() if d["current"]}
    paged = True
    if step and step.get("doc") in docs:
        paged = bool(org.doc_meta(step["doc"]).get("paged"))
    local = card_answer(q, step, paged)
    if local:
        local["latency_ms"] = round(1000 * (time.perf_counter() - t0), 1)
        return local
    settings = org.settings()
    model = model or settings.get("qa_model", "claude-opus-5-5")
    mode = mode or settings.get("retrieval", "bm25")
    query = q + (f" {step['name']}" if step and step.get("name") else "")
    hits = searcher(org).search(query, k=k, mode=mode, query_emb=query_emb)
    cites = {h["id"]: _cite(h, docs, org) for h in hits}
    if not hits:
        return {"answer": "I couldn't find anything about that in the company's documents.", "source": "none",
                "citations": [], "cost_usd": 0.0, "cached": False, "answerable": False,
                "latency_ms": round(1000 * (time.perf_counter() - t0), 1)}
    excerpts = "\n\n".join(f"[{h['id']}] ({cites[h['id']]['where']}; {h['section_path']})\n{h['text']}" for h in hits)
    stepline = ""
    if step:
        stepline = (f"Current task: {step.get('task', '')}\nCurrent step: {step.get('name', '')}"
                    f"\nStep instruction: {step.get('instruction', '')}\n\n")
    user = f"{stepline}Excerpts:\n{excerpts}\n\nQuestion: {q}"
    key = hashlib.sha256(json.dumps([QA_VERSION, model, effort, user]).encode()).hexdigest()[:24]
    cache_p = org.dir / "qa_cache" / f"{key}.json"
    hit = read_json(cache_p)
    base = {"excerpts": [{"id": h["id"], **cites[h["id"]], "text": h["text"][:400]} for h in hits], "query": query,
            "question": q, "mode": mode}
    if hit is not None:
        return {**hit, **base, "cached": True, "cost_usd": 0.0, "latency_ms": round(1000 * (time.perf_counter() - t0), 1)}
    if not allow_model:
        return _excerpt_answer(hits, cites, base, t0, "model calls are off")
    budget = budget or backend_budget()
    from ..paths import load_env
    load_env()
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _excerpt_answer(hits, cites, base, t0, "no Claude key")
    from ..verify.common import BudgetExceeded, cost_usd
    try:
        budget.ensure(cost_usd(model, estimate_tokens(len(SYSTEM) + len(user)) + 50, 1500), "this question")
        budget.check()
    except BudgetExceeded as e:
        return _excerpt_answer(hits, cites, base, t0, str(e))
    import anthropic
    client = anthropic.Anthropic(timeout=60, max_retries=1)
    resp = client.messages.create(model=model, max_tokens=1500, system=SYSTEM,
                                  messages=[{"role": "user", "content": user}],
                                  output_config={"format": {"type": "json_schema", "schema": SCHEMA}, "effort": effort})
    usd = budget.record("question", model, resp.usage, org=org.id, detail={"question": q[:120], "effort": effort})
    if resp.stop_reason == "refusal":
        return _excerpt_answer(hits, cites, base, t0, "the model declined")
    data = json.loads(next(b.text for b in resp.content if b.type == "text"))
    used = [u for u in data["used"] if u in cites]
    out = {"answer": data["answer"].strip(), "answerable": bool(data["answerable"]), "source": "model",
           "citations": [cites[u] for u in used], "model": model, "effort": effort, "created": now(),
           "input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens, "orig_cost_usd": usd,
           "orig_latency_ms": round(1000 * (time.perf_counter() - t0), 1)}
    write_json(cache_p, out)
    return {**out, **base, "cached": False, "cost_usd": usd, "latency_ms": out["orig_latency_ms"]}


def _cite(h: dict, docs: dict, org: Org) -> dict:
    d = docs.get(h["doc"]) or {}
    meta = org.doc_meta(h["doc"])
    title = d.get("title") or meta.get("filename") or "document"
    if meta.get("paged"):
        pg = f"p. {h['page_start']}" + (f"–{h['page_end']}" if h["page_end"] != h["page_start"] else "")
        where = f"{title}, {pg}"
    else:
        where = f"{title}, § {h['section_path'].split(' › ')[-1]}"
    return {"doc": h["doc"], "title": title, "page": h["page_start"] if meta.get("paged") else None,
            "page_end": h["page_end"] if meta.get("paged") else None, "section": h["section_path"], "where": where}


def _excerpt_answer(hits, cites, base, t0, why: str) -> dict:
    """No model: quote the line of the top excerpts that shares the most words with the question, with its page."""
    from .index import tokens
    q = set(tokens(base.get("question") or base.get("query", ""), expand=True))     # the question, not the step name
    best, best_s, best_h = "", -1.0, hits[0]
    for rank, h in enumerate(hits[:3]):
        for ln in h["text"].split("\n"):
            s = len(q & set(tokens(ln))) - 0.3 * rank
            if s > best_s and len(ln) > 12:
                best, best_s, best_h = ln, s, h
    return {"answer": f"The documents say: {best[:300]}", "source": "excerpt", "why_no_model": why,
            "answerable": None, "citations": [cites[best_h["id"]]], "cost_usd": 0.0, "cached": False, **base,
            "latency_ms": round(1000 * (time.perf_counter() - t0), 1)}

"""Knowledge cards: short facts quoted from the procedure's own section, attached to each compiled step (specs,
warnings, part numbers, tools, figure and page references). Extracted locally with patterns, never written by a
model, so every card is a verbatim quote with its page. The live engine and the question box read these cards; they
never read the document.

Alignment: when the compiler's steps are the manual's own numbered steps (s4 = step 4), each step's cards come from
that step's lines and the warnings just before it. Otherwise each compiled step is matched to the best few lines of
the section by BM25 over the step's name, instructions and parts.
"""
from __future__ import annotations

import re

from .index import BM25, tokens
from .sections import ADMONITION, Line, Section, Step

NUM = r"(?<![\d/.])\d+(?:/\d+)?(?:[.,]\d+)?(?:\s*(?:-|–|to|±|\+/-)\s*\d+(?:/\d+)?(?:[.,]\d+)?)?"
SPECS = [
    ("torque", re.compile(rf"{NUM}\s*(?:N\s*[·.\-]?\s*m|Nm|kgf?\s*[·.\-]?\s*m|(?:ft|in)\s*[·.\-]?\s*lb[sf]?|lb[sf]?\s*[·.\-]?\s*(?:ft|in))\b", re.I)),
    ("pressure", re.compile(rf"{NUM}\s*(?:psi[ag]?|bar|kPa|MPa|inHg|mmHg)\b", re.I)),
    ("temperature", re.compile(rf"-?{NUM}\s*°\s*[CF]\b|-?{NUM}\s*deg(?:rees)?\s*[CF]\b", re.I)),
    ("electrical", re.compile(rf"{NUM}\s*(?:V(?:AC|DC)?|A|mA|kW|W|Hz|Ω|ohms?|kV|[Vv]olts?|[Aa]mps?)\b")),
    ("volume", re.compile(rf"{NUM}\s*(?:L|l|litres?|liters?|ml|mL|qt|quarts?|gal(?:lons?)?|fl\.?\s*oz)\b")),
    ("dimension", re.compile(rf"{NUM}[\s-]*(?:mm|cm|in\.|inch(?:es)?|thou|µm)(?![a-z])", re.I)),
    ("angle", re.compile(rf"{NUM}[\s-]*(?:degrees?|deg\.?)(?!\s*[CF]\b)|{NUM}\s*°(?!\s*[CF]\b)", re.I)),
    ("interval", re.compile(rf"(?:every\s+)?{NUM}\s*(?:hours?|hrs?|operating hours|months?|cycles)\b", re.I)),
]
PART = re.compile(r"(?:P/N|Part\s*(?:No\.?|Number|#)|PN|Kit)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-./]{2,})", re.I)
FIGURE = re.compile(r"\b(?:Fig(?:ure)?|Table|Diagram)\.?\s*\d+(?:[-.]\d+)?[A-Za-z]?\b", re.I)
TOOLS = re.compile(r"^(?:special\s+)?(?:tools?|equipment|materials?|parts)\s*(?:required|needed)?\s*:", re.I)
SAFETY = re.compile(r"\b(lock\s*-?\s*out|tag\s*-?\s*out|LOTO|de-?energi[sz]\w*|isolat\w+ (?:the )?(?:power|supply|energy)|"
                    r"zero energy|stored energy|disconnect (?:the )?(?:power|supply|battery)|depressuri[sz]\w*|"
                    r"bleed (?:off )?(?:the )?pressure|arc flash|hot surface|confined space|PPE|safety glasses|"
                    r"face shield|gloves|high voltage|electric(?:al)? shock|crush|pinch point|fall protection)\b", re.I)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?;])\s+", text) if s.strip()]


def extract(text: str, page: int, max_len: int = 220) -> list[dict]:
    """Cards found in one passage. Each card: kind, label, text (a verbatim quote, trimmed), page."""
    cards: list[dict] = []
    seen: set[tuple] = set()
    num = re.match(r"^\s*(?:step\s+)?(\d{1,3})\s*[.):]\s+", text, re.I)    # the manual's own step number, if any
    if num:
        text = text[num.end():]

    def add(kind, label, quote):
        q = quote.strip()
        q = q if len(q) <= max_len else q[: max_len - 1].rsplit(" ", 1)[0] + "…"
        key = (kind, label.lower(), q.lower())
        if key not in seen:
            seen.add(key)
            c = {"kind": kind, "label": label, "text": q, "page": page}
            if num:
                c["step_no"] = int(num.group(1))
            cards.append(c)

    for sent in _sentences(text):
        if ADMONITION.match(sent):
            add("warning", ADMONITION.match(sent).group(1).upper(), sent)
            continue
        if TOOLS.match(sent):                   # "Tools required: 10 mm socket" is a tool list, not a spec
            add("tool", "tools", sent)
            continue
        for name, rx in SPECS:
            for m in rx.finditer(sent):
                kind = "temperature" if name == "angle" and re.search(r"temperature|heat|iron|oven|°", sent, re.I) else name
                add("spec", f"{kind}: {m.group(0).strip()}", sent)
        for m in PART.finditer(sent):
            add("part", f"part {m.group(1).rstrip('.,)')}", sent)
        for m in FIGURE.finditer(sent):
            add("figure", re.sub(r"(?i)^fig(?:ure)?\.?\s*", "Figure ", m.group(0)), sent)
        if SAFETY.search(sent) and not any(c["kind"] == "warning" and c["text"] == sent for c in cards):
            add("safety", SAFETY.search(sent).group(0).lower(), sent)
    return cards


def procedure_cards(lines: list[Line], sec: Section) -> list[dict]:
    """Cards that apply to the whole procedure: tools/parts lists and warnings before the first step."""
    end = sec.steps[0].line_start if sec.steps else sec.line_end
    out = []
    for i in range(sec.line_start, end):
        out += extract(lines[i].text, lines[i].page)
    return _dedupe(out)


def step_cards_numbered(lines: list[Line], steps: list[Step]) -> dict[str, list[dict]]:
    """Cards per compiled step when the steps are the manual's own numbering (s<n>)."""
    out: dict[str, list[dict]] = {}
    for st in steps:
        cs = []
        for note in st.notes:
            cs += extract(note, st.page)
        cs += extract(st.text, st.page)
        for i in range(st.line_start + 1, st.line_end):          # warnings / notes inside the step
            if ADMONITION.match(lines[i].text):
                cs += extract(lines[i].text, lines[i].page)
        cs.append({"kind": "source", "label": f"manual step {st.n}", "text": st.text[:220], "page": st.page})
        out[f"s{st.n}"] = _dedupe(cs)
    return out


def step_cards_matched(lines: list[Line], sec: Section, nodes: list, win: int = 3) -> dict[str, list[dict]]:
    """Cards per compiled step by matching each step to its best window of the section's lines (no numbering)."""
    idx = list(range(sec.line_start, sec.line_end))
    if not idx:
        return {}
    windows = [idx[i:i + win] for i in range(0, len(idx), 1)]
    bm = BM25([tokens(" ".join(lines[j].text for j in w)) for w in windows])
    out: dict[str, list[dict]] = {}
    for n in nodes:
        q = " ".join([n.name, n.instruction_novice, " ".join(n.parts)])
        s = bm.scores(tokens(q, expand=True))
        if not len(s) or s.max() <= 0:
            out[n.id] = []
            continue
        best = list(windows[int(s.argmax())])
        while best[-1] + 1 < sec.line_end and not lines[best[-1]].text.rstrip().endswith((".", ":", ";", "!", "?")) \
                and len(best) < win + 2:          # finish the sentence the window cuts off
            best.append(best[-1] + 1)
        cs = []
        lo = best[0]
        if lo - 1 >= sec.line_start and ADMONITION.match(lines[lo - 1].text):
            cs += extract(lines[lo - 1].text, lines[lo - 1].page)
        for j in best:
            cs += extract(lines[j].text, lines[j].page)
        cs.append({"kind": "source", "label": "matched passage", "page": lines[best[0]].page,
                   "text": " ".join(lines[j].text for j in best)[:220]})
        out[n.id] = _dedupe(cs)
    return out


def step_cards_aligned(lines: list[Line], sec: Section, nodes: list) -> dict[str, list[dict]]:
    """Cards per compiled step when the compiler's steps group or rename the manual's lines: split the section's lines
    into one contiguous span per step, in order (both follow the manual's order), maximizing each line's BM25 match to
    its step's name, instructions and parts. Every line lands in exactly one step, so a merged step keeps all its specs."""
    import numpy as np
    from .video import align
    idx = [i for i in range(sec.line_start, sec.line_end)]
    if not idx or not nodes:
        return {}
    bm = BM25([tokens(lines[i].text) for i in idx])
    sim = np.zeros((len(nodes), len(idx)))
    for k, n in enumerate(nodes):
        sc = bm.scores(tokens(" ".join([n.name, n.instruction_novice, " ".join(n.parts), " ".join(n.substeps)]), expand=True))
        sim[k] = sc / (sc.max() or 1.0)
    out: dict[str, list[dict]] = {}
    for n, (a, b) in zip(nodes, align(sim)):
        cs = []
        if a > 0 and ADMONITION.match(lines[idx[a - 1]].text):
            cs += extract(lines[idx[a - 1]].text, lines[idx[a - 1]].page)
        for j in range(a, b):
            cs += extract(lines[idx[j]].text, lines[idx[j]].page)
        span = " ".join(lines[idx[j]].text for j in range(a, b))
        cs.append({"kind": "source", "label": f"source lines {a + 1}–{b}", "page": lines[idx[a]].page, "text": span[:220]})
        out[n.id] = _dedupe(cs)
    return out


def safety_suggested(cards: dict[str, list[dict]], nodes: list) -> list[str]:
    """Steps to suggest as safety-critical: a DANGER/WARNING card or safety wording in the step or its cards.
    Only a suggestion; a manager confirms it on the admin page."""
    out = []
    for n in nodes:
        cs = cards.get(n.id, [])
        text = " ".join([n.name, n.instruction_novice] + [c["text"] for c in cs])
        if any(c["kind"] == "warning" and c["label"] in ("WARNING", "DANGER") for c in cs) or SAFETY.search(text):
            out.append(n.id)
    return out


def _dedupe(cs: list[dict]) -> list[dict]:
    seen, out = set(), []
    for c in cs:
        k = (c["kind"], c["label"].lower(), "" if c["kind"] == "figure" else c["text"].lower())   # one card per figure
        if k not in seen:
            seen.add(k)
            out.append(c)
    return out


def card_line(c: dict, paged: bool = True, section: str = "") -> str:
    """One card as a short spoken/printed line with its citation."""
    where = f"page {c['page']}" if paged and c.get("page") else (section or "the procedure")
    return f"{c['text']} ({where})"

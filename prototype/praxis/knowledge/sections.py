"""Section map and procedure finder, local heuristics only (no model call).

Lines -> running headers/footers removed -> headings (PDF bookmarks, numbered headings like "4.2 Replacing the
filter", "Chapter 3", Markdown "#", short ALL-CAPS lines) -> a section tree (a section runs to the next heading at
its level or above) -> numbered step runs ("1. Close the valve.", "Step 2: ...") -> procedure candidates, scored.
A manager can still compile any section; the score only orders the list.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field

ADMONITION = re.compile(r"^(warning|caution|danger|note|important|notice)\b[\s:!.\-–]*", re.I)
NUM_HEAD = re.compile(r"^(?P<num>(?:\d{1,2}\.){0,3}\d{1,2})\.?\s+(?P<title>[A-Z][^\n]{1,90})$")
KEY_HEAD = re.compile(r"^(?P<kw>chapter|section|part|appendix|procedure|task)\s+(?P<num>[0-9A-Z]{1,4}(?:[.\-][0-9]{1,3})*)"
                      r"\b[\s:.\-–]*(?P<title>.{0,90})$", re.I)
MD_HEAD = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>.+?)\s*#*$")
TOC_LINE = re.compile(r"^(?P<title>.+?)\s*(?:\.{3,}|…+|(?:\.\s){3,})\s*(?P<page>\d{1,4})$")
STEP = re.compile(r"^(?:step\s+)?(?P<n>\d{1,2})\s*[.):]\s+(?P<text>\S.*)$", re.I)
SUBSTEP = re.compile(r"^(?:[a-h]|i{1,3}|iv|v)[.)]\s+\S", re.I)
KW_LEVEL = {"chapter": 1, "part": 1, "appendix": 1, "section": 2, "procedure": 3, "task": 3}
VERBS = set("""remove install disconnect connect loosen tighten torque check inspect clean replace turn open close lift lower
apply align insert slide push pull set adjust measure verify ensure drain fill refill lubricate mount unscrew screw attach
detach release lock unlock place position secure rotate press hold wipe record start stop shut isolate test reinstall
reconnect bleed prime purge grease cut mark route fasten unfasten tag use make allow wait repeat confirm locate identify
switch power energize de-energize reassemble disassemble refit fit retighten unbolt bolt clamp unclamp support raise
take put pour flush blow inspect operate run observe note select engage disengage depress pump vent seal reset
read top determine notify obtain submit sign date coordinate prepare log issue review discuss perform inform contact
request schedule document attach hang tighten loosen zero rotate mount shim adjust""".split())
PROC_WORDS = re.compile(r"\b(replac\w*|remov\w*|install\w*|procedure|adjust\w*|inspect\w*|maintenance|servic\w*|lubricat\w*|"
                        r"repair\w*|disassembl\w*|assembl\w*|clean\w*|chang\w*|calibrat\w*|start-?up|shut-?down|lockout|"
                        r"bleed\w*|drain\w*|fill\w*|overhaul\w*|tension\w*|align\w*|test\w*|check\w*)\b", re.I)


@dataclass
class Line:
    page: int
    text: str


@dataclass
class Step:
    n: int
    text: str
    line_start: int
    line_end: int                   # exclusive
    page: int
    notes: list[str] = field(default_factory=list)   # WARNING / CAUTION / NOTE lines just before or inside the step


@dataclass
class Section:
    id: str
    title: str
    num: str
    level: int
    line_start: int                 # the heading line (inclusive)
    line_end: int                   # exclusive: the next heading at this level or above
    page_start: int
    page_end: int
    parent: str | None = None
    path: list[str] = field(default_factory=list)
    n_chars: int = 0
    n_runs: int = 0                 # numbered runs this section holds (2+: the manual's numbering restarts)
    steps: list[Step] = field(default_factory=list)
    proc_score: float = 0.0
    why: str = ""

    def as_dict(self, with_steps: bool = True) -> dict:
        d = asdict(self)
        if not with_steps:
            d.pop("steps")
        d["n_steps"] = len(self.steps)
        return d


def to_lines(pages: list[str]) -> tuple[list[Line], list[str]]:
    """All non-empty lines with their page, minus running headers/footers (a line, digits ignored, that repeats on
    at least 40% of pages, when there are 4+ pages). Returns (lines, boilerplate patterns removed)."""
    norm = lambda s: re.sub(r"\d+", "#", s.strip().lower())     # noqa: E731
    per_page = [[ln.strip() for ln in p.split("\n") if ln.strip()] for p in pages]
    boiler: set[str] = set()
    if len(pages) >= 4:
        cnt = Counter(k for pl in per_page for k in {norm(x) for x in pl})
        boiler = {k for k, c in cnt.items() if c >= max(3, 0.4 * len(pages)) and len(k) < 120}
        boiler.discard("#")
    out = []
    for i, pl in enumerate(per_page):
        for x in pl:
            if norm(x) in boiler or re.fullmatch(r"(page\s*)?\d{1,4}(\s*(of|/)\s*\d{1,4})?", x, re.I):
                continue
            out.append(Line(page=i + 1, text=x))
    return out, sorted(boiler)


def _words(s: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z\-']*", s)


def _looks_title(title: str) -> bool:
    w = [x for x in _words(title) if len(x) > 3]
    if not w:
        return False
    caps = sum(x[0].isupper() for x in w) / len(w)
    return caps >= 0.6 or title.upper() == title


def heading_of(text: str) -> tuple[int, str, str] | None:
    """(level, number, title) if the line looks like a heading, else None."""
    s = text.strip()
    if not (2 <= len(s) <= 100) or TOC_LINE.match(s) or ADMONITION.match(s):
        return None
    m = MD_HEAD.match(s)
    if m:
        return len(m.group("hashes")), "", m.group("title").strip()
    m = KEY_HEAD.match(s)
    if m and (not m.group("title") or m.group("title")[:1].isupper()):
        return KW_LEVEL[m.group("kw").lower()], m.group("num"), s
    m = NUM_HEAD.match(s)
    if m:
        num, title = m.group("num"), m.group("title").strip()
        words = _words(title)
        if title[-1] in ".,;" or len(words) > 10 or not any(len(w) >= 3 for w in words):
            return None
        if "." not in num:                      # "3 Maintenance" vs "3 Remove the cover"
            if words and words[0].lower() in VERBS or not _looks_title(title):
                return None
        if title.upper() == title and len(title) > 3:
            title = title.title()
        return num.count(".") + 1, num, f"{num} {title}"
    w = _words(s)
    letters = sum(c.isalpha() for c in s)
    if 1 <= len(w) <= 8 and letters >= 4 and s.upper() == s and letters / len(s) > 0.6 and not s.endswith("."):
        return 2, "", s.title() if len(s) > 3 else s
    return None


def find_steps(lines: list[Line], start: int, end: int, heads: set[int]) -> list[list[Step]]:
    """Numbered step runs inside [start, end): a run starts at 1 and counts up; wrapped lines and lettered sub-steps
    join the current step; a WARNING/NOTE line is attached to the step it precedes (or is inside)."""
    runs: list[list[Step]] = []
    cur: list[Step] = []
    pending: list[list] = []                    # [line idx, text] of warnings not yet attached to a step
    gap = 0
    for i in range(start, end):
        if i in heads:
            if cur:
                runs.append(cur)
            cur, pending, gap = [], [], 0
            continue
        s = lines[i].text
        m = STEP.match(s) if not re.search(r"\.{5,}|…{2,}", s) else None       # a table-of-contents line is not a step
        if m:
            n = int(m.group("n"))
            if n == 1 or (cur and n == cur[-1].n + 1):
                if n == 1 and cur:
                    runs.append(cur)
                    cur = []
                if cur:
                    cur[-1].line_end = i
                notes = [t for j, t in pending if i - j <= 8]
                cur.append(Step(n=n, text=m.group("text").strip(), line_start=i, line_end=i + 1, page=lines[i].page,
                                notes=notes))
                pending, gap = [], 0
                continue
        if ADMONITION.match(s):
            pending.append([i, s])
            gap += 1
            continue
        if pending and i - pending[-1][0] == 1 and not heading_of(s):   # a warning wrapped onto the next line
            pending[-1] = [i, (pending[-1][1] + " " + s)[:400]]
            gap += 1
            continue
        if cur:
            gap += 1
            if gap > 12:
                runs.append(cur)
                cur, pending, gap = [], [], 0
                continue
            wrapped = not cur[-1].text.rstrip().endswith((".", "!", "?", ":", ")")) or s[:1].islower()
            if SUBSTEP.match(s) or (wrapped and len(cur[-1].text) < 600 and not heading_of(s)):
                cur[-1].text = (cur[-1].text + " " + s)[:900]
                cur[-1].line_end = i + 1
                gap = 0
    if cur:
        runs.append(cur)
    out = []
    for r in runs:
        if len(r) >= 2:
            for st in r:
                st.text = st.text.strip()
            out.append(r)
    return out


def section_map(pages: list[str], outline: list[dict] | None = None) -> tuple[list[Line], list[Section], dict]:
    """Lines, the section tree (flattened, in document order) and stats. Front matter before the first heading is a
    section of its own."""
    lines, boiler = to_lines(pages)
    heads: list[tuple[int, int, str, str]] = []           # (line idx, level, num, title)
    step_lines = set()
    for run in find_steps(lines, 0, len(lines), set()):
        for st in run:
            step_lines.add(st.line_start)
    if outline and len(outline) >= 3:                     # PDF bookmarks: locate each title on its page, in order
        norm = lambda x: re.sub(r"\W+", " ", x.lower()).strip()                      # noqa: E731
        prev = -1
        for o in outline:
            pg, t = int(o.get("page") or 0), o["title"].strip()
            cands = [i for i, ln in enumerate(lines) if ln.page == pg and i > prev]
            full = norm(t)
            bare = norm(re.sub(r"^\s*[\dA-Z]{1,3}(?:[.\-]\d+)*[.)]?\s+", "", t))   # manuals often print the title
            hit = next((i for i in cands if full and full in norm(lines[i].text)), None)   # without its number
            if hit is None and len(bare) >= 4:
                hit = next((i for i in cands if norm(lines[i].text) == bare
                            or (len(bare) >= 10 and norm(lines[i].text).startswith(bare))), None)
            idx = hit if hit is not None else (cands[0] if cands else None)
            if idx is not None:
                heads.append((idx, int(o.get("level") or 1), "", t))
                prev = idx
    else:
        for i, ln in enumerate(lines):
            if i in step_lines:
                continue
            h = heading_of(ln.text)
            if h:
                heads.append((i, h[0], h[1], h[2]))
    seen, uniq = set(), []
    for h in sorted(heads):
        if h[0] not in seen:
            seen.add(h[0])
            uniq.append(h)
    heads = uniq
    if not heads or heads[0][0] > 0:
        heads.insert(0, (0, 1, "", "Front matter"))
    secs: list[Section] = []
    stack: list[Section] = []
    for k, (i, lvl, num, title) in enumerate(heads):
        end = len(lines)
        for j in range(k + 1, len(heads)):
            if heads[j][1] <= lvl:
                end = heads[j][0]
                break
        while stack and stack[-1].level >= lvl:
            stack.pop()
        sec = Section(id=f"sec{k + 1}", title=title, num=num, level=lvl, line_start=i, line_end=end,
                      page_start=lines[i].page if lines else 1, page_end=lines[max(i, end - 1)].page if lines else 1,
                      parent=stack[-1].id if stack else None, path=[s.title for s in stack] + [title])
        sec.n_chars = sum(len(lines[x].text) + 1 for x in range(i, end))
        secs.append(sec)
        stack.append(sec)
    head_idx = {h[0] for h in heads}
    for run in find_steps(lines, 0, len(lines), head_idx):          # each run belongs to the deepest section holding it
        a, b = run[0].line_start, run[-1].line_end
        owner = None
        for s in secs:
            if s.line_start <= a and b <= s.line_end and (owner is None or s.level >= owner.level):
                owner = s
        if owner is not None:
            owner.n_runs += 1
            if len(run) > len(owner.steps):
                owner.steps = run
    for s in secs:
        score_section(s)
    stats = {"n_lines": len(lines), "n_headings": len(heads), "boilerplate_removed": boiler[:20],
             "n_procedures": sum(s.proc_score >= 0.5 for s in secs),
             "toc_lines": sum(bool(TOC_LINE.match(ln.text)) for ln in lines)}
    return lines, secs, stats


def is_action(text: str) -> bool:
    """A step that tells someone to do something: starts with an action verb ("Close the valve"), or assigns
    actions to a role ("The Job Supervisor must: a. Determine ...")."""
    w = _words(text)
    if w and w[0].lower() in VERBS:
        return True
    m = re.search(r"\b(?:must|shall|should|will)\b\s*:?\s*(?:[a-h][.)]\s*)?([A-Za-z\-]+)", text)
    return bool(m and m.group(1).lower() in VERBS)


def score_section(s: Section) -> None:
    """0..1: how much the section looks like one procedure. Numbered steps count only as far as they are actions,
    so a numbered list of requirements or inspection items scores low; a procedure-like title adds a little."""
    n = len(s.steps)
    verbs = sum(is_action(st.text) for st in s.steps) / n if n else 0.0
    title_kw = 1.0 if PROC_WORDS.search(s.title) else 0.0
    size_ok = 1.0 if s.n_chars <= 40000 else 0.0
    s.proc_score = round(((min(n, 6) / 6) * (0.3 + 0.7 * verbs) * 0.8 + 0.15 * title_kw) * size_ok if n >= 3
                         else 0.15 * title_kw, 3)
    s.why = f"{n} numbered steps, {verbs:.0%} of them actions" + (f"; numbering restarts {s.n_runs - 1}×" if s.n_runs > 1 else "") + ("; procedure-like title" if title_kw else "") \
        + ("" if size_ok else "; too long to compile in one piece")


def section_text(lines: list[Line], s: Section) -> str:
    """The section's own text with page markers, exactly what the compiler sees for this procedure."""
    out, page = [], None
    for ln in lines[s.line_start:s.line_end]:
        if ln.page != page:
            page = ln.page
            out.append(f"[page {page}]")
        out.append(ln.text)
    return "\n".join(out)


def step_names(steps: list[Step], max_words: int = 12) -> list[dict]:
    """Compiler step ids/names from the manual's own numbered steps (s1 = the manual's step 1)."""
    out = []
    for st in steps:
        first = re.split(r"(?<=[.!?])\s", st.text, maxsplit=1)[0]
        w = first.split()
        out.append({"id": f"s{st.n}", "name": " ".join(w[:max_words]).rstrip(".,;:") + ("…" if len(w) > max_words else "")})
    return out

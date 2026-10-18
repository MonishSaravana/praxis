"""Local document parsing: PDF, plain text, Markdown and Word (.docx) -> text per page (or per part), plus the PDF's
outline when it has one. Runs entirely on this machine; nothing is sent anywhere.

PDF uses macOS PDFKit through a small Swift tool (`pdfkit_tool.swift`, built once into cache/bin/), so no Python
package is needed. Word files are read straight from their XML (a .docx is a zip). Page numbers are real only for
PDFs (`Parsed.paged`); text, Markdown and Word citations use the section title instead.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import unicodedata
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

from ..paths import CACHE

KINDS = {".pdf": "pdf", ".txt": "text", ".text": "text", ".md": "markdown", ".markdown": "markdown", ".docx": "docx"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}
PDFKIT_SRC = Path(__file__).with_name("pdfkit_tool.swift")
PDFKIT_BIN = CACHE / "bin" / "praxis-pdfkit"


@dataclass
class Parsed:
    kind: str                       # pdf | text | markdown | docx
    title: str
    pages: list[str]                # page i+1's text (PDF), or part i+1 (text / Markdown / Word)
    outline: list[dict] = field(default_factory=list)   # [{"title", "level", "page"}] from the PDF's bookmarks
    paged: bool = False             # True when page numbers are the document's real pages
    parser: str = ""


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def kind_of(name: str) -> str | None:
    ext = Path(name).suffix.lower()
    if ext in VIDEO_EXT:
        return "video"
    return KINDS.get(ext)


def clean(text: str) -> str:
    """NFKC (ligatures, non-breaking spaces), unified line ends, words re-joined across a hyphenated line break."""
    t = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"([a-z])-\n([a-z])", r"\1\2", t)
    t = re.sub(r"[ \t]+", " ", t)
    return "\n".join(line.strip() for line in t.split("\n"))


def parse(path: str | Path, name: str | None = None) -> Parsed:
    path = Path(path)
    kind = kind_of(name or path.name)
    if kind == "pdf":
        return parse_pdf(path, title=Path(name or path.name).stem)
    if kind in ("text", "markdown"):
        return parse_text(path.read_text(errors="replace"), kind, title=Path(name or path.name).stem)
    if kind == "docx":
        return parse_docx(path, title=Path(name or path.name).stem)
    raise ValueError(f"unsupported file type: {name or path.name} (PDF, .txt, .md or .docx)")


# ------------------------------------------------------------------------------------------ text / Markdown
def parse_text(text: str, kind: str = "text", title: str = "", part_chars: int = 4000) -> Parsed:
    """Form feeds split pages when present; otherwise parts of about part_chars, split at blank lines."""
    if "\f" in text:
        parts = [clean(p) for p in text.split("\f")]
    else:
        text = clean(text)
        parts, cur, n = [], [], 0
        for para in re.split(r"\n\s*\n", text):
            if cur and n + len(para) > part_chars:
                parts.append("\n\n".join(cur))
                cur, n = [], 0
            cur.append(para)
            n += len(para) + 2
        if cur:
            parts.append("\n\n".join(cur))
    return Parsed(kind=kind, title=title, pages=parts or [""], paged=False, parser="text")


# ------------------------------------------------------------------------------------------ Word (.docx)
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def parse_docx(path: Path, title: str = "") -> Parsed:
    """Paragraphs in order; Heading/Title styles become Markdown headings, numbered list items get their number,
    tables become ' | '-joined rows. Word's page breaks are only approximate, so pages here are parts."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(f"{W}body")
    lines: list[str] = []
    counters: dict[tuple[str, str], int] = {}

    def para_text(p) -> str:
        return "".join(t.text or "" for t in p.iter(f"{W}t"))

    for el in list(body) if body is not None else []:
        if el.tag == f"{W}tbl":
            for tr in el.iter(f"{W}tr"):
                cells = [" ".join(para_text(p) for p in tc.iter(f"{W}p")).strip() for tc in tr.iter(f"{W}tc")]
                if any(cells):
                    lines.append(" | ".join(cells))
            lines.append("")
            continue
        if el.tag != f"{W}p":
            continue
        txt = para_text(el).strip()
        ppr = el.find(f"{W}pPr")
        style = ""
        num = None
        if ppr is not None:
            ps = ppr.find(f"{W}pStyle")
            style = (ps.get(f"{W}val") if ps is not None else "") or ""
            np_ = ppr.find(f"{W}numPr")
            if np_ is not None:
                nid = np_.find(f"{W}numId")
                ilvl = np_.find(f"{W}ilvl")
                num = ((nid.get(f"{W}val") if nid is not None else "0"), (ilvl.get(f"{W}val") if ilvl is not None else "0"))
        if not txt:
            lines.append("")
            continue
        m = re.match(r"(?i)heading\s*(\d)", style)
        if m or style.lower() == "title":
            lines.append("#" * (int(m.group(1)) if m else 1) + " " + txt)
            counters.clear()                    # numbering restarts under a new heading
        elif num is not None:
            counters[num] = counters.get(num, 0) + 1
            lines.append(("   " * int(num[1])) + (f"{counters[num]}. " if num[1] == "0" else f"{chr(96 + min(counters[num], 26))}) ") + txt)
        else:
            lines.append(txt)
    p = parse_text("\n".join(lines), "docx", title=title)
    p.parser = "docx-xml"
    return p


# ------------------------------------------------------------------------------------------ PDF (macOS PDFKit)
def pdfkit_bin() -> Path:
    """The Swift PDFKit tool, compiled on first use (about a minute once; then cached)."""
    if PDFKIT_BIN.exists() and PDFKIT_BIN.stat().st_mtime >= PDFKIT_SRC.stat().st_mtime:
        return PDFKIT_BIN
    swiftc = shutil.which("swiftc")
    if swiftc is None:
        raise RuntimeError("PDF parsing needs macOS PDFKit (swiftc not found). On other systems a PDF parser package "
                           "has to be added first (see docs/BACKEND.md).")
    PDFKIT_BIN.parent.mkdir(parents=True, exist_ok=True)
    tmp = PDFKIT_BIN.with_suffix(".tmp")
    r = subprocess.run([swiftc, "-O", "-module-cache-path", str(CACHE / "swift-module-cache"), str(PDFKIT_SRC), "-o",
                        str(tmp)], capture_output=True, text=True, timeout=600)
    if not tmp.exists():
        raise RuntimeError(f"building the PDFKit tool failed: {r.stderr[-400:]}")
    tmp.replace(PDFKIT_BIN)
    return PDFKIT_BIN


def parse_pdf(path: Path, title: str = "") -> Parsed:
    r = subprocess.run([str(pdfkit_bin()), "text", str(path)], capture_output=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"could not read the PDF: {r.stderr.decode(errors='replace')[-300:]}")
    d = json.loads(r.stdout)
    pages = [clean(p) for p in d["pages"]]
    if pages and sum(len(p.strip()) for p in pages) < 20 * len(pages):
        raise RuntimeError("this PDF has almost no text layer (probably scanned images). OCR is not built yet.")
    return Parsed(kind="pdf", title=(d.get("title") or "").strip() or title or path.stem, pages=pages,
                  outline=[o for o in d.get("outline", []) if o.get("title")], paged=True, parser="pdfkit")


def render_page(path: str | Path, page: int, out: str | Path, max_side: int = 1200) -> Path:
    """One PDF page as a PNG (figures stay in the manual; this shows the page a card cites)."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([str(pdfkit_bin()), "render", str(path), str(int(page)), str(out), str(int(max_side))],
                       capture_output=True, timeout=120)
    if r.returncode != 0 or not out.exists():
        raise RuntimeError(f"could not render page {page}: {r.stderr.decode(errors='replace')[-200:]}")
    return out

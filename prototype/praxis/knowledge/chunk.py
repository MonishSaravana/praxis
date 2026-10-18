"""Chunking for local retrieval: about 900 characters each, never across a section boundary, each carrying its page
range and its section path (used for citations and prepended to the indexed text, not to the quoted text)."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .sections import Line, Section


@dataclass
class Chunk:
    id: str                         # "<doc hash[:10]>:<n>"
    doc: str                        # document file hash
    section: str                    # section id (the deepest section holding these lines)
    section_path: str               # "4 Maintenance › 4.2 Replacing the filter"
    page_start: int
    page_end: int
    line_start: int
    line_end: int
    text: str

    def as_dict(self) -> dict:
        return asdict(self)


def leaf_owner(secs: list[Section], n_lines: int) -> list[Section | None]:
    """For each line, the deepest section that contains it."""
    owner: list[Section | None] = [None] * n_lines
    for s in sorted(secs, key=lambda s: s.level):          # deeper sections overwrite their parents
        for i in range(s.line_start, min(s.line_end, n_lines)):
            owner[i] = s
    return owner


def chunk_lines(lines: list[Line], secs: list[Section], doc_hash: str, target: int = 900, hard: int = 1400) -> list[Chunk]:
    owner = leaf_owner(secs, len(lines))
    chunks: list[Chunk] = []
    buf: list[int] = []

    def flush():
        if not buf:
            return
        s = owner[buf[0]]
        text = "\n".join(lines[i].text for i in buf).strip()
        if text:
            chunks.append(Chunk(id=f"{doc_hash[:10]}:{len(chunks)}", doc=doc_hash, section=s.id if s else "",
                                section_path=" › ".join(s.path) if s else "", page_start=lines[buf[0]].page,
                                page_end=lines[buf[-1]].page, line_start=buf[0], line_end=buf[-1] + 1, text=text))
        buf.clear()

    size = 0
    for i, ln in enumerate(lines):
        if buf and owner[i] is not owner[buf[0]]:
            flush()
            size = 0
        # break at a natural point once the target is reached: a line that ends a sentence, or before a numbered step
        if buf and (size >= hard or (size >= target and (lines[buf[-1]].text.endswith((".", ":", "!", "?"))
                                                          or ln.text[:2].rstrip(".").isdigit()))):
            flush()
            size = 0
        buf.append(i)
        size += len(ln.text) + 1
    flush()
    return chunks

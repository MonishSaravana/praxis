"""Ingest once, locally: an uploaded file -> pages -> section map and procedure candidates -> chunks -> BM25 tokens
(+ optional SigLIP2 text embeddings) -> stored under the file's hash. Re-uploading the same bytes does nothing; no
step here calls a model or the network."""
from __future__ import annotations

import threading
import time
from dataclasses import asdict

import numpy as np

from .chunk import chunk_lines
from .index import Searcher, dense_text, index_text, tokens
from .parse import parse
from .sections import Line, Section, Step, section_map
from .store import Org, read_json, write_json

INGEST_VERSION = "ingest-v4"
_SEARCHERS: dict[tuple, Searcher] = {}
_LOCK = threading.Lock()


def ingest(org: Org, h: str, texts=None, force: bool = False, progress=None) -> dict:
    """Parse, map, chunk and index one stored document. texts: optional SigLIP2 text encoder (anything with
    .texts(list[str]) -> (N, D) normalized) for dense vectors. Returns the document's meta."""
    d = org.doc_dir(h)
    meta = org.doc_meta(h)
    if not force and meta.get("status") == "ready" and meta.get("ingest_version") == INGEST_VERSION \
            and (d / "index.json").exists():
        return meta
    t0 = time.perf_counter()
    say = progress or (lambda s: None)
    try:
        org.set_doc_meta(h, status="parsing", error=None)
        say("parsing")
        p = parse(org.doc_source(h), meta.get("filename"))
        write_json(d / "parsed.json", asdict(p))
        org.set_doc_meta(h, status="mapping", pages=len(p.pages), parser=p.parser, paged=p.paged, title=p.title)
        say("mapping")
        lines, secs, stats = section_map(p.pages, p.outline)
        write_json(d / "sections.json", {"lines": [asdict(x) for x in lines], "sections": [s.as_dict() for s in secs],
                                         "stats": stats})
        say("chunking")
        chunks = chunk_lines(lines, secs, h)
        cd = [c.as_dict() for c in chunks]
        write_json(d / "index.json", {"version": INGEST_VERSION, "chunks": cd,
                                      "tokens": [tokens(index_text(c)) for c in cd]})
        dense = False
        if texts is not None and cd:
            say("embedding")
            emb = np.concatenate([texts.texts([dense_text(c) for c in cd[i:i + 64]]) for i in range(0, len(cd), 64)])
            np.savez(d / "dense.npz", emb=emb.astype(np.float16))
            dense = True
        out = dict(status="ready", ingest_version=INGEST_VERSION, n_chunks=len(cd), n_sections=len(secs),
                   n_procedures=stats["n_procedures"], ingest_s=round(time.perf_counter() - t0, 2), dense=dense)
        org.set_doc_meta(h, **out)
        drop_searcher(org.id)
        return org.doc_meta(h)
    except Exception as e:  # noqa: BLE001
        org.set_doc_meta(h, status="error", error=str(e)[:300])
        raise


def load_sections(org: Org, h: str) -> tuple[list[Line], list[Section], dict]:
    d = read_json(org.doc_dir(h) / "sections.json")
    if d is None:
        raise KeyError("document not ingested yet")
    lines = [Line(**x) for x in d["lines"]]
    secs = []
    for s in d["sections"]:
        s = dict(s)
        steps = [Step(**st) for st in s.pop("steps", [])]
        s.pop("n_steps", None)
        secs.append(Section(**s, steps=steps))
    return lines, secs, d["stats"]


def searcher(org: Org, docs: list[str] | None = None) -> Searcher:
    """One in-memory searcher over the given documents (default: the latest version of each), cached until a
    document is ingested again."""
    docs = sorted(docs if docs is not None else org.current_docs())
    key = (org.id, tuple(docs))
    with _LOCK:
        if key in _SEARCHERS:
            return _SEARCHERS[key]
    chunks, toks, dense, all_dense = [], [], [], True
    for h in docs:
        idx = read_json(org.doc_dir(h) / "index.json")
        if not idx:
            continue
        chunks += idx["chunks"]
        toks += idx["tokens"]
        dp = org.doc_dir(h) / "dense.npz"
        if dp.exists():
            dense.append(np.load(dp)["emb"].astype(np.float32))
        else:
            all_dense = False
    s = Searcher(chunks, toks, np.concatenate(dense) if dense and all_dense else None)
    with _LOCK:
        _SEARCHERS[key] = s
    return s


def drop_searcher(org_id: str) -> None:
    with _LOCK:
        for k in [k for k in _SEARCHERS if k[0] == org_id]:
            del _SEARCHERS[k]


def video_meta(path) -> dict:
    import cv2
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    n = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    w, hh = cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    cap.release()
    return {"fps": round(fps, 2), "duration_s": round(n / fps, 1) if fps else None, "width": int(w), "height": int(hh)}

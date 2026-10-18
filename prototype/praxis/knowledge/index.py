"""Local retrieval over a company's documents: BM25 over chunk text (exact terms matter in manuals: part numbers,
torque units, valve tags), optionally fused with dense SigLIP2 text embeddings (already in the stack; no new model)
by reciprocal-rank fusion. Everything runs on this machine; the index is stored next to the parsed document, keyed
by the file's hash, so a document is indexed once."""
from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np

STOP = set("""a an the and or of to in on at by for with from as is are be been was were it its this that these those
into onto than then there their them they you your we our not no do does did can could should would will shall may
might must if when while which who whom what how why where all any each both few more most other some such only own
same so too very s t just also about above below over under again further once here up down out off per via""".split())
UNIT_NORM = [
    (re.compile(r"\bn\s*[·.\-]?\s*m\b"), " nm "),
    (re.compile(r"\b(?:ft|foot)\s*[·.\-]?\s*lb[sf]?\b|\blb[sf]?\s*[·.\-]?\s*ft\b"), " ftlb "),
    (re.compile(r"\bin\s*[·.\-]\s*lb[sf]?\b|\blb[sf]?\s*[·.\-]\s*in\b"), " inlb "),
    (re.compile(r"\bp\s*/\s*n\b|\bpart\s*(?:no\b\.?|number|#)"), " partnumber "),
    (re.compile(r"°\s*([cf])\b"), r" deg\1 "),
]
SYNONYMS = {"torque": ["nm", "ftlb", "inlb", "tighten"], "tighten": ["torque"], "pressure": ["psi", "bar", "kpa", "mpa"],
            "part": ["partnumber"], "temperature": ["degc", "degf"], "lockout": ["lock", "tag"], "loto": ["lockout", "tag"],
            "why": [], "spec": ["specification"], "oil": ["lubricant"], "grease": ["lubricant"]}


def stem(w: str) -> str:
    if not w.isalpha() or len(w) <= 4:
        return w
    for suf in ("ments", "ment", "ings", "ing", "edly", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4 and not (suf == "s" and w.endswith("ss")):
            w = w[: -len(suf)]
            break
    return w[:-1] if w.endswith("e") and len(w) > 4 else w


def tokens(text: str, expand: bool = False) -> list[str]:
    t = text.lower()
    for pat, rep in UNIT_NORM:
        t = pat.sub(rep, t)
    out = []
    for w in re.findall(r"[a-z0-9]+(?:[-./][a-z0-9]+)*", t):
        if w in STOP or len(w) == 1 and not w.isdigit():
            continue
        out.append(stem(w))
        if expand:
            out += [stem(x) for x in SYNONYMS.get(w, [])]
    return out


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.2, b: float = 0.75):
        self.k1, self.b, self.n = k1, b, len(docs)
        self.dl = np.array([len(d) for d in docs], dtype=np.float32)
        self.avgdl = float(self.dl.mean()) if self.n else 1.0
        self.post: dict[str, list[tuple[int, int]]] = {}
        for i, d in enumerate(docs):
            for term, tf in Counter(d).items():
                self.post.setdefault(term, []).append((i, tf))

    def idf(self, term: str) -> float:
        df = len(self.post.get(term, ()))
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def scores(self, q: list[str]) -> np.ndarray:
        s = np.zeros(self.n, dtype=np.float32)
        norm = self.k1 * (1 - self.b + self.b * self.dl / max(self.avgdl, 1e-6))
        for term, qtf in Counter(q).items():
            idf = self.idf(term)
            for i, tf in self.post.get(term, ()):
                s[i] += idf * tf * (self.k1 + 1) / (tf + norm[i]) * (1.0 if qtf == 1 else 1.2)
        return s


def index_text(c: dict) -> str:
    """What gets indexed for a chunk: its section path (so a heading's words find its body) plus its text."""
    return f"{c.get('section_path', '')}\n{c['text']}"


def dense_text(c: dict) -> str:
    """SigLIP2's text tower reads at most 64 tokens, so the dense vector sees the section path and the chunk's start."""
    return f"{c.get('section_path', '').split(' › ')[-1]}: {c['text'][:220]}"


class Searcher:
    """In-memory search over chunks from one or more documents (built per company, rebuilt when documents change)."""

    def __init__(self, chunks: list[dict], toks: list[list[str]] | None = None, dense: np.ndarray | None = None):
        self.chunks = chunks
        self.bm25 = BM25(toks if toks is not None else [tokens(index_text(c)) for c in chunks])
        self.dense = dense                       # (N, D) L2-normalized, or None

    def search(self, query: str, k: int = 5, mode: str = "bm25", query_emb: np.ndarray | None = None,
               docs: set[str] | None = None) -> list[dict]:
        """Top-k chunks as dicts with 'score' and the ranks used. mode: bm25 | dense | hybrid (RRF, k=60)."""
        if not self.chunks:
            return []
        n = len(self.chunks)
        mask = np.ones(n, bool) if docs is None else np.array([c["doc"] in docs for c in self.chunks])
        bm = self.bm25.scores(tokens(query, expand=True))
        ranks = {}
        if mode in ("bm25", "hybrid"):
            ranks["bm25"] = _rank(np.where(mask, bm, -np.inf))
        if mode in ("dense", "hybrid") and self.dense is not None and query_emb is not None:
            ds = self.dense @ np.asarray(query_emb, np.float32).reshape(-1)
            ranks["dense"] = _rank(np.where(mask, ds, -np.inf))
        if not ranks:
            ranks["bm25"] = _rank(np.where(mask, bm, -np.inf))
        fused = sum(1.0 / (60 + r) for r in ranks.values()) if len(ranks) > 1 else -next(iter(ranks.values())).astype(float)
        order = [i for i in np.argsort(-fused, kind="stable") if mask[i]][:k]
        out = []
        for i in order:
            if mode == "bm25" and bm[i] <= 0:
                continue
            d = dict(self.chunks[i])
            d["score"] = round(float(bm[i]), 3)
            d["ranks"] = {m: int(r[i]) for m, r in ranks.items()}
            out.append(d)
        return out


def _rank(scores: np.ndarray) -> np.ndarray:
    """1-based rank of each entry (highest score = 1)."""
    order = np.argsort(-scores, kind="stable")
    r = np.empty(len(scores), dtype=np.int64)
    r[order] = np.arange(1, len(scores) + 1)
    return r

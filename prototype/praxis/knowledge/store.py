"""Company profiles on disk (local, gitignored): sessions/orgs/<org_id>/.

    org.json                    name, created, settings {locked, assigned, qa_model, retrieval}
    documents.json              logical documents (by file name) -> versions [{hash, filename, uploaded_at, ...}]
    docs/<sha256>/              one uploaded file, ingested once: source.<ext>, parsed.json, sections.json,
                                index.json (chunks + tokens), dense.npz (optional), meta.json (ingest status)
    procedures/<proc_id>/       proc.json (versions, which one is approved) and v<N>/: graph.json, cards.json,
                                review.json, source.txt (the section text the compiler saw), emb.npz, refs/
    videos/<sha256>/            reference videos (source + meta)
    qa_cache/                   cached answers to questions

Deleting a company is deleting its folder. Old document and procedure versions are never overwritten.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path

from ..paths import ROOT

ORGS = ROOT / "sessions" / "orgs"
DEFAULT_SETTINGS = {"locked": False, "assigned": [], "qa_model": "claude-opus-5-5", "retrieval": "bm25"}


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, default=str))
    os.replace(tmp, path)


def read_json(path: Path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def slug(s: str, n: int = 40) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:n].strip("-") or "x"


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _safe_id(x: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9\-]{0,60}", x or ""):
        raise ValueError(f"bad id: {x!r}")
    return x


class Org:
    def __init__(self, org_id: str, root: Path | None = None):
        self.root = Path(root) if root else ORGS
        self.id = _safe_id(org_id)
        self.dir = self.root / self.id
        if not (self.dir / "org.json").exists():
            raise KeyError(f"no company profile {org_id!r}")

    # ---------------------------------------------------------------- profiles
    @classmethod
    def create(cls, name: str, root: Path | None = None) -> "Org":
        root = Path(root) if root else ORGS
        base = slug(name, 30)
        oid, k = base, 2
        while (root / oid).exists():
            oid, k = f"{base}-{k}", k + 1
        write_json(root / oid / "org.json", {"id": oid, "name": name.strip()[:80], "created": now(),
                                             "settings": dict(DEFAULT_SETTINGS)})
        return cls(oid, root)

    @staticmethod
    def list(root: Path | None = None) -> list[dict]:
        root = Path(root) if root else ORGS
        out = []
        if root.exists():
            for d in sorted(root.iterdir()):
                m = read_json(d / "org.json")
                if d.is_dir() and m:
                    out.append({"id": m["id"], "name": m["name"], "created": m["created"]})
        return out

    @property
    def meta(self) -> dict:
        m = read_json(self.dir / "org.json")
        m["settings"] = {**DEFAULT_SETTINGS, **m.get("settings", {})}
        return m

    def settings(self) -> dict:
        return self.meta["settings"]

    def update_settings(self, **kw) -> dict:
        m = self.meta
        for k, v in kw.items():
            if k in DEFAULT_SETTINGS:
                m["settings"][k] = v
        write_json(self.dir / "org.json", m)
        return m["settings"]

    # ---------------------------------------------------------------- documents
    def doc_dir(self, h: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", h):
            raise ValueError("bad document hash")
        return self.dir / "docs" / h

    def add_document(self, src: Path, filename: str, h: str, kind: str) -> dict:
        """Store an uploaded file under its hash. Same name, new content = a new version (old one kept);
        same content again = nothing new."""
        docs = read_json(self.dir / "documents.json", {})
        name = slug(Path(filename).stem, 60)
        entry = docs.setdefault(name, {"name": name, "title": Path(filename).stem, "kind": kind, "versions": []})
        for v in entry["versions"]:
            if v["hash"] == h:
                return {"name": name, "version": v["version"], "hash": h, "new": False}
        d = self.doc_dir(h)
        d.mkdir(parents=True, exist_ok=True)
        dest = d / f"source{Path(filename).suffix.lower()}"
        if not dest.exists():
            shutil.copyfile(src, dest)
        ver = len(entry["versions"]) + 1
        entry["versions"].append({"version": ver, "hash": h, "filename": filename, "uploaded_at": now(),
                                  "bytes": dest.stat().st_size})
        write_json(self.dir / "documents.json", docs)
        write_json(d / "meta.json", {**read_json(d / "meta.json", {}), "hash": h, "filename": filename, "kind": kind,
                                     "doc_name": name, "version": ver, "status": "uploaded"})
        return {"name": name, "version": ver, "hash": h, "new": True}

    def documents(self) -> list[dict]:
        docs = read_json(self.dir / "documents.json", {})
        out = []
        for name, e in docs.items():
            vers = []
            for v in e["versions"]:
                vers.append({**v, **{k: x for k, x in read_json(self.doc_dir(v["hash"]) / "meta.json", {}).items()
                                     if k in ("status", "error", "pages", "n_chunks", "n_sections", "n_procedures",
                                              "parser", "paged", "title", "ingest_s", "dense")}})
            out.append({"name": name, "title": e.get("title", name), "kind": e.get("kind"), "versions": vers,
                        "current": vers[-1]["hash"] if vers else None})
        return out

    def rename_document(self, name: str, title: str) -> dict:
        """A display title for a logical document (all its versions)."""
        docs = read_json(self.dir / "documents.json", {})
        if name not in docs:
            raise KeyError(f"no document {name!r}")
        docs[name]["title"] = title.strip()[:120] or docs[name]["title"]
        write_json(self.dir / "documents.json", docs)
        return docs[name]

    def current_docs(self) -> list[str]:
        """The latest version of each document (what questions are answered from)."""
        return [d["current"] for d in self.documents() if d["current"] and d["kind"] != "video"]

    def doc_meta(self, h: str) -> dict:
        return read_json(self.doc_dir(h) / "meta.json", {})

    def set_doc_meta(self, h: str, **kw) -> None:
        p = self.doc_dir(h) / "meta.json"
        write_json(p, {**read_json(p, {}), **kw})

    def doc_source(self, h: str) -> Path:
        return next(self.doc_dir(h).glob("source.*"))

    # ---------------------------------------------------------------- procedures
    def proc_dir(self, pid: str) -> Path:
        return self.dir / "procedures" / _safe_id(pid)

    def procedures(self) -> list[dict]:
        out = []
        pd = self.dir / "procedures"
        if pd.exists():
            for d in sorted(pd.iterdir()):
                p = read_json(d / "proc.json")
                if p:
                    out.append(p)
        return out

    def proc(self, pid: str) -> dict:
        p = read_json(self.proc_dir(pid) / "proc.json")
        if p is None:
            raise KeyError(f"no procedure {pid!r}")
        return p

    def save_proc(self, p: dict) -> None:
        write_json(self.proc_dir(p["id"]) / "proc.json", p)

    def version_dir(self, pid: str, v: int) -> Path:
        return self.proc_dir(pid) / f"v{int(v)}"

    def new_version(self, pid: str, title: str, info: dict) -> int:
        """Register a new (unapproved) version of a procedure; returns its number."""
        try:
            p = self.proc(pid)
        except KeyError:
            p = {"id": pid, "title": title, "task_id": f"org-{self.id}-{pid}"[:80], "created": now(),
                 "versions": [], "approved_version": None}
        v = len(p["versions"]) + 1
        p["versions"].append({"version": v, "created": now(), "approved": False, **info})
        p["title"] = title
        self.save_proc(p)
        return v

    def load_version(self, pid: str, v: int | None = None) -> dict:
        """graph (TaskGraph), cards, review, source text and embeddings path of one version (default: latest)."""
        from ..tasks.schema import TaskGraph
        p = self.proc(pid)
        v = v or p["versions"][-1]["version"]
        d = self.version_dir(pid, v)
        return {"proc": p, "version": v, "graph": TaskGraph.load(d / "graph.json"),
                "cards": read_json(d / "cards.json", {}), "review": read_json(d / "review.json", {}),
                "source": (d / "source.txt").read_text() if (d / "source.txt").exists() else "",
                "emb": d / "emb.npz", "refs": read_json(d / "refs" / "refs.json", {})}

    def approve(self, pid: str, v: int, by: str = "admin") -> dict:
        p = self.proc(pid)
        for x in p["versions"]:
            if x["version"] == v:
                x["approved"], x["approved_at"], x["approved_by"] = True, now(), by
        p["approved_version"] = v
        self.save_proc(p)
        return p

    def library(self, only: list[str] | None = None) -> dict[str, dict]:
        """Approved procedures, keyed by graph task id: what the live engine may use. only: procedure ids."""
        out = {}
        for p in self.procedures():
            if p.get("approved_version") and (only is None or p["id"] in only):
                out[p["task_id"]] = {**self.load_version(p["id"], p["approved_version"]), "proc_id": p["id"]}
        return out

    # ---------------------------------------------------------------- videos
    def add_video(self, src: Path, filename: str, h: str) -> dict:
        d = self.dir / "videos" / h
        d.mkdir(parents=True, exist_ok=True)
        dest = d / f"source{Path(filename).suffix.lower()}"
        if not dest.exists():
            shutil.copyfile(src, dest)
        meta = {**read_json(d / "meta.json", {}), "hash": h, "filename": filename, "uploaded_at": now(),
                "bytes": dest.stat().st_size}
        write_json(d / "meta.json", meta)
        return meta

    def videos(self) -> list[dict]:
        vd = self.dir / "videos"
        return [read_json(d / "meta.json") for d in sorted(vd.iterdir()) if (d / "meta.json").exists()] if vd.exists() else []

    def video_path(self, h: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", h):
            raise ValueError("bad video hash")
        return next((self.dir / "videos" / h).glob("source.*"))

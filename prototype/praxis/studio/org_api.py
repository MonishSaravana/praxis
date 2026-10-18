"""Company backend API for Praxis Studio (local only, like the rest of Studio): company profiles, uploads and local
ingest, the section map, compile with an estimate shown first, review / edit / approve / safety flags / lock and
assign, reference videos, and questions. Served by studio/server.py; the admin page is /admin.

Paid calls (compile, a question answered by Claude) go through knowledge.budget's ledger cap. A compile needs the
caller to confirm an amount at least as large as the estimate (`confirm_usd`).
"""
from __future__ import annotations

import tempfile
import threading
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..knowledge.store import Org, read_json

STATIC = Path(__file__).parent / "static"
router = APIRouter()
JOBS: dict = {}
MAX_UPLOAD = 500 * 1024 * 1024


def _core():
    from .server import core
    return core()


def _org(oid: str) -> Org:
    try:
        return Org(oid)
    except (KeyError, ValueError) as e:
        raise HTTPException(404, str(e)) from e


class Job:
    """A background job (ingest, compile, keyframes) with a state the page polls."""

    def __init__(self, kind: str, fn, **info):
        self.id, self.kind, self.info = uuid.uuid4().hex[:10], kind, info
        self.state, self.detail, self.error, self.result = "queued", "", None, None
        self.t0, self.t1 = time.time(), None
        JOBS[self.id] = self
        threading.Thread(target=self._run, args=(fn,), daemon=True).start()

    def progress(self, state: str, detail="") -> None:
        self.state, self.detail = state, detail

    def _run(self, fn) -> None:
        try:
            self.result = fn(self)
            self.state = "done"
        except Exception as e:  # noqa: BLE001
            self.error, self.state = str(e)[:400], "error"
        finally:
            self.t1 = time.time()

    def status(self) -> dict:
        return {"id": self.id, "kind": self.kind, "state": self.state, "detail": self.detail, "error": self.error,
                "result": self.result, "elapsed_s": round((self.t1 or time.time()) - self.t0, 1), **self.info}


def _texts():
    try:
        return _core().texts()
    except Exception:  # noqa: BLE001
        return None


def _budget() -> dict:
    from ..knowledge.budget import backend_budget
    return backend_budget().summary()


# ------------------------------------------------------------------------------------------ pages
@router.get("/admin")
def admin_page():
    return FileResponse(STATIC / "admin.html")


# ------------------------------------------------------------------------------------------ profiles
@router.get("/api/orgs")
def orgs():
    return {"orgs": Org.list(), "budget": _budget()}


@router.post("/api/orgs")
def create_org(body: dict):
    name = (body.get("name") or "").strip()
    if len(name) < 2:
        raise HTTPException(400, "give the company a name")
    return Org.create(name).meta


@router.get("/api/orgs/{oid}")
def org_detail(oid: str):
    o = _org(oid)
    procs = []
    docs = o.documents()
    latest = {d["name"]: d["versions"][-1] for d in docs if d["versions"]}
    settings = o.settings()
    titles = {d["name"]: d["title"] for d in docs}
    for p in o.procedures():
        last = p["versions"][-1]
        newer = latest.get(last.get("doc_name"))
        appr = next((v for v in p["versions"] if v["version"] == p.get("approved_version")), None)
        graph = read_json(o.version_dir(p["id"], last["version"]) / "graph.json", {})
        review = read_json(o.version_dir(p["id"], last["version"]) / "review.json", {})
        procs.append({"id": p["id"], "title": p["title"], "task_id": p["task_id"], "approved_version": p["approved_version"],
                      "approved_at": appr.get("approved_at") if appr else None,
                      "latest_version": last["version"], "n_versions": len(p["versions"]), "created": last.get("created"),
                      "n_steps": len(graph.get("nodes", [])), "n_safety": len(review.get("safety", [])),
                      "section": last.get("section_title"), "doc_name": last.get("doc_name"),
                      "doc_title": titles.get(last.get("doc_name"), last.get("doc_name")), "pages": last.get("pages"),
                      "paged": last.get("paged"), "doc_version": last.get("doc_version"), "cost_usd": last.get("cost_usd"),
                      "assigned": p["id"] in settings["assigned"],
                      "local_tracking": "reference recordings" if (o.version_dir(p["id"], p["approved_version"] or last["version"])
                                                                   / "refs" / "probe.pkl").exists() else "document only",
                      "source_updated": bool(newer and newer["version"] != last.get("doc_version"))})
    stats = {"pages": sum((d["versions"][-1].get("pages") or 0) for d in docs if d["versions"]),
             "chunks": sum((d["versions"][-1].get("n_chunks") or 0) for d in docs if d["versions"]),
             "candidates": sum((d["versions"][-1].get("n_procedures") or 0) for d in docs if d["versions"])}
    return {**o.meta, "documents": docs, "procedures": procs, "videos": o.videos(), "budget": _budget(), "stats": stats}


@router.post("/api/orgs/{oid}/settings")
def org_settings(oid: str, body: dict):
    o = _org(oid)
    kw = {}
    if "locked" in body:
        kw["locked"] = bool(body["locked"])
    if "assigned" in body:
        ids = {p["id"]: p for p in o.procedures()}
        bad = [x for x in body["assigned"] if x not in ids]
        if bad:
            raise HTTPException(400, f"unknown procedures {bad}")
        unapproved = [x for x in body["assigned"] if not ids[x].get("approved_version")]
        if unapproved:
            raise HTTPException(400, "approve a procedure before assigning it")
        kw["assigned"] = list(body["assigned"])
    if body.get("retrieval") in ("bm25", "hybrid", "dense"):
        kw["retrieval"] = body["retrieval"]
        if body["retrieval"] != "bm25":            # build the missing dense vectors (local, once per document)
            for h in o.current_docs():
                if not o.doc_meta(h).get("dense"):
                    o.update_settings(retrieval=body["retrieval"])
                    _ingest_job(o, h, force=True)
    if body.get("qa_model") in ("claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"):
        kw["qa_model"] = body["qa_model"]
    return o.update_settings(**kw)


@router.get("/api/orgs/{oid}/library")
def org_library(oid: str):
    """Approved procedures the live engine may use (in locked mode, only the assigned ones)."""
    o = _org(oid)
    s = o.settings()
    out = []
    for p in o.procedures():
        if p.get("approved_version") and (not s["locked"] or p["id"] in s["assigned"]):
            out.append({"task_id": p["task_id"], "proc_id": p["id"], "title": p["title"], "version": p["approved_version"]})
    return {"locked": s["locked"], "assigned": s["assigned"], "procedures": out}


# ------------------------------------------------------------------------------------------ uploads + ingest
@router.post("/api/orgs/{oid}/upload")
async def upload(oid: str, file: UploadFile = File(...)):
    from ..knowledge.parse import file_sha256, kind_of
    o = _org(oid)
    kind = kind_of(file.filename or "")
    if kind is None:
        raise HTTPException(400, "upload a PDF, .txt, .md or .docx document, or a video")
    up = o.dir / ".uploads"
    up.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=up, suffix=Path(file.filename).suffix.lower())
    n = 0
    with open(fd, "wb") as f:
        while chunk := await file.read(1 << 20):
            n += len(chunk)
            if n > MAX_UPLOAD:
                Path(tmp).unlink(missing_ok=True)
                raise HTTPException(413, "file is larger than 500 MB")
            f.write(chunk)
    try:
        h = file_sha256(tmp)
        if kind == "video":
            from ..knowledge.ingest import video_meta
            meta = o.add_video(Path(tmp), file.filename, h)
            vm = video_meta(o.video_path(h))
            from ..knowledge.store import write_json
            write_json(o.dir / "videos" / h / "meta.json", {**meta, **vm})
            return {"kind": "video", "hash": h, **vm}
        res = o.add_document(Path(tmp), file.filename, h, kind)
    finally:
        Path(tmp).unlink(missing_ok=True)
    job = _ingest_job(o, h)
    return {"kind": kind, **res, "job": job.status()}


def _ingest_job(o: Org, h: str, force: bool = False) -> Job:
    from ..knowledge.ingest import ingest

    def run(job):                      # dense vectors only when the company uses hybrid retrieval (unmeasured so far)
        texts = _texts() if o.settings()["retrieval"] != "bm25" else None
        m = ingest(o, h, texts=texts, force=force, progress=job.progress)
        return {k: m.get(k) for k in ("status", "pages", "n_chunks", "n_sections", "n_procedures", "ingest_s", "dense")}
    return Job("ingest", run, org=o.id, doc=h)


@router.post("/api/orgs/{oid}/documents/{name}")
def rename_document(oid: str, name: str, body: dict):
    try:
        return _org(oid).rename_document(name, str(body.get("title") or ""))
    except KeyError as e:
        raise HTTPException(404, str(e)) from e


@router.post("/api/orgs/{oid}/docs/{h}/reingest")
def reingest(oid: str, h: str):
    return _ingest_job(_org(oid), h, force=True).status()


@router.get("/api/jobs/{jid}")
def job_status(jid: str):
    j = JOBS.get(jid)
    if j is None:
        raise HTTPException(404, "no such job")
    return j.status()


@router.get("/api/orgs/{oid}/docs/{h}/sections")
def doc_sections(oid: str, h: str):
    from ..knowledge.ingest import load_sections
    o = _org(oid)
    try:
        lines, secs, stats = load_sections(o, h)
    except KeyError as e:
        raise HTTPException(409, str(e)) from e
    compiled = {}
    for p in o.procedures():
        for v in p["versions"]:
            if v.get("doc_hash") == h:
                compiled[v["section_id"]] = p["id"]
    out = []
    for s in secs:
        d = s.as_dict(with_steps=False)
        d["first_steps"] = [st.text[:90] for st in s.steps[:3]]
        d["procedure"] = compiled.get(s.id)
        out.append(d)
    return {"meta": o.doc_meta(h), "stats": stats, "sections": out}


@router.get("/api/orgs/{oid}/docs/{h}/page/{n}.png")
def doc_page(oid: str, h: str, n: int):
    from ..knowledge.parse import render_page
    o = _org(oid)
    if not o.doc_meta(h).get("paged"):
        raise HTTPException(404, "this document has no pages")
    out = o.doc_dir(h) / "pages" / f"p{int(n):04d}.png"
    if not out.exists():
        try:
            render_page(o.doc_source(h), n, out)
        except RuntimeError as e:
            raise HTTPException(404, str(e)) from e
    return FileResponse(out, media_type="image/png")


@router.get("/api/orgs/{oid}/search")
def search(oid: str, q: str, k: int = 5, mode: str | None = None):
    from ..knowledge.ingest import searcher
    o = _org(oid)
    mode = mode or o.settings()["retrieval"]
    qe = None
    if mode != "bm25" and _texts() is not None:
        qe = _texts().texts([q])[0]
    return {"query": q, "mode": mode, "hits": searcher(o).search(q, k=k, mode=mode, query_emb=qe)}


# ------------------------------------------------------------------------------------------ compile
@router.get("/api/orgs/{oid}/docs/{h}/sections/{sid}/plan")
def compile_plan(oid: str, h: str, sid: str, effort: str = "medium"):
    from ..knowledge.compile import plan
    try:
        return {**plan(_org(oid), h, sid, effort), "budget": _budget()}
    except KeyError as e:
        raise HTTPException(404, str(e)) from e


@router.post("/api/orgs/{oid}/docs/{h}/sections/{sid}/compile")
def compile_section(oid: str, h: str, sid: str, body: dict):
    from ..knowledge.compile import compile_section as run_compile
    from ..knowledge.compile import plan
    o = _org(oid)
    effort = body.get("effort", "medium")
    p = plan(o, h, sid, effort)
    if p["too_long"]:
        raise HTTPException(400, "this section is too long to compile in one piece; pick a smaller section")
    need = p["estimate"]["upper_usd"]
    if need > 0 and float(body.get("confirm_usd") or 0) < need:
        raise HTTPException(402, f"confirm the estimated cost first (up to ${need:.2f})")

    def run(job):
        pid, v = run_compile(o, h, sid, effort=effort, texts=_texts(), proc_id=body.get("proc_id"),
                             domain=body.get("domain") if body.get("domain") in ("maintenance", "assembly", "cooking", "other") else "maintenance",
                             on_progress=lambda st, n=0: job.progress(st, n))
        return {"proc_id": pid, "version": v}
    return Job("compile", run, org=o.id, doc=h, section=sid, estimate=p["estimate"]).status()


# ------------------------------------------------------------------------------------------ review
@router.get("/api/orgs/{oid}/procedures/{pid}")
def procedure(oid: str, pid: str, v: int | None = None):
    o = _org(oid)
    try:
        x = o.load_version(pid, v)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    p = x["proc"]
    ver = next(y for y in p["versions"] if y["version"] == x["version"])
    docs = {d["name"]: d for d in o.documents()}
    d = docs.get(ver.get("doc_name"))
    newer = d["versions"][-1] if d and d["versions"][-1]["version"] != ver.get("doc_version") else None
    return {"proc": p, "version": x["version"], "info": ver, "graph": x["graph"].model_dump(), "cards": x["cards"],
            "review": x["review"], "source": x["source"], "refs": x["refs"],
            "newer_doc": {"version": newer["version"], "hash": newer["hash"], "filename": newer["filename"]} if newer else None,
            "local": _local_status(o, pid, x["version"])}


def _local_status(o: Org, pid: str, v: int) -> dict:
    from ..knowledge.refs import load_marks, probe_meta
    vids = {m["hash"]: m for m in o.videos()}
    marks = load_marks(o, pid, v)
    return {"probe": probe_meta(o, pid, v),
            "marked_videos": [{"video": h, "filename": (vids.get(h) or {}).get("filename"), "marked_steps": len(m["marks"]),
                               "source": m["source"], "saved": m["saved"]} for h, m in marks.items()]}


@router.post("/api/orgs/{oid}/procedures/{pid}/edit")
def procedure_edit(oid: str, pid: str, body: dict):
    from ..knowledge.compile import edit_version
    o = _org(oid)
    v = edit_version(o, pid, int(body["version"]), body.get("edits") or {}, texts=_texts())
    return {"version": v}


@router.post("/api/orgs/{oid}/procedures/{pid}/approve")
def procedure_approve(oid: str, pid: str, body: dict):
    o = _org(oid)
    v = int(body["version"])
    x = o.load_version(pid, v)
    if not x["emb"].exists() and _texts() is not None:
        from ..knowledge.compile import embed_version
        embed_version(o, pid, v, _texts())
    return o.approve(pid, v, by=(body.get("by") or "admin")[:60])


@router.get("/api/orgs/{oid}/procedures/{pid}/recompile")
def procedure_recompile_plan(oid: str, pid: str, effort: str = "medium"):
    """Plan a recompile from the newest version of the procedure's source document (same section title)."""
    from ..knowledge.compile import find_section_like, plan
    o = _org(oid)
    p = o.proc(pid)
    last = p["versions"][-1]
    d = next((x for x in o.documents() if x["name"] == last.get("doc_name")), None)
    if d is None:
        raise HTTPException(404, "source document not found")
    h = d["current"]
    if o.doc_meta(h).get("status") != "ready":
        raise HTTPException(409, "the new document version is still being ingested")
    sid = find_section_like(o, h, last["section_title"])
    if sid is None:
        raise HTTPException(404, f"section '{last['section_title']}' not found in the new version; compile it from the section list")
    return {"doc": h, "section_id": sid, "proc_id": pid, **plan(o, h, sid, effort), "budget": _budget()}


# ------------------------------------------------------------------------------------------ reference videos
@router.post("/api/orgs/{oid}/procedures/{pid}/refs")
def procedure_refs(oid: str, pid: str, body: dict):
    from ..knowledge.video import reference_keyframes
    o = _org(oid)
    v, vid = int(body["version"]), body["video"]

    def run(job):
        job.progress("keyframes")
        enc = _core().encoders()
        with enc.gpu:
            refs = reference_keyframes(o, pid, v, vid, enc.sig)
        return {"n": len(refs)}
    return Job("refs", run, org=o.id, proc=pid, version=v).status()


@router.get("/api/orgs/{oid}/procedures/{pid}/v/{v}/refs/{name}")
def procedure_ref_image(oid: str, pid: str, v: int, name: str):
    o = _org(oid)
    if not name.endswith(".jpg") or "/" in name or ".." in name:
        raise HTTPException(400, "bad name")
    p = o.version_dir(pid, v) / "refs" / name
    if not p.exists():
        raise HTTPException(404, "no reference frame")
    return FileResponse(p, media_type="image/jpeg")


@router.get("/api/orgs/{oid}/videos/{h}/file")
def video_file(oid: str, h: str):
    o = _org(oid)
    try:
        p = o.video_path(h)
    except (ValueError, StopIteration) as e:
        raise HTTPException(404, "no such video") from e
    return FileResponse(p, media_type="video/mp4")


@router.get("/api/orgs/{oid}/procedures/{pid}/marking/{h}")
def marking_get(oid: str, pid: str, h: str, v: int | None = None):
    """What the step-marking page needs: the steps, any saved marks for this video, and whether features exist."""
    from ..knowledge.refs import features_path, load_marks, probe_meta
    o = _org(oid)
    x = o.load_version(pid, v)
    meta = next((m for m in o.videos() if m["hash"] == h), None)
    if meta is None:
        raise HTTPException(404, "no such video")
    saved = load_marks(o, pid, x["version"]).get(h)
    return {"proc": {"id": pid, "title": x["graph"].title, "version": x["version"],
                     "approved": x["proc"].get("approved_version") == x["version"]},
            "steps": [{"id": n.id, "name": n.name, "end_state": n.end_state} for n in x["graph"].nodes],
            "video": meta, "saved": saved, "features_ready": features_path(o, h).exists(), "probe": probe_meta(o, pid, x["version"])}


@router.post("/api/orgs/{oid}/procedures/{pid}/marking/{h}/auto")
def marking_auto(oid: str, pid: str, h: str, body: dict):
    """Background job: video features (once per video, local) + an automatic in-order alignment of steps to time."""
    from ..knowledge.refs import auto_marks, video_features
    o = _org(oid)
    v = int(body["version"])

    def run(job):
        job.progress("features")
        f = video_features(o, h, _core().encoders(), progress=job.progress)
        job.progress("aligning")
        return {"marks": auto_marks(o, pid, v, f, _texts()), "duration_s": float(f["t"][-1]) if len(f["t"]) else 0.0}
    return Job("auto-marks", run, org=o.id, proc=pid, video=h).status()


@router.post("/api/orgs/{oid}/procedures/{pid}/marking/{h}")
def marking_save(oid: str, pid: str, h: str, body: dict):
    from ..knowledge.refs import save_marks
    o = _org(oid)
    return save_marks(o, pid, int(body["version"]), h, body.get("marks") or {}, body.get("source") or "person")


@router.post("/api/orgs/{oid}/procedures/{pid}/train")
def procedure_train(oid: str, pid: str, body: dict):
    """Background job: train the version's local tracker on every marked reference video (local, $0)."""
    from ..knowledge.refs import train_local
    o = _org(oid)
    v = int(body["version"])

    def run(job):
        job.progress("training")
        return train_local(o, pid, v, _core().encoders(), progress=job.progress)
    return Job("train", run, org=o.id, proc=pid, version=v).status()


@router.post("/api/orgs/{oid}/procedures/{pid}/refs/clear")
def procedure_ref_clear(oid: str, pid: str, body: dict):
    from ..knowledge.store import write_json
    o = _org(oid)
    d = o.version_dir(pid, int(body["version"])) / "refs"
    refs = read_json(d / "refs.json", {})
    refs.pop(body.get("node"), None)
    write_json(d / "refs.json", refs)
    return refs


# ------------------------------------------------------------------------------------------ questions
@router.post("/api/orgs/{oid}/ask")
def ask(oid: str, body: dict):
    from ..knowledge.qa import answer
    from .org_session import LIVE, latest_live
    o = _org(oid)
    q = (body.get("question") or "").strip()
    if not q:
        raise HTTPException(400, "ask a question")
    sess = None if body.get("proc_id") else (LIVE.get(body.get("session_id") or "") or latest_live(o.id))
    step = sess.step_context() if sess is not None else None
    if step is None and body.get("proc_id"):                 # admin page: ask about a procedure's step
        x = o.load_version(body["proc_id"], body.get("version"))
        g, nid = x["graph"], body.get("node") or x["graph"].nodes[0].id
        n = g.node(nid)
        ver = next(v for v in x["proc"]["versions"] if v["version"] == x["version"])
        step = {"task": g.title, "name": n.name, "instruction": n.instruction_novice, "cards": x["cards"].get(nid, []),
                "procedure_cards": x["cards"].get("_procedure", []), "doc": ver.get("doc_hash"), "node": nid}
    qe = None
    if o.settings()["retrieval"] != "bm25" and _texts() is not None:
        qe = _texts().texts([q])[0]
    r = answer(o, q, step=step, query_emb=qe, allow_model=bool(body.get("use_model")))
    r["step"] = {k: step.get(k) for k in ("task", "name", "node")} if step else None
    r["budget"] = _budget()
    if sess is not None:
        sess.log.write("question", sess.t_last, question=q[:300], answer=r["answer"][:400], source=r["source"],
                       citations=[c.get("where") for c in r.get("citations", [])], cost_usd=r.get("cost_usd", 0.0),
                       cached=r.get("cached", False))
    return r


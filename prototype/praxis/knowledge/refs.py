"""Reference recordings: teach a company procedure's local tracker what each step looks like.

A manager uploads a recording of someone doing the job and marks when each step starts (or accepts an automatic,
in-order alignment and corrects it). Praxis then trains that procedure's local probe on the video's frames, labelled by
the marks, and live sessions use it instead of zero-shot text matching. Measured offline on CaptainCook4D pinwheels
(`eval/company_tracking.py`): a company-compiled procedure went from 0.20 step accuracy (document only) to 0.43 with
one marked recording and 0.48 with three, without any verifier calls. All local, $0.

Stored per procedure version under refs/: marks.json ({video hash: {"marks": {node: start_s}, "source", "saved"}}),
probe.pkl and probe.json (what it was trained on). Video features are cached once per video under
videos/<hash>/features.npz (t, SigLIP2 frame embedding, V-JEPA 2 window embedding, at 4 fps).
"""
from __future__ import annotations

import pickle
import time

import numpy as np

from .store import Org, now, read_json, write_json
from .video import align

FPS, WIN, STRIDE = 4.0, 8, 4            # the live loop's cadence: 4 fps, V-JEPA over 8 frames once a second


def features_path(org: Org, video_hash: str):
    return org.video_path(video_hash).parent / "features.npz"


def video_features(org: Org, video_hash: str, enc, progress=None) -> dict:
    """L1 features of a reference video, streamed (never holds the whole video), cached. enc: Studio's Encoders
    (sig, vj, gpu lock)."""
    out = features_path(org, video_hash)
    if out.exists():
        z = np.load(out)
        return {"t": z["t"], "frame": z["siglip"].astype(np.float32), "window": z["window"].astype(np.float32)}
    from ..io.sources import FileSource
    say = progress or (lambda *_: None)
    ts, sig, win = [], [], []
    batch, ring, cur_win = [], [], None
    t0 = time.perf_counter()

    def flush():
        if batch:
            with enc.gpu:
                sig.extend(enc.sig.images([f for _, f in batch]))
            batch.clear()

    for i, fr in enumerate(FileSource(org.video_path(video_hash), fps=FPS, max_side=640)):
        ts.append(fr.t)
        batch.append((fr.t, fr.rgb))
        ring = (ring + [fr.rgb])[-WIN:]
        if len(ring) == WIN and (i - (WIN - 1)) % STRIDE == 0:
            with enc.gpu:
                cur_win = enc.vj.clips([list(ring)], batch=1)[0]
        win.append(cur_win)
        if len(batch) >= 32:
            flush()
            say("features", f"{fr.t:.0f} s")
    flush()
    dim = next((w.shape[0] for w in win if w is not None), 1024)
    window = np.stack([w if w is not None else np.zeros(dim, np.float32) for w in win]) if win else np.zeros((0, dim))
    frame = np.asarray(sig, np.float32)
    np.savez_compressed(out, t=np.array(ts, np.float32), siglip=frame.astype(np.float16), window=window.astype(np.float16),
                        seconds=np.array([time.perf_counter() - t0], np.float32))
    return {"t": np.array(ts, np.float32), "frame": frame, "window": window.astype(np.float32)}


def end_state_matrix(org: Org, pid: str, v: int, texts=None) -> np.ndarray:
    d = org.version_dir(pid, v)
    if not (d / "emb.npz").exists():
        from .compile import embed_version
        embed_version(org, pid, v, texts)
    z = np.load(d / "emb.npz")
    E = z["end_state"] + 0.5 * z["name"]
    return E / np.linalg.norm(E, axis=1, keepdims=True)


def auto_marks(org: Org, pid: str, v: int, feats: dict, texts=None) -> dict[str, float]:
    """Start time of each step by an in-order alignment of the video's frames to the steps' end-state text."""
    from ..tasks.schema import TaskGraph
    g = TaskGraph.load(org.version_dir(pid, v) / "graph.json")
    E = end_state_matrix(org, pid, v, texts)
    F = feats["frame"] / np.maximum(np.linalg.norm(feats["frame"], axis=1, keepdims=True), 1e-6)
    spans = align(E @ F.T)
    return {n.id: round(float(feats["t"][a]), 2) for n, (a, _) in zip(g.nodes, spans)}


def load_marks(org: Org, pid: str, v: int) -> dict:
    return read_json(org.version_dir(pid, v) / "refs" / "marks.json", {})


def save_marks(org: Org, pid: str, v: int, video_hash: str, marks: dict, source: str) -> dict:
    from ..tasks.schema import TaskGraph
    g = TaskGraph.load(org.version_dir(pid, v) / "graph.json")
    clean = {k: round(float(t), 2) for k, t in marks.items() if k in g.ids and t is not None and float(t) >= 0}
    allm = load_marks(org, pid, v)
    allm[video_hash] = {"marks": clean, "source": source if source in ("automatic", "person", "dataset labels") else "person",
                        "saved": now()}
    write_json(org.version_dir(pid, v) / "refs" / "marks.json", allm)
    return allm[video_hash]


def frame_labels(ids: list[str], marks: dict[str, float], t: np.ndarray) -> np.ndarray:
    """Step index per frame: a step runs from its mark to the next mark in time; frames before the first mark are
    unlabelled (-1). Steps without a mark get no frames."""
    pts = sorted((s, ids.index(k)) for k, s in marks.items() if k in ids)
    y = np.full(len(t), -1)
    for j, (s, k) in enumerate(pts):
        e = pts[j + 1][0] if j + 1 < len(pts) else float("inf")
        y[(t >= s) & (t < e)] = k
    return y


def train_local(org: Org, pid: str, v: int, enc=None, progress=None) -> dict:
    """Fit the procedure version's local probe on every marked reference video. Returns what it was trained on."""
    from ..evidence import ProbeEvidence
    from ..tasks.schema import TaskGraph
    g = TaskGraph.load(org.version_dir(pid, v) / "graph.json")
    allm = load_marks(org, pid, v)
    X, y, used = [], [], []
    for vh, m in allm.items():
        if len(m["marks"]) < 2:
            continue
        f = video_features(org, vh, enc, progress)
        yi = frame_labels(g.ids, m["marks"], f["t"])
        X.append(ProbeEvidence.featurize(f["frame"], f["window"]))
        y.append(yi)
        used.append({"video": vh, "marked_steps": len(m["marks"]), "source": m["source"], "frames": int((yi >= 0).sum())})
    if not used:
        raise ValueError("mark at least two step starts on a reference video first")
    Y = np.concatenate(y)
    if len(set(Y[Y >= 0].tolist())) < 2:
        raise ValueError("the marks cover fewer than two steps")
    probe = ProbeEvidence.fit(g.ids, np.concatenate(X), Y)
    d = org.version_dir(pid, v) / "refs"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "probe.pkl", "wb") as fh:
        pickle.dump(probe, fh)
    per_step = {g.ids[k]: int((Y == k).sum()) for k in range(len(g.ids))}
    meta = {"trained": now(), "videos": used, "frames": int((Y >= 0).sum()), "steps_covered": sum(c > 0 for c in per_step.values()),
            "n_steps": len(g.ids), "frames_per_step": per_step,
            "source": used[0]["source"] if len({u["source"] for u in used}) == 1 else "mixed"}
    write_json(d / "probe.json", meta)
    return meta


def load_probe(org: Org, pid: str, v: int):
    p = org.version_dir(pid, v) / "refs" / "probe.pkl"
    if not p.exists():
        return None
    with open(p, "rb") as fh:
        return pickle.load(fh)


def probe_meta(org: Org, pid: str, v: int) -> dict | None:
    return read_json(org.version_dir(pid, v) / "refs" / "probe.json")

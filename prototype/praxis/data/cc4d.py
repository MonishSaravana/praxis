"""CaptainCook4D (Peddi et al., 2023): egocentric cooking with step timestamps and per-step error labels.

Builds:
  - the eval clip manifest: 6 recordings x 8 recipes from the official test+val recordings, each trimmed to
    a <=5 min window chosen to contain an annotated error step when the recording has one (error-free
    recordings start at t=0 so task recognition from the start is also measured)
  - the train list: official train-split recordings (L2 detector, step probes, task recognizer, calibration)
  - a held-out-procedure list: recordings of recipes outside the 8 (L2 generalization to unseen procedures)
Ground truth never comes from us: steps, times and errors are the dataset's own annotations.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from ..paths import DATA

RAW = DATA / "raw" / "cc4d"
ANN = RAW / "ann"
VID = RAW / "videos"
DATASET = "CaptainCook4D"

RECIPES = ["Tomato Mozzarella Salad", "Spiced Hot Chocolate", "Breakfast Burritos", "Microwave Egg Sandwich",
           "Pinwheels", "Microwave Mug Pizza", "Herb Omelet with Fried Tomatoes", "Cucumber Raita"]
HELDOUT_RECIPES = ["Coffee", "Mug Cake", "Zoodles", "Ramen"]      # procedure types never used for training
CLIPS_PER_RECIPE = 6
MAX_CLIP_S = 300.0
CONTEXT_BEFORE_ERROR_S = 75.0


@dataclass
class Segment:
    start: float
    end: float
    step: str              # node id, e.g. "s12"
    name: str
    has_error: bool = False
    errors: list[dict] = field(default_factory=list)


@dataclass
class Clip:
    clip_id: str
    dataset: str
    task_id: str
    recording: str
    video: str
    start: float           # window start inside the recording (s)
    end: float
    split: str
    segments: list[Segment]        # relative to clip start
    missing_steps: list[str] = field(default_factory=list)
    person: str = ""

    @property
    def duration(self) -> float:
        return self.end - self.start

    def mistakes(self) -> list[dict]:
        """Timed GT mistakes (steps with an error label other than 'Missing Step'), clip-relative."""
        out = []
        for s in self.segments:
            tags = [e["tag"] for e in s.errors if e["tag"] != "Missing Step"]
            if s.has_error and tags:
                out.append({"start": s.start, "end": s.end, "step": s.step, "tags": tags,
                            "description": "; ".join(e.get("description", "") for e in s.errors)})
        return out

    def to_json(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_json(d: dict) -> "Clip":
        d = dict(d)
        d["segments"] = [Segment(**s) for s in d["segments"]]
        return Clip(**d)


def slug(name: str) -> str:
    return "cc4d_" + re.sub(r"[^a-z0-9]+", "", name.lower())


def _load():
    cs = json.loads((ANN / "annotation_json/complete_step_annotations.json").read_text())
    err = {r["recording_id"]: r for r in json.loads((ANN / "annotation_json/error_annotations.json").read_text())}
    split = json.loads((ANN / "data_splits/recordings_data_split_combined.json").read_text())
    sp = {r: k for k, v in split.items() for r in v}
    import csv
    dur = {r["recording_id"]: float(r["duration(sec)"]) for r in csv.DictReader(open(ANN / "metadata/video_information.csv"))}
    return cs, err, sp, dur


def recording_segments(rid: str, cs: dict, err: dict) -> tuple[list[Segment], list[str]]:
    errs = {s["step_id"]: s.get("errors", []) for s in err.get(rid, {}).get("step_annotations", [])}
    segs, missing = [], []
    for s in cs[rid]["steps"]:
        sid = f"s{s['step_id']}"
        e = errs.get(s["step_id"], [])
        if s["start_time"] < 0:
            missing.append(sid)
            continue
        segs.append(Segment(float(s["start_time"]), float(s["end_time"]), sid, _clean(s["description"]),
                            bool(s["has_errors"]), e))
    segs.sort(key=lambda x: x.start)
    return segs, missing


def _clean(desc: str) -> str:
    return desc.split("-", 1)[1].strip() if "-" in desc else desc.strip()


def recipe_steps(recipe: str) -> tuple[list[dict], list[tuple[str, str]]]:
    """Global step ids for a recipe + ordering constraints from the dataset's task graph."""
    cs, _, _, _ = _load()
    steps: dict[int, str] = {}
    for d in cs.values():
        if d["activity_name"] == recipe:
            for s in d["steps"]:
                steps[s["step_id"]] = s["description"]
    tg = _task_graph_file(recipe)
    g = json.loads(tg.read_text())
    local = {int(k): v for k, v in g["steps"].items()}
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    glob_by_text = {norm(v): k for k, v in steps.items()}
    l2g = {}
    for lk, txt in local.items():
        if txt in ("START", "END"):
            continue
        gk = glob_by_text.get(norm(txt))
        if gk is None:   # fall back to best token overlap
            best = max(steps, key=lambda k: len(set(norm(steps[k])) & set(norm(txt))) - abs(len(steps[k]) - len(txt)) * 0.01)
            gk = best
        l2g[lk] = gk
    edges = []
    for a, b in g["edges"]:
        if a in l2g and b in l2g:
            edges.append((f"s{l2g[a]}", f"s{l2g[b]}"))
    ordered = sorted(steps)
    return [{"id": f"s{k}", "name": _clean(steps[k]), "raw": steps[k]} for k in ordered], edges


def _task_graph_file(recipe: str) -> Path:
    key = re.sub(r"[^a-z]", "", recipe.lower())
    for p in (ANN / "task_graphs").glob("*.json"):
        if p.stem == key:
            return p
    # e.g. "Sauted Mushrooms" vs file names
    cands = sorted((ANN / "task_graphs").glob("*.json"), key=lambda p: -len(set(p.stem) & set(key)))
    return cands[0]


def build_manifest(seed: int = 0) -> dict:
    cs, err, sp, dur = _load()
    rng = np.random.default_rng(seed)
    eval_clips, train, heldout = [], [], []
    for recipe in RECIPES + HELDOUT_RECIPES:
        rids = sorted(r for r, d in cs.items() if d["activity_name"] == recipe)
        if recipe in HELDOUT_RECIPES:
            # 2 recordings per held-out procedure type, full length, for L2 generalization only
            for rid in rids[:2]:
                segs, miss = recording_segments(rid, cs, err)
                heldout.append(Clip(f"{rid}_full", DATASET, slug(recipe), rid, str(VID / f"{rid}_360p.mp4"), 0.0,
                                    dur[rid], "heldout_type", segs, miss, str(cs[rid].get("person_id", ""))).to_json())
            continue
        pool = [r for r in rids if sp.get(r) in ("test", "val")]
        with_err = [r for r in pool if any(s.has_error and any(e["tag"] != "Missing Step" for e in s.errors)
                                           for s in recording_segments(r, cs, err)[0])]
        no_err = [r for r in pool if r not in with_err]
        pick = list(rng.permutation(no_err)[:1]) + list(rng.permutation(with_err))
        pick = (pick + [r for r in pool if r not in pick])[:CLIPS_PER_RECIPE]
        for rid in sorted(pick):
            segs, miss = recording_segments(rid, cs, err)
            errs = [s for s in segs if s.has_error and any(e["tag"] != "Missing Step" for e in s.errors)]
            if errs:
                s0 = max(0.0, errs[0].start - CONTEXT_BEFORE_ERROR_S)
                s0 = 0.0 if s0 < 45 else s0
            else:
                s0 = 0.0
            e0 = min(dur[rid], s0 + MAX_CLIP_S)
            rel = []
            for s in segs:
                if s.end <= s0 or s.start >= e0:
                    continue
                rel.append(Segment(max(0.0, s.start - s0), min(e0, s.end) - s0, s.step, s.name, s.has_error, s.errors))
            eval_clips.append(Clip(f"{rid}_{int(s0)}", DATASET, slug(recipe), rid, str(VID / f"{rid}_360p.mp4"), s0, e0,
                                   sp[rid], rel, miss, str(cs[rid].get("person_id", ""))).to_json())
        for rid in rids:
            if sp.get(rid) == "train":
                segs, miss = recording_segments(rid, cs, err)
                train.append(Clip(f"{rid}_full", DATASET, slug(recipe), rid, str(VID / f"{rid}_360p.mp4"), 0.0, dur[rid],
                                  "train", segs, miss, str(cs[rid].get("person_id", ""))).to_json())
    man = {"dataset": DATASET, "recipes": RECIPES, "heldout_recipes": HELDOUT_RECIPES, "seed": seed,
           "eval": eval_clips, "train": train, "heldout_type": heldout}
    (DATA / "cc4d").mkdir(parents=True, exist_ok=True)
    (DATA / "cc4d" / "manifest.json").write_text(json.dumps(man, indent=1))
    return man


def load_manifest() -> dict:
    return json.loads((DATA / "cc4d" / "manifest.json").read_text())


def download(rids: list[str], workers: int = 4) -> list[str]:
    """Fetch GoPro 360p mp4s (public Box static links from the official downloader metadata)."""
    import concurrent.futures as cf
    import subprocess
    links = json.loads((RAW / "download_links.json").read_text())
    VID.mkdir(parents=True, exist_ok=True)

    def one(rid: str) -> str:
        out = VID / f"{rid}_360p.mp4"
        if out.exists() and out.stat().st_size > 1e6:
            return f"have {rid}"
        tmp = out.with_suffix(".part")
        r = subprocess.run(["curl", "-sSL", "--retry", "4", "-m", "1800", "-o", str(tmp), links[rid]["gopro_360p"]],
                           capture_output=True, text=True)
        if r.returncode == 0 and tmp.stat().st_size > 1e6:
            tmp.rename(out)
            return f"ok {rid} {out.stat().st_size / 1e6:.0f}MB"
        return f"FAIL {rid} {r.stderr[:200]}"

    with cf.ThreadPoolExecutor(workers) as ex:
        return list(ex.map(one, rids))

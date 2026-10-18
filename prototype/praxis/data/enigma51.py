"""ENIGMA-51 (Ragusa et al., WACV 2024): first-person repairs of electrical boards in an industrial-like lab
(HoloLens 2, 2272x1278 @ 30 fps). Four written procedures: high- or low-voltage board x manual or electric screwdriver
(power supply, soldering station, pliers, oscilloscope). https://fpv-iplab.github.io/ENIGMA-51/

The labels are object interactions (take / release / first contact / decontact / contact, with the object), not
procedure steps. So results here are PROXIES, labeled as such:
  object consistency  at each annotated interaction, does the step Praxis believes in list the touched object among
                      its parts? (chance = the share of steps that list it)
  derived step labels each interaction is assigned to a step by a monotonic alignment of the interaction objects to
                      the steps' parts; a step spans its first to last assigned interaction. Not human step labels.

Graphs are compiled from the written procedures with the same path as pasted instructions in Studio (split into at
most 20 steps, then the L3 compiler) and kept OUT of the cooking library (data/enigma51/taskgraphs).
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from ..paths import DATA

RAW = DATA / "raw" / "enigma51"
OUT = DATA / "enigma51"
GRAPHS = OUT / "taskgraphs"
PROCS = {  # task id: (written procedure file, board, screwdriver)
    "enigma_hv_electric": ("high_voltage_electric_screwdriver.txt", "high", "electric"),
    "enigma_hv_manual": ("high_voltage_screwdriver.txt", "high", "manual"),
    "enigma_lv_electric": ("low_voltage_electric_screwdriver.txt", "low", "electric"),
    "enigma_lv_manual": ("low_voltage_screwdriver.txt", "low", "manual"),
}
TEST_VIDEOS = {"141": "enigma_hv_manual", "107": "enigma_hv_electric", "144": "enigma_lv_electric", "53": "enigma_lv_manual"}
OBJECT_WORDS = {  # ENIGMA object class -> words that name it in a compiled step's parts
    "power_supply": ["power supply"], "power_supply_cables": ["cable", "lead"], "oscilloscope": ["oscilloscope"],
    "oscilloscope_probe_tip": ["probe"], "oscilloscope_ground_clip": ["ground clip", "clip"],
    "welder_station": ["soldering", "station"], "welder_base": ["soldering", "holder", "base"],
    "welder_probe_tip": ["soldering iron", "iron", "tip"], "electric_screwdriver": ["electric screwdriver", "screwdriver"],
    "electric_screwdriver_battery": ["battery"], "battery_connector": ["battery", "connector"],
    "screwdriver": ["screwdriver"], "pliers": ["pliers"], "high_voltage_board": ["board"], "low_voltage_board": ["board"],
    "low_voltage_board_screen": ["display", "screen"], "register": ["register", "logbook", "log book", "notebook"],   # the paper log, not a resistor
    "left_red_button": ["button", "panel"], "left_green_button": ["button", "panel"],
    "right_red_button": ["button", "panel"], "right_green_button": ["button", "panel"],
    "socket_1": ["socket", "switch"], "socket_2": ["socket", "switch"], "socket_3": ["socket", "switch"],
    "socket_4": ["socket", "switch"],
}


def annotations() -> dict:
    return json.loads((RAW / "ENIGMA-51_annotations_master.json").read_text())


def interactions(video_id: str, ann: dict | None = None) -> list[tuple[float, str, str]]:
    """[(t, verb, object class name)] of one video, in time order."""
    a = ann or annotations()
    verbs = {int(k): v["class_name"] for k, v in a["interaction_types"].items()}
    objs = {int(k): v["class_name"] for k, v in a["object_classes"].items()}
    out = []
    for f in a["frame_annotations"].values():
        if str(f["video_id"]) != str(video_id):
            continue
        ids = {o["id"]: o["class_id"] for o in f.get("objects", [])}
        for it in f.get("interactions", []):
            if it["id_obj"] in ids:
                out.append((float(f["timestamp"]), verbs[it["interaction_category"]], objs[ids[it["id_obj"]]]))
    return sorted(out)


def compile_graphs(budget_usd: float = 3.0, effort: str = "medium") -> dict:
    """Written procedure -> <= 20 steps (Opus, low effort) -> typed graph (L3 compiler, Opus) -> SigLIP2 text
    embeddings. Stops before a compile once spend reaches budget_usd. Saves to data/enigma51/taskgraphs/."""
    from ..paths import load_env
    from ..perception.backbones import SigLIP
    from ..studio.tasks import _split_steps
    load_env()
    from ..tasks.compiler import compile_procedure, embed_graph
    GRAPHS.mkdir(parents=True, exist_ok=True)
    spent, out, sig = 0.0, {}, None
    for tid, (fname, board, sd) in PROCS.items():
        if (GRAPHS / f"{tid}.json").exists():
            out[tid] = "have"
            continue
        if spent >= budget_usd:
            out[tid] = "skipped: budget"
            continue
        text = (RAW / "ENIGMA-51_procedures" / fname).read_text()
        data, c1 = _split_steps(text)
        steps = [{"id": f"s{i + 1}", "name": n} for i, n in enumerate(data["steps"][:20])]
        g = compile_procedure(tid, "maintenance", text, steps, model="claude-opus-5-5", effort=effort,
                              source=f"ENIGMA-51 written procedure {fname}")
        spent += c1 + g.compiler.get("cost_usd", 0.0)
        g.compiler["split_cost_usd"] = c1
        sig = sig or SigLIP()
        emb = embed_graph(g, sig)
        g.save(GRAPHS / f"{tid}.json")
        np.savez(GRAPHS / f"{tid}.npz", **emb)
        out[tid] = {"title": g.title, "n_steps": len(g.nodes), "cost_usd": round(c1 + g.compiler["cost_usd"], 4)}
        print(tid, out[tid], flush=True)
    (OUT / "compile_summary.json").write_text(json.dumps({"graphs": out, "spend_usd": spent}, indent=2))
    return {"graphs": out, "spend_usd": spent}


def library() -> dict:
    from ..tasks.schema import TaskGraph
    return {p.stem: TaskGraph.load(p) for p in sorted(GRAPHS.glob("*.json"))}


def step_objects(g) -> list[set[str]]:
    """Per node: the ENIGMA object classes its parts (and name) mention."""
    out = []
    for n in g.nodes:
        text = " ".join([n.name, *n.parts]).lower()
        out.append({o for o, words in OBJECT_WORDS.items() if any(w in text for w in words)})
    return out


def derived_segments(g, inter: list[tuple[float, str, str]]) -> list[tuple[float, float, str]]:
    """Monotonic alignment of interaction objects to the graph's steps (dynamic programming: each interaction goes to
    a step at or after the previous one's; +1 when the step lists the object). A step spans its first to last assigned
    interaction. DERIVED labels, not human step annotations."""
    so = step_objects(g)
    K, N = len(so), len(inter)
    if N == 0:
        return []
    score = np.full((N + 1, K), -1e9)
    back = np.zeros((N + 1, K), int)
    score[0, :] = 0.0
    for i in range(1, N + 1):
        best, arg = -1e9, 0
        for k in range(K):
            if score[i - 1, k] > best:
                best, arg = score[i - 1, k], k
            score[i, k] = best + (1.0 if inter[i - 1][2] in so[k] else 0.0)
            back[i, k] = arg
    k = int(np.argmax(score[N]))
    assign = [0] * N
    for i in range(N, 0, -1):
        assign[i - 1] = k
        k = back[i, k]
    spans: dict[int, list[float]] = defaultdict(list)
    for (t, _, _), a in zip(inter, assign):
        spans[a].append(t)
    return [(min(v), max(v), g.nodes[k].id) for k, v in sorted(spans.items()) if max(v) > min(v)]


def object_consistency(g, inter, belief_at) -> dict:
    """Share of interactions whose object the believed step lists; chance = mean over interactions of the share of
    steps listing that object."""
    so = {n.id: s for n, s in zip(g.nodes, step_objects(g))}
    hit, chance, n = 0, 0.0, 0
    for t, _, obj in inter:
        b = belief_at(t)
        if b is None:
            continue
        n += 1
        hit += obj in so.get(b, set())
        chance += np.mean([obj in s for s in so.values()])
    return {"n": n, "consistency": hit / n if n else None, "chance": chance / n if n else None}

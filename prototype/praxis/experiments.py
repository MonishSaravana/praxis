"""Experiment drivers. Each writes JSON under results/ and is reproducible from the README commands."""
from __future__ import annotations

import json
import time

import numpy as np

from .data.cc4d import Clip, load_manifest
from .paths import FEATURES, RESULTS


def _items(clips: list[Clip]):
    """(ClipFeatures, boundaries=step ends, onsets=step starts) for clips whose features exist."""
    from .perception.extract import load_features
    out = []
    for c in clips:
        if not (FEATURES / f"{c.clip_id}.npz").exists():
            continue
        f, _ = load_features(c.clip_id)
        dur = float(f.t[-1]) if len(f.t) else 0.0
        ends = [s.end for s in c.segments if 1.0 < s.end < dur - 1.0]
        starts = [s.start for s in c.segments if 1.0 < s.start < dur - 1.0]
        out.append((f, ends, starts))
    return out


def l2(epochs: int = 60) -> dict:
    """Train the event detector on train-split recordings; test on held-out videos and held-out procedure types.
    Head 2 ('onset') is trained on step starts: CaptainCook4D has no hand-object grasp labels, and a new step
    usually starts with picking something up, so onsets are our proxy for grasp events (documented)."""
    from .events.train import run
    man = load_manifest()
    tr = _items([Clip.from_json(c) for c in man["train"]])
    te_vid = _items([Clip.from_json(c) for c in man["eval"]])
    te_type = _items([Clip.from_json(c) for c in man["heldout_type"]])
    print(f"L2: train {len(tr)} recordings, test {len(te_vid)} held-out clips, {len(te_type)} held-out-type recordings", flush=True)
    res = run(tr, {"heldout_videos": te_vid, "heldout_procedure_types": te_type}, epochs=epochs)
    res["train_recordings"] = [f.clip_id for f, _, _ in tr]
    (RESULTS / "l2" / "l2_event_detector.json").write_text(json.dumps(res, indent=2, default=float))
    for k, v in res["test"].items():
        print(k, {m: round(v[m]["f1"], 3) for m in v})
    return res


def probes() -> dict:
    from .tasks.train_probes import fit_all
    return fit_all()



def run_baseline_clip(clip: Clip, baseline, graph, run_name: str, every_s: float = 5.0, mistake_conf: float = 0.7,
                      frames: list | None = None):
    """Stateless ablation: the same model, window by window, no task graph and no persistent state.
    Writes a run log in the engine's format (belief/action/verdict) so the same scorer applies."""
    from .eval.harness import decode_frames
    from .paths import RUNS
    from .runlog import RunLog
    frames = frames if frames is not None else decode_frames(clip)
    names = [n.name for n in graph.nodes]
    name2id = {n.name: n.id for n in graph.nodes}
    out = RUNS / run_name / f"{clip.clip_id}.jsonl"
    with RunLog(out, {"clip": clip.clip_id, "run": run_name, "task_id": clip.task_id, "baseline": baseline.model,
                      "every_s": every_s, "mistake_conf": mistake_conf}) as log:
        log.write("task", 0.0, task_id=clip.task_id, title=graph.title, oracle=True, posterior=None, n_steps=len(names))
        t = every_s
        n_frames = len(frames)
        while t <= clip.duration:
            idx = [int(round((t - k) * 4)) for k in (2, 1, 0)]
            fr = [frames[i] for i in idx if 0 <= i < n_frames]
            r = baseline.query(fr, graph.title, names, frame_ages=[2.0, 1.0, 0.0][-len(fr):])
            if "error" in r:
                log.write("verdict", t, node=None, reason="schedule", status="error", confidence=0.0, mistake=None,
                          visibility="ok", view_request=None, model=baseline.model, role="baseline", prompt_version="",
                          latency_ms=0.0, input_tokens=0, output_tokens=0, cost_usd=0.0, orig_cost_usd=0.0, cached=False,
                          error=r["error"])
            else:
                sid = name2id.get(r["current_step"], "")
                log.write("verdict", t, node=sid, reason="schedule", status="baseline", confidence=r["step_confidence"],
                          mistake={"description": r["mistake_description"], "correction": r["correction"]} if r["mistake"] else None,
                          visibility="ok", view_request=None, model=r["model"], role="baseline", prompt_version=r["prompt_version"],
                          latency_ms=r["latency_ms"], input_tokens=r["input_tokens"], output_tokens=r["output_tokens"],
                          cost_usd=0.0 if r.get("cached") else r["cost_usd"], orig_cost_usd=r["cost_usd"],
                          cached=r.get("cached", False), error=None, mistake_confidence=r["mistake_confidence"])
                t_out = t + r["latency_ms"] / 1000
                log.write("belief", t_out, p={sid or "none": r["step_confidence"]}, entropy=0.0, map=sid,
                          map_p=r["step_confidence"], time_on_step=0.0, completed=[])
                if r["mistake"] and r["mistake_confidence"] >= mistake_conf:
                    log.write("action", t_out, action="mistake", text=r["correction"] or r["mistake_description"], node=sid,
                              detail={"what": r["mistake_description"], "p": r["mistake_confidence"]})
            t += every_s
        log.write("summary", clip.duration, n_frames=n_frames, escalated_frames=3 * int(clip.duration // every_s), wall_s=0.0)
    return out


if __name__ == "__main__":
    import sys
    t0 = time.time()
    {"l2": l2, "probes": probes}[sys.argv[1]]()
    print("done in", round(time.time() - t0), "s")

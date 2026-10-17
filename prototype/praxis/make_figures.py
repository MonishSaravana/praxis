"""Generate results/figures/*.png from results JSON (no numbers typed by hand)."""
from __future__ import annotations

import json

import numpy as np

from .eval import figures as F
from .paths import DATA, RESULTS


def main() -> list[str]:
    out = []
    runs = {n: F.load(f"runs/{n}.json") for n in ("baseline_stateless", "fused", "fused_oracle", "local_only",
                                                   "verifier_only", "fused_heuristic_gate", "fused_no_escalation",
                                                   "fused_claude_fast", "fused_distilled")}
    if runs["baseline_stateless"] and runs["fused"]:
        m = {"Stateless baseline\n(Opus 5.5 every 5 s)": runs["baseline_stateless"]["aggregate"],
             "Praxis (stateful)": runs["fused"]["aggregate"]}
        out.append(str(F.stateful_vs_stateless(m, note=f"{runs['fused']['aggregate']['n_clips']} CaptainCook4D clips")))
    # L4 ablation
    abl = {k: v["aggregate"]["step_acc"] for k, v in (("Local evidence only", runs["local_only"]),
                                                      ("Verifier only", runs["verifier_only"]),
                                                      ("Fused (ours)", runs["fused_oracle"])) if v}
    if abl:
        out.append(str(F.bars(abl, "State tracker ablation: step accuracy (task given)", "l4_ablation", "{:.0%}",
                              colors=[F.C_BASE, F.C_ALT, F.C_OURS][-len(abl):])))
    # latency distributions
    dist = {}
    vl = []
    for name in ("jev", "claude_fast", "claude_strong"):
        p = DATA / "verdicts" / f"{name}_eval.jsonl"
        if p.exists():
            rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
            vl = [r["verdict"]["latency_ms"] for r in rows if not r["verdict"]["raw"].get("cached") and not r["verdict"].get("error")]
            if vl:
                dist[{"jev": "Jev 1.14 (fast tier)", "claude_fast": "Claude Haiku 5.5", "claude_strong": "Claude Opus 5.5 (strong tier)"}[name]] = vl
    if dist:
        out.append(str(F.latency(dist, "Verifier latency per call (held-out checks)", "ms")))
    if runs["fused"]:
        fb = [x for r in runs["fused"]["per_clip"] for x in r["feedback_latency_s"]]
        if fb:
            out.append(str(F.bars({"p50": float(np.percentile(fb, 50)), "p95": float(np.percentile(fb, 95))},
                                  "Feedback latency: GT step end → Praxis feedback (s)", "feedback_latency", "{:.1f}s")))
        out.append(str(F.per_category(runs["fused"]["per_category"], "step_acc", "Step accuracy by procedure (Praxis)")))
    cal = F.load("l5/calibration.json")
    if cal:
        for k, v in cal.items():
            out.append(str(F.calibration(v["reliability_raw"], v.get("reliability_calibrated"), v["ece_raw"],
                                         v.get("ece_calibrated"), k)))
    d = F.load("l7/distill.json")
    if d:
        out.append(str(F.student_vs_teacher(d)))
    fr = F.load("l5/framing_ablation.json")
    if fr:
        vals = {f"{r['verifier']}\n{r['framing']}": r["auroc"] for r in fr["rows"]}
        out.append(str(F.bars(vals, "Verifier AUROC by evidence framing (100 train checks)", "framing_ablation", "{:.2f}")))
    l2 = F.load("l2/l2_event_detector.json")
    if l2:
        vals = {}
        for split, by_tol in l2["test"].items():
            for m in ("learned", "heuristic"):
                vals[f"{m}\n{split.replace('heldout_', '').replace('_', ' ')}"] = by_tol["tol5s"][m]["f1"]
        out.append(str(F.bars(vals, "L2 boundary detection F1 (±5 s)", "l2_event_detector", "{:.2f}")))
    u = F.load("l5/visual_uncertainty.json")
    if u:
        modes = [m for m in u["modes"] if m != "none"]
        vals = {}
        for m in modes:
            vals[f"{m}\nPraxis asks"] = u["modes"][m]["engine_view_request_rate"]
            vals[f"{m}\nbaseline wrong"] = u["modes"][m]["baseline_confident_wrong_step_rate"]
        out.append(str(F.bars(vals, "Degraded views: Praxis asks for a better view vs. baseline confidently wrong",
                              "visual_uncertainty", "{:.0%}", colors=[F.C_OURS, F.C_BASE] * len(modes))))
    return out


if __name__ == "__main__":
    for p in main():
        print(p)

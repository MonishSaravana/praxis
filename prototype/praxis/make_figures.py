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
    so, sb = F.load("l6/mistake_semantic_fused_oracle.json"), F.load("l6/mistake_semantic_baseline_stateless.json")
    if runs["baseline_stateless"] and runs["fused_oracle"] and so and sb:
        B, O = runs["baseline_stateless"]["aggregate"], runs["fused_oracle"]["aggregate"]
        rows = {"Stateless baseline\n(Opus 5.5 every 5 s)": {"step_acc": B["step_acc"], "mistakes_correct": sb["semantic_yes"],
                                                             "strict_fa_per_min": sb["strict_false_alarms_per_min"],
                                                             "cost_per_min": B["cost_usd_per_video_min"]},
                "Praxis\n(stateful)": {"step_acc": O["step_acc"], "mistakes_correct": so["semantic_yes"],
                                       "strict_fa_per_min": so["strict_false_alarms_per_min"],
                                       "cost_per_min": O["cost_usd_per_video_min"]}}
        out.append(str(F.stateful_vs_stateless(rows, note=f"{O['n_clips']} held-out CaptainCook4D clips; mistakes judged "
                                                           f"against {so['n_gt_mistakes']} annotated errors")))
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
        vals, cols = {}, []
        for m in modes:
            x = u["modes"][m]
            vals[f"{m}\nPraxis asks"] = x["engine_view_request_rate"]
            vals[f"{m}\nbaseline wrong\n(conf ≥ 0.5)"] = x["threshold_sweep"]["0.5"]["baseline_confident_wrong_step"]
            vals[f"{m}\nbaseline wrong\n(conf ≥ 0.7)"] = x["threshold_sweep"]["0.7"]["baseline_confident_wrong_step"]
            cols += [F.C_OURS, F.C_BASE, "#c9ccd1"]
        ew = max(u["modes"][m]["threshold_sweep"]["0.5"]["engine_confident_wrong"] for m in modes)
        eng = "and is never confidently wrong" if ew == 0 else f"confidently wrong ≤ {ew:.0%}"
        out.append(str(F.bars(vals, f"Degraded views: Praxis asks for a better view ({eng})\n"
                                    "vs. the stateless baseline answering confidently and wrongly",
                              "visual_uncertainty", "{:.0%}", colors=cols)))
    return out


if __name__ == "__main__":
    for p in main():
        print(p)

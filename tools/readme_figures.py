"""Figures for the top-level README, read straight from results/**/*.json (no hand-typed numbers).

    python3 tools/readme_figures.py      # -> docs/media/fig_*.png
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "media"
FONTS = ROOT / "brand" / "deck" / "v1" / "fonts"

ORANGE = "#FF5B14"
INK = "#1D2225"
GRAY = "#A9B0B4"
LIGHT = "#D5DADC"
MUTED = "#5E676C"

for f in FONTS.glob("Archivo-*.ttf"):
    font_manager.fontManager.addfont(str(f))
plt.rcParams.update({
    "font.family": "Archivo",
    "font.size": 11,
    "axes.edgecolor": LIGHT,
    "axes.labelcolor": MUTED,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.titleweight": "semibold",
    "axes.titlesize": 12.5,
    "axes.titlecolor": INK,
    "axes.titlelocation": "left",
    "axes.titlepad": 12,
    "figure.dpi": 200,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.25,
})


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


def bars(ax, labels, values, colors, fmt, title, ymax=None):
    xs = range(len(values))
    ax.bar(xs, values, color=colors, width=0.62)
    ax.set_xticks(list(xs), labels)
    ax.set_yticks([])
    ax.tick_params(axis="x", length=0)
    ax.set_title(title)
    top = ymax or max(values) * 1.25
    ax.set_ylim(0, top)
    for x, v in zip(xs, values):
        ax.text(x, v + top * 0.02, fmt(v), ha="center", va="bottom", color=INK, fontsize=12, fontweight="semibold")


def footer(fig, text):
    fig.text(0.0, -0.04, text, ha="left", va="top", color=MUTED, fontsize=8.5)


def fig_headline():
    m = load("results/metrics.json")
    p, b = m["run_fused_oracle"], m["run_baseline_stateless"]
    sp, sb = m["semantic_fused_oracle"], m["semantic_baseline_stateless"]
    labels = ["Opus every 5 s\n(stateless)", "Praxis\n(stateful)"]
    cols = [GRAY, ORANGE]
    fig, axs = plt.subplots(1, 4, figsize=(13, 3.6))
    bars(axs[0], labels, [b["step_acc"] * 100, p["step_acc"] * 100], cols, lambda v: f"{v:.0f}%",
         "Step accuracy", 70)
    bars(axs[1], labels, [sb["semantic_yes"], sp["semantic_yes"]], cols, lambda v: f"{v:.0f}",
         "Mistakes named correctly\n(judge-verified)", 5.5)
    bars(axs[2], labels, [b["mistakes"]["tp"], p["mistakes"]["tp"]], cols, lambda v: f"{v:.0f}",
         "Annotated mistakes flagged\n(time-window)", 16)
    bars(axs[3], labels, [b["cost_usd_per_video_min"] * 100, p["cost_usd_per_video_min"] * 100], cols,
         lambda v: f"{v:.1f}¢", "Cost per video-minute", 11)
    fig.subplots_adjust(wspace=0.35)
    footer(fig, "Same frontier model (Claude Opus 5.5), same 48 held-out CaptainCook4D clips (235 min), task given to both. "
                "Sources: results/runs/{fused_oracle,baseline_stateless}.json, results/l6/mistake_semantic_*.json")
    fig.savefig(OUT / "fig_headline.png")
    plt.close(fig)


def fig_ablation():
    m = load("results/metrics.json")
    runs = [("Local evidence only\n(no model calls)", m["run_local_only"], GRAY),
            ("Frontier verifier only\n(every 5 s, no local evidence)", m["run_verifier_only"], GRAY),
            ("Fused in the\nstate tracker", m["run_fused_oracle"], ORANGE)]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    bars(ax, [r[0] for r in runs], [r[1]["step_acc"] * 100 for r in runs], [r[2] for r in runs],
         lambda v: f"{v:.0f}%", "Step accuracy: the tracker is worth more than either evidence source", 70)
    for x, r in enumerate(runs):
        ax.text(x, 3, f"{r[1]['verifier_calls']:,} calls", ha="center", va="bottom", color="white", fontsize=9)
    footer(fig, "48 held-out clips, task given. Sources: results/runs/{local_only,verifier_only,fused_oracle}.json")
    fig.savefig(OUT / "fig_ablation.png")
    plt.close(fig)


def fig_uncertainty():
    modes = load("results/metrics.json")["uncertainty"]["modes"]
    names = [("blur", "Blurred"), ("occlude", "Occluded"), ("crop_away", "Work area\ncropped out")]
    fig, ax = plt.subplots(figsize=(8.4, 3.6))
    w = 0.26
    for i, (k, _) in enumerate(names):
        v = modes[k]
        vals = [v["engine_view_request_rate"] * 100, v["threshold_sweep"]["0.5"]["engine_confident_wrong"] * 100,
                v["threshold_sweep"]["0.5"]["baseline_confident_wrong_step"] * 100]
        for j, (val, c) in enumerate(zip(vals, [ORANGE, INK, GRAY])):
            x = i + (j - 1) * w
            ax.bar(x, max(val, 0.6), width=w * 0.92, color=c)
            ax.text(x, val + 2, f"{val:.0f}%", ha="center", va="bottom", fontsize=10.5, color=INK, fontweight="semibold")
    ax.set_xticks(range(len(names)), [n for _, n in names])
    ax.set_yticks([])
    ax.tick_params(axis="x", length=0)
    ax.set_ylim(0, 115)
    ax.set_title("Degraded views: Praxis asks for a better view instead of guessing")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=ORANGE, label="Praxis asks for a better view"),
                       Patch(color=INK, label="Praxis confident (≥0.5) and wrong"),
                       Patch(color=GRAY, label="Stateless Opus confident (≥0.5) and wrong")],
              frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=9.5)
    footer(fig, "60 mid-step held-out checks per condition, Claude Opus 5.5 in both arms. Source: results/l5/visual_uncertainty.json")
    fig.savefig(OUT / "fig_uncertainty.png")
    plt.close(fig)


def fig_repair():
    mo = load("results/metrics.json")["enigma_backend_flow"]["moments"]
    arms = [("General VLM,\nno procedure", mo["general"], GRAY),
            ("General VLM\n+ written procedure", mo["general+doc"], GRAY),
            ("Praxis\n(compiled procedure)", mo["backend_praxis_shown"], ORANGE)]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    xs = range(len(arms))
    right = [a[1]["correct"] / a[1]["n"] * 100 for a in arms]
    adj = [a[1]["adjacent"] / a[1]["n"] * 100 for a in arms]
    ax.bar(xs, right, color=[a[2] for a in arms], width=0.62)
    ax.bar(xs, adj, bottom=right, color=[a[2] for a in arms], alpha=0.35, width=0.62)
    for x, r, a in zip(xs, right, adj):
        ax.text(x, r / 2, f"{r:.0f}%", ha="center", va="center", color="white", fontsize=12, fontweight="semibold")
        ax.text(x, r + a + 2, f"{r + a:.0f}% within one step", ha="center", va="bottom", color=INK, fontsize=9.5)
    ax.set_xticks(list(xs), [a[0] for a in arms])
    ax.set_yticks([])
    ax.tick_params(axis="x", length=0)
    ax.set_ylim(0, 95)
    ax.set_title("Real repair footage: is the instruction on screen the right step?")
    footer(fig, "ENIGMA-51, 66 moments from 4 first-person repair videos, blind judge; step labels derived from object-interaction labels.\n"
                "Source: results/enigma51/backend_flow.json")
    fig.savefig(OUT / "fig_repair.png")
    plt.close(fig)


def fig_multitask():
    m = load("results/metrics.json")
    s, t = m["mt_eval_splices_single"], m["mt_eval_splices_mt"]
    n_sw = t["switches_detected"] + t["missed_switches"]
    rows = [("Step accuracy", s["step_acc"] * 100, t["step_acc"] * 100, "%"),
            ("Time on the right task", s["correct_task_share"] * 100, t["correct_task_share"] * 100, "%"),
            (f"Task switches caught (of {n_sw})", s["switches_detected"], t["switches_detected"], ""),
            (f"Paused jobs resumed (of {t['resume']['n']})", s["resume"]["resumed"], t["resume"]["resumed"], "")]
    fig, axs = plt.subplots(1, 4, figsize=(13, 3.4))
    for ax, (title, a, b, unit) in zip(axs, rows):
        top = 70 if unit == "%" else max(a, b) * 1.3
        bars(ax, ["Single-task", "Multi-task"], [a, b], [GRAY, ORANGE], lambda v, u=unit: f"{v:.0f}{u}", title, top)
    fig.subplots_adjust(wspace=0.35)
    footer(fig, "Synthetic sessions spliced from held-out clips (167 min): switch, switch-and-return, and off-library interruptions. "
                "Sources: results/multitask/eval_splices_{single,mt}.json")
    fig.savefig(OUT / "fig_multitask.png")
    plt.close(fig)


def fig_live():
    a = load("results/live/live_replay_10_18_0.json")["summary"]
    b = load("results/live/live_replay_async.json")["summary"]
    labels = ["Model calls\ninline", "Async\nslow path"]
    cols = [GRAY, ORANGE]
    fig, axs = plt.subplots(1, 3, figsize=(10, 3.4))
    bars(axs[0], labels, [a["tick_lag_s"]["max"], b["tick_lag_s"]["max"]], cols, lambda v: f"{v:.2f} s",
         "Worst lag behind the camera", 5.5)
    bars(axs[1], labels, [a["tick_ms"]["p95"], b["tick_ms"]["p95"]], cols, lambda v: f"{v:.0f} ms",
         "Tick compute, p95", 210)
    bars(axs[2], labels, [a["dropped_frames"], b["dropped_frames"]], cols, lambda v: f"{v:.0f}",
         "Frames dropped (of ~600)", 35)
    fig.subplots_adjust(wspace=0.35)
    footer(fig, "Same 150 s recording replayed at wall-clock speed through the live loop, task not given. "
                "Sources: results/live/live_replay_{10_18_0,async}.json")
    fig.savefig(OUT / "fig_live.png")
    plt.close(fig)


def fig_distill():
    d = load("results/metrics.json")["distillation"]
    r = d["routed_conf0.7"]
    fig, axs = plt.subplots(1, 3, figsize=(10, 3.4))
    labels = ["Opus\n(teacher)", "Student\n(local)", "Routed\n(student if sure)"]
    cols = [GRAY, ORANGE, ORANGE]
    bars(axs[0], labels, [d["teacher_acc_vs_gt"] * 100, d["student_acc_vs_gt"] * 100, r["acc_vs_gt"] * 100], cols,
         lambda v: f"{v:.0f}%", "Accuracy vs ground truth", 100)
    bars(axs[1], labels, [d["teacher_cost_per_1k_checks_usd"], d["student_cost_per_1k_checks_usd"], r["cost_per_1k_usd"]],
         cols, lambda v: f"${v:.2f}", "Cost per 1,000 checks", 13)
    axs[2].axis("off")
    axs[2].text(0.0, 0.75, f"{d['student_latency_ms_p50']:.2f} ms", fontsize=28, color=ORANGE, fontweight="semibold")
    axs[2].text(0.0, 0.6, "student latency per check (CPU)", fontsize=10.5, color=MUTED)
    axs[2].text(0.0, 0.3, f"{d['teacher_latency_ms_p50'] / 1000:.1f} s", fontsize=28, color=GRAY, fontweight="semibold")
    axs[2].text(0.0, 0.15, "frontier teacher latency per check", fontsize=10.5, color=MUTED)
    fig.subplots_adjust(wspace=0.35)
    footer(fig, f"{d['n_test']} held-out completion checks. Source: results/l7/distill.json")
    fig.savefig(OUT / "fig_distill.png")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for f in (fig_headline, fig_ablation, fig_uncertainty, fig_repair, fig_multitask, fig_live, fig_distill):
        f()
        print("wrote", f.__name__)

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
FONTS = ROOT / "brand" / "fonts"

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


def fig_taskgraph():
    """A compiled task graph: steps laid out by prerequisite depth, with duration priors and check/mistake counts."""
    from matplotlib.patches import FancyBboxPatch

    g = load("prototype/taskgraphs/cc4d_cucumberraita.json")
    nodes = {n["id"]: n for n in g["nodes"]}
    preds = {k: [] for k in nodes}
    for n in g["nodes"]:
        for s in n.get("successors", []):
            if s in preds:
                preds[s].append(n["id"])
    depth = {}

    def d(k):
        if k not in depth:
            depth[k] = 0 if not preds[k] else 1 + max(d(p) for p in preds[k])
        return depth[k]

    for k in nodes:
        d(k)
    cols = {}
    for k, v in sorted(depth.items(), key=lambda kv: (kv[1], kv[0])):
        cols.setdefault(v, []).append(k)
    W, H, dx, dy = 2.35, 0.82, 2.95, 1.12
    pos = {}
    for c, ks in cols.items():
        for i, k in enumerate(ks):
            pos[k] = (c * dx, -(i - (len(ks) - 1) / 2) * dy)
    fig, ax = plt.subplots(figsize=(15, 5.4))
    for k, n in nodes.items():
        x, y = pos[k]
        for s in n.get("successors", []):
            if s in pos:
                x2, y2 = pos[s]
                ax.annotate("", xy=(x2 - W / 2, y2), xytext=(x + W / 2, y),
                            arrowprops=dict(arrowstyle="-|>", color=GRAY, lw=1.1, shrinkA=2, shrinkB=2,
                                            connectionstyle="arc3,rad=-0.12"), zorder=1)
    for k, n in nodes.items():
        x, y = pos[k]
        start = k in g.get("start", [])
        ax.add_patch(FancyBboxPatch((x - W / 2, y - H / 2), W, H, boxstyle="round,pad=0.02,rounding_size=0.08",
                                    fc="#FFF1EA" if start else "#F6F7F6", ec=ORANGE if start else INK, lw=1.3,
                                    zorder=3))
        name = n["name"] if len(n["name"]) <= 27 else n["name"][:25] + "…"
        ax.text(x - W / 2 + 0.1, y + 0.16, name, fontsize=9.6, color=INK, weight="semibold", va="center", zorder=4)
        dur = n.get("duration") or {}
        meta = f"~{dur.get('mean_s', 0):.0f} s ± {dur.get('std_s', 0):.0f}  ·  {len(n.get('checks', []))} checks  ·  {len(n.get('mistakes', []))} mistakes"
        ax.text(x - W / 2 + 0.1, y - 0.17, meta, fontsize=8, color=MUTED, va="center", zorder=4)
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    ax.set_xlim(min(xs) - W / 2 - 0.1, max(xs) + W / 2 + 0.1)
    ax.set_ylim(min(ys) - H, max(ys) + H)
    ax.axis("off")
    ax.set_title(f"Compiled task graph: {g['title']} ({len(nodes)} steps). Orange = valid start steps; "
                 "arrows = allowed successors", loc="left")
    fig.text(0.01, -0.02, "Durations are lognormal priors fit on train-split recordings. "
             "Source: prototype/taskgraphs/cc4d_cucumberraita.json", fontsize=9, color=MUTED)
    fig.savefig(OUT / "fig_taskgraph.png")
    plt.close(fig)


def fig_belief():
    """Step belief over time vs ground truth on one held-out clip, with verifier calls and policy actions."""
    import numpy as np

    html = (ROOT / "renders/viewer/fused_10_18_0.html").read_text()
    i = html.index("const D = ") + len("const D = ")
    D, _ = json.JSONDecoder().raw_decode(html[i:])
    recs = [json.loads(line) for line in (ROOT / "runs/fused/10_18_0.jsonl").read_text().splitlines()]
    beliefs = [r for r in recs if r["kind"] == "belief"]
    verdicts = [r for r in recs if r["kind"] == "verdict"]
    actions = [r for r in recs if r["kind"] == "action"]
    names = D["names"]
    gt = D["gt"]
    order = []
    for _, _, k, _ in gt:
        if k not in order:
            order.append(k)
    peak = {k: max(b["p"].get(k, 0.0) for b in beliefs) for k in names}
    order += [k for k in names if k not in order and peak[k] >= 0.15]
    T = np.array([b["t"] for b in beliefs])
    P = np.array([[b["p"].get(k, 0.0) for k in order] for b in beliefs]).T
    fig, ax = plt.subplots(figsize=(15, 1.6 + 0.42 * len(order)))
    from matplotlib.colors import LinearSegmentedColormap

    cmap = LinearSegmentedColormap.from_list("p", ["#FFFFFF", "#FFD2BD", ORANGE, "#B53A00"])
    ax.imshow(P, aspect="auto", cmap=cmap, vmin=0, vmax=1, interpolation="nearest",
              extent=(T[0], T[-1], len(order) - 0.5, -0.5))
    for a, b_, k, err in gt:
        r = order.index(k)
        ax.add_patch(plt.Rectangle((a, r - 0.45), b_ - a, 0.9, fill=False, ec=INK, lw=1.6, ls="-"))
        if err:
            ax.text(b_ + 1, r, "annotated error", fontsize=8, color=INK, va="center")
    for v in verdicts:
        ax.plot([v["t"]], [-0.95], marker="|", color=INK if v.get("role") == "fast" else ORANGE, ms=9, mew=1.6,
                clip_on=False)
    tasks = [r for r in recs if r["kind"] == "task"]
    if len(tasks) > 1 or (tasks and tasks[0]["t"] > 0):
        t0 = next((r["t"] for r in tasks if r["t"] > 0), None)
        if t0 is not None:
            ax.axvline(t0, color=MUTED, lw=0.8, ls=(0, (2, 2)))
            ax.text(t0 + 1, len(order) - 0.2, "task recognized", fontsize=8.6, color=MUTED, va="bottom")
    lane = 0
    for a in actions:
        if a["action"] in ("mistake", "view_request"):
            ax.axvline(a["t"], color=INK, lw=0.8, ls=(0, (3, 3)))
            label = "mistake flagged" if a["action"] == "mistake" else "asked for a better view"
            ax.text(a["t"] + 1, len(order) + 0.25 + 0.42 * (lane % 2), label, fontsize=8.6, color=INK, va="bottom",
                    bbox=dict(fc="white", ec="none", pad=1.2))
            lane += 1
    ax.set_yticks(range(len(order)), [names[k] for k in order], fontsize=9)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("seconds", fontsize=9)
    ax.set_ylim(len(order) + 0.9, -1.4)
    ax.set_title(f"Tracker belief vs ground truth on a held-out clip (task not given, "
                 f"{D['metrics'].get('step accuracy', '')} step accuracy)", loc="left")
    ax.text(0, 1.0, "shading = P(step)   ·   black boxes = annotated step segments   ·   "
            "ticks = verifier calls (black: fast tier, orange: Opus escalation)", transform=ax.transAxes,
            fontsize=9, color=MUTED, va="bottom")
    fig.text(0.01, -0.03, "Pinwheels, CaptainCook4D 10_18. Source: runs/fused/10_18_0.jsonl (engine log); ground truth "
             "from CaptainCook4D via renders/viewer/fused_10_18_0.html", fontsize=9, color=MUTED)
    fig.savefig(OUT / "fig_belief.png")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for f in (fig_headline, fig_ablation, fig_uncertainty, fig_repair, fig_multitask, fig_live, fig_distill, fig_taskgraph, fig_belief):
        f()
        print("wrote", f.__name__)

"""Slide-ready PNG charts from results/*.json (white background, large type). Numbers come only from files."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from ..paths import FIGURES, RESULTS  # noqa: E402

INK = "#1c1e22"
SUB = "#5c6068"
C_OURS = "#2bb673"
C_BASE = "#9aa0a8"
C_ALT = "#3b82f6"
C_WARN = "#f5a623"

plt.rcParams.update({"font.family": "Helvetica", "font.size": 15, "axes.titlesize": 19, "axes.titleweight": "bold",
                     "axes.labelsize": 15, "axes.edgecolor": "#c9ccd1", "axes.labelcolor": INK, "xtick.color": SUB,
                     "ytick.color": SUB, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150,
                     "savefig.facecolor": "white", "figure.facecolor": "white"})


def _save(fig, name: str) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    p = FIGURES / f"{name}.png"
    fig.tight_layout()
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


def _label(ax, bars, fmt="{:.2f}"):
    for b in bars:
        h = b.get_height()
        ax.text(b.get_x() + b.get_width() / 2, h, fmt.format(h), ha="center", va="bottom", fontsize=13, color=INK)


def stateful_vs_stateless(rows: dict, note: str = "") -> Path:
    """rows: {label: {"step_acc", "mistakes_correct", "strict_fa_per_min", "cost_per_min"}}"""
    names = list(rows)
    metrics = [("Step accuracy (task given)", "step_acc", "{:.0%}"),
               ("Real mistakes caught\n(judge-verified)", "mistakes_correct", "{:.0f}"),
               ("Strict false alarms / min", "strict_fa_per_min", "{:.3f}"),
               ("Cost per video-minute (USD)", "cost_per_min", "${:.3f}")]
    fig, axes = plt.subplots(1, len(metrics), figsize=(17, 4.8))
    for ax, (title, key, fmt) in zip(axes, metrics):
        vals = [rows[n][key] or 0.0 for n in names]
        bars = ax.bar(range(len(names)), vals, color=[C_BASE if "tateless" in n else C_OURS for n in names], width=0.6)
        _label(ax, bars, fmt)
        ax.set_xticks(range(len(names)), names, fontsize=12)
        ax.set_title(title, fontsize=16)
        ax.set_ylim(0, max(vals + [1e-3]) * 1.3)
    fig.suptitle("Stateful engine vs. stateless baseline (same strong model, same clips, task given to both)"
                 + (f"\n{note}" if note else ""), fontsize=15, color=SUB, y=1.1)
    return _save(fig, "stateful_vs_stateless")


def latency(dist: dict[str, list[float]], title: str = "Latency", unit: str = "ms") -> Path:
    fig, ax = plt.subplots(figsize=(10, 4.8))
    labels = list(dist)
    data = [np.asarray(dist[k], float) for k in labels]
    parts = ax.boxplot(data, orientation="horizontal", tick_labels=labels, showfliers=False, patch_artist=True, widths=0.5)
    for i, b in enumerate(parts["boxes"]):
        b.set_facecolor([C_OURS, C_ALT, C_BASE, C_WARN][i % 4])
        b.set_alpha(0.75)
    for i, d in enumerate(data):
        if len(d):
            ax.text(np.percentile(d, 95), i + 1.3, f"p50 {np.percentile(d, 50):.0f} · p95 {np.percentile(d, 95):.0f} {unit}",
                    fontsize=12, color=SUB, ha="right")
    ax.set_xlabel(unit)
    ax.set_title(title)
    return _save(fig, "latency")


def per_category(cat: dict, key: str = "step_acc", title: str = "Step accuracy by procedure") -> Path:
    names = sorted(cat, key=lambda k: -(cat[k].get(key) or 0))
    vals = [cat[k].get(key) or 0 for k in names]
    fig, ax = plt.subplots(figsize=(11, 4.8))
    bars = ax.barh(range(len(names)), vals, color=C_OURS)
    ax.set_yticks(range(len(names)), [n.replace("cc4d_", "") for n in names])
    ax.invert_yaxis()
    for b, v in zip(bars, vals):
        ax.text(v + 0.01, b.get_y() + b.get_height() / 2, f"{v:.0%}", va="center", fontsize=12)
    ax.set_xlim(0, 1)
    ax.set_title(title)
    return _save(fig, f"per_category_{key}")


def calibration(rel_raw: dict, rel_cal: dict | None, ece_raw: float, ece_cal: float | None, name: str) -> Path:
    fig, ax = plt.subplots(figsize=(6.2, 6))
    ax.plot([0, 1], [0, 1], "--", color=C_BASE, lw=1.5)
    for rel, col, lab in ((rel_raw, C_WARN, f"raw (ECE {ece_raw:.3f})"),
                          (rel_cal, C_OURS, f"calibrated (ECE {ece_cal:.3f})" if ece_cal is not None else None)):
        if not rel:
            continue
        xs = [b["conf"] for b in rel["bins"] if b["n"] > 0]
        ys = [b["acc"] for b in rel["bins"] if b["n"] > 0]
        ns = [b["n"] for b in rel["bins"] if b["n"] > 0]
        ax.plot(xs, ys, "o-", color=col, lw=2.5, label=lab)
        ax.scatter(xs, ys, s=[20 + 3 * n for n in ns], color=col, alpha=0.35)
    ax.set_xlabel("predicted P(step complete)")
    ax.set_ylabel("observed frequency")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend(loc="upper left", frameon=False)
    ax.set_title(f"Reliability: {name}")
    return _save(fig, f"calibration_{name}")


def student_vs_teacher(d: dict) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    names = ["Teacher (frontier)", "Student (ours, local)"]
    acc = [d["teacher_acc_vs_gt"], d["student_acc_vs_gt"]]
    lat = [d["teacher_latency_ms_p50"], d["student_latency_ms_p50"]]
    cost = [d["teacher_cost_per_1k_checks_usd"], d["student_cost_per_1k_checks_usd"]]
    for ax, vals, title, fmt, log in ((axes[0], acc, "Accuracy vs ground truth", "{:.0%}", False),
                                      (axes[1], lat, "Latency per check (ms, log)", "{:.3g}", True),
                                      (axes[2], cost, "Cost per 1,000 checks (USD)", "${:.3f}", False)):
        bars = ax.bar(names, vals, color=[C_ALT, C_OURS], width=0.55)
        _label(ax, bars, fmt)
        if log:
            ax.set_yscale("log")
        ax.set_title(title)
    fig.suptitle(f"Distillation on held-out clips: student agrees with teacher on {d['agreement']:.0%} of checks",
                 fontsize=16, color=SUB, y=1.05)
    return _save(fig, "student_vs_teacher")


def bars(values: dict[str, float], title: str, name: str, fmt: str = "{:.2f}", colors: list | None = None, ylabel: str = "") -> Path:
    fig, ax = plt.subplots(figsize=(max(7, 1.6 * len(values)), 4.6))
    bs = ax.bar(list(values), list(values.values()), color=colors or [C_OURS] * len(values), width=0.6)
    _label(ax, bs, fmt)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, max(list(values.values()) + [1e-3]) * 1.25)
    plt.setp(ax.get_xticklabels(), fontsize=12)
    return _save(fig, name)


def load(rel: str) -> dict | None:
    p = RESULTS / rel
    return json.loads(p.read_text()) if p.exists() else None

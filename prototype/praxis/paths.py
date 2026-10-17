"""Filesystem layout. Heavy artifacts (raw video, features, checkpoints) live outside git."""
from __future__ import annotations

import os
from pathlib import Path

PROTO = Path(__file__).resolve().parents[1]          # prototype/
ROOT = PROTO.parent                                   # repo root
DATA = ROOT / "data"                                  # raw video + annotations (gitignored)
CACHE = ROOT / "cache"                                # model weights, API cache (gitignored)
FEATURES = DATA / "features"                          # L1 features per clip (gitignored)
CKPT = DATA / "checkpoints"                           # trained heads (gitignored)
RUNS = ROOT / "runs"                                  # JSONL run logs (gitignored; summaries copied to results/)
RESULTS = ROOT / "results"
FIGURES = RESULTS / "figures"
RENDERS = ROOT / "renders"
TASKGRAPHS = PROTO / "taskgraphs"                     # compiled task graphs (committed)
CONFIGS = PROTO / "configs"

os.environ.setdefault("HF_HOME", str(CACHE / "hf"))
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("MPLCONFIGDIR", str(CACHE / "mpl"))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def ensure_dirs() -> None:
    for p in (DATA, CACHE, FEATURES, CKPT, RUNS, RESULTS, FIGURES, RENDERS, TASKGRAPHS):
        p.mkdir(parents=True, exist_ok=True)


def load_env() -> None:
    """Load API keys from repo-root .env (never printed, never committed)."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover
        return
    for f in (ROOT / ".env", PROTO / ".env"):
        if f.exists():
            load_dotenv(f, override=False)

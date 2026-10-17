"""Filesystem layout. Heavy artifacts (raw video, features, checkpoints) live outside git."""
from __future__ import annotations

import os
import socket
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
os.environ.setdefault("HF_HUB_OFFLINE", "1")          # weights are cached; hub update checks hang on this network
os.environ.setdefault("MPLCONFIGDIR", str(CACHE / "mpl"))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


# IPv6 is black-holed on the dev network (VPN): Python tries AAAA addresses first and waits for a connect
# timeout before IPv4 (curl's happy-eyeballs hides this). Prefer IPv4 for every client in-process.
if os.environ.get("PRAXIS_IPV4_FIRST", "1") == "1" and not getattr(socket, "_praxis_v4", False):
    _gai = socket.getaddrinfo

    def _getaddrinfo_v4_first(host, port, family=0, *args, **kwargs):
        res = _gai(host, port, family, *args, **kwargs)
        v4 = [r for r in res if r[0] == socket.AF_INET]
        return v4 or res

    socket.getaddrinfo = _getaddrinfo_v4_first
    socket._praxis_v4 = True


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

"""Spend guard for the company backend: the existing Budget(max_calls, max_usd), with its running total kept in a
ledger file (sessions/orgs/spend.json) so the cap holds across Studio restarts. Every compile, section-map and
question call checks it first and records its cost after. Default cap: $5 and 200 calls in total, set by
PRAXIS_BACKEND_CAP_USD / PRAXIS_BACKEND_MAX_CALLS."""
from __future__ import annotations

import os
import threading
from pathlib import Path

from ..verify.common import Budget, BudgetExceeded, cost_usd
from .store import ORGS, now, read_json, write_json

DEFAULT_CAP_USD = 5.0
DEFAULT_MAX_CALLS = 200


class LedgerBudget(Budget):
    def __init__(self, path: Path | None = None, max_calls: int | None = None, max_usd: float | None = None):
        super().__init__(max_calls or int(os.environ.get("PRAXIS_BACKEND_MAX_CALLS", DEFAULT_MAX_CALLS)),
                         max_usd if max_usd is not None else float(os.environ.get("PRAXIS_BACKEND_CAP_USD", DEFAULT_CAP_USD)))
        self.path = Path(path) if path else ORGS / "spend.json"
        led = read_json(self.path, {"entries": []})
        self.entries = led["entries"]
        self.calls = sum(1 for e in self.entries if e.get("live", True))
        self.usd = sum(e.get("usd", 0.0) for e in self.entries)
        self._io = threading.Lock()

    def remaining(self) -> float:
        return max(0.0, self.max_usd - self.usd)

    def ensure(self, est_usd: float, what: str) -> None:
        """Refuse a call whose estimate would cross the cap (checked before Budget.check() counts the call)."""
        if self.usd + est_usd > self.max_usd:
            raise BudgetExceeded(f"budget hit: {what} would cost about ${est_usd:.3f}; ${self.usd:.3f} of the "
                                 f"${self.max_usd:.2f} backend cap is already spent")

    def record(self, what: str, model: str, usage, org: str = "", detail: dict | None = None) -> float:
        """Add one finished call (its real token counts) to the ledger. Returns its cost."""
        usd = cost_usd(model, usage.input_tokens, usage.output_tokens,
                       getattr(usage, "cache_read_input_tokens", 0) or 0,
                       getattr(usage, "cache_creation_input_tokens", 0) or 0)
        return self.record_usd(what, model, usd, usage.input_tokens, usage.output_tokens, org, detail)

    def record_usd(self, what: str, model: str, usd: float, input_tokens: int = 0, output_tokens: int = 0,
                   org: str = "", detail: dict | None = None) -> float:
        """Add one finished call whose cost the caller already computed (e.g. the compiler's own cost_usd)."""
        self.add(usd)
        with self._io:
            self.entries.append({"t": now(), "what": what, "org": org, "model": model, "usd": round(usd, 6),
                                 "input_tokens": input_tokens, "output_tokens": output_tokens, **(detail or {})})
            write_json(self.path, {"cap_usd": self.max_usd, "max_calls": self.max_calls, "total_usd": round(self.usd, 6),
                                   "calls": self.calls, "entries": self.entries})
        return usd

    def summary(self) -> dict:
        return {"spent_usd": round(self.usd, 4), "cap_usd": self.max_usd, "calls": self.calls,
                "max_calls": self.max_calls, "remaining_usd": round(self.remaining(), 4)}


_B: LedgerBudget | None = None


def backend_budget() -> LedgerBudget:
    global _B
    if _B is None:
        _B = LedgerBudget()
    return _B


def estimate_tokens(chars: int) -> int:
    """Conservative token estimate for English manual text (about 3.3 characters per token)."""
    return int(chars / 3.3) + 1

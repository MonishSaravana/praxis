"""Run configuration. Every layer reads its settings from here, so swapping an implementation
(e.g. the verifier) is a one-line change in configs/*.yaml."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

from .paths import CONFIGS


class Cfg(dict):
    """dict with attribute access (nested)."""

    def __getattr__(self, k: str) -> Any:
        try:
            v = self[k]
        except KeyError as e:
            raise AttributeError(k) from e
        return Cfg(v) if isinstance(v, dict) and not isinstance(v, Cfg) else v

    def __setattr__(self, k: str, v: Any) -> None:
        self[k] = v


def _merge(a: dict, b: dict) -> dict:
    out = copy.deepcopy(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | Path | None = None, overrides: dict | None = None) -> Cfg:
    base = yaml.safe_load((CONFIGS / "default.yaml").read_text())
    if path:
        base = _merge(base, yaml.safe_load(Path(path).read_text()) or {})
    if overrides:
        base = _merge(base, overrides)
    return _wrap(base)


def _wrap(d: Any) -> Any:
    if isinstance(d, dict):
        return Cfg({k: _wrap(v) for k, v in d.items()})
    if isinstance(d, list):
        return [_wrap(x) for x in d]
    return d


def set_path(cfg: dict, dotted: str, value: Any) -> None:
    """set_path(cfg, 'verifier.primary', 'jev')"""
    keys = dotted.split(".")
    d = cfg
    for k in keys[:-1]:
        d = d.setdefault(k, Cfg())
    d[keys[-1]] = value

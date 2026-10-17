"""praxis CLI. Every result in results/ is produced by one of these commands (see prototype/README.md)."""
from __future__ import annotations

import argparse
import json
import sys
import time

from .paths import ensure_dirs


def cmd_manifest(a):
    from .data import cc4d
    man = cc4d.build_manifest(seed=a.seed)
    print(json.dumps({k: len(v) if isinstance(v, list) else v for k, v in man.items()}, indent=1))


def cmd_download(a):
    from .data import cc4d
    man = cc4d.load_manifest()
    rids = [c["recording"] for c in man[a.split]][: a.limit or None]
    for line in cc4d.download(rids, workers=a.workers):
        print(line, flush=True)


def cmd_features(a):
    from pathlib import Path

    from .data import cc4d
    from .perception.extract import Extractor
    man = cc4d.load_manifest()
    items = [c for s in a.split.split(",") for c in man[s]]
    if a.per_task:
        seen: dict[str, int] = {}
        keep = []
        for c in items:
            if c["split"] in ("train", "heldout_type"):
                k = seen.get(c["task_id"], 0)
                if k >= a.per_task:
                    continue
                seen[c["task_id"]] = k + 1
            keep.append(c)
        items = keep
    ex = Extractor(stride_s=a.stride)
    for i, c in enumerate(items):
        waited = 0
        while not Path(c["video"]).exists() and waited < a.wait:
            time.sleep(10)
            waited += 10
        if not Path(c["video"]).exists():
            print(f"[{i + 1}/{len(items)}] missing video {c['recording']}", flush=True)
            continue
        t0 = time.time()
        ex.run(c["video"], c["clip_id"], c["start"], c["end"])
        print(f"[{i + 1}/{len(items)}] {c['clip_id']} {c['end'] - c['start']:.0f}s video in {time.time() - t0:.0f}s", flush=True)
    print("FEATURES_DONE", flush=True)


def main(argv=None):
    ensure_dirs()
    p = argparse.ArgumentParser("praxis")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("manifest")
    s.add_argument("--seed", type=int, default=0)
    s.set_defaults(fn=cmd_manifest)
    s = sub.add_parser("download")
    s.add_argument("--split", default="eval")
    s.add_argument("--limit", type=int, default=0)
    s.add_argument("--workers", type=int, default=6)
    s.set_defaults(fn=cmd_download)
    s = sub.add_parser("features")
    s.add_argument("--split", default="eval")
    s.add_argument("--per-task", type=int, default=0, help="max train/heldout recordings per task")
    s.add_argument("--stride", type=float, default=2.0)
    s.add_argument("--wait", type=int, default=1800, help="seconds to wait for a video still downloading")
    s.set_defaults(fn=cmd_features)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    sys.exit(main())

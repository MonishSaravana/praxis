"""Speed benchmark of L1 backbones on this machine (MPS). Writes results/l1_speed.json."""
from __future__ import annotations

import json
import platform

import numpy as np
import torch

from ..paths import RESULTS
from .backbones import DINOv2, Hands, SigLIP, VJEPA2, bench, device


def run(out: str | None = None) -> dict:
    rng = np.random.default_rng(0)
    frames = [rng.integers(0, 255, (360, 640, 3), dtype=np.uint8) for _ in range(32)]
    res: dict = {"device": str(device()), "torch": torch.__version__, "machine": platform.platform(), "rows": []}

    def row(name, per_call_s, items, unit):
        r = {"backbone": name, "batch": items, "sec_per_call": per_call_s,
             "ms_per_item": 1000 * per_call_s / items, "items_per_s": items / per_call_s, "unit": unit}
        res["rows"].append(r)
        print(json.dumps(r))

    sig = SigLIP()
    for b in (1, 8):
        row("siglip2-base-224 (image)", bench(lambda: sig.images(frames[:b], batch=b)), b, "frame")
    row("siglip2-base-224 (text x16)", bench(lambda: sig.texts(["attach the front wheel"] * 16)), 16, "text")
    del sig
    dino = DINOv2()
    for b in (1, 8):
        row("dinov2-small (image)", bench(lambda: dino.images(frames[:b], batch=b)), b, "frame")
    del dino
    for nf, size in ((16, 256), (8, 224)):
        vj = VJEPA2(n_frames=nf, size=size)
        row(f"vjepa2-vitl ({nf}f@{size})", bench(lambda: vj.clips([frames[:16]], batch=1), n=3), 1, "window")
        del vj
    hands = Hands()
    t = [0.0]

    def h():
        for f in frames[:8]:
            t[0] += 0.1
            hands.frame(f, t[0])
    row("mediapipe-hands", bench(h), 8, "frame")
    hands.close()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    (RESULTS / "l1").mkdir(parents=True, exist_ok=True)
    path = out or str(RESULTS / "l1" / "l1_speed.json")
    with open(path, "w") as f:
        json.dump(res, f, indent=2)
    return res


if __name__ == "__main__":
    run()

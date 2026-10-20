"""Crop the brand's concept-mock photos into the three tiles on the Solution slide.

The photos in brand/deck/v1/assets are already veiled in graphite, with the target region left in full color. This only
crops each one to the tile's shape around its region, and writes assets/tiles.json so build_hv.js can draw the HUD
(outline, chip, card, leader) natively on top, in editable text.

    python3 deck-hv/make_tiles.py
"""
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "brand", "deck", "v1", "assets")
OUT = os.path.join(HERE, "assets")
TILE_W, TILE_H = 3.94, 3.2  # inches; must match TILE in build_hv.js

# photo, target region in the photo's 1920x1080 pixels (the same regions as the S@H deck's HUD slides)
TILES = {
    "tile-step": ("photo-step.jpg", (800, 300, 1260, 820)),
    "tile-verified": ("photo-verified.jpg", (470, 560, 860, 860)),
    "tile-mistake": ("photo-mistake.jpg", (720, 160, 1160, 600)),
}


def main():
    os.makedirs(OUT, exist_ok=True)
    meta = {}
    for name, (photo, region) in TILES.items():
        im = Image.open(os.path.join(SRC, photo)).convert("RGB")
        W, H = im.size
        cw = round(H * TILE_W / TILE_H)
        cx = (region[0] + region[2]) / 2
        x0 = int(max(0, min(W - cw, cx - cw / 2)))
        im.crop((x0, 0, x0 + cw, H)).save(os.path.join(OUT, f"{name}.jpg"), quality=88)
        meta[name] = {"x0": x0, "y0": 0, "crop_w": cw, "crop_h": H, "region": list(region)}
    with open(os.path.join(OUT, "tiles.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print("wrote", ", ".join(meta))


if __name__ == "__main__":
    main()

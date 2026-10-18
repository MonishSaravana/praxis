"""Progress marks for deck/build_deck.js, drawn exactly like brand/src/assets.py `prog()` but for any slide count.

Usage: python3 deck/make_marks.py 17   ->  deck/assets/marks/prog-light-{n}of17.png and prog-dark-{n}of17.png
Needs rsvg-convert (brew install librsvg). Constants are brand/src/build.py's mark geometry.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "brand", "src"))
from marks import arc, pt  # noqa: E402  (no side effects, no dependencies)

SW, R, SX, TOP, BOT, DOT = 9, 14.5, 17.5, 8, 56, 6
MARK_BOX = (SX - SW / 2, TOP, SX + 2 * R + SW / 2, BOT)
OUT = os.path.join(HERE, "assets", "marks")


def prog(frac, ink, track, h=256):
    cx, cy = SX + R, TOP + SW / 2 + R
    a1 = 270 + 180 * frac
    ex, ey = pt(cx, cy, R, a1)
    x0, y0, x1, y1 = MARK_BOX
    g = f'<path d="{arc(cx, cy, R, a1, 450)}" stroke="#{track}" stroke-width="{SW * 0.34:.2f}" fill="none"/>' if frac < 1 else ""
    g += f'<path d="M{SX} {BOT}V{TOP + SW / 2}H{cx}A{arc(cx, cy, R, 270, a1).split("A", 1)[1]}" stroke="#{ink}" stroke-width="{SW}" fill="none"/>'
    g += f'<circle cx="{ex:.2f}" cy="{ey:.2f}" r="{DOT}" fill="#FF5B14"/>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1 - x0} {y1 - y0}" width="{(x1 - x0) * h / (y1 - y0):.0f}" height="{h}">{g}</svg>'


def png(svg, name):
    p = os.path.join(OUT, name + ".svg")
    with open(p, "w") as f:
        f.write(svg)
    subprocess.run(["rsvg-convert", p, "-o", os.path.join(OUT, name + ".png")], check=True)
    os.remove(p)


if __name__ == "__main__":
    total = int(sys.argv[1])
    os.makedirs(OUT, exist_ok=True)
    for n in range(1, total + 1):
        png(prog(n / total, "16191B", "C2C8C5"), f"prog-light-{n}of{total}")
        png(prog(n / total, "E8EBE9", "3A4044", 900), f"prog-dark-{n}of{total}")
    print("wrote", 2 * total, "marks to", OUT)

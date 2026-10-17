"""Renderer. Draws the HUD onto the source video ONLY from a saved run log (integrity rule #2).

User view (what a wearer sees): unobtrusive and voice-first. A thin progress indicator with "k/N", the
current instruction as a short card that collapses to a one-line chip, a subtle green pulse on
verification, and prominent cards only for mistakes (amber) and view requests (with a direction arrow).
At most one card at a time; cards fade on their own. The task graph, beliefs and confidences are never
shown.

Engineer view ("under the hood"): the same run with step-belief bars over the task graph, the event
detector trace, point tracks / ROI, each verifier call with latency and confidence, and the policy
decision.
"""
from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..runlog import by_kind, read_log

FONT = "/System/Library/Fonts/Avenir Next.ttc"
MONO = "/System/Library/Fonts/Menlo.ttc"
GREEN = (43, 182, 115)
AMBER = (245, 166, 35)
BLUE = (59, 130, 246)
INK = (28, 30, 34)
SUB = (92, 96, 104)

BRAND_1 = "Instructions that can finally see how you're doing."
BRAND_2 = "AI guidance for the physical world."

CARD_DUR = {"announce_task": 3.6, "instruct": 4.0, "hint": 6.5, "mistake": 6.5, "view_request": 5.5, "done": 4.0}
PRIORITY = {"mistake": 3, "view_request": 3, "hint": 2, "announce_task": 1, "instruct": 1, "done": 1}


def font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    if mono:
        return ImageFont.truetype(MONO, size)
    # Avenir Next.ttc faces: 0 Bold, 2 Demi Bold, 5 Medium, 7 Regular (index order varies; Medium/Demi look right)
    return ImageFont.truetype(FONT, size, index=2 if bold else 5)


def _wrap(draw: ImageDraw.ImageDraw, text: str, f, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=f) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _frosted(img: Image.Image, box, radius: int, tint=(255, 255, 255), alpha: float = 0.78, blur: int = 18):
    x0, y0, x1, y1 = [int(v) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(img.width, x1), min(img.height, y1)
    if x1 <= x0 or y1 <= y0:
        return
    region = img.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(blur))
    overlay = Image.new("RGB", region.size, tint)
    region = Image.blend(region, overlay, alpha)
    mask = Image.new("L", region.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, region.width - 1, region.height - 1), radius=radius, fill=255)
    # soft shadow
    sh = Image.new("L", (region.width + 24, region.height + 24), 0)
    ImageDraw.Draw(sh).rounded_rectangle((12, 14, region.width + 12, region.height + 14), radius=radius, fill=70)
    sh = sh.filter(ImageFilter.GaussianBlur(8))
    img.paste(Image.new("RGB", sh.size, (0, 0, 0)), (x0 - 12, y0 - 12), sh)
    img.paste(region, (x0, y0), mask)


@dataclass
class Card:
    t: float
    kind: str
    text: str
    detail: dict
    node: str | None


class LogState:
    """Everything the HUD needs at media time tau, derived only from the log."""

    def __init__(self, records: list[dict], n_steps: int | None = None):
        self.records = records
        self.actions = by_kind(records, "action")
        self.commits = by_kind(records, "commit")
        self.beliefs = by_kind(records, "belief")
        self.verdicts = by_kind(records, "verdict")
        self.fast = by_kind(records, "fast")
        self.tasks = by_kind(records, "task")
        self.events = by_kind(records, "event")
        self.tracks = by_kind(records, "tracks")
        self.meta = records[0] if records else {}
        self.n_steps = n_steps or (self.tasks[0]["n_steps"] if self.tasks else None)
        self.cards = [Card(a["t"], a["action"], a["text"], a.get("detail") or {}, a.get("node"))
                      for a in self.actions if a["action"] in CARD_DUR]
        self.cards.sort(key=lambda c: c.t)

    def progress(self, tau: float) -> int:
        return len({c["node"] for c in self.commits if c["t"] <= tau})

    def card(self, tau: float) -> tuple[Card | None, float]:
        """The one card on screen at tau and its opacity. Higher-priority cards are not overwritten."""
        live = [c for c in self.cards if c.t <= tau < c.t + CARD_DUR[c.kind]]
        if not live:
            return None, 0.0
        top = max(PRIORITY[c.kind] for c in live)
        c = [c for c in live if PRIORITY[c.kind] == top][-1]
        age, dur = tau - c.t, CARD_DUR[c.kind]
        a = min(1.0, age / 0.25, (dur - age) / 0.4)
        return c, max(0.0, a)

    def chip(self, tau: float) -> str | None:
        ins = [c for c in self.cards if c.kind == "instruct" and c.t <= tau]
        if not ins:
            return None
        last = ins[-1]
        done = [a for a in self.actions if a["action"] == "done" and a["t"] <= tau]
        if done:
            return None
        return last.detail.get("chip") or last.text

    def pulse(self, tau: float) -> float:
        v = [a for a in self.actions if a["action"] == "verified" and 0 <= tau - a["t"] < 0.9]
        return 0.0 if not v else 1.0 - (tau - v[-1]["t"]) / 0.9

    def belief(self, tau: float) -> dict | None:
        b = [x for x in self.beliefs if x["t"] <= tau]
        return b[-1] if b else None


def _arrow(draw: ImageDraw.ImageDraw, cx: float, cy: float, direction: str, r: float, color):
    ang = {"right": 0, "down-right": 45, "down": 90, "down-left": 135, "left": 180, "up-left": 225, "up": 270,
           "up-right": 315}.get(direction)
    if direction == "rotate":
        draw.arc((cx - r, cy - r, cx + r, cy + r), 30, 320, fill=color, width=max(3, int(r / 5)))
        ex, ey = cx + r * math.cos(math.radians(320)), cy + r * math.sin(math.radians(320))
        draw.polygon([(ex + 8, ey - 2), (ex - 6, ey - 10), (ex - 2, ey + 8)], fill=color)
        return
    if ang is None:   # "closer": concentric rings
        for k in (1.0, 0.6):
            draw.ellipse((cx - r * k, cy - r * k, cx + r * k, cy + r * k), outline=color, width=3)
        return
    a = math.radians(ang)
    x0, y0 = cx - r * math.cos(a), cy - r * math.sin(a)
    x1, y1 = cx + r * math.cos(a), cy + r * math.sin(a)
    draw.line((x0, y0, x1, y1), fill=color, width=max(4, int(r / 4)))
    h = r * 0.55
    left = (x1 - h * math.cos(a - 0.5), y1 - h * math.sin(a - 0.5))
    right = (x1 - h * math.cos(a + 0.5), y1 - h * math.sin(a + 0.5))
    draw.polygon([(x1 + 4 * math.cos(a), y1 + 4 * math.sin(a)), left, right], fill=color)


class UserView:
    def __init__(self, W: int, H: int, badge: str):
        self.W, self.H, self.badge = W, H, badge
        s = W / 1280
        self.s = s
        self.f_title = font(int(30 * s), bold=True)
        self.f_body = font(int(25 * s))
        self.f_small = font(int(17 * s))
        self.f_chip = font(int(20 * s), bold=True)
        self.f_badge = font(int(14 * s))

    def draw(self, img: Image.Image, st: LogState, tau: float, gt_text: str | None = None) -> Image.Image:
        s, W, H = self.s, self.W, self.H
        d = ImageDraw.Draw(img)
        # progress indicator (top-right): thin bar + k/N
        if st.n_steps and st.tasks and st.tasks[0]["t"] <= tau:
            k, n = st.progress(tau), st.n_steps
            bw, bh = int(150 * s), int(6 * s)
            x1, y0 = W - int(36 * s), int(34 * s)
            x0 = x1 - bw
            label = f"{k}/{n}"
            _frosted(img, (x0 - int(70 * s), y0 - int(18 * s), x1 + int(14 * s), y0 + int(22 * s)), int(16 * s), alpha=0.55, blur=10)
            d = ImageDraw.Draw(img)
            d.rounded_rectangle((x0, y0, x1, y0 + bh), radius=bh // 2, fill=(255, 255, 255, 140), outline=(210, 212, 216))
            d.rounded_rectangle((x0, y0, x0 + max(bh, int(bw * k / n)), y0 + bh), radius=bh // 2, fill=GREEN)
            d.text((x0 - int(58 * s), y0 - int(12 * s)), label, font=self.f_chip, fill=INK)
            p = st.pulse(tau)
            if p > 0:
                r = int((10 + 26 * (1 - p)) * s)
                cx, cy = x0 - int(76 * s), y0 + bh // 2
                d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=GREEN + (int(255 * p),), width=max(2, int(3 * s)))
                d.text((cx - int(7 * s), cy - int(13 * s)), "✓", font=self.f_chip, fill=GREEN)
        card, a = st.card(tau)
        if card is not None and a > 0.02:
            img = self._card(img, card, a)
        else:
            chip = st.chip(tau)
            if chip:
                self._chip(img, chip)
        d = ImageDraw.Draw(img)
        d.text((int(18 * s), H - int(28 * s)), self.badge, font=self.f_badge, fill=(255, 255, 255))
        if gt_text:
            tw = d.textlength(gt_text, font=self.f_small)
            _frosted(img, (int(16 * s), int(16 * s), int(32 * s) + tw, int(48 * s)), int(10 * s), tint=(20, 20, 24), alpha=0.6, blur=6)
            ImageDraw.Draw(img).text((int(24 * s), int(20 * s)), gt_text, font=self.f_small, fill=(255, 255, 255))
        return img

    def _chip(self, img: Image.Image, text: str) -> None:
        s = self.s
        d = ImageDraw.Draw(img)
        text = text if len(text) < 60 else text[:57] + "…"
        tw = d.textlength(text, font=self.f_chip)
        x0, y1 = int(36 * s), self.H - int(52 * s)
        box = (x0, y1 - int(40 * s), x0 + tw + int(30 * s), y1)
        _frosted(img, box, int(20 * s), alpha=0.72, blur=12)
        ImageDraw.Draw(img).text((x0 + int(15 * s), y1 - int(33 * s)), text, font=self.f_chip, fill=INK)

    def _card(self, base: Image.Image, c: Card, alpha: float) -> Image.Image:
        s, W, H = self.s, self.W, self.H
        img = base.copy()
        d = ImageDraw.Draw(img)
        prominent = c.kind in ("mistake", "view_request")
        width = int((640 if prominent else 560) * s)
        accent = {"mistake": AMBER, "view_request": BLUE, "hint": BLUE, "done": GREEN}.get(c.kind, GREEN)
        head = {"announce_task": "Task recognized", "instruct": None, "hint": "Here's a closer walkthrough",
                "mistake": "Something looks off", "view_request": "I can't see that clearly", "done": "Done"}[c.kind]
        body = c.text
        lines_extra: list[str] = []
        if c.kind == "hint":
            subs = c.detail.get("substeps") or []
            body = ""
            lines_extra = [f"{i + 1}. {x}" for i, x in enumerate(subs[:4])]
            if c.detail.get("parts_line"):
                lines_extra.append(c.detail["parts_line"])
        pad = int(22 * s)
        tx = pad + (int(16 * s) if prominent else int(10 * s))
        inner = width - tx - pad - (int(90 * s) if c.kind == "view_request" else 0)
        blines = _wrap(d, body, self.f_body, inner) if body else []
        elines = sum((_wrap(d, x, self.f_small, inner) for x in lines_extra), [])
        hh = int(36 * s) if head else 0
        height = pad * 2 + hh + len(blines) * int(33 * s) + len(elines) * int(25 * s)
        x0 = (W - width) // 2
        y0 = H - height - int(70 * s) if not prominent else int(H * 0.56) - height // 2
        _frosted(img, (x0, y0, x0 + width, y0 + height), int(22 * s), alpha=0.8)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((x0 + int(10 * s), y0 + pad, x0 + int(16 * s), y0 + height - pad), radius=int(3 * s), fill=accent)
        y = y0 + pad - int(4 * s)
        if head:
            d.text((x0 + tx, y), head, font=self.f_title, fill=accent if prominent else INK)
            y += hh
        for ln in blines:
            d.text((x0 + tx, y), ln, font=self.f_body, fill=INK)
            y += int(33 * s)
        for ln in elines:
            d.text((x0 + tx, y), ln, font=self.f_small, fill=SUB)
            y += int(25 * s)
        if c.kind == "view_request":
            _arrow(d, x0 + width - int(62 * s), y0 + height / 2, c.detail.get("direction", "closer"), int(30 * s), BLUE)
        return Image.blend(base, img, alpha)


class EngineerView:
    """Video on the left; task-graph belief, event trace, verifier calls, policy on the right/bottom."""

    def __init__(self, W: int, H: int, badge: str, graph_names: dict[str, str]):
        self.W, self.H, self.badge = W, H, badge
        self.vw, self.vh = int(W * 0.64), int(W * 0.64 * 9 / 16)
        self.names = graph_names
        self.f = font(17)
        self.fb = font(19, bold=True)
        self.fm = font(14, mono=True)
        self.fs = font(14)

    def draw(self, frame: Image.Image, st: LogState, tau: float, user: UserView) -> Image.Image:
        W, H, vw, vh = self.W, self.H, self.vw, self.vh
        canvas = Image.new("RGB", (W, H), (246, 247, 249))
        uv = user.draw(frame.resize((user.W, user.H)), st, tau)
        canvas.paste(uv.resize((vw, vh)), (0, 0))
        d = ImageDraw.Draw(canvas)
        sx, sy = vw / frame.width, vh / frame.height
        # point tracks / ROI
        for tr in st.tracks:
            if 0 <= tau - tr["t"] < 1.5:
                for (x, y), v in zip(tr["xy"], tr["visible"]):
                    if v:
                        d.ellipse((x * sx - 3, y * sy - 3, x * sx + 3, y * sy + 3), fill=(255, 64, 160))
                if tr.get("roi"):
                    x0, y0, x1, y1 = tr["roi"]
                    d.rectangle((x0 * sx, y0 * sy, x1 * sx, y1 * sy), outline=(255, 64, 160), width=2)
        # belief bars over the task graph
        px = vw + 18
        d.text((px, 12), "L4 state tracker: P(step)", font=self.fb, fill=INK)
        b = st.belief(tau)
        y = 44
        if b:
            done = set(b.get("completed", []))
            items = list(b["p"].items())
            rowh = max(16, min(30, int((vh - 70) / max(1, len(items)))))
            for nid, p in items:
                name = "done" if nid == "__done__" else self.names.get(nid, nid)
                name = name if len(name) < 34 else name[:32] + "…"
                col = GREEN if nid in done else (BLUE if nid == b["map"] else (150, 154, 160))
                d.text((px, y), ("✓ " if nid in done else "  ") + name, font=self.fs, fill=INK if nid == b["map"] else SUB)
                bx = px + 250
                d.rounded_rectangle((bx, y + 3, bx + 170, y + rowh - 6), radius=3, fill=(228, 230, 234))
                d.rounded_rectangle((bx, y + 3, bx + max(2, int(170 * p)), y + rowh - 6), radius=3, fill=col)
                y += rowh
            d.text((px, y + 6), f"entropy {b['entropy']:.2f}   time on step {b['time_on_step']:.0f}s   "
                                f"profile {b.get('user', {}).get('profile', '-')}", font=self.fm, fill=SUB)
        else:
            rec = [r for r in st.records if r["kind"] == "recognizer" and r["t"] <= tau]
            if rec:
                d.text((px, y), "L3b task recognizer", font=self.f, fill=INK)
                for i, (tid, p) in enumerate(sorted(rec[-1]["posterior"].items(), key=lambda x: -x[1])[:6]):
                    d.text((px, y + 26 + i * 24), f"{tid[:28]:<28}", font=self.fm, fill=SUB)
                    d.rounded_rectangle((px + 250, y + 30 + i * 24, px + 250 + int(170 * p), y + 42 + i * 24), radius=3, fill=BLUE)
        # event trace (last 30 s)
        ty0, ty1 = vh + 34, H - 150
        d.text((14, vh + 8), "L2 event detector: P(step boundary)   |   ticks = verifier calls", font=self.fb, fill=INK)
        win = 30.0
        xs = lambda t: 14 + (t - (tau - win)) / win * (vw - 28)
        d.rectangle((14, ty0, vw - 14, ty1), outline=(220, 222, 226))
        pts = [(xs(r["t"]), ty1 - r["boundary"] * (ty1 - ty0)) for r in st.fast if tau - win <= r["t"] <= tau]
        if len(pts) > 1:
            d.line(pts, fill=BLUE, width=2)
        for e in st.events:
            if tau - win <= e["t"] <= tau and e.get("kind") == "boundary":
                d.ellipse((xs(e["t"]) - 4, ty0 + 4, xs(e["t"]) + 4, ty0 + 12), fill=BLUE)
        for v in st.verdicts:
            if tau - win <= v["t"] <= tau:
                col = AMBER if v["status"] == "deviation" else GREEN if v["status"] == "complete" else (140, 140, 140)
                d.line((xs(v["t"]), ty0, xs(v["t"]), ty1), fill=col, width=2)
        # verifier calls
        cy = H - 140
        d.text((14, cy), "L5 verifier calls (model · latency · status · confidence)", font=self.fb, fill=INK)
        for i, v in enumerate([v for v in st.verdicts if v["t"] <= tau][-4:]):
            line = (f"t={v['t']:6.1f}s  {v['model'][:18]:<18} {v['latency_ms']:6.0f} ms  {v['status']:<11} "
                    f"p={v['confidence']:.2f}  {v['reason']}")
            d.text((14, cy + 26 + i * 22), line, font=self.fm, fill=SUB)
        # policy
        d.text((vw + 18, cy), "L6 policy decision", font=self.fb, fill=INK)
        acts = [a for a in st.actions if a["t"] <= tau][-4:]
        for i, a in enumerate(acts):
            txt = f"t={a['t']:6.1f}s {a['action']:<13} {a['text'][:28]}"
            d.text((vw + 18, cy + 26 + i * 22), txt, font=self.fm, fill=SUB)
        d.text((W - 380, H - 22), self.badge, font=self.fs, fill=SUB)
        return canvas


def end_card(W: int, H: int, sub: str = "") -> Image.Image:
    img = Image.new("RGB", (W, H), (250, 250, 252))
    d = ImageDraw.Draw(img)
    s = W / 1280
    f1, f2, f3 = font(int(56 * s), bold=True), font(int(30 * s)), font(int(20 * s))
    for text, f, y, col in (("Praxis", f1, 0.34, INK), (BRAND_1, f2, 0.5, INK), (BRAND_2, f2, 0.58, SUB), (sub, f3, 0.72, SUB)):
        if text:
            tw = d.textlength(text, font=f)
            d.text(((W - tw) / 2, H * y), text, font=f, fill=col)
    return img


def render(log_path: str | Path, video: str | Path, out: str | Path, view: str = "user", start: float = 0.0,
           t0: float = 0.0, t1: float | None = None, fps: int = 15, width: int = 1280, dataset: str = "",
           gt: list[tuple[float, float, str]] | None = None, step_names: dict[str, str] | None = None,
           end_seconds: float = 2.5, label: str = "real model output", crf: int = 26) -> Path:
    """t0/t1: clip-relative media times to render; start: offset of clip t=0 inside the video file."""
    records = read_log(log_path)
    st = LogState(records)
    badge = f"Praxis prototype v0 · {label} · {dataset}"
    cap = cv2.VideoCapture(str(video))
    nat = cap.get(cv2.CAP_PROP_FPS) or 30.0
    vid_w, vid_h = cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    H = int(round(width * vid_h / vid_w / 2) * 2)
    user = UserView(width, H, badge)
    eng = EngineerView(1600, 900, badge, step_names or {}) if view == "engineer" else None
    outW, outH = (1600, 900) if eng else (width, H)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{outW}x{outH}",
                           "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    t_end = t1 if t1 is not None else (records[-1]["t"] if records else 0.0)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int((start + t0) * nat))
    cur_idx = int((start + t0) * nat)
    tau = t0
    frame = None
    while tau <= t_end:
        want = int((start + tau) * nat)
        while cur_idx <= want:
            ok, bgr = cap.read()
            if not ok:
                break
            frame, cur_idx = bgr, cur_idx + 1
        if frame is None:
            break
        img = Image.fromarray(cv2.cvtColor(cv2.resize(frame, (width, H), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB))
        gt_text = None
        if gt is not None:
            g = [x for x in gt if x[0] <= tau < x[1]]
            b = st.belief(tau)
            pred = (step_names or {}).get(b["map"], b["map"]) if b else "-"
            gt_text = f"GT: {(step_names or {}).get(g[0][2], g[0][2]) if g else '(between steps)'}   |   Praxis: {pred}"
        if eng:
            img = eng.draw(img, st, tau, user)
        else:
            img = user.draw(img, st, tau, gt_text)
        ff.stdin.write(np.asarray(img.convert("RGB")).tobytes())
        tau += 1.0 / fps
    if end_seconds > 0:
        ec = np.asarray(end_card(outW, outH, f"Praxis prototype v0 · {label} · {dataset}"))
        for _ in range(int(end_seconds * fps)):
            ff.stdin.write(ec.tobytes())
    ff.stdin.close()
    ff.wait()
    cap.release()
    return out

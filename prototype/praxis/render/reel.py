"""Demo reel: a short cut of real moments from one saved Studio session, in two views.

    python -m praxis.render.reel                 # both views of the default cut (ENIGMA-51 video 141 session)
    python -m praxis.render.reel --view user

Like render/hud.py, everything drawn comes from the saved run log (integrity rule #2); nothing is re-timed. The cut list
(BEATS) only picks which stretches of session time to show, and every frame carries its session time code so the cuts
are visible. The user view is what the wearer sees through the glasses; the engineer view adds the state tracker, the
model calls (fast tier and escalation, with their real latencies) and a scrolling timeline of the layers.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..paths import DATA, RENDERS, ROOT
from ..runlog import by_kind, read_log
from .hud import CARD_DUR, PRIORITY, LogState

FPS = 30
W, H = 1920, 1080
FONTS = ROOT / "brand" / "deck" / "v2" / "fonts"
LOCKUP = ROOT / "brand" / "png" / "praxis-lockup-white.png"

GRAPHITE = (22, 25, 27)
PANEL = (30, 34, 37)
RULE = (48, 54, 58)
ALU = (232, 235, 233)
STEEL = (94, 103, 108)
MUTED = (150, 158, 162)
ORANGE = (255, 91, 20)
GREEN = (43, 182, 115)
BLUE = (59, 130, 246)
RED = (229, 72, 77)
STATUS_COLOR = {"complete": GREEN, "deviation": RED, "in_progress": MUTED, "not_started": STEEL}


@dataclass
class Beat:
    start: float
    end: float
    caption: str


SESSION = ROOT / "sessions" / "20261018_152645_high-voltage-board-repair-with-screwdriv"
SOURCE = DATA / "raw" / "enigma51" / "videos" / "141.mp4"      # same clock as the session (it was the upload)
SOURCE_LABEL = "ENIGMA-51 video 141 · real repair lab"
BEATS = [
    Beat(0.0, 5.0, "Starts the job from the company's own procedure"),
    Beat(21.0, 30.0, "Watches the panel: both green buttons"),
    Beat(36.5, 39.5, "The fast model's doubt goes to Opus, which clears it: no false alarm"),
    Beat(167.0, 183.0, "Safety-critical step: the iron overshoots 200 °C"),
    Beat(214.0, 223.0, "Follows the resolder"),
]
# ~15 s cut for the deck: a step change, a caught mistake, and a moment it can't see (no title or end card)
BEATS_SHORT = [
    Beat(168.5, 172.5, "Next step: it moves on and says what to do"),
    Beat(176.0, 180.5, "Mistake caught: the iron went past 200 °C"),
    Beat(266.0, 274.5, "Can't see the display: it says so and asks for a closer look"),
]
TITLE_S, END_S, XFADE = 2.6, 4.2, 0.27


def F(size: int, w: str = "Regular") -> ImageFont.FreeTypeFont:
    name = {"Regular": "Archivo-Regular", "Semi": "Archivo-SemiBold", "Wide": "ArchivoExpanded-SemiBold",
            "Mono": "IBMPlexMono-Regular", "MonoMed": "IBMPlexMono-Medium"}[w]
    return ImageFont.truetype(str(FONTS / f"{name}.ttf"), size)


def mmss(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:04.1f}"


def wrap(d: ImageDraw.ImageDraw, text: str, f, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=f) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    return lines + ([cur] if cur else [])


def clip(d: ImageDraw.ImageDraw, text: str, f, width: int) -> str:
    if d.textlength(text, font=f) <= width:
        return text
    while text and d.textlength(text + "…", font=f) > width:
        text = text[:-1]
    return text.rstrip() + "…"


def frosted(img: Image.Image, box, r: int, tint=GRAPHITE, alpha=0.74, blur=20) -> None:
    x0, y0, x1, y1 = [int(v) for v in box]
    region = img.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(blur))
    region = Image.blend(region, Image.new("RGB", region.size, tint), alpha)
    mask = Image.new("L", region.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, region.width - 1, region.height - 1], r, fill=255)
    img.paste(region, (x0, y0), mask)


def ring(size: int, n: int, done: int, cur: int, pulse: float, flash: float) -> Image.Image:
    """The progress-P ring: one segment per step, done segments lit, an orange dot on the current step."""
    S = 4
    im = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pad, wdt = 9 * S, 7 * S
    gap = 360 / n * 0.18
    for i in range(n):
        a0 = -90 + i * 360 / n + gap / 2
        a1 = -90 + (i + 1) * 360 / n - gap / 2
        col = (*ALU, 255) if i < done else (*ALU, 70)
        d.arc([pad, pad, size * S - pad, size * S - pad], a0, a1, fill=col, width=wdt)
    if pulse > 0:
        g = int(150 * pulse)
        d.ellipse([2, 2, size * S - 2, size * S - 2], outline=(*GREEN, g), width=3 * S)
    if flash > 0:
        d.ellipse([2, 2, size * S - 2, size * S - 2], outline=(*RED, int(200 * flash)), width=3 * S)
    a = np.deg2rad(-90 + (cur + 0.5) * 360 / n)
    rr = (size * S - 2 * pad) / 2
    cx, cy = size * S / 2 + rr * np.cos(a), size * S / 2 + rr * np.sin(a)
    d.ellipse([cx - 6 * S, cy - 6 * S, cx + 6 * S, cy + 6 * S], fill=(*ORANGE, 255))
    return im.resize((size, size), Image.LANCZOS)


class Session:
    """The saved log plus what the reel needs from it beyond LogState."""

    def __init__(self, folder: Path):
        self.rec = read_log(folder / "live.jsonl")
        self.st = LogState(self.rec)
        g = json.loads((folder / "taskgraph.json").read_text())
        self.names = {n["id"]: n["name"] for n in g["nodes"]}
        self.order = [n["id"] for n in g["nodes"]]
        self.n = len(self.order)
        self.meta = self.rec[0]
        self.safety = by_kind(self.rec, "org_safety")
        self.commits = by_kind(self.rec, "commit")
        self.fast = by_kind(self.rec, "fast")
        self.beliefs = by_kind(self.rec, "belief")
        self.choices = by_kind(self.rec, "step_choice")
        self.verdicts = by_kind(self.rec, "verdict")
        self.summary = (by_kind(self.rec, "summary") or [{}])[0]
        self.session = json.loads((folder / "session.json").read_text())
        self.calls = self._calls()
        self.overruled = self._overruled()
        self.view_requests = self._view_requests()

    def _calls(self) -> list[dict]:
        """Every model call as (sent, back, model, what, result, colour), times on the session clock."""
        out = []
        for c in self.choices:
            lat = c["latency_ms"] / 1000
            p = c["probs"].get(c["choice"], 0)
            res = f"step → {c['choice']} {p:.2f}" if c["choice"] != "none" else f"step → none {c['probs']['none']:.2f}"
            ms = c.get("mistake_screen") or {}
            if ms.get("choice") not in (None, "none"):
                res += f" · mistake screen {ms['choice']} {ms['p']:.2f}"
            out.append(dict(sent=c["t"], back=c["t"] + lat, model="jev", what="localize", lat=lat, res=res,
                            color=RED if ms.get("choice") not in (None, "none") else ALU, status=None))
        for v in self.verdicts:
            esc = v["model"].startswith("claude")
            back = v["applied_t"] if esc else v["t"] + v["latency_ms"] / 1000
            mis = (v.get("mistake") or {}).get("description")
            res = f"{v['node']} → {v['status'].replace('_', ' ')} {v['confidence']:.2f}"
            color = STATUS_COLOR.get(v["status"], MUTED)
            if v.get("visibility") == "insufficient" and v.get("view_request"):  # the model said it can't see
                res, mis, color = f"{v['node']} → can't see clearly", v["view_request"], BLUE
            out.append(dict(sent=v["t"], back=back, model="opus" if esc else "jev",
                            what="escalation" if esc else "verify", lat=v["latency_ms"] / 1000, res=res,
                            note=mis, color=color, status=v["status"]))
        return sorted(out, key=lambda c: c["back"])

    def _view_requests(self) -> list[tuple[float, str]]:
        """Verdicts that said the view was insufficient, as (time the answer arrived, the request it made)."""
        out = []
        for v in self.verdicts:
            if v.get("visibility") != "insufficient" or not v.get("view_request"):
                continue
            back = v["applied_t"] if v["model"].startswith("claude") else v["t"] + v["latency_ms"] / 1000
            text = v["view_request"].strip()
            if text.startswith("Show me ") and len(text) > 8:          # "Show me The x" -> "Show me the x."
                text = "Show me " + text[8].lower() + text[9:]
            out.append((back, text if text.endswith((".", "?")) else text + "."))
        return sorted(out)

    def _overruled(self) -> list[dict]:
        """Fast-tier 'deviation' verdicts whose paired escalation said otherwise and no mistake alert followed."""
        out = []
        alerts = [a["t"] for a in self.st.actions if a["action"] == "mistake"]
        for v in self.verdicts:
            if v["model"].startswith("claude") or v["status"] != "deviation":
                continue
            esc = [e for e in self.verdicts if e["model"].startswith("claude") and e["t"] == v["t"]]
            if esc and esc[0]["status"] != "deviation" and not any(v["t"] <= t <= esc[0]["applied_t"] + 1 for t in alerts):
                out.append(dict(t=esc[0]["applied_t"], node=v["node"], status=esc[0]["status"]))
        return out

    def last(self, rows: list[dict], tau: float) -> dict | None:
        lo, hi = 0, len(rows)
        while lo < hi:
            m = (lo + hi) // 2
            if rows[m]["t"] <= tau:
                lo = m + 1
            else:
                hi = m
        return rows[lo - 1] if lo else None

    def safety_at(self, tau: float) -> dict | None:
        s = [x for x in self.safety if x["t"] <= tau]
        if not s:
            return None
        ins = [a for a in self.st.actions if a["action"] == "instruct" and a["t"] <= tau]
        return s[-1] if ins and ins[-1]["node"] == s[-1]["node"] else None


# ---------------------------------------------------------------- user view (what the wearer sees)

class UserHUD:
    def __init__(self, s: Session, scale: float = 1.0, view_cards: bool = False):
        self.s, self.k, self.view_cards = s, scale, view_cards

    def px(self, v: float) -> int:
        return int(round(v * self.k))

    def draw(self, img: Image.Image, tau: float) -> Image.Image:
        s, k, px = self.s, self.k, self.px
        d = ImageDraw.Draw(img)
        b = s.last(s.beliefs, tau)
        done = len(b["completed"]) if b else 0
        cur = s.order.index(b["map"]) if b and b["map"] in s.order else 0
        pulse = max([1 - (tau - c["t"]) / 1.2 for c in s.commits if 0 <= tau - c["t"] < 1.2] + [0])
        flash = max([1 - (tau - a["t"]) / 1.4 for a in s.st.actions if a["action"] == "mistake" and 0 <= tau - a["t"] < 1.4] + [0])

        # progress: ring + k/N + task
        R = px(72)
        frosted(img, (px(28), px(26), px(28) + px(330), px(26) + px(88)), px(44), alpha=0.62)
        rg = ring(R, s.n, done, cur, pulse, flash)
        img.paste(rg, (px(36), px(34)), rg)
        d = ImageDraw.Draw(img)
        d.text((px(120), px(38)), f"{done}/{s.n}", font=F(px(30), "Semi"), fill=ALU)
        d.text((px(120), px(76)), "HV board repair", font=F(px(18)), fill=MUTED)

        # task chip right after the task is set
        t0 = s.st.tasks[0]["t"] if s.st.tasks else None
        if t0 is not None and 0 <= tau - t0 < 4.0:
            a = min(1.0, (tau - t0) / 0.25, (4.0 - (tau - t0)) / 0.4)
            self._pill(img, "Work order: high-voltage board repair · procedure v1", (px(380), px(48)), a, ORANGE)

        card, alpha = s.st.card(tau)
        vr = self._view_request_at(tau) if self.view_cards else None
        if card is not None and card.kind != "announce_task":
            self._card(img, card, alpha, s.safety_at(tau) if card.kind == "instruct" else None)
        elif vr is not None:
            # --view-cards: the verifier's logged request drawn as a card. In the live session the policy logged it but
            # put no card on screen, so the card carries a tag saying where its text comes from.
            text, a = vr
            self._card(img, SimpleNamespace(kind="view_request", text=text), a, None)
            tag = "verifier request · text from the session log"
            ft = F(px(15), "MonoMed")
            dd = ImageDraw.Draw(img)
            tw = dd.textlength(tag, font=ft)
            tx = (img.width - tw) / 2
            ty = img.height - px(66)
            frosted(img, (tx - px(12), ty - px(5), tx + tw + px(12), ty + px(24)), px(10), alpha=0.6)
            ImageDraw.Draw(img).text((tx, ty), tag, font=ft, fill=MUTED)
        else:
            chip = s.st.chip(tau, s.names)
            if chip:
                self._chip(img, chip)
        return img

    def _view_request_at(self, tau: float) -> tuple[str, float] | None:
        """The latest logged view request still on screen at tau (shown for CARD_DUR["view_request"] s), with a fade."""
        live = [(t, text) for t, text in self.s.view_requests if 0 <= tau - t < CARD_DUR["view_request"]]
        if not live:
            return None
        t, text = live[-1]
        return text, min(1.0, (tau - t) / 0.25, (CARD_DUR["view_request"] - (tau - t)) / 0.3)

    def _pill(self, img, text, xy, a, dot):
        px = self.px
        d = ImageDraw.Draw(img)
        f = F(px(19))
        w = d.textlength(text, font=f)
        x, y = xy
        box = (x, y, x + w + px(46), y + px(40))
        layer = img.copy()
        frosted(layer, box, px(20), alpha=0.7)
        dl = ImageDraw.Draw(layer)
        dl.ellipse([x + px(16), y + px(15), x + px(26), y + px(25)], fill=dot)
        dl.text((x + px(34), y + px(9)), text, font=f, fill=ALU)
        img.paste(Image.blend(img, layer, a))

    def _chip(self, img, text):
        px = self.px
        d = ImageDraw.Draw(img)
        f = F(px(24))
        text = clip(d, text, f, px(900))
        w = d.textlength(text, font=f)
        x0 = (img.width - w) / 2 - px(26)
        y0 = img.height - px(118)
        frosted(img, (x0, y0, x0 + w + px(52), y0 + px(54)), px(27), alpha=0.66)
        ImageDraw.Draw(img).text((x0 + px(26), y0 + px(12)), text, font=f, fill=ALU)

    def _card(self, img, c, alpha, safety):
        px = self.px
        head = {"mistake": "Something looks off", "hint": "Here's a closer walkthrough",
                "view_request": "I can't see that clearly", "leave_warning": None}.get(c.kind)
        accent = {"mistake": RED, "view_request": BLUE}.get(c.kind, ORANGE)
        layer = img.copy()
        d = ImageDraw.Draw(layer)
        fb, fh = F(px(30)), F(px(22), "Semi")
        cw = px(860)
        lines = wrap(d, c.text, fb, cw - px(76))
        h = px(36) + (px(34) if head else 0) + len(lines) * px(40) + px(14)
        x0 = (img.width - cw) / 2
        y0 = img.height - px(84) - h
        if safety:
            sp = "SAFETY-CRITICAL STEP · FOLLOW THE PROCEDURE EXACTLY"
            fs = F(px(16), "MonoMed")
            sw = d.textlength(sp, font=fs)
            frosted(layer, (x0, y0 - px(46), x0 + sw + px(40), y0 - px(10)), px(18), tint=(60, 24, 8), alpha=0.82)
            d = ImageDraw.Draw(layer)
            d.text((x0 + px(20), y0 - px(39)), sp, font=fs, fill=(255, 170, 130))
        frosted(layer, (x0, y0, x0 + cw, y0 + h), px(22), alpha=0.78)
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle([x0 + px(18), y0 + px(22), x0 + px(24), y0 + h - px(22)], px(3), fill=accent)
        y = y0 + px(20)
        if head:
            d.text((x0 + px(44), y), head, font=fh, fill=accent if c.kind == "mistake" else MUTED)
            y += px(34)
        for ln in lines:
            d.text((x0 + px(44), y), ln, font=fb, fill=ALU)
            y += px(40)
        img.paste(Image.blend(img, layer, alpha))


def footer(img: Image.Image, tau: float, k: float = 1.0, caption: str | None = None, cap_a: float = 0.0) -> None:
    d = ImageDraw.Draw(img)
    f = F(int(15 * k), "Mono")
    txt = f"REAL MODEL OUTPUT · {SOURCE_LABEL.upper()} · SESSION {mmss(tau)}"
    tw = d.textlength(txt, font=f)
    frosted(img, (int(18 * k), img.height - int(42 * k), int(42 * k) + tw, img.height - int(12 * k)), int(8 * k),
            alpha=0.6, blur=10)
    d = ImageDraw.Draw(img)
    d.text((int(30 * k), img.height - int(34 * k)), txt, font=f, fill=(225, 228, 226))
    if caption and cap_a > 0:
        layer = img.copy()
        fc = F(int(22 * k), "Semi")
        dl = ImageDraw.Draw(layer)
        w = dl.textlength(caption, font=fc)
        x0 = img.width - w - int(78 * k)
        y0 = int(30 * k)
        frosted(layer, (x0, y0, x0 + w + int(48 * k), y0 + int(50 * k)), int(8 * k), alpha=0.82)
        dl = ImageDraw.Draw(layer)
        dl.rectangle([x0, y0, x0 + int(5 * k), y0 + int(50 * k)], fill=ORANGE)
        dl.text((x0 + int(24 * k), y0 + int(12 * k)), caption, font=fc, fill=ALU)
        img.paste(Image.blend(img, layer, cap_a))


# ---------------------------------------------------------------- engineer view

class Engineer:
    VX, VY, VW, VH = 24, 24, 1328, 747
    CX = 1376

    def __init__(self, s: Session, view_cards: bool = False):
        self.s = s
        self.hud = UserHUD(s, scale=self.VW / W, view_cards=view_cards)

    def draw(self, frame: Image.Image, tau: float, caption: str | None, cap_a: float) -> Image.Image:
        s = self.s
        img = Image.new("RGB", (W, H), GRAPHITE)
        v = frame.resize((self.VW, self.VH), Image.BILINEAR)
        v = self.hud.draw(v, tau)
        footer(v, tau, self.VW / W, caption, cap_a)
        img.paste(v, (self.VX, self.VY))
        d = ImageDraw.Draw(img)
        self._header(d, tau)
        self._tracker(d, tau)
        self._calls(d, tau)
        self._timeline(img, tau)
        return img

    def _header(self, d, tau):
        x = self.CX
        d.text((x, 22), "UNDER THE HOOD", font=F(17, "MonoMed"), fill=ORANGE)
        d.text((x + 380, 22), mmss(tau), font=F(17, "MonoMed"), fill=ALU)
        d.text((x, 48), "live loop · fast tier jev-1.14.0 · escalation claude-opus-5-5", font=F(14, "Mono"), fill=MUTED)

    def _tracker(self, d, tau):
        s, x, y0 = self.s, self.CX, 84
        b = s.last(s.beliefs, tau)
        f = s.last(s.fast, tau)
        d.rounded_rectangle([x - 12, y0, W - 24, y0 + 330], 10, fill=PANEL)
        d.text((x + 4, y0 + 12), "L4 STATE TRACKER · P(step)", font=F(15, "MonoMed"), fill=ALU)
        if not b:
            return
        top = sorted(b["p"].items(), key=lambda kv: -kv[1])
        top = [kv for kv in top if kv[0] in s.names][:6]
        y = y0 + 44
        fn, fm = F(15), F(14, "Mono")
        for sid, p in top:
            is_map = sid == b["map"]
            done = sid in b["completed"]
            name = clip(d, f"{sid}  {s.names[sid]}", fn, 300)
            d.text((x + 4, y), name, font=fn, fill=ALU if is_map else MUTED)
            bx = x + 318
            d.rounded_rectangle([bx, y + 3, bx + 140, y + 15], 4, fill=RULE)
            if p > 0.004:
                d.rounded_rectangle([bx, y + 3, bx + max(8, int(140 * p)), y + 15], 4, fill=ORANGE if is_map else STEEL)
            d.text((bx + 148, y - 1), f"{p:.2f}", font=fm, fill=ALU if is_map else MUTED)
            y += 27
        y += 6
        d.line([x + 4, y, W - 36, y], fill=RULE)
        y += 10
        prof = b["user"]["profile"]
        rows = [("entropy", f"{b['entropy']:.2f}"), ("time on step", f"{b['time_on_step']:.0f} s"),
                ("done", ", ".join(b["completed"]) or "–"), ("user profile", prof)]
        if f:
            rows += [("hands in view", str(f["hands"])), ("L2 boundary", f"{f['boundary']:.2f}")]
        for i, (kk, vv) in enumerate(rows):
            cx = x + 4 + (i % 2) * 250
            cy = y + (i // 2) * 24
            d.text((cx, cy), kk, font=fm, fill=MUTED)
            d.text((cx + 128, cy), vv, font=fm, fill=ORANGE if (kk == "user profile" and prof != "standard") else ALU)

    def _calls(self, d, tau):
        s, x, y0 = self.s, self.CX, 428
        d.rounded_rectangle([x - 12, y0, W - 24, y0 + 343], 10, fill=PANEL)
        d.text((x + 4, y0 + 12), "MODEL CALLS", font=F(15, "MonoMed"), fill=ALU)
        d.text((x + 150, y0 + 13), "newest first · time = when the engine used the answer", font=F(12, "Mono"), fill=MUTED)
        fm, fs = F(14, "MonoMed"), F(13, "Mono")
        items = []
        for c in s.calls:
            if c["model"] == "opus" and c["sent"] <= tau < c["back"]:
                items.append(("flight", c))
            elif c["back"] <= tau:
                items.append(("back", c))
        items = sorted(items, key=lambda it: -(it[1]["sent"] if it[0] == "flight" else it[1]["back"]))[:7]
        y = y0 + 42
        for kind, c in items:
            opus = c["model"] == "opus"
            tag = "OPUS" if opus else "JEV "
            tcol = ORANGE if opus else ALU
            if kind == "flight":
                waited = tau - c["sent"]
                d.text((x + 4, y), f"{mmss(c['sent']):>6}", font=fs, fill=MUTED)
                d.text((x + 72, y), tag, font=fm, fill=tcol)
                d.text((x + 120, y), f"escalation in flight … {waited:.1f} s", font=fm, fill=ORANGE)
                dots = int(tau * 4) % 4
                d.text((x + 120, y + 19), "waiting for the answer" + "." * dots, font=fs, fill=MUTED)
            else:
                age = tau - c["back"]
                hi = age < 0.6
                d.text((x + 4, y), f"{mmss(c['back']):>6}", font=fs, fill=ALU if hi else MUTED)
                d.text((x + 72, y), tag, font=fm, fill=tcol)
                lat = f"{c['lat'] * 1000:.0f} ms" if c["lat"] < 1 else f"{c['lat']:.1f} s"
                d.text((x + 120, y), f"{c['what']:<10} {lat}", font=fm, fill=ALU)
                d.text((x + 120, y + 19), clip(d, c["res"], fs, 380), font=fs, fill=c["color"])
                if c.get("note"):
                    y += 19
                    d.text((x + 120, y + 19), clip(d, f"“{c['note']}”", fs, 380), font=fs, fill=MUTED)
            y += 44
            if y > y0 + 320:
                break

    def _timeline(self, img, tau):
        s = self.s
        d = ImageDraw.Draw(img)
        x0, x1, y0, y1 = 24, W - 24, 795, H - 22
        d.rounded_rectangle([x0, y0, x1, y1], 10, fill=PANEL)
        span, lead = 30.0, 3.0
        lx = x0 + 170
        def X(t):
            return lx + (t - (tau - span + lead)) / span * (x1 - 16 - lx)
        lanes = [("L2 event detector", 46), ("Jev · fast tier", 38), ("Opus · escalation", 38),
                 ("L4 step (MAP)", 30), ("L6 policy", 50)]
        y = y0 + 14
        ys = {}
        fl = F(14, "MonoMed")
        for name, hgt in lanes:
            ys[name] = (y, y + hgt)
            d.text((x0 + 14, y + hgt / 2 - 9), name, font=fl, fill=MUTED)
            d.line([lx, y + hgt, x1 - 16, y + hgt], fill=RULE)
            y += hgt + 8
        lo, hi = tau - span + lead, tau + lead
        # L2 boundary + grasp traces
        ya, yb = ys["L2 event detector"]
        for key, col in (("grasp", STEEL), ("boundary", ALU)):
            pts = [(X(r["t"]), yb - 2 - r[key] * (yb - ya - 6)) for r in s.fast if lo <= r["t"] <= tau]
            if len(pts) > 1:
                d.line(pts, fill=col, width=2)
        thr = yb - 2 - 0.8 * (yb - ya - 6)
        for xx in range(int(lx), int(x1 - 16), 12):
            d.line([xx, thr, xx + 5, thr], fill=(90, 60, 40))
        # Jev calls: tick at send, bar to answer
        ya, yb = ys["Jev · fast tier"]
        for c in s.calls:
            if c["model"] != "jev" or not (lo <= c["sent"] <= tau):
                continue
            row = ya + (6 if c["what"] == "localize" else 22)
            end = min(c["back"], tau)
            d.rectangle([X(c["sent"]), row, max(X(c["sent"]) + 3, X(end)), row + 10], fill=c["color"])
        # Opus escalations: bar from send to answer (grows while in flight)
        ya, yb = ys["Opus · escalation"]
        fs = F(13, "Mono")
        busy = []                                  # escalations can overlap: stack them
        for c in sorted((c for c in s.calls if c["model"] == "opus"), key=lambda c: c["sent"]):
            if not (lo - 20 <= c["sent"] <= tau) or c["back"] < lo:
                continue
            k = next((i for i, e in enumerate(busy) if e <= c["sent"]), len(busy))
            busy[k:k + 1] = [c["back"]]
            yy = ya + 2 + (k % 2) * 18
            end = min(c["back"], tau)
            xa = max(X(c["sent"]), lx)
            done = c["back"] <= tau
            d.rounded_rectangle([xa, yy, max(xa + 4, X(end)), yy + 14], 3, outline=ORANGE,
                                fill=c["color"] if done else None, width=2)
            lab = (f"model {c['lat']:.1f} s · used +{c['back'] - c['sent']:.1f} s → {c['status'].replace('_', ' ')}"
                   if done else f"{tau - c['sent']:.1f} s…")
            if X(end) > lx:
                d.text((X(end) + 8, yy), lab, font=fs, fill=ALU if done else ORANGE)
        # L4 MAP step band
        ya, yb = ys["L4 step (MAP)"]
        seg = None
        for r in s.beliefs:
            if not (lo - 1 <= r["t"] <= tau):
                continue
            if seg is None or seg[0] != r["map"]:
                if seg:
                    self._band(d, X, seg, ya, yb)
                seg = [r["map"], r["t"], r["t"], r["map_p"]]
            seg[2] = r["t"]
        if seg:
            seg[2] = tau
            self._band(d, X, seg, ya, yb)
        # L6 policy: actions, commits, overrules
        ya, yb = ys["L6 policy"]
        marks = [(a["t"], a["action"], RED if a["action"] == "mistake" else ORANGE) for a in s.st.actions
                 if a["action"] in ("instruct", "mistake", "hint", "announce_task")]
        marks += [(c["t"], f"commit {c['node']}", GREEN) for c in s.commits]
        marks += [(o["t"], "alert suppressed", MUTED) for o in s.overruled]
        marks += [(x["t"], "safety flag", (255, 170, 130)) for x in s.safety]
        lastx = -1e9
        row = 0
        for t, lab, col in sorted(marks):
            if not (lo - 6 <= t <= tau):
                continue
            xx = X(t)
            row = row + 1 if xx - lastx < 130 else 0
            lastx = xx
            d.line([xx, ya, xx, yb], fill=col, width=2)
            if xx > lx - 2:
                d.text((xx + 5, ya + 2 + (row % 3) * 16), lab, font=fs, fill=col)
        # playhead + axis
        px_ = X(tau)
        d.line([px_, y0 + 8, px_, y1 - 22], fill=ORANGE, width=2)
        for t in range(int(lo) + 1, int(hi) + 1):
            if t % 5 == 0:
                d.text((X(t) - 18, y1 - 20), mmss(t)[:-2], font=F(12, "Mono"), fill=MUTED)

    def _band(self, d, X, seg, ya, yb):
        sid, t0, t1, p = seg
        xa, xb = max(X(t0), 194), X(t1)
        if xb <= xa:
            return
        idx = int(sid[1:]) if sid[1:].isdigit() else 0
        shade = 70 + (idx * 37) % 90
        d.rectangle([xa, ya + 4, xb, yb - 2], fill=(shade, shade + 6, shade + 8))
        if xb - xa > 40:
            d.text((xa + 6, ya + 7), sid, font=F(14, "MonoMed"), fill=GRAPHITE)


# ---------------------------------------------------------------- title / end cards

def title_card(k: float = 1.0) -> Image.Image:
    img = Image.new("RGB", (W, H), GRAPHITE)
    lock = Image.open(LOCKUP).convert("RGBA")
    lw = 620
    lock = lock.resize((lw, int(lock.height * lw / lock.width)), Image.LANCZOS)
    img.paste(lock, ((W - lw) // 2, 380), lock)
    d = ImageDraw.Draw(img)
    t1 = "Instructions that can finally see how you're doing."
    f1 = F(34)
    d.text(((W - d.textlength(t1, font=f1)) / 2, 560), t1, font=f1, fill=ALU)
    t2 = "REAL REPAIR FOOTAGE · REAL MODEL OUTPUT · ONE LIVE SESSION"
    f2 = F(18, "MonoMed")
    d.text(((W - d.textlength(t2, font=f2)) / 2, 630), t2, font=f2, fill=ORANGE)
    return img


def end_card(s: Session, view: str) -> Image.Image:
    img = title_card()
    d = ImageDraw.Draw(img)
    d.rectangle([0, 540, W, H], fill=GRAPHITE)
    sess = s.session
    calls = sess["calls_by_model"]
    lines = [
        f"Selected moments from one {mmss(sess['duration_s'])[:-2]} live session on {SOURCE_LABEL}.",
        "Procedure compiled from the lab's written instructions; the models were never trained on this task.",
    ]
    if view == "engineer":
        lines += [
            f"{calls.get('jev-1.14.0', 0)} fast-tier calls · {calls.get('claude-opus-5-5', 0)} escalations · "
            f"${sess['cost']['verifier_usd']:.3f} total · {sess['errors']} errors",
            "Fast tier answers in 150 ms (median); Opus double-checks 14 moments in about 4 s each.",
        ]
    f = F(24)
    y = 590
    for i, ln in enumerate(lines):
        col = ALU if i < 2 else MUTED
        d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, font=f, fill=col)
        y += 44
    t3 = "AI guidance for the physical world."
    f3 = F(20, "MonoMed")
    d.text(((W - d.textlength(t3, font=f3)) / 2, H - 120), t3.upper(), font=f3, fill=ORANGE)
    return img


# ---------------------------------------------------------------- assembly

def frames(src: Path, start: float, dur: float):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{dur:.3f}",
           "-vf", f"fps={FPS},scale={W}:{H}:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        yield Image.frombuffer("RGB", (W, H), buf)
    p.wait()


def render(view: str, out: Path, s: Session, beats: list[Beat] = BEATS, cards: bool = True,
           view_cards: bool = False) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    put = lambda im: enc.stdin.write(im.tobytes())
    eng = Engineer(s, view_cards) if view == "engineer" else None
    hud = UserHUD(s, view_cards=view_cards)
    title = title_card()
    for i in range(int(TITLE_S * FPS) if cards else 0):
        put(Image.blend(Image.new("RGB", (W, H), GRAPHITE), title, min(1, i / 10, (TITLE_S * FPS - i) / 8)))
    for b in beats:
        n_total = int(round((b.end - b.start) * FPS))
        for i, fr in enumerate(frames(SOURCE, b.start, b.end - b.start)):
            if i >= n_total:
                break
            tau = b.start + i / FPS
            age = i / FPS
            cap_a = max(0.0, min(1.0, age / 0.3, (3.2 - age) / 0.4))
            if eng:
                im = eng.draw(fr.copy(), tau, b.caption, cap_a)
            else:
                im = hud.draw(fr.copy(), tau)
                footer(im, tau, 1.0, b.caption, cap_a)
            edge = min(i, n_total - 1 - i) / FPS
            if edge < XFADE:
                im = Image.blend(Image.new("RGB", (W, H), GRAPHITE), im, max(0.0, edge / XFADE))
            put(im)
    end = end_card(s, view)
    for i in range(int(END_S * FPS) if cards else 0):
        put(Image.blend(Image.new("RGB", (W, H), GRAPHITE), end, min(1, i / 10)))
    enc.stdin.close()
    enc.wait()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--view", choices=["user", "engineer", "both"], default="both")
    ap.add_argument("--out", default=str(RENDERS / "demo"))
    ap.add_argument("--cut", choices=["full", "short"], default="full", help="short: ~17 s, no title or end card")
    ap.add_argument("--view-cards", action="store_true", help="draw logged view requests as HUD cards (tagged)")
    ap.add_argument("--beat", type=int, default=None, help="render only this beat (0-based) of the chosen cut")
    a = ap.parse_args()
    s = Session(SESSION)
    short = a.cut == "short"
    for v in (["user", "engineer"] if a.view == "both" else [a.view]):
        name = f"praxis_repair_{'short' if short else 'demo'}_{v}.mp4"
        beats = BEATS_SHORT if short else BEATS
        if a.beat is not None:
            beats, name = [beats[a.beat]], name.replace(".mp4", f"_beat{a.beat}.mp4")
        p = render(v, Path(a.out) / name, s, beats, cards=not short and a.beat is None, view_cards=a.view_cards)
        print(p)


if __name__ == "__main__":
    main()

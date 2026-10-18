"""Praxis HUD concept mocks on stock first-person photos (1920x1080), text outlined from Archivo / IBM Plex Mono."""
import os, sys
sys.argv = [sys.argv[0], os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out')] + sys.argv[1:]
from wm import text_path
from build import SW, R, SX, TOP, BOT, DOT, MARK_BOX
from marks import pt, arc
G, AL, PL, ST, OR = '#16191B', '#E8EBE9', '#F6F7F6', '#5E676C', '#FF5B14'
GREEN, BLUE, RED = '#3DD68C', '#2F6FEB', '#D92D20'
UI = dict(wdth=100, wght=600); UI4 = dict(wdth=100, wght=430)

def T(s, size, x, y, fill, font='archivo', ax=UI, trk=0):
    d, w, _ = text_path(font, s, size, tracking=trk, x0=x, baseline=y, **(ax if font == 'archivo' else {}))
    return f'<path d="{d}" fill="{fill}"/>', w
def mono(s, size, x, y, fill): return T(s, size, x, y, fill, 'plexmono', trk=60)

def prog(frac, x, y, h, ink=AL, track='#4A5156'):
    cx, cy = SX + R, TOP + SW/2 + R; a1 = 270 + 180*frac; ex, ey = pt(cx, cy, R, a1)
    s = h / (MARK_BOX[3] - MARK_BOX[1]); tx, ty = x - MARK_BOX[0]*s, y - MARK_BOX[1]*s
    g = f'<path d="{arc(cx, cy, R, a1, 450)}" stroke="{track}" stroke-width="{SW*0.34}" fill="none"/>' if frac < 1 else ''
    g += f'<path d="M{SX} {BOT}V{TOP+SW/2}H{cx}A{arc(cx, cy, R, 270, a1).split("A",1)[1]}" stroke="{ink}" stroke-width="{SW}" fill="none"/>'
    g += f'<circle cx="{ex:.2f}" cy="{ey:.2f}" r="{DOT}" fill="{OR}"/>'
    return f'<g transform="translate({tx:.1f} {ty:.1f}) scale({s:.4f})">{g}</g>', (MARK_BOX[2]-MARK_BOX[0])*s

def progress(step, total, x=56, y=56):
    m, mw = prog(step/total, x+22, y+16, 56)
    t, tw = mono(f'STEP {step}/{total}', 26, x+22+mw+18, y+54, AL)
    return f'<rect x="{x}" y="{y}" width="{22+mw+18+tw+26:.0f}" height="88" rx="14" fill="{G}" fill-opacity=".8"/>' + m + t

def chip(text, label=None, label_color='#9AA3A7', x=56, bottom=1016, right_align=False):
    t, tw = T(text, 40, 0, 0, AL); h = 96 + (40 if label else 0); w = tw + 30 + 34
    x0 = (1920 - 56 - w) if right_align else x; y0 = bottom - h
    s = f'<rect x="{x0}" y="{y0}" width="{w:.0f}" height="{h}" rx="10" fill="{G}" fill-opacity=".86"/><rect x="{x0}" y="{y0}" width="8" height="{h}" fill="{OR}"/>'
    if label: l, _ = mono(label, 22, x0+38, y0+44, label_color); s += l
    t, _ = T(text, 40, x0+38, y0 + h - 34, AL); return s + t, (x0, y0, x0 + w, y0 + h)

def card(kind, color, title, lines, x, y, w=700):
    h = 64 + 56 + 46*len(lines) + 30
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{PL}"/><path d="M{x} {y+10}V{y+10}A10 10 0 0 1 {x+10} {y}H{x+w-10}A10 10 0 0 1 {x+w} {y+10}V{y+12}H{x}Z" fill="{color}"/>'
    s += mono(kind, 22, x+34, y+62, color if color != BLUE else '#1D4ED8')[0]
    s += T(title, 40, x+34, y+118, G)[0]
    for i, ln in enumerate(lines): s += T(ln, 31, x+34, y+170+46*i, '#3C4347', ax=UI4)[0]
    return s, (x, y, x + w, y + h)

def pulse(cx, cy, color=GREEN):
    return (f'<circle cx="{cx}" cy="{cy}" r="44" stroke="{color}" stroke-width="7" fill="none"/>'
            f'<circle cx="{cx}" cy="{cy}" r="72" stroke="{color}" stroke-width="4" fill="none" opacity=".45"/>')

def brackets(x0, y0, x1, y1, color, L=46, sw=6, dash=False):
    d = f'M{x0} {y0+L}V{y0}H{x0+L}M{x1-L} {y0}H{x1}V{y0+L}M{x1} {y1-L}V{y1}H{x1-L}M{x0+L} {y1}H{x0}V{y1-L}'
    return f'<path d="{d}" stroke="{color}" stroke-width="{sw}" fill="none"/>'

def tag(x=None):
    t, tw = mono('CONCEPT MOCK · STOCK PHOTO', 18, 0, 0, AL); x0 = 1920 - 40 - tw - 28
    return f'<rect x="{x0}" y="1032" width="{tw+28:.0f}" height="34" rx="6" fill="{G}" fill-opacity=".6"/>' + mono('CONCEPT MOCK · STOCK PHOTO', 18, x0+14, 1056, '#C9CFCC')[0]

def clamp(v, a, b): return max(a, min(b, v))
def leader(src, reg, color):
    """Line from the chip/card edge to the region edge, ending in a dot (the logo's dot)."""
    rx0, ry0, rx1, ry1 = reg; cx, cy = (rx0 + rx1) / 2, (ry0 + ry1) / 2
    sx0, sy0, sx1, sy1 = src
    ax, ay = clamp(cx, sx0 + 24, sx1 - 24), clamp(cy, sy0, sy1)
    if sy0 < cy < sy1: ax = sx0 if cx < sx0 else sx1
    bx, by = clamp(ax, rx0 + 30, rx1 - 30), clamp(ay, ry0, ry1)
    if ry0 < ay < ry1: bx = rx0 if ax < rx0 else rx1
    return (f'<path d="M{ax:.0f} {ay:.0f}L{bx:.0f} {by:.0f}" stroke="{color}" stroke-width="4"/>'
            f'<circle cx="{ax:.0f}" cy="{ay:.0f}" r="7" fill="{color}"/><circle cx="{bx:.0f}" cy="{by:.0f}" r="11" fill="{color}" stroke="#16191B" stroke-width="3"/>')

def frame(img, hud, reg=None, color=OR, src=None, dashed=False, veil=0.42, sat=0.3):
    """Photo desaturated and veiled in graphite; the target region stays in full color with an outline."""
    defs = f'<defs><filter id="ds" color-interpolation-filters="sRGB"><feColorMatrix type="saturate" values="{sat}"/></filter>'
    body = f'<image href="{img}" xlink:href="{img}" width="1920" height="1080" preserveAspectRatio="xMidYMid slice" filter="url(#ds)"/>'
    body += f'<rect width="1920" height="1080" fill="#1A1E21" opacity="{veil}"/>'
    if reg:
        x0, y0, x1, y1 = reg
        defs += f'<clipPath id="rg"><rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" rx="22"/></clipPath>'
        body += f'<image href="{img}" xlink:href="{img}" width="1920" height="1080" preserveAspectRatio="xMidYMid slice" clip-path="url(#rg)"/>'
        dash = ' stroke-dasharray="18 12"' if dashed else ''
        body += f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" rx="22" stroke="{color}" stroke-width="5" fill="none"{dash}/>'
        if src: body += leader(src, reg, color)
    defs += '</defs>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1920" height="1080" viewBox="0 0 1920 1080">{defs}{body}{hud}{tag()}</svg>'

c_step = chip('Loosen the four float-bowl screws a half turn each')
c_ver = chip('Rotate the crank to bring cylinder 3 to TDC', label='STEP 5 VERIFIED · VALVE LASH SET', label_color=GREEN)
k_mis = card('MISTAKE CAUGHT', RED, 'Lockout was skipped.', ['Open and lock the feeder breaker,', 'tag it, then test for zero voltage.'], 1164, 660, 700)
k_view = card('NEED A BETTER VIEW', BLUE, "Can't see the bearing cap.", ['Lean in over cylinder 2 and', 'hold still for two seconds.'], 1164, 56, 700)
c_cov = chip('Seat the clamp past the hose bead', right_align=True)
F = {
 'hud-step': frame('carb.jpg', progress(3, 8) + c_step[0], reg=(800, 300, 1260, 820), color=OR, src=c_step[1]),
 'hud-verified': frame('valve.jpg', progress(5, 11) + pulse(660, 740) + c_ver[0], reg=(470, 560, 860, 860), color=GREEN, src=c_ver[1]),
 'hud-mistake': frame('panel.jpg', progress(2, 7) + k_mis[0], reg=(720, 160, 1160, 600), color=RED, src=k_mis[1]),
 'hud-view': frame('block.jpg', progress(6, 12) + k_view[0], reg=(330, 620, 780, 1010), color='#6EA8FF', src=k_view[1], dashed=True),
 'hud-cover': frame('cover.jpg', progress(4, 9, x=1920-56-300) + pulse(1010, 790) + c_cov[0], reg=(860, 640, 1180, 900), color=GREEN, src=c_cov[1], veil=0.3, sat=0.45),
}
out = sys.argv[3]
for k, v in F.items(): open(os.path.join(out, k + '.svg'), 'w').write(v)
print(' '.join(F))

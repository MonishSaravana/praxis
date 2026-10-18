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
    t, _ = T(text, 40, x0+38, y0 + h - 34, AL); return s + t

def card(kind, color, title, lines, x, y, w=700):
    h = 64 + 56 + 46*len(lines) + 30
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{PL}"/><path d="M{x} {y+10}V{y+10}A10 10 0 0 1 {x+10} {y}H{x+w-10}A10 10 0 0 1 {x+w} {y+10}V{y+12}H{x}Z" fill="{color}"/>'
    s += mono(kind, 22, x+34, y+62, color if color != BLUE else '#1D4ED8')[0]
    s += T(title, 40, x+34, y+118, G)[0]
    for i, ln in enumerate(lines): s += T(ln, 31, x+34, y+170+46*i, '#3C4347', ax=UI4)[0]
    return s

def pulse(cx, cy, color=GREEN):
    return (f'<circle cx="{cx}" cy="{cy}" r="44" stroke="{color}" stroke-width="7" fill="none"/>'
            f'<circle cx="{cx}" cy="{cy}" r="72" stroke="{color}" stroke-width="4" fill="none" opacity=".45"/>')

def brackets(x0, y0, x1, y1, color, L=46, sw=6, dash=False):
    d = f'M{x0} {y0+L}V{y0}H{x0+L}M{x1-L} {y0}H{x1}V{y0+L}M{x1} {y1-L}V{y1}H{x1-L}M{x0+L} {y1}H{x0}V{y1-L}'
    return f'<path d="{d}" stroke="{color}" stroke-width="{sw}" fill="none"/>'

def tag(x=None):
    t, tw = mono('CONCEPT MOCK · STOCK PHOTO', 18, 0, 0, AL); x0 = 1920 - 40 - tw - 28
    return f'<rect x="{x0}" y="1032" width="{tw+28:.0f}" height="34" rx="6" fill="{G}" fill-opacity=".6"/>' + mono('CONCEPT MOCK · STOCK PHOTO', 18, x0+14, 1056, '#C9CFCC')[0]

def frame(img, body, shade=0.0):
    sh = f'<rect width="1920" height="1080" fill="#000" opacity="{shade}"/>' if shade else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1920" height="1080" viewBox="0 0 1920 1080"><image href="{img}" xlink:href="{img}" width="1920" height="1080" preserveAspectRatio="xMidYMid slice"/>{sh}{body}{tag()}</svg>'

F = {
 'hud-step': frame('carb.jpg', progress(3, 8) + chip('Loosen the four float-bowl screws a half turn each')),
 'hud-verified': frame('valve.jpg', progress(5, 11) + pulse(660, 760) + chip('Rotate the crank to bring cylinder 3 to TDC', label='STEP 5 VERIFIED · VALVE LASH SET', label_color=GREEN)),
 'hud-mistake': frame('panel.jpg', progress(2, 7) + brackets(740, 170, 1150, 620, RED)
                      + card('MISTAKE CAUGHT', RED, 'Lockout was skipped.', ['Open and lock the feeder breaker,', 'tag it, then test for zero voltage.'], 1164, 640, 700)),
 'hud-view': frame('block.jpg', progress(6, 12) + brackets(330, 640, 760, 1030, '#6EA8FF', sw=5)
                   + card('NEED A BETTER VIEW', BLUE, "Can't see the bearing cap.", ['Lean in over cylinder 2 and', 'hold still for two seconds.'], 1164, 56, 700), shade=0.08),
 'hud-cover': frame('cover.jpg', progress(4, 9, x=1920-56-300) + pulse(1010, 790) + chip('Seat the clamp past the hose bead', right_align=True)),
}
out = sys.argv[3]
for k, v in F.items(): open(os.path.join(out, k + '.svg'), 'w').write(v)
print(' '.join(F))

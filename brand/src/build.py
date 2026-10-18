"""Build Praxis brand assets: mark, wordmark (outlined Archivo), lockups, icons."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wm import text_path, font, glyph_name
from fontTools.pens.boundsPen import BoundsPen
from marks import pt, arc
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
C = dict(graphite='#16191B', aluminum='#E8EBE9', plate='#F6F7F6', steel='#5E676C', orange='#FF5B14')

# --- mark: 64 grid. Stem + bowl traced like a progress ring; the dot is the step you're on.
SW, R, SX, TOP, BOT, DOT, GAP, DX = 9, 14.5, 17.5, 8, 56, 6, 90, 0
def mark(ink, sig, x=0, y=0, s=1):
    cx, cy = SX + R, TOP + SW/2 + R
    a_end = 540 - GAP; ex, ey = pt(cx, cy, R, a_end)
    d = f'M{SX} {BOT}V{TOP+SW/2}M{SX-SW/2} {TOP+SW/2}H{cx}{arc(cx, cy, R, 270, a_end)[0:0]}'
    a = arc(cx, cy, R, 270, a_end).split('A', 1)[1]
    g = (f'<path d="M{SX} {BOT}V{TOP+SW/2}H{cx}A{a}" stroke="{ink}" stroke-width="{SW}" stroke-linejoin="miter" fill="none"/>'
         f'<circle cx="{ex:.2f}" cy="{ey:.2f}" r="{DOT}" fill="{sig}"/>')
    return f'<g transform="translate({x} {y}) scale({s})">{g}</g>' if (x or y or s != 1) else g
MARK_BOX = (SX - SW/2, TOP, SX + 2*R + SW/2, BOT)   # x0,y0,x1,y1 in 64 grid

# --- wordmark
AX = dict(wdth=125, wght=600); TRK = -10
def wordmark(ink, sig, size=100, x0=0, baseline=0):
    d, w, info = text_path('archivo', 'praxıs', size, tracking=TRK, x0=x0, baseline=baseline, **AX)
    f = font('archivo', **AX); gs = f.getGlyphSet(); s = size / f['head'].unitsPerEm
    bi = BoundsPen(gs); gs['i'].draw(bi); bd = BoundsPen(gs); gs[glyph_name(f, 'ı')].draw(bd)
    stem = (bd.bounds[2] - bd.bounds[0]) * s
    top_i, xh = bi.bounds[3] * s, bd.bounds[3] * s
    r = stem * 0.56
    bx, b = info['boxes'][4]; cx = bx + (b[0] + b[2]) / 2
    cy = baseline - (top_i - stem/2) + (r - stem/2) * 0.0
    bp = BoundsPen(gs); gs[glyph_name(f, 'p')].draw(bp)
    desc = -bp.bounds[1] * s
    svg = f'<path d="{d}" fill="{ink}"/><circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{sig}"/>'
    return svg, dict(width=w, top=baseline - top_i - (r - stem/2), xh=xh, desc=desc, baseline=baseline, stem=stem, left=x0 + info['boxes'][0][1][0])

def doc(w, h, body, bg=None, title='Praxis'):
    rect = f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.2f} {h:.2f}" width="{w:.0f}" height="{h:.0f}" role="img" aria-label="{title}"><title>{title}</title>{rect}{body}</svg>\n'

files = {}
for tone, ink, sig in (('', C['graphite'], C['orange']), ('-white', '#FFFFFF', C['orange']), ('-black', '#000000', '#000000')):
    mw, mh = MARK_BOX[2] - MARK_BOX[0], MARK_BOX[3] - MARK_BOX[1]
    files[f'praxis-mark{tone}.svg'] = doc(mw + 0, mh, mark(ink, sig, -MARK_BOX[0], -MARK_BOX[1]), title='Praxis')
    # wordmark, tight box
    size = 100; body, m = wordmark(ink, sig, size, 0, 0)
    top = m['top']; h = -top + m['desc']
    body, m = wordmark(ink, sig, size, -m['left'], -top)
    files[f'praxis-wordmark{tone}.svg'] = doc(m['width'] - m['left'] * 0, h, body, title='Praxis')
    # horizontal lockup: mark height = dot top .. descender of the wordmark
    s = 1.2 * m['stem'] / SW; gap = 0.36 * mw * s
    mid = -top - m['xh'] / 2 - 0.0
    mx = -MARK_BOX[0] * s; my = mid - (MARK_BOX[1] + mh / 2) * s
    wx = mw * s + gap
    body2, m2 = wordmark(ink, sig, size, wx - m['left'] + m['left'], -top)
    lock = mark(ink, sig, mx, my, s) + body2
    files[f'praxis-lockup{tone}.svg'] = doc(wx + m2['width'], h, lock, title='Praxis')
# app icon + favicon (graphite tile, light mark)
def tile(px, rad):
    mw, mh = MARK_BOX[2] - MARK_BOX[0], MARK_BOX[3] - MARK_BOX[1]
    s = px * 0.6 / mh; ox = (px - mw * s) / 2 - MARK_BOX[0] * s; oy = (px - mh * s) / 2 - MARK_BOX[1] * s
    return doc(px, px, f'<rect width="{px}" height="{px}" rx="{rad}" fill="{C["graphite"]}"/>' + mark(C['aluminum'], C['orange'], ox, oy, s), title='Praxis')
files['praxis-app-icon.svg'] = tile(1024, 230)
files['favicon.svg'] = tile(64, 14)
for k, v in files.items(): open(os.path.join(OUT, k), 'w').write(v)
json.dump({k: v for k, v in files.items()}, open(os.path.join(OUT, '_inline.json'), 'w'))
print('\n'.join(sorted(files)))

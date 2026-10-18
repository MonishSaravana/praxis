"""Static brand fonts + image assets for the editable deck."""
import os, sys, subprocess
B = os.path.dirname(os.path.abspath(__file__)); S = os.path.dirname(B)
sys.argv = [sys.argv[0], os.path.join(S, 'out')]
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from build import SW, R, SX, TOP, BOT, DOT, MARK_BOX
from marks import pt, arc
FD, AD = os.path.join(S, 'deck', 'fonts'), os.path.join(S, 'deck', 'assets')

def static(src, axes, fam, style, typo_fam, typo_style, ps, weight, width):
    f = instantiateVariableFont(TTFont(src), axes)
    n = f['name']
    for nid in (1, 2, 3, 4, 6, 16, 17, 21, 22, 25):
        n.removeNames(nameID=nid)
    full = f'{fam}' if style == 'Regular' and fam == typo_fam else f'{typo_fam} {typo_style}'.replace(' Regular', '') if typo_fam else fam
    for nid, val in ((1, fam), (2, style), (3, f'{ps};praxis-static'), (4, full if fam != 'Archivo' else 'Archivo Regular'), (6, ps)):
        n.setName(val, nid, 3, 1, 0x409); n.setName(val, nid, 1, 0, 0)
    if typo_fam:
        for nid, val in ((16, typo_fam), (17, typo_style)):
            n.setName(val, nid, 3, 1, 0x409); n.setName(val, nid, 1, 0, 0)
    for t in ('STAT', 'fvar', 'avar'):
        if t in f: del f[t]
    f['OS/2'].usWeightClass = weight; f['OS/2'].usWidthClass = width
    f['OS/2'].fsSelection = (f['OS/2'].fsSelection & ~0b1100001) | 0b1000000  # REGULAR bit; not bold/italic
    f['head'].macStyle = 0
    f.save(os.path.join(FD, ps + '.ttf'))
V = os.path.join(S, 'fonts', 'Archivo%5Bwdth,wght%5D.ttf')
static(V, dict(wdth=125, wght=600), 'Archivo Expanded SemiBold', 'Regular', 'Archivo Expanded', 'SemiBold', 'ArchivoExpanded-SemiBold', 600, 7)
static(V, dict(wdth=100, wght=400), 'Archivo', 'Regular', None, None, 'Archivo-Regular', 400, 5)
static(V, dict(wdth=100, wght=600), 'Archivo SemiBold', 'Regular', 'Archivo', 'SemiBold', 'Archivo-SemiBold', 600, 5)
for n in ('IBMPlexMono-Regular.ttf', 'IBMPlexMono-Medium.ttf'):
    TTFont(os.path.join(S, 'fonts', n)).save(os.path.join(FD, n))

def png(svg, name, w=None, h=None):
    p = os.path.join(AD, name + '.svg'); open(p, 'w').write(svg)
    args = ['rsvg-convert', p, '-o', os.path.join(AD, name + '.png')] + (['-w', str(w)] if w else []) + (['-h', str(h)] if h else [])
    subprocess.run(args, check=True); os.remove(p)
def jpg(svg, name):
    p = os.path.join(S, 'stock', '_' + name + '.svg'); open(p, 'w').write(svg)
    subprocess.run(['rsvg-convert', p, '-o', p[:-4] + '.png'], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', p[:-4] + '.png', '-q:v', '3', os.path.join(AD, name + '.jpg')], check=True)

def prog(frac, ink, track, h=256):
    cx, cy = SX + R, TOP + SW/2 + R; a1 = 270 + 180*frac; ex, ey = pt(cx, cy, R, a1)
    x0, y0, x1, y1 = MARK_BOX
    g = f'<path d="{arc(cx, cy, R, a1, 450)}" stroke="#{track}" stroke-width="{SW*0.34:.2f}" fill="none"/>' if frac < 1 else ''
    g += f'<path d="M{SX} {BOT}V{TOP+SW/2}H{cx}A{arc(cx, cy, R, 270, a1).split("A",1)[1]}" stroke="#{ink}" stroke-width="{SW}" fill="none"/>'
    g += f'<circle cx="{ex:.2f}" cy="{ey:.2f}" r="{DOT}" fill="#FF5B14"/>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1-x0} {y1-y0}" width="{(x1-x0)*h/(y1-y0):.0f}" height="{h}">{g}</svg>'
for n, d in ((2, 10), (8, 10), (9, 10)): png(prog(n/d, '16191B', 'C2C8C5'), f'prog-light-{n}of{d}')
for n, d in ((3, 8), (5, 11), (2, 7), (6, 12), (4, 9)): png(prog(n/d, 'E8EBE9', '4A5156'), f'prog-hud-{n}of{d}')
png(prog(7/10, 'E8EBE9', '3A4044', 900), 'prog-divider-7of10')
png(prog(1, 'E8EBE9', '3A4044', 900), 'mark-dark-full')

# dark grid background (the logo's 64-unit construction grid, one cell = 120 px)
lines = ''.join(f'<path d="M{x} 0V1080" stroke="#24282A" stroke-width="2" fill="none"/>' for x in range(0, 1921, 120))
lines += ''.join(f'<path d="M0 {y}H1920" stroke="#24282A" stroke-width="2" fill="none"/>' for y in range(0, 1081, 120))
png(f'<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080"><rect width="1920" height="1080" fill="#16191B"/>{lines}</svg>', 'bg-grid-dark')

# photos: desaturated + graphite veil outside the target, full colour inside (outline/HUD stay native in the deck)
def bg(img, reg, veil=0.42, sat=0.3, scrim=False):
    x0, y0, x1, y1 = reg
    s = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1920" height="1080">'
         f'<defs><filter id="ds" color-interpolation-filters="sRGB"><feColorMatrix type="saturate" values="{sat}"/></filter>'
         f'<clipPath id="rg"><rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" rx="22"/></clipPath>'
         '<linearGradient id="sc" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="#16191B" stop-opacity=".94"/>'
         '<stop offset=".42" stop-color="#16191B" stop-opacity=".8"/><stop offset=".72" stop-color="#16191B" stop-opacity="0"/></linearGradient></defs>'
         f'<image href="{img}" width="1920" height="1080" preserveAspectRatio="xMidYMid slice" filter="url(#ds)"/>'
         f'<rect width="1920" height="1080" fill="#1A1E21" opacity="{veil}"/>'
         f'<image href="{img}" width="1920" height="1080" preserveAspectRatio="xMidYMid slice" clip-path="url(#rg)"/>'
         + ('<rect width="1920" height="1080" fill="url(#sc)"/>' if scrim else '') + '</svg>')
    return s
jpg(bg('carb.jpg', (800, 300, 1260, 820)), 'photo-step')
jpg(bg('valve.jpg', (470, 560, 860, 860)), 'photo-verified')
jpg(bg('panel.jpg', (720, 160, 1160, 600)), 'photo-mistake')
jpg(bg('block.jpg', (330, 620, 780, 1010)), 'photo-view')
jpg(bg('cover.jpg', (860, 640, 1180, 900), veil=0.3, sat=0.45, scrim=True), 'photo-cover')
print('done')

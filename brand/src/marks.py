import math, sys
INK, SIG, TRACK = '#16191B', '#FF5B14', '#C9CFCC'
def pt(cx, cy, r, deg):  # deg: 0=right, 90=down (screen)
    a = math.radians(deg); return cx + r*math.cos(a), cy + r*math.sin(a)
def arc(cx, cy, r, a0, a1):
    x0, y0 = pt(cx, cy, r, a0); x1, y1 = pt(cx, cy, r, a1)
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return f'M{x0:.2f} {y0:.2f}A{r} {r} 0 {large} 1 {x1:.2f} {y1:.2f}'
def progress_p(end=40, sw=9, dot=6.4, track=True, ink=INK, sig=SIG, cap='butt'):
    cx, cy, r, sx = 33, 25.5, 14.5, 18.5
    a_end = 180 + 360 - end   # clockwise from 180 (left) through 270 (top)
    s = [f'<path d="M{sx} 10V54" stroke="{ink}" stroke-width="{sw}" stroke-linecap="{cap}" fill="none"/>']
    if track and end:
        s.append(f'<path d="{arc(cx,cy,r,a_end,540)}" stroke="{TRACK}" stroke-width="{sw*0.42:.1f}" fill="none"/>')
    s.append(f'<path d="{arc(cx,cy,r,180,a_end)}" stroke="{ink}" stroke-width="{sw}" fill="none"/>')
    dx, dy = pt(cx, cy, r, a_end); s.append(f'<circle cx="{dx:.2f}" cy="{dy:.2f}" r="{dot}" fill="{sig}"/>')
    return ''.join(s)
def hex_stripe(sw=7, ink=INK, sig=SIG):
    pts = ' '.join(f'{x:.2f},{y:.2f}' for x, y in (pt(32, 32, 21, 30 + 60*k) for k in range(6)))
    return (f'<polygon points="{pts}" stroke="{ink}" stroke-width="{sw}" fill="none" stroke-linejoin="miter"/>'
            f'<circle cx="32" cy="32" r="7.5" stroke="{ink}" stroke-width="{sw*0.8}" fill="none"/>'
            f'<path d="M44 26L60 18" stroke="{sig}" stroke-width="{sw+1}" stroke-linecap="round"/>')
def frame_dot(sw=6, ink=INK, sig=SIG):
    c = ''.join(f'<path d="{d}" stroke="{ink}" stroke-width="{sw}" fill="none"/>' for d in
        ('M8 22V8H22', 'M42 8H56V22', 'M56 42V56H42', 'M22 56H8V42'))
    return c + f'<circle cx="32" cy="32" r="7" fill="{sig}"/>'
VARIANTS = {
  'p_track40': lambda: progress_p(40), 'p_gap70': lambda: progress_p(70, track=False),
  'p_gap40': lambda: progress_p(40, track=False), 'p_closed': lambda: progress_p(0.01, track=False),
  'p_round': lambda: progress_p(60, track=False, cap='round'), 'hex': hex_stripe, 'frame': frame_dot}
if __name__ == '__main__':
    cells = []; x = 0
    for name, fn in VARIANTS.items():
        g = fn()
        cells.append(f'<g transform="translate({x+20},20) scale(2.6)">{g}</g>')
        cells.append(f'<g transform="translate({x+20},210)">{g}</g>')
        cells.append(f'<g transform="translate({x+100},226) scale(0.5)">{g}</g>')
        cells.append(f'<g transform="translate({x+140},234) scale(0.25)">{g}</g>')
        cells.append(f'<rect x="{x+20}" y="290" width="166" height="80" fill="{INK}"/>')
        cells.append(f'<g transform="translate({x+70},298)">{fn.__wrapped__() if hasattr(fn,"__wrapped__") else g.replace(INK, "#ECEEEC")}</g>')
        cells.append(f'<text x="{x+20}" y="392" font-family="Menlo" font-size="12" fill="#6B7479">{name}</text>')
        x += 200
    open(sys.argv[1], 'w').write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{x+20}" height="410"><rect width="100%" height="100%" fill="#ECEEEC"/>{"".join(cells)}</svg>')

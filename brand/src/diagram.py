"""Praxis architecture diagram, 1920x1080, all text outlined (Archivo + IBM Plex Mono)."""
import os, sys
from wm import text_path
G, AL, PL, ST, OR, OPEN = '#16191B', '#E8EBE9', '#F6F7F6', '#5E676C', '#FF5B14', '#D6DBD8'
W = {}
def T(s, size, x, y, fill=G, wdth=100, wght=600, anchor='start', maxw=None):
    d, w, _ = text_path('archivo', s, size, tracking=0, x0=0, baseline=0, wdth=wdth, wght=wght)
    if maxw and w > maxw: print(f'OVERFLOW {w:.0f}>{maxw} : {s}')
    x0 = x - (w if anchor == 'end' else w / 2 if anchor == 'middle' else 0)
    d, w, _ = text_path('archivo', s, size, tracking=0, x0=x0, baseline=y, wdth=wdth, wght=wght)
    return f'<path d="{d}" fill="{fill}"/>'
def M(s, size, x, y, fill=ST, trk=30, anchor='start', maxw=None):
    d, w, _ = text_path('plexmono', s, size, tracking=trk, x0=0, baseline=0)
    if maxw and w > maxw: print(f'OVERFLOW {w:.0f}>{maxw} : {s}')
    x0 = x - (w if anchor == 'end' else w / 2 if anchor == 'middle' else 0)
    d, w, _ = text_path('plexmono', s, size, tracking=trk, x0=x0, baseline=y)
    return f'<path d="{d}" fill="{fill}"/>'

def box(x, y, w, h, kind, title, plain, specs=(), hero=False, compact=False):
    """kind: ours | open | rented | out"""
    if kind == 'ours': r = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{PL}" stroke="{G}" stroke-width="{3.5 if hero else 2}"/>'
    elif kind == 'open': r = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{OPEN}"/>'
    elif kind == 'rented': r = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="none" stroke="{G}" stroke-width="2.2" stroke-dasharray="12 8"/>'
    else: r = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{OR}"/>'
    tag = {'ours': 'OURS', 'open': 'OPEN MODEL · LOCAL', 'rented': 'RENTED · SWAPPABLE', 'out': ''}[kind]
    s = r
    if tag: s += M(tag, 12.5, x + w - 14, y + 26, fill=(G if kind == 'ours' else ST), trk=80, anchor='end')
    ty, py = (46, 72) if compact else (54, 82)
    s += T(title, 23, x + 18, y + ty, wdth=112, maxw=w - 36)
    s += T(plain, 18, x + 18, y + py, fill='#3C4347' if kind != 'out' else G, wght=430, maxw=w - 36)
    for i, sp in enumerate(specs):
        s += M(sp, 14.5, x + 18, y + (100 if compact else 116) + 24 * i, fill=(G if kind == 'out' else ST), trk=0, maxw=w - 36)
    return s

def arrow(pts, label=None, lx=0, ly=0, anchor='start', dashed=False, color=G):
    d = 'M' + 'L'.join(f'{x} {y}' for x, y in pts)
    s = f'<path d="{d}" stroke="{color}" stroke-width="2" fill="none" marker-end="url(#ah)"{" stroke-dasharray=\"7 6\"" if dashed else ""}/>'
    if label: s += M(label, 13.5, lx, ly, fill=G, trk=20, anchor=anchor)
    return s

def tracker_viz(x, y):
    """Belief over steps: the tracker's running answer to 'where are you?'"""
    ps = [.02, .04, .09, .70, .10, .03, .02]
    s = ''; bw, gap, hmax = 24, 10, 66
    for i, p in enumerate(ps):
        h = max(3, p * hmax / .7); bx = x + i * (bw + gap)
        s += f'<rect x="{bx}" y="{y + hmax - h:.1f}" width="{bw}" height="{h:.1f}" fill="{OR if i == 3 else "#9AA3A7"}"/>'
        s += M(f'S{i+1}', 11.5, bx + bw / 2, y + hmax + 17, fill=(G if i == 3 else ST), trk=0, anchor='middle')
    return s

b = []
# header
b.append(M('HOW PRAXIS WORKS · ENGINE v0', 15, 64, 70, fill=ST, trk=90))
b.append(T('The frontier model is one swappable part. The tracking engine around it is ours.', 36, 64, 120, wdth=125, maxw=1800))
# legend
lx = 64
for kind, label in (('ours', 'Ours: code and trained weights'), ('open', 'Open model, frozen, runs on the device'), ('rented', 'Rented API behind a typed interface')):
    if kind == 'ours': b.append(f'<rect x="{lx}" y="150" width="34" height="20" rx="3" fill="{PL}" stroke="{G}" stroke-width="2"/>')
    elif kind == 'open': b.append(f'<rect x="{lx}" y="150" width="34" height="20" rx="3" fill="{OPEN}"/>')
    else: b.append(f'<rect x="{lx}" y="150" width="34" height="20" rx="3" fill="none" stroke="{G}" stroke-width="2" stroke-dasharray="6 4"/>')
    b.append(T(label, 17, lx + 46, 166, wght=430)); lx += 46 + {'ours': 290, 'open': 350, 'rented': 330}[kind]

# fast-path band goes under everything that crosses it
b.append(f'<rect x="40" y="336" width="1840" height="300" rx="10" fill="{PL}" fill-opacity=".55"/>')
# offline: procedure compiler
b.append(M('OFFLINE, ONCE PER PROCEDURE', 13.5, 64, 232, trk=80))
b.append(box(644, 196, 700, 120, 'ours', 'Procedure compiler', 'Turns a manual into a task graph the engine can track', ('steps · checks · common mistakes · typical durations',), compact=True))
b.append(M('8 procedures compiled', 14, 1374, 236, trk=0))
b.append(M('96 steps · 207 checks', 14, 1374, 258, trk=0))
b.append(M('267 known mistakes', 14, 1374, 280, trk=0))
b.append(M('$4.16 total, one-time', 14, 1374, 302, trk=0))
b.append(arrow([(924, 316), (924, 600), (906, 600)], 'library', 820, 350))
b.append(arrow([(1144, 316), (1144, 378)], 'task graph', 1156, 350))

# fast path band
b.append(M('FAST PATH · EVERY FRAME · ON THE DEVICE · 3.1× FASTER THAN REAL TIME', 13.5, 64, 362, trk=80))
Y, H = 380, 236
b.append(box(64, Y + 20, 220, 196, 'ours', 'Camera', 'First-person video', ('4 frames / s', 'webcam · file ·', 'glasses adapter', '(not yet tested)')))
b.append(box(324, Y, 280, H, 'open', 'Perception', "What's in view", ('SigLIP2 · 20 ms / frame', 'hands · 6 ms / frame', 'V-JEPA 2 · 221 ms, 1× / s')))
b.append(box(644, Y, 260, 108, 'ours', 'Event detector', 'Did a step just end?', ('learned · F1 0.38 vs 0.24',), compact=True))
b.append(box(644, Y + 128, 260, 108, 'ours', 'Task recognizer', 'Which job is this?', ('73% top-1 · median 40 s',), compact=True))
b.append(box(944, Y, 400, H, 'ours', 'State tracker', 'Where you are in the procedure', (), hero=True))
b.append(M('Bayesian semi-Markov model', 14.5, 962, Y + 112, trk=0))
b.append(M('over the task graph', 14.5, 962, Y + 134, trk=0))
b.append(tracker_viz(962, Y + 146))
b.append(M('→ P(step)', 13, 1214, Y + 168, fill=G, trk=0))
b.append(M('→ time on step', 13, 1214, Y + 192, fill=G, trk=0))
b.append(M('→ uncertainty', 13, 1214, Y + 216, fill=G, trk=0))
b.append(box(1384, Y, 250, H, 'ours', 'Policy', 'Should it say anything?', ('speak', 'verify', 'flag a mistake', 'ask for a better view', 'expand the detail')))
b.append(box(1674, Y + 38, 182, 160, 'out', 'Coach', 'Voice + HUD', ('speaks only', 'when confident')))
b.append(arrow([(284, 498), (322, 498)]))
b.append(arrow([(604, 434), (642, 434)]))
b.append(arrow([(604, 562), (642, 562)]))
b.append(arrow([(904, 434), (942, 434)]))
b.append(arrow([(904, 562), (942, 562)]))
b.append(arrow([(1344, 498), (1382, 498)]))
b.append(arrow([(1634, 498), (1672, 498)]))

# slow path band
b.append(f'<rect x="40" y="660" width="1840" height="208" rx="10" fill="none" stroke="#B9C0BC" stroke-width="1.5" stroke-dasharray="4 6"/>')
b.append(M('SLOW PATH · ONLY WHEN SOMETHING HAPPENS · 14% OF FRAMES', 13.5, 64, 686, trk=80))
b.append(box(324, 702, 580, 148, 'ours', 'Flywheel + local student', 'Every session becomes training data', ('local student: 0.03 ms per check, free', 'takes routine checks: 34% fewer frontier calls')))
b.append(box(944, 702, 400, 148, 'rented', 'Verifier', 'Answers one typed question', ('fast: Jev · 151 ms · 88% of calls', 'hard cases: Claude Opus · 3.8 s')))
b.append(box(1384, 702, 250, 148, 'ours', 'Calibration', 'Trusts each answer', ('the right amount', 'error 0.22 → 0.02')))
b.append(arrow([(1080, 616), (1080, 700)], 'a step ends · unsure ·', 1094, 646))
b.append(M('person is stuck', 13.5, 1094, 666, fill=G, trk=20))
b.append(arrow([(1344, 776), (1382, 776)]))
b.append(arrow([(1509, 702), (1509, 650), (1290, 650), (1290, 618)], 'evidence', 1300, 642))
b.append(arrow([(904, 776), (942, 776)]))
b.append(arrow([(980, 616), (980, 640), (760, 640), (760, 700)], 'session records', 772, 654, dashed=True))

# results strip
b.append(f'<path d="M64 900H1856" stroke="{G}" stroke-width="2"/>')
cells = [('54% vs 48%', 'step accuracy, same frontier model', 'with and without our layers'),
         ('$0.018 vs $0.085', 'per minute of video', 'about 5× cheaper'),
         ('77–98%', 'of blurred or blocked views:', 'asks for a better one, never confidently wrong'),
         ('~50 ms', 'local work per frame on a laptop', 'model calls never block the loop')]
cw = (1856 - 64) / 4
for i, (big, l1, l2) in enumerate(cells):
    cx = 64 + i * cw
    if i: b.append(f'<path d="M{cx - 16:.0f} 918V1034" stroke="#B9C0BC" stroke-width="1.5"/>')
    b.append(T(big, 40, cx, 958, fill=(OR if i == 0 else G) if False else G, wdth=125, maxw=cw - 30))
    b.append(T(l1, 17, cx, 990, fill='#3C4347', wght=430, maxw=cw - 30))
    b.append(T(l2, 17, cx, 1014, fill='#3C4347', wght=430, maxw=cw - 30))
b.append(M('Measured on 48 held-out first-person clips from a public dataset (CaptainCook4D) · results/RESULTS.md · docs/CLAIMS.md', 12.5, 64, 1056, trk=10))

svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080" role="img" '
       'aria-label="Praxis architecture: camera, perception, event detector and task recognizer feed a state tracker, then a policy and the coach. Only when something happens does it call a swappable verifier, whose answers are calibrated and fed back. A flywheel turns sessions into a local student model.">'
       '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#16191B"/></marker></defs>'
       f'<rect width="1920" height="1080" fill="{AL}"/>' + ''.join(b) + '</svg>')
open(sys.argv[1], 'w').write(svg); print('ok', len(svg))

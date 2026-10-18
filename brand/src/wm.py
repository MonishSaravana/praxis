import sys, functools
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
import os; F = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fonts') + '/'
FONTS = {'archivo': 'Archivo[wdth,wght].ttf', 'instrument': 'InstrumentSans[wdth,wght].ttf',
         'schibsted': 'SchibstedGrotesk[wght].ttf', 'plexmono': 'IBMPlexMono-Medium.ttf'}

@functools.lru_cache(None)
def font(name, **axes):
    f = TTFont(F + FONTS[name])
    if axes and 'fvar' in f:
        f = instantiateVariableFont(f, axes)
    return f

def glyph_name(f, ch):
    if ch == 'ı': return f.getBestCmap().get(0x131) or 'dotlessi'
    return f.getBestCmap()[ord(ch)]

def text_path(name, text, size, tracking=0, pairs=None, x0=0, baseline=0, **axes):
    """Return (svg path d, advance width, info) with text set at `size` px; tracking in em/1000."""
    f = font(name, **tuple(sorted(axes.items())) and axes)
    gs = f.getGlyphSet(); upm = f['head'].unitsPerEm; s = size / upm
    pen = SVGPathPen(gs); x = 0; boxes = []
    for i, ch in enumerate(text):
        g = glyph_name(f, ch)
        tp = TransformPen(pen, (s, 0, 0, -s, x0 + x * s, baseline))
        gs[g].draw(tp)
        bp = BoundsPen(gs); gs[g].draw(bp); boxes.append((x0 + x*s, bp.bounds and tuple(v*s for v in bp.bounds)))
        x += gs[g].width + tracking * upm / 1000
        if pairs and i + 1 < len(text): x += pairs.get(text[i:i+2], 0) * upm / 1000
    os2 = f['OS/2']
    return pen.getCommands(), x * s, dict(boxes=boxes, xh=os2.sxHeight * s, cap=os2.sCapHeight * s, upm=upm)

"""Glyphs (unicode, font, size, ink box, baseline origin) and drawn rules of a PDF page, via pdfium."""
import ctypes
from dataclasses import dataclass, field

import pypdfium2 as pdfium
import pypdfium2.raw as R


@dataclass
class Glyph:
    u: int
    font: str
    size: float
    x0: float
    y0: float
    x1: float
    y1: float
    ox: float
    oy: float
    weight: int = 400
    raw: bool = False


@dataclass
class Shape:
    kind: str  # "hrule", "vrule", "path", "image"
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass
class PageData:
    glyphs: list = field(default_factory=list)
    shapes: list = field(default_factory=list)


def _font_name(tp, i, buf, flags):
    n = R.FPDFText_GetFontInfo(tp, i, buf, len(buf), ctypes.byref(flags))
    if n <= 0:
        return ""
    return buf.raw[: max(0, n - 1)].decode("utf-8", "replace")


def page_data(pdf, page_index):
    page = pdf[page_index]
    tp = page.get_textpage()
    raw = tp.raw
    n = R.FPDFText_CountChars(raw)
    buf = ctypes.create_string_buffer(512)
    flags = ctypes.c_int()
    ox, oy = ctypes.c_double(), ctypes.c_double()
    l, r, b, t = ctypes.c_double(), ctypes.c_double(), ctypes.c_double(), ctypes.c_double()
    pd = PageData()
    for i in range(n):
        u = R.FPDFText_GetUnicode(raw, i)
        if R.FPDFText_IsGenerated(raw, i) == 1:
            continue
        if not R.FPDFText_GetCharBox(raw, i, ctypes.byref(l), ctypes.byref(r), ctypes.byref(b), ctypes.byref(t)):
            continue
        if u in (0x0D, 0x0A):
            from mathmap import font_role as _fr
            if _fr(_font_name(raw, i, buf, flags))[0] != "ex" or r.value - l.value < 0.5 or t.value - b.value < 1.0:
                continue
        R.FPDFText_GetCharOrigin(raw, i, ctypes.byref(ox), ctypes.byref(oy))
        size = R.FPDFText_GetFontSize(raw, i)
        if size < 2.0:
            rect = R.FS_RECTF()
            if R.FPDFText_GetLooseCharBox(raw, i, ctypes.byref(rect)):
                size = max(size, abs(rect.top - rect.bottom))
        pd.glyphs.append(Glyph(u, _font_name(raw, i, buf, flags), float(size), l.value, b.value, r.value, t.value,
                               ox.value, oy.value, int(R.FPDFText_GetFontWeight(raw, i))))
    from mathmap import font_role
    raw_fonts = {g.font for g in pd.glyphs if font_role(g.font)[0] == "ex" and (g.u < 0x20 or (g.u < 0x80 and chr(g.u).isalnum()))}
    keep = []
    for g in pd.glyphs:
        ex = font_role(g.font)[0] == "ex"
        if g.u in (0x20, 0xA0) and not (ex and g.font in raw_fonts and g.x1 - g.x0 > 0.5):
            continue
        g.raw = g.font in raw_fonts
        keep.append(g)
    merged = []
    for g in keep:
        if merged and 0xDC00 <= g.u <= 0xDFFF and 0xD800 <= merged[-1].u <= 0xDBFF:
            h = merged[-1]
            h.u = 0x10000 + ((h.u - 0xD800) << 10) + (g.u - 0xDC00)
            h.x0, h.y0, h.x1, h.y1 = min(h.x0, g.x0), min(h.y0, g.y0), max(h.x1, g.x1), max(h.y1, g.y1)
            continue
        merged.append(g)
    pd.glyphs = merged
    for obj in page.get_objects(max_depth=4):
        typ = obj.type
        if typ not in (R.FPDF_PAGEOBJ_PATH, R.FPDF_PAGEOBJ_IMAGE, R.FPDF_PAGEOBJ_SHADING):
            continue
        bl, bb, br, bt = ctypes.c_float(), ctypes.c_float(), ctypes.c_float(), ctypes.c_float()
        if not R.FPDFPageObj_GetBounds(obj.raw, ctypes.byref(bl), ctypes.byref(bb), ctypes.byref(br), ctypes.byref(bt)):
            continue
        x0, y0, x1, y1 = bl.value, bb.value, br.value, bt.value
        w, h = x1 - x0, y1 - y0
        nested = (getattr(obj, "level", 0) or 0) >= 1
        thin_h = h <= 1.6 and w >= max(1.0, 3.0 * h)
        thin_v = w <= 1.6 and h >= max(1.0, 3.0 * w)
        if nested and not (typ == R.FPDF_PAGEOBJ_PATH and (thin_h or thin_v)):
            continue  # drawings inside form XObjects (figures) are not formula strokes
        if typ == R.FPDF_PAGEOBJ_IMAGE:
            pd.shapes.append(Shape("hrule" if thin_h and w >= 2.0 else "image", x0, y0, x1, y1))
        elif typ == R.FPDF_PAGEOBJ_SHADING:
            pd.shapes.append(Shape("path", x0, y0, x1, y1))
        elif thin_h:
            pd.shapes.append(Shape("hrule", x0, y0, x1, y1))
        elif thin_v:
            pd.shapes.append(Shape("vrule", x0, y0, x1, y1))
        else:
            pd.shapes.append(Shape("path", x0, y0, x1, y1))
    tp.close()
    page.close()
    return pd


def select(pd, bbox, pad=0.6, display=False):
    x0, y0, x1, y1 = bbox
    X0, Y0, X1, Y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    gs = [g for g in pd.glyphs if X0 <= (g.x0 + g.x1) / 2 <= X1 and Y0 <= (g.y0 + g.y1) / 2 <= Y1]
    ss = [s for s in pd.shapes if X0 <= (s.x0 + s.x1) / 2 <= X1 and Y0 <= (s.y0 + s.y1) / 2 <= Y1
          and s.x0 >= X0 - 3.0 and s.x1 <= X1 + 3.0]
    if display and gs:
        last = max(gs, key=lambda g: g.x1)
        cands = [g for g in pd.glyphs if chr(g.u) in ".,;" and g.x0 >= X1 - 1.0 and g.x0 - last.x1 <= 0.6 * last.size
                 and Y0 <= (g.y0 + g.y1) / 2 <= Y1 and g not in gs]
        if cands:
            gs = gs + [min(cands, key=lambda g: g.x0)]
    return gs, ss


class PdfCache:
    def __init__(self, maxdocs=4):
        self.docs = {}
        self.pages = {}
        self.maxdocs = maxdocs

    def get(self, path, page_index):
        key = (path, page_index)
        if key not in self.pages:
            if path not in self.docs:
                if len(self.docs) >= self.maxdocs:
                    old = next(iter(self.docs))
                    self.docs.pop(old).close()
                    self.pages = {k: v for k, v in self.pages.items() if k[0] != old}
                self.docs[path] = pdfium.PdfDocument(path)
            self.pages[key] = page_data(self.docs[path], page_index)
        return self.pages[key]

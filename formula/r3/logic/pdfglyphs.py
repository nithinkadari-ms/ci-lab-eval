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
        if u in (0x20, 0x0D, 0x0A, 0xA0) or R.FPDFText_IsGenerated(raw, i) == 1:
            continue
        if not R.FPDFText_GetCharBox(raw, i, ctypes.byref(l), ctypes.byref(r), ctypes.byref(b), ctypes.byref(t)):
            continue
        R.FPDFText_GetCharOrigin(raw, i, ctypes.byref(ox), ctypes.byref(oy))
        size = R.FPDFText_GetFontSize(raw, i)
        pd.glyphs.append(Glyph(u, _font_name(raw, i, buf, flags), float(size), l.value, b.value, r.value, t.value,
                               ox.value, oy.value, int(R.FPDFText_GetFontWeight(raw, i))))
    for obj in page.get_objects(max_depth=4):
        typ = obj.type
        if typ not in (R.FPDF_PAGEOBJ_PATH, R.FPDF_PAGEOBJ_IMAGE, R.FPDF_PAGEOBJ_SHADING):
            continue
        try:
            x0, y0, x1, y1 = obj.get_pos()
        except Exception:
            continue
        w, h = x1 - x0, y1 - y0
        if typ == R.FPDF_PAGEOBJ_IMAGE:
            pd.shapes.append(Shape("image", x0, y0, x1, y1))
        elif typ == R.FPDF_PAGEOBJ_SHADING:
            pd.shapes.append(Shape("path", x0, y0, x1, y1))
        elif h <= 1.6 and w >= 1.0:
            pd.shapes.append(Shape("hrule", x0, y0, x1, y1))
        elif w <= 1.6 and h >= 1.0:
            pd.shapes.append(Shape("vrule", x0, y0, x1, y1))
        else:
            pd.shapes.append(Shape("path", x0, y0, x1, y1))
    tp.close()
    page.close()
    return pd


def select(pd, bbox, pad=0.6):
    x0, y0, x1, y1 = bbox
    X0, Y0, X1, Y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    gs = [g for g in pd.glyphs if X0 <= (g.x0 + g.x1) / 2 <= X1 and Y0 <= (g.y0 + g.y1) / 2 <= Y1]
    ss = [s for s in pd.shapes if X0 <= (s.x0 + s.x1) / 2 <= X1 and Y0 <= (s.y0 + s.y1) / 2 <= Y1]
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

import ctypes
import math

import pypdfium2 as pdfium
import pypdfium2.raw as C

TEXT, PATH, IMAGE, SHADING, FORM = 1, 2, 3, 4, 5


def open_pdf(path):
    return pdfium.PdfDocument(str(path))


class Geo:
    def __init__(self, page):
        l, b, r, t = page.get_cropbox()
        self.l, self.b, self.r, self.t = l, b, r, t
        self.w, self.h = r - l, t - b
        self.rot = page.get_rotation()

    def box(self, l, b, r, t):
        return [l - self.l, self.t - t, r - self.l, self.t - b]


def render(page, scale=2.0, annots=True):
    return page.render(scale=scale, draw_annots=annots, may_draw_forms=False).to_pil().convert("RGB")


def _rgba(fn, *a):
    r, g, b, al = ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint()
    ok = fn(*a, ctypes.byref(r), ctypes.byref(g), ctypes.byref(b), ctypes.byref(al))
    return (r.value, g.value, b.value, al.value) if ok else None


def _fontinfo(tp, i):
    flags = ctypes.c_int()
    n = C.FPDFText_GetFontInfo(tp, i, None, 0, ctypes.byref(flags))
    if n <= 0:
        return "", 0
    buf = ctypes.create_string_buffer(n)
    C.FPDFText_GetFontInfo(tp, i, buf, n, ctypes.byref(flags))
    return buf.value.decode("utf-8", "replace"), flags.value


def chars(page, tp=None, geo=None, style=True):
    tp = tp or page.get_textpage()
    geo = geo or Geo(page)
    raw = tp.raw
    out = []
    fcache = {}
    for i in range(tp.count_chars()):
        u = C.FPDFText_GetUnicode(raw, i)
        try:
            c = chr(u)
        except (ValueError, OverflowError):
            c = "�"
        gen = C.FPDFText_IsGenerated(raw, i) == 1
        rec = dict(i=i, c=c, gen=gen)
        if not gen and c not in "\r\n":
            try:
                l, b, r, t = tp.get_charbox(i)
            except Exception:
                l = b = r = t = 0.0
            rec["box"] = geo.box(l, b, r, t)
            if style:
                rec["size"] = C.FPDFText_GetFontSize(raw, i)
                rec["weight"] = C.FPDFText_GetFontWeight(raw, i)
                fi = _fontinfo(raw, i)
                rec["font"] = fcache.setdefault(fi, fi)[0]
                rec["fflags"] = fi[1]
                rec["rm"] = int(C.FPDFText_GetTextRenderMode(raw, i))
                rec["err"] = C.FPDFText_HasUnicodeMapError(raw, i) == 1
                rec["fill"] = _rgba(C.FPDFText_GetFillColor, raw, i)
                rec["angle"] = C.FPDFText_GetCharAngle(raw, i)
        out.append(rec)
    return out


def words(chs, gap=0.45):
    ws = []
    cur = []

    def flush():
        if cur:
            bx = [min(c["box"][0] for c in cur), min(c["box"][1] for c in cur),
                  max(c["box"][2] for c in cur), max(c["box"][3] for c in cur)]
            fonts = {}
            for c in cur:
                fonts[c.get("font", "")] = fonts.get(c.get("font", ""), 0) + 1
            ws.append(dict(text="".join(c["c"] for c in cur), box=bx, font=max(fonts, key=fonts.get),
                           size=sorted(c.get("size", 0) for c in cur)[len(cur) // 2],
                           rm=max((c.get("rm", 0) for c in cur), key=[c.get("rm", 0) for c in cur].count),
                           err=any(c.get("err") for c in cur), chars=list(cur)))
            cur.clear()

    for c in chs:
        if c["gen"] or c["c"].isspace() or "box" not in c:
            flush()
            continue
        if cur:
            p = cur[-1]
            h = max(1.0, p["box"][3] - p["box"][1], c["box"][3] - c["box"][1])
            dc = abs((p["box"][1] + p["box"][3]) - (c["box"][1] + c["box"][3])) / 2
            if c["box"][0] - p["box"][2] > gap * h or dc > 0.6 * h or c["box"][0] < p["box"][0] - 0.5 * h:
                flush()
        cur.append(c)
    flush()
    return ws


def lines(ws, ytol=0.5):
    ls = []
    for w in ws:
        h = max(1.0, w["box"][3] - w["box"][1])
        placed = False
        if ls:
            L = ls[-1]
            lb = L["box"]
            vo = min(lb[3], w["box"][3]) - max(lb[1], w["box"][1])
            if vo > ytol * min(h, lb[3] - lb[1]) and w["box"][0] >= L["words"][-1]["box"][0] - 1:
                L["words"].append(w)
                L["box"] = [min(lb[0], w["box"][0]), min(lb[1], w["box"][1]), max(lb[2], w["box"][2]), max(lb[3], w["box"][3])]
                placed = True
        if not placed:
            ls.append(dict(words=[w], box=list(w["box"])))
    for L in ls:
        L["text"] = " ".join(w["text"] for w in L["words"])
    return ls


def page_words(page, style=True):
    geo = Geo(page)
    tp = page.get_textpage()
    chs = chars(page, tp, geo, style)
    return geo, chs, words(chs)


def objects(page, tp=None, geo=None, with_text=True):
    geo = geo or Geo(page)
    tp = tp or (page.get_textpage() if with_text else None)
    out = []
    stack = []
    top = -1
    for o in page.get_objects(max_depth=8):
        if o.level == 0:
            top += 1
        while stack and stack[-1][0] >= o.level:
            stack.pop()
        try:
            l, b, r, t = o.get_pos()
        except Exception:
            continue
        if stack:
            m = stack[-1][1]
            pts = [m.on_point(x, y) for x, y in ((l, b), (l, t), (r, b), (r, t))]
            l, r = min(p[0] for p in pts), max(p[0] for p in pts)
            b, t = min(p[1] for p in pts), max(p[1] for p in pts)
        rec = dict(type=o.type, box=geo.box(l, b, r, t), level=o.level, pdf_box=(l, b, r, t), top=top if o.level == 0 else None)
        fill = _rgba(C.FPDFPageObj_GetFillColor, o.raw)
        rec["fill"] = fill
        rec["stroke"] = _rgba(C.FPDFPageObj_GetStrokeColor, o.raw)
        if o.type == TEXT:
            rec["rm"] = int(C.FPDFTextObj_GetTextRenderMode(o.raw))
            if with_text and tp is not None:
                n = C.FPDFTextObj_GetText(o.raw, tp.raw, None, 0)
                if n > 0:
                    buf = ctypes.create_string_buffer(n)
                    C.FPDFTextObj_GetText(o.raw, tp.raw, ctypes.cast(buf, ctypes.POINTER(ctypes.c_ushort)), n)
                    rec["text"] = buf.raw[:n].decode("utf-16-le", "ignore").rstrip("\x00")
                else:
                    rec["text"] = ""
            sz = ctypes.c_float()
            fs = C.FPDFTextObj_GetFontSize(o.raw, ctypes.byref(sz))
            try:
                mm = o.get_matrix()
                a, bb, c, dd = mm.a, mm.b, mm.c, mm.d
            except Exception:
                a, bb, c, dd = 1, 0, 0, 1
            rec["size"] = (sz.value if fs else 0.0) * math.hypot(c, dd)
            rec["angle"] = math.degrees(math.atan2(bb, a))
        elif o.type == PATH:
            fm, st = ctypes.c_int(), ctypes.c_int()
            C.FPDFPath_GetDrawMode(o.raw, ctypes.byref(fm), ctypes.byref(st))
            rec["fillmode"], rec["strokeon"] = fm.value, st.value
        if o.type == FORM:
            try:
                m = o.get_matrix()
                if stack:
                    m = m.multiply(stack[-1][1])
                stack.append((o.level, m))
            except Exception:
                pass
        out.append(rec)
    return out


def luma(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def cover(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    ar = (a[2] - a[0]) * (a[3] - a[1])
    return ix * iy / ar if ar > 0 else 0.0

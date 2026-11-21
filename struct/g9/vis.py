import difflib
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pikepdf

from common import dl, ocr, pdf as P

SCALE = 2.0
INK = 12
TINY_PT = 3.0
LIGHT = 232
INSTR = re.compile(r"\b(ignore|disregard|forget)\b.{0,40}\b(previous|prior|above|earlier|all)\b|\b(system prompt|you are (an?|the) (ai|assistant|model)|as an ai|assistant:|developer mode|do not (tell|reveal|mention)|instructions?:)",
                   re.I)


def _strip_ops(ops):
    out, inbt = [], False
    for ins in ops:
        op = str(getattr(ins, "operator", ""))
        if op == "BT":
            inbt = True
            continue
        if op == "ET":
            inbt = False
            continue
        if not inbt:
            out.append(ins)
    return out


def strip_text(src, dst):
    pdf = pikepdf.open(src)
    seen = set()

    def forms(res):
        xo = res.get("/XObject") if res is not None else None
        if not isinstance(xo, pikepdf.Dictionary):
            return
        for _, x in xo.items():
            if not isinstance(x, pikepdf.Stream) or x.get("/Subtype") != "/Form" or x.objgen in seen:
                continue
            seen.add(x.objgen)
            try:
                x.write(pikepdf.unparse_content_stream(_strip_ops(pikepdf.parse_content_stream(x))))
            except Exception:
                pass
            forms(x.get("/Resources"))

    for pg in pdf.pages:
        try:
            ops = pikepdf.parse_content_stream(pg)
            pg.obj.Contents = pdf.make_stream(pikepdf.unparse_content_stream(_strip_ops(ops)))
        except Exception:
            pass
        try:
            forms(pg.resources)
        except Exception:
            pass
    pdf.save(dst)


EXACT_MAX = 60


def exact_ink(path, i, top, R, box):
    d = P.open_pdf(path)
    pg = d[i]
    import pypdfium2.raw as C
    obj = C.FPDFPage_GetObject(pg.raw, top)
    if not obj or not C.FPDFPage_RemoveObject(pg.raw, obj):
        return 10 ** 9, None
    M = lum(P.render(pg, SCALE, True))
    x0, y0, x1, y1 = box
    if M.shape != R.shape:
        return 10 ** 9, None
    return int((np.abs(R[y0:y1, x0:x1] - M[y0:y1, x0:x1]) > INK).sum()), float(M[y0:y1, x0:x1].mean())


def lum(im):
    a = np.asarray(im, dtype=np.float32)
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def nonpage_text(path):
    out = []
    try:
        pdf = pikepdf.open(path)
    except Exception:
        return out
    try:
        for k, v in pdf.docinfo.items():
            out.append(("metadata", str(k), str(v)))
    except Exception:
        pass
    try:
        with pdf.open_metadata() as meta:
            for k, v in meta.items():
                out.append(("xmp", str(k), str(v)))
    except Exception:
        pass
    for i, pg in enumerate(pdf.pages):
        for a in pg.obj.get("/Annots", []) or []:
            try:
                for key in ("/Contents", "/TU", "/T", "/V"):
                    if key in a:
                        out.append(("annot", "p%d%s" % (i, key), str(a[key])))
            except Exception:
                pass
    return out


def similar(a, b):
    a = re.sub(r"\s+", "", dl.norm(a).lower())
    b = re.sub(r"\s+", "", dl.norm(b).lower())
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def check(path, tmpdir, rec=None):
    t0, c0 = time.perf_counter(), time.process_time()
    stripped = os.path.join(tmpdir, "notext.pdf")
    strip_text(path, stripped)
    doc, nt = P.open_pdf(path), P.open_pdf(stripped)
    pk = pikepdf.open(path)
    spans = []
    for i in range(len(doc)):
        pg, ng = doc[i], nt[i]
        geo = P.Geo(pg)
        tp = pg.get_textpage()
        objs = P.objects(pg, tp, geo)
        R, N = lum(P.render(pg, SCALE, True)), lum(P.render(ng, SCALE, True))
        has_annots = len(pk.pages[i].obj.get("/Annots", []) or []) > 0
        R0 = N0 = None
        if has_annots:
            R0, N0 = lum(P.render(pg, SCALE, False)), lum(P.render(ng, SCALE, False))
        Hh, Ww = R.shape
        rgb_im = None
        exact_left = [EXACT_MAX]
        for k, o in enumerate(objs):
            if o["type"] != P.TEXT:
                continue
            txt = (o.get("text") or "").strip()
            if not txt:
                continue
            b = o["box"]
            bw, bh = max(0.0, b[2] - b[0]), max(0.0, b[3] - b[1])
            ix = max(0.0, min(b[2], geo.w) - max(b[0], 0.0))
            iy = max(0.0, min(b[3], geo.h) - max(b[1], 0.0))
            inside = (ix * iy) / (bw * bh) if bw * bh > 0 else (1.0 if 0 <= b[0] <= geo.w and 0 <= b[1] <= geo.h else 0.0)
            x0, y0 = int(max(0, b[0] * SCALE - 1)), int(max(0, b[1] * SCALE - 1))
            x1, y1 = int(min(Ww, b[2] * SCALE + 1)), int(min(Hh, b[3] * SCALE + 1))
            reasons = []
            rm = o.get("rm", 0)
            eff = o.get("size") or 0.0
            if eff <= 0:
                eff = bh / 1.15
            ink, area, rr, rmean, nmean = 0, 0, 0.0, 255.0, 255.0
            if x1 > x0 and y1 > y0:
                d = np.abs(R[y0:y1, x0:x1] - N[y0:y1, x0:x1])
                ink = int((d > INK).sum())
                area = d.size
                reg = R[y0:y1, x0:x1]
                rr = float(reg.max() - reg.min())
                rmean = float(reg.mean())
                nmean = float(N[y0:y1, x0:x1].mean())
            visible = area > 0 and ink >= max(2, 0.01 * area)
            if visible and o.get("top") is not None and exact_left[0] > 0:
                others = [q for q in objs if q is not o and q["type"] == P.TEXT and (q.get("text") or "").strip() and P.cover(b, q["box"]) > 0.05]
                if others:
                    exact_left[0] -= 1
                    ink, mmean = exact_ink(path, i, o["top"], R, (x0, y0, x1, y1))
                    visible = ink >= max(2, 0.01 * area)
                    fl0 = o.get("fill")
                    if visible and fl0 and mmean is not None and abs(P.luma(fl0) - mmean) < 1.5 * INK:
                        visible = False
                        reasons.append("near_background")
            if inside < 0.5:
                reasons.append("off_crop")
            if rm in (3, 7):
                reasons.append("render_mode_%d" % rm)
            fill = o.get("fill")
            if not visible and not reasons:
                fl = P.luma(fill) if fill else 0.0
                later = [q for q in objs[k + 1:] if q["type"] in (P.PATH, P.IMAGE) and P.cover(b, q["box"]) >= 0.8]
                ink0 = 0
                if has_annots and x1 > x0 and y1 > y0:
                    ink0 = int((np.abs(R0[y0:y1, x0:x1] - N0[y0:y1, x0:x1]) > INK).sum())
                if ink0 >= max(2, 0.01 * area):
                    reasons.append("annotation_cover")
                elif fill and fill[3] < 40:
                    reasons.append("transparent")
                elif rr <= 24 and rmean <= 128:
                    reasons.append("dark_cover")
                elif later:
                    reasons.append("covered_by_image" if later[-1]["type"] == P.IMAGE else "covered_by_shape")
                elif fill and fl >= LIGHT and nmean >= LIGHT:
                    reasons.append("near_background")
                elif fill and abs(fl - nmean) < INK:
                    reasons.append("same_as_background")
                else:
                    reasons.append("not_rendered")
            if not reasons and visible and eff < TINY_PT:
                reasons.append("tiny")
            cls = "visible" if not reasons else reasons[0]
            if reasons and reasons[0] == "render_mode_3":
                imgs = [q for q in objs if q["type"] == P.IMAGE and P.cover(b, q["box"]) >= 0.8]
                if imgs:
                    cls = "ocr_layer"
                    if rec is not None:
                        if rgb_im is None:
                            rgb_im = P.render(pg, 3.0, True)
                        t, cf = rec([ocr.crop(rgb_im, 3.0, (0, 0), b)])[0]
                        sim = similar(txt, t)
                        cls = "ocr_layer_ok" if sim >= 0.5 else "ocr_layer_mismatch"
            hidden = cls not in ("visible", "ocr_layer_ok")
            spans.append(dict(page=i, text=txt, hidden=hidden, cls=cls, reasons=reasons, size=round(eff, 2), ink=ink, area=area,
                              box=[round(v, 1) for v in b]))
    nonpage = []
    for src, key, val in nonpage_text(path):
        if not val.strip():
            continue
        nonpage.append(dict(src=src, key=key, text=val[:2000], instr=bool(INSTR.search(val))))
    return dict(spans=spans, nonpage=nonpage, wall=time.perf_counter() - t0, cpu=time.process_time() - c0)


def filtered_tokens(res):
    out = []
    for s in res["spans"]:
        if not s["hidden"]:
            out += dl.tokens(s["text"])
    return out


def hidden_tokens(res, nonpage=True):
    out = []
    for s in res["spans"]:
        if s["hidden"]:
            out += dl.tokens(s["text"])
    if nonpage:
        for s in res["nonpage"]:
            out += dl.tokens(s["text"])
    return out


def all_tokens(res, nonpage=True):
    out = []
    for s in res["spans"]:
        out += dl.tokens(s["text"])
    if nonpage:
        for s in res["nonpage"]:
            out += dl.tokens(s["text"])
    return out

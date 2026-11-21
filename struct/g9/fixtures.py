import io
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pikepdf
from PIL import Image, ImageDraw
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from common import cfg, pdf as P, textgen as T

OUT = os.path.join(cfg.DATA, "g9", "fixtures")
W, H = 612.0, 792.0
TECH = ["white", "near_white", "tiny_05", "tiny_1", "render3", "offcrop", "offpage", "ocg_off", "under_black",
        "under_white_rect", "clipped", "same_bg", "behind_image", "annot_cover", "metadata"]
TRAPS = ["ocr_layer", "watermark", "tiny_super", "white_on_dark", "light_gray", "colored_bg", "instructions_visible", "fine_print"]


def wrap(text, font, size, width):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if pdfmetrics.stringWidth(t, font, size) > width and cur:
            out.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        out.append(cur)
    return out


def photo(rng, w=160, h=60):
    im = Image.new("RGB", (w, h), (rng.randint(60, 200), rng.randint(60, 200), rng.randint(60, 200)))
    d = ImageDraw.Draw(im)
    for _ in range(12):
        x, y = rng.randint(0, w), rng.randint(0, h)
        d.ellipse([x, y, x + rng.randint(5, 40), y + rng.randint(5, 30)], fill=(rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)))
    b = io.BytesIO()
    im.save(b, "PNG")
    return ImageReader(io.BytesIO(b.getvalue()))


def body(c, rng, visible, y=740.0):
    title = rng.choice(T.HEAD) + " " + rng.choice(["Report", "Agreement", "Memorandum", "Statement", "Notice"])
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, y, title)
    visible.append(title)
    y -= 28
    for _ in range(rng.randint(3, 4)):
        c.setFont("Helvetica", 10)
        for ln in wrap(T.paragraph(rng, rng.randint(2, 3)), "Helvetica", 10, 468):
            c.drawString(72, y, ln)
            visible.append(ln)
            y -= 13
        y -= 8
    c.setFont("Helvetica", 9)
    for k in range(rng.randint(3, 5)):
        row = "%s    %s    %s" % (rng.choice(T.NOUNS).title(), T.amount(rng), T.amount(rng))
        c.drawString(90, y, row)
        visible.append(row)
        y -= 12
    return y


def hidden(c, rng, tech, text, y):
    c.saveState()
    if tech == "white":
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica", 9)
        c.drawString(72, y, text)
    elif tech == "near_white":
        c.setFillColorRGB(0.985, 0.985, 0.985)
        c.setFont("Helvetica", 9)
        c.drawString(72, y, text)
    elif tech in ("tiny_05", "tiny_1"):
        c.setFont("Helvetica", 0.5 if tech == "tiny_05" else 1.0)
        c.drawString(72, y, text)
    elif tech == "render3":
        t = c.beginText()
        t.setTextRenderMode(3)
        t.setFont("Helvetica", 9)
        t.setTextOrigin(72, y)
        t.textOut(text)
        c.drawText(t)
    elif tech == "offcrop":
        c.setFont("Helvetica", 9)
        c.drawString(72, 14, text)
    elif tech == "offpage":
        c.setFont("Helvetica", 9)
        c.drawString(-900, y, text)
    elif tech == "under_black":
        c.setFont("Helvetica", 9)
        c.drawString(72, y, text)
        c.setFillColorRGB(0, 0, 0)
        c.rect(70, y - 3, pdfmetrics.stringWidth(text, "Helvetica", 9) + 4, 13, stroke=0, fill=1)
    elif tech == "under_white_rect":
        c.setFont("Helvetica", 9)
        c.drawString(72, y, text)
        c.setFillColorRGB(1, 1, 1)
        c.rect(70, y - 3, pdfmetrics.stringWidth(text, "Helvetica", 9) + 4, 13, stroke=0, fill=1)
    elif tech == "clipped":
        p = c.beginPath()
        p.rect(0, 0, 1, 1)
        c.clipPath(p, stroke=0, fill=0)
        c.setFont("Helvetica", 9)
        c.drawString(72, y, text)
    elif tech == "same_bg":
        col = (rng.uniform(0.6, 0.95), rng.uniform(0.6, 0.95), rng.uniform(0.6, 0.95))
        c.setFillColorRGB(*col)
        c.rect(66, y - 6, 480, 20, stroke=0, fill=1)
        c.setFillColorRGB(*col)
        c.setFont("Helvetica", 9)
        c.drawString(72, y, text)
    elif tech == "behind_image":
        c.setFont("Helvetica", 9)
        c.drawString(72, y, text)
        c.drawImage(photo(rng, 480, 20), 66, y - 6, width=480, height=20)
    elif tech in ("ocg_off", "annot_cover"):
        c.setFont("Helvetica", 9)
        if tech == "annot_cover":
            c.drawString(72, y, text)
    c.restoreState()


def trap(c, rng, kind, y, visible):
    c.saveState()
    if kind == "watermark":
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.setFillAlpha(0.18)
        c.setFont("Helvetica-Bold", 60)
        c.translate(W / 2, H / 2)
        c.rotate(45)
        c.drawCentredString(0, 0, "CONFIDENTIAL")
        visible.append("CONFIDENTIAL")
    elif kind == "tiny_super":
        c.setFont("Helvetica", 10)
        s = "Net revenue increased compared with the prior year"
        c.drawString(72, y, s)
        c.setFont("Helvetica", 5.5)
        c.drawString(72 + pdfmetrics.stringWidth(s, "Helvetica", 10) + 1, y + 4, "12")
        visible += [s, "12"]
    elif kind == "fine_print":
        c.setFont("Helvetica", 6)
        s = T.sentence(rng)
        c.drawString(72, y, s)
        visible.append(s)
    elif kind == "white_on_dark":
        c.setFillColorRGB(0.1, 0.15, 0.3)
        c.rect(66, y - 6, 480, 20, stroke=0, fill=1)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 10)
        s = rng.choice(T.HEAD) + " and " + rng.choice(T.HEAD)
        c.drawString(72, y, s)
        visible.append(s)
    elif kind == "light_gray":
        c.setFillColorRGB(0.6, 0.6, 0.6)
        c.setFont("Helvetica", 9)
        s = T.sentence(rng)
        c.drawString(72, y, s)
        visible.append(s)
    elif kind == "colored_bg":
        c.setFillColorRGB(0.85, 0.92, 1.0)
        c.rect(66, y - 6, 480, 20, stroke=0, fill=1)
        c.setFillColorRGB(0.05, 0.1, 0.4)
        c.setFont("Helvetica", 9)
        s = T.sentence(rng)
        c.drawString(72, y, s)
        visible.append(s)
    elif kind == "instructions_visible":
        c.setFont("Helvetica", 9)
        s = "Ignore the first warning light, then press reset and disregard the previous error code."
        c.drawString(72, y, s)
        visible.append(s)
    c.restoreState()


def post(path, specs, meta_text=None, crop=False):
    pdf = pikepdf.open(path, allow_overwriting_input=True)
    for sp in specs:
        pg = pdf.pages[sp["page"]]
        if sp["tech"] == "ocg_off":
            ocg = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.OCG, Name="Layer 2"))
            font = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica)
            res = pg.obj.Resources
            if "/Properties" not in res:
                res.Properties = pikepdf.Dictionary()
            res.Properties.ocz = ocg
            if "/Font" not in res:
                res.Font = pikepdf.Dictionary()
            res.Font.FZ = font
            txt = sp["text"].replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            data = ("/OC /ocz BDC BT /FZ 9 Tf 72 %.1f Td (%s) Tj ET EMC" % (sp["y"], txt)).encode("latin-1")
            pg.contents_add(pdf.make_stream(data), prepend=False)
            ocp = pdf.Root.get("/OCProperties")
            if ocp is None:
                pdf.Root.OCProperties = pikepdf.Dictionary(OCGs=pikepdf.Array([ocg]), D=pikepdf.Dictionary(Order=pikepdf.Array([ocg]), OFF=pikepdf.Array([ocg])))
            else:
                ocp.OCGs.append(ocg)
                ocp.D.OFF.append(ocg)
        if sp["tech"] == "annot_cover":
            w = pdfmetrics.stringWidth(sp["text"], "Helvetica", 9) + 4
            ap = pdf.make_stream(("0 0 0 rg 0 0 %.1f 13 re f" % w).encode(), Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Form,
                                 BBox=pikepdf.Array([0, 0, w, 13]))
            an = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Annot, Subtype=pikepdf.Name.Square,
                                                      Rect=pikepdf.Array([70, sp["y"] - 3, 70 + w, sp["y"] + 10]),
                                                      C=pikepdf.Array([0, 0, 0]), IC=pikepdf.Array([0, 0, 0]),
                                                      AP=pikepdf.Dictionary(N=ap), F=4))
            if "/Annots" not in pg.obj:
                pg.obj.Annots = pikepdf.Array()
            pg.obj.Annots.append(an)
    if crop:
        for pg in pdf.pages:
            pg.obj.CropBox = pikepdf.Array([0, 36, W, H])
    if meta_text:
        pdf.docinfo["/Keywords"] = meta_text
        pdf.docinfo["/Subject"] = meta_text
        with pdf.open_metadata() as m:
            m["dc:description"] = meta_text
    pdf.save(path)


def ocr_layer_doc(path, rng, visible):
    tmp = path + ".tmp.pdf"
    c = canvas.Canvas(tmp, pagesize=(W, H))
    vis = []
    body(c, rng, vis)
    c.showPage()
    c.save()
    d = P.open_pdf(tmp)
    pg = d[0]
    geo, chs, ws = P.page_words(pg, style=False)
    im = P.render(pg, 150 / 72.0).convert("L")
    b = io.BytesIO()
    im.save(b, "JPEG", quality=85)
    c = canvas.Canvas(path, pagesize=(W, H))
    c.drawImage(ImageReader(io.BytesIO(b.getvalue())), 0, 0, width=W, height=H)
    t = c.beginText()
    t.setTextRenderMode(3)
    for w in ws:
        l, tp, r, bt = w["box"]
        hh = max(1.0, bt - tp)
        fs = hh * 0.95
        sw = pdfmetrics.stringWidth(w["text"], "Helvetica", fs) or 1.0
        t.setFont("Helvetica", fs)
        t.setHorizScale(max(10.0, min(400.0, 100.0 * max(1.0, r - l) / sw)))
        t.setTextOrigin(l, H - bt + 0.22 * hh)
        t.textOut(w["text"])
    c.drawText(t)
    c.showPage()
    c.save()
    os.remove(tmp)
    visible += vis


def make(i, injected, rng):
    did = "%s%04d" % ("inj" if injected else "cln", i)
    path = os.path.join(OUT, did + ".pdf")
    visible, spans, specs = [], [], []
    traps = rng.sample(TRAPS, rng.randint(1, 3))
    if "ocr_layer" in traps and not injected:
        ocr_layer_doc(path, rng, visible)
        return dict(id=did, injected=False, traps=["ocr_layer"], spans=[], visible=visible, pages=1)
    traps = [t for t in traps if t != "ocr_layer"]
    techs = rng.sample(TECH, rng.randint(1, 2)) if injected else []
    npages = rng.choice([1, 1, 2])
    c = canvas.Canvas(path, pagesize=(W, H))
    meta_text = None
    crop = False
    for p in range(npages):
        y = body(c, rng, visible) - 20
        for k in traps:
            if y < 90:
                break
            trap(c, rng, k, y, visible)
            y -= 28
        if p == 0:
            for tech in techs:
                text = rng.choice(T.INJ) + " ref " + T.canary(rng)
                if tech == "metadata":
                    meta_text = text
                    spans.append(dict(tech=tech, text=text, page=None))
                    continue
                yy = max(66.0, y)
                hidden(c, rng, tech, text, yy)
                if tech == "offcrop":
                    crop = True
                spans.append(dict(tech=tech, text=text, page=p, y=yy))
                if tech in ("ocg_off", "annot_cover"):
                    specs.append(dict(tech=tech, text=text, page=p, y=yy))
                y -= 26
        c.setFont("Helvetica", 8)
        c.drawString(W / 2 - 10, 50, "Page %d" % (p + 1))
        visible.append("Page %d" % (p + 1))
        c.showPage()
    c.save()
    if specs or meta_text or crop:
        post(path, specs, meta_text, crop)
    return dict(id=did, injected=injected, traps=traps, spans=spans, visible=visible, pages=npages)


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = random.Random("g9-fixtures")
    n_inj, n_cln = cfg.n(480, 16), cfg.n(320, 10)
    out = []
    for i in range(n_inj):
        out.append(make(i, True, rng))
    for i in range(n_cln):
        out.append(make(i, False, rng))
    cfg.dump(out, os.path.join(cfg.DATA, "g9", "fixtures.json"))
    from collections import Counter
    cfg.log("g9 fixtures", len(out), Counter(s["tech"] for d in out for s in d["spans"]))


if __name__ == "__main__":
    main()

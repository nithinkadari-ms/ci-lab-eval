import io
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pikepdf
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from common import cfg, textgen as T

OUT = os.path.join(cfg.DATA, "g12", "fixtures")
W, H = 612.0, 792.0
WM = ["none", "none", "diag_text", "horiz_text", "annot", "image"]
LABELS = ["roman_front", "offset", "appendix", "printed_only_roman", "mismatch", "plain"]
WMTEXT = ["DRAFT", "CONFIDENTIAL", "SAMPLE", "INTERNAL USE ONLY", "COPY", "NOT FOR DISTRIBUTION"]


def roman(n, upper=False):
    vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    s = ""
    for v, r in vals:
        while n >= v:
            s += r
            n -= v
    return s.upper() if upper else s


def wm_png(text, rng):
    im = Image.new("RGBA", (900, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
    except OSError:
        f = ImageFont.load_default()
    d.text((20, 80), text[:10], fill=(200, 30, 30, 70), font=f)
    b = io.BytesIO()
    im.save(b, "PNG")
    return ImageReader(io.BytesIO(b.getvalue()))


def logo(rng):
    im = Image.new("RGB", (120, 40), (20, 60, 140))
    d = ImageDraw.Draw(im)
    d.rectangle([10, 10, 50, 30], fill=(240, 200, 40))
    b = io.BytesIO()
    im.save(b, "PNG")
    return ImageReader(io.BytesIO(b.getvalue()))


def scheme(kind, n, rng):
    printed, pl = [], None
    if kind == "roman_front":
        f = rng.randint(2, 3)
        printed = [roman(i + 1) for i in range(f)] + [str(i + 1) for i in range(n - f)]
        pl = [(0, "r", "", 1), (f, "D", "", 1)]
    elif kind == "offset":
        s = rng.randint(5, 40)
        printed = [str(s + i) for i in range(n)]
        pl = [(0, "D", "", s)]
    elif kind == "appendix":
        a = max(1, n - rng.randint(1, 2))
        printed = [str(i + 1) for i in range(a)] + ["A-%d" % (i + 1) for i in range(n - a)]
        pl = [(0, "D", "", 1), (a, "D", "A-", 1)]
    elif kind == "printed_only_roman":
        f = rng.randint(1, 2)
        printed = [roman(i + 1) for i in range(f)] + [str(i + 1) for i in range(n - f)]
    elif kind == "mismatch":
        s = rng.randint(3, 20)
        printed = [str(s + i) for i in range(n)]
        pl = [(0, "D", "", 1)]
    else:
        printed = [str(i + 1) for i in range(n)]
    return printed, pl


def make(i, rng):
    did = "wr%04d" % i
    path = os.path.join(OUT, did + ".pdf")
    n = rng.randint(3, 7)
    wm = rng.choice(WM)
    wtext = rng.choice(WMTEXT)
    lab = rng.choice(LABELS)
    printed, pl = scheme(lab, n, rng)
    fmt = rng.choice(["{}", "Page {}", "- {} -"])
    header = rng.random() < 0.6
    use_logo = rng.random() < 0.4
    reds, negs, annots = [], [], []
    c = canvas.Canvas(path, pagesize=(W, H))
    wm_img = wm_png(wtext, rng) if wm == "image" else None
    logo_img = logo(rng) if use_logo else None
    for p in range(n):
        if header:
            c.setFont("Helvetica", 8)
            c.drawString(72, H - 40, "Annual Compliance Review 2024")
        if logo_img:
            c.drawImage(logo_img, W - 160, H - 60, width=90, height=30)
        y = H - 80
        c.setFont("Helvetica-Bold", 13)
        c.drawString(72, y, rng.choice(T.HEAD))
        y -= 22
        c.setFont("Helvetica", 10)
        for _ in range(rng.randint(5, 9)):
            line = T.words(rng, 12)
            c.drawString(72, y, line)
            y -= 14
            if rng.random() < 0.18 and y > 140:
                kind = rng.choice(["applied", "unapplied", "fake", "neg_header", "neg_rule", "neg_photo", "neg_bullet"])
                y -= 6
                if kind == "applied":
                    w = rng.randint(60, 260)
                    c.setFillColorRGB(0, 0, 0)
                    c.rect(72, y - 3, w, 13, stroke=0, fill=1)
                    reds.append(dict(page=p, type="applied", box=[72, H - (y + 10), 72 + w, H - (y - 3)]))
                elif kind in ("unapplied", "fake"):
                    s = "Account %s holder %s" % (T.amount(rng), T.canary(rng))
                    c.setFillColorRGB(0, 0, 0)
                    c.drawString(72, y, s)
                    w = pdfmetrics.stringWidth(s, "Helvetica", 10) + 4
                    box = [70, H - (y + 10), 70 + w, H - (y - 3)]
                    if kind == "fake":
                        c.rect(70, y - 3, w, 13, stroke=0, fill=1)
                        reds.append(dict(page=p, type="unsafe_cover", box=box, text=s))
                    else:
                        annots.append(dict(page=p, rect=[70, y - 3, 70 + w, y + 10]))
                        reds.append(dict(page=p, type="unapplied_annot", box=box, text=s))
                elif kind == "neg_header":
                    c.setFillColorRGB(0.05, 0.05, 0.05)
                    c.rect(66, y - 5, 480, 17, stroke=0, fill=1)
                    c.setFillColorRGB(1, 1, 1)
                    c.setFont("Helvetica-Bold", 10)
                    c.drawString(72, y, "Item        Quantity        Amount")
                    c.setFont("Helvetica", 10)
                    negs.append(dict(page=p, type="dark_header", box=[66, H - (y + 12), 546, H - (y - 5)]))
                elif kind == "neg_rule":
                    c.setFillColorRGB(0, 0, 0)
                    c.rect(72, y + 2, 468, 1.5, stroke=0, fill=1)
                    negs.append(dict(page=p, type="rule"))
                elif kind == "neg_photo":
                    im = Image.new("RGB", (200, 60), (15, 15, 20))
                    b = io.BytesIO()
                    im.save(b, "PNG")
                    c.drawImage(ImageReader(io.BytesIO(b.getvalue())), 72, y - 40, width=200, height=50)
                    y -= 45
                    negs.append(dict(page=p, type="dark_photo"))
                else:
                    c.setFillColorRGB(0, 0, 0)
                    c.rect(74, y, 5, 5, stroke=0, fill=1)
                    c.drawString(84, y, T.words(rng, 6))
                    negs.append(dict(page=p, type="bullet"))
                c.setFillColorRGB(0, 0, 0)
                c.setFont("Helvetica", 10)
                y -= 16
        if rng.random() < 0.3:
            c.saveState()
            c.translate(60, 300)
            c.rotate(90)
            c.setFont("Helvetica", 9)
            c.drawString(0, 0, "Revenue by quarter (USD m)")
            c.restoreState()
        if wm == "diag_text":
            c.saveState()
            c.setFillColorRGB(0.6, 0.6, 0.6)
            c.setFillAlpha(rng.uniform(0.15, 0.35))
            c.setFont("Helvetica-Bold", 54)
            c.translate(W / 2, H / 2)
            c.rotate(rng.choice([30, 45, 55]))
            c.drawCentredString(0, 0, wtext)
            c.restoreState()
        elif wm == "horiz_text":
            c.saveState()
            c.setFillColorRGB(0.82, 0.82, 0.82)
            c.setFont("Helvetica-Bold", 40)
            c.drawCentredString(W / 2, H / 2, wtext)
            c.restoreState()
        elif wm == "image":
            c.drawImage(wm_img, 106, 300, width=400, height=133, mask="auto")
        lbl = printed[p]
        if not (p == 0 and lab in ("roman_front",) and rng.random() < 0.3):
            c.setFont("Helvetica", 9)
            c.drawCentredString(W / 2, 36, fmt.format(lbl))
        else:
            printed[p] = None
        c.showPage()
    c.save()
    pdf = pikepdf.open(path, allow_overwriting_input=True)
    if pl:
        nums = pikepdf.Array()
        for start, style, prefix, st in pl:
            d = pikepdf.Dictionary(S=pikepdf.Name("/" + style))
            if prefix:
                d.P = prefix
            if st != 1:
                d.St = st
            nums.append(start)
            nums.append(d)
        pdf.Root.PageLabels = pikepdf.Dictionary(Nums=nums)
    for a in annots:
        r = a["rect"]
        q = pikepdf.Array([r[0], r[3], r[2], r[3], r[0], r[1], r[2], r[1]])
        an = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Annot, Subtype=pikepdf.Name.Redact, Rect=pikepdf.Array(r),
                                                  QuadPoints=q, IC=pikepdf.Array([0, 0, 0])))
        pg = pdf.pages[a["page"]]
        if "/Annots" not in pg.obj:
            pg.obj.Annots = pikepdf.Array()
        pg.obj.Annots.append(an)
    if wm == "annot":
        font = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name("/Helvetica-Bold"))
        txt = wtext.replace("(", "").replace(")", "")
        ap = pdf.make_stream(("q 0.7 g BT /F1 48 Tf 10 20 Td (%s) Tj ET Q" % txt).encode("latin-1"), Type=pikepdf.Name.XObject,
                             Subtype=pikepdf.Name.Form, BBox=pikepdf.Array([0, 0, 500, 80]),
                             Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)))
        for pg in pdf.pages:
            an = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Annot, Subtype=pikepdf.Name.Watermark,
                                                      Rect=pikepdf.Array([56, 356, 556, 436]), AP=pikepdf.Dictionary(N=ap), F=4))
            if "/Annots" not in pg.obj:
                pg.obj.Annots = pikepdf.Array()
            pg.obj.Annots.append(an)
    pdf.save(path)
    return dict(id=did, pages=n, watermark=wm, wm_text=wtext if wm != "none" else None, labels=lab, printed=printed,
                pagelabels=bool(pl), redactions=reds, negatives=negs, header=header, logo=use_logo)


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = random.Random("g12-fixtures")
    out = [make(i, rng) for i in range(cfg.n(360, 12))]
    cfg.dump(out, os.path.join(cfg.DATA, "g12", "fixtures.json"))
    cfg.log("g12 fixtures", len(out))


if __name__ == "__main__":
    main()

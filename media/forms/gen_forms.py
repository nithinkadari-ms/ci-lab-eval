"""Fillable form templates (reportlab AcroForm: text fields, checkboxes, signature boxes) flattened by rendering with
pdfium (forms drawn). Gold boxes are the AcroForm widget rectangles before flattening; gold label->field pairs come
from the template. Variants per template: empty, filled (some fields left blank, checkboxes checked/unchecked,
signature strokes), filled_scan (blur, noise, 0.7 degree skew, JPEG).
usage: gen_forms.py OUTDIR N"""
import io
import json
import os
import random
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ocr"))
import data as ocrdata  # noqa: E402

LABELS = [("Full name", "name"), ("Date of birth", "date"), ("Account number", "acct"), ("Amount", "money"),
          ("Phone", "phone"), ("Employer", "name"), ("Policy No.", "ident"), ("Reference", "ident"), ("Date", "date"),
          ("City", "city"), ("Postal code", "zip"), ("Invoice No.", "ident"), ("Total due", "money"),
          ("Contact person", "name"), ("Employee ID", "ident"), ("Tax ID", "acct")]
CHECKS = ["Yes", "No", "Married", "Single", "Full time", "Part time", "Paper copy", "Email copy", "I agree",
          "New customer", "Existing customer", "Urgent"]
SCALE = 2.0


def value(kind, r):
    return {"name": f"{r.choice(ocrdata.NAMES)} {r.choice(ocrdata.STREETS)}", "date": ocrdata._date(r),
            "acct": f"{r.randint(1000, 9999)}-{r.randint(1000, 9999)}", "money": ocrdata._money(r),
            "phone": ocrdata._phone(r), "ident": ocrdata._ident(r), "city": r.choice(ocrdata.CITIES),
            "zip": str(r.randint(10000, 99999))}[kind]


def make(i, outdir):
    from reportlab.lib.colors import black, white
    from reportlab.pdfgen import canvas
    r = random.Random(9000 + i)
    W, H = 612.0, 792.0
    font = r.choice(["Helvetica", "Times-Roman"])
    fs = r.uniform(8.5, 11)
    layout = r.choice(["right", "right", "below", "grid"])
    fields = []
    y = H - 70
    specs = []
    labels = r.sample(LABELS, r.randint(6, 11))
    if r.random() < 0.4:
        labels.append(("Date", "date"))
    for lab, kind in labels:
        specs.append(("text", lab, kind))
    for _ in range(r.randint(2, 6)):
        specs.append(("check", r.choice(CHECKS), None))
    if r.random() < 0.7:
        specs.append(("sig", r.choice(["Signature", "Signature of applicant", "Authorised signature"]), None))
    r.shuffle(specs)
    variants = {}
    for var in ("empty", "filled"):
        rr = random.Random(77 + i)
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(W, H))
        c.setFont(font, fs * 1.5)
        c.drawString(50, H - 45, r.choice(["Application form", "Customer registration", "Claim form", "Order form"]))
        yy = y
        col = 0
        flds = []
        for k, (typ, lab, kind) in enumerate(specs):
            x0 = 50 if layout != "grid" or col == 0 else 320
            c.setFont(font, fs)
            text = lab + (":" if typ != "check" and rr.random() < 0.7 else "")
            lw = c.stringWidth(text, font, fs)
            fld = {"name": f"f{k}", "label": text}
            if typ == "check":
                size = fs * 1.2
                checked = var == "filled" and rr.random() < 0.5
                c.acroForm.checkbox(name=fld["name"], x=x0, y=yy - 2, size=size, checked=checked,
                                    buttonStyle=rr.choice(["check", "cross"]), borderWidth=1, borderColor=black,
                                    fillColor=white, forceBorder=True)
                c.drawString(x0 + size + 5, yy, text)
                fld.update(type="ChoiceButton", rect=[x0, yy - 2, size, size], checked=checked,
                           label_rect=[x0 + size + 5, yy - 0.22 * fs, lw, fs])
                adv = fs * 2.2
            else:
                if layout == "below":
                    lx, ly, fx, fy = x0, yy, x0, yy - fs * 2.2
                    adv = fs * 4.4
                else:
                    lx, ly, fx, fy = x0, yy, x0 + max(lw + 8, rr.uniform(110, 140)), yy - 3
                    adv = fs * 2.6
                fw = rr.uniform(140, 230) if typ == "text" else rr.uniform(160, 240)
                fh = fs * 1.6 if typ == "text" else fs * 3.0
                if typ == "sig":
                    fy -= fs * 1.4
                    adv += fs * 1.4
                c.drawString(lx, ly, text)
                v = ""
                if typ == "text" and var == "filled" and rr.random() < 0.8:
                    v = value(kind, rr)
                c.acroForm.textfield(name=fld["name"], x=fx, y=fy, width=fw, height=fh, value=v, fontName="Helvetica",
                                     fontSize=fs, borderStyle=rr.choice(["solid", "underlined"]), borderWidth=1,
                                     borderColor=black, fillColor=white, forceBorder=True)
                if typ == "sig" and var == "filled" and rr.random() < 0.85:
                    c.setLineWidth(rr.uniform(0.8, 1.5))
                    px, py = fx + 10, fy + fh * 0.35
                    p = c.beginPath()
                    p.moveTo(px, py)
                    for _ in range(rr.randint(4, 8)):
                        p.curveTo(px + rr.uniform(5, 15), py + rr.uniform(-6, 14), px + rr.uniform(10, 25),
                                  py + rr.uniform(-10, 10), px + rr.uniform(15, 30), py + rr.uniform(-3, 6))
                        px += rr.uniform(15, 30)
                    c.drawPath(p, stroke=1, fill=0)
                    v = "<signature>"
                fld.update(type="Signature" if typ == "sig" else "TextBox", rect=[fx, fy, fw, fh], value=v,
                           label_rect=[lx, ly - 0.22 * fs, lw, fs])
            flds.append(fld)
            if layout == "grid":
                col = 1 - col
                if col == 0:
                    yy -= adv
            else:
                yy -= adv
            if yy < 80:
                break
        c.showPage()
        c.save()
        variants[var] = (buf.getvalue(), flds)
    out = []
    import pypdfium2 as pdfium
    for var, (pdfb, flds) in variants.items():
        pdf = pdfium.PdfDocument(pdfb)
        pdf.init_forms()
        img = np.array(pdf[0].render(scale=SCALE, may_draw_forms=True).to_pil().convert("RGB"))
        pdf.close()

        def px(rect):
            x, y_, w, h = rect
            return [x * SCALE, (H - y_ - h) * SCALE, (x + w) * SCALE, (H - y_) * SCALE]
        gold = [dict(f, box=px(f["rect"]), label_box=px(f["label_rect"])) for f in flds]
        items = [(var, img, gold)]
        if var == "filled":
            rng = np.random.default_rng(i)
            g = cv2.GaussianBlur(img, (0, 0), 0.8).astype(np.float32) + rng.normal(0, 8, img.shape[:2])[..., None]
            g = np.clip(g, 0, 255).astype(np.uint8)
            h_, w_ = g.shape[:2]
            M = cv2.getRotationMatrix2D((w_ / 2, h_ / 2), 0.7, 1.0)
            g = cv2.warpAffine(g, M, (w_, h_), borderValue=(255, 255, 255))
            ok, enc = cv2.imencode(".jpg", g, [cv2.IMWRITE_JPEG_QUALITY, 40])
            g = cv2.cvtColor(cv2.imdecode(enc, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)

            def rot(b):
                pts = [(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])]
                q = [(M[0, 0] * x + M[0, 1] * y_ + M[0, 2], M[1, 0] * x + M[1, 1] * y_ + M[1, 2]) for x, y_ in pts]
                return [min(p[0] for p in q), min(p[1] for p in q), max(p[0] for p in q), max(p[1] for p in q)]
            items.append(("filled_scan", g, [dict(f, box=rot(f["box"]), label_box=rot(f["label_box"])) for f in gold]))
        for v, im, gd in items:
            name = f"form{i:04d}_{v}"
            cv2.imwrite(os.path.join(outdir, name + ".png"), cv2.cvtColor(im, cv2.COLOR_RGB2BGR))
            json.dump({"id": name, "template": i, "variant": v, "fields": gd}, open(os.path.join(outdir, name + ".json"), "w"))
            out.append(name)
    return out


if __name__ == "__main__":
    out, n = sys.argv[1], int(sys.argv[2])
    os.makedirs(out, exist_ok=True)
    k = 0
    for i in range(n):
        k += len(make(i, out))
    print("forms", n, "images", k)

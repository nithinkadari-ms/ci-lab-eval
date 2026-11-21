import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reportlab.pdfgen import canvas

from common import dl, ocr, pdf as P


def main():
    td = tempfile.mkdtemp()
    p = os.path.join(td, "probe.pdf")
    c = canvas.Canvas(p, pagesize=(612, 792))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 720, "1. Introduction")
    c.setFont("Helvetica", 11)
    c.drawString(72, 690, "Total amount due 1,250.00 USD on 2024-03-15 for invoice INV-20931.")
    c.drawString(72, 670, "The supplier shall deliver the revised schedule within thirty days.")
    t = c.beginText()
    t.setTextRenderMode(3)
    t.setFont("Helvetica", 11)
    t.setTextOrigin(72, 640)
    t.textOut("HIDDENCANARY invisible text")
    c.drawText(t)
    c.showPage()
    c.save()
    for kw in (dict(), dict(replace_broken_text_layer=True), dict(force_full_page_ocr=True), dict(text_layer_only=True), dict(heading_hierarchy=True)):
        doc, wall, cpu = dl.convert(p, **kw)
        its = dl.items(doc)
        print("ARM", kw, round(wall, 2), [(i["label"], i["text"][:60], i["level"], i["page"], [round(v) for v in (i["bbox"] or [])]) for i in its])
    d = P.open_pdf(p)
    pg = d[0]
    geo, chs, ws = P.page_words(pg)
    print("WORDS", [(w["text"], w["font"], round(w["size"], 1), w["rm"]) for w in ws][:20])
    objs = P.objects(pg, None, geo)
    print("OBJS", [(o["type"], o.get("text"), o.get("rm"), o.get("fill"), round(o.get("size", 0), 1)) for o in objs])
    rec = ocr.Rec()
    im = P.render(pg, 3.0)
    ls = P.lines(ws)
    res = rec([ocr.crop(im, 3.0, (0, 0), L["box"]) for L in ls])
    for L, r in zip(ls, res):
        print("OCR", repr(L["text"]), "->", r)
    print("TOC", d.get_toc and [x for x in d.get_toc()])
    print("MODELS", sorted(os.listdir(ocr.models_dir())))


if __name__ == "__main__":
    main()

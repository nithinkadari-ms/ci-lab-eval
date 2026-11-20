"""Print glyphs and page objects near a few regions (CI debugging)."""
import json, os, sys
from collections import Counter
import pypdfium2 as pdfium
import pypdfium2.raw as R
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdfglyphs import page_data, select
regions = {json.loads(l)["id"]: json.loads(l) for l in open(sys.argv[1], encoding="utf-8")}
for rid in sys.argv[2].split(","):
    r = regions[rid]
    pdf = pdfium.PdfDocument(r["pdf"])
    page = pdf[r["page_index"]]
    types = Counter()
    near = []
    x0, y0, x1, y1 = r["bbox"]
    for obj in page.get_objects(max_depth=6):
        types[obj.type] += 1
        if obj.type != R.FPDF_PAGEOBJ_TEXT:
            try:
                b = obj.get_pos()
            except Exception as e:
                b = str(e)
            if isinstance(b, tuple) and b[2] >= x0 - 5 and b[0] <= x1 + 5 and b[3] >= y0 - 5 and b[1] <= y1 + 5:
                near.append((obj.type, getattr(obj, "level", None), [round(v, 2) for v in b]))
    pd = page_data(pdf, r["page_index"])
    gs, ss = select(pd, r["bbox"])
    print("=" * 60, rid, "bbox", [round(v, 2) for v in r["bbox"]], "mediabox", r["mediabox"])
    print("object types on page", dict(types), "shapes in pd", Counter(s.kind for s in pd.shapes))
    print("non-text objects near region", near[:20])
    print("selected shapes", [(s.kind, round(s.x0, 2), round(s.y0, 2), round(s.x1, 2), round(s.y1, 2)) for s in ss])
    for g in sorted(gs, key=lambda g: g.x0)[:60]:
        print(f"  U+{g.u:04X} {chr(g.u) if g.u > 31 else '?'} {g.font[:28]:28s} size={g.size:.2f} box=({g.x0:.1f},{g.y0:.1f},{g.x1:.1f},{g.y1:.1f}) origin=({g.ox:.1f},{g.oy:.1f})")

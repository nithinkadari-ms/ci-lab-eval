"""Score formulas in PDFs (real Word with Cambria Math, or LuaLaTeX + Cambria Math on a windows runner), one shard.
Per formula: the round-3 glyph logic rebuild (formula/r3/logic, unchanged) on the formula region, the Pix2Text MFR
1.5 int8 model (decoder cap 1024) on a crop of the same region, the fonts and the share of Unicode math
alphanumerics in the region. Raw predictions are written; agg_wordpdf.py scores them.
usage: run_wordpdf.py SETNAME PDFDIR MANIFEST SHARD NSHARDS OUT.jsonl"""
import json
import os
import sys
import time
import traceback

os.environ.setdefault("MFR_MAX_NEW", "1024")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "formula", "r3", "logic"))
sys.path.insert(0, os.path.join(ROOT, "formula", "scripts"))


def region(page_words, W, H, c):
    """formula region in pdfplumber (top-left) coordinates, or None"""
    mk = [w for w in page_words if w["text"] == "EQ" + c["id"]]
    if not mk:
        return None, "marker not found"
    m = mk[0]
    if c["mode"] == "display":
        return (30.0, m["bottom"] + 1.0, W - 30.0, H - 30.0), None
    l = [w for w in page_words if w["text"] == "QQL"]
    r = [w for w in page_words if w["text"] == "QQR"]
    if not l or not r:
        return None, "inline anchors not found"
    l, r = l[0], r[0]
    lh = max(6.0, l["bottom"] - l["top"])
    if abs((l["top"] + l["bottom"]) / 2 - (r["top"] + r["bottom"]) / 2) > lh:
        return (l["x1"] + 0.3, min(l["top"], r["top"]) - 1.2 * lh, W - 30.0, max(l["bottom"], r["bottom"]) + 1.2 * lh), "wrapped"
    return (l["x1"] + 0.3, l["top"] - 1.2 * lh, r["x0"] - 0.3, l["bottom"] + 1.2 * lh), None


def main():
    setname, pdfdir, manifest, k, n, out = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
    import pdfplumber
    import pypdfium2 as pdfium
    from build import rebuild
    from mathmap import math_alnum
    from mfr import MFRFast
    from pdfglyphs import PdfCache, select
    man = json.load(open(manifest, encoding="utf-8"))
    cases = [c for i, c in enumerate(man) if i % n == k]
    model = MFRFast("p2t15_int8", threads=4)
    cache = PdfCache()
    words = {}
    pdfs = {}
    with open(out, "w", encoding="utf-8") as f:
        for c in cases:
            rec = {"set": setname, "id": c["id"], "construct": c["construct"], "mode": c["mode"]}
            try:
                path = os.path.join(pdfdir, c["doc"].replace(".docx", ".pdf"))
                if not os.path.exists(path):
                    raise FileNotFoundError(os.path.basename(path))
                key = (path, c["page"])
                if key not in words:
                    with pdfplumber.open(path) as doc:
                        pg = doc.pages[c["page"]]
                        words[key] = (pg.extract_words(), float(pg.width), float(pg.height))
                pw, W, H = words[key]
                box, note = region(pw, W, H, c)
                rec["note"] = note
                if box is None:
                    raise ValueError(note)
                bbox = (box[0], H - box[3], box[2], H - box[1])
                pd = cache.get(path, c["page"])
                gs, ss = select(pd, bbox, display=c["mode"] == "display")
                rec["n_glyphs"] = len(gs)
                rec["fonts"] = sorted({g.font.split("+")[-1] for g in gs})[:8]
                rec["math_alnum"] = sum(1 for g in gs if math_alnum(chr(g.u))) / max(1, len(gs))
                t = time.perf_counter()
                lg = rebuild(gs, ss)
                rec["logic_ms"] = (time.perf_counter() - t) * 1000
                rec["logic"], rec["conf"] = lg.get("latex") or "", float(lg.get("conf") or 0.0)
                if gs:
                    x0 = min([g.x0 for g in gs] + [s.x0 for s in ss]) - 3
                    x1 = max([g.x1 for g in gs] + [s.x1 for s in ss]) + 3
                    y0 = min([g.y0 for g in gs] + [s.y0 for s in ss]) - 3
                    y1 = max([g.y1 for g in gs] + [s.y1 for s in ss]) + 3
                    if path not in pdfs:
                        pdfs.clear()
                        pdfs[path] = pdfium.PdfDocument(path)
                    sc = 3.0
                    img = pdfs[path][c["page"]].render(scale=sc).to_pil().convert("RGB")
                    Hp = pdfs[path][c["page"]].get_height()
                    crop = img.crop((max(0, x0 * sc), max(0, (Hp - y1) * sc), min(img.width, x1 * sc),
                                     min(img.height, (Hp - y0) * sc)))
                    t = time.perf_counter()
                    txt, ntok, runaway = model(crop)
                    rec["mfr_ms"] = (time.perf_counter() - t) * 1000
                    rec["mfr"], rec["mfr_runaway"] = txt, bool(runaway)
                else:
                    rec["mfr"] = ""
            except Exception as e:  # noqa: BLE001
                rec["error"] = f"{type(e).__name__}: {e}"[:200]
                rec["tb"] = traceback.format_exc()[-400:]
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
    print("done", setname, k, n, len(cases))


if __name__ == "__main__":
    main()

"""Gap 1 runner, one shard. Only numbers are written (no transcripts), so artifacts carry no dataset text.

pages mode: FUNSD, SROIE and synthetic degraded pages
  * same-crop test: PP-OCRv6 small detector boxes (docling.rs) cropped once, read by every recognizer
  * end-to-end: detector + recognizer per engine, whole-page Tesseract, PP-OCRv6 medium det+rec, Tesseract on
    low-confidence lines (threshold grid, chosen later on the dev split), preprocessing arms
regions mode: OmniDocBench English text regions, detector on the region crop, every recognizer on its lines

usage: run_ocr.py pages|regions SHARD NSHARDS OUT.jsonl [WORKERS]
"""
import json
import os
import sys
import time
import traceback
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import data  # noqa: E402
import engines  # noqa: E402
import ppocr  # noqa: E402
from common import bag_f1, edits, norm_text, num_tokens, shard, word_edits  # noqa: E402

TAUS = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.98]
PADDLE = {"v6s", "v6m", "v5en"}
G = {}
# arm groups: each job runs one group so heavy arms do not stack; records are merged by id afterwards
GROUP = os.environ.get("OCR_GROUP", "all")
GROUP_ENG = {"core": ["v6s", "v5en", "crnn", "viptr"], "v6m": ["v6m"], "tess": ["v6s", "tess_fast", "tess_best"],
             "all": list(engines.CROP_ENGINES)}
REGION_ENG = {"core": ["v6s", "v5en", "crnn", "viptr"], "v6m": ["v6m"], "tess": ["tess_fast", "tess_best"],
              "all": list(engines.CROP_ENGINES)}


def has(part):
    return GROUP == "all" or GROUP == part


def init(mode="pages"):
    G["det_s"] = ppocr.Detector(engines.P["det_s"])
    G["eng"] = engines.build((GROUP_ENG if mode == "pages" else REGION_ENG)[GROUP])
    if mode == "pages" and has("v6m"):
        G["det_m"] = ppocr.Detector(engines.P["det_m"])
    if mode == "pages" and has("tess"):
        G["tess_page"] = {k: engines.Tess(k, psm_line=False) for k in ("fast", "best")}
    if mode == "pages" and has("core"):
        G["uvdoc"] = engines.UVDoc()


def serialize(items):
    """items: [(text, box)] -> one string, rows top-to-bottom (centre-y within half the median height), then x."""
    items = [it for it in items if it[0].strip()]
    if not items:
        return ""
    hs = sorted(b[3] - b[1] for _, b in items)
    tol = 0.5 * max(1.0, hs[len(hs) // 2])
    items.sort(key=lambda it: (it[1][1] + it[1][3]) / 2)
    rows, cur, cy = [], [], None
    for it in items:
        c = (it[1][1] + it[1][3]) / 2
        if cur and abs(c - cy) > tol:
            rows.append(cur)
            cur = []
        cur.append(it)
        cy = c if len(cur) == 1 else (cy * (len(cur) - 1) + c) / len(cur)
    rows.append(cur)
    return "\n".join(" ".join(t for t, _ in sorted(r, key=lambda it: it[1][0])) for r in rows)


def e2e_metrics(pred_items, gt_str, fields):
    ps = norm_text(serialize(pred_items))
    g = norm_text(gt_str)
    hit, npred, ngt, f1 = bag_f1(ps.split(), g.split())
    nh, nnp, nng, _ = bag_f1(num_tokens(ps), num_tokens(g))
    fx = sum(1 for f in fields if norm_text(f) and norm_text(f) in ps)
    return {"ed": edits(ps, g), "n": len(g), "bag_hit": hit, "bag_pred": npred, "bag_gt": ngt, "num_hit": nh,
            "num_pred": nnp, "num_gt": nng, "fld_hit": fx, "fld_n": len(fields)}


def assign(words, boxes):
    """GT words -> det box index (box containing the word centre with the largest overlap share), -1 if none."""
    out = []
    for w in words:
        x0, y0, x1, y1 = w["box"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        best, bi = 0.0, -1
        wa = max(1e-6, (x1 - x0) * (y1 - y0))
        for k, b in enumerate(boxes):
            bb = b["box"]
            if bb[0] <= cx <= bb[2] and bb[1] <= cy <= bb[3]:
                ov = max(0, min(x1, bb[2]) - max(x0, bb[0])) * max(0, min(y1, bb[3]) - max(y0, bb[1])) / wa
                if ov > best:
                    best, bi = ov, k
        out.append(bi)
    return out


def recog_all(crops):
    res, ms = {}, {}
    for n, e in G["eng"].items():
        t = time.perf_counter()
        res[n] = e(crops)
        ms[n] = (time.perf_counter() - t) * 1000
    return res, ms


def page_ocr(rgb, det="det_s", rec="v6s"):
    boxes = G[det](rgb)
    crops = [ppocr.crop(rgb, b["quad"]) for b in boxes]
    keep = [k for k, c in enumerate(crops) if c is not None]
    out = G["eng"][rec]([crops[k] for k in keep])
    items = []
    for k, (t, c) in zip(keep, out):
        if rec in PADDLE and (not t or c < ppocr.TEXT_SCORE):
            continue
        items.append((t, boxes[k]["box"]))
    return items, boxes


def do_page(p):
    t0 = time.perf_counter()
    rgb, words, fields, kind = data.load(p)
    rec = {k: p[k] for k in ("id", "group", "ds", "defect", "split")}
    rec.update(kind=kind, H=int(rgb.shape[0]), W=int(rgb.shape[1]), n_words=len(words), arm_group=GROUP)
    gt_str = serialize([(w["t"], w["box"]) for w in words])
    (boxes, ms_det) = engines.timed(G["det_s"], rgb)
    rec["ms_det_s"] = ms_det
    crops = [ppocr.crop(rgb, b["quad"]) for b in boxes]
    keep = [k for k, c in enumerate(crops) if c is not None]
    owner = assign(words, boxes)
    gt_by = {}
    for w, k in zip(words, owner):
        if k >= 0:
            gt_by.setdefault(k, []).append(w)
    rec["gt_words_unboxed"] = sum(1 for k in owner if k < 0)
    res, ms = recog_all([crops[k] for k in keep])
    rec["ms_rec"] = ms
    crop_rows = []
    for idx, k in enumerate(keep):
        ws = gt_by.get(k, [])
        gt = serialize([(w["t"], w["box"]) for w in ws])
        g = norm_text(gt)
        row = {"n": len(g), "nw": len(g.split()), "h": round(boxes[k]["box"][3] - boxes[k]["box"][1], 1)}
        gnum = num_tokens(g)
        for n in G["eng"]:
            t, c = res[n][idx]
            pt = norm_text(t)
            we, _ = word_edits(pt, g)
            pn = num_tokens(pt)
            from collections import Counter
            row[n] = [edits(pt, g), we, round(float(c), 4), sum((Counter(pn) & Counter(gnum)).values()), len(pt)]
        row["nnum"] = len(gnum)
        crop_rows.append(row)
    rec["crops"] = crop_rows
    e2e = {}
    items = {n: [] for n in G["eng"]}
    for idx, k in enumerate(keep):
        for n in G["eng"]:
            t, c = res[n][idx]
            if n in PADDLE and (not t or c < ppocr.TEXT_SCORE):
                continue
            items[n].append((t, boxes[k]["box"]))
    for n in G["eng"]:
        e2e[n] = e2e_metrics(items[n], gt_str, fields)
    for tau in (TAUS if has("tess") else []):
        for mode in ("rep", "rep_if_higher"):
            it = []
            for idx, k in enumerate(keep):
                t6, c6 = res["v6s"][idx]
                tt, ct = res["tess_best"][idx]
                use_t = c6 < tau and (mode == "rep" or ct > c6)
                t, c = (tt, ct) if use_t else (t6, c6)
                if not use_t and (not t or c < ppocr.TEXT_SCORE):
                    continue
                it.append((t, boxes[k]["box"]))
            e2e[f"hyb_{mode}_{tau}"] = e2e_metrics(it, gt_str, fields)
    if has("v6m"):
        t = time.perf_counter()
        mitems, _ = page_ocr(rgb, "det_m", "v6m")
        e2e["v6m_det+rec"] = e2e_metrics(mitems, gt_str, fields)
        e2e["v6m_det+rec"]["ms"] = (time.perf_counter() - t) * 1000
    for kk in (("fast", "best") if has("tess") else ()):
        t = time.perf_counter()
        e2e[f"tess_{kk}_page"] = e2e_metrics([(l["text"], l["box"]) for l in G["tess_page"][kk].page_lines(rgb)],
                                             gt_str, fields)
        e2e[f"tess_{kk}_page"]["ms"] = (time.perf_counter() - t) * 1000
    dfx = engines.defects(rgb, boxes)
    gates = engines.gate(dfx)
    rec["defects"], rec["gates"] = dfx, gates
    if not has("core"):
        rec["e2e"] = e2e
        rec["ms_page"] = (time.perf_counter() - t0) * 1000
        return rec

    def arm(name, fn):
        t = time.perf_counter()
        img = fn(rgb)
        tp = (time.perf_counter() - t) * 1000
        it, _ = page_ocr(img)
        e2e[name] = e2e_metrics(it, gt_str, fields)
        e2e[name]["ms_pre"] = tp
    arm("pre_deskew", lambda im: engines.deskew(im, dfx["skew"]) if dfx["n_lines"] else im)
    arm("pre_clahe", engines.clahe)
    arm("pre_denoise", engines.denoise)
    arm("pre_uvdoc", G["uvdoc"])

    def gated(im, uv):
        if uv and gates["uvdoc"]:
            im = G["uvdoc"](im)
        elif gates["deskew"] and dfx["n_lines"]:
            im = engines.deskew(im, dfx["skew"])
        if gates["clahe"]:
            im = engines.clahe(im)
        if gates["denoise"]:
            im = engines.denoise(im)
        return im
    if any(gates[k] for k in ("deskew", "clahe", "denoise")):
        arm("pre_gated", lambda im: gated(im, False))
    else:
        e2e["pre_gated"] = dict(e2e["v6s"], ms_pre=0.0)
    if any(gates.values()):
        arm("pre_gated_uvdoc", lambda im: gated(im, True))
    else:
        e2e["pre_gated_uvdoc"] = dict(e2e["v6s"], ms_pre=0.0)
    rec["e2e"] = e2e
    rec["ms_page"] = (time.perf_counter() - t0) * 1000
    return rec


def do_region(p):
    _, img, box, text = p["src"]
    rgb, gt = data._odb_load(img, box, text)
    g = norm_text(gt)
    rec = {k: p[k] for k in ("id", "group", "ds", "defect", "source")}
    rec["n"] = len(g)
    boxes = G["det_s"](rgb, region=True)
    crops = [c for c in (ppocr.crop(rgb, b["quad"]) for b in boxes) if c is not None]
    res, ms = recog_all(crops)
    rec["ms_rec"] = ms
    rec["n_lines"] = len(crops)
    for n in G["eng"]:
        ts = [t for t, c in res[n] if t and not (n in PADDLE and c < ppocr.TEXT_SCORE)]
        pt = norm_text(" ".join(ts))
        we, nw = word_edits(pt, g)
        rec[n] = [edits(pt, g), we, nw]
    rec["arm_group"] = GROUP
    if has("tess"):
        from PIL import Image
        import pytesseract
        t = pytesseract.image_to_string(Image.fromarray(rgb), lang="eng",
                                        config=f"--tessdata-dir {engines.P['tess_best']} --oem 1 --psm 6")
        pt = norm_text(t)
        we, nw = word_edits(pt, g)
        rec["tess_best_block"] = [edits(pt, g), we, nw]
    return rec


def safe(fn):
    def w(p):
        try:
            return fn(p)
        except Exception as e:  # noqa: BLE001
            return {"id": p["id"], "group": p["group"], "ds": p["ds"], "error": f"{type(e).__name__}: {e}"[:300],
                    "tb": traceback.format_exc()[-800:]}
    return w


def _page(p):
    return safe(do_page)(p)


def _region(p):
    return safe(do_region)(p)


def done_ids(art):
    """ids already scored with every arm in an earlier run (full records written by the all-arms runner)"""
    import glob
    ids = set()
    for f in glob.glob(os.path.join(art, "**", "*.jsonl"), recursive=True):
        for line in open(f, encoding="utf-8"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if "error" not in r and r.get("arm_group", "all") == "all":
                ids.add(r["id"])
    return ids


def main():
    mode, k, n, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    workers = int(sys.argv[5]) if len(sys.argv) > 5 else 4
    if mode == "pages":
        data.sroie_extract()
    items = data.all_pages() if mode == "pages" else data.odb_regions()
    prev = os.environ.get("OCR_DONE_DIR")
    if prev:
        done = done_ids(prev)
        items = [it for it in items if it["id"] not in done]
        print("already done in the earlier run:", len(done), "to do:", len(items), flush=True)
    items = shard(items, k, n)
    fn = _page if mode == "pages" else _region
    errs = rows = 0
    with Pool(workers, initializer=init, initargs=(mode,), maxtasksperchild=30) as pool, \
            open(out, "w", encoding="utf-8") as f:
        for i, r in enumerate(pool.imap_unordered(fn, items, chunksize=1)):
            errs += "error" in r
            rows += 1
            f.write(json.dumps(r) + "\n")
            f.flush()
            if i % 10 == 0:
                print(mode, GROUP, k, i, len(items), "errors", errs, flush=True)
    print("done", mode, GROUP, k, "items", len(items), "rows", rows, "errors", errs, flush=True)
    if items and (rows == 0 or errs > 0.02 * rows):
        sys.exit(f"FAILED: {errs} errors in {rows} rows (limit 2%)")


if __name__ == "__main__":
    main()

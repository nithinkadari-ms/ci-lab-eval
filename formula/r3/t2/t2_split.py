"""Line splitting for multi-line displays: arXiv by text-layer rows (whole-width gaps, never through a fraction
bar, radical or big operator), UniMER by horizontal projection profile (whole-width blank bands, never next to a
thin ink band such as a fraction bar). Each line is recognised separately and joined with \\ in aligned."""
import json, os, sys, time
import numpy as np
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "r3", "logic"))
os.environ.setdefault("MFR_MAX_NEW", "1023")


def cuts_text_layer(it, cache):
    from pdfglyphs import select
    from build import make_items, y_rows, main_size, Ctx
    pd = cache.get(os.path.join(ROOT, "data", "arxiv", it["paper"], "paper.pdf"), it["page_index"])
    gs, ss = select(pd, it["bbox"])
    items = make_items(gs, ss, Ctx())
    if len(items) < 2:
        return []
    size = main_size(items)
    x0 = min(i.x0 for i in items)
    x1 = max(i.x1 for i in items)
    rows = y_rows(items, size, x1 - x0)
    if len(rows) < 2:
        return []
    X0, Y0, X1, Y1 = it["crop_px"]
    sc, ph = it["scale"], it["page_h"]
    ys = []
    for up, lo in zip(rows, rows[1:]):
        y = (min(i.y0 for i in up) + max(i.y1 for i in lo)) / 2
        ys.append(int(round((ph - y) * sc - Y0)))
    return ys


def cuts_profile(img):
    a = np.asarray(img.convert("L")) < 200
    h, w = a.shape
    ink = a.any(axis=1)
    runs, k = [], 0
    while k < h:
        j = k
        while j < h and ink[j] == ink[k]:
            j += 1
        runs.append((bool(ink[k]), k, j))
        k = j
    inks = [r for r in runs if r[0]]
    heights = [j - k for _, k, j in inks if j - k >= 3]
    if len(inks) < 2 or not heights:
        return []
    hmed = float(np.median(heights))
    cols = lambda k, j: a[k:j].any(axis=0)
    ys = []
    for idx, (is_ink, k, j) in enumerate(runs):
        if is_ink or idx == 0 or idx == len(runs) - 1:
            continue
        gap = j - k
        up, lo = runs[idx - 1], runs[idx + 1]
        if gap < max(3, 0.25 * hmed):
            continue
        thin = lambda r: (r[2] - r[1]) <= max(2, 0.12 * hmed)
        if thin(up) or thin(lo):
            continue
        wu, wl = cols(up[1], up[2]).sum(), cols(lo[1], lo[2]).sum()
        if wu < 0.25 * w or wl < 0.25 * w:
            continue
        ys.append((k + j) // 2)
    # merge pieces that are too short
    out, last = [], 0
    for y in ys:
        if y - last >= 0.5 * hmed:
            out.append(y)
            last = y
    if out and h - out[-1] < 0.5 * hmed:
        out.pop()
    return out


def pieces(img, ys):
    w, h = img.size
    bounds = [0] + ys + [h]
    res = []
    for a, b in zip(bounds, bounds[1:]):
        p = img.crop((0, a, w, b))
        arr = np.asarray(p.convert("L")) < 200
        if not arr.any():
            continue
        rows = np.where(arr.any(axis=1))[0]
        colsx = np.where(arr.any(axis=0))[0]
        pad = 4
        p = p.crop((max(0, colsx[0] - pad), max(0, rows[0] - pad), min(w, colsx[-1] + pad + 1), min(b - a, rows[-1] + pad + 1)))
        res.append(p)
    return res


def main():
    from mfr import MFRFast
    from pdfglyphs import PdfCache
    model, shard, nshards = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    items = json.load(open(os.path.join(ROOT, "manifests", "t2.json"), encoding="utf-8"))
    mine = [it for k, it in enumerate(items) if k % nshards == shard]
    m = MFRFast(model, 4)
    cache = PdfCache()
    os.makedirs(os.path.join(ROOT, "results", "t2"), exist_ok=True)
    t0 = time.time()
    with open(os.path.join(ROOT, "results", "t2", f"split_{model}.s{shard}.jsonl"), "w", encoding="utf-8") as f:
        for i, it in enumerate(mine):
            img = Image.open(os.path.join(ROOT, it["image"])).convert("RGB")
            try:
                ys = cuts_text_layer(it, cache) if it["set"] == "arxiv" else cuts_profile(img)
            except Exception as e:
                ys, err = [], str(e)[:200]
            ps = pieces(img, ys) if ys else []
            rec = {"id": it["id"], "n_pieces": len(ps), "cuts": ys}
            if len(ps) >= 2:
                t = time.perf_counter()
                preds = [m(p)[0] for p in ps]
                rec["pieces"] = preds
                rec["pred"] = "\begin{aligned} " + " \\ ".join(preds) + " \end{aligned}"
                rec["s"] = round(time.perf_counter() - t, 3)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            if i % 200 == 0:
                print(i, len(mine), round(time.time() - t0), flush=True)
    print("done", model, shard, len(mine), round(time.time() - t0))


if __name__ == "__main__":
    main()

"""Why is PP-OCRv6 medium worse than small on long synthetic lines? Same detector crops as the main test, our own
synthetic pages only (text may be printed). Variants of the recognizer input:
  docling   docling.rs ocr_prep.rs: RGB planes, height 48, width round(48 w/h) (no cap), bilinear, (x/127.5 - 1)
  bgr       same, BGR planes (PaddleOCR / RapidOCR read images as BGR)
  pil       same as docling but PIL bilinear with antialias (closer to image::FilterType::Triangle on downscale)
  win640    long crops cut at white gaps into pieces <= 640 px wide at height 48, read separately, joined
Prints CER per variant and width bucket, and the 30 crops where medium is worst relative to small.
usage: diag_medium.py OUT.json"""
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import data  # noqa: E402
import engines  # noqa: E402
import ppocr  # noqa: E402
import run_ocr  # noqa: E402
from common import edits, norm_text  # noqa: E402


def read(rec, rgb, variant):
    h, w = rgb.shape[:2]
    nw = int(min(max(round(w * 48 / h), 8), 16384))
    if variant == "pil":
        from PIL import Image
        im = np.array(Image.fromarray(rgb).resize((nw, 48), Image.BILINEAR, reducing_gap=None))
    else:
        im = cv2.resize(rgb, (nw, 48), interpolation=cv2.INTER_LINEAR)
    if variant == "bgr":
        im = im[:, :, ::-1]
    x = (im.astype(np.float32) / 127.5 - 1.0).transpose(2, 0, 1)[None]
    p = rec.s.run(None, {rec.name: np.ascontiguousarray(x)})[0][0]
    idx = p.argmax(axis=1)
    out, prev = [], 0
    for c in idx:
        if c != prev and c != 0:
            out.append(rec.chars[c])
        prev = c
    return "".join(out).strip(), p.shape[0]


def pieces(rgb, maxw=640):
    h, w = rgb.shape[:2]
    scale = 48 / h
    if w * scale <= maxw:
        return [rgb]
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ink = bw.sum(axis=0) > 0
    out, start, last_gap = [], 0, None
    run = 0
    for x in range(w):
        run = run + 1 if not ink[x] else 0
        if run >= max(2, int(0.2 * h)):
            last_gap = x - run // 2
        if (x - start) * scale > maxw and last_gap and last_gap > start:
            out.append(rgb[:, start:last_gap])
            start, last_gap = last_gap, None
    out.append(rgb[:, start:])
    return [p for p in out if p.shape[1] > 2]


def main():
    out = sys.argv[1]
    pages = [p for p in data.all_pages() if p["ds"] == "synth" and p["defect"] in ("lowdpi", "curved", "clean")
             and int(p["id"].split(":")[1]) % 40 == 0]
    det = ppocr.Detector(engines.P["det_s"])
    eng = engines.build(["v6s", "v6m"])
    stats, worst, n_steps = {}, [], {}
    for p in pages:
        rgb, words, fields, kind = data.load(p)
        boxes = det(rgb)
        crops = [ppocr.crop(rgb, b["quad"]) for b in boxes]
        keep = [i for i, c in enumerate(crops) if c is not None]
        owner = run_ocr.assign(words, boxes)
        gt_by = {}
        for w_, o in zip(words, owner):
            if o >= 0:
                gt_by.setdefault(o, []).append(w_)
        for i in keep:
            g = norm_text(run_ocr.serialize([(w_["t"], w_["box"]) for w_ in gt_by.get(i, [])]))
            if not g:
                continue
            c = crops[i]
            w48 = 48 * c.shape[1] / c.shape[0]
            b = "<=320" if w48 <= 320 else "<=640" if w48 <= 640 else "<=1280" if w48 <= 1280 else ">1280"
            res = {}
            for m in ("v6s", "v6m"):
                for v in ("docling", "bgr", "pil"):
                    t, T = read(eng[m], c, v)
                    res[(m, v)] = t
                    n_steps[(m, b)] = T
                res[(m, "win640")] = " ".join(read(eng[m], pc, "docling")[0] for pc in pieces(c))
            for key, t in res.items():
                s = stats.setdefault(f"{key[0]}|{key[1]}|{b}", [0, 0, 0])
                s[0] += edits(norm_text(t), g)
                s[1] += len(g)
                s[2] += 1
            d = edits(norm_text(res[("v6m", "docling")]), g) - edits(norm_text(res[("v6s", "docling")]), g)
            worst.append((d / len(g), p["id"], round(w48), g, res[("v6s", "docling")], res[("v6m", "docling")],
                          res[("v6m", "bgr")], res[("v6m", "win640")]))
    worst.sort(key=lambda t: -t[0])
    table = {k: {"cer": v[0] / max(1, v[1]), "crops": v[2]} for k, v in sorted(stats.items())}
    json.dump({"pages": len(pages), "cer": table, "time_steps": {f"{k[0]}|{k[1]}": v for k, v in n_steps.items()},
               "worst": worst[:30]}, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for k, v in table.items():
        print(f"{k:28s} CER {v['cer']:.4f}  crops {v['crops']}")
    print("time steps per width bucket (last crop):", n_steps)
    for t in worst[:30]:
        print(f"\n[{t[1]} w48={t[2]} dCER={t[0]:.2f}]\n GT : {t[3]}\n v6s: {t[4]}\n v6m: {t[5]}\n v6m bgr: {t[6]}\n v6m win640: {t[7]}")


if __name__ == "__main__":
    main()

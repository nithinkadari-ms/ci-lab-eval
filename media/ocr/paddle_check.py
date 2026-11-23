"""Is the PP-OCRv6 medium collapse on long lines in the model or in RapidOCR's ONNX export? Runs the official Paddle
inference files (RapidOCR model hub v3.9.2, paddle/PP-OCRv6/rec/PP-OCRv6_rec_{small,medium}) with Paddle Inference
on the same detector crops as diag_medium.py, preprocessed as PaddleX OCRReisizeNormImg (BGR, height 48, width
ceil(48 w/h) up to 3200, /255 -0.5 /0.5, padded to at least 320), and compares with the ONNX files.
usage: paddle_check.py OUT.json"""
import json
import math
import os
import sys
import urllib.request

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

MS = "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.9.2/paddle/PP-OCRv6/rec/"
D = os.path.expanduser("~/paddle-rec")


def fetch(size):
    d = os.path.join(D, size)
    os.makedirs(d, exist_ok=True)
    for f in ("inference.json", "inference.pdiparams", "inference.yml"):
        p = os.path.join(d, f)
        if not os.path.exists(p):
            urllib.request.urlretrieve(MS + f"PP-OCRv6_rec_{size}/" + f, p)
    return d


def predictor(d):
    import paddle.inference as pi
    cfg = pi.Config(os.path.join(d, "inference.json"), os.path.join(d, "inference.pdiparams"))
    cfg.disable_gpu()
    cfg.set_cpu_math_library_num_threads(4)
    return pi.create_predictor(cfg)


def paddlex_input(rgb):
    img = rgb[:, :, ::-1]
    h, w = img.shape[:2]
    ratio = w / h
    imgW = max(320, int(48 * max(ratio, 320 / 48)))
    if imgW > 3200:
        resized, rw, imgW = cv2.resize(img, (3200, 48)), 3200, 3200
    else:
        rw = min(imgW, int(math.ceil(48 * ratio)))
        resized = cv2.resize(img, (rw, 48))
    x = resized.astype("float32").transpose((2, 0, 1)) / 255
    x = (x - 0.5) / 0.5
    pad = np.zeros((3, 48, imgW), dtype=np.float32)
    pad[:, :, :rw] = x
    return pad[None]


def run_paddle(pred, x):
    h = pred.get_input_handle(pred.get_input_names()[0])
    h.reshape(x.shape)
    h.copy_from_cpu(np.ascontiguousarray(x))
    pred.run()
    return pred.get_output_handle(pred.get_output_names()[0]).copy_to_cpu()[0]


def decode(p, chars):
    idx = p.argmax(axis=1)
    out, prev = [], 0
    for c in idx:
        if c != prev and c != 0 and c < len(chars):
            out.append(chars[c])
        prev = c
    return "".join(out).strip()


def main():
    out = sys.argv[1]
    chars = ppocr.load_dict(engines.P["dict_s"])
    pd_s, pd_m = predictor(fetch("small")), predictor(fetch("medium"))
    eng = engines.build(["v6s", "v6m"])
    det = ppocr.Detector(engines.P["det_s"])
    pages = [p for p in data.all_pages() if p["ds"] == "synth" and p["defect"] in ("lowdpi", "curved")
             and int(p["id"].split(":")[1]) in (4, 17, 19)]
    tot = {}
    rows = []
    for p in pages:
        rgb, words, fields, kind = data.load(p)
        boxes = det(rgb)
        crops = [ppocr.crop(rgb, b["quad"]) for b in boxes]
        owner = run_ocr.assign(words, boxes)
        gt_by = {}
        for w_, o in zip(words, owner):
            if o >= 0:
                gt_by.setdefault(o, []).append(w_)
        for i, c in enumerate(crops):
            if c is None:
                continue
            g = norm_text(run_ocr.serialize([(w_["t"], w_["box"]) for w_ in gt_by.get(i, [])]))
            if len(g) < 40:
                continue
            x = paddlex_input(c)
            r = {"onnx_s": eng["v6s"].one(c)[0], "onnx_m": eng["v6m"].one(c)[0],
                 "paddle_s": decode(run_paddle(pd_s, x), chars), "paddle_m": decode(run_paddle(pd_m, x), chars)}
            onnx_m_px = eng["v6m"].s.run(None, {eng["v6m"].name: x})[0][0]
            r["onnx_m_paddlex_input"] = decode(onnx_m_px, chars)
            for k, t in r.items():
                s = tot.setdefault(k, [0, 0])
                s[0] += edits(norm_text(t), g)
                s[1] += len(g)
            rows.append({"page": p["id"], "w48": round(48 * c.shape[1] / c.shape[0]), "gt": g, **r})
    res = {k: v[0] / max(1, v[1]) for k, v in tot.items()}
    json.dump({"cer": res, "n": len(rows), "rows": rows[:40]}, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("long crops (>= 40 chars):", len(rows))
    for k, v in res.items():
        print(f"{k:22s} CER {v:.4f}")
    for r in rows[:12]:
        print(f"\n[{r['page']} w48={r['w48']}]\n GT        : {r['gt']}\n paddle_s  : {r['paddle_s']}\n paddle_m  : {r['paddle_m']}"
              f"\n onnx_s    : {r['onnx_s']}\n onnx_m    : {r['onnx_m']}\n onnx_m(px): {r['onnx_m_paddlex_input']}")


if __name__ == "__main__":
    main()

import os

import numpy as np
import onnxruntime as ort
from PIL import Image

REC_H = 48


def models_dir():
    return os.path.join(os.environ.get("DOCLING_RS_CACHE_DIR", os.path.expanduser("~/dlrs")), "models")


class Rec:
    def __init__(self, threads=2):
        md = models_dir()
        so = ort.SessionOptions()
        so.intra_op_num_threads = threads
        so.inter_op_num_threads = 1
        self.sess = ort.InferenceSession(os.path.join(md, "ocr_rec_v6.onnx"), so, providers=["CPUExecutionProvider"])
        self.inp = self.sess.get_inputs()[0].name
        with open(os.path.join(md, "ocr_rec_v6_dict.txt"), encoding="utf-8") as f:
            lines = f.read().splitlines()
        self.chars = [""] + lines + [" "]
        self.calls = 0
        self.lines = 0

    def prep(self, im):
        im = im.convert("RGB")
        w, h = im.size
        if w == 0 or h == 0:
            return None
        nw = int(min(16384, max(8, round(w * REC_H / h))))
        im = im.resize((nw, REC_H), Image.BILINEAR)
        a = np.asarray(im, dtype=np.float32) / 127.5 - 1.0
        return a.transpose(2, 0, 1)

    def decode(self, probs):
        best = probs.argmax(-1)
        vals = probs.max(-1)
        out, prev, cs = [], 0, []
        for t, b in enumerate(best):
            b = int(b)
            if b != prev and b != 0 and b < len(self.chars):
                out.append(self.chars[b])
                cs.append(float(vals[t]))
            prev = b
        return "".join(out).strip(), (sum(cs) / len(cs) if cs else 0.0)

    def __call__(self, ims):
        res = [("", 0.0)] * len(ims)
        preps = [self.prep(im) for im in ims]
        groups = {}
        for i, p in enumerate(preps):
            if p is not None:
                groups.setdefault(p.shape[2], []).append(i)
        for w, idx in groups.items():
            for k in range(0, len(idx), 16):
                chunk = idx[k:k + 16]
                x = np.stack([preps[i] for i in chunk])
                y = self.sess.run(None, {self.inp: x})[0]
                self.calls += 1
                for j, i in enumerate(chunk):
                    res[i] = self.decode(y[j])
        self.lines += len(ims)
        return res


def crop(img, scale, crop_lt, box, pad=0.18):
    l, t, r, b = box
    h = b - t
    p = max(1.0, pad * h)
    x0 = int(max(0, (l - p - crop_lt[0]) * scale))
    y0 = int(max(0, (t - p - crop_lt[1]) * scale))
    x1 = int(min(img.size[0], (r + p - crop_lt[0]) * scale))
    y1 = int(min(img.size[1], (b + p - crop_lt[1]) * scale))
    if x1 <= x0 or y1 <= y0:
        return Image.new("RGB", (8, 8), "white")
    return img.crop((x0, y0, x1, y1))

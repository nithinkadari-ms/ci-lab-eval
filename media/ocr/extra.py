"""Gap 1 extra challengers (tests only), on the same pages and the same PP-OCRv6 small detector crops as
run_ocr.py: UnionST-SP (OpenOCR SVTRv2 + NRTR, word-level scene model) on whole line crops and on word-split crops,
UnionST as a second reader on low-confidence PP-OCRv6 lines (digit/ID changes need agreement), UniRec-0.1B
(ONNX, text crops) and DocRes as gated page cleanup. PP-OCRv6 small and medium are re-run on the same crops for
paired comparisons. Numbers only are written.

Subsets (deterministic): main = every 4th page of data.all_pages(); UniRec = every 8th page; DocRes = main-subset
pages where the cleanup gate fires (capped per defect per shard) plus forced runs on clean synthetic pages.
usage: extra.py SHARD NSHARDS OUT.jsonl"""
import functools
import json
import os
import sys
import time
import traceback
from collections import Counter

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import data  # noqa: E402
import engines  # noqa: E402
import ppocr  # noqa: E402
import run_ocr  # noqa: E402
from common import edits, norm_text, num_tokens, word_edits  # noqa: E402

OPENOCR = os.environ.get("UNIONST_OPENOCR", "/home/runner/unionst/OpenOCR")
UNIONST_PTH = os.environ.get("UNIONST_PTH", "/home/runner/extra-models/unionst/UnionST-SP.pth")
DOCRES_DIR = os.environ.get("DOCRES_DIR", "/home/runner/docres")
DOCRES_PKL = os.environ.get("DOCRES_PKL", "/home/runner/extra-models/docres/checkpoints/docres.pkl")
CAP_PER_DEFECT = 4
FORCED_CLEAN = 4
PADDLE = {"v6s", "v6m"}


def rss_mb():
    import psutil
    return psutil.Process().memory_info().rss / 1e6


# ---------------------------------------------------------------- UnionST-SP through OpenOCR's own recognizer
class UnionST:
    def __init__(self):
        import torch
        torch.set_num_threads(4)
        _load = torch.load
        torch.load = functools.partial(_load, weights_only=False)  # pinned, trusted test checkpoint
        cwd = os.getcwd()
        os.chdir(OPENOCR)
        sys.path.insert(0, OPENOCR)
        from tools.engine.config import Config
        from tools.infer_rec import OpenRecognizer
        cfg = Config("configs/rec/nrtr/svtrv2_nrtr_unionst.yml").cfg
        cfg["Global"]["pretrained_model"] = UNIONST_PTH
        cfg["Global"]["device"] = "cpu"
        self.rec = OpenRecognizer(cfg, backend="torch")
        sd = torch.load(UNIONST_PTH, map_location="cpu")
        sd = sd.get("state_dict", sd)
        mk = set(self.rec.model.state_dict()) - set(sd)
        self.missing = len(mk)
        os.chdir(cwd)
        if mk:
            raise RuntimeError(f"UnionST checkpoint misses {len(mk)} model keys, e.g. {sorted(mk)[:3]}")

    def read(self, rgbs):
        """OpenOCR's NRTR decoder places tensors with device=src.get_device(), which is -1 on CPU and rejected by
        current torch; during this call get_device returns the tensor's device object instead."""
        import torch
        from PIL import Image
        if not rgbs:
            return []
        orig = torch.Tensor.get_device
        torch.Tensor.get_device = lambda t: t.device
        try:
            out = self.rec(img_numpy_list=[Image.fromarray(x) for x in rgbs], batch_num=1)
        finally:
            torch.Tensor.get_device = orig
        return [(str(r["text"]), float(r["score"])) for r in out]


def split_words(rgb):
    """vertical white gaps wider than a quarter of the line height split a line crop into word crops"""
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    h, w = g.shape
    if w < 2 * h:
        return [rgb]
    _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ink = bw.sum(axis=0) > 0
    gap = max(3, int(0.25 * h))
    cuts, run = [], 0
    for x in range(w):
        if not ink[x]:
            run += 1
        else:
            if run >= gap:
                cuts.append(x - run // 2)
            run = 0
    edges = [0] + cuts + [w]
    out = []
    for a, b in zip(edges, edges[1:]):
        seg = ink[a:b]
        if seg.sum() == 0:
            continue
        xs = np.where(seg)[0]
        x0, x1 = max(0, a + xs[0] - 2), min(w, a + xs[-1] + 3)
        if x1 - x0 >= 2:
            out.append(np.ascontiguousarray(rgb[:, x0:x1]))
    return out or [rgb]


def merge(base, other):
    """second reader: word-aligned (edit distance) merge; never change a token with digits unless both agree"""
    import difflib
    a, b = base.split(), other.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal" or op == "delete":
            out += a[i1:i2]
        elif op == "replace":
            xa, xb = a[i1:i2], b[j1:j2]
            if any(any(c.isdigit() for c in t) for t in xa + xb):
                out += xa
            elif len(xa) == len(xb):
                out += xb
            else:
                out += xa
    return " ".join(out)


# ---------------------------------------------------------------- UniRec-0.1B (ONNX, from the round-3 reference set)
class UniRecPIL:
    def __init__(self):
        sys.path.insert(0, os.path.join(ROOT, "formula", "scripts"))
        import refmodels
        self.m = refmodels.UniRec(threads=4)
        self.size_mb = sum(os.path.getsize(os.path.join(refmodels.RD, "unirec", f)) for f in
                           ("unirec_encoder.onnx", "unirec_decoder.onnx")) / 1e6

    def one(self, rgb):
        from PIL import Image
        m = self.m
        img = Image.fromarray(rgb)
        w, h = img.size
        ar = w / h
        if w > m.MAX_W or h > m.MAX_H:
            if (m.MAX_W / m.MAX_H) >= ar:
                nh, nw = m.MAX_H, int(m.MAX_H * ar)
            else:
                nw, nh = m.MAX_W, int(m.MAX_W / ar)
        else:
            nw, nh = w, h
        fw, fh = max(int(nw // m.DIV * m.DIV), 64), max(int(nh // m.DIV * m.DIV), 64)
        x = (np.array(img.resize((fw, fh), resample=Image.BICUBIC), dtype=np.float32) / 255.0 - 0.5) / 0.5
        x = x.transpose(2, 0, 1)[None].astype(np.float32)
        tmp = "/tmp/_unirec_crop.npy"
        np.save(tmp, x)
        m.preprocess = lambda path: np.load(path)
        txt, n, runaway = m(tmp)
        return " ".join(txt.split()), (0.0 if runaway else 1.0)

    def read(self, rgbs):
        return [self.one(x) for x in rgbs]


# ---------------------------------------------------------------- DocRes (author code: Restormer + task prompts)
def _deshadow_prompt(img):
    h, w = img.shape[:2]
    img = cv2.resize(img, (1024, 1024))
    bg = [cv2.medianBlur(cv2.dilate(p, np.ones((7, 7), np.uint8)), 21) for p in cv2.split(img)]
    return cv2.resize(cv2.merge(bg), (w, h))


def _appearance_prompt(img):
    h, w = img.shape[:2]
    img = cv2.resize(img, (1024, 1024))
    planes = []
    for p in cv2.split(img):
        bg = cv2.medianBlur(cv2.dilate(p, np.ones((7, 7), np.uint8)), 21)
        diff = 255 - cv2.absdiff(p, bg)
        planes.append(cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1))
    return cv2.resize(cv2.merge(planes), (w, h))


def _deblur_prompt(img):
    x = cv2.convertScaleAbs(cv2.Sobel(img, cv2.CV_16S, 1, 0))
    y = cv2.convertScaleAbs(cv2.Sobel(img, cv2.CV_16S, 0, 1))
    hf = cv2.cvtColor(cv2.addWeighted(x, 0.5, y, 0.5, 0), cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(hf, cv2.COLOR_GRAY2BGR)


class DocRes:
    """Port of DocRes inference.py (deshadowing / appearance / deblurring) in float32 on CPU (the author code casts
    to fp16 for GPU). The network runs at full resolution in 512 px tiles with 64 px overlap (the author code runs the
    whole image, resized to 1600 x 1600 for large pages); the task prompts are computed on the whole page."""
    MAX = 1600

    def __init__(self):
        import torch
        torch.set_num_threads(4)
        sys.path.insert(0, DOCRES_DIR)
        from models import restormer_arch
        self.torch = torch
        self.model = restormer_arch.Restormer(inp_channels=6, out_channels=3, dim=48, num_blocks=[2, 3, 3, 4],
                                              num_refinement_blocks=4, heads=[1, 2, 4, 8], ffn_expansion_factor=2.66,
                                              bias=False, LayerNorm_type="WithBias", dual_pixel_task=True)
        raw = torch.load(DOCRES_PKL, map_location="cpu", weights_only=False)["model_state"]
        st = {(k[7:] if k.startswith("module.") else k): v for k, v in raw.items()}
        self.model.load_state_dict(st)
        self.model.eval()

    def _run(self, x):
        t = self.torch.from_numpy((x / 255.0).transpose(2, 0, 1)).unsqueeze(0).float()
        with self.torch.no_grad():
            p = self.torch.clamp(self.model(t), 0, 1)[0].permute(1, 2, 0).numpy()
        return (p * 255).astype(np.uint8)

    @staticmethod
    def _pad8(im):
        h, w = im.shape[:2]
        ph, pw = (8 - h % 8) % 8, (8 - w % 8) % 8
        return cv2.copyMakeBorder(im, ph, 0, pw, 0, cv2.BORDER_REPLICATE), ph, pw

    def _tiled(self, x, tile=512, ov=64):
        """full-resolution inference in overlapping tiles (bounded memory on CPU); the prompt channels are computed
        on the whole page beforehand, as in the author code"""
        x, ph, pw = self._pad8(x)
        H, W = x.shape[:2]
        out = np.zeros((H, W, 3), np.float32)
        wsum = np.zeros((H, W, 1), np.float32)
        step = tile - ov
        ys = list(range(0, max(1, H - ov), step)) or [0]
        xs = list(range(0, max(1, W - ov), step)) or [0]
        for y0 in ys:
            for x0 in xs:
                y1, x1 = min(H, y0 + tile), min(W, x0 + tile)
                ya, xa = max(0, y1 - tile), max(0, x1 - tile)
                t8, tph, tpw = self._pad8(x[ya:y1, xa:x1])
                out[ya:y1, xa:x1] += self._run(t8)[tph:, tpw:].astype(np.float32)
                wsum[ya:y1, xa:x1] += 1
        return (out / np.maximum(wsum, 1)).astype(np.uint8)[ph:, pw:]

    def __call__(self, rgb, task):
        bgr = rgb[:, :, ::-1].copy()
        if task == "deblurring":
            prompt = _deblur_prompt(bgr)
        elif task == "deshadowing":
            prompt = _deshadow_prompt(bgr)
        else:
            prompt = _appearance_prompt(bgr)
        out = self._tiled(np.concatenate((bgr, prompt), -1))
        return np.ascontiguousarray(out[:, :, ::-1])


def docres_gate(rgb, dfx):
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    lap = float(cv2.Laplacian(g, cv2.CV_64F).var())
    if lap < 120:
        return "deblurring", lap
    if dfx["illum"] > 40:
        return "deshadowing", lap
    if dfx["contrast"] < 110:
        return "appearance", lap
    return None, lap


# ---------------------------------------------------------------- per page
def page_e2e(rgb, det, rec_fn, paddle, gt_str, fields):
    boxes = det(rgb)
    crops = [ppocr.crop(rgb, b["quad"]) for b in boxes]
    keep = [k for k, c in enumerate(crops) if c is not None]
    res = rec_fn([crops[k] for k in keep])
    items = [(t, boxes[k]["box"]) for k, (t, c) in zip(keep, res) if t and not (paddle and c < ppocr.TEXT_SCORE)]
    return run_ocr.e2e_metrics(items, gt_str, fields)


GROUP = os.environ.get("EXTRA_GROUP", "unionst")
CAP_JOB = int(os.environ.get("DOCRES_CAP", "2"))
FORCED_JOB = int(os.environ.get("DOCRES_FORCED", "2"))


def crop_gt(words, boxes, keep):
    owner = run_ocr.assign(words, boxes)
    gt_by = {}
    for w, o in zip(words, owner):
        if o >= 0:
            gt_by.setdefault(o, []).append(w)
    return [norm_text(run_ocr.serialize([(w["t"], w["box"]) for w in gt_by.get(i, [])])) for i in keep]


def score_text(t, g):
    pt = norm_text(t)
    we, _ = word_edits(pt, g)
    gnum = num_tokens(g)
    return [edits(pt, g), we, sum((Counter(num_tokens(pt)) & Counter(gnum)).values())]


def main():
    """EXTRA_GROUP=unionst (every 4th page; v6s + UnionST line / word-split / second reader),
    unirec (every 8th page; v6s + UniRec), docres (every 4th page; gate + tiled DocRes + v6s end to end).
    PP-OCRv6 medium on the same crops comes from the main OCR records (same detector, same crop order)."""
    k, n, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    pages = data.all_pages()
    step = 8 if GROUP == "unirec" else 4
    sub = [p for i, p in enumerate(pages) if i % step == 0]
    mine = [p for i, p in enumerate(sub) if i % n == k]
    info = {"group": GROUP, "rss_start": rss_mb()}
    det = ppocr.Detector(engines.P["det_s"])
    v6s = engines.build(["v6s"])["v6s"]
    info["rss_ppocr"] = rss_mb()
    if GROUP == "unionst":
        model = UnionST()
        info["unionst_missing_keys"] = model.missing
        info["unionst_mb"] = os.path.getsize(UNIONST_PTH) / 1e6
    elif GROUP == "unirec":
        model = UniRecPIL()
        info["unirec_mb"] = model.size_mb
    else:
        model = DocRes()
        info["docres_mb"] = os.path.getsize(DOCRES_PKL) / 1e6
    info["rss_model"] = rss_mb()
    print("models", info, flush=True)
    caps = Counter()
    forced = rows = errs = 0
    with open(out, "w", encoding="utf-8") as f:
        f.write(json.dumps({"info": info}) + "\n")
        for p in mine:
            rec = {key: p[key] for key in ("id", "group", "ds", "defect", "split")}
            rec["xgroup"] = GROUP
            try:
                rgb, words, fields, kind = data.load(p)
                rec["kind"] = kind
                gt_str = run_ocr.serialize([(w["t"], w["box"]) for w in words])
                boxes = det(rgb)
                crops = [ppocr.crop(rgb, b["quad"]) for b in boxes]
                keep = [i for i, c in enumerate(crops) if c is not None]
                kc = [crops[i] for i in keep]
                rec["n_crops"] = len(kc)
                if GROUP == "docres":
                    dfx = engines.defects(rgb, boxes)
                    task, lap = docres_gate(rgb, dfx)
                    rec["docres_gate"], rec["lap_var"] = task, lap
                    run_task, why = None, None
                    if task and caps[p["defect"]] < CAP_JOB:
                        caps[p["defect"]] += 1
                        run_task, why = task, "gate"
                    elif p["ds"] == "synth" and p["defect"] == "clean" and forced < FORCED_JOB and not task:
                        forced += 1
                        run_task, why = "appearance", "forced_clean"
                    e2e = {}
                    if run_task:
                        e2e["v6s"] = page_e2e(rgb, det, v6s, True, gt_str, fields)
                        t = time.perf_counter()
                        clean = model(rgb, run_task)
                        dt = (time.perf_counter() - t) * 1000
                        m = page_e2e(clean, det, v6s, True, gt_str, fields)
                        m["ms_docres"] = dt
                        e2e["docres_v6s"] = m
                        rec["docres_task"], rec["docres_why"] = run_task, why
                        rec["rss"] = rss_mb()
                    rec["e2e"] = e2e
                else:
                    gts = crop_gt(words, boxes, keep)
                    R, ms = {}, {}
                    t = time.perf_counter()
                    R["v6s"] = v6s(kc)
                    ms["v6s"] = (time.perf_counter() - t) * 1000
                    if GROUP == "unionst":
                        t = time.perf_counter()
                        R["unionst_line"] = model.read(kc)
                        ms["unionst_line"] = (time.perf_counter() - t) * 1000
                        t = time.perf_counter()
                        R["unionst_words"], nwords = [], 0
                        for c in kc:
                            ws = split_words(c)
                            nwords += len(ws)
                            rr = model.read(ws)
                            R["unionst_words"].append((" ".join(x for x, _ in rr if x),
                                                       min([s_ for _, s_ in rr] or [0.0])))
                        ms["unionst_words"] = (time.perf_counter() - t) * 1000
                        rec["n_word_crops"] = nwords
                    else:
                        t = time.perf_counter()
                        R["unirec"] = model.read(kc)
                        ms["unirec"] = (time.perf_counter() - t) * 1000
                    rec["ms"] = ms
                    crow = []
                    for idx, g in enumerate(gts):
                        row = {"n": len(g), "nw": len(g.split()), "nnum": len(num_tokens(g)),
                               "w_px": int(kc[idx].shape[1]), "h_px": int(kc[idx].shape[0])}
                        for name in R:
                            row[name] = score_text(R[name][idx][0], g) + [round(float(R[name][idx][1]), 4)]
                        if GROUP == "unionst":
                            row["merged"] = score_text(merge(R["v6s"][idx][0], R["unionst_words"][idx][0]), g)
                        crow.append(row)
                    rec["crops"] = crow
                    e2e = {}
                    for name in R:
                        items = [(t_, boxes[i]["box"]) for i, (t_, c_) in zip(keep, R[name])
                                 if t_ and not (name in PADDLE and c_ < ppocr.TEXT_SCORE)]
                        e2e[name] = run_ocr.e2e_metrics(items, gt_str, fields)
                    rec["e2e"] = e2e
                    rec["rss"] = rss_mb()
            except Exception as e:  # noqa: BLE001
                rec["error"] = f"{type(e).__name__}: {e}"[:300]
                rec["tb"] = traceback.format_exc()[-800:]
                errs += 1
            rows += 1
            f.write(json.dumps(rec) + "\n")
            f.flush()
            if rows % 5 == 0:
                print(GROUP, k, rows, len(mine), "errors", errs, "rss", round(rss_mb()), flush=True)
    print("done", GROUP, k, n, "rows", rows, "errors", errs, flush=True)
    if mine and (rows == 0 or errs > 0.02 * rows):
        sys.exit(f"FAILED: {errs} errors in {rows} rows (limit 2%)")


if __name__ == "__main__":
    main()

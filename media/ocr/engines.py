"""Recognizers behind one crop interface, Tesseract page OCR, gated preprocessing and UVDoc."""
import math
import os
import time

import cv2
import numpy as np

import ppocr

D = os.path.join(os.environ.get("MEDIA_MODELS", os.path.join(os.path.expanduser("~"), "media-models")), "ocr")
P = {
    "det_s": os.path.join(D, "dlrs", "ocr_det.onnx"),
    "rec_s": os.path.join(D, "dlrs", "ocr_rec_v6.onnx"),
    "dict_s": os.path.join(D, "dlrs", "ocr_rec_v6_dict.txt"),
    "det_m": os.path.join(D, "v6m", "det_medium.onnx"),
    "rec_m": os.path.join(D, "v6m", "rec_medium.onnx"),
    "dict_m": os.path.join(D, "v6m", "dict.txt"),
    "v5en": os.path.join(D, "v5en", "inference.onnx"),
    "v5en_yml": os.path.join(D, "v5en", "inference.yml"),
    "uvdoc": os.path.join(D, "uvdoc", "inference.onnx"),
    "crnn": os.path.join(D, "crnn"),
    "viptr": os.path.join(D, "viptr"),
    "tess_fast": os.path.join(D, "tess_fast"),
    "tess_best": os.path.join(D, "tess_best"),
}
CROP_ENGINES = ["v6s", "v6m", "v5en", "crnn", "viptr", "tess_fast", "tess_best"]


class Tess:
    """Tesseract 5 LSTM through tesserocr (built against the apt libtesseract) or the apt CLI via pytesseract."""

    def __init__(self, kind, psm_line=True):
        self.dir = P["tess_" + kind]
        self.psm_line = psm_line
        self.api = None
        try:
            import tesserocr
            self.api = tesserocr.PyTessBaseAPI(path=self.dir, lang="eng", oem=tesserocr.OEM.LSTM_ONLY,
                                               psm=tesserocr.PSM.SINGLE_LINE if psm_line else tesserocr.PSM.AUTO)
            self.backend = "tesserocr " + tesserocr.tesseract_version().split()[1]
        except Exception as e:  # noqa: BLE001
            import pytesseract
            self.backend = "pytesseract " + str(pytesseract.get_tesseract_version()) + f" ({type(e).__name__})"

    def one(self, rgb):
        from PIL import Image
        im = Image.fromarray(rgb)
        if self.api is not None:
            self.api.SetImage(im)
            t = self.api.GetUTF8Text()
            c = self.api.MeanTextConf() / 100.0
            return " ".join(t.split()), max(0.0, c)
        import pytesseract
        cfg = f"--tessdata-dir {self.dir} --oem 1 --psm {7 if self.psm_line else 3}"
        d = pytesseract.image_to_data(im, lang="eng", config=cfg, output_type=pytesseract.Output.DICT)
        words = [(w, float(c)) for w, c in zip(d["text"], d["conf"]) if w.strip()]
        if not words:
            return "", 0.0
        return " ".join(w for w, _ in words), sum(max(0.0, c) for _, c in words) / len(words) / 100.0

    def __call__(self, crops):
        return [self.one(c) for c in crops]

    def page_lines(self, rgb):
        """Whole-page Tesseract with its own layout: text lines with boxes."""
        from PIL import Image
        import pytesseract
        d = pytesseract.image_to_data(Image.fromarray(rgb), lang="eng",
                                      config=f"--tessdata-dir {self.dir} --oem 1 --psm 3",
                                      output_type=pytesseract.Output.DICT)
        lines = {}
        for i, w in enumerate(d["text"]):
            if not w.strip():
                continue
            k = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
            x0, y0 = d["left"][i], d["top"][i]
            x1, y1 = x0 + d["width"][i], y0 + d["height"][i]
            L = lines.setdefault(k, {"words": [], "box": [x0, y0, x1, y1]})
            L["words"].append(w)
            b = L["box"]
            L["box"] = [min(b[0], x0), min(b[1], y0), max(b[2], x1), max(b[3], y1)]
        return [{"text": " ".join(v["words"]), "box": v["box"], "conf": 1.0} for v in lines.values()]


class OnnxTR:
    def __init__(self, key):
        from onnxtr.models import EngineConfig, from_hub, recognition_predictor
        import onnxruntime as ort
        so = ort.SessionOptions()
        so.intra_op_num_threads = 1
        so.inter_op_num_threads = 1
        so.enable_cpu_mem_arena = False
        cfg = EngineConfig(providers=["CPUExecutionProvider"], session_options=so)
        repo = {"crnn": "Felix92/onnxtr-crnn-mobilenet-v3-small", "viptr": "Felix92/onnxtr-viptr-tiny"}[key]
        model = from_hub(repo, engine_cfg=cfg)
        self.p = recognition_predictor(model)

    def __call__(self, crops):
        if not crops:
            return []
        res = self.p([np.ascontiguousarray(c) for c in crops])
        return [(str(t).strip(), float(c)) for t, c in res]


def build(names, threads=1):
    eng = {}
    for n in names:
        if n == "v6s":
            eng[n] = ppocr.Recognizer(P["rec_s"], ppocr.load_dict(P["dict_s"]), threads)
        elif n == "v6m":
            dpath = P["dict_m"] if os.path.exists(P["dict_m"]) else P["dict_s"]
            eng[n] = ppocr.Recognizer(P["rec_m"], ppocr.load_dict(dpath), threads)
        elif n == "v5en":
            eng[n] = ppocr.Recognizer(P["v5en"], ppocr.dict_from_yml(P["v5en_yml"]), threads)
        elif n in ("crnn", "viptr"):
            eng[n] = OnnxTR(n)
        elif n in ("tess_fast", "tess_best"):
            eng[n] = Tess(n.split("_")[1])
    return eng


# ---------------------------------------------------------------- defects, gates and preprocessing
def gray(rgb):
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)


def line_angles(boxes):
    out = []
    for b in boxes:
        q = b["quad"]
        dx, dy = q[1][0] - q[0][0], q[1][1] - q[0][1]
        L = math.hypot(dx, dy)
        h = math.dist(q[0], q[3])
        if L > 3 * h and L > 40:
            out.append((math.degrees(math.atan2(dy, dx)), L))
    return out


def defects(rgb, boxes):
    """Cheap defect estimates used by the gates (thresholds fixed a priori, not tuned on test data)."""
    g = gray(rgb)
    ang = line_angles(boxes)
    if ang:
        tot = sum(L for _, L in ang)
        med = sorted(ang)[len(ang) // 2][0]
        spread = math.sqrt(sum(L * (a - med) ** 2 for a, L in ang) / tot)
    else:
        med, spread = 0.0, 0.0
    p5, p95 = np.percentile(g, 5), np.percentile(g, 95)
    bg = cv2.medianBlur(cv2.resize(g, (max(8, g.shape[1] // 8), max(8, g.shape[0] // 8))), 5)
    illum = float(np.percentile(bg, 90) - np.percentile(bg, 10))
    noise = float(np.mean(np.abs(g.astype(np.int16) - cv2.medianBlur(g, 3).astype(np.int16))))
    return {"skew": float(med), "angle_spread": float(spread), "contrast": float(p95 - p5), "illum": illum,
            "noise": noise, "n_lines": len(ang)}


GATES = {"skew": 0.8, "spread": 1.2, "contrast": 110.0, "illum": 40.0, "noise": 9.0}


def gate(d):
    return {"deskew": abs(d["skew"]) > GATES["skew"],
            "clahe": d["contrast"] < GATES["contrast"] or d["illum"] > GATES["illum"],
            "denoise": d["noise"] > GATES["noise"],
            "uvdoc": d["angle_spread"] > GATES["spread"] or abs(d["skew"]) > GATES["skew"]}


def deskew(rgb, angle):
    h, w = rgb.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(rgb, M, (w, h), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))


def clahe(rgb):
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    lab[:, :, 0] = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)


def denoise(rgb):
    return cv2.fastNlMeansDenoisingColored(rgb, None, 7, 7, 7, 21)


class UVDoc:
    """PaddleX UVDoc ONNX: BGR / 255, CHW, the network returns the unwarped image (PaddleX DocTrPostProcess)."""

    def __init__(self, threads=1):
        self.s = ppocr.session(P["uvdoc"], threads)
        self.name = self.s.get_inputs()[0].name

    def __call__(self, rgb):
        h, w = rgb.shape[:2]
        sc = min(1.0, 1600.0 / max(h, w))
        im = cv2.resize(rgb, (int(w * sc), int(h * sc)), interpolation=cv2.INTER_AREA) if sc < 1 else rgb
        x = (im[:, :, ::-1].astype(np.float32) / 255.0).transpose(2, 0, 1)[None]
        y = self.s.run(None, {self.name: np.ascontiguousarray(x)})[0]
        y = y[0] if y.ndim == 4 else y
        out = np.clip(y.transpose(1, 2, 0) * 255.0, 0, 255).astype(np.uint8)[:, :, ::-1]
        if sc < 1:
            out = cv2.resize(out, (w, h), interpolation=cv2.INTER_CUBIC)
        return np.ascontiguousarray(out)


def timed(fn, *a):
    t = time.perf_counter()
    r = fn(*a)
    return r, (time.perf_counter() - t) * 1000

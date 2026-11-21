"""FFDetr form-field detection, test only. Loads the RF-DETR Medium checkpoints the same way commonforms 0.2.1
FFDetrDetector does (commonforms/inference.py: RFDETRMedium(pretrain_weights=...), predict(threshold=0.4),
class-agnostic NMS 0.1, classes 0 TextBox / 1 ChoiceButton / 2 Signature, PDF pages rendered at scale 2), but
calls rfdetr (Apache-2.0) directly instead of installing commonforms (no licence file; pulls in ultralytics).

Data: generated flattened forms (gold = AcroForm widget boxes), FUNSD (proxy gold: answer entities as value
regions, question entities as places where no field should be), SignverOD signature boxes (sample).
Checkbox state: FFDetr has no checked/unchecked class; state is read from the ink share inside each detected box.
usage: run_ffdetr.py OUTDIR"""
import glob
import io
import json
import os
import sys
import time
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from common import DATA, MODELS  # noqa: E402

CKPT = {"ffdetr": ("jbarrow/FFDetr", "56f4e4235e28dcb2953513dc020bb191a2f54cfe"),
        "ffdetr_filled": ("pdf-net/ffdetr-filled", "186c904429b94645763044c725ee73550b5995fa")}
CLS = {0: "TextBox", 1: "ChoiceButton", 2: "Signature"}
N_SIGNVER = int(os.environ.get("N_SIGNVER", "250"))
INK_THR = 0.06


def load(key):
    from huggingface_hub import hf_hub_download
    from rfdetr import RFDETRMedium
    repo, rev = CKPT[key]
    p = hf_hub_download(repo, "FFDetr.pth", revision=rev, local_dir=os.path.join(MODELS, key))
    try:
        m = RFDETRMedium(pretrain_weights=p, device="cpu")
    except Exception as e:  # noqa: BLE001
        print("plain load failed, retrying with trust_checkpoint:", type(e).__name__, str(e)[:200])
        m = RFDETRMedium(pretrain_weights=p, trust_checkpoint=True)
    return m, os.path.getsize(p)


def detect(m, pil):
    t = time.perf_counter()
    d = m.predict(pil, threshold=0.4)
    if isinstance(d, list):
        d = d[0]
    d = d.with_nms(threshold=0.1, class_agnostic=True)
    ms = (time.perf_counter() - t) * 1000
    out = [{"cls": CLS.get(int(c), str(c)), "box": [float(v) for v in b], "score": float(s)}
           for c, b, s in zip(d.class_id, d.xyxy, d.confidence)]
    return out, ms


def iou(a, b):
    i = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def ioa(a, b):
    """share of a inside b"""
    i = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return i / max(1e-6, (a[2] - a[0]) * (a[3] - a[1]))


def match(preds, golds, thr=0.5, cls=True):
    used, tp = set(), []
    for p in sorted(preds, key=lambda p: -p["score"]):
        best, bi = thr, None
        for k, g in enumerate(golds):
            if k in used or (cls and g["type"] != p["cls"]):
                continue
            v = iou(p["box"], g["box"])
            if v >= best:
                best, bi = v, k
        if bi is not None:
            used.add(bi)
            tp.append((p, golds[bi]))
    return tp


def ink(gray, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    a = gray[int(y0 + 0.2 * h):int(y1 - 0.2 * h), int(x0 + 0.2 * w):int(x1 - 0.2 * w)]
    return float((a < 128).mean()) if a.size else 0.0


def prf(tp, npred, ngold):
    p, r = tp / max(1, npred), tp / max(1, ngold)
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    import cv2
    from PIL import Image
    gen = sorted(glob.glob(os.path.join(DATA, "forms_gen", "*.json")))
    funsd = sorted(glob.glob(os.path.join(DATA, "funsd", "dataset", "*", "annotations", "*.json")))
    sv = []
    try:
        import pyarrow.parquet as pq
        files = sorted(glob.glob(os.path.join(DATA, "signverod", "**", "*.parquet"), recursive=True))
        cats = defaultdict(int)
        for f in files:
            for b in pq.ParquetFile(f).iter_batches(batch_size=8):
                for row in b.to_pylist():
                    o = row["objects"] or {}
                    for c in o.get("category", []):
                        cats[c] += 1
                    if any(c == 1 for c in o.get("category", [])) and len(sv) < N_SIGNVER:
                        sv.append(row)
                if len(sv) >= N_SIGNVER:
                    break
            if len(sv) >= N_SIGNVER:
                break
        print("signverod categories seen", dict(cats), "pages used", len(sv))
    except Exception as e:  # noqa: BLE001
        print("signverod unavailable:", e)
    res = {}
    dets_out = open(os.path.join(out, "ffdetr-dets.jsonl"), "w")
    md = ["## Forms: FFDetr (test only)", ""]
    for key in CKPT:
        m, size = load(key)
        R = {"size_mb": size / 1e6, "gen": defaultdict(lambda: defaultdict(lambda: [0, 0, 0])), "ms": [],
             "state": defaultdict(lambda: [0, 0]), "state_gold": [0, 0], "funsd": [0, 0, 0, 0, 0], "sig": [0, 0, 0]}
        for jf in gen:
            g = json.load(open(jf))
            img = cv2.cvtColor(cv2.imread(jf[:-5] + ".png"), cv2.COLOR_BGR2RGB)
            pr, ms = detect(m, Image.fromarray(img))
            R["ms"].append(ms)
            dets_out.write(json.dumps({"model": key, "ds": "gen", "id": g["id"], "dets": pr}) + "\n")
            golds = g["fields"]
            var = g["variant"]
            for t in ("TextBox", "ChoiceButton", "Signature"):
                gg = [x for x in golds if x["type"] == t]
                pp = [x for x in pr if x["cls"] == t]
                tp = match(pp, gg)
                R["gen"][var][t][0] += len(tp)
                R["gen"][var][t][1] += len(pp)
                R["gen"][var][t][2] += len(gg)
            tp = match(pr, golds, cls=False)
            R["gen"][var]["any class"][0] += len(tp)
            R["gen"][var]["any class"][1] += len(pr)
            R["gen"][var]["any class"][2] += len(golds)
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            for p, gd in match([x for x in pr if x["cls"] == "ChoiceButton"], [x for x in golds if x["type"] == "ChoiceButton"]):
                ok = (ink(gray, p["box"]) > INK_THR) == bool(gd.get("checked"))
                R["state"][var][0] += ok
                R["state"][var][1] += 1
            for gd in golds:
                if gd["type"] == "ChoiceButton" and var != "empty":
                    R["state_gold"][0] += (ink(gray, gd["box"]) > INK_THR) == bool(gd.get("checked"))
                    R["state_gold"][1] += 1
        for af in funsd:
            d = json.load(open(af, encoding="utf-8"))
            ip = af.replace(os.sep + "annotations" + os.sep, os.sep + "images" + os.sep)[:-5] + ".png"
            img = Image.open(ip).convert("RGB")
            pr, ms = detect(m, img)
            stem = os.path.splitext(os.path.basename(af))[0]
            dets_out.write(json.dumps({"model": key, "ds": "funsd", "id": stem, "dets": pr}) + "\n")
            ans = [e["box"] for e in d["form"] if e["label"] == "answer"]
            qs = [e["box"] for e in d["form"] if e["label"] == "question"]
            tb = [p for p in pr if p["cls"] == "TextBox"]
            cov = sum(1 for a in ans if any(ioa(a, p["box"]) >= 0.5 for p in tb))
            good = sum(1 for p in tb if any(ioa(a, p["box"]) >= 0.5 or iou(a, p["box"]) >= 0.3 for a in ans))
            onq = sum(1 for p in tb if any(ioa(q, p["box"]) >= 0.5 for q in qs))
            f = R["funsd"]
            f[0] += cov
            f[1] += len(ans)
            f[2] += good
            f[3] += len(tb)
            f[4] += onq
        for row in sv:
            im = row["image"]
            pil = Image.open(io.BytesIO(im["bytes"] if isinstance(im, dict) else im)).convert("RGB")
            pr, ms = detect(m, pil)
            o = row["objects"]
            gs = [[b[0], b[1], b[0] + b[2], b[1] + b[3]] for b, c in zip(o["bbox"], o["category"]) if c == 1]
            ps = [p for p in pr if p["cls"] == "Signature"]
            used = set()
            for p in ps:
                for k, gb in enumerate(gs):
                    if k not in used and iou(p["box"], gb) >= 0.3:
                        used.add(k)
                        break
            R["sig"][0] += len(used)
            R["sig"][1] += len(ps)
            R["sig"][2] += len(gs)
        res[key] = R
    dets_out.close()
    md.append("Checkpoints: jbarrow/FFDetr@56f4e42 and pdf-net/ffdetr-filled@186c904 (model cards: apache-2.0; "
              "repos ship no separate LICENSE file). Matching at IoU 0.5 with the same class unless noted.")
    md.append("")
    md.append("### Generated flattened forms (gold = AcroForm widgets before flattening)")
    md.append("")
    md.append("| model | variant | field type | P | R | F1 | gold |")
    md.append("|---|---|---|---|---|---|---|")
    js = {}
    for key, R in res.items():
        js[key] = {"size_mb": R["size_mb"], "ms_p50": sorted(R["ms"])[len(R["ms"]) // 2] if R["ms"] else None}
        for var, d in sorted(R["gen"].items()):
            for t, (tp, npd, ng) in d.items():
                p, r, f = prf(tp, npd, ng)
                js[key][f"{var}:{t}"] = {"p": p, "r": r, "f1": f, "n": ng}
                md.append(f"| {key} | {var} | {t} | {p:.3f} | {r:.3f} | {f:.3f} | {ng} |")
    md.append("")
    md.append("Checkbox state (ink share inside the detected box > 0.06; FFDetr itself has no checked/unchecked class):")
    md.append("")
    for key, R in res.items():
        s = ", ".join(f"{v} {a}/{n} ({a / max(1, n):.3f})" for v, (a, n) in sorted(R["state"].items()))
        md.append(f"- {key}: {s}; same rule on the gold boxes: {R['state_gold'][0]}/{R['state_gold'][1]}")
    md.append("")
    md.append("### FUNSD (no widget boxes: answer entities used as value regions)")
    md.append("")
    md.append("| model | answers covered (recall proxy) | TextBox boxes on an answer (precision proxy) | TextBox boxes on a question label |")
    md.append("|---|---|---|---|")
    for key, R in res.items():
        f = R["funsd"]
        md.append(f"| {key} | {f[0]}/{f[1]} = {f[0] / max(1, f[1]):.3f} | {f[2]}/{f[3]} = {f[2] / max(1, f[3]):.3f} | "
                  f"{f[4]}/{f[3]} = {f[4] / max(1, f[3]):.3f} |")
        js[key]["funsd"] = f
    md.append("")
    if sv:
        md.append(f"### Signatures (SignverOD, {len(sv)} scanned pages with signatures, IoU 0.3)")
        md.append("")
        md.append("| model | P | R | F1 |")
        md.append("|---|---|---|---|")
        for key, R in res.items():
            p, r, f = prf(*R["sig"])
            js[key]["signverod"] = {"p": p, "r": r, "f1": f, "n": R["sig"][2]}
            md.append(f"| {key} | {p:.3f} | {r:.3f} | {f:.3f} |")
        md.append("")
    md.append("CPU time per page (4 threads, torch CPU, includes pre/post-processing): " + ", ".join(
        f"{k} p50 {js[k]['ms_p50']:.0f} ms ({js[k]['size_mb']:.0f} MB checkpoint)" for k in js if js[k]["ms_p50"]))
    md.append("")
    open(os.path.join(out, "ffdetr.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    json.dump(js, open(os.path.join(out, "ffdetr.json"), "w"), indent=1)
    print("\n".join(md))
    _ = np


if __name__ == "__main__":
    main()

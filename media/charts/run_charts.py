"""Gap 2 runner. Per chart: vector extraction (synthetic PDFs) or raster tracing (PNG/JPEG), or DePlot (reference).
Writes numbers only. usage: run_charts.py ours|deplot SHARD NSHARDS OUT.jsonl"""
import json
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ocr"))
import datasets  # noqa: E402
import metrics  # noqa: E402
from common import shard  # noqa: E402

N_DEPLOT = {"synth": 200, "chartx": 250, "plotqa": 250}


def gt_view(gt):
    """Series names a reader can see: synthetic charts without a legend show no series name."""
    s = [dict(x) for x in gt["series"]]
    if gt.get("legend") is False:
        for x in s:
            x["name"] = ""
    return s


def rms_noname(gt_s, pred_s):
    import numpy as np
    from scipy.optimize import linear_sum_assignment
    if not gt_s or not pred_s:
        return metrics.rms(gt_s, pred_s)
    cost = np.zeros((len(gt_s), len(pred_s)))
    for i, g in enumerate(gt_s):
        for j, p in enumerate(pred_s):
            cost[i, j] = 1 - metrics.rms([dict(g, name="")], [dict(p, name="")])[2]
    ri, ci = linear_sum_assignment(cost)
    m = dict(zip(ci.tolist(), ri.tolist()))
    G = [dict(g, name=f"s{i}") for i, g in enumerate(gt_s)]
    Pp = [dict(p, name=f"s{m[j]}" if j in m else f"extra{j}") for j, p in enumerate(pred_s)]
    return metrics.rms(G, Pp)


def point_f1(gt, pred, tol=0.02):
    import numpy as np
    from scipy.optimize import linear_sum_assignment
    allx = [float(v) for s in gt["series"] for v in s["x"]]
    ally = [float(v) for s in gt["series"] for v in s["y"]]
    xr = (max(allx) - min(allx)) or 1.0
    yr = (max(ally) - min(ally)) or 1.0
    hit = ng = npd = 0
    for s in gt["series"]:
        ng += len(s["x"])
        q = [p for p in pred.get("series", []) if p.get("color") and metrics.color_close(p["color"], s["color"])]
        if not q:
            continue
        q = q[0]
        px = [(float(a), float(b)) for a, b in zip(q["x"], q["y"]) if isinstance(a, (int, float))]
        if not px:
            continue
        c = np.array([[max(abs(a - x) / xr, abs(b - y) / yr) for a, b in px] for x, y in zip(s["x"], s["y"])])
        ri, ci = linear_sum_assignment(c)
        hit += int(sum(c[r, k] <= tol for r, k in zip(ri, ci)))
    for p in pred.get("series", []):
        npd += len(p["y"])
    P = hit / max(1, npd)
    R = hit / max(1, ng)
    return 2 * P * R / (P + R) if P + R else 0.0


def score(it, pred):
    gt = it["gt"]
    rec = {k: it.get(k) for k in ("id", "ds", "var", "ctype", "group", "supported")}
    if pred.get("abstain"):
        rec["abstain"] = pred["abstain"]
        rec.update(rms_p=0.0, rms_r=0.0, rms_f1=0.0, rmsn_f1=0.0)
        return rec
    ps = [{"name": s.get("name", ""), "x": list(s["x"]), "y": list(s["y"]), "color": s.get("color"),
           "xi": s.get("xi")} for s in pred["series"]]
    p, r, f = metrics.rms(gt_view(gt), ps)
    rec.update(rms_p=p, rms_r=r, rms_f1=f, rmsn_f1=rms_noname(gt_view(gt), ps)[2])
    if it["ds"] == "synth":
        if gt["type"] == "scatter":
            rec["point_f1"] = point_f1(gt, pred)
        else:
            if gt["x_kind"] == "cat":
                for q in ps:
                    if q.get("xi") is not None and None not in q["xi"] and q["xi"]:
                        q["x"] = [gt["categories"][k] if 0 <= k < len(gt["categories"]) else x
                                  for k, x in zip(q["xi"], q["x"])]
            errs = metrics.point_errors(gt, {"series": ps})
            got = [e for e in errs if e is not None]
            rec["pts"] = len(errs)
            rec["pts_found"] = len(got)
            rec["within1"] = sum(1 for e in got if e <= 0.01)
            rec["within5"] = sum(1 for e in got if e <= 0.05)
            rec["med_err"] = sorted(got)[len(got) // 2] if got else None
    return rec


def run_ours(items, out):
    import engines
    import ppocr
    import raster_extract
    import vector_extract
    det = ppocr.Detector(engines.P["det_s"])
    rec_ = ppocr.Recognizer(engines.P["rec_s"], ppocr.load_dict(engines.P["dict_s"]))
    import cv2
    with open(out, "w") as f:
        for it in items:
            t = time.perf_counter()
            try:
                if it.get("var") == "vector":
                    pred = vector_extract.extract(it["path"])
                    method = "vector"
                else:
                    rgb = cv2.cvtColor(cv2.imread(it["path"]), cv2.COLOR_BGR2RGB)
                    pred = raster_extract.extract(rgb, det, rec_)
                    method = "raster"
                r = score(it, pred)
            except Exception as e:  # noqa: BLE001
                r = {k: it.get(k) for k in ("id", "ds", "var", "ctype", "group", "supported")}
                r.update(error=f"{type(e).__name__}: {e}"[:200], tb=traceback.format_exc()[-600:],
                         abstain="error", rms_p=0.0, rms_r=0.0, rms_f1=0.0, rmsn_f1=0.0)
                method = "vector" if it.get("var") == "vector" else "raster"
            r["method"] = method
            r["ms"] = (time.perf_counter() - t) * 1000
            f.write(json.dumps(r) + "\n")


def deplot_subset(items):
    out, cnt = [], {}
    for it in items:
        if it.get("var") in ("vector", "raster_150", "raster_jpeg"):
            continue
        if it["ds"] != "synth" and not it.get("supported"):
            continue
        k = it["ds"]
        if cnt.get(k, 0) < N_DEPLOT[k]:
            out.append(it)
            cnt[k] = cnt.get(k, 0) + 1
    return out


def run_deplot(items, out):
    import torch
    from PIL import Image
    from transformers import Pix2StructForConditionalGeneration, Pix2StructProcessor
    torch.set_num_threads(4)
    proc = Pix2StructProcessor.from_pretrained("google/deplot")
    model = Pix2StructForConditionalGeneration.from_pretrained("google/deplot").eval()
    with open(out, "w") as f:
        for it in items:
            t = time.perf_counter()
            try:
                im = Image.open(it["path"]).convert("RGB")
                inp = proc(images=im, text="Generate underlying data table of the figure below:", return_tensors="pt")
                with torch.no_grad():
                    ids = model.generate(**inp, max_new_tokens=512)
                txt = proc.decode(ids[0], skip_special_tokens=True)
                r = score(it, {"series": metrics.table_text_to_series(txt)})
            except Exception as e:  # noqa: BLE001
                r = {k: it.get(k) for k in ("id", "ds", "var", "ctype", "group", "supported")}
                r.update(error=f"{type(e).__name__}: {e}"[:200], abstain="error", rms_p=0.0, rms_r=0.0, rms_f1=0.0,
                         rmsn_f1=0.0)
            r["method"] = "deplot"
            r["ms"] = (time.perf_counter() - t) * 1000
            f.write(json.dumps(r) + "\n")
            f.flush()


def main():
    mode, k, n, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    items = datasets.load()
    if mode == "ours":
        run_ours(shard(items, k, n), out)
    else:
        run_deplot(shard(deplot_subset(items), k, n), out)
    print("done", mode, k, n)


if __name__ == "__main__":
    main()

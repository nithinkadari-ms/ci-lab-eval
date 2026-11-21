"""Gap 3 + FFDetr: the geometry + Hungarian label->value matcher with FFDetr field boxes as the value regions,
against the same matcher on OCR lines only. Keys are always PP-OCRv6 lines (lines inside a field box are value
text, not keys). Each matcher is fitted on its dataset's training half and scored on the other half.
  FUNSD: train = training_data, test = testing_data; entity-level pairs as in run_forms.py.
  generated forms: split by template; gold pairs = template label -> widget. OCR-only cannot pair a blank field
  (there is no text), so scores are given for filled fields and for all fields.
usage: ffdetr_match.py DETS.jsonl OUTDIR"""
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ocr"))
import run_forms as rf  # noqa: E402
from common import DATA, pfmt, sign_test, split_of  # noqa: E402


def iou(a, b):
    i = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def ioa(a, b):
    i = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return i / max(1e-6, (a[2] - a[0]) * (a[3] - a[1]))


def units(lines, dets):
    """FFDetr boxes become value units (text = OCR lines inside); remaining OCR lines are key candidates."""
    us = []
    inside = set()
    for d in dets:
        mem = [k for k, L in enumerate(lines) if ioa(L["box"], d["box"]) >= 0.6]
        inside.update(mem)
        t = " ".join(lines[k]["t"] for k in sorted(mem, key=lambda k: (lines[k]["box"][1], lines[k]["box"][0])))
        us.append({"t": t, "box": d["box"], "conf": d["score"], "unit": True, "cls": d["cls"], "mem": mem})
    keys = [dict(L, unit=False) for k, L in enumerate(lines) if k not in inside]
    return keys, us


def build(doc, mode):
    """-> combined list, key->value candidates, line height."""
    if mode == "ocr":
        allx = [dict(L, unit=False) for L in doc["lines"]]
        cands, lh = rf.candidates(allx, doc["W"])
        return allx, cands, lh
    keys, us = units(doc["lines"], doc["dets"])
    allx = keys + us
    cands, lh = rf.candidates(allx, doc["W"])
    nk = len(keys)
    cands = [(i, j, d) for i, j, d in cands if i < nk and j >= nk]
    return allx, cands, lh


def fit_eval(train, test, mode, label_fn, ent_fn):
    from sklearn.linear_model import LogisticRegression
    Xs, ys = [], []
    for d in train:
        allx, cands, lh = build(d, mode)
        if not cands:
            continue
        Xs.append(rf.feats(allx, cands, lh, d["W"]))
        ys.append(np.array([label_fn(d, allx, i, j) for i, j, _ in cands]))
    m = LogisticRegression(max_iter=4000).fit(np.vstack(Xs), np.concatenate(ys))
    best = None
    for th in np.linspace(-3, 3, 25):
        tp = npd = ng = 0
        for d in train[1::2]:
            allx, cands, lh = build(d, mode)
            pairs = rf.assign(allx, cands, m.decision_function(rf.feats(allx, cands, lh, d["W"])), th) if cands else []
            a, b, c = ent_fn(d, allx, pairs)
            tp, npd, ng = tp + a, npd + b, ng + c
        f = 2 * tp / max(1, npd + ng)
        if best is None or f > best[0]:
            best = (f, th)
    out = []
    for d in test:
        allx, cands, lh = build(d, mode)
        pairs = rf.assign(allx, cands, m.decision_function(rf.feats(allx, cands, lh, d["W"])), best[1]) if cands else []
        out.append(ent_fn(d, allx, pairs))
    return out, best[1]


def f1s(rs):
    tp, npd, ng = (sum(r[k] for r in rs) for k in range(3))
    p, r = tp / max(1, npd), tp / max(1, ng)
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def doc_f1(r):
    return 2 * r[0] / max(1, r[1] + r[2])


def main():
    dets_path, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    dets = defaultdict(dict)
    for line in open(dets_path):
        r = json.loads(line)
        dets[r["model"]][(r["ds"], r["id"])] = r["dets"]
    import engines
    import ppocr
    det = ppocr.Detector(engines.P["det_s"])
    rec = ppocr.Recognizer(engines.P["rec_s"], ppocr.load_dict(engines.P["dict_s"]))
    md = ["### FFDetr boxes as value regions for the label->value matcher", ""]
    js = {}
    # ---------------- FUNSD
    fdocs = []
    for sp in ("training_data", "testing_data"):
        for ann in sorted(glob.glob(os.path.join(DATA, "funsd", "dataset", sp, "annotations", "*.json"))):
            stem = os.path.splitext(os.path.basename(ann))[0]
            lines, W, H = rf.ocr_doc(os.path.join(DATA, "funsd", "dataset", sp, "images", stem + ".png"), det, rec)
            ents, links = rf.gt_doc(ann)
            rf.map_lines(lines, ents)
            fdocs.append({"id": stem, "split": "train" if sp == "training_data" else "test", "lines": lines,
                          "ents": ents, "links": links, "W": W, "H": H})

    def f_label(d, allx, i, j):
        a, b = allx[i], allx[j]
        ea = a.get("ent")
        eb = b.get("ent") if not b.get("unit") else unit_ent(d, b)
        return int((ea, eb) in d["links"])

    def unit_ent(d, u):
        if "ent" not in u:
            best, bi = 0.0, None
            for eid, e in d["ents"].items():
                if e["label"] != "answer":
                    continue
                v = ioa(e["box"], u["box"])
                if v > best:
                    best, bi = v, eid
            u["ent"] = bi if best >= 0.5 else None
        return u["ent"]

    def f_ent(d, allx, pairs):
        pred = set()
        bad = 0
        for i, j in pairs:
            a = allx[i].get("ent")
            b = unit_ent(d, allx[j]) if allx[j].get("unit") else allx[j].get("ent")
            if a is None or b is None or a == b:
                bad += 1
            else:
                pred.add((a, b))
        return len(pred & d["links"]), len(pred) + bad, len(d["links"])
    tr = [d for d in fdocs if d["split"] == "train"]
    te = [d for d in fdocs if d["split"] == "test"]
    base, thb = fit_eval(tr, te, "ocr", f_label, f_ent)
    md.append("FUNSD (50 test forms, entity-level pairs):")
    md.append("")
    md.append("| value regions | pair P | pair R | pair F1 | forms better / worse vs OCR only | p |")
    md.append("|---|---|---|---|---|---|")
    p, r, f = f1s(base)
    md.append(f"| OCR lines only | {p:.3f} | {r:.3f} | {f:.3f} | - | - |")
    js["funsd"] = {"ocr": [p, r, f]}
    for key in dets:
        for d in fdocs:
            d["dets"] = [x for x in dets[key].get(("funsd", d["id"]), []) if x["cls"] == "TextBox"]
        res, th = fit_eval(tr, te, "ffdetr", f_label, f_ent)
        p, r, f = f1s(res)
        w, l, pv = sign_test([doc_f1(a) - doc_f1(b) for a, b in zip(res, base)])
        js["funsd"][key] = [p, r, f, w, l, pv]
        md.append(f"| {key} TextBox boxes | {p:.3f} | {r:.3f} | {f:.3f} | {w} / {l} | {pfmt(pv)} |")
    md.append("")
    # ---------------- generated forms
    gdocs = []
    import cv2
    for jf in sorted(glob.glob(os.path.join(DATA, "forms_gen", "*.json"))):
        g = json.load(open(jf))
        rgb = cv2.cvtColor(cv2.imread(jf[:-5] + ".png"), cv2.COLOR_BGR2RGB)
        boxes = det(rgb)
        lines = []
        for b in boxes:
            c = ppocr.crop(rgb, b["quad"])
            if c is None:
                continue
            t, conf = rec.one(c)
            if t and conf >= ppocr.TEXT_SCORE:
                lines.append({"t": t, "box": b["box"], "conf": conf})
        flds = g["fields"]
        for L in lines:
            L["ent"] = None
            for k, fd in enumerate(flds):
                if ioa(L["box"], fd["label_box"]) >= 0.5:
                    L["ent"] = f"L{k}"
                    break
                if ioa(L["box"], fd["box"]) >= 0.5 and fd["type"] != "ChoiceButton":
                    L["ent"] = f"F{k}"
                    break
        filled = {(f"L{k}", f"F{k}") for k, fd in enumerate(flds) if fd["type"] != "ChoiceButton" and fd.get("value")}
        allp = {(f"L{k}", f"F{k}") for k in range(len(flds))}
        gdocs.append({"id": g["id"], "variant": g["variant"], "split": split_of(f"tpl{g['template']}"), "lines": lines,
                      "flds": flds, "filled": filled, "all": allp, "W": rgb.shape[1], "H": rgb.shape[0]})

    def g_ent_of(d, x):
        if not x.get("unit"):
            return x.get("ent")
        if "ent" not in x:
            best, bi = 0.3, None
            for k, fd in enumerate(d["flds"]):
                v = iou(x["box"], fd["box"])
                if v >= best:
                    best, bi = v, f"F{k}"
            x["ent"] = bi
        return x["ent"]

    def g_label(d, allx, i, j):
        return int((g_ent_of(d, allx[i]), g_ent_of(d, allx[j])) in d["all"])

    def g_ent(which):
        def fn(d, allx, pairs):
            gold = d[which]
            pred, bad = set(), 0
            for i, j in pairs:
                a, b = g_ent_of(d, allx[i]), g_ent_of(d, allx[j])
                if a is None or b is None or not a.startswith("L") or not b.startswith("F"):
                    bad += 1
                else:
                    pred.add((a, b))
            if which == "filled":
                pred = {x for x in pred if x in d["all"] and x in gold} | {x for x in pred if x not in d["all"]}
            return len(pred & gold), len(pred) + bad, len(gold)
        return fn
    md.append("Generated flattened forms (test templates):")
    md.append("")
    md.append("| variant | gold pairs | value regions | pair P | pair R | pair F1 | forms better / worse vs OCR only | p |")
    md.append("|---|---|---|---|---|---|---|---|")
    js["gen"] = {}
    for var in ("empty", "filled", "filled_scan"):
        ds = [d for d in gdocs if d["variant"] == var]
        tr = [d for d in ds if d["split"] == "dev"]
        te = [d for d in ds if d["split"] == "test"]
        for which in (("filled", "all") if var != "empty" else ("all",)):
            if var != "empty":
                b, _ = fit_eval(tr, te, "ocr", g_label, g_ent(which))
                p, r, f = f1s(b)
                js["gen"][f"{var}:{which}:ocr"] = [p, r, f]
                md.append(f"| {var} | {which} fields | OCR lines only | {p:.3f} | {r:.3f} | {f:.3f} | - | - |")
            else:
                b = None
                md.append(f"| {var} | all fields | OCR lines only | - | 0.000 | - | - | - |")
            for key in dets:
                for d in ds:
                    d["dets"] = dets[key].get(("gen", d["id"]), [])
                res, _ = fit_eval(tr, te, "ffdetr", g_label, g_ent(which))
                p, r, f = f1s(res)
                if b is not None:
                    w, l, pv = sign_test([doc_f1(x) - doc_f1(y) for x, y in zip(res, b)])
                    cmp_ = f"{w} / {l} | {pfmt(pv)}"
                else:
                    cmp_ = "- | -"
                js["gen"][f"{var}:{which}:{key}"] = [p, r, f]
                md.append(f"| {var} | {which} fields | {key} boxes | {p:.3f} | {r:.3f} | {f:.3f} | {cmp_} |")
    md.append("")
    open(os.path.join(out, "ffdetr_match.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    json.dump(js, open(os.path.join(out, "ffdetr_match.json"), "w"), indent=1)
    print("\n".join(md))


if __name__ == "__main__":
    main()

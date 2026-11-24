"""Milestone 12: weights for the geometry + Hungarian form matcher that can ship.

Round 4 fitted the matcher's logistic scores on FUNSD's training forms. FUNSD is research-only, so weights fitted
on it cannot ship. This run fits the same features (run_forms.feats, unchanged) on the generated forms
(gen_forms.py: our own templates, empty / filled / filled_scan, PP-OCRv6 small lines) and compares on the FUNSD
test forms (internal testing only):
  nn          rule key typing + nearest line (round-4 baseline)
  geo_funsd   fitted on FUNSD training forms (round-4 method; for comparison only, never shipped)
  geo_gen     fitted on generated forms, threshold picked on generated forms only (the shipping candidate)
Writes weights for geo_gen (and geo_funsd for comparison) and 12 generated forms' OCR lines with the Python
matcher's outputs, for the Rust equality tests. usage: m12_forms.py OUTDIR"""
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

FEATURES = ["bias", "right", "below", "gap", "gap_sq", "dy_center", "dx_left", "key_a", "key_b", "colon_a",
            "colon_b", "digit_a", "digit_b", "date_b", "phone_b", "amount_b", "date_pair", "phone_pair",
            "amount_pair", "number_pair", "words_a", "words_b", "alpha_a", "alpha_b", "lower_b", "upper_a",
            "rank", "rank0", "conf_a", "conf_b", "dx_page"]


def ioa(a, b):
    i = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return i / max(1e-6, (a[2] - a[0]) * (a[3] - a[1]))


def ocr_image(rgb, det, rec, ppocr):
    lines = []
    for b in det(rgb):
        c = ppocr.crop(rgb, b["quad"])
        if c is None:
            continue
        t, conf = rec.one(c)
        if t and conf >= ppocr.TEXT_SCORE:
            lines.append({"t": t, "box": [float(v) for v in b["box"]], "conf": float(conf)})
    return lines


def gen_docs(det, rec, ppocr):
    import cv2
    docs = []
    for jf in sorted(glob.glob(os.path.join(DATA, "forms_gen", "*.json"))):
        g = json.load(open(jf))
        rgb = cv2.cvtColor(cv2.imread(jf[:-5] + ".png"), cv2.COLOR_BGR2RGB)
        lines = ocr_image(rgb, det, rec, ppocr)
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
        links = {(f"L{k}", f"F{k}") for k, fd in enumerate(flds) if fd["type"] != "ChoiceButton" and fd.get("value")}
        ents = {}
        for k, fd in enumerate(flds):
            ents[f"L{k}"] = {"label": "question", "text": fd["label"]}
            if fd["type"] != "ChoiceButton":
                ents[f"F{k}"] = {"label": "answer", "text": fd.get("value") or ""}
        d = {"id": g["id"], "variant": g["variant"], "template": g["template"],
             "split": split_of(f"tpl{g['template']}"), "lines": lines, "ents": ents, "links": links,
             "W": rgb.shape[1], "H": rgb.shape[0]}
        d["cands"], d["lh"] = rf.candidates(lines, d["W"])
        docs.append(d)
    return docs


def funsd_docs(det, rec):
    docs = []
    for sp in ("training_data", "testing_data"):
        for ann in sorted(glob.glob(os.path.join(DATA, "funsd", "dataset", sp, "annotations", "*.json"))):
            stem = os.path.splitext(os.path.basename(ann))[0]
            lines, W, H = rf.ocr_doc(os.path.join(DATA, "funsd", "dataset", sp, "images", stem + ".png"), det, rec)
            ents, links = rf.gt_doc(ann)
            rf.map_lines(lines, ents)
            d = {"id": stem, "split": "train" if sp == "training_data" else "test", "lines": lines, "ents": ents,
                 "links": links, "W": W, "H": H}
            d["cands"], d["lh"] = rf.candidates(lines, W)
            docs.append(d)
    return docs


def xy(d):
    X = rf.feats(d["lines"], d["cands"], d["lh"], d["W"])
    y = np.array([int((d["lines"][i]["ent"], d["lines"][j]["ent"]) in d["links"]) for i, j, _ in d["cands"]])
    return X, y


def fit(train, tune):
    from sklearn.linear_model import LogisticRegression
    Xs, ys = zip(*[xy(d) for d in train if d["cands"]])
    m = LogisticRegression(max_iter=4000, C=1.0, class_weight=None).fit(np.vstack(Xs), np.concatenate(ys))
    best = None
    for th in np.linspace(-3, 3, 25):
        rs = [rf.evaluate(d, rf.assign(d["lines"], d["cands"], m.decision_function(xy(d)[0]), th))
              for d in tune if d["cands"]]
        f = rf.prf(rs)[2]
        if best is None or f > best[0]:
            best = (f, float(th))
    return m, best[1]


def score(m, th, docs):
    out = []
    for d in docs:
        if not d["cands"]:
            out.append(rf.evaluate(d, []))
            continue
        out.append(rf.evaluate(d, rf.assign(d["lines"], d["cands"], m.decision_function(xy(d)[0]), th)))
    return out


def nn(docs):
    out = []
    for d in docs:
        L = d["lines"]
        key = lambda i: rf.keyness(L[i]["t"]) > 0  # noqa: E731
        out.append(rf.evaluate(d, rf.nearest(L, d["cands"], key, lambda j: not key(j))))
    return out


def row(name, rs):
    p, r, f = rf.prf(rs)
    bl = sum(x["filled"] for x in rs) / max(1, sum(x["blank"] for x in rs))
    rp, rr, _ = rf.prf(rs, "rep_tp", "rep_np", "rep_ng")
    return f"| {name} | {p:.3f} | {r:.3f} | {f:.3f} | {bl:.3f} | {rp:.3f} / {rr:.3f} |", \
        {"p": p, "r": r, "f1": f, "blank_filled": bl, "rep_p": rp, "rep_r": rr}


def f1_of(r):
    p = r["tp"] / max(1, r["np"])
    q = r["tp"] / max(1, r["ng"])
    return 2 * p * q / (p + q) if p + q else 0.0


def weights(m, th, source):
    return {"source": source, "features": FEATURES, "coef": [float(v) for v in m.coef_[0]],
            "intercept": float(m.intercept_[0]), "threshold": th, "big_cost": 1e6}


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    import engines
    import ppocr
    det = ppocr.Detector(engines.P["det_s"])
    rec = ppocr.Recognizer(engines.P["rec_s"], ppocr.load_dict(engines.P["dict_s"]))
    gdocs = gen_docs(det, rec, ppocr)
    fdocs = funsd_docs(det, rec)
    ftrain = [d for d in fdocs if d["split"] == "train"]
    ftest = [d for d in fdocs if d["split"] == "test"]
    gdev = [d for d in gdocs if d["split"] == "dev"]
    gtest = [d for d in gdocs if d["split"] == "test"]
    m_f, th_f = fit(ftrain, [d for k, d in enumerate(ftrain) if k % 2 == 1])
    m_g, th_g = fit(gdocs, gdocs)
    m_gd, th_gd = fit(gdev, gdev)
    res = {"nn": nn(ftest), "geo_funsd": score(m_f, th_f, ftest), "geo_gen": score(m_g, th_g, ftest)}
    md = ["## Milestone 12: shippable weights for the form matcher", "",
          f"Generated forms: {len(gdocs)} images ({len(gdev)} dev / {len(gtest)} test by template). "
          f"FUNSD test: {len(ftest)} forms. Thresholds: geo_funsd {th_f:.2f} (FUNSD train half), "
          f"geo_gen {th_g:.2f} (generated forms).", "",
          "FUNSD test (50 forms, PP-OCRv6 small lines, entity-level pairs):", "",
          "| method | pair P | pair R | pair F1 | blanks wrongly filled | repeated-label P / R |",
          "|---|---|---|---|---|---|"]
    summary = {}
    for k, rs in res.items():
        line, s = row(k, rs)
        md.append(line)
        summary[k] = s
    md += ["", "| A vs B (per-form F1) | A better | B better | p |", "|---|---|---|---|"]
    sig = {}
    for a, b in [("geo_gen", "nn"), ("geo_gen", "geo_funsd"), ("geo_funsd", "nn")]:
        w, l, p = sign_test([f1_of(x) - f1_of(y) for x, y in zip(res[a], res[b])])
        sig[f"{a}>{b}"] = {"w": w, "l": l, "p": p}
        md.append(f"| {a} vs {b} | {w} | {l} | {pfmt(p)} |")
    md += ["", "Generated forms, held-out templates (fitted on dev templates only):", "",
           "| variant | method | pair P | pair R | pair F1 | blanks wrongly filled | repeated-label P / R |",
           "|---|---|---|---|---|---|---|"]
    for var in ("empty", "filled", "filled_scan"):
        ds = [d for d in gtest if d["variant"] == var]
        for name, rs in (("nn", nn(ds)), ("geo_gen_dev", score(m_gd, th_gd, ds))):
            line, s = row(name, rs)
            md.append(f"| {var} " + line)
            summary[f"gen_{var}_{name}"] = s
    md.append("")
    open(os.path.join(out, "m12_forms.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    json.dump({"summary": summary, "sig": sig}, open(os.path.join(out, "m12_forms.json"), "w"), indent=1)
    json.dump(weights(m_g, th_g, "generated forms (gen_forms.py), all variants"),
              open(os.path.join(out, "form_matcher_gen.json"), "w"), indent=1)
    json.dump(weights(m_f, th_f, "FUNSD training forms (research-only: internal comparison, never shipped)"),
              open(os.path.join(out, "form_matcher_funsd.json"), "w"), indent=1)
    samples = []
    for d in sorted(gtest, key=lambda d: d["id"])[:12]:
        X = rf.feats(d["lines"], d["cands"], d["lh"], d["W"]) if d["cands"] else np.zeros((0, len(FEATURES)))
        s = m_g.decision_function(X) if d["cands"] else np.zeros(0)
        pairs = rf.assign(d["lines"], d["cands"], s, th_g) if d["cands"] else []
        samples.append({"id": d["id"], "W": d["W"], "H": d["H"],
                        "lines": [{"t": L["t"], "box": L["box"], "conf": L["conf"]} for L in d["lines"]],
                        "cands": [[i, j, k] for i, j, k in d["cands"]], "lh": d["lh"],
                        "feats": X.tolist(), "scores": [float(v) for v in s],
                        "pairs": [[int(i), int(j)] for i, j in pairs]})
    json.dump(samples, open(os.path.join(out, "form_samples_gen.json"), "w"))
    print("\n".join(md))


if __name__ == "__main__":
    main()

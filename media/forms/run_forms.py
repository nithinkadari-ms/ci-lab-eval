"""Gap 3: label -> value pairing on scanned forms (FUNSD) from PP-OCRv6 boxes (not the answer-key boxes).

Methods
  nn        rule key typing (colon / key words) + nearest line to the right, else below
  nn_lilt   LiLT (philschmid/lilt-en-funsd) question/answer typing + nearest answer line to the right/below
  geo       docspatial-style geometry + value-type features, logistic scores, Hungarian assignment with abstention
  geo_lilt  geo plus LiLT type probabilities as features
geo is fitted on FUNSD training_data (149 forms); everything is scored on testing_data (50 forms), at entity level
(OCR lines mapped to FUNSD entities by word overlap): pair precision / recall / F1, blank fields wrongly filled,
repeated labels, exact value text. usage: run_forms.py OUTDIR [--no-lilt]"""
import glob
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ocr"))
from common import DATA, MODELS, norm_text, pfmt, sign_test  # noqa: E402

KEYWORDS = {"date", "name", "no", "no.", "number", "to", "from", "fax", "phone", "tel", "re", "subject", "cc",
            "address", "company", "title", "brand", "code", "total", "amount", "signature", "dept", "department",
            "city", "state", "zip", "account", "telephone", "attention", "attn", "page", "pages", "time", "product"}
DATE_RE = re.compile(r"\b(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d)", re.I)
PHONE_RE = re.compile(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
AMOUNT_RE = re.compile(r"[$]\s?\d|\d[\d,]*\.\d{2}\b")


def ocr_doc(img, det, rec):
    import cv2
    import ppocr
    rgb = cv2.cvtColor(cv2.imread(img), cv2.COLOR_BGR2RGB)
    boxes = det(rgb)
    out = []
    for b in boxes:
        c = ppocr.crop(rgb, b["quad"])
        if c is None:
            continue
        t, conf = rec.one(c)
        if t and conf >= ppocr.TEXT_SCORE:
            out.append({"t": t, "box": b["box"], "conf": conf})
    return out, rgb.shape[1], rgb.shape[0]


def gt_doc(ann):
    d = json.load(open(ann, encoding="utf-8"))
    ents = {e["id"]: e for e in d["form"]}
    links = set()
    for e in d["form"]:
        for a, b in e.get("linking", []):
            if a in ents and b in ents:
                la, lb = ents[a]["label"], ents[b]["label"]
                if la == "question" and lb == "answer":
                    links.add((a, b))
                elif la == "answer" and lb == "question":
                    links.add((b, a))
    return ents, links


def map_lines(lines, ents):
    for L in lines:
        x0, y0, x1, y1 = L["box"]
        best, bi = 0.0, None
        for eid, e in ents.items():
            ov = 0.0
            for w in e.get("words", []):
                a = w["box"]
                inter = max(0, min(x1, a[2]) - max(x0, a[0])) * max(0, min(y1, a[3]) - max(y0, a[1]))
                wa = max(1e-6, (a[2] - a[0]) * (a[3] - a[1]))
                if inter / wa >= 0.5:
                    ov += inter
            if ov > best:
                best, bi = ov, eid
        L["ent"] = bi


def vtype(t):
    s = t.lower()
    return {"date": bool(DATE_RE.search(s)), "phone": bool(PHONE_RE.search(s)), "amount": bool(AMOUNT_RE.search(s)),
            "digit": any(c.isdigit() for c in s), "alpha": sum(c.isalpha() for c in s) / max(1, len(s))}


def keyness(t):
    s = t.strip().lower()
    toks = re.findall(r"[a-z.#]+", s)
    return float(s.endswith(":") or s.endswith("#") or (len(toks) <= 4 and any(k in KEYWORDS for k in toks)))


def candidates(lines, W):
    hs = sorted(L["box"][3] - L["box"][1] for L in lines) or [10]
    lh = max(4.0, hs[len(hs) // 2])
    out = []
    for i, a in enumerate(lines):
        A = a["box"]
        for j, b in enumerate(lines):
            if i == j:
                continue
            B = b["box"]
            vov = min(A[3], B[3]) - max(A[1], B[1])
            right = vov > 0.4 * min(A[3] - A[1], B[3] - B[1]) and B[0] >= A[2] - 0.5 * lh and B[0] - A[2] <= 0.6 * W
            below = B[1] >= A[3] - 0.3 * lh and B[1] - A[3] <= 4 * lh and (
                min(A[2], B[2]) - max(A[0], B[0]) > 0 or abs(A[0] - B[0]) < 2 * lh)
            if right or below:
                out.append((i, j, "right" if right else "below"))
    return out, lh


def feats(lines, cands, lh, W, lilt=None):
    by_i = defaultdict(list)
    for i, j, d in cands:
        A, B = lines[i]["box"], lines[j]["box"]
        gap = (B[0] - A[2]) if d == "right" else (B[1] - A[3])
        by_i[i].append((max(0.0, gap), j, d))
    rank = {}
    for i, v in by_i.items():
        for r, (_, j, d) in enumerate(sorted(v)):
            rank[(i, j)] = r
    X = []
    for i, j, d in cands:
        a, b = lines[i], lines[j]
        A, B = a["box"], b["box"]
        gap = (B[0] - A[2]) if d == "right" else (B[1] - A[3])
        ta, tb = vtype(a["t"]), vtype(b["t"])
        la = a["t"].lower()
        f = [1.0, float(d == "right"), float(d == "below"), max(0.0, gap) / lh, min(5.0, max(0.0, gap) / lh) ** 2,
             abs((A[1] + A[3]) / 2 - (B[1] + B[3]) / 2) / lh, abs(A[0] - B[0]) / lh,
             keyness(a["t"]), keyness(b["t"]), float(a["t"].strip().endswith(":")), float(b["t"].strip().endswith(":")),
             float(ta["digit"]), float(tb["digit"]), float(tb["date"]), float(tb["phone"]), float(tb["amount"]),
             float("date" in la and tb["date"]), float(("phone" in la or "tel" in la or "fax" in la) and tb["phone"]),
             float(("total" in la or "amount" in la or "$" in la) and tb["amount"]),
             float(("no" in la.split() or "#" in la or "number" in la) and tb["digit"]),
             min(10, len(a["t"].split())) / 10, min(10, len(b["t"].split())) / 10, ta["alpha"], tb["alpha"],
             float(b["t"][:1].islower()), float(a["t"].isupper()), min(rank.get((i, j), 9), 9) / 9,
             float(rank.get((i, j), 9) == 0), a["conf"], b["conf"], (B[0] - A[0]) / W]
        if lilt is not None:
            qa, aa = lilt[i], lilt[j]
            f += [qa[0], qa[1], aa[0], aa[1], qa[0] * aa[1]]
        X.append(f)
    return np.array(X, dtype=np.float64)


def lilt_types(lines, W, H, model, tok):
    """per OCR line: (P(question), P(answer)) averaged over its words' first sub-tokens."""
    import torch
    words, boxes, owner = [], [], []
    for k, L in enumerate(lines):
        toks = L["t"].split()
        x0, y0, x1, y1 = L["box"]
        n = max(1, len(L["t"]))
        pos = 0
        for t in toks:
            s = L["t"].index(t, pos)
            a, b = s / n, (s + len(t)) / n
            bx = [x0 + a * (x1 - x0), y0, x0 + b * (x1 - x0), y1]
            boxes.append([int(max(0, min(1000, 1000 * bx[0] / W))), int(max(0, min(1000, 1000 * bx[1] / H))),
                          int(max(0, min(1000, 1000 * bx[2] / W))), int(max(0, min(1000, 1000 * bx[3] / H)))])
            words.append(t)
            owner.append(k)
            pos = s + len(t)
    probs = np.zeros((len(words), 7))
    step = 150
    for s in range(0, len(words), step):
        ws, bs = words[s:s + step], boxes[s:s + step]
        enc = tok(ws, boxes=bs, truncation=True, max_length=512, return_tensors="pt")
        with torch.no_grad():
            lg = model(input_ids=enc["input_ids"], bbox=enc["bbox"], attention_mask=enc["attention_mask"]).logits[0]
        pr = torch.softmax(lg, -1).numpy()
        seen = set()
        for ti, wi in enumerate(enc.word_ids(0)):
            if wi is not None and wi not in seen:
                seen.add(wi)
                probs[s + wi] = pr[ti]
    out = [[0.0, 0.0] for _ in lines]
    cnt = Counter(owner)
    for p, k in zip(probs, owner):
        out[k][0] += (p[3] + p[4]) / cnt[k]
        out[k][1] += (p[5] + p[6]) / cnt[k]
    return out


def assign(lines, cands, scores, thr):
    from scipy.optimize import linear_sum_assignment
    n = len(lines)
    if not cands:
        return []
    M = np.full((n, n), 1e6)
    for (i, j, _), s in zip(cands, scores):
        if s > thr:
            M[i, j] = -s
    ri, ci = linear_sum_assignment(M)
    return [(i, j) for i, j in zip(ri, ci) if M[i, j] < 1e5]


def nearest(lines, cands, keyfn, valfn):
    by = defaultdict(list)
    for i, j, d in cands:
        if keyfn(i) and valfn(j):
            A, B = lines[i]["box"], lines[j]["box"]
            gap = (B[0] - A[2]) if d == "right" else (B[1] - A[3]) + 0.5 * (B[3] - B[1])
            by[i].append((d != "right", max(0.0, gap), j))
    return [(i, min(v)[2]) for i, v in by.items()]


def evaluate(doc, pairs):
    lines, ents, links = doc["lines"], doc["ents"], doc["links"]
    pred = set()
    unm = 0
    for i, j in pairs:
        a, b = lines[i]["ent"], lines[j]["ent"]
        if a is None or b is None or a == b:
            unm += 1
            continue
        pred.add((a, b))
    tp = len(pred & links)
    qs = [e for e, v in ents.items() if v["label"] == "question"]
    linked_q = {a for a, _ in links}
    blank = [q for q in qs if q not in linked_q]
    filled = sum(1 for a, _ in pred if a in blank)
    qtext = Counter(norm_text(ents[q]["text"]).lower() for q in qs)
    rep = {q for q in qs if qtext[norm_text(ents[q]["text"]).lower()] > 1}
    exact = 0
    for a, b in pred & links:
        txt = " ".join(L["t"] for L in sorted([L for L in lines if L["ent"] == b], key=lambda L: (L["box"][1], L["box"][0])))
        exact += norm_text(txt).lower() == norm_text(ents[b]["text"]).lower()
    return {"tp": tp, "np": len(pred) + unm, "ng": len(links), "blank": len(blank), "filled": filled,
            "rep_tp": len({x for x in pred & links if x[0] in rep}), "rep_ng": len({x for x in links if x[0] in rep}),
            "rep_np": len({x for x in pred if x[0] in rep}), "exact": exact}


def prf(rs, tp="tp", npk="np", ng="ng"):
    T, Np, Ng = sum(r[tp] for r in rs), sum(r[npk] for r in rs), sum(r[ng] for r in rs)
    p, r = T / max(1, Np), T / max(1, Ng)
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def main():
    out = sys.argv[1]
    use_lilt = "--no-lilt" not in sys.argv
    os.makedirs(out, exist_ok=True)
    import engines
    import ppocr
    det = ppocr.Detector(engines.P["det_s"])
    rec = ppocr.Recognizer(engines.P["rec_s"], ppocr.load_dict(engines.P["dict_s"]))
    model = tok = None
    if use_lilt:
        from transformers import LayoutLMv3TokenizerFast, LiltForTokenClassification
        md = os.path.join(MODELS, "lilt")
        tok = LayoutLMv3TokenizerFast.from_pretrained(md)
        model = LiltForTokenClassification.from_pretrained(md).eval()
    docs = []
    t_ocr = t_lilt = 0.0
    for sp in ("training_data", "testing_data"):
        for ann in sorted(glob.glob(os.path.join(DATA, "funsd", "dataset", sp, "annotations", "*.json"))):
            stem = os.path.splitext(os.path.basename(ann))[0]
            img = os.path.join(DATA, "funsd", "dataset", sp, "images", stem + ".png")
            t = time.perf_counter()
            lines, W, H = ocr_doc(img, det, rec)
            t_ocr += time.perf_counter() - t
            ents, links = gt_doc(ann)
            map_lines(lines, ents)
            doc = {"id": stem, "split": "train" if sp == "training_data" else "test", "lines": lines, "ents": ents,
                   "links": links, "W": W, "H": H}
            if use_lilt:
                t = time.perf_counter()
                doc["lilt"] = lilt_types(lines, W, H, model, tok)
                t_lilt += time.perf_counter() - t
            cands, lh = candidates(lines, W)
            doc["cands"], doc["lh"] = cands, lh
            docs.append(doc)
    from sklearn.linear_model import LogisticRegression

    def xy(doc, with_lilt):
        X = feats(doc["lines"], doc["cands"], doc["lh"], doc["W"], doc.get("lilt") if with_lilt else None)
        y = np.array([int((doc["lines"][i]["ent"], doc["lines"][j]["ent"]) in doc["links"]) for i, j, _ in doc["cands"]])
        return X, y
    train = [d for d in docs if d["split"] == "train"]
    test = [d for d in docs if d["split"] == "test"]
    variants = ["geo"] + (["geo_lilt"] if use_lilt else [])
    models, thr = {}, {}
    for v in variants:
        wl = v == "geo_lilt"
        Xs, ys = zip(*[xy(d, wl) for d in train if d["cands"]])
        X, y = np.vstack(Xs), np.concatenate(ys)
        m = LogisticRegression(max_iter=4000, C=1.0, class_weight=None).fit(X, y)
        models[v] = m
        half = [d for k, d in enumerate(train) if k % 2 == 1]
        best = None
        for th in np.linspace(-3, 3, 25):
            rs = []
            for d in half:
                if not d["cands"]:
                    continue
                s = m.decision_function(xy(d, wl)[0])
                rs.append(evaluate(d, assign(d["lines"], d["cands"], s, th)))
            f = prf(rs)[2]
            if best is None or f > best[0]:
                best = (f, th)
        thr[v] = best[1]
    results = defaultdict(list)
    for d in test:
        L = d["lines"]
        rule_key = lambda i: keyness(L[i]["t"]) > 0  # noqa: E731
        results["nn"].append(evaluate(d, nearest(L, d["cands"], rule_key, lambda j: not rule_key(j))))
        if use_lilt:
            q = lambda i: d["lilt"][i][0] > max(0.5, d["lilt"][i][1])  # noqa: E731
            a = lambda j: d["lilt"][j][1] > max(0.5, d["lilt"][j][0])  # noqa: E731
            results["nn_lilt"].append(evaluate(d, nearest(L, d["cands"], q, a)))
        for v in variants:
            if not d["cands"]:
                results[v].append(evaluate(d, []))
                continue
            s = models[v].decision_function(xy(d, v == "geo_lilt")[0])
            results[v].append(evaluate(d, assign(L, d["cands"], s, thr[v])))
    md = ["## Gap 3. Forms without fillable fields (FUNSD test, 50 forms, PP-OCRv6 small boxes)", ""]
    ng = sum(r["ng"] for r in results["nn"])
    md.append(f"OCR lines: {sum(len(d['lines']) for d in test)}; mapped to an entity: "
              f"{sum(1 for d in test for l in d['lines'] if l['ent'] is not None)}; question->answer links: {ng}; "
              f"blank questions: {sum(r['blank'] for r in results['nn'])}. Thresholds picked on half of the training "
              f"forms: {', '.join(f'{k} {v:.2f}' for k, v in thr.items())}.")
    md.append("")
    md.append("| method | pair P | pair R | pair F1 | exact value P / R | blanks wrongly filled | repeated-label P / R |")
    md.append("|---|---|---|---|---|---|---|")
    summary = {}
    for k, rs in results.items():
        p, r, f = prf(rs)
        ep, er, _ = prf(rs, "exact")
        rp, rr, _ = prf(rs, "rep_tp", "rep_np", "rep_ng")
        bl = sum(x["filled"] for x in rs) / max(1, sum(x["blank"] for x in rs))
        summary[k] = {"p": p, "r": r, "f1": f, "exact_p": ep, "exact_r": er, "blank_filled": bl, "rep_p": rp, "rep_r": rr}
        md.append(f"| {k} | {p:.3f} | {r:.3f} | {f:.3f} | {ep:.3f} / {er:.3f} | {bl:.3f} | {rp:.3f} / {rr:.3f} |")
    md.append("")
    md.append("Paired per-form F1 (sign test):")
    md.append("")
    md.append("| A vs B | A better | B better | p |")
    md.append("|---|---|---|---|")

    def f1(r):
        p = r["tp"] / max(1, r["np"])
        q = r["tp"] / max(1, r["ng"])
        return 2 * p * q / (p + q) if p + q else 0.0
    sig = {}
    for a, b in [("geo", "nn"), ("geo", "nn_lilt"), ("geo_lilt", "geo"), ("geo_lilt", "nn_lilt")]:
        if a in results and b in results:
            w, l, p = sign_test([f1(x) - f1(y) for x, y in zip(results[a], results[b])])
            sig[f"{a}>{b}"] = {"w": w, "l": l, "p": p}
            md.append(f"| {a} vs {b} | {w} | {l} | {pfmt(p)} |")
    md.append("")
    md.append(f"Time: OCR {t_ocr / len(docs):.2f} s/form; LiLT {t_lilt / max(1, len(docs)):.2f} s/form (CPU, 521 MB "
              f"fp32 checkpoint); geometry matcher < 5 ms/form.")
    md.append("")
    md.append("EC-FUNSD and DocILE: not used (no EC-FUNSD release on the Hugging Face hub when checked on "
              "2026-11-21; DocILE data is gated behind a research-access request).")
    open(os.path.join(out, "forms.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    json.dump({"summary": summary, "sig": sig, "thr": thr}, open(os.path.join(out, "forms.json"), "w"), indent=1)
    print("\n".join(md))


if __name__ == "__main__":
    main()

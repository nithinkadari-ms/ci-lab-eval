"""Tester round 2: the form matcher refitted with nothing taken from FUNSD.

FUNSD is research-only, so it may not shape anything shipped. The shipped matcher (m12_forms_b.py simulator v2,
C = 0.01) had its regularisation chosen with FUNSD training forms as validation, its label-word list (KEYWORDS:
"brand", "product", "attn", ...) came from the FUNSD experiment script, and the simulator's labels, names and
dates imitated FUNSD's forms. Here:

* KEYWORDS is a documented generic list: the words of the HTML Living Standard's autofill field names and their
  descriptions for people, organizations, addresses and contacts (WHATWG HTML, "Autofilling form controls: the
  autocomplete attribute"), plus the label words of the value types the matcher itself recognises (dates, times,
  phone numbers, amounts, numbers) and "signature".
* The simulator (m12_forms_b.sim_doc, unchanged layout code) uses generic labels, names, cities and years of our
  own, half of them without a keyword, so the keyword feature is not a perfect label detector.
* Rule fixed before the run: simulated forms are split 60 / 20 / 20 by seed (fit / select / test). For each C in
  the grid the threshold is picked on the select split (best pair F1); C is the one with the best select-split
  pair F1 among those whose share of blanks wrongly filled is not above the nearest-label rule's on the select
  split (if none qualifies, the best F1). The test split and FUNSD test (evaluation only, never used to choose)
  are reported; the shipped round-b weights (old keywords) are scored for comparison.

usage: t2_forms_clean.py OUTDIR [N_SIM] [OLD_WEIGHTS_JSON]"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ocr"))
import m12_forms as m12  # noqa: E402
import m12_forms_b as b  # noqa: E402
import run_forms as rf  # noqa: E402
from common import pfmt, sign_test  # noqa: E402

OLD_KEYWORDS = set(rf.KEYWORDS)
AUTOFILL = ["name", "title", "prefix", "suffix", "nickname", "username", "password", "company", "organization",
            "address", "street", "city", "town", "state", "province", "country", "postal", "zip", "code",
            "telephone", "tel", "email", "birthday", "gender", "sex", "language", "url", "photo", "currency",
            "amount"]
VALUE_TYPES = ["date", "time", "phone", "total", "price", "number", "no", "no.", "signature"]
KEYWORDS = set(AUTOFILL) | set(VALUE_TYPES)

LABELS = ["Name", "Full name", "First name", "Last name", "Date", "Date of birth", "Address", "Street address",
          "City", "State", "Postal code", "Country", "Phone", "Telephone", "Mobile", "Email", "Company",
          "Organization", "Job title", "Signature", "Total", "Total due", "Amount", "Unit price", "Quantity",
          "Invoice number", "Order No.", "Account number", "Reference", "Customer ID", "Policy number",
          "Department", "Manager", "Approved by", "Requested by", "Start date", "End date", "Project",
          "Description", "Remarks", "Notes", "Gender", "Nationality", "Occupation", "Employer",
          "Emergency contact", "Relationship", "Payment method", "Due date", "Ship to", "Bill to", "Tax ID",
          "Website", "Insurance provider", "Member ID", "Vehicle", "Registration", "Model", "Serial number",
          "Location", "Time", "Duration", "Room", "Event", "Supervisor", "Purpose", "Destination", "Weight",
          "Colour", "Size", "Status", "Category", "Priority", "Language", "Currency", "Witness"]
NAMES = ["Alex Morgan", "Priya Shah", "Daniel Okafor", "Maria Rossi", "Chen Wei", "Laura Becker", "Omar Haddad",
         "Sofia Lind", "J. Martinez", "K. O'Brien", "H. Tanaka", "N. Kowalczyk", "R. Silva", "E. Dubois"]
CITIES = ["Springfield", "Riverton", "Lakeside", "Fairview", "Greenville", "Hillcrest", "Westbrook", "Eastport",
          "Northfield"]
PERSON_LABELS = {"name", "full name", "first name", "last name", "manager", "approved by", "requested by",
                 "emergency contact", "supervisor", "witness", "signature"}
PLACE_LABELS = {"city", "address", "street address", "state", "country", "location", "destination"}


def value_text(r, label):
    l = label.lower()
    if "date" in l or l in ("time", "birth"):
        y = r.randint(1990, 2030)
        return r.choice([f"{r.randint(1, 12)}/{r.randint(1, 28)}/{y}", f"{r.randint(1, 28)}.{r.randint(1, 12)}.{y}",
                         f"{r.choice(['January', 'March', 'June', 'Sept.', 'Oct', 'December'])} {r.randint(1, 28)}, {y}",
                         f"{y}-{r.randint(1, 12):02d}-{r.randint(1, 28):02d}", f"{r.randint(1, 12)}:{r.randint(0, 59):02d}"])
    if "phone" in l or "tel" in l or "mobile" in l:
        return r.choice([f"({r.randint(200, 999)}) {r.randint(200, 999)}-{r.randint(1000, 9999)}",
                         f"{r.randint(200, 999)}-{r.randint(200, 999)}-{r.randint(1000, 9999)}",
                         f"+{r.randint(1, 99)} {r.randint(10, 999)} {r.randint(100000, 9999999)}"])
    if any(w in l for w in ("total", "amount", "price", "cost")):
        return r.choice([f"${r.randint(1, 99999):,}.{r.randint(0, 99):02d}", f"{r.randint(1, 9999):,}.{r.randint(0, 99):02d}",
                         f"EUR {r.randint(1, 999)}"])
    if "no" in l.split() or "no." in l or "number" in l or "id" in l.split() or "quantity" in l:
        return r.choice([str(r.randint(1, 99)), f"{r.randint(100, 99999)}", f"{r.choice('ABCDEFGHK')}{r.randint(100, 9999)}",
                         f"{r.randint(1000, 9999)}-{r.randint(10, 99)}"])
    if l == "email":
        return f"{r.choice(['info', 'a.morgan', 'office', 'p.shah'])}@{r.choice(['example.com', 'mail.org'])}"
    if l in PERSON_LABELS:
        return r.choice(NAMES)
    if l in PLACE_LABELS:
        if "address" in l:
            return f"{r.randint(1, 999)} {r.choice(['Main St.', 'Oak Ave', 'Park Road', 'Mill Lane'])}"
        return r.choice(CITIES)
    n = r.randint(1, 5)
    t = " ".join(r.choice(b.WORDS) for _ in range(n))
    return t if r.random() < 0.5 else t.upper()


def use_vocabulary(keywords):
    rf.KEYWORDS.clear()
    rf.KEYWORDS.update(keywords)


def scores_with(weights, docs):
    coef = np.array(weights["coef"])
    out = []
    for d in docs:
        if not d["cands"]:
            out.append(rf.evaluate(d, []))
            continue
        s = m12.xy(d)[0] @ coef + weights["intercept"]
        out.append(rf.evaluate(d, rf.assign(d["lines"], d["cands"], s, weights["threshold"])))
    return out


def main():
    out = sys.argv[1]
    n_sim = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    old_path = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, "form_matcher_sim2.json")
    os.makedirs(out, exist_ok=True)
    use_vocabulary(KEYWORDS)
    b.LABELS, b.NAMES, b.CITIES, b.value_text = LABELS, NAMES, CITIES, value_text
    sims = [b.sim_doc(20_000 + s) for s in range(n_sim)]
    fit_docs = [d for k, d in enumerate(sims) if k % 5 in (0, 1, 2)]
    select = [d for k, d in enumerate(sims) if k % 5 == 3]
    test = [d for k, d in enumerate(sims) if k % 5 == 4]
    rows, summary = [], {}

    def add(name, rs):
        line, s = m12.row(name, rs)
        rows.append(line)
        summary[name] = s
        return s

    nn_select = add("nn@select", m12.nn(select))
    models = {}
    for C in (0.001, 0.01, 0.1, 1.0, 10.0):
        m, th = b.fit_c(fit_docs, select, C)
        models[C] = (m, th)
        add(f"C{C:g}@select", m12.score(m, th, select))
    ok = [C for C in models if summary[f"C{C:g}@select"]["blank_filled"] <= nn_select["blank_filled"]]
    pool = ok or list(models)
    chosen = max(pool, key=lambda C: summary[f"C{C:g}@select"]["f1"])
    m, th = models[chosen]
    add("nn@test", m12.nn(test))
    add(f"chosen C{chosen:g}@test", m12.score(m, th, test))
    import engines
    import ppocr
    det = ppocr.Detector(engines.P["det_s"])
    rec = ppocr.Recognizer(engines.P["rec_s"], ppocr.load_dict(engines.P["dict_s"]))
    fdocs = m12.funsd_docs(det, rec)
    ftest = [d for d in fdocs if d["split"] == "test"]
    res_new = m12.score(m, th, ftest)
    res_nn = m12.nn(ftest)
    add(f"chosen C{chosen:g}@funsd_test", res_new)
    add("nn@funsd_test", res_nn)
    old = json.load(open(old_path, encoding="utf-8"))
    use_vocabulary(OLD_KEYWORDS)
    for d in ftest:
        d["cands"], d["lh"] = rf.candidates(d["lines"], d["W"])
    res_old = scores_with(old, ftest)
    add("shipped sim2 (old keywords)@funsd_test", res_old)
    add("nn old keywords@funsd_test", m12.nn(ftest))
    use_vocabulary(KEYWORDS)
    sig = {}
    for name, other in (("nn", res_nn), ("shipped", res_old)):
        w, l, p = sign_test([m12.f1_of(x) - m12.f1_of(y) for x, y in zip(res_new, other)])
        sig[f"new>{name}"] = {"w": w, "l": l, "p": p}
    md = ["## Tester round 2: form matcher refitted without FUNSD", "",
          f"Keywords ({len(KEYWORDS)}): {', '.join(sorted(KEYWORDS))}.", "",
          f"Simulated forms v3: {n_sim} (fit {len(fit_docs)} / select {len(select)} / test {len(test)}). "
          f"Thresholds: " + ", ".join(f"C={C:g} {t:.2f}" for C, (_, t) in models.items()) +
          f". Chosen C = {chosen:g} (rule fixed in advance, see the script).", "",
          "| method | pair P | pair R | pair F1 | blanks wrongly filled | repeated-label P / R |",
          "|---|---|---|---|---|---|"] + rows + ["", "| new vs (per-form F1, FUNSD test) | new better | worse | p |",
                                                 "|---|---|---|---|"]
    for k, v in sig.items():
        md.append(f"| {k} | {v['w']} | {v['l']} | {pfmt(v['p'])} |")
    md.append("")
    open(os.path.join(out, "t2_forms_clean.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    json.dump({"summary": summary, "sig": sig, "chosen_c": chosen, "keywords": sorted(KEYWORDS)},
              open(os.path.join(out, "t2_forms_clean.json"), "w"), indent=1)
    json.dump(m12.weights(m, th, f"line-level form simulator v3 (t2_forms_clean.py, generic labels and keywords, "
                                 f"no FUNSD), C = {chosen:g} chosen on held-out simulated forms"),
              open(os.path.join(out, "form_matcher.json"), "w"), indent=1)
    samples = []
    for d in test[:12]:
        X = rf.feats(d["lines"], d["cands"], d["lh"], d["W"]) if d["cands"] else np.zeros((0, len(m12.FEATURES)))
        s = m.decision_function(X) if d["cands"] else np.zeros(0)
        pairs = rf.assign(d["lines"], d["cands"], s, th) if d["cands"] else []
        samples.append({"id": d["id"], "W": d["W"], "H": d["H"],
                        "lines": [{"t": L["t"], "box": L["box"], "conf": L["conf"]} for L in d["lines"]],
                        "cands": [[i, j, k] for i, j, k in d["cands"]], "lh": d["lh"], "feats": X.tolist(),
                        "scores": [float(v) for v in s], "pairs": [[int(i), int(j)] for i, j in pairs]})
    json.dump(samples, open(os.path.join(out, "form_samples_sim3.json"), "w"))
    print("\n".join(md))


if __name__ == "__main__":
    main()

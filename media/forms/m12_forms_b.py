"""Milestone 12, round b: the generated-form weights of m12_forms.py fell below the nearest-label rule on FUNSD
(pair F1 .300 vs .372): gen_forms.py's templates are too clean (no prose, headers, tables or several fields per row),
so the matcher learned to pair everything. This run fits the same matcher (run_forms.feats, unchanged) on a
line-level form simulator with that variety, our own code and data (no dataset), and scores it on the FUNSD test
forms (internal testing only). The shipping candidate is fixed in advance: simulator v2, C = 1, threshold picked on
held-out simulated forms. Other C values and the round-4 FUNSD fit are listed for comparison only.
usage: m12_forms_b.py OUTDIR [N_SIM]"""
import json
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ocr"))
import m12_forms as m12  # noqa: E402
import run_forms as rf  # noqa: E402
from common import pfmt, sign_test  # noqa: E402

LABELS = ["DATE", "TO", "FROM", "SUBJECT", "RE", "FAX NO.", "PHONE", "TEL", "CC", "Name", "Address", "Company", "Title",
          "Brand", "Product code", "Total", "Amount", "Signature", "Dept.", "Department", "City", "State", "Zip",
          "Account No.", "Telephone", "Attention", "Pages", "Time", "Product", "Date of birth", "Invoice No.",
          "Reference", "Employee ID", "Policy number", "Contact person", "Total due", "Customer name", "Email",
          "Region", "Quantity", "Unit price", "Approved by", "Requested by", "Project", "Budget", "Start date",
          "End date", "Cost center", "Description", "Remarks", "Market", "Distribution", "Media", "Agency",
          "Program", "Proposed by", "Phone number", "No. of pages", "Job number", "Lot number", "Test date"]
WORDS = ("the of and to in a for is on that by this with you it not or be are from at as your all have new more an "
         "was we will home can us about if page my has search free but our one other do no information time they "
         "site he up may what which their news out use any there see only so his when contact here business who "
         "web also now help get pm view online first am been would how were me services some these click its like "
         "service than find price date back top people had list name just over state year day into email two "
         "health world next used go work last most products music buy data make them should product system post "
         "her city add policy number such please available copyright support message after best software then "
         "jan good video well where info rights public books high school through each links she review years order "
         "very privacy book items company read group need many user said does set under general research university "
         "january mail full map reviews program life know games way days management part could great united hotel "
         "real item international center must store travel comments made development report off member details "
         "line terms before hotels did send right type because local those using results office education national "
         "car design take posted internet address community within states area want phone shipping reserved "
         "subject between forum family long based code show even black check special prices website index being "
         "women much sign file link open today technology south case project same pages uk version section own found "
         "sports house related security both county american photo game members power while care network down "
         "computer systems three total place end following download him without per access think north resources "
         "current posts big media law control water history pictures size art personal since including guide shop "
         "directory board location change white text small rating rate government children during usa return "
         "students shopping account times sites level digital profile previous form events love old john main call "
         "hours image department title description non insurance another why shall property class still money "
         "quality every listing content country private little visit save tools low reply customer december "
         "compare movies include college value article york man card jobs provide food source author different "
         "press learn sale around print course job canada process teen room stock training too credit point join "
         "science men categories advanced west sales look english left team estate box conditions select windows "
         "photos thread week category note live large gallery table register however june october november market "
         "library really action start series model features air industry plan human provided tv yes required second "
         "hot accessories cost movie forums march la september better say questions july yahoo going medical test "
         "friend come dec server pc study application cart staff articles san feedback again play looking issues "
         "april never users complete street topic comment financial things working against standard tax person "
         "below mobile less got blog party payment equipment login student let programs offers legal above recent "
         "park stores side act problem red give memory performance social august quote language story sell options "
         "experience rates create key body young america important field few east paper single age activities club "
         "example girls additional password latest something road gift question changes night ca hard texas oct "
         "pay four poker status browse issue range building seller court february always result audio light write "
         "war nov offer blue groups al easy given files event release analysis request fax china making picture "
         "needs possible might professional yet month major star areas future space committee hand sun cards "
         "problems london washington meeting rss become interest id child keep enter california share similar "
         "garden schools million added reference companies listed baby learning energy run delivery net popular "
         "term film stories put computers journal reports co try welcome central images president notice god "
         "original head radio until cell color self council away includes track australia discussion archive once "
         "others entertainment agreement format least society months log safety friends sure faq trade edition "
         "cars messages marketing tell further updated association able having provides david fun already green "
         "studies close common drive specific several gold feb living sep collection called short arts lot ask "
         "display limited powered solutions means director daily beach past natural whether due et electronics five "
         "upon period planning database says official weather mar land average done technical window france pro "
         "region island record direct microsoft conference environment records st district calendar costs style "
         "url front statement update parts aug ever downloads early miles sound resource present applications "
         "either ago document word works material bill apr written talk federal hosting rules final adult tickets "
         "thing centre requirements via cheap kids finance true minutes else mark third rock gifts europe reading "
         "topics bad individual tips plus auto cover usually edit together videos percent fast function fact unit "
         "getting global tech meet far economic en player projects lyrics often subscribe submit germany amount "
         "watch included feel though bank risk thanks everything deals various words linux jul production "
         "commercial james weight town heart advertising received choose treatment newsletter archives points "
         "knowledge magazine error camera jun girl currently construction toys registered clear golf receive "
         "domain methods chapter makes protection policies loan wide beauty manager india position taken sort "
         "listings models michael known half cases step engineering florida simple quick none wireless license "
         "paul friday lake whole annual published later basic sony shows corporate google church method purchase "
         "customers active response practice hardware figure materials fire holiday chat enough designed along "
         "among death writing speed html countries loss face brand discount higher effects created remember "
         "standards oil bit yellow political increase advertise kingdom base near environmental thought stuff").split()
NAMES = ["John Smith", "Mary Jones", "R. J. Reynolds", "Dr. A. Patel", "L. Chen", "K. Brown", "M. Garcia", "T. Nguyen",
         "S. O'Neil", "P. Muller", "J. W. Davis", "Anna Kowalski", "B. Thompson", "C. D. Evans", "H. Ito"]
CITIES = ["New York", "Winston-Salem", "Chicago", "Atlanta", "Richmond", "Denver", "Boston", "Dallas", "Seattle"]


def value_text(r, label):
    l = label.lower()
    if "date" in l or l in ("date", "time"):
        return r.choice([f"{r.randint(1, 12)}/{r.randint(1, 28)}/{r.choice(['98', '99', '1997', '2001'])}",
                         f"{r.choice(['January', 'March', 'June', 'Sept.', 'Oct', 'December'])} {r.randint(1, 28)}, "
                         f"{r.randint(1985, 2005)}", f"{r.randint(1, 28)}.{r.randint(1, 12)}.{r.randint(90, 99)}"])
    if "phone" in l or "fax" in l or "tel" in l:
        return r.choice([f"({r.randint(200, 999)}) {r.randint(200, 999)}-{r.randint(1000, 9999)}",
                         f"{r.randint(200, 999)}-{r.randint(200, 999)}-{r.randint(1000, 9999)}",
                         f"{r.randint(200, 999)} {r.randint(200, 999)} {r.randint(1000, 9999)}"])
    if "total" in l or "amount" in l or "price" in l or "budget" in l or "cost" in l:
        return r.choice([f"${r.randint(1, 99999):,}.{r.randint(0, 99):02d}", f"{r.randint(1, 9999):,}.{r.randint(0, 99):02d}",
                         f"${r.randint(1, 999)}"])
    if "no" in l.split() or "no." in l or "number" in l or "id" in l.split() or "code" in l or "pages" in l:
        return r.choice([str(r.randint(1, 99)), f"{r.randint(100, 99999)}", f"{r.choice('ABCDEFG')}{r.randint(100, 9999)}",
                         f"{r.randint(1000, 9999)}-{r.randint(10, 99)}"])
    if l in ("to", "from", "cc", "name", "attention", "approved by", "requested by", "proposed by", "contact person",
             "customer name", "signature"):
        return r.choice(NAMES)
    if l in ("city", "address", "region", "state"):
        return r.choice(CITIES) if l != "address" else f"{r.randint(1, 999)} {r.choice(['Main St.', 'Oak Ave', 'Park Road'])}"
    n = r.randint(1, 5)
    t = " ".join(r.choice(WORDS) for _ in range(n))
    return t if r.random() < 0.5 else t.upper()


def label_text(r):
    lab = r.choice(LABELS)
    u = r.random()
    if u < 0.35:
        lab = lab.upper()
    elif u < 0.45:
        lab = lab.lower()
    end = r.random()
    if end < 0.6:
        lab += ":"
    elif end < 0.65:
        lab += " #"
    return lab


def sentence(r, n):
    t = " ".join(r.choice(WORDS) for _ in range(n))
    return t[:1].upper() + t[1:] + r.choice([".", ",", "", ";"])


class Doc:
    def __init__(self, r):
        self.r = r
        self.W = r.uniform(700, 1000)
        self.H = self.W * r.uniform(1.25, 1.35)
        self.h = r.uniform(9, 16)
        self.lines, self.ents, self.links = [], {}, set()
        self.k = 0

    def line(self, text, x, y, ent, label):
        r = self.r
        w = len(text) * self.h * r.uniform(0.45, 0.62)
        jit = lambda: r.uniform(-1.5, 1.5)  # noqa: E731
        box = [x + jit(), y + jit(), x + w + jit(), y + self.h + jit()]
        conf = 1.0 if r.random() < 0.3 else r.uniform(0.75, 1.0)
        self.lines.append({"t": text, "box": box, "conf": conf, "ent": ent})
        if ent is not None and ent not in self.ents:
            self.ents[ent] = {"label": label, "text": text}
        return box

    def ent(self):
        self.k += 1
        return f"e{self.k}"


def sim_doc(seed):
    r = random.Random(seed)
    d = Doc(r)
    h = d.h
    y = r.uniform(30, 80)
    left = r.uniform(30, 90)
    right_edge = d.W - r.uniform(30, 90)
    for _ in range(r.randint(0, 3)):
        t = " ".join(r.choice(WORDS) for _ in range(r.randint(1, 4))).upper()
        d.line(t, r.uniform(left, d.W / 2), y, d.ent(), "header")
        y += h * r.uniform(1.3, 2.2)
    two_col = r.random() < 0.4
    col_x = [left, left + (right_edge - left) * r.uniform(0.45, 0.6)]
    below_style = r.random() < 0.3
    n_fields = r.randint(4, 18)
    labels_seen = []
    f = 0
    while f < n_fields and y < d.H - 6 * h:
        kind = r.random()
        if kind < 0.12:
            for _ in range(r.randint(1, 5)):
                if y >= d.H - 3 * h:
                    break
                d.line(sentence(r, r.randint(5, 14)), left + r.uniform(0, 20), y, d.ent(), "other")
                y += h * r.uniform(1.15, 1.4)
            y += h * r.uniform(0.5, 1.5)
            continue
        if kind < 0.17:
            for _ in range(r.randint(2, 4)):
                x = left
                for _c in range(r.randint(2, 4)):
                    t = r.choice([f"{r.randint(1, 999)}", f"{r.uniform(0, 100):.1f}", r.choice(WORDS)])
                    d.line(t, x, y, d.ent(), "other")
                    x += r.uniform(80, 160)
                y += h * 1.4
            continue
        if kind < 0.22:
            for _ in range(r.randint(2, 4)):
                box = r.choice(["[ ]", "[x]", "☐", "☒", "O", "X"])
                d.line(f"{box} {r.choice(['Yes', 'No', 'Single', 'Married', 'Other', 'New', 'Renewal'])}",
                       left + r.uniform(0, 300), y, d.ent(), "other")
                y += h * 1.5
            continue
        cols = 2 if two_col and r.random() < 0.8 else 1
        row_h = h
        for c in range(cols):
            if f >= n_fields:
                break
            f += 1
            lab = label_text(r) if not (labels_seen and r.random() < 0.08) else r.choice(labels_seen)
            labels_seen.append(lab)
            x0 = col_x[c] + r.uniform(-5, 15)
            le = d.ent()
            has_value = r.random() < 0.72
            merged = has_value and r.random() < 0.12
            if merged:
                d.line(f"{lab} {value_text(r, lab.rstrip(':# '))}", x0, y, le, "question")
                continue
            lbox = d.line(lab, x0, y, le, "question")
            if not has_value:
                if r.random() < 0.3:
                    d.line("_" * r.randint(8, 30), lbox[2] + r.uniform(5, 20), y, None, "other")
                continue
            ve = d.ent()
            vt = value_text(r, lab.rstrip(":# "))
            style = "below" if below_style and r.random() < 0.8 else r.choice(["right"] * 8 + ["below", "offset"])
            if style == "right":
                vx = max(lbox[2] + r.uniform(5, 60), x0 + r.uniform(0, 1) * 160)
                d.line(vt, vx, y + r.uniform(-0.25, 0.25) * h, ve, "answer")
            elif style == "offset":
                d.line(vt, lbox[2] + r.uniform(5, 40), y - r.uniform(0.3, 0.5) * h, ve, "answer")
            else:
                d.line(vt, x0 + r.uniform(-5, 30), y + h * r.uniform(1.2, 1.8), ve, "answer")
                row_h = max(row_h, h * 2.0)
            if r.random() < 0.1:
                d.line(value_text(r, "remarks"), x0 + r.uniform(0, 30), y + row_h + h * 0.3, ve, "answer")
                row_h += h * 1.3
            d.links.add((le, ve))
        y += row_h + h * r.uniform(0.6, 1.6)
    for _ in range(r.randint(0, 2)):
        if y < d.H - 2 * h:
            d.line(sentence(r, r.randint(4, 10)), left, d.H - r.uniform(2, 5) * h, d.ent(), "other")
    doc = {"id": f"sim{seed}", "lines": d.lines, "ents": d.ents, "links": d.links, "W": d.W, "H": d.H}
    doc["cands"], doc["lh"] = rf.candidates(d.lines, d.W)
    return doc


def fit_c(train, tune, C):
    from sklearn.linear_model import LogisticRegression
    Xs, ys = zip(*[m12.xy(d) for d in train if d["cands"]])
    m = LogisticRegression(max_iter=6000, C=C).fit(np.vstack(Xs), np.concatenate(ys))
    best = None
    for th in np.linspace(-3, 3, 25):
        rs = [rf.evaluate(d, rf.assign(d["lines"], d["cands"], m.decision_function(m12.xy(d)[0]), th))
              for d in tune if d["cands"]]
        f = rf.prf(rs)[2]
        if best is None or f > best[0]:
            best = (f, float(th))
    return m, best[1]


def main():
    out = sys.argv[1]
    n_sim = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    os.makedirs(out, exist_ok=True)
    sims = [sim_doc(s) for s in range(n_sim)]
    tr, tu = sims[: int(0.8 * n_sim)], sims[int(0.8 * n_sim):]
    import engines
    import ppocr
    det = ppocr.Detector(engines.P["det_s"])
    rec = ppocr.Recognizer(engines.P["rec_s"], ppocr.load_dict(engines.P["dict_s"]))
    fdocs = m12.funsd_docs(det, rec)
    ftrain = [d for d in fdocs if d["split"] == "train"]
    ftest = [d for d in fdocs if d["split"] == "test"]
    res = {"nn": m12.nn(ftest)}
    m_f, th_f = m12.fit(ftrain, [d for k, d in enumerate(ftrain) if k % 2 == 1])
    res["geo_funsd"] = m12.score(m_f, th_f, ftest)
    models = {}
    for C in (1.0, 0.1, 0.01):
        m, th = fit_c(tr, tu, C)
        models[C] = (m, th)
        res[f"sim2_C{C:g}"] = m12.score(m, th, ftest)
        res[f"sim2_C{C:g}@sim"] = [rf.evaluate(d, rf.assign(d["lines"], d["cands"], m.decision_function(m12.xy(d)[0]),
                                                             th)) for d in tu if d["cands"]]
    md = ["## Milestone 12b: form matcher fitted on a line-level form simulator", "",
          f"Simulated forms: {n_sim} ({len(tr)} fit / {len(tu)} threshold). Thresholds: " +
          ", ".join(f"C={C:g} {th:.2f}" for C, (_, th) in models.items()) + f"; geo_funsd {th_f:.2f}.", "",
          "FUNSD test (50 forms, PP-OCRv6 small lines, entity-level pairs); `@sim` rows are held-out simulated forms:",
          "", "| method | pair P | pair R | pair F1 | blanks wrongly filled | repeated-label P / R |",
          "|---|---|---|---|---|---|"]
    summary = {}
    for k, rs in res.items():
        line, s = m12.row(k, rs)
        md.append(line)
        summary[k] = s
    md += ["", "| A vs B (per-form F1, FUNSD test) | A better | B better | p |", "|---|---|---|---|"]
    sig = {}
    for a in [f"sim2_C{C:g}" for C in models]:
        for b in ("nn", "geo_funsd"):
            w, l, p = sign_test([m12.f1_of(x) - m12.f1_of(y) for x, y in zip(res[a], res[b])])
            sig[f"{a}>{b}"] = {"w": w, "l": l, "p": p}
            md.append(f"| {a} vs {b} | {w} | {l} | {pfmt(p)} |")
    md.append("")
    open(os.path.join(out, "m12_forms_b.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    json.dump({"summary": summary, "sig": sig}, open(os.path.join(out, "m12_forms_b.json"), "w"), indent=1)
    m, th = models[1.0]
    json.dump(m12.weights(m, th, "line-level form simulator v2 (m12_forms_b.py), C = 1"),
              open(os.path.join(out, "form_matcher_sim2.json"), "w"), indent=1)
    samples = []
    for d in tu[:12]:
        X = rf.feats(d["lines"], d["cands"], d["lh"], d["W"]) if d["cands"] else np.zeros((0, len(m12.FEATURES)))
        s = m.decision_function(X) if d["cands"] else np.zeros(0)
        pairs = rf.assign(d["lines"], d["cands"], s, th) if d["cands"] else []
        samples.append({"id": d["id"], "W": d["W"], "H": d["H"],
                        "lines": [{"t": L["t"], "box": L["box"], "conf": L["conf"]} for L in d["lines"]],
                        "cands": [[i, j, k] for i, j, k in d["cands"]], "lh": d["lh"], "feats": X.tolist(),
                        "scores": [float(v) for v in s], "pairs": [[int(i), int(j)] for i, j in pairs]})
    json.dump(samples, open(os.path.join(out, "form_samples_sim2.json"), "w"))
    print("\n".join(md))


if __name__ == "__main__":
    main()

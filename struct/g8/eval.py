import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import cfg, stats as S

VARS = [("C", "clean control"), ("R", "ToUnicode digit remap"), ("O", "image + wrong invisible OCR layer"), ("M", "mixed scanned/digital")]
ARMS = ["dl_textonly", "dl_default", "dl_rbtl", "dl_fullocr", "R1", "R2"]
LABEL = {"dl_textonly": "docling-rs text layer only", "dl_default": "docling-rs default (current)",
         "dl_rbtl": "docling-rs replace_broken_text_layer", "dl_fullocr": "docling-rs full-page OCR (PP-OCRv6)",
         "R1": "region routing: triggers + font sampling", "R2": "region routing + verify all critical lines"}


def arm(r, a):
    return r["arms"].get(a) if a.startswith("dl_") else r["routers"].get(a)


def tot(recs, a, key, pred=None):
    s = 0
    for r in recs:
        x = arm(r, a)
        if not x or "pages" not in x:
            continue
        for p in x["pages"]:
            if pred is None or pred(p):
                s += p.get(key) or 0
    return s


def wtot(recs, a, key):
    s = 0
    for r in recs:
        x = arm(r, a)
        if not x or "pages" not in x:
            continue
        for p in x["pages"]:
            if p.get("words"):
                s += p["words"][key]
    return s


def cpu_page(recs, a):
    v = []
    for r in recs:
        x = arm(r, a)
        if x and "cpu" in x and x.get("n"):
            v.append(x["cpu"] / x["n"])
    return v


def summarize():
    recs = []
    for f in sorted(glob.glob(os.path.join(cfg.RES, "g8", "metrics-*.jsonl"))):
        recs += [r for r in cfg.jsonl(f)]
    errs = [r for r in recs if "error" in r]
    recs = [r for r in recs if "error" not in r and r.get("arms")]
    docs = sorted({r["doc"] for r in recs})
    test = [r for r in recs if S.split_of(r["doc"]) == "test"]
    md = ["## Gap 8. Broken or misleading text layers", ""]
    md.append("Documents: %d real born-digital PDFs (%d arXiv q-fin/econ/stat, %d Federal Register), up to 5 digit-rich pages each; %d doc-variant records, %d scoring errors."
              % (len(docs), len({r['doc'] for r in recs if r['source'].startswith('arxiv')}), len({r['doc'] for r in recs if r['source'] == 'federal_register'}), len(recs), len(errs)))
    md.append("Gold text is the clean PDF's own text layer (pdfium words). Variants: R = font ToUnicode CMaps rewritten with pikepdf so two digit pairs swap (glyphs and rendering unchanged, verified by pixel comparison); O = page image + invisible OCR layer with realistic OCR confusions (35% of critical words, 6% of others); M = every second page image-only. Critical values = tokens with at least two digits (amounts, dates, IDs). Tables use the document-grouped test split (80%, hash of document id); thresholds were fixed before the run.")
    md.append("")
    summ = {}
    for v, vname in VARS:
        rv = [r for r in test if r["variant"] == v]
        if not rv:
            continue
        md.append("### Variant %s: %s (%d documents)" % (v, vname, len(rv)))
        md.append("")
        md.append("| Arm | Critical recall | Wrong critical values emitted / 100 gold | Corrupted/missing critical values recovered | Token recall | Token precision | CPU s/page mean | CPU s/page p95 |")
        md.append("|---|---|---|---|---|---|---|---|")
        for a in ARMS:
            g = tot(rv, a, "g")
            if not g:
                continue
            c = S.boot(rv, lambda s, a=a: S.ratio(tot(s, a, "correct"), tot(s, a, "g")))
            bad = tot(rv, a, "bad")
            rec = S.ratio(tot(rv, a, "recovered"), bad)
            cp = cpu_page(rv, a)
            md.append("| %s | %s | %s | %s (%d/%d) | %s | %s | %s | %s |" % (
                LABEL[a], S.ci(c), S.fmt(100 * S.ratio(tot(rv, a, "wrong"), g), 2), S.fmt(rec), tot(rv, a, "recovered"), bad,
                S.fmt(S.ratio(tot(rv, a, "tov"), tot(rv, a, "tg"))), S.fmt(S.ratio(tot(rv, a, "tov"), tot(rv, a, "to"))),
                S.fmt(sum(cp) / len(cp) if cp else float("nan"), 2), S.fmt(S.pct(cp, 0.95), 2)))
            summ.setdefault(v, {})[a] = dict(crit_recall=c[0], recovered=rec, wrong_per100=100 * S.ratio(tot(rv, a, "wrong"), g))
        md.append("")
        rows = []
        for a in ("R1", "R2"):
            n = wtot(rv, a, "n")
            if not n:
                continue
            cb = wtot(rv, a, "c_bad")
            nat_ok = wtot(rv, a, "native_ok")
            rows.append("| %s | %d | %s | %s | %s | %s | %s | %s |" % (
                LABEL[a], cb,
                S.fmt(S.ratio(wtot(rv, a, "c_fixed"), cb)), S.fmt(S.ratio(wtot(rv, a, "c_caught"), cb)),
                S.fmt(S.ratio(wtot(rv, a, "kept"), nat_ok), 4), S.fmt(S.ratio(wtot(rv, a, "flag_ok"), nat_ok), 4),
                S.fmt(S.ratio(tot(rv, a, "ocr_area"), tot(rv, a, "text_area"))),
                S.fmt(S.ratio(tot(rv, a, "ocr_lines"), sum(x["n"] for x in (arm(r, a) for r in rv) if x and "n" in x)), 1)))
        if rows:
            md.append("Word-aligned router audit (gold word vs native word vs router output):")
            md.append("")
            md.append("| Router | Wrong native critical words | Corrected | Caught (corrected or flagged) | Correct native words kept | Correct native words flagged | OCR share (area) | OCR lines / page |")
            md.append("|---|---|---|---|---|---|---|---|")
            md += rows
            md.append("")
        pairs = []
        for a, b in (("dl_default", "R1"), ("dl_default", "R2"), ("dl_fullocr", "R2"), ("dl_rbtl", "R2")):
            if not tot(rv, a, "g") or not tot(rv, b, "g"):
                continue
            pr = S.paired(rv, lambda s, a=a: S.ratio(tot(s, a, "correct") - tot(s, a, "wrong"), tot(s, a, "g")),
                          lambda s, b=b: S.ratio(tot(s, b, "correct") - tot(s, b, "wrong"), tot(s, b, "g")))
            pairs.append("| %s vs %s | %s | %s | %s | [%s, %s] | %s |" % (LABEL[b], LABEL[a], S.fmt(pr["a"]), S.fmt(pr["b"]), S.fmt(pr["diff"]),
                                                                  S.fmt(pr["lo"]), S.fmt(pr["hi"]), S.fmt(pr["p"], 4)))
        if pairs:
            md.append("Paired document bootstrap on net critical accuracy ((correct - wrong) / gold critical values):")
            md.append("")
            md.append("| Comparison | Baseline | Candidate | Difference | 95% CI | p |")
            md.append("|---|---|---|---|---|---|")
            md += pairs
            md.append("")
    clean = [r for r in test if r["variant"] == "C"]
    keep = {a: S.ratio(wtot(clean, a, "kept"), wtot(clean, a, "native_ok")) for a in ("R1", "R2")}
    summ["clean_keep"] = keep
    ex = [dict(doc=r["doc"], variant=r["variant"], **e) for r in recs for e in r.get("examples", []) if r["variant"] in ("R", "O")]
    if ex:
        md.append("Failure and catch examples (router R2, critical words whose native text was wrong):")
        md.append("")
        md.append("| Doc | Variant | Gold | Native | Router output | Flagged |")
        md.append("|---|---|---|---|---|---|")
        for e in ex[:14]:
            md.append("| %s | %s | `%s` | `%s` | `%s` | %s |" % (e["doc"], e["variant"], e["gold"], e["native"], e["out"], e["flag"]))
        md.append("")
    dist = {}
    for r in recs:
        if r["variant"] == "R":
            for a in ("R1",):
                x = r["routers"].get(a) or {}
                dist[r["doc"]] = bool(x.get("distrust"))
    if dist:
        md.append("Font-level distrust fired on %d of %d remapped documents (R1). Dev-split documents: %d."
                  % (sum(dist.values()), len(dist), len({r['doc'] for r in recs}) - len({r['doc'] for r in test})))
        md.append("")
    errs_s = [r for r in recs for a, x in list(r["arms"].items()) + list(r["routers"].items()) if x and "error" in x]
    if errs_s or errs:
        md.append("Conversion/router errors: %d arm runs, %d records failed scoring." % (len(errs_s), len(errs)))
        md.append("")
    return "\n".join(md), summ


if __name__ == "__main__":
    print(summarize()[0])

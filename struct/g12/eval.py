import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import cfg, dl, pdf as P, stats as S


def summarize():
    recs = []
    for f in sorted(glob.glob(os.path.join(cfg.RES, "g12", "raw-*.jsonl"))):
        recs += cfg.jsonl(f)
    fx = [r for r in recs if r.get("gold") and "det" in r]
    md = ["## Gap 12. Watermarks, redactions, page labels", ""]
    md.append("Generated fixtures: %d multi-page PDFs (reportlab + pikepdf) with repeated text/image/annotation watermarks, applied, unapplied (Redact annotation) and unsafe (box over live text) redactions, dark negatives (table header bands, rules, bullets, dark photos), repeated headers and logos, rotated axis labels, and six page-label schemes. DocHush public fixtures are listed separately." % len(fx))
    md.append("")
    summ = {}
    pos = [r for r in fx if r["gold"]["watermark"] != "none"]
    neg = [r for r in fx if r["gold"]["watermark"] == "none"]
    tp = sum(r["det"]["watermark"] for r in pos)
    fp = sum(r["det"]["watermark"] for r in neg)
    p_, r_, f_ = S.f1(tp, tp + fp, len(pos))
    md.append("### Watermarks (document level)")
    md.append("")
    md.append("| Kind | Docs | Detected | Watermark text in docling-rs body text | in docling-rs furniture |")
    md.append("|---|---|---|---|---|")
    for k in ("diag_text", "horiz_text", "annot", "image"):
        xs = [r for r in pos if r["gold"]["watermark"] == k]
        if not xs:
            continue
        leak = [dl.norm(r["gold"]["wm_text"]).lower() in dl.norm(r.get("dl", {}).get("body", "")).lower() for r in xs if "dl" in r]
        furn = [dl.norm(r["gold"]["wm_text"]).lower() in dl.norm(r.get("dl", {}).get("furn", "")).lower() for r in xs if "dl" in r]
        md.append("| %s | %d | %s | %s | %s |" % (k, len(xs), S.fmt(S.ratio(sum(r["det"]["watermark"] for r in xs), len(xs))),
                                               S.fmt(S.ratio(sum(leak), len(leak))), S.fmt(S.ratio(sum(furn), len(furn)))))
    md.append("| none (negatives: repeated headers, logos, rotated labels) | %d | false flags %s | | |" % (len(neg), S.fmt(S.ratio(fp, len(neg)))))
    md.append("")
    md.append("Watermark precision %s, recall %s, F1 %s." % (S.fmt(p_), S.fmt(r_), S.fmt(f_)))
    md.append("")
    summ["wm"] = dict(p=p_, r=r_, f1=f_)
    md.append("### Redactions (region level, IoU >= 0.5 on the same page)")
    md.append("")
    by = {}
    fpr = 0
    npred = 0
    leak_unsafe = []
    for r in fx:
        gold = r["gold"]["redactions"]
        pred = list(r["det"]["redactions"])
        npred += len(pred)
        used = set()
        for g in gold:
            hit = None
            for k, p in enumerate(pred):
                if k in used or p["page"] != g["page"]:
                    continue
                if P.iou(g["box"], p["box"]) >= 0.5:
                    hit = k
                    break
            if hit is not None:
                used.add(hit)
            by.setdefault(g["type"], []).append((hit is not None, hit is not None and pred[hit]["type"] == g["type"]))
            if g["type"] in ("unsafe_cover", "unapplied_annot") and "dl" in r:
                can = g["text"].split()[-1]
                leak_unsafe.append((g["type"], can in r["dl"]["body"] + " " + r["dl"]["furn"]))
        fpr += len(pred) - len(used)
    md.append("| Type | Gold regions | Located | Located with correct type | Covered text present in docling-rs output |")
    md.append("|---|---|---|---|---|")
    for t, xs in sorted(by.items()):
        lk = [x for tt, x in leak_unsafe if tt == t]
        md.append("| %s | %d | %s | %s | %s |" % (t, len(xs), S.fmt(S.ratio(sum(a for a, _ in xs), len(xs))),
                                               S.fmt(S.ratio(sum(b for _, b in xs), len(xs))), S.fmt(S.ratio(sum(lk), len(lk))) if lk else "-"))
    nneg = sum(1 for r in fx for g in r["gold"]["negatives"] if g["type"] in ("dark_header", "rule", "dark_photo", "bullet"))
    md.append("")
    md.append("Unmatched predicted redactions (false flags): %d of %d predictions; dark negatives present: %d." % (fpr, npred, nneg))
    md.append("")
    summ["redaction_false_flags"] = fpr
    md.append("### Page labels (per page, against the printed label)")
    md.append("")
    md.append("| Scheme | Pages | Physical index (docling-rs page_no) | /PageLabels only | Printed-label detection | Fused | Mismatch flagged (docs) |")
    md.append("|---|---|---|---|---|---|---|")
    tot = {"phys": [0, 0], "pl": [0, 0], "pr": [0, 0], "fu": [0, 0]}
    for sch in ("plain", "roman_front", "offset", "appendix", "printed_only_roman", "mismatch"):
        xs = [r for r in fx if r["gold"]["labels"] == sch]
        if not xs:
            continue
        c = {"phys": 0, "pl": 0, "pr": 0, "fu": 0}
        n = 0
        mm = 0
        for r in xs:
            d = r["det"]
            mm += d["mismatch"]
            for i, g in enumerate(r["gold"]["printed"]):
                if g is None:
                    continue
                n += 1
                c["phys"] += str(i + 1) == g
                c["pl"] += ((d["pagelabels"][i] if d["pagelabels"] else str(i + 1)) or "").lower() == g.lower()
                c["pr"] += (d["printed"][i] or "").lower() == g.lower()
                c["fu"] += (d["fused"][i] or "").lower() == g.lower()
        for k in c:
            tot[k][0] += c[k]
            tot[k][1] += n
        md.append("| %s | %d | %s | %s | %s | %s | %d/%d |" % (sch, n, *[S.fmt(S.ratio(c[k], n)) for k in ("phys", "pl", "pr", "fu")], mm, len(xs)))
    md.append("| **all** | %d | %s | %s | %s | %s | |" % (tot["fu"][1], *[S.fmt(S.ratio(*tot[k])) for k in ("phys", "pl", "pr", "fu")]))
    md.append("")
    summ["labels"] = {k: S.ratio(*v) for k, v in tot.items()}
    mm_pos = [r for r in fx if r["gold"]["labels"] == "mismatch"]
    mm_neg = [r for r in fx if r["gold"]["labels"] in ("roman_front", "offset", "appendix")]
    md.append("Mismatch flag: recall %s on %d docs whose /PageLabels disagree with the print; false flags %s on %d docs with correct /PageLabels." % (
        S.fmt(S.ratio(sum(r["det"]["mismatch"] for r in mm_pos), len(mm_pos))), len(mm_pos),
        S.fmt(S.ratio(sum(r["det"]["mismatch"] for r in mm_neg), len(mm_neg))), len(mm_neg)))
    md.append("")
    dh = [r for r in recs if str(r["id"]).startswith("dochush:") and "det" in r]
    if dh:
        md.append("DocHush fixtures: " + "; ".join("%s -> %s" % (r["id"][8:], ",".join(sorted({x["type"] for x in r["det"]["redactions"]})) or "none") for r in dh) + ".")
        md.append("")
    cpu = [r["det_cpu"] for r in fx if "det_cpu" in r]
    if cpu:
        md.append("Detector CPU per document: mean %s s, p95 %s s. Errors: %d." % (S.fmt(sum(cpu) / len(cpu), 3), S.fmt(S.pct(cpu, 0.95), 3),
                                                                               sum(1 for r in recs if "det_error" in r or "dl_error" in r)))
        md.append("")
    return "\n".join(md), summ


if __name__ == "__main__":
    print(summarize()[0])

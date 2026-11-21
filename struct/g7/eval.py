import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import cfg, stats as S

LABEL = {"dl": "docling-rs default (no typed links)", "pattern": "text pattern + geometry (captions, reference list, superscripts)",
         "explicit": "PDF link annotations only (GoTo destinations)", "combined": "pattern + link annotations"}
TYPES = {"fig": "figure refs", "table": "table refs", "bibr": "citations", "fn": "footnotes"}


def t(recs, a, ty, f):
    return sum(r["arms"][a][ty][f] for r in recs)


def summarize():
    recs = []
    for f in sorted(glob.glob(os.path.join(cfg.RES, "g7", "metrics-*.jsonl"))):
        recs += cfg.jsonl(f)
    errs = [r for r in recs if "error" in r]
    recs = [r for r in recs if "error" not in r]
    test = [r for r in recs if S.split_of(r["id"]) == "test"]
    md = ["## Gap 7. Cross-references", ""]
    md.append("PMC Open Access articles from the AWS open-data bucket (licence_code CC BY / CC0 / CC BY-SA / CC BY-ND only, research articles with 2+ figures, 1+ table, 10+ references, 3-30 pages). Gold links are JATS `<xref ref-type rid>` in the body (figures and tables by label number, citations by reference label or list position, ranges like `[3-5]` expanded). A predicted link counts only if its target exists in the parsed PDF (caption with that number, reference entry). %d articles scored (%d test split), %d errors." % (len(recs), len(test), len(errs)))
    md.append("")
    summ = {}
    if not test:
        return "\n".join(md), summ
    md.append("| Arm | Type | Gold links | Precision | Recall [95% CI] | F1 |")
    md.append("|---|---|---|---|---|---|")
    for a in ("dl", "pattern", "explicit", "combined"):
        for ty in TYPES:
            ng = t(test, a, ty, "ng")
            if not ng:
                continue
            tp, np_ = t(test, a, ty, "tp"), t(test, a, ty, "np")
            p, r_, f = S.f1(tp, np_, ng)
            rc = S.boot(test, lambda x, a=a, ty=ty: S.ratio(t(x, a, ty, "tp"), t(x, a, ty, "ng")), B=1000)
            md.append("| %s | %s | %d | %s | %s | %s |" % (LABEL[a], TYPES[ty], ng, S.fmt(p), S.ci(rc), S.fmt(f)))
            summ["%s|%s" % (a, ty)] = dict(p=p, r=r_, f1=f)
    md.append("")
    for ty in ("fig", "table", "bibr"):
        pr = S.paired(test, lambda x, ty=ty: S.f1(t(x, "pattern", ty, "tp"), t(x, "pattern", ty, "np"), t(x, "pattern", ty, "ng"))[2],
                      lambda x, ty=ty: S.f1(t(x, "combined", ty, "tp"), t(x, "combined", ty, "np"), t(x, "combined", ty, "ng"))[2], B=1000)
        md.append("Adding link annotations, %s F1: %s -> %s, difference %s [%s, %s], p=%s." % (TYPES[ty], S.fmt(pr["a"]), S.fmt(pr["b"]), S.fmt(pr["diff"]), S.fmt(pr["lo"]), S.fmt(pr["hi"]), S.fmt(pr["p"], 4)))
    md.append("")
    num = [r for r in test if r["info"]["gold_numeric"]]
    ay = [r for r in test if not r["info"]["gold_numeric"]]
    for name, rs in (("numbered reference lists", num), ("author-year reference lists", ay)):
        if rs:
            p, r_, f = S.f1(t(rs, "combined", "bibr", "tp"), t(rs, "combined", "bibr", "np"), t(rs, "combined", "bibr", "ng"))
            md.append("Citations, %s (%d articles): P %s, R %s, F1 %s." % (name, len(rs), S.fmt(p), S.fmt(r_), S.fmt(f)))
    la = sum(1 for r in test if r["info"]["link_annots"] > 0)
    md.append("Articles with internal GoTo link annotations: %d of %d. docling-rs JSON internal (non-URI) hyperlinks found: %d. Reference entries found vs gold: %d vs %d." % (
        la, len(test), sum(r["info"]["dl_internal_links"] for r in test), sum(r["info"]["refs_found"] for r in test), sum(r["info"]["refs_gold"] for r in test)))
    md.append("")
    cpu = [r["cpu"]["link"] / max(1, r["cpu"]["pages"]) for r in recs]
    md.append("Linker CPU %s s/page on top of docling-rs (%s s/page)." % (S.fmt(sum(cpu) / len(cpu), 3), S.fmt(sum(r["cpu"]["dl"] / max(1, r["cpu"]["pages"]) for r in recs) / len(recs), 3)))
    md.append("")
    ex = [r for r in test if r.get("examples") and (r["examples"]["missed"] or r["examples"]["extra"])][:4]
    if ex:
        md.append("Failure examples ([type, key, gold count, predicted count]):")
        md.append("")
        for r in ex:
            md.append("- %s: missed %s; extra %s" % (r["id"], r["examples"]["missed"][:4], r["examples"]["extra"][:4]))
        md.append("")
    return "\n".join(md), summ


if __name__ == "__main__":
    print(summarize()[0])

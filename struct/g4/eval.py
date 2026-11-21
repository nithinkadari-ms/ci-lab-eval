import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import cfg, stats as S

LABEL = {"dl": "docling-rs default", "ours": "marker + indent state machine"}


def t(recs, a, f):
    return sum(r["arms"][a][f] for r in recs)


def summarize():
    recs = []
    for f in sorted(glob.glob(os.path.join(cfg.RES, "g4", "metrics-*.jsonl"))):
        recs += cfg.jsonl(f)
    errs = [r for r in recs if "error" in r]
    recs = [r for r in recs if "error" not in r]
    test = [r for r in recs if S.split_of(r["id"]) == "test"]
    md = ["## Gap 4. Nested lists", ""]
    md.append("DOCX files generated with python-docx carrying real OOXML numbering (numId/ilvl, 7 marker families: bullets, 1./a./i., (1)/(a)/(i), 1./1.1./1.1.1., I./A./1., mixed, 1)/a)/i)), restarts (startOverride), continued lists, 30%% wrapped items, numbered headings and number-leading prose as negatives; converted to PDF with LibreOffice headless on the runner. Gold comes from the DOCX. %d documents scored (%d test split), %d errors." % (len(recs), len(test), len(errs)))
    md.append("")
    if not test:
        return "\n".join(md), {}
    md.append("| Arm | Item P | Item R | Item F1 [95% CI] | Exact depth (matched) | Parent-edge F1 [95% CI] | Wrapped items complete | False list items on negatives |")
    md.append("|---|---|---|---|---|---|---|---|")
    summ = {}
    for a in ("dl", "ours"):
        p, r_, f = S.f1(t(test, a, "tp"), t(test, a, "np"), t(test, a, "ng"))
        fi = S.boot(test, lambda x, a=a: S.f1(t(x, a, "tp"), t(x, a, "np"), t(x, a, "ng"))[2], B=1000)
        fe = S.boot(test, lambda x, a=a: S.f1(t(x, a, "edge"), t(x, a, "np"), t(x, a, "ng"))[2], B=1000)
        md.append("| %s | %s | %s | %s | %s | %s | %s | %s (%d/%d) |" % (
            LABEL[a], S.fmt(p), S.fmt(r_), S.ci(fi), S.fmt(S.ratio(t(test, a, "depth_ok"), t(test, a, "tp"))), S.ci(fe),
            S.fmt(S.ratio(t(test, a, "complete"), t(test, a, "wrapped"))), S.fmt(S.ratio(t(test, a, "negf"), t(test, a, "neg")), 4), t(test, a, "negf"), t(test, a, "neg")))
        summ[a] = dict(item_f1=fi[0], edge_f1=fe[0], depth=S.ratio(t(test, a, "depth_ok"), t(test, a, "tp")), false=S.ratio(t(test, a, "negf"), t(test, a, "neg")))
    md.append("")
    pe = S.paired(test, lambda x: S.f1(t(x, "dl", "edge"), t(x, "dl", "np"), t(x, "dl", "ng"))[2],
                  lambda x: S.f1(t(x, "ours", "edge"), t(x, "ours", "np"), t(x, "ours", "ng"))[2], B=1000)
    pi = S.paired(test, lambda x: S.f1(t(x, "dl", "tp"), t(x, "dl", "np"), t(x, "dl", "ng"))[2],
                  lambda x: S.f1(t(x, "ours", "tp"), t(x, "ours", "np"), t(x, "ours", "ng"))[2], B=1000)
    md.append("Paired document bootstrap, state machine minus docling-rs: parent-edge F1 %s [%s, %s] p=%s; item F1 %s [%s, %s] p=%s. Parent-edge precision of the state machine: %s (target >= 0.95)." % (
        S.fmt(pe["diff"]), S.fmt(pe["lo"]), S.fmt(pe["hi"]), S.fmt(pe["p"], 4), S.fmt(pi["diff"]), S.fmt(pi["lo"]), S.fmt(pi["hi"]), S.fmt(pi["p"], 4),
        S.fmt(S.ratio(t(test, "ours", "edge"), t(test, "ours", "np")))))
    md.append("")
    md.append("| Marker family | Gold items | docling-rs depth exact | state machine depth exact | docling-rs edge | state machine edge |")
    md.append("|---|---|---|---|---|---|")
    fams = sorted({k for r in test for k in r["arms"]["ours"]["fam"]})
    for fm in fams:
        g = sum(r["arms"]["ours"]["fam"].get(fm, [0, 0, 0])[0] for r in test)
        vals = []
        for a in ("dl", "ours"):
            vals.append(S.ratio(sum(r["arms"][a]["fam"].get(fm, [0, 0, 0])[1] for r in test), g))
        for a in ("dl", "ours"):
            vals.append(S.ratio(sum(r["arms"][a]["fam"].get(fm, [0, 0, 0])[2] for r in test), g))
        md.append("| %s | %d | %s |" % (fm, g, " | ".join(S.fmt(v) for v in vals)))
    md.append("")
    md.append("Depth accuracy by gold depth (matched items): " + "; ".join(
        "depth %s: docling-rs %s, state machine %s" % (d, S.fmt(S.ratio(sum(r["arms"]["dl"]["bydepth"].get(d, [0, 0])[1] for r in test), sum(r["arms"]["dl"]["bydepth"].get(d, [0, 0])[0] for r in test))),
                                                      S.fmt(S.ratio(sum(r["arms"]["ours"]["bydepth"].get(d, [0, 0])[1] for r in test), sum(r["arms"]["ours"]["bydepth"].get(d, [0, 0])[0] for r in test))))
        for d in ("1", "2", "3", "4")) + ".")
    md.append("")
    cpu = [r["cpu"]["ours"] / max(1, r["cpu"]["pages"]) for r in recs]
    md.append("State machine CPU %s s/page (on top of the docling-rs run, %s s/page)." % (S.fmt(sum(cpu) / len(cpu), 4),
                                                                                       S.fmt(sum(r["cpu"]["dl"] / max(1, r["cpu"]["pages"]) for r in recs) / len(recs), 3)))
    ex = test[0]["examples"] if test else None
    if ex:
        md.append("")
        md.append("Example %s: gold %s; docling-rs %s; state machine %s." % (test[0]["id"], ex["gold"][:5], ex["dl"][:5], ex["ours"][:5]))
    md.append("")
    return "\n".join(md), summ


if __name__ == "__main__":
    print(summarize()[0])

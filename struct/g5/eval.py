import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import cfg, stats as S

LABEL = {"dl_flat": "docling-rs default (flat levels)", "dl_hh": "docling-rs heading_hierarchy (with outline)",
         "dl_hh_mask": "docling-rs heading_hierarchy (outline masked)", "ours_outline": "repair: outline anchors + TOC + font tiers",
         "ours_mask": "repair, outline masked (TOC + numbering + font tiers)", "ours_mask_norej": "repair masked, no false-heading rejection"}
SETS = {"comphrdoc": "Comp-HRDoc test (arXiv PDFs, gold TOC trees)", "pmc_jats": "PMC OA (CC BY/CC0), JATS section tree as gold"}


def s(recs, k, f):
    return sum(r["arms"][k][f] for r in recs if k in r["arms"])


def hf1(recs, k):
    return S.f1(s(recs, k, "tp"), s(recs, k, "np"), s(recs, k, "ng"))[2]


def ef1(recs, k):
    return S.f1(s(recs, k, "edge"), s(recs, k, "np"), s(recs, k, "ng"))[2]


def summarize():
    recs = []
    for f in sorted(glob.glob(os.path.join(cfg.RES, "g5", "metrics-*.jsonl"))):
        recs += cfg.jsonl(f)
    errs = [r for r in recs if "error" in r]
    recs = [r for r in recs if "error" not in r]
    test = [r for r in recs if S.split_of(r["id"]) == "test"]
    md = ["## Gap 5. Heading repair", ""]
    md.append("Candidates come from docling-rs default output (layout labels and text). The repair adds outline anchors (pdfium bookmarks, fuzzy title + page match), printed-TOC matching, numbering depth and per-document font tiers (size, weight), and rejects running heads (same text on 3+ pages or in the top/bottom 6%% band), captions (`Figure/Table N`), TOC lines and long sentences. Test split = 80%% of documents by hash; %d documents scored, %d errors." % (len(recs), len(errs)))
    md.append("")
    summ = {}
    for st, title in SETS.items():
        for gname in ("main", "outline"):
            rs = [r for r in test if r["set"] == st and any(k.startswith(gname + "|") for k in r["arms"])]
            if not rs:
                continue
            arms = sorted({k.split("|")[1] for r in rs for k in r["arms"] if k.startswith(gname + "|")}, key=list(LABEL).index)
            md.append("### %s, gold = %s (%d docs)" % (title, "authored tree" if gname == "main" else "PDF bookmarks (systems see the masked PDF)", len(rs)))
            md.append("")
            md.append("| Arm | Heading P | Heading R | Heading F1 [95% CI] | Level accuracy (matched) | Parent-edge F1 [95% CI] | False-heading rate | of which captions / running heads / other |")
            md.append("|---|---|---|---|---|---|---|---|")
            for a in arms:
                k = gname + "|" + a
                tp, np_, ng = s(rs, k, "tp"), s(rs, k, "np"), s(rs, k, "ng")
                p, rr, _ = S.f1(tp, np_, ng)
                hf = S.boot(rs, lambda x, k=k: hf1(x, k), B=1000)
                ef = S.boot(rs, lambda x, k=k: ef1(x, k), B=1000)
                fh = np_ - tp
                md.append("| %s | %s | %s | %s | %s | %s | %s | %d / %d / %d |" % (
                    LABEL[a], S.fmt(p), S.fmt(rr), S.ci(hf), S.fmt(S.ratio(s(rs, k, "lvl_ok"), tp)), S.ci(ef), S.fmt(S.ratio(fh, np_)),
                    s(rs, k, "f_cap"), s(rs, k, "f_rep"), s(rs, k, "f_oth")))
                summ["%s|%s|%s" % (st, gname, a)] = dict(hf1=hf[0], ef1=ef[0], lvl=S.ratio(s(rs, k, "lvl_ok"), tp), false=S.ratio(fh, np_))
            md.append("")
            pairs = []
            for a, b in (("dl_hh_mask", "ours_mask"), ("dl_flat", "ours_mask"), ("dl_hh", "ours_outline"), ("ours_mask_norej", "ours_mask")):
                ka, kb = gname + "|" + a, gname + "|" + b
                if not any(ka in r["arms"] for r in rs) or not any(kb in r["arms"] for r in rs):
                    continue
                pr = S.paired(rs, lambda x, k=ka: ef1(x, k), lambda x, k=kb: ef1(x, k), B=1000)
                pairs.append("| %s vs %s | %s | %s | %s [%s, %s] | %s |" % (LABEL[b], LABEL[a], S.fmt(pr["a"]), S.fmt(pr["b"]), S.fmt(pr["diff"]),
                                                                     S.fmt(pr["lo"]), S.fmt(pr["hi"]), S.fmt(pr["p"], 4)))
                cap_rep_a = s(rs, ka, "f_cap") + s(rs, ka, "f_rep")
                cap_rep_b = s(rs, kb, "f_cap") + s(rs, kb, "f_rep")
                summ["%s|%s|caprep|%s>%s" % (st, gname, a, b)] = (cap_rep_a, cap_rep_b)
            if pairs:
                md.append("Paired document bootstrap on parent-edge F1:")
                md.append("")
                md.append("| Comparison | Baseline | Candidate | Difference [95% CI] | p |")
                md.append("|---|---|---|---|---|")
                md += pairs
                md.append("")
    cpu = {}
    for r in recs:
        for k, v in r.get("cpu", {}).items():
            cpu.setdefault(k, []).append(v / max(1, r.get("pages", 1)))
    if cpu:
        md.append("CPU per page: " + ", ".join("%s %s s" % (k, S.fmt(sum(v) / len(v), 3)) for k, v in sorted(cpu.items())) + " (docling-rs arms include layout inference; repair excludes the shared docling-rs run).")
        md.append("")
    ex = [r for r in test if r.get("examples")][:3]
    for r in ex:
        md.append("Example %s: gold %s; docling-rs hh masked %s; repair %s." % (r["id"], r["examples"]["gold"][:6], r["examples"]["dl_hh_mask"][:6], r["examples"]["ours_mask"][:6]))
    md.append("")
    return "\n".join(md), summ


if __name__ == "__main__":
    print(summarize()[0])

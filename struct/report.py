import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import cfg, stats as S

GAPS = [("g8", "g8.eval"), ("g9", "g9.eval"), ("g12", "g12.eval"), ("g5", "g5.eval"), ("g4", "g4.eval"), ("g7", "g7.eval")]


def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict) or k not in d:
            return float("nan")
        d = d[k]
    return d


def verdicts(sm):
    out = []
    r8 = sm.get("g8", {})
    rec = g(r8, "R", "R2", "recovered")
    keep = g(r8, "clean_keep", "R2")
    out.append("| 8 Text-layer trust | routing R2 recovers %s of remapped critical values (target 0.90), keeps %s of correct native words on clean pages (target 0.995) | %s |" % (
        S.fmt(rec), S.fmt(keep, 4), "meets both targets" if rec >= 0.9 and keep >= 0.995 else "does not meet both targets"))
    r9 = sm.get("g9", {})
    out.append("| 9 Hidden text | fixture hidden-span recall %s, clean-doc false flags %s, visible text kept %s; docling-rs exposes %s of hidden spans today | %s |" % (
        S.fmt(g(r9, "fixture_recall")), S.fmt(g(r9, "clean_doc_falseflag")), S.fmt(g(r9, "visible_kept"), 4), S.fmt(g(r9, "fixture_dl_reach")),
        "meets targets" if g(r9, "fixture_recall") >= 0.95 and g(r9, "visible_kept") >= 0.995 else "below target"))
    r12 = sm.get("g12", {})
    out.append("| 12 Watermarks, redactions, labels | watermark F1 %s; page-label accuracy fused %s vs physical %s | %s |" % (
        S.fmt(g(r12, "wm", "f1")), S.fmt(g(r12, "labels", "fu")), S.fmt(g(r12, "labels", "phys")),
        "adopt" if g(r12, "wm", "f1") >= 0.9 and g(r12, "labels", "fu") >= 0.95 else "partial"))
    r5 = sm.get("g5", {})
    a = g(r5, "comphrdoc|main|ours_mask", "ef1")
    b = g(r5, "comphrdoc|main|dl_hh_mask", "ef1")
    out.append("| 5 Heading repair | Comp-HRDoc parent-edge F1 without outline: repair %s vs docling-rs heading_hierarchy %s | %s |" % (
        S.fmt(a), S.fmt(b), "gain >= 5 points" if a - b >= 0.05 else "gain < 5 points"))
    r4 = sm.get("g4", {})
    out.append("| 4 Nested lists | parent-edge F1 state machine %s vs docling-rs %s; false list items %s | %s |" % (
        S.fmt(g(r4, "ours", "edge_f1")), S.fmt(g(r4, "dl", "edge_f1")), S.fmt(g(r4, "ours", "false"), 4),
        "adopt" if g(r4, "ours", "edge_f1") - g(r4, "dl", "edge_f1") >= 0.05 and g(r4, "ours", "false") < 0.01 else "partial"))
    r7 = sm.get("g7", {})
    out.append("| 7 Cross-references | combined F1: figures %s, tables %s, citations %s (docling-rs: no typed links) | %s |" % (
        S.fmt(g(r7, "combined|fig", "f1")), S.fmt(g(r7, "combined|table", "f1")), S.fmt(g(r7, "combined|bibr", "f1")),
        "adopt" if min(g(r7, "combined|fig", "f1"), g(r7, "combined|table", "f1")) >= 0.9 else "partial"))
    return out


def main():
    parts, sm = [], {}
    for name, mod in GAPS:
        try:
            m = __import__(mod, fromlist=["summarize"])
            md, s = m.summarize()
            parts.append(md)
            sm[name] = s
        except Exception:
            parts.append("## %s\n\nReport generation failed:\n\n```\n%s\n```\n" % (name, traceback.format_exc()[-1500:]))
    head = ["# Round 4: text trust and document structure", "",
            "Converter under test: docling.rs 2.84.0 (`docling-rs==2.84.0` wheel, default CPU models, table structure off). All runs on GitHub-hosted ubuntu-24.04 runners. Run: %s." % os.environ.get("GITHUB_RUN_ID", "local"),
            "", "| Gap | Key result | Auto verdict against the research targets |", "|---|---|---|"]
    head += verdicts(sm)
    head.append("")
    txt = "\n".join(head + parts)
    os.makedirs(os.path.join(cfg.RES, "report"), exist_ok=True)
    with open(os.path.join(cfg.RES, "report", "REPORT.md"), "w", encoding="utf-8") as f:
        f.write(txt)
    with open(os.path.join(cfg.RES, "report", "summary.json"), "w", encoding="utf-8") as f:
        json.dump(sm, f, indent=1, default=str)
    print(txt)


if __name__ == "__main__":
    main()

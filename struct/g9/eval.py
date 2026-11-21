import glob
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import cfg, dl, stats as S
from g9 import vis

DH_HIDDEN = {"cover-rect-content", "cover-square-annot", "cover-square-annot-noap", "hidden-layer", "offpage-text", "render-mode-3", "white-text"}


def msum(c):
    return sum(c.values())


def load():
    recs = []
    for f in sorted(glob.glob(os.path.join(cfg.RES, "g9", "raw-*.jsonl"))):
        recs += cfg.jsonl(f)
    return recs


def page_hidden_tokens(v):
    return Counter(t for s in v["spans"] if s["hidden"] for t in dl.tokens(s["text"]))


def summarize():
    recs = load()
    md = ["## Gap 9. Hidden text and prompt injection", ""]
    summ = {}
    fx = [r for r in recs if r["set"] == "fixture" and "vis" in r]
    by_tech = {}
    for r in fx:
        v = r["vis"]
        H = page_hidden_tokens(v)
        dtext = dl.norm(r.get("dl", {}).get("text", "")).lower()
        F = Counter(vis.filtered_tokens(v))
        for sp in r["gold"]["spans"]:
            can = sp["text"].split()[-1]
            if sp["tech"] == "metadata":
                det = any(can in n["text"] and n["instr"] for n in v["nonpage"])
                cls = "metadata_instruction" if det else "-"
            else:
                st = Counter(dl.tokens(sp["text"]))
                det = msum(st & H) / max(1, msum(st)) >= 0.8
                cls = next((s["cls"] for s in v["spans"] if can in s["text"]), "not_extracted")
            by_tech.setdefault(sp["tech"], []).append(dict(det=det, cls=cls, dl=can.lower() in dtext, filt=F[can] > 0,
                                                           extracted=any(can in s["text"] for s in v["spans"])))
    md.append("### Own fixtures (%d documents: %d with hidden spans, %d clean with false-flag traps)" % (
        len(fx), sum(1 for r in fx if r["gold"]["injected"]), sum(1 for r in fx if not r["gold"]["injected"])))
    md.append("")
    md.append("| Technique | Spans | Hidden-span recall [95% CI] | Main attribution | Reaches docling-rs output today | Reaches filtered output |")
    md.append("|---|---|---|---|---|---|")
    allk = alln = 0
    for t in sorted(by_tech):
        xs = by_tech[t]
        k = sum(x["det"] for x in xs)
        allk += k
        alln += len(xs)
        w = S.wilson(k, len(xs))
        cl = Counter(x["cls"] for x in xs).most_common(1)[0][0]
        md.append("| %s | %d | %s [%s, %s] | %s | %s | %s |" % (t, len(xs), S.fmt(w[0]), S.fmt(w[1]), S.fmt(w[2]), cl,
                                                         S.fmt(S.ratio(sum(x["dl"] for x in xs), len(xs))),
                                                         S.fmt(S.ratio(sum(x["filt"] for x in xs), len(xs)))))
    w = S.wilson(allk, alln)
    dl_all = sum(x["dl"] for xs in by_tech.values() for x in xs)
    md.append("| **all** | %d | %s [%s, %s] | | %s | %s |" % (alln, S.fmt(w[0]), S.fmt(w[1]), S.fmt(w[2]), S.fmt(S.ratio(dl_all, alln)),
                                                         S.fmt(S.ratio(sum(x["filt"] for xs in by_tech.values() for x in xs), alln))))
    md.append("")
    summ["fixture_recall"] = w[0]
    summ["fixture_dl_reach"] = S.ratio(dl_all, alln)
    cl = [r for r in fx if not r["gold"]["injected"]]
    traps = {}
    vt = vk = vf = 0
    for r in fx:
        v = r["vis"]
        V = Counter(t for s in r["gold"]["visible"] for t in dl.tokens(s))
        H = page_hidden_tokens(v) - Counter(t for sp in r["gold"]["spans"] for t in dl.tokens(sp["text"]))
        F = Counter(vis.filtered_tokens(v))
        vt += msum(V)
        vk += msum(V & F)
        vf += msum(V & H)
        if not r["gold"]["injected"]:
            anyf = any(s["hidden"] for s in v["spans"])
            for t in r["gold"]["traps"] or ["none"]:
                traps.setdefault(t, []).append(anyf)
    md.append("False flags on clean fixtures (document flagged if any span is marked hidden):")
    md.append("")
    md.append("| Trap present | Clean docs | Docs falsely flagged |")
    md.append("|---|---|---|")
    for t in sorted(traps):
        md.append("| %s | %d | %s |" % (t, len(traps[t]), S.fmt(S.ratio(sum(traps[t]), len(traps[t])))))
    nf = sum(1 for r in cl if any(s["hidden"] for s in r["vis"]["spans"]))
    md.append("| **any clean doc** | %d | %s |" % (len(cl), S.fmt(S.ratio(nf, len(cl)))))
    md.append("")
    md.append("Legitimate visible text kept after removing hidden spans: %s (%d of %d tokens); visible tokens wrongly flagged: %s."
              % (S.fmt(S.ratio(vk, vt), 4), vk, vt, S.fmt(S.ratio(vf, vt), 4)))
    md.append("")
    summ["clean_doc_falseflag"] = S.ratio(nf, len(cl))
    summ["visible_kept"] = S.ratio(vk, vt)
    cr = [r for r in recs if r["set"] == "cracked" and "vis" in r]
    if cr:
        groups = {}
        for r in cr:
            groups.setdefault(r["gold"]["group"], {})[r["gold"]["pdf_role"]] = r
        fam, reg, ben, conf, exs = {}, {}, [], {}, []
        empty = 0
        for g, roles in groups.items():
            inj, org = roles.get("injected_attack"), roles.get("benign_original")
            for role in ("benign_original", "benign_confounder"):
                b = roles.get(role)
                if b:
                    sp = b["vis"]["spans"]
                    toks = sum(len(dl.tokens(s["text"])) for s in sp)
                    ht = sum(len(dl.tokens(s["text"])) for s in sp if s["hidden"])
                    x = dict(anyf=any(s["hidden"] for s in sp), toks=toks, ht=ht)
                    if role == "benign_original":
                        ben.append(x)
                    if role == "benign_confounder":
                        conf.setdefault(b["gold"].get("benign_confounder_family", "?"), []).append(x)
            if not inj or not org:
                continue
            G = Counter(vis.all_tokens(inj["vis"])) - Counter(vis.all_tokens(org["vis"]))
            if not G:
                empty += 1
                continue
            H = Counter(vis.hidden_tokens(inj["vis"]))
            D = Counter(dl.tokens(inj.get("dl", {}).get("text", ""))) - Counter(dl.tokens(org.get("dl", {}).get("text", "")))
            Fd = Counter(vis.filtered_tokens(inj["vis"])) - Counter(vis.filtered_tokens(org["vis"]))
            x = dict(rec=msum(G & H) / msum(G), dl=msum(G & D) / msum(G), filt=msum(G & Fd) / msum(G))
            if len(exs) < 8:
                exs.append((inj["gold"].get("attack_family"), " ".join(list(G.elements())[:8]), round(x["rec"], 2), round(x["dl"], 2)))
            fam.setdefault(inj["gold"].get("attack_family", "?"), []).append(x)
            reg.setdefault(inj["gold"].get("rendering_regime", "?"), []).append(x)
        md.append("### CrackedPDFs (MIT, HF revision 02d7e0b; paper test split, up to 40 triads per attack family)")
        md.append("")
        md.append("Injected text = tokens present in the injected PDF but not in its paired benign original (page text plus metadata/annotation strings). %d triads had no extractable injected text and are excluded." % empty)
        md.append("")
        for title, dd in (("attack family", fam), ("rendering regime", reg)):
            md.append("| %s | Docs | Hidden-token recall | Docs detected (recall >= 0.5) | Injected tokens reaching docling-rs output | Reaching filtered output |" % title.capitalize())
            md.append("|---|---|---|---|---|---|")
            for k in sorted(dd):
                xs = dd[k]
                md.append("| %s | %d | %s | %s | %s | %s |" % (k, len(xs), S.fmt(sum(x["rec"] for x in xs) / len(xs)),
                                                            S.fmt(sum(x["rec"] >= 0.5 for x in xs) / len(xs)),
                                                            S.fmt(sum(x["dl"] for x in xs) / len(xs)), S.fmt(sum(x["filt"] for x in xs) / len(xs))))
            md.append("")
        allx = [x for xs in fam.values() for x in xs]
        if allx:
            summ["cracked_recall"] = sum(x["rec"] for x in allx) / len(allx)
            summ["cracked_dl_reach"] = sum(x["dl"] for x in allx) / len(allx)
        if exs:
            md.append("Injected-token examples (family, first tokens, hidden recall, docling-rs reach): " + "; ".join("%s: `%s` %s/%s" % e for e in exs) + ".")
            md.append("")
        md.append("False flags on benign originals (no hidden content by construction): %d PDFs, flagged docs %s, flagged tokens %s. Benign confounders below carry deliberately hidden or low-visibility benign content, so visibility flags there are expected; the table shows how often they are flagged." % (
            len(ben), S.fmt(S.ratio(sum(x["anyf"] for x in ben), len(ben))), S.fmt(S.ratio(sum(x["ht"] for x in ben), sum(x["toks"] for x in ben)), 4)))
        md.append("")
        if conf:
            md.append("| Benign confounder family | Docs | Docs flagged | Tokens flagged |")
            md.append("|---|---|---|---|")
            for k in sorted(conf):
                xs = conf[k]
                md.append("| %s | %d | %s | %s |" % (k, len(xs), S.fmt(sum(x["anyf"] for x in xs) / len(xs)),
                                                    S.fmt(S.ratio(sum(x["ht"] for x in xs), sum(x["toks"] for x in xs)), 4)))
            md.append("")
    dh = [r for r in recs if r["set"] == "dochush" and "vis" in r]
    if dh:
        ok = 0
        md.append("### DocHush public fixtures (Apache-2.0 code, CC BY 4.0 corpus, commit 674c23d)")
        md.append("")
        md.append("| File | Expected hidden text | Flagged | Classes |")
        md.append("|---|---|---|---|")
        for r in sorted(dh, key=lambda r: r["id"]):
            f = any(s["hidden"] for s in r["vis"]["spans"])
            e = r["id"] in DH_HIDDEN
            ok += f == e
            md.append("| %s | %s | %s | %s |" % (r["id"], e, f, ", ".join(sorted({s["cls"] for s in r["vis"]["spans"] if s["hidden"]})) or "-"))
        md.append("")
        md.append("Agreement with DocHush expected hidden-text findings: %d of %d files." % (ok, len(dh)))
        md.append("")
    cpu = [r["vis"]["cpu"] for r in recs if "vis" in r]
    if cpu:
        md.append("Visibility check CPU per document: mean %s s, p95 %s s (three or five pdfium renders at 144 dpi per page)." % (
            S.fmt(sum(cpu) / len(cpu), 2), S.fmt(S.pct(cpu, 0.95), 2)))
    errs = sum(1 for r in recs if "vis_error" in r or "dl_error" in r)
    md.append("Errors: %d of %d documents." % (errs, len(recs)))
    md.append("")
    return "\n".join(md), summ


if __name__ == "__main__":
    print(summarize()[0])

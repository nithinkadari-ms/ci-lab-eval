"""Gap 1 report. usage: agg_ocr.py ARTDIR OUT.md OUT.json"""
import glob
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import boot_ci, fmt, jl_read, pfmt, sign_test  # noqa: E402

ENG = ["v6s", "v6m", "v5en", "crnn", "viptr", "tess_fast", "tess_best"]
TAUS = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.98]
L = []


def P(s=""):
    L.append(s)


def crop_stats(pages, eng, tau=None, mode=None):
    """micro CER/WER/numeric over crops with GT; per-group CER for paired tests."""
    E = N = WE = NW = NH = NN = 0
    grp = defaultdict(lambda: [0, 0])
    for p in pages:
        for c in p["crops"]:
            if c["n"] == 0:
                continue
            if tau is None:
                r = c[eng]
            else:
                c6, ct = c["v6s"][2], c["tess_best"][2]
                use = c6 < tau and (mode == "rep" or ct > c6)
                r = c["tess_best"] if use else c["v6s"]
            E += r[0]
            N += c["n"]
            WE += r[1]
            NW += c["nw"]
            NH += r[3]
            NN += c["nnum"]
            grp[p["group"]][0] += r[0]
            grp[p["group"]][1] += c["n"]
    return {"cer": E / max(1, N), "wer": WE / max(1, NW), "num": NH / max(1, NN), "n": N,
            "grp": {g: e / max(1, n) for g, (e, n) in grp.items()}}


def e2e_stats(pages, arm):
    S = defaultdict(float)
    grp = defaultdict(lambda: [0, 0])
    ms = []
    for p in pages:
        r = p["e2e"].get(arm)
        if r is None:
            continue
        for k in ("ed", "n", "bag_hit", "bag_pred", "bag_gt", "num_hit", "num_pred", "num_gt", "fld_hit", "fld_n"):
            S[k] += r[k]
        grp[p["group"]][0] += r["ed"]
        grp[p["group"]][1] += r["n"]
        if "ms" in r:
            ms.append(r["ms"])
        if "ms_pre" in r:
            ms.append(r["ms_pre"])
    P_ = S["bag_hit"] / max(1, S["bag_pred"])
    R_ = S["bag_hit"] / max(1, S["bag_gt"])
    return {"cer": S["ed"] / max(1, S["n"]), "bag_f1": 2 * P_ * R_ / max(1e-9, P_ + R_),
            "num_rec": S["num_hit"] / max(1, S["num_gt"]), "num_prec": S["num_hit"] / max(1, S["num_pred"]),
            "fld": S["fld_hit"] / max(1, S["fld_n"]), "grp": {g: e / max(1, n) for g, (e, n) in grp.items()},
            "ms": sum(ms) / len(ms) if ms else None}


def paired(base, cand):
    gs = sorted(set(base) & set(cand))
    diffs = [base[g] - cand[g] for g in gs]
    w, l, p = sign_test(diffs)
    lo, hi = boot_ci(diffs)
    return w, l, p, lo, hi, len(gs)


def main():
    art, out_md, out_js = sys.argv[1], sys.argv[2], sys.argv[3]
    pages = [r for r in jl_read(glob.glob(os.path.join(art, "**", "ocr-pages-*.jsonl"), recursive=True))]
    regs = [r for r in jl_read(glob.glob(os.path.join(art, "**", "ocr-regions-*.jsonl"), recursive=True))]
    errs = [r for r in pages + regs if "error" in r]
    pages = [r for r in pages if "error" not in r]
    regs = [r for r in regs if "error" not in r]
    res = {"n_pages": len(pages), "n_regions": len(regs), "errors": len(errs)}
    P("## Gap 1. OCR on scanned English documents")
    P()
    P(f"Pages: {len(pages)} (errors {len(errs)}); OmniDocBench regions: {len(regs)}. Baseline `v6s` = docling.rs "
      "models-v1 `ocr_det.onnx` + `ocr_rec_v6.onnx` (PP-OCRv6 **small**, per the release manifest), with docling.rs "
      "pre/post-processing ported to Python. CER/WER are micro-averaged; paired tests are per document "
      "(sign test on per-document CER, bootstrap 95% CI of the mean CER reduction), on the held-out test split.")
    P()
    slices = [("all", lambda p: True)]
    for ds in ("funsd", "sroie", "synth"):
        slices.append((ds, lambda p, ds=ds: p["ds"] == ds))
    for d in ("clean", "lowdpi", "blur", "noise", "skew", "curved", "jpeg", "faded"):
        slices.append(("synth:" + d, lambda p, d=d: p["ds"] == "synth" and p["defect"] == d))
    slices.append(("synth:tiny_print", lambda p: p["ds"] == "synth" and p.get("kind") == "tiny"))
    P("### 1a. Same detector crops (PP-OCRv6 small boxes), test split: CER / WER / numeric-token exact")
    P()
    P("| slice | crops chars | " + " | ".join(ENG) + " |")
    P("|---" * (len(ENG) + 2) + "|")
    res["crop"] = {}
    test = [p for p in pages if p["split"] == "test"]
    dev = [p for p in pages if p["split"] == "dev"]
    for name, f in slices:
        ps = [p for p in test if f(p)]
        if not ps:
            continue
        st = {e: crop_stats(ps, e) for e in ENG}
        res["crop"][name] = {e: {k: v for k, v in st[e].items() if k != "grp"} for e in ENG}
        P(f"| {name} | {st['v6s']['n']} | " + " | ".join(
            f"{st[e]['cer']:.3f} / {st[e]['wer']:.3f} / {st[e]['num']:.3f}" for e in ENG) + " |")
    P()
    P("Paired per-document CER vs v6s (test split; wins = documents where the challenger has lower CER):")
    P()
    P("| slice | challenger | docs | wins | losses | p | mean CER reduction 95% CI |")
    P("|---|---|---|---|---|---|---|")
    for name, f in slices[:4] + [s for s in slices if s[0].startswith("synth:")]:
        ps = [p for p in test if f(p)]
        if not ps:
            continue
        base = crop_stats(ps, "v6s")["grp"]
        for e in ENG[1:]:
            w, l, pv, lo, hi, n = paired(base, crop_stats(ps, e)["grp"])
            P(f"| {name} | {e} | {n} | {w} | {l} | {pfmt(pv)} | [{lo:+.4f}, {hi:+.4f}] |")
    P()
    P("### 1b. Tesseract best only on low-confidence lines (threshold picked on the dev split)")
    P()
    best = {}
    for mode in ("rep", "rep_if_higher"):
        scores = [(crop_stats(dev, None, t, mode)["cer"], t) for t in TAUS]
        best[mode] = min(scores)[1]
    P("| mode | tau (dev) | test CER | v6s test CER | docs | wins | losses | p | CI |")
    P("|---|---|---|---|---|---|---|---|---|")
    res["hybrid"] = {}
    b = crop_stats(test, "v6s")
    for mode, t in best.items():
        h = crop_stats(test, None, t, mode)
        w, l, pv, lo, hi, n = paired(b["grp"], h["grp"])
        res["hybrid"][mode] = {"tau": t, "cer": h["cer"], "base": b["cer"], "p": pv}
        P(f"| {mode} | {t} | {h['cer']:.4f} | {b['cer']:.4f} | {n} | {w} | {l} | {pfmt(pv)} | [{lo:+.4f}, {hi:+.4f}] |")
    P()
    P("### 1c. End to end (detector + recognizer), test split")
    P()
    arms = ENG + ["v6m_det+rec", "tess_fast_page", "tess_best_page", f"hyb_rep_{best['rep']}",
                  f"hyb_rep_if_higher_{best['rep_if_higher']}", "pre_deskew", "pre_clahe", "pre_denoise", "pre_uvdoc",
                  "pre_gated", "pre_gated_uvdoc"]
    res["e2e"] = {}
    for name, f in slices:
        ps = [p for p in test if f(p)]
        if not ps:
            continue
        P(f"**{name}** ({len(ps)} pages)")
        P()
        P("| arm | page CER | bag-of-words F1 | numeric recall | numeric precision | critical fields exact | "
          "docs | wins | losses | p (CER vs v6s) | extra ms/page |")
        P("|---|---|---|---|---|---|---|---|---|---|---|")
        base = e2e_stats(ps, "v6s")
        res["e2e"][name] = {}
        for a in arms:
            s = e2e_stats(ps, a)
            res["e2e"][name][a] = {k: v for k, v in s.items() if k != "grp"}
            if a == "v6s":
                w = l = n = 0
                pv = None
            else:
                w, l, pv, _, _, n = paired(base["grp"], s["grp"])
            P(f"| {a} | {s['cer']:.4f} | {s['bag_f1']:.4f} | {s['num_rec']:.4f} | {s['num_prec']:.4f} | "
              f"{s['fld']:.4f} | {n} | {w} | {l} | {pfmt(pv)} | {fmt(s['ms'], 0)} |")
        P()
    P("### 1d. Gate triggers by synthetic defect (share of pages where each gate fired)")
    P()
    P("| defect | pages | deskew | clahe | denoise | uvdoc |")
    P("|---|---|---|---|---|---|")
    by = defaultdict(list)
    for p in pages:
        by[p["defect"]].append(p)
    for d, ps in sorted(by.items()):
        P(f"| {d} | {len(ps)} | " + " | ".join(
            f"{sum(p['gates'][g] for p in ps) / len(ps):.2f}" for g in ("deskew", "clahe", "denoise", "uvdoc")) + " |")
    P()
    if regs:
        P("### 1e. OmniDocBench English text regions (detector on the region crop, all regions)")
        P()
        cols = ENG + ["tess_best_block"]
        P("| slice | regions | " + " | ".join(cols) + " (CER / WER) |")
        P("|---" * (len(cols) + 2) + "|")
        res["odb"] = {}
        for name, f in (("all", lambda r: True), ("hard sources", lambda r: r["defect"] == "odb_hard"),
                        ("other sources", lambda r: r["defect"] == "odb_other")):
            rs = [r for r in regs if f(r)]
            if not rs:
                continue
            n = sum(r["n"] for r in rs)
            row = {}
            for e in cols:
                ce = sum(r[e][0] for r in rs) / max(1, n)
                we = sum(r[e][1] for r in rs) / max(1, sum(r[e][2] for r in rs))
                row[e] = (ce, we)
            res["odb"][name] = row
            P(f"| {name} | {len(rs)} | " + " | ".join(f"{row[e][0]:.3f} / {row[e][1]:.3f}" for e in cols) + " |")
        P()
        P("| challenger | pages (groups) | wins | losses | p | CI (CER reduction vs v6s) |")
        P("|---|---|---|---|---|---|")
        gb = defaultdict(lambda: defaultdict(lambda: [0, 0]))
        for r in regs:
            for e in cols:
                gb[e][r["group"]][0] += r[e][0]
                gb[e][r["group"]][1] += r["n"]
        base = {g: a / max(1, b) for g, (a, b) in gb["v6s"].items()}
        for e in cols[1:]:
            c = {g: a / max(1, b) for g, (a, b) in gb[e].items()}
            w, l, pv, lo, hi, n = paired(base, c)
            P(f"| {e} | {n} | {w} | {l} | {pfmt(pv)} | [{lo:+.4f}, {hi:+.4f}] |")
        P()
    tj = glob.glob(os.path.join(art, "**", "ocr-timing.json"), recursive=True)
    if tj:
        t = json.load(open(tj[0]))
        res["timing"] = t
        P(f"### 1f. Speed and memory (one thread, own process; {t['machine'].get('model', '')})")
        P()
        P("| component | items | load ms | mean ms | p50 ms | p95 ms | peak RSS MB |")
        P("|---|---|---|---|---|---|---|")
        for r in t["rows"]:
            if "error" in r:
                P(f"| {r['what']} | error: {r['error'][:80]} | | | | | |")
            else:
                P(f"| {r['what']} | {r['n']} | {r['load_ms']:.0f} | {r['mean_ms']:.1f} | {r['p50_ms']:.1f} | "
                  f"{r['p95_ms']:.1f} | {r['peak_rss_mb']:.0f} |")
        P()
    if errs:
        P("Errors (first 5): " + "; ".join(f"{e['id']}: {e['error'][:120]}" for e in errs[:5]))
        P()
    open(out_md, "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(res, open(out_js, "w"), indent=1)


if __name__ == "__main__":
    main()

"""Report for the gap-1 extra challengers. usage: extra_agg.py ARTDIR OUT.md OUT.json"""
import glob
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import boot_ci, jl_read, pfmt, sign_test  # noqa: E402

L = []


def P(s=""):
    L.append(s)


def crop_stats(pages, eng, pick=None):
    E = N = WE = NW = NH = NN = 0
    grp = defaultdict(lambda: [0, 0])
    for p in pages:
        for c in p.get("crops", []):
            if c["n"] == 0 or (eng is not None and eng not in c):
                continue
            r = pick(c) if pick else c[eng]
            E += r[0]
            N += c["n"]
            WE += r[1]
            NW += c["nw"]
            NH += r[2]
            NN += c["nnum"]
            grp[p["group"]][0] += r[0]
            grp[p["group"]][1] += c["n"]
    return {"cer": E / max(1, N), "wer": WE / max(1, NW), "num": NH / max(1, NN), "chars": N,
            "grp": {g: e / max(1, n) for g, (e, n) in grp.items()}}


def paired(a, b):
    gs = sorted(set(a) & set(b))
    d = [a[g] - b[g] for g in gs]
    w, l, p = sign_test(d)
    lo, hi = boot_ci(d)
    return w, l, p, lo, hi, len(gs)


def main():
    art, out_md, out_js = sys.argv[1], sys.argv[2], sys.argv[3]
    rows = jl_read(glob.glob(os.path.join(art, "**", "extra-*.jsonl"), recursive=True))
    infos = {r["info"].get("group", "all"): r["info"] for r in rows if "info" in r}
    errs = [r for r in rows if "error" in r]
    by = {}
    mism = 0
    for r in rows:
        if "id" not in r or "error" in r:
            continue
        b0 = by.get(r["id"])
        if b0 is None:
            by[r["id"]] = r
            continue
        if r.get("crops"):
            if not b0.get("crops"):
                b0["crops"] = r["crops"]
            elif len(b0["crops"]) == len(r["crops"]):
                for c1, c2 in zip(b0["crops"], r["crops"]):
                    for kk, v in c2.items():
                        c1.setdefault(kk, v)
            else:
                mism += 1
        for kk in ("e2e", "ms"):
            for k2, v in (r.get(kk) or {}).items():
                b0.setdefault(kk, {}).setdefault(k2, v)
        for kk in ("docres_gate", "docres_task", "docres_why", "lap_var", "n_crops", "n_word_crops"):
            if kk in r:
                b0.setdefault(kk, r[kk])
    main_dir = sys.argv[4] if len(sys.argv) > 4 else None
    v6m_pages = 0
    if main_dir:
        for m in jl_read(glob.glob(os.path.join(main_dir, "**", "ocr-pages-*.jsonl"), recursive=True)):
            e = by.get(m.get("id"))
            if e is None or "error" in m or not e.get("crops") or not m.get("crops"):
                continue
            if len(m["crops"]) != len(e["crops"]) or "v6m" not in m["crops"][0]:
                continue
            for c1, c2 in zip(e["crops"], m["crops"]):
                if c1["n"] == c2["n"] and "v6m" in c2:
                    ed, we, conf, nh, _ = c2["v6m"]
                    c1.setdefault("v6m", [ed, we, nh, conf])
            v6m_pages += 1
    pages = list(by.values())
    res = {}
    P("## OCR: extra challengers")
    P()
    P(f"Same pages and the same PP-OCRv6 small detector crops as the main OCR test (UnionST and DocRes: every 4th "
      f"page; UniRec: every 8th page). Pages with records: {len(pages)}, line crops: "
      f"{sum(len(p.get('crops', [])) for p in pages)}, page errors {len(errs)}, crop-count mismatches between jobs "
      f"{mism}. PP-OCRv6 medium on the same crops is taken from the main OCR records ({v6m_pages} pages matched). "
      "Paired tests per document; only the second-reader threshold is tuned (dev split).")
    P()
    for g, i in sorted(infos.items()):
        P(f"- {g}: " + ", ".join(f"{k} {v:.1f}" if isinstance(v, float) else f"{k} {v}" for k, v in i.items() if k != "group"))
    P()
    slices = [("all", lambda p: True), ("funsd", lambda p: p["ds"] == "funsd"), ("sroie", lambda p: p["ds"] == "sroie"),
              ("synth", lambda p: p["ds"] == "synth")]
    for d in ("clean", "lowdpi", "blur", "noise", "skew", "curved", "jpeg", "faded"):
        slices.append(("synth:" + d, lambda p, d=d: p["ds"] == "synth" and p["defect"] == d))
    engs = ["v6s", "v6m", "unionst_line", "unionst_words"]
    P("### Same crops: CER / WER / numeric-token exact")
    P()
    P("| slice | chars | " + " | ".join(engs) + " | unirec subset: v6s | v6m | unirec |")
    P("|---" * (len(engs) + 5) + "|")
    res["crop"] = {}
    for name, f in slices:
        ps = [p for p in pages if f(p)]
        if not ps:
            continue
        st = {e: crop_stats(ps, e) for e in engs}
        up = [p for p in ps if any("unirec" in c for c in p.get("crops", []))]
        su = {e: crop_stats(up, e) for e in ("v6s", "v6m", "unirec")} if up else None
        res["crop"][name] = {e: {k: v for k, v in st[e].items() if k != "grp"} for e in engs}
        cell = lambda s: f"{s['cer']:.3f} / {s['wer']:.3f} / {s['num']:.3f}"  # noqa: E731
        P(f"| {name} | {st['v6s']['chars']} | " + " | ".join(cell(st[e]) for e in engs) + " | "
          + (" | ".join(cell(su[e]) for e in ("v6s", "v6m", "unirec")) if su else "- | - | -") + " |")
    P()
    P("Paired per-document CER vs PP-OCRv6 small and medium (wins = challenger lower CER):")
    P()
    P("| slice | challenger | baseline | docs | wins | losses | p | mean CER reduction 95% CI |")
    P("|---|---|---|---|---|---|---|---|")
    for name, f in slices[:4]:
        ps = [p for p in pages if f(p)]
        for ch in ("unionst_line", "unionst_words", "unirec"):
            for base in ("v6s", "v6m"):
                sub = [p for p in ps if any(ch in c for c in p.get("crops", []))]
                if not sub:
                    continue
                both = [dict(p, crops=[c for c in p.get("crops", []) if ch in c and base in c]) for p in sub]
                w, l, pv, lo, hi, n = paired(crop_stats(both, base)["grp"], crop_stats(both, ch)["grp"])
                P(f"| {name} | {ch} | {base} | {n} | {w} | {l} | {pfmt(pv)} | [{lo:+.4f}, {hi:+.4f}] |")
    P()
    P("### UnionST on long lines (word-level model, max 25 characters, input squeezed to at most 128 x 32)")
    P()
    P("| GT line length (chars) | crops | v6s CER | UnionST whole line CER | UnionST word-split CER |")
    P("|---|---|---|---|---|")
    for lo_, hi_ in ((1, 10), (11, 25), (26, 50), (51, 100), (101, 10000)):
        cs = [c for p in pages for c in p.get("crops", []) if lo_ <= c["n"] <= hi_]
        if not cs:
            continue
        n = sum(c["n"] for c in cs)
        P(f"| {lo_}-{hi_ if hi_ < 10000 else '+'} | {len(cs)} | {sum(c['v6s'][0] for c in cs) / n:.3f} | "
          f"{sum(c['unionst_line'][0] for c in cs) / n:.3f} | {sum(c['unionst_words'][0] for c in cs) / n:.3f} |")
    P()
    P("### UnionST as a second reader on low-confidence PP-OCRv6 small lines")
    P()
    dev = [p for p in pages if p["split"] == "dev"]
    test = [p for p in pages if p["split"] == "test"]
    confs = sorted(c["v6s"][3] for p in dev for c in p.get("crops", []) if c["n"])
    best = None
    for q in (0.10, 0.12, 0.15, 0.18, 0.20):
        tau = confs[int(q * (len(confs) - 1))] if confs else 0
        pick = lambda c, t=tau: c["merged"] if c["v6s"][3] <= t else c["v6s"]  # noqa: E731
        cer = crop_stats(dev, None, pick)["cer"]
        if best is None or cer < best[0]:
            best = (cer, q, tau)
    if best:
        _, q, tau = best
        pick = lambda c: c["merged"] if c["v6s"][3] <= tau else c["v6s"]  # noqa: E731
        b = crop_stats(test, "v6s")
        h = crop_stats(test, None, pick)
        share = sum(1 for p in test for c in p.get("crops", []) if c["n"] and c["v6s"][3] <= tau) / max(
            1, sum(1 for p in test for c in p.get("crops", []) if c["n"]))
        w, l, pv, lo, hi, n = paired(b["grp"], h["grp"])
        res["second_reader"] = {"budget_dev": q, "tau": tau, "share_test": share, "cer": h["cer"], "base": b["cer"],
                                "num": h["num"], "base_num": b["num"], "p": pv}
        P(f"Threshold from the dev split: re-read the lowest {q:.0%} confidence lines (conf <= {tau:.3f}); on the test "
          f"split {share:.1%} of lines were re-read. Merge: word alignment by edit distance; a token with digits is "
          f"only changed when both readers agree.")
        P()
        P("| test split | CER | WER | numeric exact | docs better / worse | p | CI |")
        P("|---|---|---|---|---|---|---|")
        P(f"| PP-OCRv6 small | {b['cer']:.4f} | {b['wer']:.4f} | {b['num']:.4f} | - | - | - |")
        P(f"| + UnionST second reader | {h['cer']:.4f} | {h['wer']:.4f} | {h['num']:.4f} | {w} / {l} | {pfmt(pv)} | "
          f"[{lo:+.4f}, {hi:+.4f}] |")
        P()
    P("### DocRes as gated cleanup (page CER end to end, PP-OCRv6 small det+rec)")
    P()
    P("| case | pages | CER without | CER with DocRes | pages better / worse | median DocRes s/page |")
    P("|---|---|---|---|---|---|")
    groups = defaultdict(list)
    for p in pages:
        e = p.get("e2e", {})
        if "docres_v6s" in e:
            key = ("forced on clean pages (gate did not fire)" if p.get("docres_why") == "forced_clean"
                   else f"gate: {p['docres_task']} on {p['ds']}:{p['defect']}")
            groups[key].append(p)
    res["docres"] = {}
    for key, ps in sorted(groups.items()):
        a = sum(p["e2e"]["v6s"]["ed"] for p in ps) / max(1, sum(p["e2e"]["v6s"]["n"] for p in ps))
        b = sum(p["e2e"]["docres_v6s"]["ed"] for p in ps) / max(1, sum(p["e2e"]["docres_v6s"]["n"] for p in ps))
        d = [p["e2e"]["v6s"]["ed"] / max(1, p["e2e"]["v6s"]["n"]) - p["e2e"]["docres_v6s"]["ed"] / max(1, p["e2e"]["docres_v6s"]["n"]) for p in ps]
        w, l, _ = sign_test(d)
        s = sorted(p["e2e"]["docres_v6s"]["ms_docres"] for p in ps)[len(ps) // 2] / 1000
        res["docres"][key] = {"n": len(ps), "without": a, "with": b}
        P(f"| {key} | {len(ps)} | {a:.4f} | {b:.4f} | {w} / {l} | {s:.1f} |")
    gate = defaultdict(lambda: [0, 0])
    for p in pages:
        gate[p["defect"]][0] += bool(p.get("docres_gate"))
        gate[p["defect"]][1] += 1
    P()
    P("Gate firing rate by page type: " + ", ".join(f"{k} {a}/{n}" for k, (a, n) in sorted(gate.items())))
    P()
    P("### CPU time on the same crops (ms per line crop, 4 threads, shared runner)")
    P()
    tot = defaultdict(float)
    cnt = defaultdict(int)
    for p in pages:
        for k_, v in p.get("ms", {}).items():
            tot[k_] += v
            cnt[k_] += p["n_crops"]
    P(", ".join(f"{k_}: {tot[k_] / max(1, cnt[k_]):.1f}" for k_ in tot))
    P()
    if errs:
        P("Errors (first 3): " + "; ".join(f"{e['id']}: {e['error'][:120]}" for e in errs[:3]))
        P()
    open(out_md, "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(res, open(out_js, "w"), indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()

"""Gap 2 report. usage: agg_charts.py ARTDIR OUT.md OUT.json"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import jl_read, pfmt, sign_test  # noqa: E402

L = []


def P(s=""):
    L.append(s)


def summ(rs):
    n = len(rs)
    cov = [r for r in rs if not r.get("abstain")]
    o = {"n": n, "coverage": len(cov) / max(1, n),
         "rms_all": sum(r["rms_f1"] for r in rs) / max(1, n),
         "rms_cov": sum(r["rms_f1"] for r in cov) / max(1, len(cov)) if cov else None,
         "rmsn_all": sum(r["rmsn_f1"] for r in rs) / max(1, n),
         "ms": sorted(r["ms"] for r in rs)[n // 2] if n else None}
    pts = sum(r.get("pts", 0) for r in rs)
    if pts:
        o["found"] = sum(r.get("pts_found", 0) for r in rs) / pts
        o["w1"] = sum(r.get("within1", 0) for r in rs) / pts
        o["w5"] = sum(r.get("within5", 0) for r in rs) / pts
    pf = [r["point_f1"] for r in rs if "point_f1" in r]
    if pf:
        o["point_f1"] = sum(pf) / len(pf)
    return o


def row(name, o):
    f = lambda v: "-" if v is None else f"{v:.3f}"  # noqa: E731
    ms = "-" if o["ms"] is None else f"{o['ms']:.0f}"
    P(f"| {name} | {o['n']} | {o['coverage']:.3f} | {f(o['rms_all'])} | {f(o['rms_cov'])} | {f(o['rmsn_all'])} | "
      f"{f(o.get('found'))} | {f(o.get('w1'))} | {f(o.get('w5'))} | {f(o.get('point_f1'))} | {ms} |")


def main():
    art, out_md, out_js = sys.argv[1], sys.argv[2], sys.argv[3]
    rs = jl_read(glob.glob(os.path.join(art, "**", "charts-*.jsonl"), recursive=True))
    ours = [r for r in rs if r["method"] in ("vector", "raster")]
    dep = [r for r in rs if r["method"] == "deplot"]
    res = {}
    P("## Gap 2. Charts")
    P()
    P("RMS = DePlot's relative mapping similarity F1 (keys `x series`, number_theta 0.1); `all` counts abstentions as "
      "0, `covered` only charts the method answered; `names ignored` matches series by assignment instead of name. "
      "Synthetic charts also report the share of true points recovered and within 1% / 5% relative error "
      "(series matched by colour, points by category), and point F1 (2% of axis range) for scatter plots.")
    P()
    hdr = ("| slice | charts | coverage | RMS-F1 all | RMS-F1 covered | RMS-F1 names ignored | points found | "
           "within 1% | within 5% | scatter point F1 | median ms |")
    P("### 2a. Vector charts (synthetic PDFs) vs raster tracing of the same charts")
    P()
    P(hdr)
    P("|---" * 11 + "|")
    syn = [r for r in ours if r["ds"] == "synth"]
    res["synth"] = {}
    for var in ("vector", "raster_150", "raster_100", "raster_jpeg"):
        x = [r for r in syn if r["var"] == var]
        if x:
            res["synth"][var] = summ(x)
            row(f"{var} (all types)", res["synth"][var])
    for t in sorted({r["ctype"] for r in syn}):
        for var in ("vector", "raster_150"):
            x = [r for r in syn if r["var"] == var and r["ctype"] == t]
            if x:
                o = summ(x)
                res["synth"][f"{var}:{t}"] = o
                row(f"{var}: {t}", o)
    P()
    vec = {r["group"]: r for r in syn if r["var"] == "vector"}
    ras = {r["group"]: r for r in syn if r["var"] == "raster_150"}
    common = sorted(set(vec) & set(ras))
    w, l, p = sign_test([vec[g]["rms_f1"] - ras[g]["rms_f1"] for g in common])
    P(f"Vector vs raster (150 dpi) on the same {len(common)} charts, per-chart RMS-F1: vector better {w}, "
      f"worse {l}, p = {pfmt(p)}.")
    P()
    P("Abstention reasons (vector): " + ", ".join(f"{k}: {v}" for k, v in Counter(
        r.get("abstain") for r in syn if r["var"] == "vector" and r.get("abstain")).most_common()))
    P()
    P("### 2b. Raster charts from datasets")
    P()
    P(hdr)
    P("|---" * 11 + "|")
    res["datasets"] = {}
    for ds in ("chartx", "plotqa"):
        x = [r for r in ours if r["ds"] == ds]
        if not x:
            continue
        res["datasets"][ds] = summ(x)
        row(f"{ds} all", res["datasets"][ds])
        xs = [r for r in x if r.get("supported")]
        row(f"{ds} supported types", summ(xs))
        by = defaultdict(list)
        for r in x:
            by[r["ctype"]].append(r)
        for t, v in sorted(by.items(), key=lambda kv: -len(kv[1]))[:14]:
            row(f"{ds}: {t}", summ(v))
    P()
    if dep:
        P("### 2c. DePlot (google/deplot, ~1.1 GB, offline reference) vs our tracing on the same charts")
        P()
        P("| set | charts | DePlot RMS-F1 | ours RMS-F1 (abstain = 0) | ours coverage | ours better | DePlot better | p | "
          "DePlot median s/chart |")
        P("|---|---|---|---|---|---|---|---|---|")
        ob = {r["id"]: r for r in ours}
        res["deplot"] = {}
        for ds in ("synth", "chartx", "plotqa"):
            d = [r for r in dep if r["ds"] == ds and r["id"] in ob]
            if not d:
                continue
            diffs = [ob[r["id"]]["rms_f1"] - r["rms_f1"] for r in d]
            w, l, p = sign_test(diffs)
            o = {"n": len(d), "deplot": sum(r["rms_f1"] for r in d) / len(d),
                 "ours": sum(ob[r["id"]]["rms_f1"] for r in d) / len(d),
                 "cov": sum(1 for r in d if not ob[r["id"]].get("abstain")) / len(d), "w": w, "l": l, "p": p,
                 "s": sorted(r["ms"] for r in d)[len(d) // 2] / 1000}
            res["deplot"][ds] = o
            P(f"| {ds} | {o['n']} | {o['deplot']:.3f} | {o['ours']:.3f} | {o['cov']:.3f} | {w} | {l} | {pfmt(p)} | "
              f"{o['s']:.1f} |")
        P()
    errs = [r for r in rs if r.get("error")]
    if errs:
        P(f"Errors: {len(errs)}; first: " + "; ".join(f"{e['id']}: {e['error'][:100]}" for e in errs[:4]))
        P()
    open(out_md, "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(res, open(out_js, "w"), indent=1)


if __name__ == "__main__":
    main()

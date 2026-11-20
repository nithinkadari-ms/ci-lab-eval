"""Round 3 scoring: Test 1 (logic rebuild, baselines, hybrid gate), Test 2 (1024 cap, line splitting), Test 7 (CDM)."""
import glob, json, math, os, random, statistics, sys, zlib
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from texnorm import norm_tokens
from taxonomy import difficulty, tags
from evaluate import bleu4
from rapidfuzz.distance import Levenshtein


def join_lines(parts):
    r"""Recognised line pieces -> one aligned block: \begin{aligned} p1 \ p2 \end{aligned}."""
    bs = chr(92)
    return bs + "begin{aligned} " + (" " + bs + bs + " ").join(parts) + " " + bs + "end{aligned}"


R = os.path.join(ROOT, "results")
OUT = []
SUMMARY = {}


def jl(pattern):
    rows = {}
    for p in sorted(glob.glob(pattern)):
        for l in open(p, encoding="utf-8"):
            l = l.strip()
            if not l:
                continue
            try:
                r = json.loads(l)
            except ValueError:
                continue
            rows.setdefault(r["id"], r)
    return rows


def sc(gt_n, pred):
    pn = norm_tokens(pred or "")
    a, b = "".join(gt_n), "".join(pn)
    return pn, a == b, 1 - Levenshtein.distance(a, b) / max(len(a), len(b), 1)


def sign_test(wins, losses):
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    if n > 2000:
        z = (abs(wins - losses) - 1) / math.sqrt(n)
        return math.erfc(z / math.sqrt(2))
    lp = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) - n * math.log(2) for i in range(k + 1)]
    m = max(lp)
    p = 2 * math.exp(m) * sum(math.exp(x - m) for x in lp)
    return min(1.0, p)


def fmtp(p):
    return "<1e-6" if p < 1e-6 else f"{p:.2g}"


class Scored:
    def __init__(self, items, preds):
        """preds: id -> latex (None = no output)."""
        self.em, self.ed, self.pn = {}, {}, {}
        for it in items:
            pn, e, d = sc(it["_gtn"], preds.get(it["id"]))
            self.em[it["id"]], self.ed[it["id"]], self.pn[it["id"]] = e, d, pn

    def stats(self, ids):
        ids = list(ids)
        if not ids:
            return None
        return {"n": len(ids), "exact": 100 * sum(self.em[i] for i in ids) / len(ids),
                "edit": sum(self.ed[i] for i in ids) / len(ids)}


def table(title, rows, cols):
    OUT.append(f"\n### {title}\n\n| " + " | ".join(cols) + " |\n|" + "---|" * len(cols))
    for r in rows:
        OUT.append("| " + " | ".join(str(x) for x in r) + " |")


def load_manifest(name):
    items = json.load(open(os.path.join(ROOT, "manifests", name + ".json"), encoding="utf-8"))
    for it in items:
        it["_gtn"] = norm_tokens(it["gt"])
        it["_diff"] = difficulty(it["gt"])
        it["_tags"] = tags(it)
    return items


# ============================================================ Test 1
def test1():
    items = load_manifest("arxiv")
    byid = {it["id"]: it for it in items}
    ids = [it["id"] for it in items]
    int8 = jl(os.path.join(R, "acc", "p2t15_int8.arxiv.s*.jsonl"))
    logic = jl(os.path.join(R, "t1", "logic.jsonl"))
    tools = {t: jl(os.path.join(R, "t1", f"{t}.jsonl")) for t in ("pdfmath", "rustypaper", "kakemono", "gopdfkit")}
    if not int8 or not logic:
        OUT.append("\n## Test 1\n\nmissing inputs: int8 %d, logic %d" % (len(int8), len(logic)))
        return
    for it in items:
        it["_family"] = logic.get(it["id"], {}).get("family") or "none"
    P = {"p2t15_int8": {i: r.get("pred") for i, r in int8.items()}, "logic": {i: r.get("latex") for i, r in logic.items()}}
    for t, d in tools.items():
        if d:
            P[t] = {i: (r.get("latex") if r.get("status") in ("ok", "picture") else None) for i, r in d.items()}
    S = {k: Scored(items, v) for k, v in P.items()}
    conf = {i: float(logic.get(i, {}).get("conf") or 0.0) for i in ids}
    base = S["p2t15_int8"]

    def hybrid_preds(gate):
        return {i: (P["logic"].get(i) if gate(i) else P["p2t15_int8"].get(i)) for i in ids}

    # gate sweep
    taus = [0.0, 0.3, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.98, 1.0, 1.01]
    sweep = []
    for t in taus:
        acc = [i for i in ids if conf[i] >= t and P["logic"].get(i)]
        hy = Scored(items, hybrid_preds(lambda i, t=t: conf[i] >= t and bool(P["logic"].get(i))))
        w = sum(1 for i in ids if hy.em[i] and not base.em[i])
        l = sum(1 for i in ids if base.em[i] and not hy.em[i])
        s_acc = S["logic"].stats(acc) if acc else None
        b_acc = base.stats(acc) if acc else None
        sweep.append((t, len(acc), s_acc, b_acc, hy.stats(ids), w, l, sign_test(w, l)))
    best = max(sweep, key=lambda r: (r[4]["exact"], -r[0]))
    tau = best[0]
    # 2-fold cross-validation of the threshold by paper
    fold = {i: zlib.crc32(byid[i]["paper"].encode()) % 2 for i in ids}
    cv_em = []
    for f in (0, 1):
        tr = [i for i in ids if fold[i] != f]
        te = [i for i in ids if fold[i] == f]
        bt = max(taus, key=lambda t: sum((S["logic"].em[i] if conf[i] >= t and P["logic"].get(i) else base.em[i]) for i in tr))
        cv_em += [(S["logic"].em[i] if conf[i] >= bt and P["logic"].get(i) else base.em[i]) for i in te]
    cv_exact = 100 * sum(cv_em) / len(cv_em)
    P["hybrid_logic"] = hybrid_preds(lambda i: conf[i] >= tau and bool(P["logic"].get(i)))
    S["hybrid_logic"] = Scored(items, P["hybrid_logic"])
    # the baseline tools expose no calibrated confidence, so only the own rebuild gets a hybrid gate
    systems = list(S)
    OUT.append(f"\n## Test 1 - formulas rebuilt from the PDF text layer ({len(ids)} arXiv crops)\n")
    OUT.append(f"Gate threshold for hybrid_logic chosen on all crops: tau={tau}; 2-fold cross-validated by paper: hybrid exact {cv_exact:.1f}%.")
    rows = []
    for k in systems:
        st = S[k].stats(ids)
        w = sum(1 for i in ids if S[k].em[i] and not base.em[i])
        l = sum(1 for i in ids if base.em[i] and not S[k].em[i])
        bl = bleu4([byid[i]["_gtn"] for i in ids], [S[k].pn[i] for i in ids])
        out_rate = 100 * sum(1 for i in ids if P[k].get(i)) / len(ids)
        rows.append((k, st["n"], f"{st['exact']:.1f}", f"{st['edit']:.4f}", f"{bl:.4f}", f"{out_rate:.1f}",
                     "-" if k == "p2t15_int8" else f"+{w}/-{l}", "-" if k == "p2t15_int8" else fmtp(sign_test(w, l))))
        SUMMARY[f"t1_{k}_exact"] = round(st["exact"], 2)
    table("Overall (all crops; paired sign test vs Pix2Text INT8 on exact match)", rows,
          ["system", "n", "exact %", "edit", "BLEU-4", "has output %", "wins/losses vs INT8", "p"])
    rows = []
    for t, n_acc, s_acc, b_acc, hy, w, l, p in sweep:
        rows.append((t, n_acc, f"{100 * n_acc / len(ids):.1f}", f"{s_acc['exact']:.1f}" if s_acc else "-",
                     f"{b_acc['exact']:.1f}" if b_acc else "-", f"{hy['exact']:.1f}", f"{hy['edit']:.4f}", f"+{w}/-{l}", fmtp(p)))
    table("Gate sweep: logic accepted when confidence >= tau, else Pix2Text INT8", rows,
          ["tau", "accepted", "coverage %", "logic exact on accepted", "INT8 exact on same", "hybrid exact", "hybrid edit", "vs INT8", "p"])
    SUMMARY["t1_tau"] = tau
    SUMMARY["t1_cv_exact"] = round(cv_exact, 2)
    acc = [i for i in ids if conf[i] >= tau and P["logic"].get(i)]
    SUMMARY["t1_coverage"] = round(100 * len(acc) / len(ids), 2)
    # per family / bucket / tag
    fams = Counter(byid[i]["_family"] for i in ids)
    show = ["p2t15_int8", "logic", "hybrid_logic"] + [k for k in ("pdfmath", "rustypaper", "kakemono", "gopdfkit") if k in S]
    rows = []
    for fam, n in fams.most_common():
        fid = [i for i in ids if byid[i]["_family"] == fam]
        cov = 100 * sum(1 for i in fid if conf[i] >= tau and P["logic"].get(i)) / n
        rows.append([fam, n, f"{cov:.1f}"] + [f"{S[k].stats(fid)['exact']:.1f}" for k in show])
    table("Exact % by font family of the region (family from the glyph font names)", rows, ["family", "n", "logic coverage %"] + show)
    groups = [("diff", d, [i for i in ids if byid[i]["_diff"] == d]) for d in ("simple", "medium", "complex")]
    tagset = sorted({t for i in ids for t in byid[i]["_tags"]})
    groups += [("tag", t, [i for i in ids if t in byid[i]["_tags"]]) for t in tagset]
    rows = []
    for kind, name, gids in groups:
        if not gids:
            continue
        cov = 100 * sum(1 for i in gids if conf[i] >= tau and P["logic"].get(i)) / len(gids)
        w = sum(1 for i in gids if S["hybrid_logic"].em[i] and not base.em[i])
        l = sum(1 for i in gids if base.em[i] and not S["hybrid_logic"].em[i])
        rows.append([f"{kind}:{name}", len(gids), f"{cov:.1f}"] + [f"{S[k].stats(gids)['exact']:.1f}" for k in show] + [fmtp(sign_test(w, l))])
    table("Exact % per difficulty bucket and tag (tags overlap); p = hybrid_logic vs INT8", rows,
          ["group", "n", "logic coverage %"] + show + ["p"])
    # speed
    lms = [r.get("ms") for r in logic.values() if r.get("ms") is not None]
    lmsp = [r.get("ms_with_page") for r in logic.values() if r.get("ms_with_page") is not None]
    rows = [("logic (build only)", f"{statistics.median(lms):.2f}", f"{q(lms, 0.95):.2f}"),
            ("logic incl. page parse share", f"{statistics.median(lmsp):.2f}", f"{q(lmsp, 0.95):.2f}")]
    for t, d in tools.items():
        ms = [r.get("ms") for r in d.values() if isinstance(r.get("ms"), (int, float))]
        if ms:
            rows.append((t, f"{statistics.median(ms):.2f}", f"{q(ms, 0.95):.2f}"))
    s8 = [r.get("s") * 1000 for r in int8.values() if isinstance(r.get("s"), (int, float))]
    if s8:
        rows.append(("Pix2Text INT8 (per crop, 4 threads, same arXiv crops)", f"{statistics.median(s8):.0f}", f"{q(s8, 0.95):.0f}"))
    table("Speed per formula (ms)", rows, ["system", "p50 ms", "p95 ms"])
    # failure examples
    rnd = random.Random(3)
    OUT.append("\n### Failure examples\n")
    cut = lambda s: (" ".join((s or "").split()))[:170]
    hi_wrong = [i for i in acc if not S["logic"].em[i]]
    for i in rnd.sample(hi_wrong, min(6, len(hi_wrong))):
        OUT.append(f"- logic accepted but wrong `{i}` conf={conf[i]} family={byid[i]['_family']}<br>GT: `{cut(byid[i]['gt'])}`<br>logic: `{cut(P['logic'].get(i))}`<br>INT8: `{cut(P['p2t15_int8'].get(i))}`")
    rej_right = [i for i in ids if conf[i] < tau and S["logic"].em[i]]
    OUT.append(f"\nlogic exact but rejected by the gate: {len(rej_right)}; logic wrong and rejected: {sum(1 for i in ids if conf[i] < tau and not S['logic'].em[i])}")
    pp = [i for i in ids if logic.get(i, {}).get("punct_from_page")]
    if pp:
        OUT.append(f"\nTrailing punctuation taken from the page just right of a display crop (the models see only the crop): "
                   f"{len(pp)} crops; on these logic exact {100 * sum(S['logic'].em[i] for i in pp) / len(pp):.1f}%, "
                   f"INT8 exact {100 * sum(base.em[i] for i in pp) / len(pp):.1f}%. "
                   f"All crops without these: logic {100 * sum(S['logic'].em[i] for i in ids if i not in set(pp)) / max(1, len(ids) - len(pp)):.1f}%, "
                   f"INT8 {100 * sum(base.em[i] for i in ids if i not in set(pp)) / max(1, len(ids) - len(pp)):.1f}%.")
        SUMMARY["t1_punct_from_page"] = len(pp)
    for t in [k for k in ("pdfmath", "rustypaper", "kakemono", "gopdfkit") if k in S]:
        wr = [i for i in ids if P[t].get(i) and not S[t].em[i]]
        for i in rnd.sample(wr, min(2, len(wr))):
            OUT.append(f"- {t} wrong `{i}`<br>GT: `{cut(byid[i]['gt'])}`<br>{t}: `{cut(P[t].get(i))}`")
    note_c = Counter(n.split(" ")[0] + " " + (n.split(" ")[1] if len(n.split(" ")) > 1 else "") for r in logic.values() for n in (r.get("notes") or []))
    OUT.append("\nmost frequent logic confidence penalties: " + ", ".join(f"{k} ({v})" for k, v in note_c.most_common(12)))
    json.dump({"tau": tau, "conf": conf, "logic": P["logic"]}, open(os.path.join(R, "t1_gate.json"), "w"))


def q(v, p):
    s = sorted(v)
    return s[min(len(s) - 1, int(round(p * (len(s) - 1))))]


# ============================================================ Test 2
def test2():
    items = load_manifest("t2")
    byid = {it["id"]: it for it in items}
    OUT.append("\n## Test 2 - complex formulas: decode cap 1024 and line splitting\n")
    for model in ("p2t15_int8", "p2t15_fp32"):
        dec = jl(os.path.join(R, "t2", f"dec_{model}.s*.jsonl"))
        if not dec:
            OUT.append(f"\n{model}: no decode results")
            continue
        ids = [i for i in byid if i in dec]
        S512 = Scored([byid[i] for i in ids], {i: dec[i]["pred512"] for i in ids})
        S1024 = Scored([byid[i] for i in ids], {i: dec[i]["pred1024"] for i in ids})
        rows = []
        for name, sel in (("UniMER CPE", lambda i: byid[i]["set"] == "unimer_cpe"), ("arXiv complex/long", lambda i: byid[i]["set"] == "arxiv"), ("all", lambda i: True)):
            g = [i for i in ids if sel(i)]
            if not g:
                continue
            r512 = sum(1 for i in g if dec[i]["runaway512"])
            r1024 = sum(1 for i in g if dec[i]["runaway1024"])
            gone = sum(1 for i in g if dec[i]["runaway512"] and not dec[i]["runaway1024"])
            w = sum(1 for i in g if S1024.em[i] and not S512.em[i])
            l = sum(1 for i in g if S512.em[i] and not S1024.em[i])
            a, b = S512.stats(g), S1024.stats(g)
            rows.append((name, len(g), r512, r1024, gone, f"{a['exact']:.1f}", f"{b['exact']:.1f}", f"{a['edit']:.4f}", f"{b['edit']:.4f}", f"+{w}/-{l}", fmtp(sign_test(w, l))))
            SUMMARY[f"t2_{model}_{name}_runaways"] = (r512, r1024, gone)
        table(f"{model}: cap 512 vs 1023 new tokens (split decoder, greedy)", rows,
              ["set", "n", "runaways @512", "runaways @1024", "disappeared", "exact @512", "exact @1024", "edit @512", "edit @1024", "1024 vs 512", "p"])
        sp = jl(os.path.join(R, "t2", f"split_{model}.s*.jsonl"))
        if not sp:
            continue
        ids2 = [i for i in ids if i in sp]
        P_split = {i: (join_lines(sp[i]["pieces"]) if sp[i].get("pieces") else dec[i]["pred1024"]) for i in ids2}
        SS = Scored([byid[i] for i in ids2], P_split)
        rows = []
        multi = lambda i: "\\\\" in byid[i]["gt"] or "aligned" in byid[i]["gt"] or "gathered" in byid[i]["gt"]
        for name, sel in (("UniMER CPE, split applied", lambda i: byid[i]["set"] == "unimer_cpe" and sp[i]["n_pieces"] >= 2),
                          ("arXiv, split applied", lambda i: byid[i]["set"] == "arxiv" and sp[i]["n_pieces"] >= 2),
                          ("GT multi-line (all)", multi), ("GT single-line but split", lambda i: sp[i]["n_pieces"] >= 2 and not multi(i)),
                          ("all Test 2 items", lambda i: True)):
            g = [i for i in ids2 if sel(i)]
            if not g:
                continue
            w = sum(1 for i in g if SS.em[i] and not S1024.em[i])
            l = sum(1 for i in g if S1024.em[i] and not SS.em[i])
            a, b = S1024.stats(g), SS.stats(g)
            napplied = sum(1 for i in g if sp[i]["n_pieces"] >= 2)
            rows.append((name, len(g), napplied, f"{a['exact']:.1f}", f"{b['exact']:.1f}", f"{a['edit']:.4f}", f"{b['edit']:.4f}", f"+{w}/-{l}", fmtp(sign_test(w, l))))
        table(f"{model}: line splitting vs no splitting (both at cap 1023)", rows,
              ["subset", "n", "split applied", "exact unsplit", "exact split", "edit unsplit", "edit split", "split vs unsplit", "p"])
        json.dump({i: P_split[i] for i in ids2}, open(os.path.join(R, f"t2_split_{model}.json"), "w"))


# ============================================================ Test 7
def test7():
    files = sorted(glob.glob(os.path.join(R, "cdm", "*.jsonl")))
    if not files:
        OUT.append("\n## Test 7 - CDM\n\nno CDM results")
        return
    data = defaultdict(dict)
    for p in files:
        sysname = os.path.basename(p).split(".")[0]
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                data[sysname][r["id"]] = r
    sub = set(json.load(open(os.path.join(ROOT, "manifests", "cdm_subset.json"))))
    OUT.append("\n## Test 7 - CDM (OmniDocBench CDM code, TeX Live 2023 subset, ImageMagick 7.1.1-47)\n")
    gate = json.load(open(os.path.join(R, "t1_gate.json"))) if os.path.exists(os.path.join(R, "t1_gate.json")) else None
    if gate and "logic" in data and "p2t15_int8" in data:
        hy = {}
        for i, r in data["p2t15_int8"].items():
            if i.startswith("arxiv/") and gate["conf"].get(i, 0) >= gate["tau"] and gate["logic"].get(i) and i in data["logic"]:
                hy[i] = data["logic"][i]
            else:
                hy[i] = r
        data["hybrid_logic"] = hy
    groups = [("all 3000 (models)", lambda i: True), ("arXiv part", lambda i: i.startswith("arxiv/")),
              ("UniMER part", lambda i: not i.startswith("arxiv/"))]
    rows = []
    for name, d in sorted(data.items()):
        st = Counter(r.get("status") for r in d.values())
        ok_gt = [i for i, r in d.items() if r.get("status") in ("ok", "pred_render_fail")]
        f1 = [d[i]["cdm_f1"] or 0.0 for i in ok_gt]
        rows.append((name, len(d), st.get("ok", 0), st.get("pred_render_fail", 0), st.get("gt_render_fail", 0), st.get("error", 0),
                     f"{statistics.mean(f1):.4f}" if f1 else "-", f"{100 * sum(1 for x in f1 if x >= 0.9999) / len(f1):.1f}" if f1 else "-"))
    table("Per system: coverage and mean CDM F1 over ids whose ground truth rendered (pred render failure counts as 0)", rows,
          ["system", "inputs", "ok", "pred render fail", "gt render fail", "error", "mean CDM F1", "CDM exact %"])
    # common-id comparison per domain
    for name, sel in groups[1:]:
        cand = [s for s, d in data.items() if any(sel(i) for i in d)]
        common = None
        for s in cand:
            ok = {i for i, r in data[s].items() if sel(i) and r.get("status") in ("ok", "pred_render_fail")}
            common = ok if common is None else common & ok
        if not common:
            continue
        rows = []
        for s in sorted(cand, key=lambda s: -statistics.mean((data[s][i]["cdm_f1"] or 0) for i in common)):
            f1 = [(data[s][i]["cdm_f1"] or 0) for i in common]
            rows.append((s, len(common), f"{statistics.mean(f1):.4f}", f"{100 * sum(1 for x in f1 if x >= 0.9999) / len(f1):.1f}"))
        table(f"CDM on common ids, {name}", rows, ["system", "n", "mean CDM F1", "CDM exact %"])


if __name__ == "__main__":
    which = sys.argv[1:] or ["1", "2", "7"]
    OUT.append("# Formula round 3\n")
    if "1" in which:
        test1()
    if "2" in which:
        test2()
    if "7" in which:
        test7()
    open(os.path.join(R, "report_r3.md"), "w", encoding="utf-8").write("\n".join(OUT))
    json.dump(SUMMARY, open(os.path.join(R, "summary_r3.json"), "w"), indent=1, default=str)
    print("\n".join(OUT))

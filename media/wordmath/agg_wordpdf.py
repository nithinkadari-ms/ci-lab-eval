"""Score the real-Word and Windows-render (LuaLaTeX + Cambria Math) sets. Exact = round-3 normalised token string
equal to any accepted gold form; edit = 1 - Levenshtein / max length on the normalised strings (best gold form).
Equation numbers are stripped from predictions and gold before scoring. Logic+fallback: logic accepted when its
confidence >= tau and it produced output, else Pix2Text int8; tau is chosen on the dev half of each set (ids
hashed) and reported on the other half, plus all formulas at that tau for the per-construct tables.
usage: agg_wordpdf.py ARTDIR OUT.md OUT.json"""
import glob
import json
import os
import re
import sys
import zlib
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "formula", "scripts"))
sys.path.insert(0, os.path.dirname(HERE))
from rapidfuzz.distance import Levenshtein  # noqa: E402
from texnorm import norm_tokens  # noqa: E402
from common import pfmt, sign_test  # noqa: E402

NO_RE = re.compile(r"\\tag\*?\s*\{\s*\d+\s*\}|#\s*\(\s*\d+\s*\)|\(\s*\d+\s*\)\s*$")
TAUS = [round(0.05 * i, 2) for i in range(21)]


def norm(s):
    try:
        return "".join(norm_tokens(NO_RE.sub("", s or "")))
    except Exception:  # noqa: BLE001
        return "ERR"


def score(pred, golds):
    p = norm(pred)
    best_e, best_d = 0, 0.0
    for g in golds:
        a = norm(g)
        e = int(a == p and bool(pred))
        d = 1 - Levenshtein.distance(a, p) / max(len(a), len(p), 1) if pred else 0.0
        best_e, best_d = max(best_e, e), max(best_d, d)
    return best_e, best_d


def dev(i):
    return zlib.crc32(i.encode()) % 2 == 0


def main():
    art, out_md, out_js = sys.argv[1], sys.argv[2], sys.argv[3]
    golds = {}
    for m in glob.glob(os.path.join(art, "**", "manifest.json"), recursive=True):
        for c in json.load(open(m, encoding="utf-8")):
            golds[c["id"] + ("@word" if "omml" in c else "@win")] = c["gold"]
    R = defaultdict(list)
    for f in glob.glob(os.path.join(art, "**", "wordpdf-*.jsonl"), recursive=True):
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            r["gold"] = golds.get(r["id"] + "@" + r["set"])
            R[r["set"]].append(r)
    res = {}
    for s, rs in R.items():
        for r in rs:
            g = r["gold"] or [""]
            r["L"] = score(r.get("logic"), g)
            r["M"] = score(r.get("mfr"), g)
        dv = [r for r in rs if dev(r["id"])]

        def hyb(r, t):
            return r["L"] if (r.get("conf", 0) >= t and r.get("logic")) else r["M"]
        tau = max(TAUS, key=lambda t: (sum(hyb(r, t)[0] for r in dv), t))
        for r in rs:
            r["H"] = hyb(r, tau)
            r["acc"] = bool(r.get("logic")) and r.get("conf", 0) >= tau
        res[s] = {"tau": tau, "rows": rs}
    names = [s for s in ("word", "win") if s in res]
    title = {"word": "real Word (Cambria Math)", "win": "Windows LuaLaTeX + Cambria Math"}
    L = ["## Word formulas: real Word / Cambria Math", ""]
    for s in names:
        rs = res[s]["rows"]
        err = Counter(r.get("error", "").split(":")[0] for r in rs if r.get("error"))
        fonts = Counter(f_ for r in rs for f_ in r.get("fonts") or [])
        ma = sum(r.get("math_alnum", 0) for r in rs) / max(1, len(rs))
        L.append(f"- {title[s]}: {len(rs)} formulas, errors {dict(err)}; gate tau (dev half) = {res[s]['tau']}; fonts in "
                 f"regions: {', '.join(f'{k} ({v})' for k, v in fonts.most_common(6))}; mean share of Unicode math "
                 f"alphanumerics among region glyphs {ma:.2f}.")
    L.append("")
    L.append("Held-out half (tau chosen on the other half):")
    L.append("")
    L.append("| set | n | logic exact | model exact | logic+fallback exact | logic coverage | logic exact on accepted | "
             "hybrid vs model (better / worse, p) |")
    L.append("|---|---|---|---|---|---|---|---|")
    js = {}
    for s in names:
        te = [r for r in res[s]["rows"] if not dev(r["id"]) and not r.get("error")]
        n = max(1, len(te))
        acc = [r for r in te if r["acc"]]
        w = sum(1 for r in te if r["H"][0] and not r["M"][0])
        l_ = sum(1 for r in te if r["M"][0] and not r["H"][0])
        _, _, p = sign_test([r["H"][0] - r["M"][0] for r in te])
        o = {"n": len(te), "logic": 100 * sum(r["L"][0] for r in te) / n, "model": 100 * sum(r["M"][0] for r in te) / n,
             "hybrid": 100 * sum(r["H"][0] for r in te) / n, "coverage": 100 * len(acc) / n,
             "acc_exact": 100 * sum(r["L"][0] for r in acc) / max(1, len(acc)), "w": w, "l": l_, "p": p}
        js[s] = o
        L.append(f"| {title[s]} | {o['n']} | {o['logic']:.1f}% | {o['model']:.1f}% | **{o['hybrid']:.1f}%** | "
                 f"{o['coverage']:.1f}% | {o['acc_exact']:.1f}% | {w} / {l_}, p = {pfmt(p)} |")
    L.append("")
    L.append("Per construct, all formulas (exact % / edit score); columns per set:")
    L.append("")
    hdr = "| construct | " + " | ".join(f"{s}: n | {s}: logic | {s}: model | {s}: logic+fallback | {s}: coverage" for s in names) + " |"
    L.append(hdr)
    L.append("|---|" + "---|" * (5 * len(names)))
    kinds = sorted({r["construct"] for s in names for r in res[s]["rows"]})
    for k in kinds + ["inline", "display", "ALL"]:
        cells = []
        for s in names:
            rs = [r for r in res[s]["rows"] if not r.get("error") and (k == "ALL" or r["construct"] == k or r["mode"] == k)]
            if not rs:
                cells += ["0", "-", "-", "-", "-"]
                continue
            n = len(rs)

            def f(key):
                return f"{100 * sum(r[key][0] for r in rs) / n:.1f} / {sum(r[key][1] for r in rs) / n:.3f}"
            cells += [str(n), f("L"), f("M"), f("H"), f"{100 * sum(r['acc'] for r in rs) / n:.0f}%"]
        L.append(f"| {k} | " + " | ".join(cells) + " |")
    L.append("")
    for s in names:
        rs = [r for r in res[s]["rows"] if not r.get("error")]
        ms = sorted(r.get("mfr_ms", 0) for r in rs if "mfr_ms" in r)
        lm = sorted(r.get("logic_ms", 0) for r in rs if "logic_ms" in r)
        if ms and lm:
            L.append(f"- {title[s]}: logic median {lm[len(lm) // 2]:.1f} ms, Pix2Text int8 median {ms[len(ms) // 2]:.0f} ms "
                     f"(4 threads), decoder runaways {sum(1 for r in rs if r.get('mfr_runaway'))}.")
    L.append("")
    open(out_md, "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump({"held_out": js, "tau": {s: res[s]["tau"] for s in names}}, open(out_js, "w"), indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()

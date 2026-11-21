"""Gap 11: Word (OMML) equations.
  A. OMML -> LaTeX with easydoc-math 0.1.2 (Rust, built on the runner), scored against gold LaTeX after the
     round-3 normaliser (formula/scripts/texnorm.py).
  B. OMML -> MathML with plurimath/omml2mathml omml2mml.xsl (BSD-2, XSLT 1.0 via lxml), scored as a canonical
     MathML skeleton against gold MathML from the same AST (generated cases).
  C. DOCX -> PDF with LibreOffice, then the round-3 glyph logic rebuild (formula/r3/logic) on each equation's
     region, scored like A.
Equation numbers: the expression is scored with the number removed; whether the number survives is reported.
usage: run_wordmath.py EDM_BIN XSL OUTDIR [--pdf]"""
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "formula", "scripts"))
sys.path.insert(0, os.path.join(ROOT, "formula", "r3", "logic"))
sys.path.insert(0, os.path.dirname(HERE))
import gen  # noqa: E402
import texnorm  # noqa: E402
from common import pfmt, sign_test  # noqa: E402

EQNO_RE = re.compile(r"\\tag\*?\s*\{\s*(\d+)\s*\}|#\s*\(\s*(\d+)\s*\)|\(\s*(\d+)\s*\)\s*$")


def tnorm(s):
    try:
        return texnorm.normalize(s)
    except Exception:  # noqa: BLE001
        return "ERR:" + s


def strip_no(s):
    m = list(EQNO_RE.finditer(s or ""))
    if not m:
        return s, None
    last = m[-1]
    num = next(g for g in last.groups() if g)
    return (s[:last.start()] + s[last.end():]).strip(), num


def tex_ok(out, case):
    if out is None:
        return False, False
    num_kept = None
    if case.get("eqno"):
        out, num = strip_no(out)
        num_kept = num == case["eqno"]
        golds = [strip_no(g)[0] for g in case["gold"]]
    else:
        golds = case["gold"]
    o = tnorm(out)
    return o in {tnorm(g) for g in golds}, num_kept


# ---------------------------------------------------------------- MathML skeleton
INVIS = {"\u2061", "\u2062", "\u2063", "\u2064", "\u200b"}
BIGOPS = {"\u2211", "\u220f", "\u222b", "\u222e", "\u22c3", "\u2210", "\u22c2"}
ACCMAP = {"\u0302": "ACC_hat", "^": "ACC_hat", "\u02c6": "ACC_hat", "\u0303": "ACC_tilde", "~": "ACC_tilde",
          "\u02dc": "ACC_tilde", "\u0307": "ACC_dot", "\u02d9": "ACC_dot", ".": "ACC_dot", "\u0308": "ACC_ddot",
          "\u00a8": "ACC_ddot", "\u20d7": "ACC_vec", "\u2192": "ACC_vec", "\u00af": "BAR", "\u203e": "BAR",
          "\u0305": "BAR", "_": "BAR", "\u0332": "BAR", "\u2015": "BAR", "\u23df": "BRACE", "\ufe38": "BRACE"}
CHARMAP = {"\u2212": "-", "\u2009": "", "\u00a0": ""}


def local(el):
    return el.tag.split("}")[-1] if isinstance(el.tag, str) else ""


def toks(el):
    t = "".join(el.itertext())
    out = []
    for c in t:
        c = CHARMAP.get(c, c)
        if not c or c.isspace() or c in INVIS:
            continue
        out.append(("t", c))
    return out


def skel(el):
    k = local(el)
    ch = [c for c in el if isinstance(c.tag, str)]
    if k in ("mi", "mn", "mo", "mtext", "ms"):
        return toks(el)
    if k in ("math", "mrow", "mstyle", "mpadded", "menclose", "mphantom", "merror", "oMath", "oMathPara"):
        out = []
        for c in ch:
            out += skel(c)
        return out
    if k == "semantics":
        return skel(ch[0]) if ch else []
    if k in ("mspace", "maligngroup", "malignmark", "none", "annotation", "annotation-xml"):
        return []
    S = lambda i: tuple(skel(ch[i])) if i < len(ch) else ()  # noqa: E731
    if k == "mfrac":
        return [("frac", S(0), S(1))]
    if k == "msqrt":
        out = []
        for c in ch:
            out += skel(c)
        return [("sqrt", tuple(out))]
    if k == "mroot":
        return [("root", S(0), S(1))]
    base_big = lambda: len(S(0)) == 1 and S(0)[0][0] == "t" and S(0)[0][1] in BIGOPS  # noqa: E731
    if k == "msup" or (k == "mover" and base_big()):
        return [("sup", S(0), S(1))]
    if k == "msub" or (k == "munder" and base_big()):
        return [("sub", S(0), S(1))]
    if k in ("msubsup", "munderover"):
        return [("subsup", S(0), S(1), S(2))]
    if k in ("mover", "munder"):
        sc = S(1)
        if len(sc) == 1 and sc[0][0] == "t" and sc[0][1] in ACCMAP:
            sc = (("t", ACCMAP[sc[0][1]]),)
        return [("over" if k == "mover" else "under", S(0), sc)]
    if k == "mtable":
        rows = []
        for r in ch:
            cells = [c for c in r if isinstance(c.tag, str) and local(c) == "mtd"]
            if local(r) == "mlabeledtr":
                cells = cells[1:]
            rows.append(tuple(tuple(skel(c)) for c in cells))
        return [("table", tuple(rows))]
    if k == "mtd":
        out = []
        for c in ch:
            out += skel(c)
        return out
    if k == "mfenced":
        op, cl = el.get("open", "("), el.get("close", ")")
        seps = (el.get("separators", ",") or "").replace(" ", "")
        out = [("t", op)] if op else []
        for i, c in enumerate(ch):
            if i and seps:
                out.append(("t", seps[min(i - 1, len(seps) - 1)]))
            out += skel(c)
        return out + ([("t", cl)] if cl else [])
    if k == "mmultiscripts":
        names = [local(c) for c in ch]
        if "mprescripts" in names:
            j = names.index("mprescripts")
            return [("pre", S(j + 1), S(j + 2), S(0))]
        return [("subsup", S(0), S(1), S(2))]
    out = []
    for c in ch:
        out += skel(c)
    return out


def tup(x):
    if isinstance(x, list):
        return tuple(tup(v) for v in x)
    if isinstance(x, tuple):
        return tuple(tup(v) for v in x)
    return x


def strip_no_skel(sk):
    s = list(sk)
    num = None
    if len(s) >= 4 and s[-1] == ("t", ")"):
        j = len(s) - 2
        digits = []
        while j >= 0 and s[j][0] == "t" and s[j][1].isdigit():
            digits.insert(0, s[j][1])
            j -= 1
        if digits and j >= 1 and s[j] == ("t", "(") and s[j - 1] == ("t", "#"):
            num = "".join(digits)
            s = s[:j - 1]
    return tuple(s), num


def mml_ok(root, case):
    if root is None or "mml" not in case:
        return None, None
    sk = tup(skel(root))
    if len(sk) == 1 and sk[0][0] == "table" and case["construct"] == "eqnumber":
        rows = sk[0][1]
        if len(rows) == 1 and len(rows[0]) == 1:
            sk = rows[0][0]
    num_kept = None
    if case.get("eqno"):
        sk, num = strip_no_skel(sk)
        num_kept = num == case["eqno"]
    return sk == tup(case["mml"]), num_kept


# ---------------------------------------------------------------- PDF route
def pdf_route(cases, outdir):
    import pdfplumber
    from build import rebuild
    from pdfglyphs import PdfCache, select
    per = 25
    res = {}
    chunks = [cases[i:i + per] for i in range(0, len(cases), per)]
    t_lo = 0.0
    for ci, ch in enumerate(chunks):
        for k, c in enumerate(ch):
            c["marker"] = f"EQ{ci:03d}x{k:03d}"
        path = os.path.join(outdir, f"wm_{ci:03d}.docx")
        gen.docx(ch, path)
        t = time.perf_counter()
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", outdir, path], check=False,
                       capture_output=True, timeout=300)
        t_lo += time.perf_counter() - t
        pdf = path[:-5] + ".pdf"
        if not os.path.exists(pdf):
            for c in ch:
                res[c["id"]] = {"error": "libreoffice failed"}
            continue
        marks = {}
        with pdfplumber.open(pdf) as doc:
            for pi, page in enumerate(doc.pages):
                for w in page.extract_words():
                    if re.fullmatch(r"EQ\d{3}x\d{3}|EQEND", w["text"]):
                        marks[w["text"]] = (pi, w["top"], w["bottom"], float(page.width), float(page.height))
        cache = PdfCache()
        order = [c["marker"] for c in ch] + ["EQEND"]
        for k, c in enumerate(ch):
            a, b = marks.get(order[k]), marks.get(order[k + 1])
            if a is None:
                res[c["id"]] = {"error": "marker not found"}
                continue
            pi, _, abot, W, H = a
            btop = b[1] if b is not None and b[0] == pi else H - 50
            bbox = (40.0, H - btop + 0.5, W - 40.0, H - abot - 0.5)
            try:
                pd = cache.get(pdf, pi)
                gs, ss = select(pd, bbox, display=True)
                r = rebuild(gs, ss)
                fonts = sorted({g.font for g in gs})
                res[c["id"]] = {"latex": r.get("latex") or "", "fonts": fonts[:6], "n_glyphs": len(gs)}
            except Exception as e:  # noqa: BLE001
                res[c["id"]] = {"error": f"{type(e).__name__}: {e}"[:200]}
    return res, t_lo / max(1, len(chunks))


def main():
    edm, xsl, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    do_pdf = "--pdf" in sys.argv
    os.makedirs(outdir, exist_ok=True)
    cases = gen.all_cases(per=int(os.environ.get("WM_PER", "40")))
    inp = "\n".join(f"{c['id']}\t{gen.omath(c)}" for c in cases) + "\n"
    t = time.perf_counter()
    p = subprocess.run([edm], input=inp, capture_output=True, text=True, encoding="utf-8")
    edm_s = time.perf_counter() - t
    edm_out = {}
    for line in p.stdout.splitlines():
        parts = line.split("\t", 3)
        if len(parts) == 4:
            edm_out[parts[0]] = (parts[1], int(parts[2]), parts[3])
    from pathlib import Path
    from lxml import etree
    wrapper = os.path.join(outdir, "omml2mml_root.xsl")
    open(wrapper, "w", encoding="utf-8").write(
        '<?xml version="1.0"?><xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" '
        'xmlns="http://www.w3.org/1998/Math/MathML">'
        f'<xsl:import href="{Path(xsl).resolve().as_uri()}"/>'
        '<xsl:template match="/"><math><xsl:apply-templates select="*"/></math></xsl:template></xsl:stylesheet>')
    xslt = etree.XSLT(etree.parse(wrapper))
    rows = []
    t_x = 0.0
    for c in cases:
        r = {"id": c["id"], "construct": c["construct"], "source": c["source"]}
        st, us, tex = edm_out.get(c["id"], ("missing", 0, ""))
        r["edm_status"] = st
        r["edm_us"] = us
        r["edm_ok"], r["edm_no"] = tex_ok(tex if st == "ok" else None, c)
        try:
            t = time.perf_counter()
            res = xslt(etree.fromstring(gen.omath(c).encode("utf-8")))
            t_x += time.perf_counter() - t
            root = res.getroot()
            if root is not None and local(root) != "math":
                wrap = etree.Element("{http://www.w3.org/1998/Math/MathML}math")
                wrap.append(root)
                root = wrap
            r["xsl_ok"], r["xsl_no"] = mml_ok(root, c)
            r["xsl_status"] = "ok" if root is not None else "empty"
        except Exception as e:  # noqa: BLE001
            r["xsl_ok"], r["xsl_no"], r["xsl_status"] = False, None, f"error {type(e).__name__}"
        rows.append(r)
    pdfres, lo_s = ({}, 0.0)
    if do_pdf:
        pdfres, lo_s = pdf_route(cases, outdir)
        for c, r in zip(cases, rows):
            pr = pdfres.get(c["id"], {})
            if "error" in pr:
                r["pdf_ok"], r["pdf_no"], r["pdf_status"] = False, None, pr["error"]
            else:
                r["pdf_ok"], r["pdf_no"] = tex_ok(pr["latex"], c)
                r["pdf_status"] = "ok" if pr["latex"] else "empty"
                r["pdf_fonts"] = pr.get("fonts")
    with open(os.path.join(outdir, "wordmath-rows.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    by = defaultdict(list)
    for r in rows:
        by[r["construct"]].append(r)
    L = ["## Gap 11. Word formulas (OMML)", ""]
    L.append(f"{len(rows)} equations ({sum(r['source'] == 'hand' for r in rows)} hand-written OMML with hand LaTeX, "
             f"the rest generated from one AST into OMML + gold LaTeX + gold MathML). easydoc-math scored by "
             f"normalised LaTeX against the gold forms; omml2mml.xsl scored by canonical MathML skeleton (generated "
             f"cases only, hand cases have no MathML gold); PDF route = LibreOffice export + round-3 glyph logic.")
    L.append("")
    L.append("| construct | n | easydoc-math exact | easydoc errors | omml2mml.xsl skeleton exact | PDF glyph rebuild exact |")
    L.append("|---|---|---|---|---|---|")
    summ = {}
    for k in gen.CONSTRUCTS:
        rs = by.get(k, [])
        if not rs:
            continue
        e = sum(1 for r in rs if r["edm_ok"]) / len(rs)
        ee = sum(1 for r in rs if r["edm_status"] != "ok")
        xs = [r for r in rs if r["xsl_ok"] is not None]
        x = sum(1 for r in xs if r["xsl_ok"]) / len(xs) if xs else None
        ps = [r for r in rs if "pdf_ok" in r]
        pv = sum(1 for r in ps if r["pdf_ok"]) / len(ps) if ps else None
        summ[k] = {"n": len(rs), "edm": e, "xsl": x, "pdf": pv}
        L.append(f"| {k} | {len(rs)} | {e:.3f} | {ee} | {'-' if x is None else f'{x:.3f}'} | "
                 f"{'-' if pv is None else f'{pv:.3f}'} |")
    tot = {"edm": sum(r["edm_ok"] for r in rows) / len(rows)}
    xs = [r for r in rows if r["xsl_ok"] is not None]
    tot["xsl"] = sum(1 for r in xs if r["xsl_ok"]) / max(1, len(xs))
    ps = [r for r in rows if "pdf_ok" in r]
    tot["pdf"] = sum(1 for r in ps if r["pdf_ok"]) / max(1, len(ps)) if ps else None
    pdf_cell = "-" if tot["pdf"] is None else f"**{tot['pdf']:.3f}**"
    L.append(f"| **all** | {len(rows)} | **{tot['edm']:.3f}** | {sum(r['edm_status'] != 'ok' for r in rows)} | "
             f"**{tot['xsl']:.3f}** | {pdf_cell} |")
    L.append("")
    hand = [r for r in rows if r["source"] == "hand"]
    L.append(f"Hand-written cases only: easydoc-math {sum(r['edm_ok'] for r in hand)}/{len(hand)}"
             + (f", PDF route {sum(1 for r in hand if r.get('pdf_ok'))}/{len(hand)}" if ps else "") + ".")
    eq = [r for r in rows if r["construct"] == "eqnumber"]
    L.append(f"Equation numbers kept: easydoc-math {sum(1 for r in eq if r['edm_no'])}/{len(eq)}, omml2mml.xsl "
             f"{sum(1 for r in eq if r['xsl_no'])}/{len(eq)}" + (f", PDF route {sum(1 for r in eq if r.get('pdf_no'))}/{len(eq)}" if ps else "") + ".")
    gen_rows = [r for r in rows if r["xsl_ok"] is not None]
    w, l, pv = sign_test([int(bool(r["edm_ok"])) - int(bool(r["xsl_ok"])) for r in gen_rows])
    L.append(f"easydoc-math vs omml2mml.xsl on the same {len(gen_rows)} generated equations: easydoc right and XSLT "
             f"wrong {w}, the reverse {l}, sign test p = {pfmt(pv)} (different output formats, see method).")
    if ps:
        fonts = defaultdict(int)
        for r in ps:
            for f_ in r.get("pdf_fonts") or []:
                fonts[re.sub(r"^[A-Z]{6}\+", "", f_)] += 1
        L.append("PDF fonts seen in equation regions: " + ", ".join(f"{k} ({v})" for k, v in sorted(fonts.items(), key=lambda kv: -kv[1])[:8]) + ".")
        L.append(f"LibreOffice export {lo_s:.1f} s per 25-equation DOCX.")
    L.append(f"Speed: easydoc-math {sum(r['edm_us'] for r in rows) / max(1, len(rows)):.0f} us/equation in the Rust "
             f"binary (process total {edm_s:.2f} s for {len(rows)}); XSLT {1000 * t_x / max(1, len(rows)):.2f} ms/equation.")
    st = defaultdict(int)
    for r in rows:
        if not r["edm_ok"]:
            st[r["construct"]] += 1
    L.append("")
    open(os.path.join(outdir, "wordmath.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump({"by_construct": summ, "total": tot}, open(os.path.join(outdir, "wordmath.json"), "w"), indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()

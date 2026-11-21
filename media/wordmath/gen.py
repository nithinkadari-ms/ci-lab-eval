"""Word equations from one AST: native OMML (as Word writes it), gold LaTeX (with accepted alternatives) and gold
Presentation MathML. Randomised cases per construct plus hand-written cases (hand OMML + hand LaTeX)."""
import random
from xml.sax.saxutils import escape

ACC = {"hat": "̂", "tilde": "̃", "dot": "̇", "ddot": "̈", "vec": "⃗"}
NARY = {"sum": "∑", "prod": "∏", "int": "∫", "oint": "∮", "bigcup": "⋃"}
FUNCS = ["sin", "cos", "tan", "log", "ln", "exp"]
DELIM = {"(": ("(", ")"), "[": ("[", "]"), "{": ("\\{", "\\}"), "|": ("|", "|")}
GREEK = {"α": "\\alpha", "β": "\\beta", "γ": "\\gamma", "θ": "\\theta", "λ": "\\lambda",
         "μ": "\\mu", "σ": "\\sigma", "π": "\\pi", "ω": "\\omega", "Δ": "\\Delta"}
OPS = {"+": "+", "-": "-", "=": "=", "≤": "\\leq", "≥": "\\geq", "·": "\\cdot", "×": "\\times",
       "→": "\\rightarrow", "∞": "\\infty", "≠": "\\neq", ",": ","}


# ---------------------------------------------------------------- AST helpers
def T(s):
    return ("t", s)


def R(*xs):
    return ("row", [T(x) if isinstance(x, str) else x for x in xs])


def tex_text(s):
    out = []
    for ch in s:
        out.append(GREEK.get(ch) or OPS.get(ch) or ch)
        if out[-1].startswith("\\") and out[-1][-1].isalpha():
            out[-1] += " "
    return "".join(out)


# ---------------------------------------------------------------- OMML
def om(n):
    k = n[0]
    if k == "t":
        return f"<m:r><m:t>{escape(n[1])}</m:t></m:r>"
    if k == "row":
        return "".join(om(x) for x in n[1])
    if k == "frac":
        pr = "" if n[3] == "bar" else f'<m:fPr><m:type m:val="{n[3]}"/></m:fPr>'
        return f"<m:f>{pr}<m:num>{om(n[1])}</m:num><m:den>{om(n[2])}</m:den></m:f>"
    if k == "sup":
        return f"<m:sSup><m:e>{om(n[1])}</m:e><m:sup>{om(n[2])}</m:sup></m:sSup>"
    if k == "sub":
        return f"<m:sSub><m:e>{om(n[1])}</m:e><m:sub>{om(n[2])}</m:sub></m:sSub>"
    if k == "subsup":
        return f"<m:sSubSup><m:e>{om(n[1])}</m:e><m:sub>{om(n[2])}</m:sub><m:sup>{om(n[3])}</m:sup></m:sSubSup>"
    if k == "pre":
        return f"<m:sPre><m:sub>{om(n[1])}</m:sub><m:sup>{om(n[2])}</m:sup><m:e>{om(n[3])}</m:e></m:sPre>"
    if k == "nary":
        _, op, lo, hi, body, loc = n
        pr = f'<m:chr m:val="{NARY[op]}"/>' if op != "int" else ""
        pr += f'<m:limLoc m:val="{loc}"/>'
        if lo is None:
            pr += '<m:subHide m:val="1"/>'
        if hi is None:
            pr += '<m:supHide m:val="1"/>'
        return (f"<m:nary><m:naryPr>{pr}</m:naryPr><m:sub>{om(lo) if lo else ''}</m:sub>"
                f"<m:sup>{om(hi) if hi else ''}</m:sup><m:e>{om(body)}</m:e></m:nary>")
    if k == "rad":
        if n[1] is None:
            return f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{om(n[2])}</m:e></m:rad>'
        return f"<m:rad><m:deg>{om(n[1])}</m:deg><m:e>{om(n[2])}</m:e></m:rad>"
    if k == "mat":
        rows = "".join("<m:mr>" + "".join(f"<m:e>{om(c)}</m:e>" for c in r) + "</m:mr>" for r in n[1])
        return f"<m:m>{rows}</m:m>"
    if k == "d":
        _, beg, inner = n
        b, e = beg, {"(": ")", "[": "]", "{": "}", "|": "|"}[beg]
        pr = "" if beg == "(" else f'<m:dPr><m:begChr m:val="{escape(b)}"/><m:endChr m:val="{escape(e)}"/></m:dPr>'
        return f"<m:d>{pr}" + "".join(f"<m:e>{om(x)}</m:e>" for x in inner) + "</m:d>"
    if k == "eqarr":
        return "<m:eqArr>" + "".join(f"<m:e>{om(r)}</m:e>" for r in n[1]) + "</m:eqArr>"
    if k == "acc":
        pr = "" if n[1] == "hat" else f'<m:accPr><m:chr m:val="{ACC[n[1]]}"/></m:accPr>'
        return f"<m:acc>{pr}<m:e>{om(n[2])}</m:e></m:acc>"
    if k == "bar":
        return f'<m:bar><m:barPr><m:pos m:val="{n[1]}"/></m:barPr><m:e>{om(n[2])}</m:e></m:bar>'
    if k == "func":
        return (f'<m:func><m:fName><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>{n[1]}</m:t></m:r></m:fName>'
                f"<m:e>{om(n[2])}</m:e></m:func>")
    if k == "lim":
        return ('<m:func><m:fName><m:limLow><m:e><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>lim</m:t></m:r></m:e>'
                f"<m:lim>{om(n[1])}</m:lim></m:limLow></m:fName><m:e>{om(n[2])}</m:e></m:func>")
    if k == "brace":
        return ('<m:limLow><m:e><m:groupChr><m:groupChrPr><m:chr m:val="⏟"/><m:pos m:val="bot"/>'
                f'<m:vertJc m:val="top"/></m:groupChrPr><m:e>{om(n[1])}</m:e></m:groupChr></m:e>'
                f"<m:lim>{om(n[2])}</m:lim></m:limLow>")
    if k == "eqno":
        return f"<m:eqArr><m:e>{om(n[1])}<m:r><m:t>#({n[2]})</m:t></m:r></m:e></m:eqArr>"
    raise ValueError(k)


# ---------------------------------------------------------------- gold LaTeX (list of accepted forms)
def tx(n):
    """-> list of accepted LaTeX strings (cartesian over alternatives, capped)."""
    k = n[0]

    def comb(parts):
        outs = [""]
        for p in parts:
            alts = p if isinstance(p, list) else [p]
            outs = [o + a for o in outs for a in alts][:24]
        return outs
    if k == "t":
        return [tex_text(n[1])]
    if k == "row":
        return comb([tx(x) for x in n[1]])
    if k == "frac":
        if n[3] == "lin":
            return comb([tx(n[1]), "/", tx(n[2])]) + comb(["{", tx(n[1]), "}/{", tx(n[2]), "}"])
        if n[3] == "noBar":
            return comb(["{", tx(n[1]), " \\atop ", tx(n[2]), "}"]) + comb(["\\genfrac{}{}{0pt}{}{", tx(n[1]), "}{", tx(n[2]), "}"]) \
                + comb(["\\binom{", tx(n[1]), "}{", tx(n[2]), "}"])
        f = comb(["\\frac{", tx(n[1]), "}{", tx(n[2]), "}"])
        if n[3] == "skw":
            f += comb(["{", tx(n[1]), "}/{", tx(n[2]), "}"]) + comb(["^{", tx(n[1]), "}/_{", tx(n[2]), "}"])
        return f
    if k == "sup":
        return comb(["{", tx(n[1]), "}^{", tx(n[2]), "}"])
    if k == "sub":
        return comb(["{", tx(n[1]), "}_{", tx(n[2]), "}"])
    if k == "subsup":
        return comb(["{", tx(n[1]), "}_{", tx(n[2]), "}^{", tx(n[3]), "}"])
    if k == "pre":
        return comb(["{}_{", tx(n[1]), "}^{", tx(n[2]), "}{", tx(n[3]), "}"]) + comb(["\\prescript{", tx(n[2]), "}{", tx(n[1]), "}{", tx(n[3]), "}"])
    if k == "nary":
        _, op, lo, hi, body, loc = n
        s = ["\\" + op]
        if lo:
            s += ["_{", tx(lo), "}"]
        if hi:
            s += ["^{", tx(hi), "}"]
        return comb(s + ["{", tx(body), "}"])
    if k == "rad":
        if n[1] is None:
            return comb(["\\sqrt{", tx(n[2]), "}"])
        return comb(["\\sqrt[", tx(n[1]), "]{", tx(n[2]), "}"])
    if k == "mat":
        body = comb([" \\\\ ".join(" & ".join(tx(c)[0] for c in r) for r in n[1])])
        return comb(["\\begin{matrix}", body, "\\end{matrix}"]) + comb(["\\begin{array}{" + "c" * len(n[1][0]) + "}", body, "\\end{array}"])
    if k == "d":
        beg = n[1]
        lo, hi = DELIM[beg]
        inner = n[2]
        if len(inner) == 1 and inner[0][0] == "mat":
            env = {"(": "pmatrix", "[": "bmatrix", "{": "Bmatrix", "|": "vmatrix"}[beg]
            body = " \\\\ ".join(" & ".join(tx(c)[0] for c in r) for r in inner[0][1])
            return [f"\\begin{{{env}}}{body}\\end{{{env}}}"] + comb(["\\left" + lo, tx(inner[0]), "\\right" + hi])
        parts = ["\\left" + lo]
        for j, x in enumerate(inner):
            if j:
                parts.append("|")
            parts.append(tx(x))
        parts.append("\\right" + hi)
        return comb(parts)
    if k == "eqarr":
        body = " \\\\ ".join(tx(r)[0] for r in n[1])
        return [f"\\begin{{aligned}}{body}\\end{{aligned}}", f"\\begin{{array}}{{l}}{body}\\end{{array}}",
                f"\\begin{{matrix}}{body}\\end{{matrix}}", f"\\begin{{gathered}}{body}\\end{{gathered}}",
                f"\\begin{{array}}{{c}}{body}\\end{{array}}"]
    if k == "acc":
        return comb(["\\" + n[1] + "{", tx(n[2]), "}"])
    if k == "bar":
        return comb(["\\overline{" if n[1] == "top" else "\\underline{", tx(n[2]), "}"])
    if k == "func":
        return comb(["\\" + n[1] + "{", tx(n[2]), "}"]) + comb(["\\" + n[1] + " ", tx(n[2])])
    if k == "lim":
        return comb(["\\lim_{", tx(n[1]), "}{", tx(n[2]), "}"])
    if k == "brace":
        return comb(["\\underbrace{", tx(n[1]), "}_{", tx(n[2]), "}"])
    if k == "eqno":
        return comb([tx(n[1]), f"\\tag{{{n[2]}}}"])
    raise ValueError(k)


# ---------------------------------------------------------------- gold MathML skeleton
def mm(n):
    """Canonical skeleton: nested tuples; tokens are single characters ('t', ch)."""
    k = n[0]
    if k == "t":
        return [("t", c) for c in n[1] if not c.isspace()]
    if k == "row":
        out = []
        for x in n[1]:
            out += mm(x)
        return out
    if k == "frac":
        if n[3] == "lin":
            return mm(n[1]) + [("t", "/")] + mm(n[2])
        return [("frac", tuple(mm(n[1])), tuple(mm(n[2])))]
    if k == "sup":
        return [("sup", tuple(mm(n[1])), tuple(mm(n[2])))]
    if k == "sub":
        return [("sub", tuple(mm(n[1])), tuple(mm(n[2])))]
    if k == "subsup":
        return [("subsup", tuple(mm(n[1])), tuple(mm(n[2])), tuple(mm(n[3])))]
    if k == "pre":
        return [("pre", tuple(mm(n[1])), tuple(mm(n[2])), tuple(mm(n[3])))]
    if k == "nary":
        _, op, lo, hi, body, loc = n
        base = (("t", NARY[op]),)
        if lo and hi:
            s = ("subsup", base, tuple(mm(lo)), tuple(mm(hi)))
        elif lo:
            s = ("sub", base, tuple(mm(lo)))
        elif hi:
            s = ("sup", base, tuple(mm(hi)))
        else:
            s = base[0]
        return [s] + mm(body)
    if k == "rad":
        return [("sqrt", tuple(mm(n[2])))] if n[1] is None else [("root", tuple(mm(n[2])), tuple(mm(n[1])))]
    if k == "mat":
        return [("table", tuple(tuple(tuple(mm(c)) for c in r) for r in n[1]))]
    if k == "d":
        e = {"(": ")", "[": "]", "{": "}", "|": "|"}[n[1]]
        out = [("t", n[1])]
        for j, x in enumerate(n[2]):
            if j:
                out.append(("t", "|"))
            out += mm(x)
        return out + [("t", e)]
    if k == "eqarr":
        return [("table", tuple((tuple(mm(r)),) for r in n[1]))]
    if k == "acc":
        return [("over", tuple(mm(n[2])), (("t", "ACC_" + n[1]),))]
    if k == "bar":
        return [("over" if n[1] == "top" else "under", tuple(mm(n[2])), (("t", "BAR"),))]
    if k == "func":
        return [("t", c) for c in n[1]] + mm(n[2])
    if k == "lim":
        return [("under", (("t", "l"), ("t", "i"), ("t", "m")), tuple(mm(n[1])))] + mm(n[2])
    if k == "brace":
        return [("under", (("under", tuple(mm(n[1])), (("t", "BRACE"),)),), tuple(mm(n[2])))]
    if k == "eqno":
        return mm(n[1])
    raise ValueError(k)


# ---------------------------------------------------------------- random cases
def atom(r, d=0):
    c = r.random()
    if c < 0.45:
        return T(r.choice("abcdxyzkn") if r.random() < 0.8 else r.choice(list(GREEK)))
    if c < 0.7:
        return T(str(r.randint(1, 99)))
    if d < 2:
        return expr(r, d + 1)
    return T(r.choice("xyz"))


def expr(r, d=0):
    n = r.randint(1, 3)
    parts = []
    for i in range(n):
        if i:
            parts.append(T(r.choice(["+", "-", "·", "="])))
        parts.append(construct(r, r.choice(CONSTRUCTS[:-2]), d + 1) if d < 2 and r.random() < 0.35 else atom(r, d + 1))
    return ("row", parts)


def construct(r, kind, d=0):
    a = lambda: atom(r, d)  # noqa: E731
    e = lambda: expr(r, d) if d < 2 else atom(r, 2)  # noqa: E731
    if kind == "fraction":
        return ("frac", e(), e(), r.choice(["bar", "bar", "bar", "skw", "lin"]))
    if kind == "binomial":
        return ("d", "(", [("frac", a(), a(), "noBar")])
    if kind == "superscript":
        return ("sup", a(), e())
    if kind == "subscript":
        return ("sub", a(), e())
    if kind == "subsup":
        return ("subsup", a(), a(), a())
    if kind == "prescript":
        return ("pre", a(), a(), a())
    if kind == "nary":
        op = r.choice(["sum", "prod", "int", "oint", "bigcup"])
        loc = "subSup" if op in ("int", "oint") else r.choice(["undOvr", "undOvr", "subSup"])
        lo = R(r.choice("ijk"), "=", str(r.randint(0, 1))) if op not in ("int", "oint") else a()
        hi = T(r.choice(["n", "N", "∞", "m"])) if op not in ("int", "oint") else a()
        if r.random() < 0.15:
            hi = None
        if r.random() < 0.08:
            lo = None
        return ("nary", op, lo, hi, e(), loc)
    if kind == "radical":
        return ("rad", None if r.random() < 0.6 else T(str(r.randint(3, 5))), e())
    if kind == "matrix":
        nr, nc = r.randint(2, 3), r.randint(2, 3)
        m = ("mat", [[a() for _ in range(nc)] for _ in range(nr)])
        return ("d", r.choice(["(", "[", "|"]), [m]) if r.random() < 0.8 else m
    if kind == "eqarray":
        return ("eqarr", [("row", [T(r.choice("xyz")), T("="), e()]) for _ in range(r.randint(2, 3))])
    if kind == "accent":
        return ("acc", r.choice(list(ACC)), T(r.choice("xyzv")))
    if kind == "bar":
        return ("bar", r.choice(["top", "bot"]), a())
    if kind == "delimiter":
        return ("d", r.choice(["(", "[", "{", "|"]), [e()] if r.random() < 0.8 else [e(), e()])
    if kind == "function":
        return ("func", r.choice(FUNCS), a())
    if kind == "limit":
        return ("lim", R(r.choice("xn"), "→", r.choice(["0", "∞", "a"])), e())
    if kind == "underbrace":
        return ("brace", e(), T(r.choice("nkm")))
    if kind == "eqnumber":
        return ("eqno", ("row", [T("E"), T("="), ("sup", T("m"), T("2")), T("+"), e()]), str(r.randint(1, 40)))
    if kind == "nested":
        return ("frac", ("rad", None, ("sup", a(), ("frac", a(), a(), "bar"))),
                ("nary", "sum", R("i", "=", "1"), T("n"), ("sub", T("x"), T("i")), "undOvr"), "bar")
    raise ValueError(kind)


CONSTRUCTS = ["fraction", "binomial", "superscript", "subscript", "subsup", "prescript", "nary", "radical", "matrix",
              "eqarray", "accent", "bar", "delimiter", "function", "limit", "underbrace", "eqnumber", "nested"]


def random_cases(per=40, seed=11):
    r = random.Random(seed)
    out = []
    for kind in CONSTRUCTS:
        for i in range(per):
            n = construct(r, kind)
            if kind not in ("eqnumber", "eqarray") and r.random() < 0.3:
                n = ("row", [T(r.choice("fgh")), T("="), n])
            out.append({"id": f"{kind}-{i:03d}", "construct": kind, "ast": n, "source": "generated"})
    return out


# ---------------------------------------------------------------- hand-written cases: OMML and LaTeX typed by hand
HAND = [
    ("fraction", "<m:f><m:num><m:r><m:t>a</m:t></m:r></m:num><m:den><m:r><m:t>b</m:t></m:r></m:den></m:f>", [r"\frac{a}{b}"]),
    ("fraction", "<m:f><m:num><m:r><m:t>x+1</m:t></m:r></m:num><m:den><m:sSup><m:e><m:r><m:t>x</m:t></m:r></m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup><m:r><m:t>-1</m:t></m:r></m:den></m:f>", [r"\frac{x+1}{x^{2}-1}"]),
    ("fraction", '<m:f><m:fPr><m:type m:val="lin"/></m:fPr><m:num><m:r><m:t>dy</m:t></m:r></m:num><m:den><m:r><m:t>dx</m:t></m:r></m:den></m:f>', [r"dy/dx", r"{dy}/{dx}"]),
    ("superscript", "<m:sSup><m:e><m:r><m:t>e</m:t></m:r></m:e><m:sup><m:r><m:t>-</m:t></m:r><m:sSup><m:e><m:r><m:t>x</m:t></m:r></m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup></m:sup></m:sSup>", [r"e^{-x^{2}}"]),
    ("subsup", "<m:sSubSup><m:e><m:r><m:t>x</m:t></m:r></m:e><m:sub><m:r><m:t>i</m:t></m:r></m:sub><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSubSup>", [r"x_{i}^{2}"]),
    ("subscript", "<m:sSub><m:e><m:r><m:t>a</m:t></m:r></m:e><m:sub><m:r><m:t>n+1</m:t></m:r></m:sub></m:sSub><m:r><m:t>=2</m:t></m:r><m:sSub><m:e><m:r><m:t>a</m:t></m:r></m:e><m:sub><m:r><m:t>n</m:t></m:r></m:sub></m:sSub>", [r"a_{n+1}=2a_{n}"]),
    ("prescript", "<m:sPre><m:sub><m:r><m:t>6</m:t></m:r></m:sub><m:sup><m:r><m:t>14</m:t></m:r></m:sup><m:e><m:r><m:t>C</m:t></m:r></m:e></m:sPre>", [r"{}_{6}^{14}C", r"\prescript{14}{6}{C}"]),
    ("nary", '<m:nary><m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="undOvr"/></m:naryPr><m:sub><m:r><m:t>i=1</m:t></m:r></m:sub><m:sup><m:r><m:t>n</m:t></m:r></m:sup><m:e><m:r><m:t>i</m:t></m:r></m:e></m:nary><m:r><m:t>=</m:t></m:r><m:f><m:num><m:r><m:t>n(n+1)</m:t></m:r></m:num><m:den><m:r><m:t>2</m:t></m:r></m:den></m:f>', [r"\sum_{i=1}^{n}i=\frac{n(n+1)}{2}"]),
    ("nary", '<m:nary><m:naryPr><m:limLoc m:val="subSup"/></m:naryPr><m:sub><m:r><m:t>0</m:t></m:r></m:sub><m:sup><m:r><m:t>∞</m:t></m:r></m:sup><m:e><m:sSup><m:e><m:r><m:t>e</m:t></m:r></m:e><m:sup><m:r><m:t>-x</m:t></m:r></m:sup></m:sSup><m:r><m:t>dx</m:t></m:r></m:e></m:nary>', [r"\int_{0}^{\infty}e^{-x}dx"]),
    ("nary", '<m:nary><m:naryPr><m:chr m:val="∏"/><m:limLoc m:val="undOvr"/><m:supHide m:val="1"/></m:naryPr><m:sub><m:r><m:t>p</m:t></m:r></m:sub><m:sup/><m:e><m:r><m:t>p</m:t></m:r></m:e></m:nary>', [r"\prod_{p}p"]),
    ("radical", '<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e><m:sSup><m:e><m:r><m:t>b</m:t></m:r></m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup><m:r><m:t>-4ac</m:t></m:r></m:e></m:rad>', [r"\sqrt{b^{2}-4ac}"]),
    ("radical", "<m:rad><m:deg><m:r><m:t>3</m:t></m:r></m:deg><m:e><m:r><m:t>x</m:t></m:r></m:e></m:rad>", [r"\sqrt[3]{x}"]),
    ("matrix", "<m:d><m:e><m:m><m:mr><m:e><m:r><m:t>a</m:t></m:r></m:e><m:e><m:r><m:t>b</m:t></m:r></m:e></m:mr><m:mr><m:e><m:r><m:t>c</m:t></m:r></m:e><m:e><m:r><m:t>d</m:t></m:r></m:e></m:mr></m:m></m:e></m:d>", [r"\begin{pmatrix}a&b\\c&d\end{pmatrix}"]),
    ("matrix", '<m:d><m:dPr><m:begChr m:val="["/><m:endChr m:val="]"/></m:dPr><m:e><m:m><m:mr><m:e><m:r><m:t>1</m:t></m:r></m:e><m:e><m:r><m:t>0</m:t></m:r></m:e></m:mr><m:mr><m:e><m:r><m:t>0</m:t></m:r></m:e><m:e><m:r><m:t>1</m:t></m:r></m:e></m:mr></m:m></m:e></m:d>', [r"\begin{bmatrix}1&0\\0&1\end{bmatrix}"]),
    ("matrix", '<m:d><m:dPr><m:begChr m:val="|"/><m:endChr m:val="|"/></m:dPr><m:e><m:m><m:mr><m:e><m:r><m:t>x</m:t></m:r></m:e><m:e><m:r><m:t>y</m:t></m:r></m:e></m:mr><m:mr><m:e><m:r><m:t>z</m:t></m:r></m:e><m:e><m:r><m:t>w</m:t></m:r></m:e></m:mr></m:m></m:e></m:d>', [r"\begin{vmatrix}x&y\\z&w\end{vmatrix}"]),
    ("eqarray", "<m:eqArr><m:e><m:r><m:t>x+y=1</m:t></m:r></m:e><m:e><m:r><m:t>x-y=3</m:t></m:r></m:e></m:eqArr>", [r"\begin{aligned}x+y=1\\x-y=3\end{aligned}", r"\begin{array}{l}x+y=1\\x-y=3\end{array}", r"\begin{matrix}x+y=1\\x-y=3\end{matrix}", r"\begin{gathered}x+y=1\\x-y=3\end{gathered}", r"\begin{array}{c}x+y=1\\x-y=3\end{array}"]),
    ("accent", "<m:acc><m:e><m:r><m:t>x</m:t></m:r></m:e></m:acc>", [r"\hat{x}"]),
    ("accent", '<m:acc><m:accPr><m:chr m:val="⃗"/></m:accPr><m:e><m:r><m:t>v</m:t></m:r></m:e></m:acc>', [r"\vec{v}"]),
    ("accent", '<m:acc><m:accPr><m:chr m:val="̃"/></m:accPr><m:e><m:r><m:t>a</m:t></m:r></m:e></m:acc>', [r"\tilde{a}"]),
    ("accent", '<m:acc><m:accPr><m:chr m:val="̇"/></m:accPr><m:e><m:r><m:t>q</m:t></m:r></m:e></m:acc>', [r"\dot{q}"]),
    ("bar", '<m:bar><m:barPr><m:pos m:val="top"/></m:barPr><m:e><m:r><m:t>z</m:t></m:r></m:e></m:bar>', [r"\overline{z}"]),
    ("bar", "<m:bar><m:e><m:r><m:t>AB</m:t></m:r></m:e></m:bar>", [r"\underline{AB}"]),
    ("delimiter", "<m:sSup><m:e><m:d><m:e><m:r><m:t>a+b</m:t></m:r></m:e></m:d></m:e><m:sup><m:r><m:t>2</m:t></m:r></m:sup></m:sSup>", [r"\left(a+b\right)^{2}"]),
    ("delimiter", '<m:d><m:dPr><m:begChr m:val="{"/><m:endChr m:val="}"/></m:dPr><m:e><m:r><m:t>x</m:t></m:r></m:e><m:e><m:r><m:t>x&gt;0</m:t></m:r></m:e></m:d>', [r"\left\{x|x>0\right\}"]),
    ("function", '<m:func><m:fName><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>sin</m:t></m:r></m:fName><m:e><m:r><m:t>θ</m:t></m:r></m:e></m:func>', [r"\sin{\theta}", r"\sin \theta"]),
    ("function", '<m:func><m:fName><m:sSub><m:e><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>log</m:t></m:r></m:e><m:sub><m:r><m:t>2</m:t></m:r></m:sub></m:sSub></m:fName><m:e><m:r><m:t>n</m:t></m:r></m:e></m:func>', [r"\log_{2}{n}", r"\log_{2} n"]),
    ("limit", '<m:func><m:fName><m:limLow><m:e><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>lim</m:t></m:r></m:e><m:lim><m:r><m:t>x→0</m:t></m:r></m:lim></m:limLow></m:fName><m:e><m:f><m:num><m:func><m:fName><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>sin</m:t></m:r></m:fName><m:e><m:r><m:t>x</m:t></m:r></m:e></m:func></m:num><m:den><m:r><m:t>x</m:t></m:r></m:den></m:f></m:e></m:func>', [r"\lim_{x\to 0}\frac{\sin x}{x}", r"\lim_{x\to 0}{\frac{\sin{x}}{x}}"]),
    ("underbrace", '<m:limLow><m:e><m:groupChr><m:groupChrPr><m:chr m:val="⏟"/><m:pos m:val="bot"/><m:vertJc m:val="top"/></m:groupChrPr><m:e><m:r><m:t>1+…+1</m:t></m:r></m:e></m:groupChr></m:e><m:lim><m:r><m:t>n</m:t></m:r></m:lim></m:limLow>', [r"\underbrace{1+\ldots+1}_{n}", r"\underbrace{1+\dots+1}_{n}"]),
    ("eqnumber", "<m:eqArr><m:e><m:r><m:t>F=ma</m:t></m:r><m:r><m:t>#(2)</m:t></m:r></m:e></m:eqArr>", [r"F=ma\tag{2}"]),
    ("binomial", '<m:d><m:e><m:f><m:fPr><m:type m:val="noBar"/></m:fPr><m:num><m:r><m:t>n</m:t></m:r></m:num><m:den><m:r><m:t>k</m:t></m:r></m:den></m:f></m:e></m:d>', [r"\binom{n}{k}", r"\left({n \atop k}\right)"]),
    ("nested", '<m:sSup><m:e><m:d><m:e><m:f><m:num><m:r><m:t>1</m:t></m:r></m:num><m:den><m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e><m:r><m:t>2π</m:t></m:r></m:e></m:rad></m:den></m:f></m:e></m:d></m:e><m:sup><m:r><m:t>n</m:t></m:r></m:sup></m:sSup>', [r"\left(\frac{1}{\sqrt{2\pi}}\right)^{n}"]),
]


def hand_cases():
    return [{"id": f"hand-{i:02d}", "construct": c, "omml": o, "gold": g, "source": "hand"} for i, (c, o, g) in enumerate(HAND)]


def all_cases(per=40):
    cs = []
    for c in random_cases(per):
        c["omml"] = om(c["ast"])
        c["gold"] = tx(c["ast"])
        c["mml"] = mm(c["ast"])
        c["eqno"] = c["ast"][2] if c["ast"][0] == "eqno" else None
        cs.append(c)
    for c in hand_cases():
        c["eqno"] = "2" if c["construct"] == "eqnumber" else None
        cs.append(c)
    return cs


NS = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" ' \
     'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def omath(c):
    return f"<m:oMath {NS}>{c['omml']}</m:oMath>"


def docx(cases, path):
    """Minimal DOCX: one marker paragraph then one display equation (oMathPara) per case."""
    import zipfile
    body = []
    for c in cases:
        body.append(f'<w:p><w:r><w:t>{c["marker"]}</w:t></w:r></w:p>')
        body.append(f"<w:p><m:oMathPara><m:oMath>{c['omml']}</m:oMath></m:oMathPara></w:p>")
    body.append('<w:p><w:r><w:t>EQEND</w:t></w:r></w:p>')
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {NS}><w:body>' + "".join(body)
           + '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" '
           'w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/'
          'package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
          'relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/'
          'document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"'
          '/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats'
            '.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)

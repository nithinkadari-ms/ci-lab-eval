"""Fair LaTeX normaliser for the Word-equation scores (milestone 11).

Built on the round-3 normaliser (formula/scripts/texnorm.py). On top of it, differences that do not
change the rendered structure are ignored, the same way for every system and for the gold:
  - Unicode symbols vs control words (Greek letters, operators, arrows, dots: the glyph-rebuild
    prototype's own tables, formula/r3/logic/mathmap.py), invisible characters dropped;
  - \\genfrac{}{}{0pt}{}{a}{b}, {a \\atop b} and \\binom{a}{b} (= (a atop b)) as one form;
  - \\sin(a) vs \\sin{a}: parentheses that only wrap the argument of an operator name;
  - \\overrightarrow vs \\vec.
Structural differences (fraction vs slash, script placement, missing or extra content, matrix shape)
still count."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "formula", "scripts"))
sys.path.insert(0, os.path.join(ROOT, "formula", "r3", "logic"))
import texnorm  # noqa: E402
from mathmap import GREEK, SYM  # noqa: E402

INVISIBLE = {"⁡", "⁢", "⁣", "⁤", "​", "﻿", " ", " ", " ", " ",
             " ", " ", " ", " ", "⏟", "⏞"}
EXTRA = {"−": "-", "‐": "-", "‑": "-", "–": "-", "′": "'", "″": "''",
         "‖": r"\|", "∥": r"\|", "⋅": r"\cdot", "·": r"\cdot", "∙": r"\cdot",
         "→": r"\rightarrow", "∞": r"\infty", "…": r"\ldots", "⋯": r"\cdots"}
OPNAMES = {t[1:] for t in texnorm.OPS}
texnorm.ARITY.setdefault(r"\atop", 2)


def unicode_to_macros(s):
    out = []
    for ch in s:
        if ch in INVISIBLE:
            out.append(" ")
            continue
        if ch in EXTRA:
            out.append(" " + EXTRA[ch] + " ")
            continue
        if ch in GREEK and ch not in "ΑΒΕΖΗΙΚΜΝΟΡΤΧο":
            out.append(" " + GREEK[ch] + " ")
            continue
        if ch in SYM and not ch.isascii():
            tok = SYM[ch][0]
            out.append(" " + tok + " ")
            continue
        out.append(ch)
    return "".join(out)


def _split_atop(nodes):
    """A list (group or top level) with a top-level atop, choose or over becomes
    atop{left}{right} (frac for over; choose adds the parentheses)."""
    res = [("G", _split_atop(n[1])) if isinstance(n, tuple) else n for n in nodes]
    for k, t in enumerate(res):
        if isinstance(t, str) and t in (r"\atop", r"\choose", r"\over"):
            marker = r"\frac" if t == r"\over" else r"\atop"
            out = [marker, ("G", res[:k]), ("G", res[k + 1:])]
            return ["(", *out, ")"] if t == r"\choose" else out
    return res


def _genfrac_and_binom(nodes):
    out = []
    i = 0
    while i < len(nodes):
        n = nodes[i]
        if isinstance(n, tuple):
            out.append(("G", _genfrac_and_binom(n[1])))
            i += 1
            continue
        if n == r"\genfrac" and i + 6 <= len(nodes):
            args = nodes[i + 1:i + 7]
            a, b = args[4], args[5]
            out += [r"\atop", a if isinstance(a, tuple) else ("G", [a]), b if isinstance(b, tuple) else ("G", [b])]
            i += 7
            continue
        if n in (r"\binom", r"\dbinom", r"\tbinom") and i + 2 < len(nodes):
            a, b = nodes[i + 1], nodes[i + 2]
            out += ["(", r"\atop", a if isinstance(a, tuple) else ("G", [a]),
                    b if isinstance(b, tuple) else ("G", [b]), ")"]
            i += 3
            continue
        if n == r"\overrightarrow":
            out.append(r"\vec")
            i += 1
            continue
        out.append(n)
        i += 1
    return out


def _drop_op_parens(toks):
    """`s i n ( x )` -> `s i n x` when the parentheses wrap exactly the argument."""
    out = list(toks)
    changed = True
    while changed:
        changed = False
        for k in range(len(out)):
            if out[k] != "(":
                continue
            word = ""
            j = k - 1
            while j >= 0 and len(out[j]) == 1 and out[j].isalpha():
                word = out[j] + word
                j -= 1
            if not any(word.endswith(w) for w in OPNAMES):
                continue
            depth = 0
            for m in range(k, len(out)):
                if out[m] == "(":
                    depth += 1
                elif out[m] == ")":
                    depth -= 1
                    if depth == 0:
                        out = out[:k] + out[k + 1:m] + out[m + 1:]
                        changed = True
                        break
            if changed:
                break
    return out


def norm_tokens(s):
    s = unicode_to_macros(s or "")
    s = s.replace(r"\begin{align*}", r"\begin{aligned}").replace(r"\end{align*}", r"\end{aligned}")
    nodes, _ = texnorm.parse(texnorm.tokenize(s))
    nodes = _genfrac_and_binom(_split_atop(nodes))
    toks = texnorm.flatten(texnorm.norm_nodes(nodes))
    toks = texnorm.merge_scripts(toks)
    while toks and toks[-1] == r"\\":
        toks.pop()
    return _drop_op_parens(toks)


def normalize(s):
    try:
        return "".join(norm_tokens(s))
    except Exception:  # noqa: BLE001
        return "ERR:" + (s or "")


if __name__ == "__main__":
    tests = [
        (r"\alpha+\beta", "α+β", True), (r"a\cdot b", "a·b", True),
        (r"\left|\begin{matrix}a&b\\c&d\end{matrix}\right|", r"\begin{vmatrix}a&b\\c&d\end{vmatrix}", True),
        (r"\genfrac{}{}{0pt}{}{n}{k}", r"{n \atop k}", True), (r"\left({n \atop k}\right)", r"\binom{n}{k}", True),
        (r"\sin(a)", r"\sin{a}", True), (r"\sin \theta", r"\sin{\theta}", True),
        (r"\frac{a}{b}", r"a/b", False), (r"x^{2}", r"x_{2}", False), (r"\sqrt{x}", r"\sqrt[3]{x}", False),
        (r"\vec{v}", r"\overrightarrow{v}", True), (r"a-b", "a−b", True),
    ]
    bad = 0
    for a, b, same in tests:
        ok = (normalize(a) == normalize(b)) == same
        bad += not ok
        print("ok " if ok else "BAD", normalize(a), "|", normalize(b))
    sys.exit(1 if bad else 0)

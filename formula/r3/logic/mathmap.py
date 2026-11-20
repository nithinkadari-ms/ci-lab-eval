"""Map PDF glyphs (unicode from the text layer + font name) to LaTeX tokens and token classes."""
import re
import unicodedata

# ---------------------------------------------------------------- font classes
FAMILY_KEYS = [
    ("CM/LM", ("cmmi", "cmr", "cmsy", "cmex", "cmbx", "cmti", "cmss", "cmtt", "cmbsy", "cmmib", "cmsl", "cmcsc", "cmu",
               "lmroman", "lmmath", "lmsans", "lmmono", "lmmi", "lmsy", "lmex", "latinmodern", "msbm", "msam", "eufm",
               "eufb", "eusm", "rsfs", "cmitt", "sfrm", "ecrm", "ecti", "ecbx", "ectt", "ecss", "tcrm")),
    ("STIX/XITS", ("stix", "xits")),
    ("Times-like", ("times", "nimbusrom", "termes", "txmi", "txsy", "txex", "txr", "ptmr", "ptmri", "rtxmi", "rtxr",
                    "newtx", "mathptmx", "ntxmi", "ntxsy", "ntxex", "zrmm", "txb", "nimbusromno9l", "utmr", "utmri",
                    "rtxsc", "txtt", "txss", "rpxr")),
    ("Libertine", ("libertin", "biolinum", "libertinus", "lbt")),
    ("Palatino-like", ("palatino", "pxmi", "pxsy", "pxex", "pagella", "pplr", "pplri", "urwpalladio", "zplm")),
    ("Cambria/Office", ("cambria", "calibri", "arial", "helvetica", "segoe")),
]


def base_font(name):
    name = (name or "").split("+")[-1]
    return name.lower()


def font_family(name):
    b = base_font(name)
    for fam, keys in FAMILY_KEYS:
        if any(k in b for k in keys):
            return fam
    return "other"


def font_role(name):
    """Coarse role of a font: mi (math italic), rm, sy, ex, bb, frak, scr, cal, tt, sf, plus a bold flag."""
    b = base_font(name)
    bold = any(k in b for k in ("cmbx", "cmmib", "cmbsy", "bold", "-bd", "-bx", "lmroman10-bold", "semibold"))
    if "msbm" in b or "doublestruck" in b or "bbold" in b or "dsrom" in b:
        return "bb", bold
    if "eufm" in b or "eufb" in b or "fraktur" in b:
        return "frak", bold
    if "rsfs" in b or "script" in b and "math" not in b:
        return "scr", bold
    if "eusm" in b or "eusb" in b:
        return "cal", bold
    if any(k in b for k in ("cmex", "lmex", "mathextension", "txex", "pxex", "esint", "stixsize", "stixintegrals",
                            "stixvariants", "ntxex")):
        return "ex", bold
    if any(k in b for k in ("cmsy", "cmbsy", "lmsy", "mathsymbols", "txsy", "pxsy", "ntxsy", "msam")):
        return "sy", bold
    if any(k in b for k in ("cmmi", "lmmi", "mathitalic", "txmi", "pxmi", "rtxmi", "ntxmi", "cmmib", "zxxmi")):
        return "mi", bold
    if any(k in b for k in ("cmtt", "lmmono", "courier", "txtt", "mono")):
        return "tt", bold
    if any(k in b for k in ("cmss", "lmsans", "helvet", "arial", "biolinum", "sans")):
        return "sf", bold
    return "rm", bold or any(k in b for k in ("cmbx", "bold"))


# ---------------------------------------------------------------- TeX font encodings (used when ToUnicode is missing)
GREEK_UP = "ΓΔΘΛΞΠΣΥΦΨΩ"
OML = {i: GREEK_UP[i] for i in range(11)}
OML.update({0x0B + i: c for i, c in enumerate("αβγδϵζηθικλμνξπρστυϕχψωεϑϖϱςφ")})
OML.update({0x3A: ".", 0x3B: ",", 0x3C: "<", 0x3D: "/", 0x3E: ">", 0x3F: "⋆", 0x40: "∂", 0x60: "ℓ", 0x7B: "ı",
            0x7C: "ȷ", 0x7D: "℘", 0x7E: "⃗"})
OT1 = {i: GREEK_UP[i] for i in range(11)}
OT1.update({0x7B: "–", 0x7C: "—", 0x7D: "˝", 0x7E: "˜", 0x7F: "¨", 0x12: "`", 0x13: "´", 0x14: "ˇ", 0x15: "˘",
            0x16: "¯", 0x17: "˚", 0x5E: "ˆ", 0x5F: "˙"})
OMS = dict(enumerate("−·×∗÷⋄±∓⊕⊖⊗⊘⊙○∘•≍≡⊆⊇≤≥⪯⪰∼≈⊂⊃≪≫≺≻←→↑↓↔↗↘≃⇐⇒⇑⇓⇔↖↙∝′∞∈∋△▽"))
OMS.update({0x36: "̸", 0x37: "↦", 0x38: "∀", 0x39: "∃", 0x3A: "¬", 0x3B: "∅", 0x3C: "ℜ", 0x3D: "ℑ", 0x3E: "⊤",
            0x3F: "⊥", 0x40: "ℵ", 0x5B: "∪", 0x5C: "∩", 0x5D: "⊎", 0x5E: "∧", 0x5F: "∨", 0x60: "⊢", 0x61: "⊣",
            0x62: "⌊", 0x63: "⌋", 0x64: "⌈", 0x65: "⌉", 0x66: "{", 0x67: "}", 0x68: "⟨", 0x69: "⟩", 0x6A: "|",
            0x6B: "‖", 0x6C: "↕", 0x6D: "⇕", 0x6E: "\\", 0x6F: "≀", 0x70: "√", 0x71: "⨿", 0x72: "∇", 0x73: "∫",
            0x74: "⊔", 0x75: "⊓", 0x76: "⊑", 0x77: "⊒", 0x78: "§", 0x79: "†", 0x7A: "‡", 0x7B: "¶", 0x7C: "♣",
            0x7D: "♢", 0x7E: "♡", 0x7F: "♠"})
OMX = {}
for codes, ch in [((0x00, 0x10, 0x12, 0x20, 0x30, 0x40, 0x42), "("), ((0x01, 0x11, 0x13, 0x21, 0x31, 0x41, 0x43), ")"),
                  ((0x02, 0x14, 0x22, 0x32, 0x36, 0x34, 0x68), "["), ((0x03, 0x15, 0x23, 0x33, 0x37, 0x35, 0x69), "]"),
                  ((0x04, 0x16, 0x24, 0x6A), "⌊"), ((0x05, 0x17, 0x25, 0x6B), "⌋"), ((0x06, 0x18, 0x26, 0x6C), "⌈"),
                  ((0x07, 0x19, 0x27, 0x6D), "⌉"), ((0x08, 0x1A, 0x28, 0x38, 0x3A, 0x3C, 0x3E, 0x6E), "{"),
                  ((0x09, 0x1B, 0x29, 0x39, 0x3B, 0x3D, 0x6F), "}"), ((0x0A, 0x1C, 0x2A, 0x44), "⟨"),
                  ((0x0B, 0x1D, 0x2B, 0x45), "⟩"), ((0x0C, 0x3F, 0x42), "|"), ((0x0D, 0x77), "‖"),
                  ((0x0E, 0x1E, 0x2C), "/"), ((0x0F, 0x1F, 0x2D), "\\"), ((0x46, 0x47), "⨆"), ((0x48, 0x49), "∮"),
                  ((0x4A, 0x4B), "⨀"), ((0x4C, 0x4D), "⨁"), ((0x4E, 0x4F), "⨂"), ((0x50, 0x58), "∑"),
                  ((0x51, 0x59), "∏"), ((0x52, 0x5A), "∫"), ((0x53, 0x5B), "⋃"), ((0x54, 0x5C), "⋂"),
                  ((0x55, 0x5D), "⨄"), ((0x56, 0x5E), "⋀"), ((0x57, 0x5F), "⋁"), ((0x60, 0x61), "∐"),
                  ((0x62, 0x63, 0x64), "ˆ"), ((0x65, 0x66, 0x67), "˜"), ((0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76), "√")]:
    for c in codes:
        OMX[c] = ch

# ---------------------------------------------------------------- unicode -> LaTeX
GREEK = {"α": "\\alpha", "β": "\\beta", "γ": "\\gamma", "δ": "\\delta", "ϵ": "\\epsilon", "ε": "\\varepsilon",
         "ζ": "\\zeta", "η": "\\eta", "θ": "\\theta", "ϑ": "\\vartheta", "ι": "\\iota", "κ": "\\kappa", "ϰ": "\\varkappa",
         "λ": "\\lambda", "μ": "\\mu", "µ": "\\mu", "ν": "\\nu", "ξ": "\\xi", "ο": "o", "π": "\\pi", "ϖ": "\\varpi",
         "ρ": "\\rho", "ϱ": "\\varrho", "σ": "\\sigma", "ς": "\\varsigma", "τ": "\\tau", "υ": "\\upsilon",
         "ϕ": "\\phi", "φ": "\\varphi", "χ": "\\chi", "ψ": "\\psi", "ω": "\\omega", "Γ": "\\Gamma", "Δ": "\\Delta",
         "Θ": "\\Theta", "Λ": "\\Lambda", "Ξ": "\\Xi", "Π": "\\Pi", "Σ": "\\Sigma", "Υ": "\\Upsilon", "ϒ": "\\Upsilon",
         "Φ": "\\Phi", "Ψ": "\\Psi", "Ω": "\\Omega", "Ϝ": "\\digamma", "ϝ": "\\digamma"}
for up, lat in [("Α", "A"), ("Β", "B"), ("Ε", "E"), ("Ζ", "Z"), ("Η", "H"), ("Ι", "I"), ("Κ", "K"), ("Μ", "M"),
                ("Ν", "N"), ("Ο", "O"), ("Ρ", "P"), ("Τ", "T"), ("Χ", "X")]:
    GREEK[up] = lat
SYM = {
    "+": ("+", "bin"), "−": ("-", "bin"), "-": ("-", "bin"), "–": ("-", "bin"), "×": ("\\times", "bin"),
    "·": ("\\cdot", "bin"), "⋅": ("\\cdot", "bin"), "∙": ("\\cdot", "bin"), "÷": ("\\div", "bin"), "±": ("\\pm", "bin"),
    "∓": ("\\mp", "bin"), "∗": ("*", "bin"), "*": ("*", "bin"), "⋆": ("\\star", "bin"), "∘": ("\\circ", "bin"),
    "○": ("\\bigcirc", "bin"), "•": ("\\bullet", "bin"), "⊕": ("\\oplus", "bin"), "⊖": ("\\ominus", "bin"),
    "⊗": ("\\otimes", "bin"), "⊘": ("\\oslash", "bin"), "⊙": ("\\odot", "bin"), "∪": ("\\cup", "bin"),
    "∩": ("\\cap", "bin"), "⊎": ("\\uplus", "bin"), "∧": ("\\wedge", "bin"), "∨": ("\\vee", "bin"),
    "∖": ("\\setminus", "bin"), "⊔": ("\\sqcup", "bin"), "⊓": ("\\sqcap", "bin"), "⋄": ("\\diamond", "bin"),
    "†": ("\\dagger", "bin"), "‡": ("\\ddagger", "bin"), "≀": ("\\wr", "bin"), "⨿": ("\\amalg", "bin"),
    "⊠": ("\\boxtimes", "bin"), "⊞": ("\\boxplus", "bin"), "⋉": ("\\ltimes", "bin"), "⋊": ("\\rtimes", "bin"),
    "=": ("=", "rel"), "≠": ("\\neq", "rel"), "<": ("<", "rel"), ">": (">", "rel"), "≤": ("\\leq", "rel"),
    "≥": ("\\geq", "rel"), "⩽": ("\\leqslant", "rel"), "⩾": ("\\geqslant", "rel"), "≪": ("\\ll", "rel"),
    "≫": ("\\gg", "rel"), "≈": ("\\approx", "rel"), "≃": ("\\simeq", "rel"), "≅": ("\\cong", "rel"),
    "≡": ("\\equiv", "rel"), "∼": ("\\sim", "rel"), "~": ("\\sim", "rel"), "∝": ("\\propto", "rel"),
    "≍": ("\\asymp", "rel"), "∈": ("\\in", "rel"), "∉": ("\\notin", "rel"), "∋": ("\\ni", "rel"),
    "⊂": ("\\subset", "rel"), "⊃": ("\\supset", "rel"), "⊆": ("\\subseteq", "rel"), "⊇": ("\\supseteq", "rel"),
    "⊊": ("\\subsetneq", "rel"), "⊋": ("\\supsetneq", "rel"), "⊑": ("\\sqsubseteq", "rel"),
    "⊒": ("\\sqsupseteq", "rel"), "≺": ("\\prec", "rel"), "≻": ("\\succ", "rel"), "⪯": ("\\preceq", "rel"),
    "⪰": ("\\succeq", "rel"), "≲": ("\\lesssim", "rel"), "≳": ("\\gtrsim", "rel"), "≔": (":=", "rel"),
    "⊢": ("\\vdash", "rel"), "⊣": ("\\dashv", "rel"), "⊨": ("\\models", "rel"), "⊥": ("\\perp", "ord"),
    "∥": ("\\|", "fence"), "∣": ("\\mid", "rel"), "≜": ("\\triangleq", "rel"), "≐": ("\\doteq", "rel"),
    "≱": ("\\ngeq", "rel"), "⊲": ("\\triangleleft", "bin"), "⊳": ("\\triangleright", "bin"),
    "⊴": ("\\trianglelefteq", "rel"), "⊵": ("\\trianglerighteq", "rel"), "≅": ("\\cong", "rel"),
    "→": ("\\rightarrow", "rel"), "←": ("\\leftarrow", "rel"), "↔": ("\\leftrightarrow", "rel"),
    "⇒": ("\\Rightarrow", "rel"), "⇐": ("\\Leftarrow", "rel"), "⇔": ("\\Leftrightarrow", "rel"),
    "⟶": ("\\longrightarrow", "rel"), "⟵": ("\\longleftarrow", "rel"), "⟹": ("\\Longrightarrow", "rel"),
    "⟸": ("\\Longleftarrow", "rel"), "⟺": ("\\Longleftrightarrow", "rel"), "↦": ("\\mapsto", "rel"),
    "⟼": ("\\longmapsto", "rel"), "↑": ("\\uparrow", "rel"), "↓": ("\\downarrow", "rel"), "⇑": ("\\Uparrow", "rel"),
    "⇓": ("\\Downarrow", "rel"), "↗": ("\\nearrow", "rel"), "↘": ("\\searrow", "rel"), "↖": ("\\nwarrow", "rel"),
    "↙": ("\\swarrow", "rel"), "↪": ("\\hookrightarrow", "rel"), "↩": ("\\hookleftarrow", "rel"),
    "⇀": ("\\rightharpoonup", "rel"), "⇌": ("\\rightleftharpoons", "rel"), "↠": ("\\twoheadrightarrow", "rel"),
    "∀": ("\\forall", "ord"), "∃": ("\\exists", "ord"), "∄": ("\\nexists", "ord"), "¬": ("\\neg", "ord"),
    "∅": ("\\emptyset", "ord"), "∞": ("\\infty", "ord"), "∂": ("\\partial", "ord"), "∇": ("\\nabla", "ord"),
    "ℓ": ("\\ell", "ord"), "ℏ": ("\\hbar", "ord"), "ħ": ("\\hbar", "ord"), "ℜ": ("\\Re", "ord"), "ℑ": ("\\Im", "ord"),
    "ℵ": ("\\aleph", "ord"), "℘": ("\\wp", "ord"), "∠": ("\\angle", "ord"), "△": ("\\triangle", "ord"),
    "▽": ("\\triangledown", "ord"), "□": ("\\Box", "ord"), "◻": ("\\Box", "ord"), "■": ("\\blacksquare", "ord"),
    "⊤": ("\\top", "ord"), "♯": ("\\sharp", "ord"), "♭": ("\\flat", "ord"), "♮": ("\\natural", "ord"),
    "♣": ("\\clubsuit", "ord"), "♢": ("\\diamondsuit", "ord"), "♡": ("\\heartsuit", "ord"), "♠": ("\\spadesuit", "ord"),
    "ı": ("\\imath", "ord"), "ȷ": ("\\jmath", "ord"), "§": ("\\S", "ord"), "¶": ("\\P", "ord"), "°": ("^{\\circ}", "ord"),
    "′": ("\\prime", "prime"), "″": ("\\prime\\prime", "prime"), "'": ("\\prime", "prime"), "’": ("\\prime", "prime"),
    "…": ("\\ldots", "ord"), "⋯": ("\\cdots", "ord"), "⋮": ("\\vdots", "ord"), "⋱": ("\\ddots", "ord"),
    "∴": ("\\therefore", "rel"), "∵": ("\\because", "rel"), "√": ("\\sqrt", "rad"),
    "(": ("(", "open"), ")": (")", "close"), "[": ("[", "open"), "]": ("]", "close"), "{": ("\\{", "open"),
    "}": ("\\}", "close"), "⟨": ("\\langle", "open"), "⟩": ("\\rangle", "close"), "〈": ("\\langle", "open"),
    "〉": ("\\rangle", "close"), "⌊": ("\\lfloor", "open"), "⌋": ("\\rfloor", "close"), "⌈": ("\\lceil", "open"),
    "⌉": ("\\rceil", "close"), "|": ("|", "fence"), "‖": ("\\|", "fence"), "/": ("/", "ord"), "\\": ("\\backslash", "ord"),
    ",": (",", "punct"), ";": (";", "punct"), ":": (":", "rel"), ".": (".", "ord"), "!": ("!", "ord"), "?": ("?", "ord"),
    "∑": ("\\sum", "bigop"), "∏": ("\\prod", "bigop"), "∐": ("\\coprod", "bigop"), "∫": ("\\int", "bigop"),
    "∬": ("\\iint", "bigop"), "∭": ("\\iiint", "bigop"), "∮": ("\\oint", "bigop"), "⋃": ("\\bigcup", "bigop"),
    "⋂": ("\\bigcap", "bigop"), "⨁": ("\\bigoplus", "bigop"), "⨂": ("\\bigotimes", "bigop"),
    "⨀": ("\\bigodot", "bigop"), "⨄": ("\\biguplus", "bigop"), "⨆": ("\\bigsqcup", "bigop"),
    "⋀": ("\\bigwedge", "bigop"), "⋁": ("\\bigvee", "bigop"), "⨅": ("\\bigsqcap", "bigop"),
    "%": ("\\%", "ord"), "#": ("\\#", "ord"), "&": ("\\&", "ord"), "$": ("\\$", "ord"), "@": ("@", "ord"),
    "^": ("\\hat", "accent"), "ˆ": ("\\hat", "accent"), "̂": ("\\hat", "accent"), "˜": ("\\tilde", "accent"),
    "̃": ("\\tilde", "accent"), "¯": ("\\bar", "accent"), "̄": ("\\bar", "accent"), "ˉ": ("\\bar", "accent"),
    "˙": ("\\dot", "accent"), "̇": ("\\dot", "accent"), "¨": ("\\ddot", "accent"), "̈": ("\\ddot", "accent"),
    "ˇ": ("\\check", "accent"), "̌": ("\\check", "accent"), "´": ("\\acute", "accent"), "`": ("\\grave", "accent"),
    "˘": ("\\breve", "accent"), "̆": ("\\breve", "accent"), "⃗": ("\\vec", "accent"), "˚": ("\\mathring", "accent"),
    "̸": ("\\not", "not"),
}
ACCENT_CHARS = {k for k, v in SYM.items() if v[1] == "accent"}
STYLE_CMD = {"bb": "\\mathbb", "frak": "\\mathfrak", "scr": "\\mathscr", "cal": "\\mathcal", "tt": "\\mathtt",
             "sf": "\\mathsf"}


def math_alnum(ch):
    """Unicode mathematical alphanumerics (U+1D400 block, ℝ etc.) -> (style, base char) or None."""
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return None
    if not (name.startswith("MATHEMATICAL") or name.startswith("DOUBLE-STRUCK") or name.startswith("SCRIPT CAPITAL")
            or name.startswith("BLACK-LETTER") or name.startswith("PLANCK") or name.startswith("SCRIPT SMALL")):
        return None
    base = unicodedata.normalize("NFKC", ch)
    if not (len(base) == 1 and (base.isalnum() or base in GREEK)):
        return None
    style = None
    if "DOUBLE-STRUCK" in name:
        style = "bb"
    elif "FRAKTUR" in name or "BLACK-LETTER" in name:
        style = "frak"
    elif "SCRIPT" in name:
        style = "cal"
    elif "MONOSPACE" in name:
        style = "tt"
    elif "SANS-SERIF" in name:
        style = "sf"
    bold = "BOLD" in name
    return style, bold, base


PIECES = {}
for _codes, _ch in [((0xF8EB, 0xF8EC, 0xF8ED, 0x239B, 0x239C, 0x239D), "("), ((0xF8F6, 0xF8F7, 0xF8F8, 0x239E, 0x239F, 0x23A0), ")"),
                    ((0xF8EE, 0xF8EF, 0xF8F0, 0x23A1, 0x23A2, 0x23A3), "["), ((0xF8F9, 0xF8FA, 0xF8FB, 0x23A4, 0x23A5, 0x23A6), "]"),
                    ((0xF8F1, 0xF8F2, 0xF8F3, 0x23A7, 0x23A8, 0x23A9), "{"), ((0xF8FC, 0xF8FD, 0xF8FE, 0x23AB, 0x23AC, 0x23AD), "}"),
                    ((0xF8F4, 0x23AA), "brace-ext"), ((0xF8E6, 0x23D0), "|"), ((0x23B7,), "√")]:
    for _c in _codes:
        PIECES[_c] = _ch


def decode_char(u, font):
    """Return (char, unknown_flag) after encoding fallbacks for fonts without ToUnicode."""
    role, _ = font_role(font)
    b = base_font(font)
    if u in PIECES:
        return "piece:" + PIECES[u], False
    if role == "ex" and u < 0x80 and chr(u) not in "()[]{}|/\\<>":
        return OMX.get(u, None), u not in OMX
    if u < 0x20 or (role == "sy" and u < 0x80 and not chr(u).isalnum() and u not in (0x28, 0x29, 0x5B, 0x5D, 0x7B, 0x7D, 0x7C, 0x2F, 0x2C)):
        if role == "sy":
            return OMS.get(u), u not in OMS
        if role == "mi":
            return OML.get(u), u not in OML
        if u < 0x20:
            return OT1.get(u), u not in OT1
    if role == "mi" and u in (0x3C, 0x3E, 0x3D) and "cmmi" in b:
        return OML.get(u), False
    if 0xE000 <= u <= 0xF8FF or u == 0xFFFD:
        return None, True
    return chr(u), False


def to_latex(ch, font):
    """-> (latex, kind) for one decoded character. kind: letter, digit, bin, rel, ord, open, close, fence, punct,
    bigop, rad, accent, prime, not, unknown."""
    role, bold = font_role(font)
    if len(ch) == 1 and ch not in GREEK and ch not in SYM and not math_alnum(ch):
        n = unicodedata.normalize("NFKC", ch)
        if len(n) == 1 and (n in GREEK or n in SYM):
            ch = n
    ma = math_alnum(ch)
    if ma:
        style, bold2, base = ma
        tok = GREEK.get(base, base)
        if style in STYLE_CMD:
            tok = f"{STYLE_CMD[style]}{{{tok}}}"
        if bold or bold2:
            tok = f"\\mathbf{{{tok}}}"
        return tok, "letter"
    if ch in GREEK:
        tok = GREEK[ch]
        return (f"\\mathbf{{{tok}}}" if bold else tok), "letter"
    if ch.isascii() and ch.isalpha():
        if role == "sy" and ch.isupper():
            tok = f"\\mathcal{{{ch}}}"
        elif role in STYLE_CMD:
            tok = f"{STYLE_CMD[role]}{{{ch}}}"
        else:
            tok = ch
        if bold:
            tok = f"\\mathbf{{{tok}}}"
        return tok, "letter"
    if ch.isdigit() and ch.isascii():
        return (f"\\mathbf{{{ch}}}" if bold else ch), "digit"
    if role == "bb" and ch == "1":
        return "\\mathbb{1}", "letter"
    if ch in SYM:
        return SYM[ch]
    n = unicodedata.normalize("NFKC", ch)
    if n != ch and n in SYM:
        return SYM[n]
    if n != ch and len(n) == 1 and n.isascii() and n.isalnum():
        return n, "letter" if n.isalpha() else "digit"
    if ch.isalpha():
        return ch, "letter"
    return None, "unknown"

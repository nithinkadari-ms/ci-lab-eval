"""Rebuild LaTeX from the glyphs and rules of one formula region (no model).

Pipeline: glyph gathering with font names -> font classes and symbol mapping -> rows (y-cut through
whole-width gaps) -> per row, horizontal groups (x-overlap) -> per group: fraction, radical, big operator
with limits, accent / overline, stacked rows (matrix columns) -> sequence assembly with scripts by
size and baseline offset, fences, matrices / cases -> confidence -> LaTeX repair."""
import re
import statistics
from dataclasses import dataclass, field

try:
    from .mathmap import decode_char, to_latex, font_role, font_family, ACCENT_CHARS
except ImportError:
    from mathmap import decode_char, to_latex, font_role, font_family, ACCENT_CHARS

RELS = set()
OPNAMES = {"sin", "cos", "tan", "cot", "sec", "csc", "log", "ln", "exp", "lim", "max", "min", "sup", "inf", "det",
           "dim", "ker", "deg", "arg", "gcd", "lcm", "sinh", "cosh", "tanh", "arcsin", "arccos", "arctan", "Pr",
           "mod", "Tr", "tr", "diag", "sgn", "sign", "rank", "span", "supp", "argmax", "argmin", "liminf", "limsup"}


@dataclass
class Item:
    tok: str
    kind: str
    x0: float
    y0: float
    x1: float
    y1: float
    base: float
    size: float
    ch: str = ""
    font: str = ""
    is_rule: bool = False

    @property
    def cx(self):
        return (self.x0 + self.x1) / 2

    @property
    def cy(self):
        return (self.y0 + self.y1) / 2

    @property
    def w(self):
        return self.x1 - self.x0

    @property
    def h(self):
        return self.y1 - self.y0


@dataclass
class Atom:
    tex: str
    kind: str
    x0: float
    y0: float
    x1: float
    y1: float
    base: float
    size: float
    rows: list = None  # for stacks: list of row tex
    row_items: list = None
    small: bool = False
    cols: list = None
    row_atoms: list = None


class Ctx:
    def __init__(self):
        self.conf = 1.0
        self.notes = []

    def pen(self, f, note):
        self.conf *= f
        if len(self.notes) < 30:
            self.notes.append(note)


def bbox_of(items):
    return (min(i.x0 for i in items), min(i.y0 for i in items), max(i.x1 for i in items), max(i.y1 for i in items))


def main_size(items):
    sizes = [round(i.size * 2) / 2 for i in items if not i.is_rule and i.kind not in ("bigop", "rad") and i.size > 0]
    if not sizes:
        sizes = [i.size for i in items if i.size > 0] or [10.0]
    mx = max(sizes)
    big = [s for s in sizes if s >= 0.8 * mx]
    return statistics.mode(big)


# ---------------------------------------------------------------- items from glyphs
def make_items(glyphs, shapes, ctx):
    items = []
    for g in glyphs:
        ch, unknown = decode_char(g.u, g.font)
        if ch is None:
            ctx.pen(0.5, f"unmapped U+{g.u:04X} {g.font}")
            items.append(Item("?", "unknown", g.x0, g.y0, g.x1, g.y1, g.oy, g.size, "", g.font))
            continue
        if ch.startswith("piece:"):
            items.append(Item(ch[6:], "piece", g.x0, g.y0, g.x1, g.y1, g.oy, g.size, ch[6:], g.font))
            continue
        tok, kind = to_latex(ch, g.font)
        if tok is None:
            ctx.pen(0.5, f"no latex for {ch!r} U+{ord(ch):04X} {g.font}")
            items.append(Item("?", "unknown", g.x0, g.y0, g.x1, g.y1, g.oy, g.size, ch, g.font))
            continue
        x0, y0, x1, y1 = g.x0, g.y0, g.x1, g.y1
        if x1 - x0 < 0.05 and y1 - y0 < 0.05:
            x1, y1 = x0 + 0.3 * g.size, y0 + 0.5 * g.size
        items.append(Item(tok, kind, x0, y0, x1, y1, g.oy, g.size, ch, g.font))
    items = merge_pieces(items, ctx)
    for s in shapes:
        if s.kind == "hrule":
            items.append(Item("", "hrule", s.x0, s.y0, s.x1, s.y1, (s.y0 + s.y1) / 2, 0.0, is_rule=True))
        elif s.kind == "vrule":
            items.append(Item("|", "fence", s.x0, s.y0, s.x1, s.y1, s.y0, max(1.0, s.y1 - s.y0), "|", is_rule=True))
        elif s.kind == "image":
            ctx.pen(0.2, "image in region")
        else:
            ctx.pen(0.6, "non-rule drawing in region")
    return items


def merge_pieces(items, ctx):
    """Grown delimiters are built from stacked pieces (top, extension, bottom): merge them into one tall delimiter."""
    pieces = [i for i in items if i.kind == "piece"]
    if not pieces:
        return items
    rest = [i for i in items if i.kind != "piece"]
    pieces.sort(key=lambda i: (round(i.x0), -i.y1))
    groups = []
    for p in sorted(pieces, key=lambda i: -i.y1):
        for g in groups:
            gx0, gx1 = min(i.x0 for i in g), max(i.x1 for i in g)
            gy0 = min(i.y0 for i in g)
            if min(gx1, p.x1) - max(gx0, p.x0) > 0.3 * min(gx1 - gx0, p.x1 - p.x0) and p.y1 >= gy0 - 2.0:
                g.append(p)
                break
        else:
            groups.append([p])
    for g in groups:
        chars = [i.ch for i in g if i.ch not in ("brace-ext", "|")]
        ch = chars[0] if chars else ("|" if any(i.ch == "|" for i in g) else "{")
        tok, kind = to_latex(ch, "")
        x0, y0, x1, y1 = bbox_of(g)
        size = max(i.size for i in g)
        if ch == "√":
            tok, kind = "\\sqrt", "rad"
        rest.append(Item(tok, kind, x0, y0, x1, y1, min(i.base for i in g), size, ch, g[0].font))
    return rest


ARROWS = {("-", "\\rightarrow"): "\\longrightarrow", ("\\leftarrow", "-"): "\\longleftarrow",
          ("=", "\\Rightarrow"): "\\Longrightarrow", ("\\Leftarrow", "="): "\\Longleftarrow",
          ("\\leftarrow", "\\rightarrow"): "\\longleftrightarrow", ("\\Leftarrow", "\\Rightarrow"): "\\Longleftrightarrow",
          ("\\mapsto", "\\rightarrow"): "\\mapsto", ("\\mapsto", "-", "\\rightarrow"): "\\longmapsto",
          ("-", "-", "\\rightarrow"): "\\longrightarrow", ("\\leftarrow", "-", "-"): "\\longleftarrow",
          ("\\hookleftarrow", "\\rightarrow"): "\\hookrightarrow", ("-", "\\rightharpoonup"): "\\rightharpoonup",
          (":", "="): ":=", ("=", ":"): "=:"}


# ---------------------------------------------------------------- cuts
def x_groups(items, size):
    """Connected components: items overlapping clearly in x, or overlapping in x while stacked (y-disjoint)."""
    tol = 0.12 * size
    n = len(items)
    parent = list(range(n))

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for p_ in range(n):
        a = items[p_]
        for q_ in range(p_ + 1, n):
            b = items[q_]
            ov = min(a.x1, b.x1) - max(a.x0, b.x0)
            if ov <= 0:
                continue
            ydis = a.y1 < b.y0 or b.y1 < a.y0
            if ov > tol or (ydis and ov > 0.15 * min(max(a.w, 0.01), max(b.w, 0.01))):
                parent[find(p_)] = find(q_)
    comps = {}
    for k in range(n):
        comps.setdefault(find(k), []).append(items[k])
    return sorted(comps.values(), key=lambda g: min(i.x0 for i in g))



def y_rows(items, size, region_w, strict=True):
    """Split into rows at whole-width vertical gaps; refuse cuts that would separate a fraction rule, limits
    or scripts from their row."""
    if len(items) < 2:
        return [items]
    ivs = [(i.y0, i.y1, i) for i in sorted(items, key=lambda i: (i.y0, i.y1))]
    groups, cur, top = [], [ivs[0][2]], ivs[0][1]
    for y0, y1, it in ivs[1:]:
        if y0 > top + 0.12 * size:
            groups.append(cur)
            cur, top = [it], y1
        else:
            cur.append(it)
            top = max(top, y1)
    groups.append(cur)
    if len(groups) == 1:
        return [items]
    groups = groups[::-1]  # top to bottom

    def solid(g):
        gl = [i for i in g if not i.is_rule]
        if not gl:
            return False
        ms = max(i.size for i in gl)
        w = max(i.x1 for i in g) - min(i.x0 for i in g)
        return ms >= 0.88 * size and (w >= 0.2 * region_w or not strict)

    def blocked(up, lo):
        """A cut must not separate a fraction bar or big operator from material on the other side."""
        gap_top, gap_bot = min(i.y0 for i in up), max(i.y1 for i in lo)
        for side, other in ((up, lo), (lo, up)):
            for r in side:
                if (r.is_rule and r.kind == "hrule") or r.kind in ("bigop", "rad"):
                    near = min(abs(r.y0 - gap_top), abs(r.y1 - gap_bot), abs(r.y0 - gap_bot), abs(r.y1 - gap_top))
                    if near <= 0.9 * size and any(o.x1 > r.x0 and o.x0 < r.x1 for o in other):
                        return True
        return False

    merged = [groups[0]]
    for g in groups[1:]:
        prev = merged[-1]
        if solid(prev) and solid(g) and not only_rule(prev) and not only_rule(g) and not blocked(prev, g):
            merged.append(g)
        else:
            merged[-1] = prev + g
    # a row consisting of a lone rule belongs to a fraction: merge it with neighbours
    out = []
    for g in merged:
        if out and (only_rule(g) or only_rule(out[-1])):
            out[-1] = out[-1] + g
        else:
            out.append(g)
    return out


def only_rule(g):
    return all(i.is_rule for i in g)


# ---------------------------------------------------------------- parsing
def parse_block(items, ctx, top=False):
    if not items:
        return Atom("", "empty", 0, 0, 0, 0, 0, 0)
    size = main_size(items)
    x0, y0, x1, y1 = bbox_of(items)
    rows = y_rows(items, size, x1 - x0)
    if len(rows) > 1:
        ratoms = [parse_row(r, ctx) for r in rows]
        rtex = [ra.tex for ra in ratoms]
        if top:
            tex = "\\begin{aligned} " + " \\\\ ".join(rtex) + " \\end{aligned}"
        else:
            tex = "\\begin{matrix} " + " \\\\ ".join(rtex) + " \\end{matrix}"
        return Atom(tex, "stack", x0, y0, x1, y1, rows_base(rows), size, rows=rtex, row_items=rows, row_atoms=ratoms)
    return parse_row(items, ctx)


def rows_base(rows):
    mid = rows[len(rows) // 2]
    gl = [i for i in mid if not i.is_rule]
    return statistics.median(i.base for i in gl) if gl else (min(i.y0 for i in mid) + max(i.y1 for i in mid)) / 2


def parse_row(items, ctx):
    size = main_size(items)
    groups = x_groups(items, size)
    atoms = [parse_group(g, ctx, size) for g in groups]
    return assemble(atoms, ctx)


def leaf(it):
    small = False
    return Atom(it.tok, it.kind, it.x0, it.y0, it.x1, it.y1, it.base, it.size, small=small)


def parse_group(g, ctx, row_size):
    if len(g) == 1:
        it = g[0]
        if it.is_rule:
            if it.kind == "hrule":
                ctx.pen(0.8, "lone rule")
                return Atom("-", "bin", it.x0, it.y0, it.x1, it.y1, it.y0 - 0.25 * row_size, row_size)
            return Atom("|", "fence", it.x0, it.y0, it.x1, it.y1, it.y0, row_size)
        return leaf(it)
    x0, y0, x1, y1 = bbox_of(g)
    w = x1 - x0
    glyphs = [i for i in g if not i.is_rule]
    rules = [i for i in g if i.is_rule and i.kind == "hrule"]
    # radical: surd glyph + bar starting near its right edge
    surds = [i for i in glyphs if i.kind == "rad"]
    if surds:
        s = min(surds, key=lambda i: i.x0)
        bars = [r for r in rules if abs(r.x0 - s.x1) < 0.35 * max(s.size, 4) and r.y0 >= s.y0 + 0.4 * s.h]
        if bars:
            bar = max(bars, key=lambda r: r.w)
            inner = [i for i in g if i is not s and i is not bar and i.cx > bar.x0 and i.cx <= bar.x1 + 0.5 and i.cy < bar.y0]
            idx = [i for i in g if i is not s and i is not bar and i.cx < s.x1 and i.cy > s.cy and i not in inner]
            rest = [i for i in g if i is not s and i is not bar and i not in inner and i not in idx]
            body = parse_block(inner, ctx).tex if inner else ""
            tex = f"\\sqrt{{{body}}}" if not idx else f"\\sqrt[{parse_block(idx, ctx).tex}]{{{body}}}"
            a = Atom(tex, "rad", x0, y0, x1, y1, inner_base(inner, s), row_size)
            return combine_rest(a, rest, ctx, row_size)
        inner = [i for i in g if i is not s and i.x0 >= s.x0]
        ctx.pen(0.75, "radical without bar")
        body = parse_block(inner, ctx).tex if inner else ""
        return Atom(f"\\sqrt{{{body}}}", "rad", x0, y0, x1, y1, inner_base(inner, s), row_size)
    # fraction: widest rule with material above and below
    for bar in sorted(rules, key=lambda r: -r.w):
        if bar.w < 0.5 * w:
            break
        above = [i for i in g if i is not bar and i.cy > bar.y1 and i.cx >= bar.x0 - 1 and i.cx <= bar.x1 + 1]
        below = [i for i in g if i is not bar and i.cy < bar.y0 and i.cx >= bar.x0 - 1 and i.cx <= bar.x1 + 1]
        if above and below:
            rest = [i for i in g if i is not bar and i not in above and i not in below]
            num, den = parse_block(above, ctx), parse_block(below, ctx)
            a = Atom(f"\\frac{{{num.tex}}}{{{den.tex}}}", "frac", bar.x0, y0, bar.x1, y1, bar.y0 - 0.25 * row_size, row_size)
            return combine_rest(a, rest, ctx, row_size)
        if above and not below:
            # overline
            rest = [i for i in g if i is not bar and i not in above]
            if not rest:
                body = parse_block(above, ctx)
                return Atom(f"\\overline{{{body.tex}}}", "acc", x0, y0, x1, y1, body.base, body.size)
        if below and not above and bar.y0 > max(i.y1 for i in below) - 0.5:
            rest = [i for i in g if i is not bar and i not in below]
            if not rest:
                body = parse_block(below, ctx)
                return Atom(f"\\overline{{{body.tex}}}", "acc", x0, y0, x1, y1, body.base, body.size)
    # big operator with limits above / below
    ops = [i for i in glyphs if i.kind == "bigop"]
    if ops:
        op = max(ops, key=lambda i: i.h)
        above = [i for i in g if i is not op and i.y0 >= op.y1 - 0.15 * op.h]
        below = [i for i in g if i is not op and i.y1 <= op.y0 + 0.15 * op.h]
        rest = [i for i in g if i is not op and i not in above and i not in below]
        if above or below:
            tex = op.tok + (f"_{{{parse_block(below, ctx).tex}}}" if below else "") + \
                (f"^{{{parse_block(above, ctx).tex}}}" if above else "")
            a = Atom(tex, "limop", x0, y0, x1, y1, None, row_size)
            return combine_rest(a, rest, ctx, row_size)
    # word-operator limits (lim, max, min, sup, inf, argmin) : letters on a row with small material below
    # accents above a base
    accs = [i for i in glyphs if i.kind == "accent"]
    if accs:
        acc = max(accs, key=lambda i: i.y1)
        base = [i for i in g if i is not acc and i.cy < acc.cy]
        if base and acc.y0 >= max(i.y0 for i in base) + 0.3 * (max(i.y1 for i in base) - min(i.y0 for i in base)):
            rest = [i for i in g if i is not acc and i not in base]
            body = parse_block(base, ctx)
            cmd = acc.tok
            if cmd == "\\hat" and acc.w > 1.6 * max(1.0, acc.size * 0.5):
                cmd = "\\widehat"
            if cmd == "\\tilde" and acc.w > 1.6 * max(1.0, acc.size * 0.5):
                cmd = "\\widetilde"
            a = Atom(f"{cmd}{{{body.tex}}}", "acc", x0, y0, x1, y1, body.base, body.size)
            return combine_rest(a, rest, ctx, row_size)
    # vertical stack (matrix column, sub+sup pair, cases rows, word operators with limits, under/over-set)
    rows = y_rows(g, main_size(g), w, strict=False)
    if len(rows) == 2:
        top_g, bot_g = rows
        tsz = max((i.size for i in top_g if not i.is_rule), default=0)
        bsz = max((i.size for i in bot_g if not i.is_rule), default=0)
        if tsz >= 0.9 * row_size and bsz and bsz <= 0.85 * tsz:
            word = "".join(i.ch for i in sorted(top_g, key=lambda i: i.x0) if not i.is_rule)
            top = parse_row(top_g, ctx)
            bot = parse_block(bot_g, ctx)
            if word in OPNAMES:
                tex = top.tex + "_{" + bot.tex + "}"
            else:
                ctx.pen(0.9, "underset")
                tex = "\\underset{" + bot.tex + "}{" + top.tex + "}"
            return Atom(tex, "limop", x0, y0, x1, y1, None, row_size)
        if bsz >= 0.9 * row_size and tsz and tsz <= 0.85 * bsz:
            top = parse_block(top_g, ctx)
            bot = parse_row(bot_g, ctx)
            ctx.pen(0.9, "overset")
            return Atom("\\overset{" + top.tex + "}{" + bot.tex + "}", "limop", x0, y0, x1, y1, None, row_size)
    if len(rows) > 1:
        ratoms = [parse_row(r, ctx) for r in rows]
        rtex = [ra.tex for ra in ratoms]
        sm = max((i.size for i in glyphs), default=row_size)
        return Atom("\\begin{matrix} " + " \\\\ ".join(rtex) + " \\end{matrix}", "stack", x0, y0, x1, y1,
                    rows_base(rows), sm, rows=rtex, row_items=rows, small=sm <= 0.85 * row_size, row_atoms=ratoms)
    # overlapping glyphs (e.g. negated relations, kerning) -> left-to-right
    if any(i.tok == "\\not" for i in g):
        others = [i for i in g if i.tok != "\\not"]
        if len(others) == 1:
            o = others[0]
            neg = {"=": "\\neq", "\\in": "\\notin", "\\equiv": "\\not\\equiv", "\\subset": "\\not\\subset"}.get(o.tok, "\\not " + o.tok)
            return Atom(neg, "rel", x0, y0, x1, y1, o.base, o.size)
    if len(glyphs) == 2 and {glyphs[0].ch, glyphs[1].ch} <= {"=", "/"} and any(i.ch == "/" for i in glyphs):
        return Atom("\\neq", "rel", x0, y0, x1, y1, glyphs[0].base, glyphs[0].size)
    seq = sorted(g, key=lambda i: i.x0)
    key = tuple(i.tok for i in seq if not i.is_rule)
    if key in ARROWS and all(not i.is_rule for i in seq):
        return Atom(ARROWS[key], "rel", x0, y0, x1, y1, statistics.median(i.base for i in seq), max(i.size for i in seq))
    if len(seq) > 1:
        sub_atoms = [parse_group([i], ctx, row_size) for i in seq]
        a = assemble(sub_atoms, ctx)
        ctx.pen(0.92, "overlapping glyphs")
        return a
    return leaf(seq[0])


def inner_base(inner, s):
    gl = [i for i in inner if not i.is_rule]
    return statistics.median(i.base for i in gl) if gl else s.base


def combine_rest(a, rest, ctx, row_size):
    if not rest:
        return a
    atoms = [a] + [parse_group([i], ctx, row_size) for i in rest]
    ctx.pen(0.85, "leftover glyphs in structure")
    return assemble(sorted(atoms, key=lambda t: t.x0), ctx)


# ---------------------------------------------------------------- sequence assembly
def assemble(atoms, ctx):
    atoms = sorted(atoms, key=lambda a: a.x0)
    if not atoms:
        return Atom("", "empty", 0, 0, 0, 0, 0, 0)
    sized = [a for a in atoms if a.kind not in ("bigop", "limop", "rad", "frac", "stack", "open", "close", "fence") and a.size > 0 and a.base is not None]
    if not sized:
        sized = [a for a in atoms if a.size > 0 and a.base is not None] or atoms
    sizes = [round(a.size * 2) / 2 for a in sized]
    mx = max(sizes)
    msize = statistics.mode([s for s in sizes if s >= 0.8 * mx])
    bases = [a.base for a in sized if a.base is not None and abs(a.size - msize) <= 0.12 * msize]
    mbase = statistics.median(bases) if bases else statistics.median(a.base for a in sized if a.base is not None) if any(a.base is not None for a in sized) else 0

    def level(a):
        if a.kind in ("bigop", "limop", "open", "close", "fence") or a.base is None:
            return 0
        if a.kind == "stack":
            if a.small and a.rows and len(a.rows) == 2:
                return 2
            return 0
        small = a.size <= 0.86 * msize
        shift = a.base - mbase
        if a.kind == "prime":
            return 1
        if small and shift > 0.1 * msize:
            if shift < 0.18 * msize:
                ctx.pen(0.95, "marginal superscript")
            return 1
        if small and shift < -0.06 * msize:
            if shift > -0.12 * msize:
                ctx.pen(0.95, "marginal subscript")
            return -1
        return 0

    def is_small(a):
        return a.kind not in ("bigop", "limop", "open", "close", "fence", "frac", "stack") and a.size <= 0.86 * msize

    atoms = merge_columns(atoms, msize)
    out = []  # list of [tex, kind, atom]
    i = 0
    n = len(atoms)
    while i < n:
        a = atoms[i]
        lv = level(a)
        if lv == 0:
            out.append([a.tex, a.kind, a])
            i += 1
            continue
        # a cluster of script material after one base: split it into the superscript and subscript streams
        sups, subs, last = [], [], None
        j = i
        while j < n:
            b = atoms[j]
            lb = level(b)
            if lb == 0:
                if last is not None and is_small(b):
                    lb = last
                else:
                    break
            if lb == 2:
                ra = b.row_atoms or []
                if len(ra) == 2:
                    sups.append(ra[0])
                    subs.append(ra[1])
                last = -1
            elif lb == 1:
                sups.append(b)
                last = 1
            else:
                subs.append(b)
                last = -1
            j += 1
        script = ""
        if subs:
            script += "_{" + assemble(subs, ctx).tex + "}"
        if sups:
            if all(r.kind == "prime" for r in sups):
                script += "^{" + "".join("\\prime" for _ in sups) + "}"
            else:
                script += "^{" + assemble(sups, ctx).tex + "}"
        attach(out, script)
        i = j
    toks = merge_words(out)
    toks = fences(toks)
    tex = " ".join(t for t in toks if t)
    x0 = min(a.x0 for a in atoms)
    x1 = max(a.x1 for a in atoms)
    y0 = min(a.y0 for a in atoms)
    y1 = max(a.y1 for a in atoms)
    return Atom(tex, "seq", x0, y0, x1, y1, mbase, msize)


def merge_columns(atoms, msize):
    """Adjacent stacks with the same number of rows and aligned rows are columns of one matrix."""
    res = []
    for a in atoms:
        prev = res[-1] if res else None
        if prev is not None and a.kind == "stack" and prev.kind == "stack" and not a.small and not prev.small \
                and len(a.rows) == len(prev.rows) and a.row_items and prev.row_items and \
                all(abs(row_mid(p) - row_mid(q)) <= 0.6 * msize for p, q in zip(a.row_items, prev.row_items)):
            cols = (prev.cols if prev.cols else [prev.rows]) + [a.rows]
            rows = [" & ".join(c[k] for c in cols) for k in range(len(a.rows))]
            m = Atom("\\begin{matrix} " + " \\\\ ".join(rows) + " \\end{matrix}", "stack", prev.x0, min(prev.y0, a.y0),
                     a.x1, max(prev.y1, a.y1), prev.base, prev.size, rows=rows, row_items=prev.row_items)
            m.cols = cols
            res[-1] = m
        else:
            res.append(a)
    return res


def row_mid(items):
    return (min(i.y0 for i in items) + max(i.y1 for i in items)) / 2


def attach(out, script):
    if not out:
        out.append(["{}" + script, "ord", None])
        return
    tex = out[-1][0]
    if script.startswith("^") and re.search(r"\^\{[^{}]*\}$", tex):
        out.append(["{}" + script, "ord", None])
        return
    out[-1][0] = tex + script


def merge_words(out):
    """Turn upright letter runs that spell operator names into the bare word (normaliser treats \\sin as sin)."""
    return [o[0] for o in out]


def fences(toks):
    """Matrices between fences and cases: '\\{' followed by a stack without a closing fence -> cases."""
    res = list(toks)
    for k in range(len(res) - 1):
        if res[k] == "\\{" and res[k + 1].startswith("\\begin{matrix}") and not any(t.startswith("\\}") for t in res[k + 2:]):
            body = res[k + 1][len("\\begin{matrix}"):]
            body = body[: body.rfind("\\end{matrix}")]
            res[k] = ""
            res[k + 1] = "\\begin{cases}" + body + "\\end{cases}"
            break
    return res


# ---------------------------------------------------------------- repair + driver
def repair(tex):
    tex = re.sub(r"\s+", " ", tex).strip()
    for _ in range(3):
        tex = re.sub(r"[\^_]\{\s*\}", "", tex)
    depth = 0
    out = []
    for ch in tex:
        if ch == "{":
            depth += 1
        elif ch == "}":
            if depth == 0:
                continue
            depth -= 1
        out.append(ch)
    tex = "".join(out) + "}" * depth
    return tex


def family_of(glyphs):
    from collections import Counter
    c = Counter(font_family(g.font) for g in glyphs)
    return c.most_common(1)[0][0] if c else "none"


def rebuild(glyphs, shapes):
    ctx = Ctx()
    if not glyphs:
        return {"latex": "", "conf": 0.0, "family": "none", "notes": ["no glyphs"], "fonts": []}
    items = make_items(glyphs, shapes, ctx)
    gl = [i for i in items if not i.is_rule]
    if not gl:
        return {"latex": "", "conf": 0.0, "family": family_of(glyphs), "notes": ["no glyph items"], "fonts": []}
    try:
        atom = parse_block(items, ctx, top=True)
        tex = repair(atom.tex)
    except Exception as e:
        return {"latex": "", "conf": 0.0, "family": family_of(glyphs), "notes": [f"exception {type(e).__name__}: {e}"], "fonts": []}
    opens = len(re.findall(r"(?<!\\)[(\[]|\\\{|\\langle|\\lfloor|\\lceil", tex))
    closes = len(re.findall(r"(?<!\\)[)\]]|\\\}|\\rangle|\\rfloor|\\rceil", tex))
    if opens != closes:
        ctx.pen(0.8, f"unbalanced delimiters {opens}/{closes}")
    from collections import Counter
    fonts = [f for f, _ in Counter((g.font or "").split("+")[-1] for g in glyphs).most_common(4)]
    fam = family_of(glyphs)
    if fam not in ("CM/LM",):
        ctx.pen(0.9, f"font family {fam}")
    return {"latex": tex, "conf": round(ctx.conf, 4), "family": fam, "notes": ctx.notes, "fonts": fonts}

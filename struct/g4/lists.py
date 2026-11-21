import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import dl, pdf as P

BULLETS = set("•◦▪▫‣⁃●○■□–—-*·∙➢→►♦")
EXCLUDE = {"section_header", "title", "table", "picture", "page_header", "page_footer", "caption", "formula", "chart", "document_index"}
ROMAN = re.compile(r"^(?=[ivxlcdm]+$)m{0,3}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$", re.I)
MARK = re.compile(r"^(\(?)([0-9]{1,2}(?:\.[0-9]{1,2})*|[a-zA-Z]|[ivxlcdmIVXLCDM]{1,5})([\.\)])?$")
TOL = 4.0


def roman_val(s):
    v = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    s = s.lower()
    t = 0
    for i, ch in enumerate(s):
        x = v[ch]
        t += -x if i + 1 < len(s) and v[s[i + 1]] > x else x
    return t


def parse_marker(words):
    if not words:
        return None
    w0 = dl.norm(words[0]["text"])
    rest = words[1:]
    if len(w0) >= 2 and w0[0] in BULLETS and w0[1].isalnum():
        return dict(fam="bullet", style=w0[0], val=None, x=words[0]["box"][0], body_x=words[0]["box"][0] + 6, first_body=w0[1:], rest=rest)
    if w0 in BULLETS:
        if not rest:
            return None
        return dict(fam="bullet", style=w0, val=None, x=words[0]["box"][0], body_x=rest[0]["box"][0], rest=rest)
    m = MARK.match(w0)
    if not m or not rest:
        return None
    op, core, close = m.group(1), m.group(2), m.group(3) or ""
    if op and close != ")":
        return None
    if not op and not close:
        return None
    style = ("(" if op else "") + close
    nxt = dl.norm(rest[0]["text"])
    if core[0].isdigit():
        parts = core.split(".")
        if any(int(p) > 99 for p in parts):
            return None
        if len(parts) > 1 and close != "." and nxt[:1].islower():
            return None
        fam = "multi" if len(parts) > 1 else "dec"
        val = int(parts[-1])
    else:
        fam = "alpha_or_roman"
        val = core
    return dict(fam=fam, style=style, val=val, depth_hint=core.count(".") + 1 if core[0].isdigit() else None,
                x=words[0]["box"][0], body_x=rest[0]["box"][0], rest=rest)


def resolve(mk, prev):
    if mk["fam"] != "alpha_or_roman":
        return mk
    c = mk["val"]
    up = c.isupper()
    if len(c) == 1:
        av = ord(c.lower()) - 96
        if prev and prev["fam"].endswith("alpha") and prev["style"] == mk["style"] and prev["val"] + 1 == av:
            mk.update(fam=("u" if up else "l") + "alpha", val=av)
            return mk
        if ROMAN.match(c) and (c.lower() == "i" and not (prev and prev["fam"].endswith("alpha") and prev["val"] == 8)
                               or (prev and prev["fam"].endswith("roman") and prev["val"] + 1 == roman_val(c))):
            mk.update(fam=("u" if up else "l") + "roman", val=roman_val(c))
            return mk
        mk.update(fam=("u" if up else "l") + "alpha", val=av)
        return mk
    if ROMAN.match(c):
        mk.update(fam=("u" if up else "l") + "roman", val=roman_val(c))
        return mk
    return None


def page_lines(path, items):
    doc = P.open_pdf(path)
    regions = {}
    for k, it in enumerate(items):
        if it["page"] and it["bbox"]:
            regions.setdefault(it["page"], []).append((k, it))
    out = []
    for i in range(len(doc)):
        _, _, ws = P.page_words(doc[i], style=False)
        for L in P.lines(ws):
            cx, cy = (L["box"][0] + L["box"][2]) / 2, (L["box"][1] + L["box"][3]) / 2
            owner = None
            for k, it in regions.get(i + 1, []):
                b = it["bbox"]
                if b[0] - 3 <= L["box"][0] + 1 and L["box"][0] <= b[2] and b[1] - 3 <= cy <= b[3] + 3:
                    owner = (k, it)
                    break
            lab = owner[1]["label"] if owner else None
            inside = owner[1]["inside"] if owner else None
            if lab in EXCLUDE or inside:
                continue
            L["page"] = i
            L["order"] = (i, owner[0] if owner else 10 ** 6, L["box"][1])
            out.append(L)
    out.sort(key=lambda L: L["order"])
    return out


def detect(path, items):
    lines = page_lines(path, items)
    res = []
    stack = []
    cur = None
    prevL = None
    for L in lines:
        mk = parse_marker(L["words"])
        prev_sib = None
        if mk:
            x = mk["x"]
            while stack and x < stack[-1]["x"] - TOL:
                stack.pop()
            if stack and abs(x - stack[-1]["x"]) <= TOL:
                prev_sib = stack[-1]["mk"]
            mk = resolve(mk, prev_sib)
        if mk:
            x = mk["x"]
            if stack and abs(x - stack[-1]["x"]) <= TOL:
                parent = stack[-2]["item"] if len(stack) > 1 else -1
                stack.pop()
            elif stack and x > stack[-1]["x"] + TOL:
                parent = stack[-1]["item"]
            else:
                stack = []
                parent = -1
            body = " ".join(w["text"] for w in mk["rest"])
            if mk.get("first_body"):
                body = mk["first_body"] + " " + body
            res.append(dict(text=body.strip(), depth=len(stack) + 1, parent=parent, fam=mk["fam"], style=mk["style"], val=mk["val"],
                            page=L["page"], run=None))
            stack.append(dict(x=x, mk=mk, item=len(res) - 1))
            cur = dict(body_x=mk["body_x"], item=len(res) - 1)
        else:
            h = max(1.0, L["box"][3] - L["box"][1])
            cont = False
            if cur is not None and prevL is not None:
                same_page = L["page"] == prevL["page"]
                gap = L["box"][1] - prevL["box"][3] if same_page else 0
                if (L["box"][0] >= cur["body_x"] - TOL) and (not same_page or gap <= 1.2 * h):
                    cont = True
            if cont:
                res[cur["item"]]["text"] += " " + L["text"]
            else:
                stack = []
                cur = None
                if res:
                    res[-1]["closed"] = True
        prevL = L
    runs, run = [], []
    for k, it in enumerate(res):
        run.append(k)
        if it.get("closed") or k == len(res) - 1:
            runs.append(run)
            run = []
    drop = set()
    for run in runs:
        enum = [k for k in run if res[k]["fam"] != "bullet"]
        if len(run) == 1 and enum:
            v = res[run[0]]["val"]
            if v not in (1,) or res[run[0]]["fam"] in ("multi",):
                drop.add(run[0])
        sib = {}
        ok = tot = 0
        for k in enum:
            key = (res[k]["parent"], res[k]["fam"], res[k]["style"])
            if key in sib:
                tot += 1
                ok += isinstance(res[k]["val"], int) and isinstance(sib[key], int) and res[k]["val"] == sib[key] + 1
            sib[key] = res[k]["val"]
        if tot >= 2 and ok < 0.5 * tot:
            drop.update(enum)
    keep = [k for k in range(len(res)) if k not in drop]
    remap = {k: i for i, k in enumerate(keep)}
    out = []
    for k in keep:
        it = dict(res[k])
        p = it["parent"]
        while p >= 0 and p in drop:
            p = res[p]["parent"]
        it["parent"] = remap.get(p, -1)
        out.append(it)
    return out

import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pikepdf

from common import dl, pdf as P

ROMAN = re.compile(r"^(?=[ivxlcdm]+$)m{0,3}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$", re.I)
LABEL = re.compile(r"^(?:page\s+)?-?\s*([ivxlcdm]+|\d{1,4}|[A-Z]{1,2}-\d{1,3})\s*-?(?:\s+of\s+\d+)?$", re.I)


def roman_val(s):
    v = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    s = s.lower()
    t = 0
    for i, ch in enumerate(s):
        x = v[ch]
        t += -x if i + 1 < len(s) and v[s[i + 1]] > x else x
    return t


def to_roman(n, upper=False):
    vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    s = ""
    for v, r in vals:
        while n >= v:
            s += r
            n -= v
    return s.upper() if upper else s


def letters(n, upper):
    k = (n - 1) % 26
    s = chr((65 if upper else 97) + k) * ((n - 1) // 26 + 1)
    return s


def nums(tree, out):
    if "/Nums" in tree:
        a = tree.Nums
        for i in range(0, len(a) - 1, 2):
            out.append((int(a[i]), a[i + 1]))
    for k in tree.get("/Kids", []) or []:
        nums(k, out)


def page_labels(pk):
    if "/PageLabels" not in pk.Root:
        return None
    ranges = []
    try:
        nums(pk.Root.PageLabels, ranges)
    except Exception:
        return None
    ranges.sort(key=lambda x: x[0])
    n = len(pk.pages)
    out = [None] * n
    for j, (start, d) in enumerate(ranges):
        end = ranges[j + 1][0] if j + 1 < len(ranges) else n
        style = str(d.get("/S", "")) if "/S" in d else ""
        pre = str(d.get("/P", "")) if "/P" in d else ""
        st = int(d.get("/St", 1)) if "/St" in d else 1
        for p in range(start, min(end, n)):
            k = st + p - start
            body = {"/D": str(k), "/R": to_roman(k, True), "/r": to_roman(k), "/A": letters(k, True), "/a": letters(k, False)}.get(style, "")
            out[p] = pre + body
    return out


def printed_label(geo, ws):
    band = [w for w in ws if w["box"][1] > geo.h * 0.9 or w["box"][3] < geo.h * 0.08]
    lines = P.lines(sorted(band, key=lambda w: (round(w["box"][1] / 4), w["box"][0])))
    best = None
    for L in lines:
        t = dl.norm(L["text"]).strip()
        m = LABEL.match(t)
        if m:
            lab = m.group(1)
            if lab.isalpha() and not ROMAN.match(lab):
                continue
            score = (1 if L["box"][1] > geo.h * 0.9 else 0, -abs((L["box"][0] + L["box"][2]) / 2 - geo.w / 2))
            if best is None or score > best[0]:
                best = (score, lab)
    return best[1] if best else None


def succ(lab):
    if lab is None:
        return None
    if lab.isdigit():
        return str(int(lab) + 1)
    if ROMAN.match(lab):
        return to_roman(roman_val(lab) + 1, lab.isupper())
    m = re.match(r"^([A-Z]{1,2}-)(\d+)$", lab)
    if m:
        return m.group(1) + str(int(m.group(2)) + 1)
    return None


def fuse(pl, pr):
    n = len(pr)
    both = [i for i in range(n) if pr[i] and pl and pl[i]]
    agree = sum(1 for i in both if pl[i].lower() == pr[i].lower())
    mismatch = bool(pl) and len(both) >= 2 and agree < 0.8 * len(both)
    out = [None] * n
    if pl and not mismatch:
        return list(pl), False
    for i in range(n):
        out[i] = pr[i]
    for i in range(1, n):
        if out[i] is None:
            out[i] = succ(out[i - 1])
    for i in range(n - 2, -1, -1):
        if out[i] is None and out[i + 1] and out[i + 1].isdigit() and int(out[i + 1]) > 1:
            out[i] = str(int(out[i + 1]) - 1)
    for i in range(n):
        if out[i] is None:
            out[i] = (pl[i] if pl else None) or str(i + 1)
    return out, mismatch


def detect(path):
    doc = P.open_pdf(path)
    pk = pikepdf.open(path)
    n = len(doc)
    cand, imgs, reds, printed = {}, {}, [], []
    wm_annot = False
    for i in range(n):
        pg = doc[i]
        geo = P.Geo(pg)
        tp = pg.get_textpage()
        objs = P.objects(pg, tp, geo)
        _, _, ws = P.page_words(pg, style=False)
        printed.append(printed_label(geo, ws))
        for k, o in enumerate(objs):
            if o["type"] == P.TEXT:
                t = re.sub(r"\s+", " ", dl.norm(o.get("text") or "")).strip().upper()
                if len(t) < 3:
                    continue
                ang = abs(o.get("angle", 0.0)) % 180
                rotated = 5 < ang < 85 or 95 < ang < 175
                fill = o.get("fill") or (0, 0, 0, 255)
                alpha = fill[3]
                light = P.luma(fill) > 150
                big = (o.get("size") or 0) >= 20
                cx = (o["box"][0] + o["box"][2]) / 2 / geo.w
                cy = (o["box"][1] + o["box"][3]) / 2 / geo.h
                central = 0.2 < cx < 0.8 and 0.2 < cy < 0.8
                if central and ((rotated and big) or (alpha < 200 and big) or (big and light)):
                    cand.setdefault(t, set()).add(i)
            elif o["type"] == P.IMAGE:
                b = o["box"]
                area = (b[2] - b[0]) * (b[3] - b[1]) / (geo.w * geo.h)
                cx = (b[0] + b[2]) / 2 / geo.w
                cy = (b[1] + b[3]) / 2 / geo.h
                if area >= 0.08 and 0.25 < cx < 0.75 and 0.25 < cy < 0.75:
                    key = tuple(round(v / 6) for v in b)
                    imgs.setdefault(key, set()).add(i)
            elif o["type"] == P.PATH and o.get("fillmode", 0) > 0:
                f = o.get("fill") or (0, 0, 0, 255)
                b = o["box"]
                w, h = b[2] - b[0], b[3] - b[1]
                if P.luma(f) < 50 and f[3] > 200 and w >= 8 and 5 <= h <= 60 and w * h < 0.3 * geo.w * geo.h:
                    before = [q for q in objs[:k] if q["type"] == P.TEXT and (q.get("text") or "").strip() and P.cover(q["box"], b) >= 0.5]
                    after = [q for q in objs[k + 1:] if q["type"] == P.TEXT and (q.get("text") or "").strip() and P.cover(q["box"], b) >= 0.5]
                    if after:
                        continue
                    reds.append(dict(page=i, box=[round(v, 1) for v in b], type="unsafe_cover" if before else "applied",
                                     text=" ".join(q.get("text", "") for q in before)[:200]))
        for a in pk.pages[i].obj.get("/Annots", []) or []:
            st = str(a.get("/Subtype", ""))
            if st == "/Redact":
                r = [float(x) for x in a.Rect]
                reds.append(dict(page=i, box=geo.box(min(r[0], r[2]), min(r[1], r[3]), max(r[0], r[2]), max(r[1], r[3])), type="unapplied_annot"))
            elif st == "/Watermark":
                wm_annot = True
    need = max(2, math.ceil(0.5 * n)) if n > 1 else 1
    wm_text = [t for t, ps in cand.items() if len(ps) >= need]
    wm_img = [k for k, ps in imgs.items() if len(ps) >= need]
    kinds = (["text"] if wm_text else []) + (["annot"] if wm_annot else []) + (["image"] if wm_img else [])
    pl = page_labels(pk)
    fused, mismatch = fuse(pl, printed)
    return dict(watermark=bool(kinds), wm_kinds=kinds, wm_text=wm_text[:3], redactions=reds, pagelabels=pl, printed=printed,
                fused=fused, mismatch=mismatch, pages=n)

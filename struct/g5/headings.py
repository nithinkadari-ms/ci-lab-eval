import difflib
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import dl, pdf as P

NUM = re.compile(r"^\s*((?:\d+\.)*\d+)\.?\s+(?=\S)")
ROMAN_H = re.compile(r"^\s*([IVXLC]+)\.\s+\S")
ALPHA_H = re.compile(r"^\s*([A-Z])[\.\)]\s+\S")
CAPTION = re.compile(r"^\s*(fig(ure)?s?|table|tab|algorithm|listing|scheme|chart|exhibit|plate|box|supplementary (fig|table))\b\.?\s*[\dIVXA-Z]", re.I)
STRIP = re.compile(r"^\s*((\d+|[ivxlc]+|[a-z])(\.\d+)*[\.\)]?|\(?[a-z0-9]+\))\s+", re.I)
TOCLINE = re.compile(r"^(.*?\S)\s*(?:[\.·… ]{2,}|\s{2,}|\t)\s*(\d{1,4})\s*$")
TEXT_LABELS = ("text", "list_item", "section_header", "paragraph")
SECTION_WORDS = re.compile(r"^(abstract|summary|introduction|background|keywords?)")


def key(s):
    s = dl.norm(s)
    s = STRIP.sub("", s)
    return re.sub(r"[^a-z0-9]", "", s.lower())


def sim(a, b):
    ka, kb = key(a), key(b)
    if not ka or not kb:
        return 0.0
    if len(ka) >= 12 and len(kb) >= 12 and (ka.startswith(kb) or kb.startswith(ka)):
        return 0.95
    return difflib.SequenceMatcher(None, ka, kb, autojunk=False).ratio()


def outline(path):
    doc = P.open_pdf(path)
    out = []
    try:
        for it in doc.get_toc(max_depth=12):
            out.append(dict(title=it.title or "", level=it.level + 1, page=it.page_index))
    except Exception:
        pass
    return out


def styles(path, items):
    doc = P.open_pdf(path)
    bypage = {}
    for it in items:
        if it["page"] and it["bbox"]:
            bypage.setdefault(it["page"], []).append(it)
    for p, its in bypage.items():
        if p - 1 >= len(doc):
            continue
        pg = doc[p - 1]
        geo = P.Geo(pg)
        chs = [c for c in P.chars(pg, None, geo, style=True) if "box" in c and c["c"].strip()]
        for it in its:
            b = it["bbox"]
            sel = [c for c in chs if b[0] - 1 <= (c["box"][0] + c["box"][2]) / 2 <= b[2] + 1 and b[1] - 1 <= (c["box"][1] + c["box"][3]) / 2 <= b[3] + 1]
            if not sel:
                continue
            sizes = sorted(round(c.get("size", 0) * 2) / 2 for c in sel)
            it["size"] = sizes[len(sizes) // 2]
            it["bold"] = sum(1 for c in sel if c.get("weight", 400) >= 600 or "bold" in c.get("font", "").lower() or "black" in c.get("font", "").lower()) / len(sel)
            al = [c["c"] for c in sel if c["c"].isalpha()]
            it["caps"] = sum(1 for c in al if c.isupper()) / len(al) if al else 0.0
            it["italic"] = sum(1 for c in sel if (c.get("fflags", 0) & 0x40) or "italic" in c.get("font", "").lower() or "oblique" in c.get("font", "").lower()) / len(sel)
            it["ph"] = geo.h
            it["nchars"] = len(sel)


def toc_entries(path):
    doc = P.open_pdf(path)
    pages = {}
    for i in range(min(12, len(doc))):
        _, _, ws = P.page_words(doc[i], style=False)
        for L in P.lines(ws):
            m = TOCLINE.match(dl.norm(L["text"]))
            if m and len(m.group(1)) >= 3 and re.search(r"[A-Za-z]{3,}", m.group(1)):
                pages.setdefault(i, []).append(dict(title=m.group(1).strip(" ."), page=int(m.group(2)), x=L["box"][0]))
    out = []
    for p, es in sorted(pages.items()):
        if len(es) >= 5:
            out += es
    if not out:
        return []
    xs = sorted({round(e["x"] / 8) for e in out})
    for e in out:
        m = NUM.match(e["title"])
        e["level"] = m.group(1).count(".") + 1 if m else xs.index(round(e["x"] / 8)) + 1
    return out


def tier(it):
    return (it.get("size", 0.0), round(it.get("bold", 0.0)), 1 if it.get("caps", 0.0) >= 0.8 else 0, round(it.get("italic", 0.0)))


def repeated(items):
    cnt = {}
    for it in items:
        if it["page"]:
            k = re.sub(r"\d+", "", key(it["text"]))
            if len(k) >= 3:
                cnt.setdefault(k, set()).add(it["page"])
    return {k for k, ps in cnt.items() if len(ps) >= 3}


def repair(path, items, use_outline=True, reject=True, use_toc=True):
    styles(path, items)
    body = [it for it in items if it["label"] == "text" and it.get("size")]
    bsz = Counter(it["size"] for it in body for _ in range(max(1, it.get("nchars", 1) // 20)))
    body_size = bsz.most_common(1)[0][0] if bsz else 10.0
    rep = repeated(items) if reject else set()
    ol = outline(path) if use_outline else []
    cands = []
    for k, it in enumerate(items):
        if it["furniture"] or it["inside"] or not it["text"].strip():
            continue
        t = dl.norm(it["text"]).strip()
        nw = len(t.split())
        if it["label"] == "section_header":
            cands.append(k)
        elif it["label"] in ("text", "list_item") and nw <= 14 and not t.endswith((".", ",", ";", ":")):
            numbered = NUM.match(t) or ROMAN_H.match(t)
            styled = (it.get("size", 0) >= body_size + 1.0) or (it.get("bold", 0) >= 0.8 and nw <= 10)
            if numbered and styled:
                cands.append(k)
    level = {}
    src = {}
    if ol:
        for e in ol:
            best, bk = 0.0, None
            for k, it in enumerate(items):
                if it["label"] not in TEXT_LABELS or it["furniture"] or not it["page"] or len(it["text"].split()) > 20:
                    continue
                if abs((it["page"] - 1) - e["page"]) > 1:
                    continue
                s = sim(e["title"], it["text"])
                if s > best:
                    best, bk = s, k
            if bk is not None and best >= 0.85 and bk not in level:
                level[bk] = e["level"]
                src[bk] = "outline"
                if bk not in cands:
                    cands.append(bk)
    if not ol and use_toc:
        for e in toc_entries(path):
            best, bk = 0.0, None
            for k in cands:
                s = sim(e["title"], items[k]["text"])
                if s > best:
                    best, bk = s, k
            if bk is not None and best >= 0.85 and bk not in level:
                level[bk] = e["level"]
                src[bk] = "toc"
    front = None
    for it in items:
        if it["page"] == 1 and it["label"] == "text" and it["bbox"] and len(it["text"].split()) >= 30 and not it["furniture"]:
            front = it["bbox"][1] if front is None else min(front, it["bbox"][1])
    keep = []
    for k in sorted(set(cands)):
        it = items[k]
        t = dl.norm(it["text"]).strip()
        if reject and k not in level:
            if CAPTION.match(t) or TOCLINE.match(t):
                continue
            numbered = bool(NUM.match(t) or ROMAN_H.match(t))
            if not numbered and re.sub(r"\d+", "", key(t)) in rep:
                continue
            if not numbered and front is not None and it["page"] == 1 and it["bbox"] and it["bbox"][3] <= front and not SECTION_WORDS.match(key(t)):
                continue
            ph = it.get("ph") or 792.0
            if it["bbox"] and (it["bbox"][3] < 0.06 * ph or it["bbox"][1] > 0.94 * ph):
                continue
            if len(t.split()) > 20 or (t.endswith(".") and len(t.split()) > 8):
                continue
            if not re.search(r"[A-Za-z]{2,}", t):
                continue
        keep.append(k)
    for k in keep:
        if k in level:
            continue
        t = dl.norm(items[k]["text"]).strip()
        m = NUM.match(t)
        if m:
            level[k] = m.group(1).count(".") + 1
            src[k] = "numbering"
    tiers = {}
    for k in keep:
        it = items[k]
        tiers.setdefault(tier(it), []).append(k)
    order = sorted(tiers, key=lambda x: (-x[0], -x[1], -x[2], x[3]))
    tier_level = {}
    for tk in order:
        ev = [level[k] for k in tiers[tk] if k in level]
        if ev:
            tier_level[tk] = Counter(ev).most_common(1)[0][0]
    last = 0
    for tk in order:
        if tk in tier_level:
            last = tier_level[tk]
        else:
            tier_level[tk] = last + 1 if last else order.index(tk) + 1
            last = tier_level[tk]
    out = []
    for k in keep:
        it = items[k]
        lv = level.get(k, tier_level.get(tier(it), 1))
        out.append(dict(k=k, text=it["text"], level=max(1, lv), src=src.get(k, "style")))
    return out

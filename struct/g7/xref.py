import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pikepdf

from common import dl, pdf as P

REFS = re.compile(r"^\s*(\d+\.?\s*)?(references?|bibliography|literature cited|works cited|reference list)\s*$", re.I)
CAP = re.compile(r"^\s*(fig(?:ure)?s?\.?|table|tab\.)\s*(S?\d+)", re.I)
NUMS = r"S?\d+[A-Za-z]?(?:\s*[-–—]\s*S?\d+[A-Za-z]?)?"
FIG = re.compile(r"\b(Fig(?:ure)?s?\.?)\s*(%s(?:\s*(?:,|and|&)\s*%s)*)" % (NUMS, NUMS))
TAB = re.compile(r"\b(Tables?)\s*(%s(?:\s*(?:,|and|&)\s*%s)*)" % (NUMS, NUMS))
BR = re.compile(r"\[(\d{1,3}(?:\s*[-–—,;]\s*\d{1,3})*)\]")
PAR = re.compile(r"\((\d{1,3}(?:\s*[-–—,;]\s*\d{1,3})*)\)")
AY = re.compile(r"([A-Z][A-Za-zÀ-ɏ'\-]+)(?:\s+et\s+al\.?|\s+(?:and|&)\s+[A-Z][A-Za-zÀ-ɏ'\-]+)?,?\s+\(?((?:19|20)\d{2})[a-z]?\)?")
ENTRY_NUM = re.compile(r"^\s*\[?(\d{1,3})[\]\.\)]?\s+")
YEAR = re.compile(r"\b((?:19|20)\d{2})[a-z]?\b")


def expand(s, allow_s=True):
    out = []
    for part in re.split(r"\s*(?:,|;|and|&)\s*", s):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(S?)(\d+)[A-Za-z]?(?:\s*[-–—]\s*(S?)(\d+)[A-Za-z]?)?$", part)
        if not m:
            continue
        a = int(m.group(2))
        if m.group(4):
            b = int(m.group(4))
            if a < b <= a + 30:
                out += [m.group(1) + str(k) for k in range(a, b + 1)]
                continue
        out.append(m.group(1) + str(a))
    return [x.upper() for x in out]


def sections(items):
    start = None
    for k, it in enumerate(items):
        if it["label"] in ("section_header", "title", "text") and REFS.match(dl.norm(it["text"])) and not it["furniture"]:
            start = k
    if start is None:
        return items, [], None
    end = len(items)
    for k in range(start + 1, len(items)):
        it = items[k]
        if it["label"] == "section_header" and not REFS.match(it["text"]) and not ENTRY_NUM.match(it["text"]):
            end = k
            break
    return items[:start], [it for it in items[start + 1:end] if it["text"].strip() and not it["furniture"]], start


def ref_entries(ritems):
    ents = []
    for it in ritems:
        t = dl.norm(it["text"])
        marks = list(re.finditer(r"(?:^|\s)\[(\d{1,3})\]\s", t))
        if len(marks) >= 2:
            for j, m in enumerate(marks):
                seg = t[m.start():marks[j + 1].start() if j + 1 < len(marks) else len(t)]
                ents.append(dict(text=seg.strip(), item=it))
        else:
            ents.append(dict(text=t, item=it))
    numbered = sum(1 for e in ents if ENTRY_NUM.match(e["text"])) >= 0.7 * max(1, len(ents))
    for pos, e in enumerate(ents, 1):
        m = ENTRY_NUM.match(e["text"])
        e["label"] = m.group(1) if m else None
        e["pos"] = pos
        body = ENTRY_NUM.sub("", e["text"])
        sm = re.match(r"\s*([A-Z][A-Za-zÀ-ɏ'\-]+)", body)
        e["surname"] = sm.group(1).lower() if sm else None
        y = YEAR.search(body)
        e["year"] = y.group(1) if y else None
    return ents, numbered


def superscripts(path, body_items, page_filter=None):
    doc = P.open_pdf(path)
    out = []
    bypage = {}
    for it in body_items:
        if it["page"] and it["bbox"] and it["label"] in ("text", "list_item"):
            bypage.setdefault(it["page"], []).append(it["bbox"])
    for p, boxes in bypage.items():
        if p - 1 >= len(doc):
            continue
        pg = doc[p - 1]
        geo = P.Geo(pg)
        chs = [c for c in P.chars(pg, None, geo, style=True) if "box" in c]
        ws = P.words(chs)
        for L in P.lines(ws):
            cx, cy = (L["box"][0] + L["box"][2]) / 2, (L["box"][1] + L["box"][3]) / 2
            if not any(b[0] - 2 <= cx <= b[2] + 2 and b[1] - 2 <= cy <= b[3] + 2 for b in boxes):
                continue
            lc = [c for w in L["words"] for c in w["chars"]]
            sizes = sorted(c.get("size", 0) for c in lc if c["c"].isalpha())
            if len(sizes) < 5:
                continue
            med = sizes[len(sizes) // 2]
            bases = sorted(c["box"][3] for c in lc if c["c"].isalpha() and c["c"].islower() and c["c"] not in "gjpqy")
            base = bases[len(bases) // 2] if bases else L["box"][3]
            run = ""
            for c in lc + [dict(c=" ", size=med, box=[0, 0, 0, base])]:
                sup = c.get("size", med) < 0.8 * med and c["box"][3] < base - 0.15 * med and (c["c"].isdigit() or c["c"] in ",–-—")
                if sup:
                    run += c["c"]
                elif run:
                    if any(ch.isdigit() for ch in run):
                        out.append(run.strip(",-–—"))
                    run = ""
    return out


def dest_of(pdf, d, names, pidx):
    if isinstance(d, (pikepdf.String, str, pikepdf.Name)):
        d = names.get(str(d).lstrip("/"))
        if d is None:
            return None
    if isinstance(d, pikepdf.Dictionary) and "/D" in d:
        d = d.D
    if isinstance(d, pikepdf.Array) and len(d) >= 1:
        pg = d[0]
        try:
            pi = pidx.get(pg.objgen)
        except Exception:
            pi = int(pg) if isinstance(pg, int) else None
        top = None
        if len(d) >= 4 and str(d[1]) == "/XYZ":
            try:
                top = float(d[3])
            except Exception:
                top = None
        elif len(d) >= 3 and str(d[1]) in ("/FitH", "/FitBH"):
            try:
                top = float(d[2])
            except Exception:
                top = None
        return (pi, top) if pi is not None else None
    return None


def name_tree(node, out):
    if "/Names" in node:
        a = node.Names
        for i in range(0, len(a) - 1, 2):
            out[str(a[i])] = a[i + 1]
    for k in node.get("/Kids", []) or []:
        name_tree(k, out)


def explicit_links(path, items, ents, numbered, caps):
    pdf = pikepdf.open(path)
    pidx = {p.obj.objgen: i for i, p in enumerate(pdf.pages)}
    names = {}
    try:
        if "/Names" in pdf.Root and "/Dests" in pdf.Root.Names:
            name_tree(pdf.Root.Names.Dests, names)
        if "/Dests" in pdf.Root:
            for k, v in pdf.Root.Dests.items():
                names[str(k).lstrip("/")] = v
    except Exception:
        pass
    doc = P.open_pdf(path)
    ent_by_item = {}
    for e in ents:
        ent_by_item.setdefault(id(e["item"]), []).append(e)
    links = Counter()
    n = 0
    for i, pg in enumerate(pdf.pages):
        for a in pg.obj.get("/Annots", []) or []:
            try:
                if str(a.get("/Subtype")) != "/Link":
                    continue
                d = a.get("/Dest")
                if d is None and "/A" in a and str(a.A.get("/S")) == "/GoTo":
                    d = a.A.get("/D")
                if d is None:
                    continue
                tgt = dest_of(pdf, d, names, pidx)
                if not tgt:
                    continue
                n += 1
                tp, top = tgt
                dpg = doc[tp]
                geo = P.Geo(dpg)
                ty = geo.t - top if top is not None else 0.0
                best, bd = None, 1e9
                for it in items:
                    if it["page"] != tp + 1 or not it["bbox"]:
                        continue
                    dd = it["bbox"][1] - ty
                    if -6 <= dd < bd and dd <= 60:
                        best, bd = it, dd
                if best is None:
                    continue
                m = CAP.match(dl.norm(best["text"]))
                if best["label"] == "caption" or (m and best["label"] == "text"):
                    if m:
                        links[("table" if m.group(1).lower().startswith("tab") else "fig", m.group(2).upper())] += 1
                    continue
                es = ent_by_item.get(id(best))
                if es:
                    e = es[0]
                    links[("bibr", e["label"] if numbered and e["label"] else str(e["pos"]))] += 1
            except Exception:
                continue
    return links, n


def link(path, doc):
    items = dl.items(doc)
    body, ritems, _ = sections(items)
    ents, numbered = ref_entries(ritems)
    caps = {"fig": set(), "table": set()}
    for it in items:
        m = CAP.match(dl.norm(it["text"]))
        if m and (it["label"] == "caption" or it["label"] == "text"):
            caps["table" if m.group(1).lower().startswith("tab") else "fig"].add(m.group(2).upper())
    labels = {e["label"] for e in ents if e["label"]}
    btxt = [it for it in body if it["label"] in ("text", "list_item", "footnote") and not it["furniture"] and it["inside"] is None]
    pat = Counter()
    unresolved = Counter()
    has_br = False
    for it in btxt:
        t = dl.norm(it["text"])
        for rx, ty in ((FIG, "fig"), (TAB, "table")):
            for m in rx.finditer(t):
                for k in expand(m.group(2)):
                    if k in caps[ty]:
                        pat[(ty, k)] += 1
                    else:
                        unresolved[ty] += 1
        if numbered:
            for m in BR.finditer(t):
                has_br = True
                for k in expand(m.group(1)):
                    if k in labels:
                        pat[("bibr", k)] += 1
                    else:
                        unresolved["bibr"] += 1
    if numbered and not has_br:
        for it in btxt:
            for m in PAR.finditer(dl.norm(it["text"])):
                ks = expand(m.group(1))
                if ks and all(k in labels for k in ks):
                    for k in ks:
                        pat[("bibr", k)] += 1
        sups = superscripts(path, btxt)
        for s in sups:
            for k in expand(s):
                if k in labels:
                    pat[("bibr", k)] += 1
                else:
                    unresolved["bibr"] += 1
    if not numbered and ents:
        idx = {}
        for e in ents:
            if e["surname"] and e["year"]:
                idx.setdefault((e["surname"], e["year"]), []).append(e["pos"])
        for it in btxt:
            for m in AY.finditer(dl.norm(it["text"])):
                c = idx.get((m.group(1).lower(), m.group(2)))
                if c and len(c) == 1:
                    pat[("bibr", str(c[0]))] += 1
                elif c:
                    unresolved["bibr_ambiguous"] += 1
    exp, nlinks = explicit_links(path, items, ents, numbered, caps)
    comb = Counter()
    for k in set(pat) | set(exp):
        comb[k] = max(pat[k], exp[k])
    internal = sum(1 for it in items if it.get("hyperlink") and not str(it["hyperlink"]).startswith(("http", "mailto", "ftp")))
    return dict(pattern=pat, explicit=exp, combined=comb, unresolved=unresolved, n_link_annots=nlinks, refs=len(ents), numbered=numbered,
                caps={k: sorted(v) for k, v in caps.items()}, dl_internal_links=internal)

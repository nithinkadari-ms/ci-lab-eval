import re

from lxml import etree

EXCL = {"fig", "table-wrap", "caption", "fn", "table", "fn-group", "ref-list", "supplementary-material"}
DASH = {"-", "–", "—", "‐", "‑", "‒", "−"}


def root_of(data):
    parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True, recover=True, load_dtd=False)
    r = etree.fromstring(data, parser)
    for el in r.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return r


def text(el):
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip() if el is not None else ""


def label_key(s):
    m = re.search(r"(S?\d+)", s or "", re.I)
    return m.group(1).upper() if m else None


def targets(r):
    figs = {f.get("id"): label_key(text(f.find("label"))) for f in r.iter("fig") if f.get("id")}
    tabs = {t.get("id"): label_key(text(t.find("label"))) for t in r.iter("table-wrap") if t.get("id")}
    refs = {}
    for pos, ref in enumerate(r.iter("ref"), 1):
        lab = text(ref.find("label")).strip(".[]() ")
        refs[ref.get("id")] = (pos, lab if lab.isdigit() else None)
    fns = {f.get("id"): text(f.find("label")) or None for f in r.iter("fn") if f.get("id")}
    return figs, tabs, refs, fns


def xrefs(r):
    figs, tabs, refs, fns = targets(r)
    numeric = sum(1 for v in refs.values() if v[1]) >= 0.8 * max(1, len(refs))
    body = r.find(".//body")
    out = []
    if body is None:
        return out, dict(figs=figs, tabs=tabs, refs=len(refs), numeric=numeric)
    prev = None
    for x in body.iter("xref"):
        anc = {a.tag for a in x.iterancestors()}
        if anc & EXCL:
            prev = None
            continue
        t = x.get("ref-type")
        rids = (x.get("rid") or "").split()
        keys = []
        for rid in rids:
            if t == "fig" and figs.get(rid):
                keys.append(("fig", figs[rid]))
            elif t == "table" and tabs.get(rid):
                keys.append(("table", tabs[rid]))
            elif t == "bibr" and rid in refs:
                pos, lab = refs[rid]
                keys.append(("bibr", lab if numeric and lab else str(pos)))
            elif t in ("fn", "table-fn") and rid in fns:
                keys.append(("fn", fns[rid] or rid))
        if t == "bibr" and prev is not None and prev[0] is x.getprevious() and keys and prev[1]:
            between = (prev[0].tail or "").strip()
            if between in DASH:
                try:
                    a, b = int(prev[1][-1][1]), int(keys[0][1])
                    for k in range(a + 1, b):
                        out.append(dict(type="bibr", key=str(k), text="(range)"))
                except ValueError:
                    pass
        for tt, kk in keys:
            out.append(dict(type=tt, key=kk, text=text(x)[:40]))
        prev = (x, keys) if t == "bibr" else None
    return out, dict(figs=figs, tabs=tabs, refs=len(refs), numeric=numeric)


def sections(r):
    out = []

    def walk(el, depth, parent):
        for sec in el.findall("sec"):
            tt = text(sec.find("title"))
            lb = text(sec.find("label"))
            if tt:
                out.append(dict(text=(lb + " " + tt).strip(), depth=depth, parent=parent))
                walk(sec, depth + 1, len(out) - 1)
            else:
                walk(sec, depth, parent)

    body = r.find(".//body")
    if body is not None:
        walk(body, 1, -1)
    back = r.find(".//back")
    if back is not None:
        for el in back:
            tag = el.tag if isinstance(el.tag, str) else ""
            if tag == "ack":
                out.append(dict(text=text(el.find("title")) or "Acknowledgments", depth=1, parent=-1))
            elif tag == "ref-list":
                out.append(dict(text=text(el.find("title")) or "References", depth=1, parent=-1))
            elif tag in ("app-group", "sec", "notes"):
                if tag == "sec" or text(el.find("title")):
                    t = text(el.find("title"))
                    if t:
                        out.append(dict(text=t, depth=1, parent=-1))
                        walk(el, 2, len(out) - 1)
                    else:
                        walk(el, 1, -1)
                for app in el.findall("app"):
                    t = text(app.find("title"))
                    if t:
                        out.append(dict(text=t, depth=1, parent=-1))
                        walk(app, 2, len(out) - 1)
    return out

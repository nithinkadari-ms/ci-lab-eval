import json
import os
import re
import time
import unicodedata

os.environ.setdefault("DOCLING_RS_CACHE_DIR", os.path.expanduser("~/dlrs"))

import docling_rs as d
from docling_rs import models as dm

dm.ensure_env(os.environ["DOCLING_RS_CACHE_DIR"])

_CONV = {}

BASE = dict(do_table_structure=False)


def converter(**kw):
    o = dict(BASE)
    o.update(kw)
    k = tuple(sorted((a, repr(b)) for a, b in o.items()))
    if k not in _CONV:
        _CONV[k] = d.DocumentConverter(**o)
    return _CONV[k]


def convert(path, page_range=None, **kw):
    c = converter(**kw)
    t0, p0 = time.perf_counter(), time.process_time()
    native = c._convert_native(str(path), page_range, None)
    doc = json.loads(native.document_json)
    return doc, time.perf_counter() - t0, time.process_time() - p0


def _res(doc, ref):
    _, kind, idx = ref.split("/")
    return doc[kind][int(idx)]


def _topleft(b, ph):
    if str(b.get("coord_origin", "BOTTOMLEFT")).upper().endswith("BOTTOMLEFT"):
        t, bb = ph - b["t"], ph - b["b"]
        return [b["l"], min(t, bb), b["r"], max(t, bb)]
    return [b["l"], min(b["t"], b["b"]), b["r"], max(b["t"], b["b"])]


def items(doc):
    out = []
    pages = doc.get("pages", {})

    def ph(p):
        pg = pages.get(str(p)) or {}
        return (pg.get("size") or {}).get("height", 792.0)

    def walk(node, depth, furn, inside):
        for ch in node.get("children", []) or []:
            ref = ch.get("$ref")
            if not ref:
                continue
            it = _res(doc, ref)
            lab = it.get("label")
            pr = it.get("prov") or []
            kind = ref.split("/")[1]
            if kind != "groups":
                rec = dict(ref=ref, kind=kind, label=lab, text=it.get("text") or "", level=it.get("level"),
                           marker=it.get("marker"), enumerated=it.get("enumerated"), list_depth=depth,
                           furniture=furn or it.get("content_layer") == "furniture", inside=inside,
                           hyperlink=it.get("hyperlink"), page=None, bbox=None)
                if pr:
                    rec["page"] = pr[0]["page_no"]
                    rec["bbox"] = _topleft(pr[0]["bbox"], ph(pr[0]["page_no"]))
                if lab == "list_item" and it.get("marker"):
                    rec["text"] = (it["marker"] + " " + rec["text"]).strip()
                if kind == "tables":
                    cells = ((it.get("data") or {}).get("table_cells")) or []
                    rec["text"] = " ".join(c.get("text") or "" for c in cells)
                out.append(rec)
            nd = depth + (1 if kind == "groups" and lab == "list" else 0)
            walk(it, nd, furn, inside or (lab if lab in ("picture", "table", "chart") else None))

    walk(doc.get("body", {}), 0, False, None)
    walk(doc.get("furniture", {}), 0, True, None)
    return out


def all_text(doc):
    parts = [t.get("text") or "" for t in doc.get("texts", [])]
    for tb in doc.get("tables", []):
        for c in ((tb.get("data") or {}).get("table_cells")) or []:
            parts.append(c.get("text") or "")
    return "\n".join(parts)


_FOLD = {"‘": "'", "’": "'", "‚": "'", "‛": "'", "“": '"', "”": '"', "„": '"',
         "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-", " ": " ",
         "…": "..."}


def norm(s):
    s = unicodedata.normalize("NFKC", s or "")
    return "".join(_FOLD.get(c, c) for c in s)


_EDGE = re.compile(r"^[\W_]+|[\W_]+$")


def tokens(s):
    out = []
    for w in norm(s).split():
        w = _EDGE.sub("", w)
        if w:
            out.append(w)
    return out

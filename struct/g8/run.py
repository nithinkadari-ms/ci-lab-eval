import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import cfg, dl, ocr
from g8 import metrics
from g8.router import Router, lexicon

DOCS = os.path.join(cfg.DATA, "g8", "docs")
ARMS = {
    "dl_default": dict(),
    "dl_rbtl": dict(replace_broken_text_layer=True),
    "dl_fullocr": dict(force_full_page_ocr=True),
    "dl_textonly": dict(text_layer_only=True),
}


def page_texts(doc, n):
    out = [[] for _ in range(n)]
    for it in dl.items(doc):
        p = it.get("page")
        if p and 1 <= p <= n and it["text"]:
            out[p - 1].append(it["text"])
    return ["\n".join(x) for x in out]


def scan_page(path, i):
    doc, _, _ = dl.convert(path, force_full_page_ocr=True, page_range=(i + 1, i + 1))
    return "\n".join(it["text"] for it in dl.items(doc) if it["text"])


def main():
    man = cfg.load(os.path.join(cfg.DATA, "g8", "docs.json"))
    mine = cfg.shard(man)
    sh = os.environ.get("SHARD", "0")
    out = os.path.join(cfg.RES, "g8", "metrics-%s.jsonl" % sh)
    raw = os.path.join(cfg.RES, "g8", "raw-%s.jsonl" % sh)
    rec = ocr.Rec(threads=4)
    lex = lexicon()
    routers = {"R1": Router(rec, lex, crit_all=False), "R2": Router(rec, lex, crit_all=True)}
    for m in mine:
        g = cfg.load(os.path.join(DOCS, m["id"], "gold.json"))
        n = len(g["pages"])
        for v in m["variants"]:
            path = os.path.join(DOCS, m["id"], v + ".pdf")
            r = dict(doc=m["id"], source=m["source"], variant=v, arms={}, routers={})
            for name, kw in ARMS.items():
                try:
                    doc, wall, cpu = dl.convert(path, **kw)
                    r["arms"][name] = dict(pages=page_texts(doc, n), wall=wall, cpu=cpu)
                except Exception as e:
                    r["arms"][name] = dict(error=repr(e)[:300])
            for name, rt in routers.items():
                try:
                    l0 = rec.lines
                    res = rt.run(path, docling_scan=scan_page)
                    res["rec_lines"] = rec.lines - l0
                    r["routers"][name] = res
                except Exception:
                    r["routers"][name] = dict(error=traceback.format_exc()[-600:])
            cfg.jsonl_append(raw, r)
            try:
                cfg.jsonl_append(out, metrics.score(g, r))
            except Exception:
                cfg.jsonl_append(out, dict(doc=m["id"], variant=v, error=traceback.format_exc()[-800:]))
            cfg.log(m["id"], v, {k: round(a.get("cpu", -1), 1) for k, a in r["arms"].items()},
                    {k: (round(a.get("cpu", -1), 1), a.get("distrust")) for k, a in r["routers"].items()})


if __name__ == "__main__":
    main()

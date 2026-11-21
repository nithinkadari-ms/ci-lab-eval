import os
import sys
import time
import traceback
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import cfg, dl
from g7 import jats, xref

TYPES = ("fig", "table", "bibr", "fn")


def score(gold, pred):
    out = {}
    for t in TYPES:
        g = Counter({k: v for k, v in gold.items() if k[0] == t})
        p = Counter({k: v for k, v in pred.items() if k[0] == t})
        out[t] = dict(tp=sum((g & p).values()), np=sum(p.values()), ng=sum(g.values()))
    return out


def main():
    man = cfg.load(os.path.join(cfg.DATA, "pmc", "pmc.json"))
    mine = cfg.shard(man)
    out = os.path.join(cfg.RES, "g7", "metrics-%s.jsonl" % os.environ.get("SHARD", "0"))
    for m in mine:
        r = dict(id=m["id"], numeric=m["numeric"])
        try:
            root = jats.root_of(open(os.path.join(cfg.DATA, m["xml"]), "rb").read())
            gx, info = jats.xrefs(root)
            gold = Counter((x["type"], x["key"]) for x in gx)
            doc, wall, cpu = dl.convert(os.path.join(cfg.DATA, m["pdf"]))
            t0 = time.process_time()
            res = xref.link(os.path.join(cfg.DATA, m["pdf"]), doc)
            r["cpu"] = dict(dl=cpu, link=time.process_time() - t0, pages=len(doc.get("pages", {})))
            r["arms"] = {a: score(gold, res[a]) for a in ("pattern", "explicit", "combined")}
            r["arms"]["dl"] = score(gold, Counter())
            r["info"] = dict(refs_found=res["refs"], refs_gold=info["refs"], numbered=res["numbered"], gold_numeric=info["numeric"],
                             link_annots=res["n_link_annots"], unresolved=dict(res["unresolved"]), dl_internal_links=res["dl_internal_links"],
                             caps=res["caps"], gold_figs=sorted({v for v in info["figs"].values() if v}), gold_tabs=sorted({v for v in info["tabs"].values() if v}))
            fn = []
            for (t, k), v in gold.items():
                if res["combined"][(t, k)] < v and len(fn) < 6:
                    fn.append([t, k, v, res["combined"][(t, k)]])
            fp = [[t, k, v, gold[(t, k)]] for (t, k), v in res["combined"].items() if v > gold[(t, k)]][:6]
            r["examples"] = dict(missed=fn, extra=fp)
        except Exception:
            r["error"] = traceback.format_exc()[-800:]
        cfg.jsonl_append(out, r)
        cfg.log(m["id"], {a: {t: (v["tp"], v["np"], v["ng"]) for t, v in x.items()} for a, x in r.get("arms", {}).items() if a == "combined"})


if __name__ == "__main__":
    main()

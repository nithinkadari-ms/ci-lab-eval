import copy
import os
import sys
import tempfile
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pikepdf

from common import cfg, dl
from g5 import headings as HD
from g5 import metrics as M
from g7 import jats


def mask(src, dst):
    pdf = pikepdf.open(src)
    for k in ("/Outlines", "/PageMode"):
        if k in pdf.Root:
            del pdf.Root[k]
    pdf.save(dst)


def dl_heads(doc):
    return [dict(text=it["text"], level=it["level"] or 1) for it in dl.items(doc)
            if it["label"] == "section_header" and not it["furniture"] and not it["inside"] and it["text"].strip()]


def docs():
    out = []
    a = os.path.join(cfg.DATA, "g5", "comphrdoc.json")
    if os.path.exists(a):
        for d in cfg.load(a):
            out.append(dict(id=d["id"], set="comphrdoc", pdf=os.path.join(cfg.DATA, d["pdf"]), gold=d["gold"]))
    b = os.path.join(cfg.DATA, "pmc", "pmc.json")
    if os.path.exists(b):
        for d in cfg.load(b):
            out.append(dict(id=d["id"], set="pmc_jats", pdf=os.path.join(cfg.DATA, d["pdf"]), xml=os.path.join(cfg.DATA, d["xml"])))
    return out


def main():
    alld = docs()
    mine = cfg.shard(alld)
    out = os.path.join(cfg.RES, "g5", "metrics-%s.jsonl" % os.environ.get("SHARD", "0"))
    cfg.log("g5 docs", len(alld), "mine", len(mine))
    for d in mine:
        r = dict(id=d["id"], set=d["set"], arms={}, cpu={}, sizes={})
        try:
            if d["set"] == "pmc_jats":
                gold = jats.sections(jats.root_of(open(d["xml"], "rb").read()))
            else:
                gold = d["gold"]
            ol = HD.outline(d["pdf"])
            r["outline_n"] = len(ol)
            golds = {"main": gold}
            if len(ol) >= 4 and max(e["level"] for e in ol) >= 2:
                golds["outline"] = M.outline_gold(ol)
            with tempfile.TemporaryDirectory() as td:
                mp = os.path.join(td, "masked.pdf")
                mask(d["pdf"], mp)
                flat, _, c1 = dl.convert(d["pdf"])
                hh, _, c2 = dl.convert(d["pdf"], heading_hierarchy=True)
                hhm, _, c3 = dl.convert(mp, heading_hierarchy=True)
                r["cpu"].update(dl_flat=c1, dl_hh=c2, dl_hh_mask=c3)
                items = dl.items(flat)
                rep = HD.repeated(items)
                preds = {"dl_flat": dl_heads(flat), "dl_hh": dl_heads(hh), "dl_hh_mask": dl_heads(hhm)}
                for name, kw, path in (("ours_outline", dict(use_outline=True), d["pdf"]), ("ours_mask", dict(use_outline=False), mp),
                                       ("ours_mask_norej", dict(use_outline=False, reject=False), mp)):
                    t0 = time.process_time()
                    preds[name] = HD.repair(path, copy.deepcopy(items), **kw)
                    r["cpu"][name] = time.process_time() - t0
            for gname, g in golds.items():
                arms = list(preds) if gname == "main" else ["dl_flat", "dl_hh_mask", "ours_mask", "ours_mask_norej"]
                for a in arms:
                    r["arms"]["%s|%s" % (gname, a)] = M.score(g, preds[a], rep, ignore=d["set"] == "pmc_jats")
            r["pages"] = len(flat.get("pages", {}))
            r["examples"] = dict(gold=[x["text"] for x in gold][:12], dl_hh_mask=[(p["text"][:60], p["level"]) for p in preds["dl_hh_mask"]][:12],
                                 ours_mask=[(p["text"][:60], p["level"], p["src"]) for p in preds["ours_mask"]][:12])
        except Exception:
            r["error"] = traceback.format_exc()[-800:]
        cfg.jsonl_append(out, r)
        cfg.log(d["id"], {k: (v["tp"], v["np"], v["ng"]) for k, v in r["arms"].items() if k.startswith("main")}, "ERR" if "error" in r else "")


if __name__ == "__main__":
    main()

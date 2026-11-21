import os
import sys
import tempfile
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import cfg, dl, net, ocr
from g9 import vis

DOCHUSH = "674c23d56326664718cbf8f596bc5d6340ae0c8a"
DH_FILES = ["clean-text", "cover-rect-content", "cover-square-annot", "cover-square-annot-noap", "unapplied-redact-annot",
            "white-text", "render-mode-3", "offpage-text", "metadata-leak", "attachment", "bookmarks", "hidden-layer",
            "form-field", "javascript", "incremental-update", "pattern-pii", "image-only-redacted", "many-pages"]


def jobs():
    out = []
    fx = cfg.load(os.path.join(cfg.DATA, "g9", "fixtures.json"))
    for d in fx:
        out.append(dict(set="fixture", id=d["id"], path=os.path.join(cfg.DATA, "g9", "fixtures", d["id"] + ".pdf"), gold=d))
    cp = os.path.join(cfg.DATA, "g9", "cracked.json")
    if os.path.exists(cp):
        for m in cfg.load(cp)["items"]:
            out.append(dict(set="cracked", id=m["pdf_id"], path=os.path.join(cfg.DATA, "g9", "cracked", m["local"]), gold=m))
    dh = os.path.join(cfg.DATA, "g9", "dochush")
    os.makedirs(dh, exist_ok=True)
    for f in DH_FILES:
        p = os.path.join(dh, f + ".pdf")
        net.download("https://raw.githubusercontent.com/dochush/pdf-redaction-checker/%s/fixtures/%s.pdf" % (DOCHUSH, f), p, min_bytes=100)
        if os.path.exists(p):
            out.append(dict(set="dochush", id=f, path=p, gold=dict(name=f)))
    return out


def main():
    allj = jobs()
    mine = cfg.shard(allj)
    sh = os.environ.get("SHARD", "0")
    out = os.path.join(cfg.RES, "g9", "raw-%s.jsonl" % sh)
    rec = ocr.Rec(threads=4)
    cfg.log("g9 jobs", len(allj), "mine", len(mine))
    for j in mine:
        r = dict(set=j["set"], id=j["id"], gold=j["gold"])
        with tempfile.TemporaryDirectory() as td:
            try:
                r["vis"] = vis.check(j["path"], td, rec)
            except Exception:
                r["vis_error"] = traceback.format_exc()[-600:]
        try:
            doc, wall, cpu = dl.convert(j["path"])
            r["dl"] = dict(text=dl.all_text(doc)[:60000], wall=wall, cpu=cpu, pages=len(doc.get("pages", {})))
        except Exception as e:
            r["dl_error"] = repr(e)[:300]
        cfg.jsonl_append(out, r)
        cfg.log(j["set"], j["id"], "hidden spans", sum(1 for s in r.get("vis", {}).get("spans", []) if s["hidden"]),
                "err" if "vis_error" in r or "dl_error" in r else "")


if __name__ == "__main__":
    main()

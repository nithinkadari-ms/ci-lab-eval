import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import cfg, dl, net
from g12.detect import detect


def main():
    fx = cfg.load(os.path.join(cfg.DATA, "g12", "fixtures.json"))
    mine = cfg.shard(fx)
    out = os.path.join(cfg.RES, "g12", "raw-%s.jsonl" % os.environ.get("SHARD", "0"))
    dh = os.path.join(cfg.DATA, "g9", "dochush")
    extra = []
    for f in ("unapplied-redact-annot", "cover-rect-content", "clean-text", "image-only-redacted"):
        p = os.path.join(dh, f + ".pdf")
        os.makedirs(dh, exist_ok=True)
        net.download("https://raw.githubusercontent.com/dochush/pdf-redaction-checker/674c23d56326664718cbf8f596bc5d6340ae0c8a/fixtures/%s.pdf" % f, p, min_bytes=100)
        if os.path.exists(p) and os.environ.get("SHARD", "0") == "0":
            extra.append(dict(id="dochush:" + f, path=p, gold=None))
    for g in [dict(id=d["id"], path=os.path.join(cfg.DATA, "g12", "fixtures", d["id"] + ".pdf"), gold=d) for d in mine] + extra:
        r = dict(id=g["id"], gold=g["gold"])
        try:
            t0 = time.process_time()
            r["det"] = detect(g["path"])
            r["det_cpu"] = time.process_time() - t0
        except Exception:
            r["det_error"] = traceback.format_exc()[-600:]
        try:
            doc, wall, cpu = dl.convert(g["path"])
            its = dl.items(doc)
            r["dl"] = dict(body=" ".join(i["text"] for i in its if not i["furniture"]), furn=" ".join(i["text"] for i in its if i["furniture"]),
                           pages=sorted(int(k) for k in doc.get("pages", {})), cpu=cpu)
        except Exception as e:
            r["dl_error"] = repr(e)[:300]
        cfg.jsonl_append(out, r)
        cfg.log(g["id"], r.get("det", {}).get("wm_kinds"), len(r.get("det", {}).get("redactions", [])), r.get("det", {}).get("mismatch"))


if __name__ == "__main__":
    main()

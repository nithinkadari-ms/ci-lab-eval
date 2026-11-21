import io
import json
import os
import sys
import zipfile
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import cfg, net

ZIP_URL = "https://media.githubusercontent.com/media/microsoft/CompHRDoc/main/CompHRDoc.zip"
OUT = os.path.join(cfg.DATA, "g5")


def main():
    os.makedirs(os.path.join(OUT, "pdf"), exist_ok=True)
    zp = os.path.join(OUT, "CompHRDoc.zip")
    if not net.download(ZIP_URL, zp, min_bytes=10_000_000):
        raise SystemExit("CompHRDoc.zip download failed")
    gold = {}
    classes = Counter()
    with zipfile.ZipFile(zp) as z:
        names = z.namelist()
        cfg.log("zip entries", len(names), [n for n in names if n.lower().endswith("readme.md")])
        for n in names:
            if "test_eval_toc/" in n and n.endswith(".json"):
                did = os.path.basename(n)[:-5]
                d = json.loads(z.read(n).decode("utf-8"))
                gold[did] = d
                classes.update(x.get("class") for x in d)
        for n in names:
            if n.lower().endswith("hrdh_msra_pod_test/readme.md"):
                cfg.log(z.read(n).decode("utf-8", "replace")[:3000])
    os.remove(zp)
    cfg.log("test_eval_toc docs", len(gold), classes.most_common())
    ids = sorted(gold)[:cfg.n(220, 3)]
    man = []
    for did in ids:
        dest = os.path.join(OUT, "pdf", did + ".pdf")
        if net.download("https://export.arxiv.org/pdf/" + did, dest, delay=3.5) and net.is_pdf(dest):
            heads = []
            for x in gold[did]:
                heads.append(dict(text=x.get("text", ""), parent=x.get("parent_id", -1), page=x.get("page"), cls=x.get("class")))
            man.append(dict(id="chrd_" + did, set="comphrdoc", pdf=os.path.join("g5", "pdf", did + ".pdf"), gold=heads, arxiv=did))
        elif os.path.exists(dest):
            os.remove(dest)
    cfg.dump(man, os.path.join(OUT, "comphrdoc.json"))
    cfg.log("g5 comphrdoc docs", len(man))


if __name__ == "__main__":
    main()

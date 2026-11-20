"""Build CDM input pairs {id, gt, pred} for one system on the fixed 3,000-case subset."""
import glob, json, os, sys


def join_lines(parts):
    r"""Recognised line pieces -> one aligned block: \begin{aligned} p1 \ p2 \end{aligned}."""
    bs = chr(92)
    return bs + "begin{aligned} " + (" " + bs + bs + " ").join(parts) + " " + bs + "end{aligned}"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
system, shard, nsh, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
sub = json.load(open(os.path.join(ROOT, "manifests", "cdm_subset.json")))
gt = {}
for mf in ("arxiv", "unimer"):
    for it in json.load(open(os.path.join(ROOT, "manifests", mf + ".json"), encoding="utf-8")):
        gt[it["id"]] = it["gt"]


def rows(pattern):
    d = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "results", pattern))):
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                d.setdefault(r["id"], r)
    return d


if system in ("logic", "pdfmath", "rustypaper", "kakemono", "gopdfkit"):
    src = rows(f"t1/{system}.jsonl")
    pred = {i: (r.get("latex") or "") for i, r in src.items() if r.get("status") != "error" or r.get("latex")}
    pred.update({i: "" for i, r in src.items() if i not in pred})
elif system.startswith("t2_"):
    model = "p2t15_" + system.split("_p2t15_")[1].rsplit("_", 1)[0]
    dec = rows(f"t2/dec_{model}.s*.jsonl")
    if system.endswith("_1024"):
        pred = {i: r["pred1024"] for i, r in dec.items()}
    else:
        sp = rows(f"t2/split_{model}.s*.jsonl")
        pred = {i: (join_lines(sp[i]["pieces"]) if i in sp and sp[i].get("pieces") else r["pred1024"]) for i, r in dec.items()}
else:
    pred = {i: r.get("pred", "") for i, r in rows(f"acc/{system}.cdm_items.s*.jsonl").items()}
ids = [i for i in sub if i in pred]
ids = [i for k, i in enumerate(ids) if k % nsh == shard]
with open(out, "w", encoding="utf-8") as f:
    for i in ids:
        f.write(json.dumps({"id": i, "gt": gt[i], "pred": pred[i] or ""}, ensure_ascii=False) + "\n")
print(system, "pairs", len(ids))

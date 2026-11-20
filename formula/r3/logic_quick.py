"""Quick look at the logic rebuild alone: exact % by family and difficulty, plus mismatches."""
import json, os, sys, random
from collections import defaultdict
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from texnorm import normalize
from taxonomy import difficulty
items = {it["id"]: it for it in json.load(open(os.path.join(ROOT, "manifests", "arxiv.json"), encoding="utf-8"))}
res = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")]
agg = defaultdict(lambda: [0, 0])
bad = []
for r in res:
    it = items[r["id"]]
    ok = bool(r.get("latex")) and normalize(r["latex"]) == normalize(it["gt"])
    for k in ("ALL", "fam:" + str(r.get("family")), "diff:" + difficulty(it["gt"]), "conf>=0.9" if (r.get("conf") or 0) >= 0.9 else "conf<0.9"):
        agg[k][0] += ok
        agg[k][1] += 1
    if not ok and not it.get("lowres"):
        bad.append((r, it))
for k, (a, n) in sorted(agg.items()):
    print(f"{k:28s} {a:5d}/{n:5d} = {100 * a / n:.1f}%")
random.Random(int(os.environ.get("SEED", "1"))).shuffle(bad)
for r, it in bad[:int(os.environ.get("NBAD", "40"))]:
    print("-" * 80)
    print(r["id"], "conf", r.get("conf"), r.get("family"), r.get("fonts"), r.get("notes", [])[:4])
    print("GT :", normalize(it["gt"])[:220])
    print("OUT:", normalize(r.get("latex") or "")[:220])

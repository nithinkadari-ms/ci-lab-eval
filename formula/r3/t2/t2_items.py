"""Test 2 item set: all UniMER CPE + arXiv items tagged complex or long."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from taxonomy import difficulty, tags
out = []
for it in json.load(open(os.path.join(ROOT, "manifests", "unimer.json"), encoding="utf-8")):
    if it["set"] == "unimer_cpe":
        out.append(it)
for it in json.load(open(os.path.join(ROOT, "manifests", "arxiv.json"), encoding="utf-8")):
    if difficulty(it["gt"]) == "complex" or "long (>100 tokens)" in tags(it):
        out.append(it)
json.dump(out, open(os.path.join(ROOT, "manifests", "t2.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("t2 items", len(out))

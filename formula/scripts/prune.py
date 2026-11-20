import json, os, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
keep = set()
for mf in ["own12.json", "unimer.json", "unimer_hwe.json", "arxiv.json"]:
    for it in json.load(open(os.path.join(ROOT, "manifests", mf), encoding="utf-8")):
        keep.add(os.path.normpath(os.path.join(ROOT, it["image"])))
base = os.path.join(ROOT, "data", "unimer", "x")
n = 0
for dp, _, fs in os.walk(base):
    for f in fs:
        p = os.path.normpath(os.path.join(dp, f))
        if p not in keep:
            os.remove(p)
            n += 1
papers = {it["paper"] for it in json.load(open(os.path.join(ROOT, "manifests", "arxiv.json"), encoding="utf-8"))}
ad = os.path.join(ROOT, "data", "arxiv")
for d in os.listdir(ad) if os.path.isdir(ad) else []:
    p = os.path.join(ad, d)
    if not os.path.isdir(p):
        continue
    shutil.rmtree(os.path.join(p, "src"), ignore_errors=True)
    if d not in papers:
        shutil.rmtree(p, ignore_errors=True)
print("removed", n, "kept", len(keep))

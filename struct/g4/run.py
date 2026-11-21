import difflib
import os
import re
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import cfg, dl
from g4 import lists as LS

LEAD = re.compile(r"^\s*(\(?([0-9]{1,2}(\.[0-9]{1,2})*|[a-zA-Z]|[ivxlcdmIVXLCDM]{1,5})[\.\)]|[•◦▪–\-\*·])\s+")


def key(s):
    s = LEAD.sub("", dl.norm(s))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def sim(a, b):
    a, b = key(a)[:80], key(b)[:80]
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    if n >= 25 and a[:n] == b[:n]:
        return 1.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def dl_items(doc):
    out, stack = [], []
    run_open = False
    for it in dl.items(doc):
        if it["label"] == "list_item" and not it["furniture"]:
            d = max(1, it["list_depth"])
            if not run_open:
                stack = []
            while stack and stack[-1][1] >= d:
                stack.pop()
            out.append(dict(text=it["text"], depth=d, parent=stack[-1][0] if stack else -1))
            stack.append((len(out) - 1, d))
            run_open = True
        elif it["text"].strip() and not it["furniture"]:
            run_open = False
    return out


def score(gold, pred):
    gl = [k for k, g in enumerate(gold) if g["kind"] == "list"]
    gidx = {k: i for i, k in enumerate(gl)}
    neg = [k for k, g in enumerate(gold) if g["kind"] != "list"]
    match = [None] * len(pred)
    used = set()
    for pj, p in enumerate(pred):
        best, bk = 0.8, None
        for k in gl:
            if k in used:
                continue
            s = sim(gold[k]["text"], p["text"])
            if s > best:
                best, bk = s, k
        if bk is not None:
            used.add(bk)
            match[pj] = bk
    tp = sum(m is not None for m in match)
    depth_ok = edge = complete = wrapped = 0
    fam = {}
    for pj, k in enumerate(match):
        if k is None:
            continue
        g = gold[k]
        dok = pred[pj]["depth"] == g["ilvl"] + 1
        depth_ok += dok
        pp = pred[pj]["parent"]
        gp = g["parent"]
        eok = (pp < 0 and gp < 0) or (pp >= 0 and match[pp] is not None and match[pp] == gp)
        edge += eok
        if g.get("wrapped"):
            wrapped += 1
            complete += abs(len(key(pred[pj]["text"])) - len(key(g["text"]))) <= 0.1 * len(key(g["text"]))
        f = fam.setdefault(g["family"], [0, 0, 0])
        f[1] += dok
        f[2] += eok
    for k in gl:
        fam.setdefault(gold[k]["family"], [0, 0, 0])[0] += 1
    negf = 0
    for pj, p in enumerate(pred):
        if match[pj] is None and any(sim(gold[k]["text"], p["text"]) >= 0.8 for k in neg):
            negf += 1
    bydepth = {}
    for pj, k in enumerate(match):
        if k is not None:
            d = gold[k]["ilvl"] + 1
            x = bydepth.setdefault(str(d), [0, 0])
            x[0] += 1
            x[1] += pred[pj]["depth"] == d
    return dict(tp=tp, np=len(pred), ng=len(gl), depth_ok=depth_ok, edge=edge, wrapped=wrapped, complete=complete,
                neg=len(neg), negf=negf, fam=fam, bydepth=bydepth)


def main():
    man = cfg.load(os.path.join(cfg.DATA, "g4", "lists.json"))
    mine = cfg.shard(man)
    out = os.path.join(cfg.RES, "g4", "metrics-%s.jsonl" % os.environ.get("SHARD", "0"))
    for m in mine:
        r = dict(id=m["id"])
        path = os.path.join(cfg.DATA, "g4", "pdf", m["id"] + ".pdf")
        try:
            doc, wall, cpu = dl.convert(path)
            items = dl.items(doc)
            t0 = time.process_time()
            ours = LS.detect(path, items)
            r["cpu"] = dict(dl=cpu, ours=time.process_time() - t0, pages=len(doc.get("pages", {})))
            base = dl_items(doc)
            r["arms"] = dict(dl=score(m["gold"], base), ours=score(m["gold"], ours))
            r["examples"] = dict(dl=[(x["text"][:50], x["depth"]) for x in base[:8]], ours=[(x["text"][:50], x["depth"], x["fam"]) for x in ours[:8]],
                                 gold=[(g["text"][:50], g["ilvl"] + 1) for g in m["gold"] if g["kind"] == "list"][:8])
        except Exception:
            r["error"] = traceback.format_exc()[-800:]
        cfg.jsonl_append(out, r)
        cfg.log(m["id"], {k: (v["tp"], v["np"], v["ng"], v["edge"]) for k, v in r.get("arms", {}).items()})


if __name__ == "__main__":
    main()

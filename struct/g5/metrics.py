import re

from g5.headings import CAPTION, key, sim

IGNORE = re.compile(r"^(abstract|keywords?|key words|summary|graphical abstract|highlights|author summary|significance)$")


def parents(levels):
    out, stack = [], []
    for lv in levels:
        while stack and stack[-1][1] >= lv:
            stack.pop()
        out.append(stack[-1][0] if stack else -1)
        stack.append((len(out) - 1, lv))
    return out


def depths(par):
    d = []
    for i, p in enumerate(par):
        d.append(d[p] + 1 if 0 <= p < i else 1)
    return d


def score(gold, pred, rep_keys=frozenset(), ignore=False, thr=0.8):
    gpar = [g["parent"] for g in gold]
    gdep = depths(gpar) if gold else []
    if ignore:
        pred = [p for p in pred if not IGNORE.match(re.sub(r"[^a-z ]", "", p["text"].lower()).strip())]
    lv = [p["level"] for p in pred]
    if lv:
        m0 = min(lv)
        lv = [x - m0 + 1 for x in lv]
    ppar = parents(lv)
    match = [None] * len(pred)
    used = set()
    for gi, g in enumerate(gold):
        best, bj = thr, None
        for pj, p in enumerate(pred):
            if pj in used:
                continue
            s = sim(g["text"], p["text"])
            if s > best or (s == best and bj is not None and abs(pj - gi) < abs(bj - gi)):
                best, bj = s, pj
        if bj is not None:
            used.add(bj)
            match[bj] = gi
    tp = sum(1 for m in match if m is not None)
    lvl_ok = edge = 0
    for pj, gi in enumerate(match):
        if gi is None:
            continue
        lvl_ok += lv[pj] == gdep[gi]
        pp = ppar[pj]
        gp = gpar[gi]
        if (pp < 0 and gp < 0) or (pp >= 0 and match[pp] is not None and match[pp] == gp):
            edge += 1
    fcap = frep = foth = 0
    for pj, p in enumerate(pred):
        if match[pj] is None:
            t = p["text"]
            if CAPTION.match(t):
                fcap += 1
            elif re.sub(r"\d+", "", key(t)) in rep_keys:
                frep += 1
            else:
                foth += 1
    return dict(tp=tp, np=len(pred), ng=len(gold), lvl_ok=lvl_ok, edge=edge, f_cap=fcap, f_rep=frep, f_oth=foth)


def outline_gold(ol):
    lv = [e["level"] for e in ol]
    par = parents(lv)
    return [dict(text=e["title"], parent=par[i]) for i, e in enumerate(ol)]

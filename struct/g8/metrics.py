import re
from collections import Counter

from common import dl

CRIT = re.compile(r"\d.*\d")


def crit(tokens):
    return Counter(t for t in tokens if CRIT.search(t))


def msum(c):
    return sum(c.values())


def inter(a, b):
    return msum(a & b)


def crit_scores(G, N, O):
    gbad = G - N
    rec = 0
    for v, k in gbad.items():
        rec += min(k, max(0, O[v] - (G[v] - k)))
    return dict(g=msum(G), correct=inter(G, O), out=msum(O), wrong=msum(O - G), bad=msum(gbad),
                bad_wrong=msum(N - G), recovered=rec)


def tok_scores(gt, ot):
    a, b = Counter(gt), Counter(ot)
    return dict(tg=msum(a), to=msum(b), tov=inter(a, b))


def grid(words, cell=12.0):
    g = {}
    for k, w in enumerate(words):
        cx, cy = (w[4] + w[6]) / 2, (w[5] + w[7]) / 2
        g.setdefault((int(cx // cell), int(cy // cell)), []).append(k)
    return g


def match(gw, rw, cell=12.0):
    g = grid(rw, cell)
    used = set()
    out = []
    for w in gw:
        l, t, r, b = w[1], w[2], w[3], w[4]
        cx, cy = (l + r) / 2, (t + b) / 2
        best, bk = 0.0, None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for k in g.get((int(cx // cell) + dx, int(cy // cell) + dy), []):
                    if k in used:
                        continue
                    x = rw[k]
                    ix = max(0.0, min(r, x[6]) - max(l, x[4]))
                    iy = max(0.0, min(b, x[7]) - max(t, x[5]))
                    i = ix * iy
                    u = (r - l) * (b - t) + (x[6] - x[4]) * (x[7] - x[5]) - i
                    s = i / u if u > 0 else 0.0
                    if s > best:
                        best, bk = s, k
        if bk is not None and best >= 0.4:
            used.add(bk)
            out.append(bk)
        else:
            out.append(None)
    return out


def word_scores(gw, rw):
    keys = ["n", "native_ok", "kept", "broken", "fixed", "flag_bad", "flag_ok", "unmatched",
            "c_n", "c_bad", "c_fixed", "c_caught", "c_broken", "c_native_ok", "c_flag_ok"]
    s = dict.fromkeys(keys, 0)
    for w, k in zip(gw, match(gw, rw)):
        s["n"] += 1
        c = bool(CRIT.search(w[0]))
        s["c_n"] += c
        if k is None:
            s["unmatched"] += 1
            if c:
                s["c_bad"] += 1
            continue
        g = dl.norm(w[0])
        nat, out, flag = dl.norm(rw[k][0]), dl.norm(rw[k][1]), rw[k][3]
        nok, ook = nat == g, out == g
        if nok:
            s["native_ok"] += 1
            s["kept"] += out == nat
            s["broken"] += not ook
            s["flag_ok"] += flag
            if c:
                s["c_native_ok"] += 1
                s["c_broken"] += not ook
                s["c_flag_ok"] += flag
        else:
            s["fixed"] += ook
            s["flag_bad"] += flag and not ook
            if c:
                s["c_bad"] += 1
                s["c_fixed"] += ook
                s["c_caught"] += ook or bool(flag)
    return s


def score(gold, rec):
    out = dict(doc=rec["doc"], source=rec["source"], variant=rec["variant"], arms={}, routers={})
    gp = gold["pages"]
    gtok = [dl.tokens(" ".join(w[0] for w in p["words"])) for p in gp]
    G = [crit(t) for t in gtok]
    nat = None
    r1 = rec["routers"].get("R1", {})
    if "pages" in r1:
        nat = [crit(dl.tokens(" ".join(w[0] for w in p["words"]))) for p in r1["pages"]]
    if nat is None:
        return out
    scanned = set(gold["variants"].get("M", {}).get("scanned", [])) if rec["variant"] == "M" else set()
    for name, a in rec["arms"].items():
        if "pages" not in a:
            out["arms"][name] = dict(error=a.get("error"))
            continue
        pages = []
        for i, txt in enumerate(a["pages"][:len(gp)]):
            ot = dl.tokens(txt)
            pages.append(dict(scan=i in scanned, **crit_scores(G[i], nat[i], crit(ot)), **tok_scores(gtok[i], ot)))
        out["arms"][name] = dict(pages=pages, cpu=a["cpu"], wall=a["wall"], n=len(gp))
    for name, r in rec["routers"].items():
        if "pages" not in r:
            out["routers"][name] = dict(error=r.get("error"))
            continue
        pages = []
        for i, p in enumerate(r["pages"][:len(gp)]):
            if p.get("scan_text") is not None:
                ot = dl.tokens(p["scan_text"])
                ws = None
            else:
                ot = dl.tokens(" ".join(w[1] for w in p["words"]))
                ws = word_scores(gp[i]["words"], p["words"])
            pages.append(dict(scan=i in scanned, mode=p["mode"], ocr_lines=p["ocr_lines"], ocr_area=p["ocr_area"],
                              text_area=p["text_area"], words=ws, **crit_scores(G[i], nat[i], crit(ot)), **tok_scores(gtok[i], ot)))
        out["routers"][name] = dict(pages=pages, cpu=r["cpu"], wall=r["wall"], n=len(gp), distrust=r.get("distrust"),
                                    fonts=r.get("fonts"), rec_lines=r.get("rec_lines"))
    ex = []
    r2 = rec["routers"].get("R2", {})
    if "pages" in r2:
        for i, p in enumerate(r2["pages"][:len(gp)]):
            if p.get("scan_text") is not None:
                continue
            for w, k in zip(gp[i]["words"], match(gp[i]["words"], p["words"])):
                if k is not None and CRIT.search(w[0]) and dl.norm(p["words"][k][0]) != dl.norm(w[0]) and len(ex) < 6:
                    ex.append(dict(page=i, gold=w[0], native=p["words"][k][0], out=p["words"][k][1], flag=p["words"][k][3]))
    out["examples"] = ex
    return out

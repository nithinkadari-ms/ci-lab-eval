import difflib
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import dl, ocr, pdf as P

SCALE = 3.0
CRIT = re.compile(r"\d.*\d")
ALPHA = re.compile(r"^[A-Za-z]{3,}$")


def lexicon():
    import symspellpy
    fp = os.path.join(os.path.dirname(symspellpy.__file__), "frequency_dictionary_en_82_765.txt")
    with open(fp, encoding="utf-8") as f:
        return {ln.split()[0] for ln in f if ln.strip()}


def anomalous(t):
    for c in t:
        o = ord(c)
        if 0xE000 <= o <= 0xF8FF or o == 0xFFFD or (o < 32) or 0x7F <= o < 0xA0:
            return True
    scripts = set()
    for c in t:
        if c.isalpha():
            o = ord(c)
            scripts.add("L" if o < 0x250 else "G" if 0x370 <= o < 0x400 else "C" if 0x400 <= o < 0x530 else "O")
    return len(scripts) > 1 and "L" in scripts


def align(words, ocr_text):
    nat = [dl.norm(w["text"]) for w in words]
    A = "".join(nat)
    owner = []
    for k, s in enumerate(nat):
        owner += [k] * len(s)
    B = dl.norm(ocr_text).replace(" ", "")
    piece = [None] * len(A)
    one = [False] * len(A)
    sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                piece[i1 + k] = B[j1 + k]
                one[i1 + k] = True
        elif tag == "delete":
            for k in range(i1, i2):
                piece[k] = ""
        elif tag == "replace":
            if owner[i1] == owner[i2 - 1]:
                piece[i1] = B[j1:j2]
                for k in range(i1 + 1, i2):
                    piece[k] = ""
        elif tag == "insert":
            if 0 < i1 < len(A) and owner[i1 - 1] == owner[i1] and piece[i1 - 1] is not None:
                piece[i1 - 1] = piece[i1 - 1] + B[j1:j2]
    out, pairs = [], []
    pos = 0
    for k, s in enumerate(nat):
        seg = piece[pos:pos + len(s)]
        out.append(None if any(p is None for p in seg) else "".join(seg))
        for q in range(pos, pos + len(s)):
            if one[q] and A[q] != piece[q]:
                pairs.append((k, A[q], piece[q]))
        pos += len(s)
    return out, pairs


def loose(s):
    return re.sub(r"\W", "", dl.norm(s).lower())


def bare(w):
    return dl.norm(w["text"]).strip(".,;:()[]\"'")


class Router:
    def __init__(self, rec, lex, crit_all=False, k_digit=4, k_alpha=2, k_more=12, tau_layer=0.08, seed=0):
        self.rec, self.lex = rec, lex
        self.crit_all, self.k_digit, self.k_alpha, self.k_more = crit_all, k_digit, k_alpha, k_more
        self.tau_layer, self.seed = tau_layer, seed

    def crop(self, im, box, page):
        return ocr.crop(im, SCALE, (0, 0), box)

    def is_word(self, w):
        t = bare(w)
        return bool(ALPHA.match(t)) and t.islower()

    def nonword(self, w):
        return self.is_word(w) and bare(w) not in self.lex

    def nonword_rate(self, line):
        toks = [w for w in line["words"] if self.is_word(w)]
        if len(toks) < 4:
            return 0.0
        return sum(1 for w in toks if bare(w) not in self.lex) / len(toks)

    def suspicious(self, w):
        return w["err"] or anomalous(w["text"]) or self.nonword(w)

    def run(self, path, docling_scan=None):
        t0, c0 = time.perf_counter(), time.process_time()
        doc = P.open_pdf(path)
        rng = random.Random("%s:%s" % (self.seed, os.path.basename(os.path.dirname(path))))
        pages = []
        for i in range(len(doc)):
            pg = doc[i]
            geo, chs, ws = P.page_words(pg, style=True)
            objs = P.objects(pg, geo=geo, with_text=False)
            area = geo.w * geo.h
            img = sum(max(0.0, min(o["box"][2], geo.w) - max(o["box"][0], 0)) * max(0.0, min(o["box"][3], geo.h) - max(o["box"][1], 0))
                      for o in objs if o["type"] == P.IMAGE)
            img_cov = min(1.0, img / area) if area else 0.0
            inv = sum(1 for w in ws if w["rm"] in (3, 7))
            if len(ws) < 5 and img_cov > 0.3:
                mode = "scan"
            elif ws and inv > 0.6 * len(ws) and img_cov > 0.3:
                mode = "layer"
            else:
                mode = "digital"
            ls = P.lines(ws)
            for L in ls:
                for w in L["words"]:
                    w.update(out=w["text"], src="native", flag=False)
            pages.append(dict(i=i, geo=geo, words=ws, lines=ls, mode=mode, img_cov=img_cov, im=None, read=set(),
                              text_area=sum((L["box"][2] - L["box"][0]) * (L["box"][3] - L["box"][1]) for L in ls)))

        def image(p):
            if p["im"] is None:
                p["im"] = P.render(doc[p["i"]], SCALE, annots=True)
            return p["im"]

        def read(p, ls):
            todo = [L for L in ls if "res" not in L]
            if todo:
                im = image(p)
                res = self.rec([self.crop(im, L["box"], p["i"]) for L in todo])
                for L, r in zip(todo, res):
                    L["res"] = r
                    p["read"].add(id(L))

        def apply(L, sel=None, replace=True):
            txt, cf = L["res"]
            al, pairs = align(L["words"], txt)
            for w, o in zip(L["words"], al):
                if sel is not None and not sel(w):
                    continue
                if o is None:
                    w["flag"] = True
                elif o != dl.norm(w["text"]):
                    if replace:
                        w["out"], w["src"] = o, "ocr"
                    else:
                        w["flag"] = True
            return pairs

        for p in pages:
            if p["mode"] != "layer":
                continue
            ls = p["lines"]
            crit = [L for L in ls if any(CRIT.search(w["text"]) for w in L["words"])]
            cid = set(id(L) for L in crit)
            rest = [L for L in ls if id(L) not in cid]
            nc = min(4, len(crit))
            samp = rng.sample(crit, nc) + rng.sample(rest, min(8 - nc, len(rest)))
            read(p, samp)
            agree = tot = 0
            for L in samp:
                al, _ = align(L["words"], L["res"][0])
                for w, o in zip(L["words"], al):
                    tot += 1
                    agree += 1 if o is not None and loose(o) == loose(w["text"]) else 0
            p["layer_agree"] = agree / tot if tot else 1.0
            if tot and 1 - agree / tot > self.tau_layer:
                p["layer_distrust"] = True
                read(p, ls)
                for L in ls:
                    apply(L)
            else:
                for L in samp:
                    apply(L, replace=L["res"][1] >= 0.9)
                if self.crit_all:
                    read(p, crit)
                    for L in crit:
                        apply(L, replace=L["res"][1] >= 0.9)

        dig = [p for p in pages if p["mode"] == "digital"]
        for p in dig:
            trig = [L for L in p["lines"] if any(w["err"] or anomalous(w["text"]) for w in L["words"]) or self.nonword_rate(L) > 0.5]
            p["trig_lines"] = len(trig)
            read(p, trig)
            for L in trig:
                apply(L, sel=self.suspicious)
        fonts = {}
        for p in dig:
            for L in p["lines"]:
                for f in set(w["font"] for w in L["words"]):
                    hasd = any(w["font"] == f and any(c.isdigit() for c in w["text"]) for w in L["words"])
                    fonts.setdefault(f, dict(d=[], a=[]))["d" if hasd else "a"].append((p, L))

        def stats_for(f, samp):
            nd = na = md = ma = 0
            cnt = {}
            byp = {}
            for p, L in samp:
                byp.setdefault(id(p), (p, []))[1].append(L)
            for p, Ls in byp.values():
                read(p, Ls)
                for L in Ls:
                    _, pairs = align(L["words"], L["res"][0])
                    fw = {k for k, w in enumerate(L["words"]) if w["font"] == f}
                    for k, a, b in pairs:
                        if k not in fw:
                            continue
                        if a.isdigit() and b.isdigit():
                            md += 1
                            cnt[(a, b)] = cnt.get((a, b), 0) + 1
                        elif a.isalpha() and b.isalpha() and a.lower() != b.lower():
                            ma += 1
                    nd += sum(sum(c.isdigit() for c in dl.norm(L["words"][k]["text"])) for k in fw)
                    na += sum(sum(c.isalpha() for c in dl.norm(L["words"][k]["text"])) for k in fw)
            return nd, md, na, ma, (max(cnt.values()) if cnt else 0)

        dist_d, dist_a = set(), set()
        fstat = {}
        for f, s in fonts.items():
            sd = rng.sample(s["d"], min(self.k_digit, len(s["d"])))
            sa = rng.sample(s["a"], min(self.k_alpha, len(s["a"])))
            nd, md, na, ma, rep = stats_for(f, sd + sa)
            esc = False
            if (md == 1 and rep < 2) or 0 < ma < 3:
                esc = True
                used = set(id(L) for _, L in sd + sa)
                more = [x for x in s["d"] if id(x[1]) not in used]
                more_a = [x for x in s["a"] if id(x[1]) not in used]
                extra = rng.sample(more, min(self.k_more, len(more))) + rng.sample(more_a, min(self.k_more // 2, len(more_a)))
                nd, md, na, ma, rep = stats_for(f, sd + sa + extra)
            bd = (md >= 2 and nd > 0 and md / nd >= 0.1) or rep >= 2
            ba = ma >= 3 and na > 0 and ma / na >= 0.05
            fstat[f] = dict(nd=nd, md=md, na=na, ma=ma, rep=rep, esc=esc, distrust_digits=bool(bd), distrust_letters=bool(ba))
            if bd:
                dist_d.add(f)
            if ba:
                dist_a.add(f)

        def bad_word(w):
            return (w["font"] in dist_d and any(c.isdigit() for c in w["text"])) or (w["font"] in dist_a and any(c.isalpha() for c in w["text"]))

        def crit_check(w):
            return bool(CRIT.search(w["text"])) and not bad_word(w) and w["src"] != "ocr"

        for p in dig:
            hit = [L for L in p["lines"] if any(bad_word(w) for w in L["words"])]
            read(p, hit)
            for L in hit:
                apply(L, sel=bad_word)
            if self.crit_all:
                read(p, [L for L in p["lines"] if any(crit_check(w) for w in L["words"])])
            for L in p["lines"]:
                if "res" in L:
                    apply(L, sel=crit_check, replace=False)
        scan_tokens = {}
        for p in pages:
            if p["mode"] == "scan" and docling_scan is not None:
                scan_tokens[p["i"]] = docling_scan(path, p["i"])
        out = []
        for p in pages:
            ra = sum((L["box"][2] - L["box"][0]) * (L["box"][3] - L["box"][1]) for L in p["lines"] if id(L) in p["read"])
            out.append(dict(i=p["i"], mode=p["mode"], img_cov=round(p["img_cov"], 3), ocr_lines=len(p["read"]), n_lines=len(p["lines"]),
                            ocr_area=ra, text_area=p["text_area"], layer_agree=p.get("layer_agree"), trig_lines=p.get("trig_lines", 0),
                            scan_text=scan_tokens.get(p["i"]),
                            words=[[w["text"], w["out"], w["src"], int(w["flag"]), *[round(v, 1) for v in w["box"]]] for w in p["words"]]))
        return dict(pages=out, fonts=fstat, distrust=sorted(dist_d | dist_a), wall=time.perf_counter() - t0, cpu=time.process_time() - c0)

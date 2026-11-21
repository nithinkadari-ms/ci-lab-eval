import io
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pikepdf
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from common import cfg, pdf as P

SRC = os.path.join(cfg.DATA, "g8", "src")
OUT = os.path.join(cfg.DATA, "g8", "docs")
PAGES = 5
DPI = 150
SWAPS = [("1", "7"), ("3", "8"), ("5", "6"), ("0", "8"), ("2", "7"), ("4", "9"), ("6", "9"), ("1", "4")]
DIGIT_CONF = {"1": "7", "7": "1", "5": "6", "6": "5", "0": "8", "8": "0", "3": "8", "2": "7", "9": "4", "4": "9"}
ALPHA_CONF = [("rn", "m"), ("m", "rn"), ("l", "1"), ("O", "0"), ("e", "c"), ("c", "e"), ("i", "l"), ("S", "5"), ("B", "8"), ("h", "b")]
FONT = "Helvetica"
for fp in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",):
    if os.path.exists(fp):
        pdfmetrics.registerFont(TTFont("DejaVu", fp))
        FONT = "DejaVu"

CRIT = re.compile(r"\d.*\d")


def is_crit(tok):
    return bool(CRIT.search(tok))


def parse_cmap(data):
    s = data.decode("latin-1")
    spaces = re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", " ".join(re.findall(r"begincodespacerange(.*?)endcodespacerange", s, re.S)))
    m = {}

    def dst(h):
        try:
            return bytes.fromhex(h if len(h) % 2 == 0 else "0" + h).decode("utf-16-be", "replace")
        except ValueError:
            return ""

    for blk in re.findall(r"beginbfchar(.*?)endbfchar", s, re.S):
        for a, b in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>", blk):
            m[(int(a, 16), len(a) // 2)] = dst(b)
    for blk in re.findall(r"beginbfrange(.*?)endbfrange", s, re.S):
        for a, b, arr, base in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(?:\[([^\]]*)\]|<([0-9A-Fa-f]*)>)", blk):
            lo, hi, nb = int(a, 16), int(b, 16), len(a) // 2
            if hi - lo > 65535:
                continue
            if arr:
                for k, h in enumerate(re.findall(r"<([0-9A-Fa-f]*)>", arr)):
                    m[(lo + k, nb)] = dst(h)
            else:
                units = bytearray(bytes.fromhex(base if len(base) % 2 == 0 else "0" + base))
                for k in range(hi - lo + 1):
                    u = bytearray(units)
                    if len(u) >= 2:
                        last = int.from_bytes(u[-2:], "big") + k
                        u[-2:] = (last & 0xFFFF).to_bytes(2, "big")
                    else:
                        u = bytearray([(u[0] + k) & 0xFF]) if u else u
                    m[(lo + k, nb)] = bytes(u).decode("utf-16-be", "replace")
    return m, spaces


def write_cmap(m, spaces):
    nb = max((k[1] for k in m), default=1)
    if not spaces:
        spaces = [("00" * nb, "FF" * nb)]
    lines = ["/CIDInit /ProcSet findresource begin", "12 dict begin", "begincmap",
             "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def",
             "/CMapName /Adobe-Identity-UCS def", "/CMapType 2 def",
             "%d begincodespacerange" % len(spaces)]
    lines += ["<%s> <%s>" % (a, b) for a, b in spaces]
    lines.append("endcodespacerange")
    items = sorted(m.items())
    for i in range(0, len(items), 100):
        chunk = items[i:i + 100]
        lines.append("%d beginbfchar" % len(chunk))
        for (code, n), u in chunk:
            lines.append("<%0*X> <%s>" % (2 * n, code, u.encode("utf-16-be").hex().upper()))
        lines.append("endbfchar")
    lines += ["endcmap", "CMapName currentdict /CMap defineresource pop", "end", "end"]
    return "\n".join(lines).encode("latin-1")


def simple_maps(path):
    from pdfminer.pdfdocument import PDFDocument
    from pdfminer.pdfinterp import PDFResourceManager
    from pdfminer.pdfpage import PDFPage
    from pdfminer.pdfparser import PDFParser
    from pdfminer.pdftypes import PDFObjRef, resolve1
    out = {}
    with open(path, "rb") as f:
        doc = PDFDocument(PDFParser(f))
        rm = PDFResourceManager(caching=True)
        for page in PDFPage.create_pages(doc):
            fd = resolve1((page.resources or {}).get("Font")) or {}
            for _, spec in fd.items():
                if not isinstance(spec, PDFObjRef) or spec.objid in out:
                    continue
                try:
                    font = rm.get_font(spec.objid, resolve1(spec))
                except Exception:
                    continue
                if font.is_multibyte():
                    continue
                mp = {}
                for code in range(256):
                    try:
                        u = font.to_unichr(code)
                    except Exception:
                        continue
                    if u:
                        mp[(code, 1)] = u
                out[spec.objid] = mp
    return out


def pick_pages(path):
    doc = P.open_pdf(path)
    cand = []
    for i in range(min(len(doc), 30)):
        pg = doc[i]
        if pg.get_rotation() != 0:
            continue
        txt = pg.get_textpage().get_text_bounded()
        if len(txt) < 300:
            continue
        cand.append((sum(ch.isdigit() for ch in txt), i))
    cand.sort(reverse=True)
    return sorted(i for _, i in cand[:PAGES])


def page_words(path):
    doc = P.open_pdf(path)
    pages = []
    for i in range(len(doc)):
        pg = doc[i]
        geo, chs, ws = P.page_words(pg, style=True)
        pages.append(dict(w=geo.w, h=geo.h, words=[[w["text"], *[round(v, 2) for v in w["box"]], w["font"]] for w in ws]))
    return pages


def render_jpeg(path, idx, dpi=DPI):
    doc = P.open_pdf(path)
    im = P.render(doc[idx], scale=dpi / 72.0, annots=True).convert("L")
    b = io.BytesIO()
    im.save(b, "JPEG", quality=82)
    return b.getvalue(), im.size


def remap(clean, dest, rng, gold):
    swap = rng.sample(SWAPS, 8)
    pairs, used = [], set()
    for a, b in swap:
        if a not in used and b not in used:
            pairs.append((a, b))
            used |= {a, b}
        if len(pairs) == 2:
            break
    dmap = {}
    for a, b in pairs:
        dmap[a], dmap[b] = b, a
    fcount = {}
    for pg in gold:
        for w in pg["words"]:
            if any(c.isdigit() for c in w[0]):
                fcount[w[5]] = fcount.get(w[5], 0) + sum(c.isdigit() for c in w[0])
    mode = "all" if rng.random() < 0.5 or not fcount else "one"
    target = max(fcount, key=fcount.get) if fcount else None
    smaps = simple_maps(clean)
    pdf = pikepdf.open(clean)
    touched = 0
    seen = set()
    for pg in pdf.pages:
        try:
            res = pg.resources
        except Exception:
            res = pg.obj.get("/Resources", pikepdf.Dictionary())
        fonts = res.get("/Font", pikepdf.Dictionary())
        for _, f in fonts.items():
            if not isinstance(f, pikepdf.Dictionary) or f.objgen in seen:
                continue
            seen.add(f.objgen)
            base = str(f.get("/BaseFont", ""))[1:]
            if mode == "one" and target and base.split("+")[-1] not in target and target not in base:
                continue
            m, spaces = None, None
            if "/ToUnicode" in f:
                try:
                    m, spaces = parse_cmap(f.ToUnicode.read_bytes())
                except Exception:
                    m = None
            if not m and f.get("/Subtype") != "/Type0":
                m, spaces = smaps.get(f.objgen[0]), None
            if not m:
                continue
            changed = False
            nm = {}
            for k, u in m.items():
                if len(u) == 1 and u in dmap:
                    nm[k] = dmap[u]
                    changed = True
                else:
                    nm[k] = u
            if not changed:
                continue
            f.ToUnicode = pdf.make_stream(write_cmap(nm, spaces))
            touched += 1
    pdf.save(dest)
    return dict(pairs=pairs, mode=mode, target=target if mode == "one" else None, fonts=touched)


def noisy(word, rng, crit):
    p = 0.35 if crit else 0.06
    if rng.random() >= p:
        return word
    digits = [i for i, c in enumerate(word) if c in DIGIT_CONF]
    if crit and digits:
        i = rng.choice(digits)
        return word[:i] + DIGIT_CONF[word[i]] + word[i + 1:]
    opts = [(a, b) for a, b in ALPHA_CONF if a in word]
    if opts and rng.random() < 0.7:
        a, b = rng.choice(opts)
        i = word.index(a)
        return word[:i] + b + word[i + len(a):]
    if len(word) > 3:
        i = rng.randrange(len(word))
        return word[:i] + word[i + 1:]
    return word


def image_pdf(clean, gold, dest, rng, layer):
    c = canvas.Canvas(dest)
    layers = []
    for i, pg in enumerate(gold):
        w, h = pg["w"], pg["h"]
        c.setPageSize((w, h))
        jpg, _ = render_jpeg(clean, i)
        from reportlab.lib.utils import ImageReader
        c.drawImage(ImageReader(io.BytesIO(jpg)), 0, 0, width=w, height=h)
        lw = []
        if layer:
            t = c.beginText()
            t.setTextRenderMode(3)
            for wd in pg["words"]:
                txt, l, tp, r, b = wd[0], wd[1], wd[2], wd[3], wd[4]
                bad = noisy(txt, rng, is_crit(txt))
                hh = max(1.0, b - tp)
                fs = max(1.0, hh * 0.95)
                sw = pdfmetrics.stringWidth(bad, FONT, fs) or 1.0
                t.setFont(FONT, fs)
                t.setHorizScale(max(10.0, min(400.0, 100.0 * max(1.0, r - l) / sw)))
                t.setTextOrigin(l, h - b + 0.22 * hh)
                t.textOut(bad)
                lw.append(bad)
            c.drawText(t)
        layers.append(lw)
        c.showPage()
    c.save()
    return layers


def mixed(clean, gold, dest):
    tmp = dest + ".img.pdf"
    image_pdf(clean, gold, tmp, random.Random(0), layer=False)
    src = pikepdf.open(clean)
    img = pikepdf.open(tmp)
    out = pikepdf.new()
    scanned = []
    for i in range(len(src.pages)):
        if i % 2 == 1:
            out.pages.append(img.pages[i])
            scanned.append(i)
        else:
            out.pages.append(src.pages[i])
    out.save(dest)
    out.close()
    img.close()
    src.close()
    os.remove(tmp)
    return scanned


def build(rec):
    did = rec["id"]
    d = os.path.join(OUT, did)
    os.makedirs(d, exist_ok=True)
    src = os.path.join(SRC, did + ".pdf")
    pages = pick_pages(src)
    if not pages:
        return None
    sp = pikepdf.open(src)
    cp = pikepdf.new()
    for i in pages:
        cp.pages.append(sp.pages[i])
    if "/Outlines" in cp.Root:
        del cp.Root["/Outlines"]
    clean = os.path.join(d, "C.pdf")
    cp.save(clean)
    gold = page_words(clean)
    rng = random.Random("g8:" + did)
    meta = dict(id=did, source=rec["source"], url=rec["url"], src_pages=pages, pages=gold, variants={"C": {}})
    try:
        r = remap(clean, os.path.join(d, "R.pdf"), rng, gold)
        rg = page_words(os.path.join(d, "R.pdf"))
        ch = nd = 0
        for g, x in zip(gold, rg):
            a = "".join(w[0] for w in g["words"])
            b = "".join(w[0] for w in x["words"])
            if len(a) == len(b):
                for u, v in zip(a, b):
                    if u != v:
                        ch += 1
                        nd += 0 if (u.isdigit() and v.isdigit()) else 1
            else:
                nd += abs(len(a) - len(b))
        c0, c1 = P.open_pdf(clean), P.open_pdf(os.path.join(d, "R.pdf"))
        eq = all(P.render(c0[i], 1.0).tobytes() == P.render(c1[i], 1.0).tobytes() for i in range(len(c0)))
        r.update(changed_chars=ch, nondigit_changes=nd, render_equal=eq)
        if ch > 0:
            meta["variants"]["R"] = r
        else:
            os.remove(os.path.join(d, "R.pdf"))
            meta["remap_skipped"] = r
    except Exception as e:
        meta["remap_error"] = repr(e)[:300]
    layers = image_pdf(clean, gold, os.path.join(d, "O.pdf"), rng, layer=True)
    meta["variants"]["O"] = dict(layer=layers)
    meta["variants"]["M"] = dict(scanned=mixed(clean, gold, os.path.join(d, "M.pdf")))
    cfg.dump(meta, os.path.join(d, "gold.json"))
    return meta


def main():
    man = cfg.load(os.path.join(cfg.DATA, "g8", "src.json"))
    ok = []
    for rec in man:
        try:
            m = build(rec)
            if m:
                ok.append(dict(id=rec["id"], source=rec["source"], variants=sorted(m["variants"]),
                               remap=m["variants"].get("R")))
                cfg.log(rec["id"], sorted(m["variants"]), m["variants"].get("R"))
        except Exception as e:
            cfg.log("build fail", rec["id"], repr(e)[:300])
    cfg.dump(ok, os.path.join(cfg.DATA, "g8", "docs.json"))
    cfg.log("g8 docs", len(ok), "with R", sum(1 for x in ok if "R" in x["variants"]))


if __name__ == "__main__":
    main()

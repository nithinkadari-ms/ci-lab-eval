import os
import random
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Pt

from common import cfg, textgen as T

OUT = os.path.join(cfg.DATA, "g4")
FAMILIES = {
    "bullets": [("bullet", "•"), ("bullet", "◦"), ("bullet", "▪"), ("bullet", "–")],
    "dec_alpha_roman": [("decimal", "%1."), ("lowerLetter", "%2."), ("lowerRoman", "%3."), ("decimal", "%4)")],
    "paren": [("decimal", "(%1)"), ("lowerLetter", "(%2)"), ("lowerRoman", "(%3)"), ("upperLetter", "(%4)")],
    "outline": [("decimal", "%1."), ("decimal", "%1.%2."), ("decimal", "%1.%2.%3."), ("decimal", "%1.%2.%3.%4.")],
    "upper": [("upperRoman", "%1."), ("upperLetter", "%2."), ("decimal", "%3."), ("lowerLetter", "%4)")],
    "mixed": [("decimal", "%1."), ("bullet", "•"), ("lowerLetter", "%3)"), ("bullet", "–")],
    "close_paren": [("decimal", "%1)"), ("lowerLetter", "%2)"), ("lowerRoman", "%3)"), ("decimal", "%4.")],
}
NEG = ["2019 was a difficult year for the regional business and %s",
       "3.5 million units were shipped during the period and %s",
       "1990s regulations still apply to %s",
       "(See Table 2 for details.) %s",
       "A. Smith and B. Jones reviewed %s",
       "12 May 2024: the committee noted that %s",
       "No. 7 warehouse remained closed while %s",
       "IV drug pricing was discussed in relation to %s",
       "e.g. the supplier, the customer and %s",
       "i.e. all parties acknowledged that %s"]


def abstract_xml(aid, fam, tie):
    lv = []
    for i in range(9):
        fmt, txt = FAMILIES[fam][min(i, 3)]
        if fam in ("dec_alpha_roman", "paren", "close_paren", "upper", "mixed") and "%" in txt:
            txt = txt.replace("%%%d" % (min(i, 3) + 1), "%%%d" % (i + 1))
        if fam == "outline":
            txt = ".".join("%%%d" % (k + 1) for k in range(i + 1)) + "."
        rpr = '<w:rPr><w:rFonts w:ascii="DejaVu Sans" w:hAnsi="DejaVu Sans"/></w:rPr>' if fmt == "bullet" else ""
        left = 720 * (i + 1) + tie
        lv.append('<w:lvl w:ilvl="%d"><w:start w:val="1"/><w:numFmt w:val="%s"/><w:lvlText w:val="%s"/><w:lvlJc w:val="left"/>'
                  '<w:pPr><w:ind w:left="%d" w:hanging="360"/></w:pPr>%s</w:lvl>' % (i, fmt, txt, left, rpr))
    return parse_xml('<w:abstractNum %s w:abstractNumId="%d"><w:multiLevelType w:val="multilevel"/>%s</w:abstractNum>' % (nsdecls("w"), aid, "".join(lv)))


def num_xml(nid, aid, restart):
    ov = '<w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride>' if restart else ""
    return parse_xml('<w:num %s w:numId="%d"><w:abstractNumId w:val="%d"/>%s</w:num>' % (nsdecls("w"), nid, aid, ov))


def set_num(p, nid, ilvl):
    ppr = p._p.get_or_add_pPr()
    ppr.append(parse_xml('<w:numPr %s><w:ilvl w:val="%d"/><w:numId w:val="%d"/></w:numPr>' % (nsdecls("w"), ilvl, nid)))


def item_text(rng):
    if rng.random() < 0.3:
        return T.words(rng, rng.randint(35, 70)).capitalize() + "."
    return T.words(rng, rng.randint(4, 18)).capitalize()


def make(i, rng):
    did = "lst%04d" % i
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = rng.choice(["Liberation Serif", "Liberation Sans", "DejaVu Serif"])
    st.font.size = Pt(rng.choice([10, 11, 12]))
    numbering = doc.part.numbering_part.element
    first_num = numbering.find(qn("w:num"))
    aid, nid = 100, 200
    gold = []
    items = 0
    n_lists = rng.randint(2, 5)
    last_num = {}
    sec = 1
    for li in range(n_lists):
        r = rng.random()
        if r < 0.35:
            t = rng.choice(T.HEAD)
            if rng.random() < 0.5:
                t = "%d. %s" % (sec, t)
                sec += 1
            doc.add_heading(t, level=rng.choice([1, 2]))
            gold.append(dict(kind="heading", text=t))
        for _ in range(rng.randint(1, 2)):
            if rng.random() < 0.4:
                t = rng.choice(NEG) % T.sentence(rng).lower()
            else:
                t = T.paragraph(rng, rng.randint(1, 3))
            doc.add_paragraph(t)
            gold.append(dict(kind="prose", text=t))
        fam = rng.choice(list(FAMILIES))
        mode = "new"
        if fam in last_num and rng.random() < 0.5:
            mode = rng.choice(["restart", "continue"])
        if mode == "continue":
            this = last_num[fam][1]
            lid = last_num[fam][2]
        else:
            if mode == "new":
                a = aid
                aid += 1
                el = abstract_xml(a, fam, rng.choice([0, 0, 180]))
                first_num = numbering.find(qn("w:num"))
                if first_num is not None:
                    first_num.addprevious(el)
                else:
                    numbering.append(el)
            else:
                a = last_num[fam][0]
            this = nid
            nid += 1
            numbering.append(num_xml(this, a, mode == "restart"))
            lid = "L%d" % li
        last_num[fam] = (a if mode != "continue" else last_num[fam][0], this, lid)
        n = rng.randint(3, 12)
        lvl = 0
        stack = []
        for k in range(n):
            if k > 0:
                x = rng.random()
                if x < 0.25 and lvl < 3:
                    lvl += 1
                elif x < 0.42 and lvl > 0:
                    lvl = rng.randint(0, lvl - 1)
            while stack and stack[-1][1] >= lvl:
                stack.pop()
            parent = stack[-1][0] if stack else -1
            t = item_text(rng)
            p = doc.add_paragraph(t)
            set_num(p, this, lvl)
            gold.append(dict(kind="list", text=t, ilvl=lvl, list=lid, family=fam, mode=mode, parent=parent, wrapped=len(t.split()) > 30))
            stack.append((len(gold) - 1, lvl))
            items += 1
    path = os.path.join(OUT, "docx", did + ".docx")
    doc.save(path)
    return dict(id=did, gold=gold, items=items)


def main():
    os.makedirs(os.path.join(OUT, "docx"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "pdf"), exist_ok=True)
    rng = random.Random("g4-lists")
    man = [make(i, rng) for i in range(cfg.n(260, 6))]
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", os.path.join(OUT, "pdf")] +
                   [os.path.join(OUT, "docx", m["id"] + ".docx") for m in man], check=False, timeout=3600)
    ok = [m for m in man if os.path.exists(os.path.join(OUT, "pdf", m["id"] + ".pdf"))]
    cfg.dump(ok, os.path.join(OUT, "lists.json"))
    cfg.log("g4 docs", len(man), "pdf ok", len(ok), "items", sum(m["items"] for m in ok))


if __name__ == "__main__":
    main()

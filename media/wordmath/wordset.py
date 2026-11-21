"""Test sets for "Word formulas: real Word / Cambria Math".
  docx: N_DOCS .docx files, PER_DOC equations each, one equation per page (marker paragraph EQ<id> first),
        display (oMathPara) or inline (QQL <oMath> QQR in a sentence); for export to PDF by Microsoft Word.
  tex:  the same kind of formulas as LuaLaTeX sources with unicode-math and Cambria Math, one per page,
        in chunks of 100, for a windows runner that has the Cambria fonts.
Gold = the LaTeX of the source OMML (gen.tx, all accepted forms), scored with the round-3 normaliser.
usage: wordset.py docx OUTDIR N_DOCS PER_DOC | wordset.py tex OUTDIR N"""
import json
import os
import random
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen  # noqa: E402

KINDS = gen.CONSTRUCTS + ["long"]
NO_INLINE = {"matrix", "eqarray", "eqnumber", "nested", "long", "underbrace"}
LONG_PARTS = ["fraction", "superscript", "subsup", "nary", "radical", "delimiter", "function", "accent", "subscript"]


def make_case(r, kind, i):
    if kind == "long":
        parts = []
        for k in range(r.randint(4, 6)):
            if k:
                parts.append(gen.T(r.choice(["+", "-", "=", "\u00b7"])))
            parts.append(gen.construct(r, r.choice(LONG_PARTS), 1))
        ast = ("row", parts)
    else:
        ast = gen.construct(r, kind)
    mode = "inline" if kind not in NO_INLINE and r.random() < 0.3 else "display"
    return {"id": f"{kind}-{i:04d}", "construct": kind, "ast": ast, "mode": mode, "omml": gen.om(ast),
            "gold": gen.tx(ast), "eqno": ast[2] if ast[0] == "eqno" else None}


def cases(n, seed):
    r = random.Random(seed)
    out = []
    for i in range(n):
        out.append(make_case(r, KINDS[i % len(KINDS)], i))
    return out


def docx_set(out, n_docs, per):
    os.makedirs(out, exist_ok=True)
    cs = cases(n_docs * per, 2026)
    man = []
    for d in range(n_docs):
        name = f"wf_{d:03d}.docx"
        chunk = cs[d * per:(d + 1) * per]
        body = []
        for p, c in enumerate(chunk):
            if p:
                body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
            body.append(f'<w:p><w:r><w:t>EQ{c["id"]}</w:t></w:r></w:p>')
            if c["mode"] == "display":
                body.append(f"<w:p><m:oMathPara><m:oMath>{c['omml']}</m:oMath></m:oMathPara></w:p>")
            else:
                body.append('<w:p><w:r><w:t xml:space="preserve">The value QQL </w:t></w:r>'
                            f"<m:oMath>{c['omml']}</m:oMath>"
                            '<w:r><w:t xml:space="preserve"> QQR is used below.</w:t></w:r></w:p>')
            man.append({k: c[k] for k in ("id", "construct", "mode", "gold", "eqno", "omml")} | {"doc": name, "page": p})
        doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {gen.NS}><w:body>' + "".join(body)
               + '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" '
               'w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>')
        with zipfile.ZipFile(os.path.join(out, name), "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://'
                       'schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="'
                       'application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType'
                       '="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.'
                       'openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
            z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http:'
                       '//schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://'
                       'schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/'
                       'document.xml"/></Relationships>')
            z.writestr("word/document.xml", doc)
    json.dump(man, open(os.path.join(out, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False)
    from collections import Counter
    print(n_docs, "docx,", len(man), "equations", Counter((m["construct"], m["mode"]) for m in man))


PRE = r"""\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,mathtools}
\usepackage{unicode-math}
\setmainfont{Cambria}
\setmathfont{Cambria Math}
\pagestyle{empty}
\begin{document}
"""


def tex_set(out, n):
    os.makedirs(out, exist_ok=True)
    cs = cases(n, 4242)
    man = []
    per = 100
    for d in range(0, n, per):
        name = f"wt_{d // per:03d}"
        body = []
        for p, c in enumerate(cs[d:d + per]):
            tex = c["gold"][0]
            if p:
                body.append(r"\newpage")
            body.append(f"\\noindent EQ{c['id']}\\par\\medskip")
            if c["mode"] == "display":
                body.append(f"\\begin{{equation*}}\n{tex}\n\\end{{equation*}}")
            else:
                body.append(f"\\noindent The value QQL ${tex}$ QQR is used below.")
            man.append({k: c[k] for k in ("id", "construct", "mode", "gold", "eqno")} | {"doc": name + ".pdf", "page": p})
        open(os.path.join(out, name + ".tex"), "w", encoding="utf-8").write(PRE + "\n".join(body) + "\n\\end{document}\n")
    json.dump(man, open(os.path.join(out, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(len(man), "formulas in", (n + per - 1) // per, "tex files")


if __name__ == "__main__":
    if sys.argv[1] == "docx":
        docx_set(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    else:
        tex_set(sys.argv[2], int(sys.argv[3]))

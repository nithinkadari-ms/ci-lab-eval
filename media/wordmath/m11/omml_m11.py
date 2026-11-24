"""Milestone 11: Word equations (OMML) to LaTeX, five converters, two equation sets, one fair normaliser.

Sets:
  wordmath   the round-4 set (media/wordmath/gen.py): 720 generated equations (18 constructs) and 31
             hand-written ones, with accepted gold LaTeX forms.
  plurimath  plurimath-testsuite corpus/omml (BSD-2, pinned commit), every case with an expected LaTeX
             rendering (the expectations are plurimath's own conventions).
Systems:
  ours       Contextual's converter (outputs produced by the private build on the CI runner, file
             ours.jsonl next to this script: one {"set", "id", "latex"} line per case)
  docling    docling.rs 2.84.0 built-in converter (Python wheel), through a DOCX
  easydoc    easydoc-math 0.1.2 (media/wordmath/edm), on the OMML directly
  anydoc     anydoc 0.2.5 as published (anydoc-cli here), through a DOCX
  docboss    docboss at a pinned commit (its `md` command), through a DOCX
Scoring: exact match after the fair normaliser (fairnorm.py) against any accepted gold; equation numbers
removed before comparing (as in round 4). The round-3 normaliser is reported too.

usage:
  omml_m11.py docx-outputs TOOL CMD OUTDIR     TOOL in docling, anydoc, docboss; CMD = binary or '-'
  omml_m11.py edm-outputs EDM_BIN OUTDIR
  omml_m11.py score OUTDIR"""
import glob
import json
import os
import re
import subprocess
import sys
import zipfile
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
WM = os.path.dirname(HERE)
sys.path.insert(0, WM)
sys.path.insert(0, HERE)
import gen  # noqa: E402
import fairnorm  # noqa: E402
import texnorm  # noqa: E402  (on the path through fairnorm)

PTS = os.environ.get("PTS_DIR", "pts")
EQNO_RE = re.compile(r"\\tag\*?\s*\{\s*(\d+)\s*\}|#\s*\(\s*(\d+)\s*\)|\\qquad\s*\(\s*(\d+)\s*\)\s*$|\(\s*(\d+)\s*\)\s*$")
NS = gen.NS
MARK = re.compile(r"^(EQ\d{3}x\d{3}|EQEND)$")


def cases():
    out = []
    for c in gen.all_cases(per=40):
        out.append({"set": "wordmath", "id": c["id"], "group": c["construct"], "gold": c["gold"],
                    "eqno": c["eqno"], "omath": gen.omath(c),
                    "para": f"<m:oMathPara><m:oMath>{c['omml']}</m:oMath></m:oMathPara>"})
    import yaml
    for f in sorted(glob.glob(os.path.join(PTS, "corpus", "omml", "*.yaml"))):
        if f.endswith("rejections.yaml"):
            continue
        d = yaml.safe_load(open(f, encoding="utf-8"))
        for c in d["cases"]:
            lat = (c.get("expected") or {}).get("latex")
            if isinstance(lat, dict):
                lat = lat.get("output")
            if not isinstance(lat, str):
                continue
            out.append({"set": "plurimath", "id": c["id"], "group": d["group"], "gold": [lat], "eqno": None,
                        "omath": c["input"], "para": c["input"]})
    return out


def well_formed(fragment):
    from lxml import etree
    try:
        etree.fromstring(f"<w:p {NS}>{fragment}</w:p>".encode("utf-8"))
        return True
    except etree.XMLSyntaxError:
        return False


def write_docx(chunk, path):
    body = []
    for c in chunk:
        body.append(f'<w:p><w:r><w:t>{c["marker"]}</w:t></w:r></w:p>')
        body.append(f"<w:p>{c['para']}</w:p>")
    body.append('<w:p><w:r><w:t>EQEND</w:t></w:r></w:p>')
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {NS}><w:body>' + "".join(body)
           + '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/></w:sectPr></w:body></w:document>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/'
          'package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
          'relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/'
          'document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"'
          '/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats'
            '.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)


def strip_math(s):
    s = (s or "").strip()
    for a, b in (("$$", "$$"), ("$", "$"), ("\\[", "\\]"), ("\\(", "\\)")):
        if s.startswith(a) and s.endswith(b) and len(s) >= len(a) + len(b):
            return s[len(a):len(s) - len(b)].strip()
    return s


def join_lines(parts):
    parts = [p for p in (strip_math(x) for x in parts) if p]
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return "\\begin{gathered} " + " \\\\ ".join(parts) + " \\end{gathered}"


def docling_texts(path):
    import docling_rs as d
    native = d.DocumentConverter()._convert_native(path, None, None)
    doc = json.loads(native.document_json)
    out = []

    def walk(node):
        for ch in node.get("children", []) or []:
            parts = ch.get("$ref", "").split("/")
            if len(parts) != 3:
                continue
            item = doc[parts[1]][int(parts[2])]
            if parts[1] == "texts":
                out.append((item.get("label", ""), item.get("text", "")))
            walk(item)
    walk(doc.get("body", {}))
    return out


def markdown_blocks(md):
    """(label, text) pairs from Markdown: marker lines as text, everything else as math candidates."""
    out = []
    for line in md.splitlines():
        t = line.strip().strip("\\")
        if not t:
            continue
        if MARK.match(t):
            out.append(("text", t))
        else:
            out.append(("formula", line.strip()))
    return out


def docx_outputs(tool, cmd, outdir):
    os.makedirs(outdir, exist_ok=True)
    cs = cases()
    good = [c for c in cs if well_formed(c["para"])]
    got = {}
    per = 50
    for ci in range(0, len(good), per):
        ch = good[ci:ci + per]
        for k, c in enumerate(ch):
            c["marker"] = f"EQ{ci // per:03d}x{k:03d}"
        path = os.path.join(outdir, f"{tool}_{ci // per:03d}.docx")
        write_docx(ch, path)
        try:
            if tool == "docling":
                blocks = docling_texts(path)
            else:
                args = [cmd, path] if tool == "anydoc" else [cmd, "md", path]
                p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=600)
                if p.returncode != 0:
                    raise RuntimeError(p.stderr[-300:])
                blocks = markdown_blocks(p.stdout)
        except Exception as e:  # noqa: BLE001
            for c in ch:
                got[c["id"]] = {"error": f"{type(e).__name__}: {e}"[:200]}
            continue
        by_marker = {c["marker"]: c for c in ch}
        cur, buf = None, []
        for label, text in blocks + [("text", "EQEND")]:
            t = text.strip()
            if MARK.match(t):
                if cur is not None:
                    got[cur["id"]] = {"latex": join_lines(buf)}
                cur, buf = by_marker.get(t), []
                continue
            if cur is not None and (label == "formula" or t.startswith("$")):
                buf.append(t)
        os.remove(path)
    with open(os.path.join(outdir, f"{tool}.jsonl"), "w", encoding="utf-8") as f:
        for c in cs:
            r = got.get(c["id"], {"error": "not converted (input is not well-formed XML)"
                                  if c not in good else "no output after marker"})
            f.write(json.dumps({"set": c["set"], "id": c["id"], **r}, ensure_ascii=False) + "\n")


def edm_outputs(edm, outdir):
    os.makedirs(outdir, exist_ok=True)
    cs = cases()
    inp = "".join(f"{c['set']}:{c['id']}\t{c['omath'].replace(chr(10), ' ').replace(chr(13), ' ')}\n" for c in cs)
    p = subprocess.run([edm], input=inp, capture_output=True, text=True, encoding="utf-8")
    got = {}
    for line in p.stdout.splitlines():
        parts = line.split("\t", 3)
        if len(parts) == 4:
            got[parts[0]] = {"latex": parts[3]} if parts[1] == "ok" else {"error": parts[3][:200]}
    with open(os.path.join(outdir, "easydoc.jsonl"), "w", encoding="utf-8") as f:
        for c in cs:
            r = got.get(f"{c['set']}:{c['id']}", {"error": "missing"})
            f.write(json.dumps({"set": c["set"], "id": c["id"], **r}, ensure_ascii=False) + "\n")


def strip_no(s):
    m = list(EQNO_RE.finditer(s or ""))
    if not m:
        return s, None
    last = m[-1]
    num = next(g for g in last.groups() if g)
    return (s[:last.start()] + s[last.end():]).strip(), num


def correct(out, case, norm):
    if not out:
        return False
    golds = case["gold"]
    if case.get("eqno"):
        out, _ = strip_no(out)
        golds = [strip_no(g)[0] for g in golds]
    o = norm(out)
    return o in {norm(g) for g in golds}


def plain(s):
    try:
        return texnorm.normalize(s)
    except Exception:  # noqa: BLE001
        return "ERR:" + s


SYSTEMS = ["ours", "docling", "easydoc", "anydoc", "docboss"]


def load(path):
    out = {}
    if not os.path.exists(path):
        return None
    for line in open(path, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[(r["set"], r["id"])] = r.get("latex")
    return out


def score(outdir):
    cs = cases()
    outs = {"ours": load(os.path.join(HERE, "ours.jsonl"))}
    for s in SYSTEMS[1:]:
        outs[s] = load(os.path.join(outdir, f"{s}.jsonl"))
    present = [s for s in SYSTEMS if outs[s] is not None]
    rows = []
    for c in cs:
        r = {"set": c["set"], "id": c["id"], "group": c["group"], "gold": c["gold"][0]}
        for s in present:
            o = outs[s].get((c["set"], c["id"]))
            r[s] = o
            r[s + "_fair"] = correct(o, c, fairnorm.normalize)
            r[s + "_plain"] = correct(o, c, plain)
        rows.append(r)
    json.dump(rows, open(os.path.join(outdir, "omml_m11_rows.json"), "w", encoding="utf-8"), ensure_ascii=False,
              indent=0)
    L = ["## Word equations (OMML) to LaTeX: milestone 11", "",
         "Exact match after the fair normaliser (fairnorm.py: Unicode vs control words, genfrac/atop/binom, "
         "sin(a) vs sin{a}, overrightarrow vs vec ignored; structure counts). Equation numbers removed first.", ""]
    summary = {}
    for st in ("wordmath", "plurimath"):
        sub = [r for r in rows if r["set"] == st]
        if not sub:
            continue
        L += [f"### {st} ({len(sub)} equations)", "", "| group | n | " + " | ".join(present) + " |",
              "|---|---|" + "---|" * len(present)]
        by = defaultdict(list)
        for r in sub:
            by[r["group"]].append(r)
        for g in sorted(by):
            rs = by[g]
            L.append(f"| {g} | {len(rs)} | " + " | ".join(f"{sum(r[s + '_fair'] for r in rs) / len(rs):.3f}"
                                                         for s in present) + " |")
        tot = {s: sum(r[s + "_fair"] for r in sub) / len(sub) for s in present}
        pl = {s: sum(r[s + "_plain"] for r in sub) / len(sub) for s in present}
        L.append(f"| **all (fair)** | {len(sub)} | " + " | ".join(f"**{tot[s]:.1%}**" for s in present) + " |")
        L.append(f"| all (round-3 normaliser) | {len(sub)} | " + " | ".join(f"{pl[s]:.1%}" for s in present) + " |")
        L.append("")
        summary[st] = {"n": len(sub), "fair": tot, "round3": pl}
        if "ours" in present:
            for other in present:
                if other == "ours":
                    continue
                w = sum(1 for r in sub if r["ours_fair"] and not r[other + "_fair"])
                lo = sum(1 for r in sub if r[other + "_fair"] and not r["ours_fair"])
                L.append(f"- ours vs {other}: ours right and {other} wrong {w}, the reverse {lo}")
            L.append("")
            fails = [r for r in sub if not r["ours_fair"]][:30]
            if fails:
                L += ["Our failures (first 30):", ""]
                for r in fails:
                    L.append(f"- `{r['id']}` got `{(r['ours'] or '')[:140]}` gold `{r['gold'][:140]}`")
                L.append("")
    open(os.path.join(outdir, "OMML_M11.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(summary, open(os.path.join(outdir, "omml_m11_summary.json"), "w"), indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    if sys.argv[1] == "docx-outputs":
        docx_outputs(sys.argv[2], sys.argv[3], sys.argv[4])
    elif sys.argv[1] == "edm-outputs":
        edm_outputs(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "score":
        score(sys.argv[2])
    else:
        sys.exit(__doc__)

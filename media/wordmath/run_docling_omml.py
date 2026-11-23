"""Gap 11 add-on: docling.rs 2.84.0's own OMML -> LaTeX converter (backend/omml.rs, a dwml port) on the same
generated + hand-written equation set as run_wordmath.py, scored with the same LaTeX normaliser and the same
equation-number handling as the easydoc-math arm.
usage: run_docling_omml.py OUTDIR"""
import json
import os
import re
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen  # noqa: E402
from run_wordmath import tex_ok  # noqa: E402

os.environ.setdefault("DOCLING_RS_CACHE_DIR", os.path.expanduser("~/dlrs"))
import docling_rs as d  # noqa: E402

MARK = re.compile(r"^(EQ\d{3}x\d{3}|EQEND)$")


def strip_math(s):
    s = (s or "").strip()
    for a, b in (("$$", "$$"), ("$", "$"), ("\\[", "\\]"), ("\\(", "\\)")):
        if s.startswith(a) and s.endswith(b) and len(s) >= len(a) + len(b):
            return s[len(a):len(s) - len(b)].strip()
    return s


def body_texts(doc):
    out = []

    def walk(node):
        for ch in node.get("children", []) or []:
            ref = ch.get("$ref", "")
            parts = ref.split("/")
            if len(parts) != 3:
                continue
            item = doc[parts[1]][int(parts[2])]
            if parts[1] == "texts":
                out.append((item.get("label", ""), item.get("text", ""), item.get("orig", "")))
            walk(item)

    walk(doc.get("body", {}))
    return out


def main():
    outdir = sys.argv[1]
    os.makedirs(outdir, exist_ok=True)
    cases = gen.all_cases(per=int(os.environ.get("WM_PER", "40")))
    conv = d.DocumentConverter()
    per = 50
    got = {}
    t_conv = 0.0
    for ci in range(0, len(cases), per):
        ch = cases[ci:ci + per]
        for k, c in enumerate(ch):
            c["marker"] = f"EQ{ci // per:03d}x{k:03d}"
        path = os.path.join(outdir, f"dm_{ci // per:03d}.docx")
        gen.docx(ch, path)
        t = time.perf_counter()
        try:
            native = conv._convert_native(path, None, None)
            doc = json.loads(native.document_json)
        except Exception as e:  # noqa: BLE001
            for c in ch:
                got[c["id"]] = {"error": f"{type(e).__name__}: {e}"[:200]}
            continue
        t_conv += time.perf_counter() - t
        texts = body_texts(doc)
        by_marker = {c["marker"]: c for c in ch}
        cur = None
        for label, text, orig in texts:
            if MARK.match(text.strip()):
                cur = by_marker.get(text.strip())
                continue
            if cur is None or cur["id"] in got:
                continue
            if label == "formula" or text.strip().startswith("$"):
                got[cur["id"]] = {"label": label, "latex": strip_math(text), "raw": text[:400]}
        for c in ch:
            got.setdefault(c["id"], {"error": "no formula item after marker"})
        os.remove(path)
    rows = []
    for c in cases:
        g = got[c["id"]]
        r = {"id": c["id"], "construct": c["construct"], "source": c["source"]}
        if "error" in g:
            r["ok"], r["no"], r["status"] = False, None, g["error"]
        else:
            r["ok"], r["no"] = tex_ok(g["latex"], c)
            r["status"] = "ok" if g["latex"] else "empty"
            r["latex"] = g["latex"][:300]
            r["gold"] = c["gold"][0][:300]
        rows.append(r)
    json.dump(rows, open(os.path.join(outdir, "docling_omml.json"), "w"), indent=1)
    by = defaultdict(list)
    for r in rows:
        by[r["construct"]].append(r)
    L = ["## Word formulas: docling.rs built-in OMML -> LaTeX", "",
         f"{len(rows)} equations (generated + hand-written, same set and scorer as the easydoc-math arm). "
         f"Conversion time {t_conv:.1f} s total.", "",
         "| construct | n | docling.rs exact | errors / empty |", "|---|---|---|---|"]
    for k in sorted(by):
        rs = by[k]
        bad = sum(1 for r in rs if r["status"] != "ok")
        L.append(f"| {k} | {len(rs)} | {sum(r['ok'] for r in rs)}/{len(rs)} | {bad} |")
    n_ok = sum(r["ok"] for r in rows)
    L.append(f"| **all** | {len(rows)} | **{n_ok}/{len(rows)} = {n_ok / max(1, len(rows)):.1%}** | "
             f"{sum(1 for r in rows if r['status'] != 'ok')} |")
    hand = [r for r in rows if r["source"] == "hand"]
    eq = [r for r in rows if r["no"] is not None]
    L += ["", f"Hand-written cases: {sum(r['ok'] for r in hand)}/{len(hand)}.",
          f"Equation numbers kept: {sum(1 for r in eq if r['no'])}/{len(eq)}.", "",
          "Failure examples (first 25):", ""]
    for r in [r for r in rows if not r["ok"]][:25]:
        L.append(f"- `{r['construct']}` {r['status']}: got `{r.get('latex', '')[:120]}` gold `{r.get('gold', '')[:120]}`")
    open(os.path.join(outdir, "DOCLING_OMML.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:40]))


if __name__ == "__main__":
    main()

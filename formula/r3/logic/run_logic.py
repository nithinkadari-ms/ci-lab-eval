"""Rebuild LaTeX for formula regions from the PDF text layer. In: regions JSONL. Out: one JSON line per region."""
import argparse, json, os, sys, time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdfglyphs import PdfCache, select
from build import rebuild


def work(batch):
    cache = PdfCache()
    out = []
    for r in batch:
        t = time.perf_counter()
        try:
            pd = cache.get(r["pdf"], r["page_index"])
            t1 = time.perf_counter()
            gs, ss = select(pd, r["bbox"])
            res = rebuild(gs, ss)
            res.update({"id": r["id"], "tool": "logic", "status": "ok" if res["latex"] else "no_math", "error": None,
                        "n_glyphs": len(gs), "n_shapes": len(ss), "ms": round((time.perf_counter() - t1) * 1000, 2),
                        "ms_with_page": round((time.perf_counter() - t) * 1000, 2)})
        except Exception as e:
            res = {"id": r["id"], "tool": "logic", "latex": None, "conf": 0.0, "status": "error",
                   "error": f"{type(e).__name__}: {str(e)[:300]}", "ms": round((time.perf_counter() - t) * 1000, 2)}
        out.append(res)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 2)
    a = ap.parse_args()
    regions = [json.loads(l) for l in open(a.input, encoding="utf-8") if l.strip()]
    by_pdf = {}
    for r in regions:
        by_pdf.setdefault(r["pdf"], []).append(r)
    batches = list(by_pdf.values())
    with Pool(a.workers) as p:
        results = [x for b in p.imap_unordered(work, batches) for x in b]
    got = {r["id"]: r for r in results}
    with open(a.output, "w", encoding="utf-8") as f:
        for r in regions:
            f.write(json.dumps(got.get(r["id"], {"id": r["id"], "tool": "logic", "latex": None, "status": "error",
                                                  "error": "missing"}), ensure_ascii=False) + "\n")
    st = {}
    for r in results:
        st[r["status"]] = st.get(r["status"], 0) + 1
    print("logic done", len(regions), st, flush=True)


if __name__ == "__main__":
    main()

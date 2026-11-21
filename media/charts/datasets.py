"""Chart items: synthetic matplotlib charts (vector PDF + PNG renders), ChartX test (InternScience/ChartX), and a
PlotQA test sample (achang/plot_qa, values from the PlotQA source annotations). prep writes PNGs + GT JSON
to ~/media-data/charts and a manifest; nothing is committed.
usage: datasets.py prep N_SYNTH N_PLOTQA"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from common import DATA  # noqa: E402
from metrics import parse_number  # noqa: E402

OUT = os.path.join(DATA, "charts")
SUPPORTED_CHARTX = {"bar_chart", "bar_chart_num", "line_chart", "line_chart_num", "histogram", "area_chart",
                    "multi-axes", "3D-Bar", "bubble"}


def chartx_items():
    cx = os.path.join(DATA, "chartx")
    ann = json.load(open(os.path.join(cx, "ChartX_annotation_test.json"), encoding="utf-8"))
    if isinstance(ann, dict):
        ann = next(v for v in ann.values() if isinstance(v, list))
    pngs = {}
    for p in glob.glob(os.path.join(cx, "**", "*.png"), recursive=True):
        pngs.setdefault(os.path.basename(p), []).append(p)
    print("chartx keys", sorted(ann[0].keys()), "pngs", sum(len(v) for v in pngs.values()))
    items = []
    for k, a in enumerate(ann):
        ctype = a.get("chart_type") or a.get("type") or "?"
        img = a.get("img") or a.get("imgname") or ""
        cand = pngs.get(os.path.basename(img), [])
        if len(cand) > 1:
            cand = [c for c in cand if ctype in c] or cand
        if not cand:
            continue
        csv = (a.get("csv") or "").replace("\\n", "\n").replace("\\t", "\t")
        rows = [[c.strip() for c in r.split("\t")] for r in csv.strip().split("\n") if r.strip()]
        if len(rows) < 2:
            continue
        head = rows[0]
        series = []
        for j in range(1, len(head)):
            xs, ys = [], []
            for r in rows[1:]:
                if j < len(r):
                    v = parse_number(r[j])
                    if v is not None:
                        xs.append(r[0])
                        ys.append(v)
            series.append({"name": head[j], "x": xs, "y": ys})
        gt = {"id": f"chartx:{k}", "type": ctype, "x_kind": "cat", "series": series}
        items.append({"id": gt["id"], "ds": "chartx", "ctype": ctype, "img": cand[0], "gt": gt,
                      "group": gt["id"], "supported": ctype in SUPPORTED_CHARTX})
    return items


def parse_donut(s):
    """Donut json2token string -> python object (dicts from <s_k>..</s_k>, lists split on top-level <sep/>)."""
    toks = re.findall(r"<s_[^>]+>|</s_[^>]+>|<sep/>|[^<]+|<", s)
    pos = 0

    def parse_seq(end):
        nonlocal pos
        items, cur, text = [], {}, ""
        while pos < len(toks):
            t = toks[pos]
            if end and t == end:
                pos += 1
                break
            if t.startswith("<s_"):
                k = t[3:-1]
                pos += 1
                cur[k] = parse_seq(f"</s_{k}>")
            elif t == "<sep/>":
                pos += 1
                items.append(cur if cur else text.strip())
                cur, text = {}, ""
            elif t.startswith("</s_"):
                pos += 1
            else:
                text += t
                pos += 1
        last = cur if cur else text.strip()
        if items:
            items.append(last)
            return items
        return last
    return parse_seq(None)


def plotqa_items(n):
    import pyarrow.parquet as pq
    from PIL import Image
    files = sorted(glob.glob(os.path.join(DATA, "plotqa", "**", "*.parquet"), recursive=True))
    pf = pq.ParquetFile(files[0])
    total = pf.metadata.num_rows
    step = max(1, total // n)
    items, r = [], 0
    os.makedirs(os.path.join(OUT, "plotqa"), exist_ok=True)
    for b in pf.iter_batches(batch_size=32, columns=["image", "text"]):
        for row in b.to_pylist():
            if r % step == 0 and len(items) < n:
                d = parse_donut(row["text"])
                d = d if isinstance(d, dict) else {}
                if not items:
                    print("plotqa sample keys", sorted(d.keys()), str(d)[:300])
                models = d.get("models", [])
                if isinstance(models, dict):
                    models = [models]
                series = []
                for m in models:
                    if not isinstance(m, dict):
                        continue
                    xs = m.get("x", [])
                    ys = m.get("y", [])
                    xs = xs if isinstance(xs, list) else [xs]
                    ys = ys if isinstance(ys, list) else [ys]
                    yv = [parse_number(v) for v in ys]
                    pairs = [(str(x), y) for x, y in zip(xs, yv) if y is not None]
                    series.append({"name": str(m.get("label") or m.get("name") or ""), "color": None,
                                   "x": [p[0] for p in pairs], "y": [p[1] for p in pairs]})
                ctype = str(d.get("type", "?"))
                img = row["image"]
                path = os.path.join(OUT, "plotqa", f"{r}.png")
                Image.open(io.BytesIO(img["bytes"] if isinstance(img, dict) else img)).convert("RGB").save(path)
                gt = {"id": f"plotqa:{r}", "type": ctype, "x_kind": "cat", "series": series}
                items.append({"id": gt["id"], "ds": "plotqa", "ctype": ctype, "img": path, "gt": gt,
                              "group": gt["id"], "supported": True})
            r += 1
        if len(items) >= n:
            break
    return items


def synth_items(n):
    import gen_vector
    d = os.path.join(OUT, "synth")
    os.makedirs(d, exist_ok=True)
    for i in range(n):
        if not os.path.exists(os.path.join(d, f"vec{i:04d}.json")):
            gen_vector.make(i, d)
    items = []
    import cv2
    for i in range(n):
        base = os.path.join(d, f"vec{i:04d}")
        gt = json.load(open(base + ".json"))
        im = cv2.imread(base + "_100.png")
        cv2.imwrite(base + "_jpeg.jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 30])
        for var, path in (("vector", base + ".pdf"), ("raster_100", base + "_100.png"),
                          ("raster_150", base + "_150.png"), ("raster_jpeg", base + "_jpeg.jpg")):
            items.append({"id": f"{gt['id']}:{var}", "ds": "synth", "var": var, "ctype": gt["type"], "path": path,
                          "gt": gt, "group": gt["id"], "supported": True})
    return items


def prep(n_synth, n_plotqa):
    items = synth_items(n_synth) + chartx_items() + plotqa_items(n_plotqa)
    for it in items:
        if "img" in it:
            it["path"] = it.pop("img")
            it["var"] = "raster"
    json.dump(items, open(os.path.join(OUT, "manifest.json"), "w"))
    from collections import Counter
    print(len(items), Counter((i["ds"], i.get("var")) for i in items))
    print(Counter(i["ctype"] for i in items if i["ds"] != "synth"))


def load():
    return json.load(open(os.path.join(OUT, "manifest.json")))


if __name__ == "__main__":
    if sys.argv[1] == "prep":
        prep(int(sys.argv[2]), int(sys.argv[3]))

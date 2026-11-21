"""ChartDetective-style vector chart extraction (idea from m-damien/ChartDetective, BSD-2-Clause; this is our own
automatic implementation): read PDF drawing objects with pdfplumber, calibrate axes from numeric tick text
(snapped to drawn tick marks when present) with a linear or log fit that must agree with every extra tick,
then turn filled rectangles, stroked polylines and repeated small markers into series by colour; legend
swatches next to text give the series names; abstain when the geometry and the ticks do not agree."""
import math
from collections import defaultdict

from metrics import parse_number, to_hex

GRAY_TOL = 18


def col(c):
    try:
        if c is None:
            return None
        if isinstance(c, (int, float)):
            c = (c,)
        c = [float(v) for v in c]
        if len(c) == 1:
            rgb = (c[0], c[0], c[0])
        elif len(c) == 3:
            rgb = tuple(c)
        elif len(c) == 4:
            k = c[3]
            rgb = tuple((1 - v) * (1 - k) for v in c[:3])
        else:
            return None
        return to_hex([v * 255 for v in rgb])
    except (TypeError, ValueError):
        return None


def is_grayish(h):
    if h is None:
        return True
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return max(r, g, b) - min(r, g, b) < GRAY_TOL


def is_white(h):
    if h is None:
        return True
    return all(int(h[i:i + 2], 16) > 235 for i in (1, 3, 5))


def fit(pairs, allow_log=True):
    """pairs [(pos, value)] -> (fn pos->value, kind, max residual in pos units) or None."""
    if len(pairs) < 2:
        return None
    best = None
    for kind in ("lin", "log"):
        if kind == "log" and (not allow_log or any(v <= 0 for _, v in pairs)):
            continue
        xs = [p for p, _ in pairs]
        ys = [v if kind == "lin" else math.log10(v) for _, v in pairs]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        if sxx < 1e-9:
            continue
        a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
        if abs(a) < 1e-12:
            continue
        b = my - a * mx
        res = max(abs((y - b) / a - x) for x, y in zip(xs, ys))
        if best is None or res < best[2]:
            best = (a, b, res, kind)
    if best is None:
        return None
    a, b, res, kind = best
    if kind == "lin":
        return (lambda p: a * p + b), kind, res, (lambda v: (v - b) / a)
    return (lambda p: 10 ** (a * p + b)), kind, res, (lambda v: (math.log10(v) - b) / a if v > 0 else None)


def words_of(page):
    ws = page.extract_words(extra_attrs=["size"], keep_blank_chars=False, use_text_flow=False, x_tolerance=1.2)
    for w in ws:
        w["cx"], w["cy"] = (w["x0"] + w["x1"]) / 2, (w["top"] + w["bottom"]) / 2
    out, used = [], set()
    for i, w in enumerate(ws):
        if i in used:
            continue
        if w["text"] in ("10", "−10", "-10"):
            for j, e in enumerate(ws):
                if j != i and j not in used and e["size"] < 0.85 * w["size"] and 0 <= e["x0"] - w["x1"] < 2.5 \
                        and e["bottom"] <= w["cy"] + 1 and parse_number(e["text"]) is not None:
                    w = dict(w, text=f"1e{parse_number(e['text']):g}", x1=e["x1"], exp=True)
                    w["cx"] = (w["x0"] + w["x1"]) / 2
                    used.add(j)
                    break
        out.append(w)
    return out


def tick_value(text):
    if text.startswith("1e"):
        try:
            return 10 ** float(text[2:])
        except ValueError:
            return None
    return parse_number(text)


def segments(page):
    segs = []
    for o in list(page.lines) + list(page.curves):
        pts = o.get("pts") or [(o["x0"], o["top"]), (o["x1"], o["bottom"])]
        segs.append({"pts": [(float(x), float(y)) for x, y in pts], "color": col(o.get("stroking_color")),
                     "fill": col(o.get("non_stroking_color")) if o.get("fill") else None,
                     "x0": o["x0"], "x1": o["x1"], "top": o["top"], "bottom": o["bottom"], "kind": o["object_type"]})
    return segs


def plot_area(page, rects, segs):
    W, H = float(page.width), float(page.height)
    cands = [r for r in rects if (r["x1"] - r["x0"]) > 0.3 * W and (r["bottom"] - r["top"]) > 0.25 * H
             and not ((r["x1"] - r["x0"]) > 0.97 * W and (r["bottom"] - r["top"]) > 0.97 * H)
             and (not r.get("fill") or is_white(col(r.get("non_stroking_color"))))]
    if cands:
        r = max(cands, key=lambda r: (r["x1"] - r["x0"]) * (r["bottom"] - r["top"]))
        return [r["x0"], r["top"], r["x1"], r["bottom"]]
    hs = [s for s in segs if len(s["pts"]) == 2 and abs(s["pts"][0][1] - s["pts"][1][1]) < 0.3
          and abs(s["pts"][0][0] - s["pts"][1][0]) > 0.25 * W and not is_white(s["color"])]
    vs = [s for s in segs if len(s["pts"]) == 2 and abs(s["pts"][0][0] - s["pts"][1][0]) < 0.3
          and abs(s["pts"][0][1] - s["pts"][1][1]) > 0.2 * H and not is_white(s["color"])]
    if hs and vs:
        x0 = min(s["x0"] for s in vs)
        x1 = max(max(s["x1"] for s in hs), max(s["x1"] for s in vs))
        y1 = max(s["bottom"] for s in hs)
        y0 = min(min(s["top"] for s in vs), min(s["top"] for s in hs))
        return [x0, y0, x1, y1]
    return None


def axis_ticks(words, area, axis):
    x0, y0, x1, y1 = area
    if axis == "y":
        c = [w for w in words if w["x1"] <= x0 + 1.5 and y0 - 4 <= w["cy"] <= y1 + 4 and w["x0"] > x0 - 120]
        if not c:
            return [], []
        right = max(w["x1"] for w in c)
        c = [w for w in c if right - w["x1"] < 6]
    else:
        c = [w for w in words if y1 - 1.5 <= w["top"] <= y1 + 30 and x0 - 6 <= w["cx"] <= x1 + 6]
        if not c:
            return [], []
        top = min(w["top"] for w in c)
        c = [w for w in c if w["top"] - top < 6 or w.get("upright") is False]
    num = [w for w in c if tick_value(w["text"]) is not None and not w["text"].isalpha()]
    return num, c


def snap(ticks, segs, area, axis):
    x0, y0, x1, y1 = area
    marks = []
    for s in segs:
        if len(s["pts"]) != 2:
            continue
        (ax, ay), (bx, by) = s["pts"]
        L = math.hypot(bx - ax, by - ay)
        if not 1.0 <= L <= 9:
            continue
        if axis == "y" and abs(ay - by) < 0.3 and min(abs(ax - x0), abs(bx - x0)) < 1.5:
            marks.append((ay + by) / 2)
        if axis == "x" and abs(ax - bx) < 0.3 and min(abs(ay - y1), abs(by - y1)) < 1.5:
            marks.append((ax + bx) / 2)
    out = []
    for w in ticks:
        c = w["cy"] if axis == "y" else w["cx"]
        near = [m for m in marks if abs(m - c) < 4.0]
        out.append(min(near, key=lambda m: abs(m - c)) if near else c)
    return out, bool(marks)


def calibrate(words, segs, area, axis):
    ticks, alltxt = axis_ticks(words, area, axis)
    if len(ticks) < 2:
        return None, alltxt
    pos, snapped = snap(ticks, segs, area, axis)
    pairs = sorted({(round(p, 2), tick_value(w["text"])) for p, w in zip(pos, ticks)})
    f = fit(pairs)
    if f is None:
        return None, alltxt
    fn, kind, res, inv = f
    span = abs(pairs[-1][0] - pairs[0][0]) or 1.0
    if len(pairs) >= 3 and res > max(1.5, 0.02 * span):
        return {"error": f"ticks disagree ({res:.1f} pt)"}, alltxt
    return {"fn": fn, "inv": inv, "kind": kind, "res": res, "n": len(pairs), "snapped": snapped}, alltxt


def legend(words, rects, segs):
    """Swatch (small filled rect or short stroked segment) immediately left of a text label -> colour: name."""
    sw = []
    for r in rects:
        w, h = r["x1"] - r["x0"], r["bottom"] - r["top"]
        if 2 <= w <= 30 and 1 <= h <= 14:
            sw.append((r["x0"], r["top"], r["x1"], r["bottom"], col(r.get("non_stroking_color"))))
    for s in segs:
        if len(s["pts"]) == 2 and abs(s["pts"][0][1] - s["pts"][1][1]) < 0.3 and 6 <= abs(s["pts"][0][0] - s["pts"][1][0]) <= 30:
            sw.append((s["x0"], s["top"] - 1, s["x1"], s["bottom"] + 1, s["color"]))
        elif len(s["pts"]) > 2 and (s["x1"] - s["x0"]) < 10 and (s["bottom"] - s["top"]) < 10 and s["fill"]:
            sw.append((s["x0"], s["top"], s["x1"], s["bottom"], s["fill"]))
    out, boxes = {}, []
    for x0, t, x1, b, c in sw:
        if c is None or is_white(c):
            continue
        cy = (t + b) / 2
        right = sorted([w for w in words if 0.5 <= w["x0"] - x1 <= 14 and abs(w["cy"] - cy) < 0.6 * w["size"]],
                       key=lambda w: w["x0"])
        if not right:
            continue
        name = [right[0]]
        for w in right[1:]:
            if w["x0"] - name[-1]["x1"] < 0.6 * w["size"]:
                name.append(w)
            else:
                break
        if c not in out:
            out[c] = " ".join(w["text"] for w in name)
            boxes.append((x0 - 1, min(t, name[0]["top"]) - 1, name[-1]["x1"] + 1, max(b, name[0]["bottom"]) + 1))
    return out, boxes


def inside(b, area, tol=1.5):
    return b[0] >= area[0] - tol and b[2] <= area[2] + tol and b[1] >= area[1] - tol and b[3] <= area[3] + tol


def extract(pdf_path):
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        rects = list(page.rects)
        segs = segments(page)
        words = words_of(page)
        area = plot_area(page, rects, segs)
        if area is None:
            return {"abstain": "no plot area"}
        ycal, ytxt = calibrate(words, segs, area, "y")
        xcal, xtxt = calibrate(words, segs, area, "x")
        if ycal and "error" in ycal:
            ycal = None
        if xcal and "error" in xcal:
            xcal = None
        names, lboxes = legend(words, rects, segs)

        def not_legend(b):
            return not any(b[0] >= lb[0] - 1 and b[2] <= lb[2] + 1 and b[1] >= lb[1] - 1 and b[3] <= lb[3] + 1 for lb in lboxes)
        bars = []
        for r in rects:
            b = (r["x0"], r["top"], r["x1"], r["bottom"])
            c = col(r.get("non_stroking_color"))
            if not r.get("fill") or c is None or is_white(c) or is_grayish(c):
                continue
            if (b[2] - b[0]) < 0.3 or (b[3] - b[1]) < 0.05 or not inside(b, area) or not not_legend(b):
                continue
            if (b[2] - b[0]) > 0.95 * (area[2] - area[0]) and (b[3] - b[1]) > 0.95 * (area[3] - area[1]):
                continue
            bars.append((b, c))
        lines, marks = [], []
        pw, ph = area[2] - area[0], area[3] - area[1]
        for s in segs:
            b = (s["x0"], s["top"], s["x1"], s["bottom"])
            if not inside(b, area, 2.5) or not not_legend(b):
                continue
            small = (b[2] - b[0]) < 0.04 * pw and (b[3] - b[1]) < 0.04 * ph
            if small and len(s["pts"]) >= 3 and (s["fill"] or s["color"]):
                c = s["fill"] if s["fill"] and not is_white(s["fill"]) else s["color"]
                if c and not is_grayish(c):
                    marks.append((((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), c))
                continue
            c = s["color"]
            if c is None or is_grayish(c) or is_white(c) or len(s["pts"]) < 2:
                continue
            lines.append((s["pts"], c))
        for r in rects:
            b = (r["x0"], r["top"], r["x1"], r["bottom"])
            c = col(r.get("non_stroking_color"))
            if r.get("fill") and c and not is_grayish(c) and (b[2] - b[0]) < 0.04 * pw and (b[3] - b[1]) < 0.04 * ph \
                    and inside(b, area) and not_legend(b) and abs((b[2] - b[0]) - (b[3] - b[1])) < 0.5:
                marks.append((((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), c))
        series = defaultdict(lambda: {"x": [], "y": [], "xi": []})
        if bars and len(bars) >= max(1, len(lines)):
            def mode_count(vals):
                vals = sorted(round(v * 2) / 2 for v in vals)
                best = cur = 1
                for a, b in zip(vals, vals[1:]):
                    cur = cur + 1 if a == b else 1
                    best = max(best, cur)
                return best
            vert = max(mode_count([b[3] for b, _ in bars]), mode_count([b[1] for b, _ in bars]))
            hori = max(mode_count([b[0] for b, _ in bars]), mode_count([b[2] for b, _ in bars]))
            if hori > vert:
                if xcal is None:
                    return {"abstain": "horizontal bars without a calibrated value axis"}
                cal, catw, axis = xcal, sorted(ytxt, key=lambda w: w["cy"]), "h"
            else:
                if ycal is None:
                    return {"abstain": "bars without a calibrated value axis"}
                cal, catw, axis = ycal, sorted(xtxt, key=lambda w: w["cx"]), "v"
            z = cal["inv"](0.0) if cal["kind"] == "lin" else None
            for b, c in bars:
                if axis == "v":
                    lo, hi = b[3], b[1]
                    center = (b[0] + b[2]) / 2
                else:
                    lo, hi = b[0], b[2]
                    center = (b[1] + b[3]) / 2
                if cal["kind"] == "log":
                    v = cal["fn"](hi)
                else:
                    near, far = (lo, hi) if z is None or abs(lo - z) <= abs(hi - z) else (hi, lo)
                    v = cal["fn"](far) - cal["fn"](near)
                if catw:
                    k = min(range(len(catw)), key=lambda k: abs((catw[k]["cx"] if axis == "v" else catw[k]["cy"]) - center))
                    if axis == "h":
                        k_lab = catw[k]["text"]
                    else:
                        k_lab = catw[k]["text"]
                    series[c]["x"].append(k_lab)
                    series[c]["xi"].append(k if axis == "v" else len(catw) - 1 - k)
                else:
                    series[c]["x"].append(f"{center:.0f}")
                    series[c]["xi"].append(None)
                series[c]["y"].append(v)
                series[c]["pos"] = series[c].get("pos", []) + [center]
            kind = "bar"
        elif lines or marks:
            if ycal is None:
                return {"abstain": "no calibrated y axis"}
            catw = sorted(xtxt, key=lambda w: w["cx"])
            pts_by = defaultdict(list)
            for pts, c in lines:
                for p in pts:
                    pts_by[c].append(p)
            for p, c in marks:
                pts_by[c].append(p)
            allx = [p[0] for v in pts_by.values() for p in v]
            if len(catw) >= 2 and allx:
                sp = abs(catw[1]["cx"] - catw[0]["cx"])
                hit = sum(1 for x in allx if min(abs(w["cx"] - x) for w in catw) <= 0.25 * sp)
                if hit >= 0.9 * len(allx):
                    xcal = None
            if xcal is None and len(catw) < 2:
                return {"abstain": "x axis neither numeric nor categorical"}
            for c, pts in pts_by.items():
                seen = set()
                for x, y in sorted(pts):
                    key = (round(x, 1), round(y, 1))
                    if key in seen:
                        continue
                    seen.add(key)
                    if xcal is not None:
                        xv = xcal["fn"](x)
                        series[c]["x"].append(xv)
                        series[c]["xi"].append(None)
                    else:
                        k = min(range(len(catw)), key=lambda k: abs(catw[k]["cx"] - x))
                        sp = (catw[1]["cx"] - catw[0]["cx"]) if len(catw) > 1 else 1e9
                        if abs(catw[k]["cx"] - x) > 0.25 * abs(sp):
                            continue
                        series[c]["x"].append(catw[k]["text"])
                        series[c]["xi"].append(k)
                    series[c]["y"].append(ycal["fn"](y))
            kind = "line"
        else:
            return {"abstain": "no marks"}
        out = []
        for c, s in series.items():
            if not s["y"]:
                continue
            if kind == "line" and xcal is None:
                agg = {}
                for x, xi, y in zip(s["x"], s["xi"], s["y"]):
                    agg.setdefault((xi, x), []).append(y)
                items = sorted(agg.items(), key=lambda kv: kv[0][0])
                s = {"x": [k[1] for k, _ in items], "xi": [k[0] for k, _ in items],
                     "y": [sorted(v)[len(v) // 2] for _, v in items]}
            out.append({"name": names.get(c, ""), "color": c, "x": s["x"], "xi": s["xi"], "y": s["y"]})
        if not out:
            return {"abstain": "no series"}
        return {"series": out, "kind": kind, "ycal": (ycal or {}).get("kind"), "xcal": (xcal or {}).get("kind"),
                "snapped": bool((ycal or {}).get("snapped"))}

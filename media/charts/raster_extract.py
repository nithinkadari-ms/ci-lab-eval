"""Raster chart tracing in the style of figrecover (UBC-FRESH/figrecover, MIT: colour masks, column-wise median
for lines, x-runs for bars, connected components for scatter), made automatic: axes from long dark strokes,
calibration from PP-OCRv6 tick text (linear or log fit, extra ticks must agree), series colours by colour
quantisation of the plot area, names from legend swatches next to OCR text. Abstains when no consistent
calibration exists or the marks are ambiguous."""
import cv2
import numpy as np

from metrics import parse_number, to_hex
from vector_extract import fit


def ocr_texts(rgb, det, rec):
    import ppocr
    H, W = rgb.shape[:2]
    f = 2.0 if max(H, W) < 900 else 1.0
    im = cv2.resize(rgb, (int(W * f), int(H * f)), interpolation=cv2.INTER_CUBIC) if f != 1 else rgb
    boxes = det(im)
    crops = [ppocr.crop(im, b["quad"]) for b in boxes]
    out = []
    for b, c in zip(boxes, crops):
        if c is None:
            continue
        t, conf = rec.one(c)
        if t and conf >= ppocr.TEXT_SCORE:
            x0, y0, x1, y1 = [v / f for v in b["box"]]
            out.append({"t": t, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "cx": (x0 + x1) / 2, "cy": (y0 + y1) / 2})
    return out


def axes(rgb):
    H, W = rgb.shape[:2]
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    dark = (g < 110).astype(np.uint8)
    hk = cv2.morphologyEx(dark, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(15, int(0.3 * W)), 1)))
    vk = cv2.morphologyEx(dark, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(15, int(0.3 * H)))))
    rows = [y for y in range(H) if hk[y].sum() > 0.3 * W and y > 0.35 * H]
    cols = [x for x in range(W) if vk[:, x].sum() > 0.3 * H and x < 0.5 * W]
    if not rows or not cols:
        return None
    y1 = max(rows)
    x0 = min(cols)
    xs = np.where(hk[y1] > 0)[0]
    ys = np.where(vk[:, x0] > 0)[0]
    x1 = int(xs.max()) if xs.size else W - 1
    y0 = int(ys.min()) if ys.size else 0
    if x1 - x0 < 0.2 * W or y1 - y0 < 0.2 * H:
        return None
    return [int(x0), int(y0), int(x1), int(y1)]


def colour_clusters(rgb, area, min_share=0.002):
    x0, y0, x1, y1 = area
    sub = rgb[y0 + 2:y1 - 1, x0 + 2:x1 - 1].astype(np.int32)
    if sub.size == 0:
        return [], None
    hsv = cv2.cvtColor(sub.astype(np.uint8), cv2.COLOR_RGB2HSV)
    colored = (hsv[:, :, 1] > 60) & (hsv[:, :, 2] > 40)
    q = (sub // 32)
    key = q[:, :, 0] * 64 + q[:, :, 1] * 8 + q[:, :, 2]
    ks, cnt = np.unique(key[colored], return_counts=True)
    tot = colored.size
    cents = []
    for k, c in sorted(zip(ks.tolist(), cnt.tolist()), key=lambda t: -t[1]):
        if c < min_share * tot:
            continue
        m = colored & (key == k)
        mean = sub[m].mean(axis=0)
        for cl in cents:
            if np.linalg.norm(cl["mean"] - mean) < 60:
                cl["keys"].append(k)
                break
        else:
            cents.append({"mean": mean, "keys": [k]})
    out = []
    for cl in cents:
        m = colored & np.isin(key, cl["keys"])
        full = np.zeros(rgb.shape[:2], dtype=np.uint8)
        full[y0 + 2:y1 - 1, x0 + 2:x1 - 1] = m.astype(np.uint8)
        out.append({"hex": to_hex(sub[m].mean(axis=0)), "mask": full})
    return out, colored


def calibrate(texts, area, axis):
    x0, y0, x1, y1 = area
    if axis == "y":
        c = [t for t in texts if t["x1"] <= x0 + 6 and y0 - 8 <= t["cy"] <= y1 + 8]
    else:
        c = [t for t in texts if y1 - 3 <= t["y0"] <= y1 + 60 and x0 - 8 <= t["cx"] <= x1 + 8]
    num = [(t["cy"] if axis == "y" else t["cx"], parse_number(t["t"])) for t in c]
    num = sorted({(round(p, 1), v) for p, v in num if v is not None})
    f = fit(num) if len(num) >= 2 else None
    if f is None:
        return None, c
    fn, kind, res, inv = f
    span = abs(num[-1][0] - num[0][0]) or 1.0
    if len(num) >= 3 and res > max(3.0, 0.03 * span):
        return None, c
    return {"fn": fn, "inv": inv, "kind": kind}, c


def runs(vals):
    out = []
    if not len(vals):
        return out
    s = p = vals[0]
    for v in vals[1:]:
        if v != p + 1:
            out.append((s, p))
            s = v
        p = v
    out.append((s, p))
    return out


def extract(rgb, det, rec):
    H, W = rgb.shape[:2]
    area = axes(rgb)
    if area is None:
        return {"abstain": "no axes"}
    texts = ocr_texts(rgb, det, rec)
    ycal, ytxt = calibrate(texts, area, "y")
    xcal, xtxt = calibrate(texts, area, "x")
    clusters, _ = colour_clusters(rgb, area)
    if not clusters:
        return {"abstain": "no coloured marks"}
    x0, y0, x1, y1 = area
    pa = (x1 - x0) * (y1 - y0)
    names = {}
    for cl in clusters:
        n, lab, st, cen = cv2.connectedComponentsWithStats(cl["mask"])
        keep = cl["mask"].copy()
        for k in range(1, n):
            x, y, w, h, a = st[k]
            if a > 0.01 * pa or h > 0.06 * H:
                continue
            right = [t for t in texts if 0 <= t["x0"] - (x + w) <= 3 * max(h, 6) and abs(t["cy"] - (y + h / 2)) < max(h, 8)]
            if right:
                names[cl["hex"]] = min(right, key=lambda t: t["x0"])["t"]
                keep[lab == k] = 0
        cl["mask"] = keep
    series = []
    xl = sorted(xtxt, key=lambda t: t["cx"])
    yl = sorted(ytxt, key=lambda t: t["cy"])
    for cl in clusters:
        m = cl["mask"]
        n, lab, st, cen = cv2.connectedComponentsWithStats(m)
        comps = [(st[k], cen[k]) for k in range(1, n) if st[k][4] >= 4]
        if not comps:
            continue
        big = [c for c in comps if c[0][4] > 0.002 * pa]
        fill = [c[0][4] / max(1, c[0][2] * c[0][3]) for c in big]
        s = {"name": names.get(cl["hex"], ""), "color": cl["hex"], "x": [], "y": [], "xi": []}
        if big and np.mean(fill) > 0.8 and len(big) >= 1:
            vert = sum(1 for c in big if abs(c[0][1] + c[0][3] - y1) < 4 or c[0][3] > c[0][2]) >= sum(
                1 for c in big if abs(c[0][0] - x0) < 4)
            cal, labs = (ycal, xl) if vert else (xcal, yl)
            if cal is None:
                continue
            z = cal["inv"](0.0) if cal["kind"] == "lin" else None
            ys_, xs_ = np.nonzero(m)
            occ = sorted(set((xs_ if vert else ys_).tolist()))
            for a, b in runs(occ):
                if b - a < 2:
                    continue
                sel = (xs_ >= a) & (xs_ <= b) if vert else (ys_ >= a) & (ys_ <= b)
                other = ys_[sel] if vert else xs_[sel]
                lo, hi = (other.max(), other.min()) if vert else (other.min(), other.max())
                if cal["kind"] == "log":
                    v = cal["fn"](hi)
                else:
                    near, far = (lo, hi) if z is None or abs(lo - z) <= abs(hi - z) else (hi, lo)
                    v = cal["fn"](far) - cal["fn"](near)
                c = (a + b) / 2
                if labs:
                    k = min(range(len(labs)), key=lambda k: abs((labs[k]["cx"] if vert else labs[k]["cy"]) - c))
                    s["x"].append(labs[k]["t"])
                    s["xi"].append(k if vert else len(labs) - 1 - k)
                else:
                    s["x"].append(f"{c:.0f}")
                    s["xi"].append(None)
                s["y"].append(v)
        else:
            if ycal is None:
                continue
            small = [c for c in comps if c[0][4] < 0.002 * pa]
            if len(small) >= 5 and len(small) >= 0.8 * len(comps) and xcal is not None:
                for stt, cc in small:
                    s["x"].append(xcal["fn"](cc[0]))
                    s["xi"].append(None)
                    s["y"].append(ycal["fn"](cc[1]))
            else:
                ys_, xs_ = np.nonzero(m)
                if xs_.size == 0:
                    continue
                cols = {}
                for x, y in zip(xs_.tolist(), ys_.tolist()):
                    cols.setdefault(x, []).append(y)
                if len(xl) >= 2:
                    for k, t in enumerate(xl):
                        xc = int(round(t["cx"]))
                        near = [x for x in range(xc - 2, xc + 3) if x in cols]
                        if not near:
                            continue
                        yv = float(np.median([y for x in near for y in cols[x]]))
                        s["x"].append(t["t"])
                        s["xi"].append(k)
                        s["y"].append(ycal["fn"](yv))
                elif xcal is not None:
                    for x in sorted(cols)[::2]:
                        s["x"].append(xcal["fn"](x))
                        s["xi"].append(None)
                        s["y"].append(ycal["fn"](float(np.median(cols[x]))))
        if s["y"]:
            series.append(s)
    if not series:
        return {"abstain": "no calibrated series"}
    return {"series": series, "ycal": (ycal or {}).get("kind"), "xcal": (xcal or {}).get("kind")}

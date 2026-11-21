"""Chart metrics. RMS precision/recall/F1 re-implemented from google-research/deplot/metrics.py (Apache-2.0):
datapoints "row header + column header" -> value, keys matched by Hungarian assignment on ANLS distance
(text_theta 0.5), value similarity 1 - min(1, |t-p|/|t|) cut at number_theta 0.1. Titles are not scored."""
import math
import re

import numpy as np
from rapidfuzz.distance import Levenshtein
from scipy.optimize import linear_sum_assignment

NUM_RE = re.compile(r"[-+−]?\d[\d,]*\.?\d*(?:[eE][-+]?\d+)?|[-+−]?\.\d+")


def parse_number(s):
    """'$1,200' -> 1200, '20%' -> 20, '1.5k' -> 1500, '3M' -> 3e6, '−4' -> -4; None if no number."""
    if s is None:
        return None
    t = str(s).strip().replace("−", "-").replace(" ", "")
    if not t:
        return None
    m = NUM_RE.search(t)
    if not m:
        return None
    try:
        v = float(m.group(0).replace(",", "").replace("−", "-"))
    except ValueError:
        return None
    tail = t[m.end():m.end() + 1].lower()
    if tail == "k":
        v *= 1e3
    elif tail == "m":
        v *= 1e6
    elif tail == "b":
        v *= 1e9
    if t.startswith("(") and t.endswith(")"):
        v = -abs(v)
    return v


def anls(t, p, theta=0.5):
    t, p = str(t).lower().strip(), str(p).lower().strip()
    if not t and not p:
        return 1.0
    d = Levenshtein.distance(t, p) / max(len(t), len(p), 1)
    return 1.0 - d if d < theta else 0.0


def rel_dist(t, p, theta=1.0):
    if not t:
        return float(not p)
    d = min(abs((t - p) / t), 1.0)
    return d if d < theta else 1.0


def datapoints(series, categories=None):
    """series: [{name, x, y}] -> [(key, value)] with key = '<x> <series name>' as DePlot builds them."""
    out = []
    for s in series:
        for x, y in zip(s["x"], s["y"]):
            if y is None:
                continue
            xk = x if isinstance(x, str) else f"{x:g}"
            out.append((f"{xk} {s.get('name') or ''}".strip(), y))
    return out


def rms(target, pred, text_theta=0.5, number_theta=0.1):
    T = datapoints(target)
    Pp = datapoints(pred)
    if not T and not Pp:
        return 1.0, 1.0, 1.0
    if not T:
        return 0.0, 1.0, 0.0
    if not Pp:
        return 1.0, 0.0, 0.0
    cost = np.array([[1 - anls(t, p, text_theta) for p, _ in Pp] for t, _ in T])
    ri, ci = linear_sum_assignment(cost)
    score = 0.0
    for r, c in zip(ri, ci):
        k = anls(T[r][0], Pp[c][0], text_theta)
        tv, pv = T[r][1], Pp[c][1]
        if isinstance(tv, (int, float)) and isinstance(pv, (int, float)) and tv:
            score += k * (1 - rel_dist(float(tv), float(pv), number_theta))
        elif tv == pv:
            score += k
    if score == 0:
        return 0.0, 0.0, 0.0
    P = score / len(Pp)
    R = score / len(T)
    return P, R, 2 * P * R / (P + R)


def point_errors(gt, pred):
    """Synthetic charts: series matched by colour, points by category index or nearest x.
    Returns list of relative errors |p-t|/max(|t|, eps) for every GT point (missing point -> None)."""
    errs = []
    span = max((abs(v) for s in gt["series"] for v in s["y"]), default=1.0) or 1.0
    for s in gt["series"]:
        ps = [q for q in pred.get("series", []) if q.get("color") and color_close(q["color"], s["color"])]
        q = ps[0] if ps else None
        for k, (x, y) in enumerate(zip(s["x"], s["y"])):
            if q is None:
                errs.append(None)
                continue
            v = None
            if gt.get("x_kind") == "cat":
                if x in q["x"]:
                    v = q["y"][q["x"].index(x)]
                elif "xi" in q and k in q["xi"]:
                    v = q["y"][q["xi"].index(k)]
            else:
                cand = [(abs(float(px) - float(x)), py) for px, py in zip(q["x"], q["y"]) if isinstance(px, (int, float))]
                xr = max(1e-9, max(float(v_) for v_ in s["x"]) - min(float(v_) for v_ in s["x"]))
                if cand:
                    d, py = min(cand, key=lambda c: c[0])
                    if d <= 0.02 * xr:
                        v = py
            if v is None:
                errs.append(None)
            else:
                errs.append(abs(v - y) / max(abs(y), 0.01 * span))
    return errs


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def color_close(a, b, tol=40):
    ra, rb = hexrgb(a), hexrgb(b)
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(ra, rb))) <= tol


def to_hex(rgb):
    return "#%02x%02x%02x" % tuple(int(max(0, min(255, round(v)))) for v in rgb)


def table_text_to_series(text):
    """DePlot output 'TITLE | t <0x0A> h1 | h2 <0x0A> r | v' -> series list (columns = series)."""
    lines = [l.strip() for l in text.replace("<0x0A>", "\n").split("\n") if l.strip()]
    if lines and lines[0].lower().startswith("title"):
        lines = lines[1:]
    if len(lines) < 2:
        return []
    head = [c.strip() for c in lines[0].split("|")]
    rows = [[c.strip() for c in l.split("|")] for l in lines[1:]]
    out = []
    for j in range(1, len(head)):
        xs, ys = [], []
        for r in rows:
            if j < len(r):
                v = parse_number(r[j])
                if v is not None:
                    xs.append(r[0])
                    ys.append(v)
        out.append({"name": head[j], "x": xs, "y": ys})
    return out

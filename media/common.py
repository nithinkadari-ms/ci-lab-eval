"""Shared helpers for the round-4 media tests: text metrics, document-grouped splits, paired statistics."""
import hashlib
import json
import math
import os
import random
import re

from rapidfuzz.distance import Levenshtein

HOME = os.path.expanduser("~")
DATA = os.environ.get("MEDIA_DATA", os.path.join(HOME, "media-data"))
MODELS = os.environ.get("MEDIA_MODELS", os.path.join(HOME, "media-models"))

_Q = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
                    "−": "-", " ": " ", "‐": "-", "‑": "-", "，": ",", "：": ":",
                    "（": "(", "）": ")", "．": "."})


def norm_text(s):
    s = (s or "").translate(_Q)
    return re.sub(r"\s+", " ", s).strip()


def edits(a, b):
    return Levenshtein.distance(a, b)


def word_edits(pred, gt):
    p, g = norm_text(pred).split(), norm_text(gt).split()
    return Levenshtein.distance(p, g), len(g)


def is_num(tok):
    return any(c.isdigit() for c in tok)


def num_tokens(s):
    return [t.strip(".,;:()[]") for t in norm_text(s).split() if is_num(t)]


def bag_f1(pred_tokens, gt_tokens):
    from collections import Counter
    p, g = Counter(pred_tokens), Counter(gt_tokens)
    hit = sum((p & g).values())
    P = hit / max(1, sum(p.values()))
    R = hit / max(1, sum(g.values()))
    return hit, sum(p.values()), sum(g.values()), (2 * P * R / (P + R) if P + R else 0.0)


def split_of(group, test_share=0.5, salt="r4"):
    h = int(hashlib.md5((salt + ":" + str(group)).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "test" if h < test_share else "dev"


def shard(items, k, n):
    return [x for i, x in enumerate(items) if i % n == k]


def sign_test(diffs):
    """diffs: per-group (candidate - baseline) where positive = candidate better. Two-sided binomial on non-ties."""
    from scipy.stats import binomtest
    w = sum(1 for d in diffs if d > 1e-12)
    l = sum(1 for d in diffs if d < -1e-12)
    p = binomtest(w, w + l).pvalue if w + l else 1.0
    return w, l, p


def boot_ci(diffs, n=2000, seed=0):
    if not diffs:
        return (float("nan"), float("nan"))
    r = random.Random(seed)
    m = len(diffs)
    means = sorted(sum(diffs[r.randrange(m)] for _ in range(m)) / m for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n) - 1]


def jl_read(paths):
    out = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        pass
    return out


def fmt(v, nd=3):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "-"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def pfmt(p):
    if p is None:
        return "-"
    return f"{p:.1e}" if p < 0.001 else f"{p:.3f}"


def peak_rss_mb():
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

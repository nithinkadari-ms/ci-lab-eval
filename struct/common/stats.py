import hashlib
import math
import random


def split_of(group, dev_mod=5):
    h = int(hashlib.sha1(str(group).encode()).hexdigest()[:8], 16)
    return "dev" if h % dev_mod == 0 else "test"


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (p, max(0.0, c - h), min(1.0, c + h))


def ratio(num, den):
    return num / den if den else float("nan")


def f1(tp, np_, ng):
    p, r = ratio(tp, np_), ratio(tp, ng)
    if np_ == 0 and ng == 0:
        return p, r, float("nan")
    p0 = p if p == p else 0.0
    r0 = r if r == r else 0.0
    return p, r, (2 * p0 * r0 / (p0 + r0)) if p0 + r0 > 0 else 0.0


def micro_f1(recs, tp="tp", np_="np", ng="ng"):
    return f1(sum(r[tp] for r in recs), sum(r[np_] for r in recs), sum(r[ng] for r in recs))[2]


def boot(recs, fn, B=2000, seed=0):
    n = len(recs)
    if n == 0:
        return (float("nan"),) * 3
    rng = random.Random(seed)
    v = fn(recs)
    xs = []
    for _ in range(B):
        s = [recs[rng.randrange(n)] for _ in range(n)]
        x = fn(s)
        if x == x:
            xs.append(x)
    xs.sort()
    if not xs:
        return (v, float("nan"), float("nan"))
    return (v, xs[int(0.025 * len(xs))], xs[min(len(xs) - 1, int(0.975 * len(xs)))])


def paired(recs, fa, fb, B=2000, seed=0):
    n = len(recs)
    if n == 0:
        return dict(a=float("nan"), b=float("nan"), diff=float("nan"), lo=float("nan"), hi=float("nan"), p=float("nan"), n=0)
    rng = random.Random(seed)
    a, b = fa(recs), fb(recs)
    ds = []
    for _ in range(B):
        s = [recs[rng.randrange(n)] for _ in range(n)]
        x = fb(s) - fa(s)
        if x == x:
            ds.append(x)
    ds.sort()
    if not ds:
        return dict(a=a, b=b, diff=b - a, lo=float("nan"), hi=float("nan"), p=float("nan"), n=n)
    le = sum(1 for x in ds if x <= 0) / len(ds)
    ge = sum(1 for x in ds if x >= 0) / len(ds)
    return dict(a=a, b=b, diff=b - a, lo=ds[int(0.025 * len(ds))], hi=ds[min(len(ds) - 1, int(0.975 * len(ds)))],
                p=min(1.0, 2 * min(le, ge)), n=n)


def fmt(x, d=3):
    if x is None:
        return "-"
    if isinstance(x, float):
        if x != x:
            return "-"
        return f"{x:.{d}f}"
    return str(x)


def ci(t, d=3):
    v, lo, hi = t
    return f"{fmt(v, d)} [{fmt(lo, d)}, {fmt(hi, d)}]"


def pct(values, q):
    v = sorted(x for x in values if x == x)
    if not v:
        return float("nan")
    return v[min(len(v) - 1, int(q * (len(v) - 1) + 0.5))]

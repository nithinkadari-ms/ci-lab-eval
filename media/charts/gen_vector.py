"""Vector chart PDFs (and raster renders of the same figures) drawn by matplotlib from known data.
Types cover bar, grouped, stacked, horizontal, negative bars, line, line with markers, dense line, scatter and
log-y. Tick formats vary ($, %, k suffix, thousands separators), fonts are embedded as TrueType (42) or Type 3.
usage: gen_vector.py OUTDIR N"""
import json
import os
import random
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#17becf", "#bcbd22"]
TYPES = ["bar", "grouped_bar", "stacked_bar", "hbar", "neg_bar", "line", "line_markers", "dense_line", "scatter",
         "log_line"]
CATS = [["Q1", "Q2", "Q3", "Q4"], ["North", "South", "East", "West", "Central"],
        ["2018", "2019", "2020", "2021", "2022", "2023"], ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"],
        ["Retail", "Energy", "Health", "Finance", "Tech", "Media", "Transport"],
        ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]]
SERIES = ["Revenue", "Costs", "Profit", "Forecast", "Actual", "Budget", "Group A", "Group B", "Group C"]


def fmt_for(r):
    k = r.randrange(5)
    if k == 0:
        return "plain", 1.0, None
    if k == 1:
        return "dollar", 1000.0, FuncFormatter(lambda v, _: f"${v:,.0f}")
    if k == 2:
        return "percent", 1.0, FuncFormatter(lambda v, _: f"{v:.0f}%")
    if k == 3:
        return "ksuffix", 1000.0, FuncFormatter(lambda v, _: f"{v / 1000:g}k")
    return "decimal", 0.01, None


def make(i, outdir):
    r = random.Random(5000 + i)
    t = TYPES[i % len(TYPES)]
    fonttype = 42 if i % 3 else 3
    plt.rcParams.update({"pdf.fonttype": fonttype, "font.size": r.choice([8, 9, 10, 11]),
                         "font.family": r.choice(["DejaVu Sans", "DejaVu Serif"])})
    fig, ax = plt.subplots(figsize=(r.uniform(4.2, 7.0), r.uniform(3.0, 4.8)))
    fmt_name, scale, formatter = fmt_for(r)
    if t == "log_line":
        fmt_name, scale, formatter = "log", 1.0, None
    nser = {"bar": 1, "hbar": 1, "neg_bar": 1, "grouped_bar": r.randint(2, 4), "stacked_bar": r.randint(2, 3),
            "line": r.randint(1, 3), "line_markers": r.randint(1, 3), "dense_line": r.randint(1, 2),
            "scatter": r.randint(1, 3), "log_line": r.randint(1, 2)}[t]
    names = r.sample(SERIES, nser)
    colors = r.sample(PALETTE, nser)
    gt = {"id": f"vec{i:04d}", "type": t, "fonttype": fonttype, "fmt": fmt_name, "series": []}
    if t in ("scatter", "dense_line"):
        n = r.randint(15, 40) if t == "scatter" else r.randint(40, 90)
        x_kind = "num"
        for nm, c in zip(names, colors):
            if t == "scatter":
                xs = sorted(round(r.uniform(0, 100), 2) for _ in range(n))
                ys = [round(r.uniform(5, 95) * scale, 2) for _ in xs]
                ax.scatter(xs, ys, color=c, s=r.choice([12, 20, 30]), label=nm,
                           marker=r.choice(["o", "s", "^"]))
            else:
                xs = list(range(n))
                v = r.uniform(20, 80)
                ys = []
                for _ in xs:
                    v = max(1, v + r.uniform(-6, 6))
                    ys.append(round(v * scale, 2))
                ax.plot(xs, ys, color=c, label=nm, linewidth=r.choice([1.0, 1.5]))
            gt["series"].append({"name": nm, "color": c, "x": xs, "y": ys})
        gt["categories"] = None
    else:
        cats = r.choice(CATS)
        x_kind = "cat"
        gt["categories"] = cats
        pos = list(range(len(cats)))
        bottom = [0.0] * len(cats)
        width = 0.8 / nser if t == "grouped_bar" else r.uniform(0.5, 0.8)
        for k, (nm, c) in enumerate(zip(names, colors)):
            if t == "log_line":
                ys = [round(10 ** r.uniform(0, 5), 1) for _ in cats]
            elif t == "neg_bar":
                ys = [round(r.uniform(-60, 80) * scale, 1) for _ in cats]
            else:
                ys = [round(r.uniform(5, 100) * scale, 1) for _ in cats]
            if t in ("bar", "neg_bar"):
                ax.bar(pos, ys, width=width, color=c, label=nm)
            elif t == "grouped_bar":
                ax.bar([p - 0.4 + width * (k + 0.5) for p in pos], ys, width=width, color=c, label=nm)
            elif t == "stacked_bar":
                ax.bar(pos, ys, width=width, bottom=bottom, color=c, label=nm)
                bottom = [b + y for b, y in zip(bottom, ys)]
            elif t == "hbar":
                ax.barh(pos, ys, height=width, color=c, label=nm)
            else:
                ax.plot(pos, ys, color=c, label=nm, marker="o" if t == "line_markers" else None,
                        linewidth=r.choice([1.2, 1.8, 2.4]))
            gt["series"].append({"name": nm, "color": c, "x": cats, "y": ys})
        if t == "hbar":
            ax.set_yticks(pos)
            ax.set_yticklabels(cats)
        else:
            ax.set_xticks(pos)
            ax.set_xticklabels(cats, rotation=r.choice([0, 0, 30, 45]) if len(cats) > 5 else 0)
    if t == "log_line":
        ax.set_yscale("log")
    if formatter is not None:
        (ax.xaxis if t == "hbar" else ax.yaxis).set_major_formatter(formatter)
    gt["x_kind"] = x_kind
    gt["log"] = t == "log_line"
    gt["horizontal"] = t == "hbar"
    if r.random() < 0.5:
        ax.grid(axis="x" if t == "hbar" else "y", color="#cccccc", linewidth=0.6)
        ax.set_axisbelow(True)
    gt["legend"] = nser > 1 or r.random() < 0.5
    if gt["legend"]:
        if r.random() < 0.7:
            ax.legend(loc="best", fontsize="small")
        else:
            ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=nser, fontsize="small")
    if r.random() < 0.6:
        ax.set_title(r.choice(["Quarterly results", "Regional sales", "Annual trend", "Survey results"]))
    if r.random() < 0.5:
        ax.set_ylabel(r.choice(["Value", "USD", "Share", "Count"]))
    for sp in ("top", "right"):
        if r.random() < 0.5:
            ax.spines[sp].set_visible(False)
    fig.tight_layout()
    base = os.path.join(outdir, gt["id"])
    fig.savefig(base + ".pdf")
    fig.savefig(base + "_100.png", dpi=100)
    fig.savefig(base + "_150.png", dpi=150)
    plt.close(fig)
    json.dump(gt, open(base + ".json", "w"))


if __name__ == "__main__":
    out, n = sys.argv[1], int(sys.argv[2])
    os.makedirs(out, exist_ok=True)
    for i in range(n):
        make(i, out)
    print("charts", n)

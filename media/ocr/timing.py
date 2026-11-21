"""CPU time and peak RAM per OCR component, each in its own process with one thread, on a fixed crop set.
usage: timing.py OUT.json"""
import json
import os
import pickle
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))


def make_set(path):
    import data
    import engines
    import ppocr
    det = ppocr.Detector(engines.P["det_s"])
    ps = [p for p in data.all_pages() if p["ds"] in ("funsd", "sroie") or p["defect"] == "clean"]
    ps = ps[::max(1, len(ps) // 24)][:24]
    pages, crops = [], []
    for p in ps:
        rgb = data.load(p)[0]
        pages.append(rgb)
        for b in det(rgb):
            c = ppocr.crop(rgb, b["quad"])
            if c is not None:
                crops.append(c)
    pickle.dump({"pages": pages, "crops": crops[:600]}, open(path, "wb"))


def child(what, path):
    import resource
    import engines
    import ppocr
    s = pickle.load(open(path, "rb"))
    t0 = time.perf_counter()
    if what in ("det_s", "det_m"):
        m = ppocr.Detector(engines.P[what])
        load_ms = (time.perf_counter() - t0) * 1000
        xs = s["pages"]
        run = lambda x: m(x)  # noqa: E731
    elif what == "uvdoc":
        m = engines.UVDoc()
        load_ms = (time.perf_counter() - t0) * 1000
        xs = s["pages"][:8]
        run = lambda x: m(x)  # noqa: E731
    else:
        m = engines.build([what])[what]
        load_ms = (time.perf_counter() - t0) * 1000
        xs = s["crops"]
        run = lambda x: m([x])  # noqa: E731
    run(xs[0])
    ts = []
    for x in xs:
        t = time.perf_counter()
        run(x)
        ts.append((time.perf_counter() - t) * 1000)
    ts.sort()
    print(json.dumps({"what": what, "n": len(ts), "load_ms": load_ms, "mean_ms": statistics.mean(ts),
                      "p50_ms": ts[len(ts) // 2], "p95_ms": ts[int(0.95 * (len(ts) - 1))],
                      "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0}))


def main():
    out = sys.argv[1]
    path = os.path.join(os.path.dirname(os.path.abspath(out)) or ".", "timing_set.pkl")
    make_set(path)
    res = []
    for w in ["det_s", "det_m", "uvdoc", "v6s", "v6m", "v5en", "crnn", "viptr", "tess_fast", "tess_best"]:
        r = subprocess.run([sys.executable, __file__, "--child", w, path], capture_output=True, text=True,
                           env=dict(os.environ, OMP_NUM_THREADS="1"))
        line = [l for l in r.stdout.splitlines() if l.startswith("{")]
        res.append(json.loads(line[-1]) if line else {"what": w, "error": (r.stderr or "")[-400:]})
        print(res[-1], flush=True)
    import platform
    info = {"cpu": platform.processor(), "nproc": os.cpu_count()}
    try:
        info["model"] = [l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")][0]
    except Exception:  # noqa: BLE001
        pass
    json.dump({"machine": info, "rows": res}, open(out, "w"), indent=1)
    os.remove(path)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        child(sys.argv[2], sys.argv[3])
    else:
        main()

"""Pix2Text MFR 1.5 with the decode cap at 1023 new tokens (positions 0..1023); the 512-cap result is the prefix."""
import json, os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("MFR_MAX_NEW", "1023")
from mfr import MFRFast
model, shard, nshards = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
budget = float(os.environ.get("BUDGET_S", "6300"))
items = json.load(open(os.path.join(ROOT, "manifests", "t2.json"), encoding="utf-8"))
mine = [it for k, it in enumerate(items) if k % nshards == shard]
m = MFRFast(model, 4)
os.makedirs(os.path.join(ROOT, "results", "t2"), exist_ok=True)
t0 = time.time()
with open(os.path.join(ROOT, "results", "t2", f"dec_{model}.s{shard}.jsonl"), "w", encoding="utf-8") as f:
    for i, it in enumerate(mine):
        if time.time() - t0 > budget:
            print("BUDGET STOP", i, len(mine), flush=True)
            break
        t = time.perf_counter()
        pred, n, run = m(os.path.join(ROOT, it["image"]))
        ids = m.last_ids
        if n >= 512:
            p512, run512 = m.tok.decode(ids[:512], skip_special_tokens=True), True
        else:
            p512, run512 = pred, False
        f.write(json.dumps({"id": it["id"], "pred1024": pred, "ntok": n, "runaway1024": run, "pred512": p512,
                            "runaway512": run512, "s": round(time.perf_counter() - t, 3)}, ensure_ascii=False) + "\n")
        f.flush()
        if i % 100 == 0:
            print(i, len(mine), round(time.time() - t0), flush=True)
print("done", model, shard, len(mine), round(time.time() - t0))

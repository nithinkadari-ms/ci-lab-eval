import json
import os
import random
import sys
import tarfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pyarrow.parquet as pq

from common import cfg, net

REV = "02d7e0be03b09d6a29c7e4d388440bc1f5a4907b"
BASE = "https://huggingface.co/datasets/volkthienpreecha/crackedpdfs/resolve/%s/" % REV
OUT = os.path.join(cfg.DATA, "g9", "cracked")
DL = os.path.join(cfg.DATA, "g9", "cracked_dl")


def test_ids(splits):
    if isinstance(splits, dict):
        for k in ("test", "Test", "test_ids", "test_pdf_ids"):
            if k in splits and isinstance(splits[k], list):
                return set(map(str, splits[k]))
        for k, v in splits.items():
            if isinstance(v, dict):
                r = test_ids(v)
                if r:
                    return r
        vals = list(splits.values())
        if vals and all(isinstance(v, str) for v in vals):
            return {k for k, v in splits.items() if v.lower() == "test"}
    return set()


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(DL, exist_ok=True)
    for f in ("data/metadata.parquet", "data/splits.json", "LICENSE", "README.md"):
        net.download(BASE + f, os.path.join(DL, os.path.basename(f)), min_bytes=10)
    meta = pq.read_table(os.path.join(DL, "metadata.parquet")).to_pylist()
    splits = json.load(open(os.path.join(DL, "splits.json"), encoding="utf-8"))
    cfg.log("cracked columns", sorted(meta[0].keys()))
    cfg.log("splits keys", list(splits)[:10] if isinstance(splits, dict) else type(splits))
    tids = test_ids(splits)
    cfg.log("test ids", len(tids))
    key = "triad_id" if meta[0].get("triad_id") else ("pair_id" if meta[0].get("pair_id") else "sample_id")
    groups = {}
    for m in meta:
        groups.setdefault(str(m.get(key)), []).append(m)
    by_fam = {}
    for g, ms in groups.items():
        roles = {m["pdf_role"]: m for m in ms}
        inj = roles.get("injected_attack")
        org = roles.get("benign_original")
        if not inj or not org:
            continue
        if tids and str(inj["pdf_id"]) not in tids and str(inj.get("base_pdf_id")) not in tids:
            continue
        by_fam.setdefault(inj.get("attack_family", "none"), []).append(g)
    rng = random.Random("cracked")
    per = cfg.n(40, 1)
    chosen = []
    for fam in sorted(by_fam):
        gs = sorted(by_fam[fam])
        chosen += rng.sample(gs, min(per, len(gs)))
    if cfg.SCALE == "probe":
        chosen = chosen[:6]
    want = {}
    sel = []
    for g in chosen:
        for m in groups[g]:
            fp = m["file_path"].lstrip("./")
            want[fp] = m
            sel.append(dict(group=g, **{k: (v if isinstance(v, (str, int, float, bool)) or v is None else str(v)) for k, v in m.items()}))
    cfg.log("families", {f: len(v) for f, v in by_fam.items()}, "chosen groups", len(chosen), "files", len(want))
    for arc in ("benign", "injected"):
        tgz = os.path.join(DL, arc + ".tar.gz")
        if not net.download(BASE + "pdfs/%s.tar.gz" % arc, tgz, min_bytes=1000):
            raise SystemExit("download failed " + arc)
        got = 0
        with tarfile.open(tgz, "r|gz") as tf:
            for mem in tf:
                if not mem.isfile():
                    continue
                name = mem.name.lstrip("./")
                if name in want:
                    data = tf.extractfile(mem).read()
                    dest = os.path.join(OUT, name.replace("/", "__"))
                    with open(dest, "wb") as f:
                        f.write(data)
                    got += 1
        cfg.log(arc, "extracted", got)
        os.remove(tgz)
    for s in sel:
        s["local"] = s["file_path"].lstrip("./").replace("/", "__")
    sel = [s for s in sel if os.path.exists(os.path.join(OUT, s["local"]))]
    cfg.dump(dict(key=key, items=sel), os.path.join(cfg.DATA, "g9", "cracked.json"))
    cfg.log("cracked selected", len(sel))


if __name__ == "__main__":
    main()

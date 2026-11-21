import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("STRUCT_DATA", os.path.join(ROOT, "data"))
RES = os.environ.get("STRUCT_RES", os.path.join(ROOT, "res"))
SCALE = os.environ.get("SCALE", "probe")


def n(full, probe):
    return probe if SCALE == "probe" else full


def shard(items, k=None, nsh=None):
    k = int(os.environ.get("SHARD", "0")) if k is None else k
    nsh = int(os.environ.get("NSHARD", "1")) if nsh is None else nsh
    return [x for i, x in enumerate(items) if i % nsh == k]


def dump(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def jsonl_append(path, rec):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def jsonl(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def log(*a):
    print(*a, file=sys.stderr, flush=True)

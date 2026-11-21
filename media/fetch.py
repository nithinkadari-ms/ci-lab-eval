"""Downloads for the round-4 media tests. Datasets and weights go to ~/media-data and ~/media-models (actions/cache),
never into the repo. Every model file is recorded with its size, sha256 and the licence its card/manifest declares.

usage: fetch.py ocr_models | ocr_data | chart_data | forms_models | verify OUT.json
"""
import hashlib
import json
import os
import sys
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, MODELS  # noqa: E402

DLRS = "https://github.com/docling-project/docling.rs/releases/download/models-v1/"
MS = "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.9.2/"
HF_MODELS = {
    "v5en": ("PaddlePaddle/en_PP-OCRv5_mobile_rec_onnx", ["inference.onnx", "inference.yml", "README.md"]),
    "uvdoc": ("PaddlePaddle/UVDoc_onnx", ["inference.onnx", "inference.yml", "README.md"]),
    "crnn": ("Felix92/onnxtr-crnn-mobilenet-v3-small", ["model.onnx", "config.json", "README.md"]),
    "viptr": ("Felix92/onnxtr-viptr-tiny", ["model.onnx", "config.json", "README.md"]),
}
ODB_REPO = "opendatalab/OmniDocBench"
SROIE_REPO = "arvindrajan92/sroie_document_understanding"


def get(url, dst, tries=4):
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        return dst
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    err = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ci-eval"})
            with urllib.request.urlopen(req, timeout=300) as r, open(dst + ".part", "wb") as f:
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
            os.replace(dst + ".part", dst)
            return dst
        except Exception as e:  # noqa: BLE001
            err = e
    raise RuntimeError(f"download failed {url}: {err}")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ocr_models():
    d = os.path.join(MODELS, "ocr")
    sums = {}
    try:
        get(DLRS + "SHA256SUMS", os.path.join(d, "SHA256SUMS"))
        for line in open(os.path.join(d, "SHA256SUMS"), encoding="utf-8"):
            parts = line.split()
            if len(parts) == 2:
                sums[parts[1].lstrip("*")] = parts[0]
    except Exception as e:  # noqa: BLE001
        print("no SHA256SUMS:", e)
    for f in ("ocr_det.onnx", "ocr_rec_v6.onnx", "ocr_rec_v6_dict.txt", "picture_classifier.onnx", "models.json"):
        p = get(DLRS + f, os.path.join(d, "dlrs", f))
        if f in sums and sha(p) != sums[f]:
            sys.exit(f"sha mismatch {f}")
    for rel, name in (("onnx/PP-OCRv6/rec/PP-OCRv6_rec_medium.onnx", "rec_medium.onnx"),
                      ("onnx/PP-OCRv6/det/PP-OCRv6_det_medium.onnx", "det_medium.onnx")):
        get(MS + rel, os.path.join(d, "v6m", name))
    try:
        get(MS + "paddle/PP-OCRv6/rec/PP-OCRv6_rec_medium/ppocrv6_dict.txt", os.path.join(d, "v6m", "dict.txt"))
    except Exception as e:  # noqa: BLE001
        print("medium dict not hosted, the small dict is used if the class count matches:", e)
    from huggingface_hub import hf_hub_download
    for key, (repo, files) in HF_MODELS.items():
        for f in files:
            hf_hub_download(repo, f, local_dir=os.path.join(d, key))
    for kind in ("fast", "best"):
        get(f"https://github.com/tesseract-ocr/tessdata_{kind}/raw/main/eng.traineddata",
            os.path.join(d, "tess_" + kind, "eng.traineddata"))
    print("ocr models ok")


def ocr_data():
    from huggingface_hub import HfApi, hf_hub_download
    fz = get("https://guillaumejaume.github.io/FUNSD/dataset.zip", os.path.join(DATA, "funsd", "dataset.zip"))
    with zipfile.ZipFile(fz) as z:
        z.extractall(os.path.join(DATA, "funsd"))
    files = [f for f in HfApi().list_repo_files(SROIE_REPO, repo_type="dataset") if f.endswith(".parquet")]
    print("sroie parquet", files)
    for f in files:
        hf_hub_download(SROIE_REPO, f, repo_type="dataset", local_dir=os.path.join(DATA, "sroie"))
    odb = os.path.join(DATA, "odb")
    hf_hub_download(ODB_REPO, "OmniDocBench.json", repo_type="dataset", local_dir=odb)
    d = json.load(open(os.path.join(odb, "OmniDocBench.json"), encoding="utf-8"))
    en = [p["page_info"]["image_path"] for p in d if p["page_info"]["page_attribute"].get("language") == "english"]

    def one(n):
        if os.path.exists(os.path.join(odb, "images", n)):
            return 0
        for _ in range(4):
            try:
                hf_hub_download(ODB_REPO, "images/" + n, repo_type="dataset", local_dir=odb)
                return 0
            except Exception:  # noqa: BLE001
                pass
        return 1
    with ThreadPoolExecutor(8) as ex:
        bad = sum(ex.map(one, en))
    print("odb english", len(en), "failed", bad)
    if bad > 10:
        sys.exit(1)


def chart_data():
    from huggingface_hub import HfApi, hf_hub_download
    cx = os.path.join(DATA, "chartx")
    for f in ("ChartX_annotation_test.json", "ChartX_png.zip", "README.md"):
        hf_hub_download("InternScience/ChartX", f, repo_type="dataset", local_dir=cx)
    with zipfile.ZipFile(os.path.join(cx, "ChartX_png.zip")) as z:
        z.extractall(cx)
    os.remove(os.path.join(cx, "ChartX_png.zip"))
    files = sorted(f for f in HfApi().list_repo_files("achang/plot_qa", repo_type="dataset")
                   if f.endswith(".parquet") and "test" in f)
    print("plotqa test parquet", files)
    hf_hub_download("achang/plot_qa", files[0], repo_type="dataset", local_dir=os.path.join(DATA, "plotqa"))


def forms_models():
    from huggingface_hub import hf_hub_download
    for f in ("config.json", "pytorch_model.bin", "tokenizer.json", "tokenizer_config.json", "vocab.json",
              "merges.txt", "special_tokens_map.json", "preprocessor_config.json", "README.md"):
        hf_hub_download("philschmid/lilt-en-funsd", f, local_dir=os.path.join(MODELS, "lilt"))


def forms_data():
    """SignverOD (ondrs/signverod, Apache-2.0 card): first parquet shard only, for the FFDetr signature check."""
    from huggingface_hub import HfApi, hf_hub_download
    files = sorted(f for f in HfApi().list_repo_files("ondrs/signverod", repo_type="dataset") if f.endswith(".parquet"))
    print("signverod parquet", files)
    if files:
        hf_hub_download("ondrs/signverod", files[0], repo_type="dataset", local_dir=os.path.join(DATA, "signverod"))


def verify(out):
    """Sizes, sha256 and declared licences of every model file actually downloaded."""
    from huggingface_hub import HfApi
    api = HfApi()
    rec = {"files": [], "cards": {}}
    for root, _, fs in os.walk(MODELS):
        for f in fs:
            if f.endswith((".onnx", ".traineddata", ".bin", ".txt", ".yml", ".json", ".safetensors")):
                p = os.path.join(root, f)
                rec["files"].append({"path": os.path.relpath(p, MODELS), "bytes": os.path.getsize(p),
                                     "sha256": sha(p) if os.path.getsize(p) < 2_000_000_000 else None})
    for repo in [v[0] for v in HF_MODELS.values()] + ["philschmid/lilt-en-funsd", "google/deplot", "jbarrow/FFDetr",
                                                       "pdf-net/ffdetr-filled",
                                                       "timm/mobilenetv3_small_100.lamb_in1k", "facebook/dinov2-small"]:
        try:
            info = api.model_info(repo, files_metadata=True)
            cd = info.card_data.to_dict() if info.card_data else {}
            rec["cards"][repo] = {"sha": info.sha, "license": cd.get("license"),
                                  "sizes": {s.rfilename: s.size for s in (info.siblings or []) if s.size}}
        except Exception as e:  # noqa: BLE001
            rec["cards"][repo] = {"error": str(e)[:200]}
    for repo in ("InternScience/ChartX", "achang/plot_qa", SROIE_REPO, ODB_REPO, "ondrs/signverod", "mapo80/stamps",
                 "axonstan/LogoDet-3K", "HuggingFaceM4/WebSight", "dell-research-harvard/AmericanStories"):
        try:
            info = api.dataset_info(repo)
            cd = info.card_data.to_dict() if info.card_data else {}
            rec["cards"]["dataset:" + repo] = {"sha": info.sha, "license": cd.get("license")}
        except Exception as e:  # noqa: BLE001
            rec["cards"]["dataset:" + repo] = {"error": str(e)[:200]}
    mj = os.path.join(MODELS, "ocr", "dlrs", "models.json")
    if os.path.exists(mj):
        m = json.load(open(mj, encoding="utf-8"))
        arts = m["artifacts"] if isinstance(m["artifacts"], list) else list(m["artifacts"].values())
        rec["docling_rs_manifest"] = {a["id"]: {"name": a.get("name"), "license": a.get("license")} for a in arts
                                      if a.get("id") in ("ocr_det_v6", "ocr_rec_v6", "picture_classifier")}
    json.dump(rec, open(out, "w", encoding="utf-8"), indent=1)
    print(json.dumps(rec["cards"], indent=1)[:4000])


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "verify":
        verify(sys.argv[2])
    else:
        globals()[what]()

"""regions.jsonl for all arXiv crops: id, pdf, page_index, bbox (PDF points, y up), mediabox."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
items = json.load(open(os.path.join(ROOT, "manifests", "arxiv.json"), encoding="utf-8"))
only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 and sys.argv[2] else None
n = 0
with open(sys.argv[1], "w", encoding="utf-8") as f:
    for it in items:
        if only and it["id"] not in only:
            continue
        f.write(json.dumps({"id": it["id"], "pdf": os.path.join(ROOT, "data", "arxiv", it["paper"], "paper.pdf"),
                            "page_index": it["page_index"], "bbox": it["bbox"], "mediabox": it["mediabox"]}) + "\n")
        n += 1
print("regions", n)

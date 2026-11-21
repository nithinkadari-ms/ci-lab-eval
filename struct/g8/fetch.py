import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import cfg, net

OUT = os.path.join(cfg.DATA, "g8", "src")

ARXIV = [("q-fin.GN", 25), ("q-fin.ST", 20), ("q-fin.RM", 15), ("econ.GN", 20), ("stat.AP", 20)]
FR_DATES = ["2024-03-15", "2024-06-14", "2024-09-13", "2024-12-13"]


def arxiv_ids(cat, k):
    url = ("https://export.arxiv.org/api/query?search_query=cat:%s+AND+submittedDate:[202401010000+TO+202406302359]"
           "&start=0&max_results=%d&sortBy=submittedDate&sortOrder=ascending" % (cat, k * 2))
    r = net.get(url, delay=3.5, host_key="arxiv")
    if r is None:
        return []
    ids = re.findall(r"<id>https?://arxiv\.org/abs/([^<]+)</id>", r.text)
    return ids


def fr_docs(date, k):
    url = ("https://www.federalregister.gov/api/v1/documents.json?per_page=100&order=document_number"
           "&conditions[publication_date][is]=%s&conditions[type][]=RULE&conditions[type][]=NOTICE"
           "&fields[]=document_number&fields[]=pdf_url&fields[]=page_length" % date)
    r = net.get(url, delay=1.0)
    if r is None:
        return []
    out = []
    for d in r.json().get("results", []):
        pl = d.get("page_length") or 0
        if d.get("pdf_url") and 2 <= pl <= 30:
            out.append((d["document_number"], d["pdf_url"]))
    return out[:k]


def main():
    os.makedirs(OUT, exist_ok=True)
    man = []
    for cat, k in ARXIV:
        k = cfg.n(k, 1)
        got = 0
        for aid in arxiv_ids(cat, k):
            if got >= k:
                break
            fid = "arxiv_" + aid.replace("/", "_")
            if any(m["id"] == fid for m in man):
                continue
            dest = os.path.join(OUT, fid + ".pdf")
            if net.download("https://export.arxiv.org/pdf/" + aid, dest, delay=3.5) and net.is_pdf(dest):
                man.append(dict(id=fid, source="arxiv:" + cat, url="https://arxiv.org/abs/" + aid))
                got += 1
            elif os.path.exists(dest):
                os.remove(dest)
        cfg.log(cat, got)
    per = cfg.n(13, 1)
    for date in FR_DATES[:cfg.n(4, 2)]:
        got = 0
        for num, url in fr_docs(date, per * 2):
            if got >= per:
                break
            fid = "fr_" + num
            dest = os.path.join(OUT, fid + ".pdf")
            if net.download(url, dest, delay=1.0) and net.is_pdf(dest):
                man.append(dict(id=fid, source="federal_register", url=url))
                got += 1
        cfg.log(date, got)
    cfg.dump(man, os.path.join(cfg.DATA, "g8", "src.json"))
    cfg.log("g8 sources", len(man))


if __name__ == "__main__":
    main()

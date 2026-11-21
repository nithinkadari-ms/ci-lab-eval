import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pypdfium2 as pdfium

from common import cfg, net
from g7 import jats

B = "https://pmc-oa-opendata.s3.amazonaws.com/"
OUT = os.path.join(cfg.DATA, "pmc")
OK_LIC = {"ccby", "cc0", "ccbysa", "ccbynd"}
STARTS = ["metadata/PMC10500000", "metadata/PMC11000000", "metadata/PMC11500000", "metadata/PMC12000000"]


def https(u):
    if not u:
        return None
    u = u.split("?")[0]
    if u.startswith("s3://pmc-oa-opendata/"):
        return B + u[len("s3://pmc-oa-opendata/"):]
    return u


def keys(start, n):
    out, token = [], None
    while len(out) < n:
        url = B + "?list-type=2&prefix=metadata/&max-keys=1000&start-after=" + start
        if token:
            url = B + "?list-type=2&prefix=metadata/&max-keys=1000&continuation-token=" + requests_quote(token)
        r = net.get(url)
        if r is None:
            break
        out += re.findall(r"<Key>([^<]+\.json)</Key>", r.text)
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", r.text)
        if not m:
            break
        token = m.group(1)
    return out[:n]


def requests_quote(s):
    from urllib.parse import quote
    return quote(s, safe="")


def main():
    os.makedirs(OUT, exist_ok=True)
    want = cfg.n(240, 4)
    per = want // len(STARTS) + 1
    man = []
    seen_lic = {}
    for st in STARTS[:cfg.n(4, 1)]:
        got = 0
        for k in keys(st, 3000):
            if got >= per:
                break
            r = net.get(B + k)
            if r is None:
                continue
            try:
                m = r.json()
            except ValueError:
                continue
            lic = re.sub(r"[^a-z0-9]", "", str(m.get("license_code", "")).lower())
            seen_lic[lic] = seen_lic.get(lic, 0) + 1
            if lic not in OK_LIC or not m.get("pdf_url") or str(m.get("is_retracted", "")).lower() in ("true", "yes", "1"):
                continue
            pid = "%s.%s" % (m.get("pmcid"), m.get("version"))
            xp = os.path.join(OUT, pid + ".xml")
            if not net.download(https(m.get("xml_url")), xp, min_bytes=2000):
                continue
            try:
                root = jats.root_of(open(xp, "rb").read())
            except Exception:
                os.remove(xp)
                continue
            art = root.get("article-type", "")
            refs = list(root.iter("ref"))
            figs = list(root.iter("fig"))
            tabs = list(root.iter("table-wrap"))
            xr, info = jats.xrefs(root)
            secs = jats.sections(root)
            if art != "research-article" or len(refs) < 10 or len(figs) < 2 or len(tabs) < 1 or len(xr) < 20 or len(secs) < 4:
                os.remove(xp)
                continue
            pp = os.path.join(OUT, pid + ".pdf")
            if not net.download(https(m.get("pdf_url")), pp, min_bytes=20000) or not net.is_pdf(pp):
                os.remove(xp)
                if os.path.exists(pp):
                    os.remove(pp)
                continue
            try:
                npg = len(pdfium.PdfDocument(pp))
            except Exception:
                npg = 0
            if not 3 <= npg <= 30:
                os.remove(xp)
                os.remove(pp)
                continue
            man.append(dict(id=pid, license=m.get("license_code"), pages=npg, xml=os.path.join("pmc", pid + ".xml"), pdf=os.path.join("pmc", pid + ".pdf"),
                            doi=m.get("doi"), numeric=info["numeric"], n_xref=len(xr), n_secs=len(secs)))
            got += 1
        cfg.log(st, got)
    cfg.dump(man, os.path.join(OUT, "pmc.json"))
    cfg.log("pmc docs", len(man), "licences seen", seen_lic)


if __name__ == "__main__":
    main()

"""OCR test pages: FUNSD forms, SROIE receipts, OmniDocBench English text regions and synthetic born-digital
business pages rendered and degraded with known transforms (word boxes follow the same transform).

Page record: id, group (document; splits and paired tests are per group), ds, defect, words [{t, box}],
fields [str] (critical values that must be read exactly), and a loader for the RGB image."""
import glob
import io
import json
import math
import os
import random
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import DATA, split_of  # noqa: E402

DEFECTS = ["clean", "lowdpi", "blur", "noise", "skew", "curved", "jpeg", "faded"]
N_SYNTH = int(os.environ.get("OCR_N_SYNTH", "240"))
N_ODB_REGIONS = int(os.environ.get("OCR_N_ODB", "4000"))
HARD_SOURCES = {"newspaper", "magazine", "exam_paper", "colorful_textbook", "note"}


# ---------------------------------------------------------------- FUNSD
def funsd_pages():
    out = []
    for sp in ("training_data", "testing_data"):
        for a in sorted(glob.glob(os.path.join(DATA, "funsd", "dataset", sp, "annotations", "*.json"))):
            stem = os.path.splitext(os.path.basename(a))[0]
            img = os.path.join(DATA, "funsd", "dataset", sp, "images", stem + ".png")
            out.append({"id": f"funsd:{stem}", "group": f"funsd:{stem}", "ds": "funsd", "defect": "real_scan",
                        "src": ("funsd", a, img)})
    return out


def _funsd_load(a, img):
    d = json.load(open(a, encoding="utf-8"))
    words = []
    for e in d["form"]:
        for w in e.get("words", []):
            if w.get("text", "").strip():
                words.append({"t": w["text"].strip(), "box": [float(v) for v in w["box"]]})
    rgb = cv2.cvtColor(cv2.imread(img, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    fields = [w["t"] for w in words if any(c.isdigit() for c in w["t"]) and len(w["t"]) >= 2]
    return rgb, words, fields


# ---------------------------------------------------------------- SROIE
def _sroie_rows():
    import pyarrow.parquet as pq
    files = sorted(glob.glob(os.path.join(DATA, "sroie", "**", "*.parquet"), recursive=True))
    for f in files:
        pf = pq.ParquetFile(f)
        for b in pf.iter_batches(batch_size=16):
            for r in b.to_pylist():
                yield r


SROIE_PNG = os.path.join(DATA, "sroie_png")


def sroie_extract():
    """write each receipt once as PNG + GT JSON so workers never hold the parquet rows in memory"""
    if os.path.exists(os.path.join(SROIE_PNG, "done")):
        return
    os.makedirs(SROIE_PNG, exist_ok=True)
    for i, r in enumerate(_sroie_rows()):
        img = r["image"]
        with open(os.path.join(SROIE_PNG, f"{i}.img"), "wb") as f:
            f.write(img["bytes"] if isinstance(img, dict) else img)
        json.dump(r["ocr"] or [], open(os.path.join(SROIE_PNG, f"{i}.json"), "w", encoding="utf-8"))
    open(os.path.join(SROIE_PNG, "done"), "w").close()


def sroie_pages():
    sroie_extract()
    n = len(glob.glob(os.path.join(SROIE_PNG, "*.json")))
    return [{"id": f"sroie:{i}", "group": f"sroie:{i}", "ds": "sroie", "defect": "receipt", "src": ("sroie", i)}
            for i in range(n)]


def _split_line(text, box):
    """Line -> words, x-extent split by character share (SROIE ships line boxes only)."""
    toks = text.split()
    if not toks:
        return []
    x0, y0, x1, y1 = box
    total = max(1, len(text))
    out, pos = [], 0
    for t in toks:
        i = text.index(t, pos)
        a, b = i / total, (i + len(t)) / total
        out.append({"t": t, "box": [x0 + a * (x1 - x0), y0, x0 + b * (x1 - x0), y1]})
        pos = i + len(t)
    return out


def _sroie_load(i):
    from PIL import Image
    rgb = np.array(Image.open(os.path.join(SROIE_PNG, f"{i}.img")).convert("RGB"))
    words, fields = [], []
    for o in json.load(open(os.path.join(SROIE_PNG, f"{i}.json"), encoding="utf-8")):
        pts = o["box"]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        t = " ".join(str(o.get("text") or "").split())
        if not t:
            continue
        words += _split_line(t, [min(xs), min(ys), max(xs), max(ys)])
        if str(o.get("label", "")).lower() in ("date", "total"):
            fields += [w for w in t.split() if any(c.isdigit() for c in w)]
    return rgb, words, fields


# ---------------------------------------------------------------- OmniDocBench text regions
def odb_regions():
    d = json.load(open(os.path.join(DATA, "odb", "OmniDocBench.json"), encoding="utf-8"))
    hard, easy = [], []
    for p in d:
        a = p["page_info"]["page_attribute"]
        if a.get("language") != "english":
            continue
        img = os.path.join(DATA, "odb", "images", p["page_info"]["image_path"])
        src = a.get("data_source")
        for k, e in enumerate(p["layout_dets"]):
            if e.get("category_type") not in ("text_block", "title") or e.get("ignore"):
                continue
            t = e.get("text") or ""
            if not t.strip() or "$" in t or "\\" in t or len(t) > 700 or len(t) < 3:
                continue
            xs, ys = e["poly"][0::2], e["poly"][1::2]
            rec = {"id": f"odb:{p['page_info']['image_path']}:{k}", "group": "odb:" + p["page_info"]["image_path"],
                   "ds": "odb", "defect": "odb_" + ("hard" if src in HARD_SOURCES else "other"), "source": src,
                   "src": ("odb", img, [min(xs), min(ys), max(xs), max(ys)], t)}
            (hard if src in HARD_SOURCES else easy).append(rec)
    r = random.Random(7)
    r.shuffle(easy)
    r.shuffle(hard)
    nh = min(len(hard), int(N_ODB_REGIONS * 0.6))
    return sorted(hard[:nh] + easy[:N_ODB_REGIONS - nh], key=lambda x: x["id"])


def _odb_load(img, box, text):
    im = cv2.imread(img, cv2.IMREAD_COLOR)
    H, W = im.shape[:2]
    pad = 4
    x0, y0 = max(0, int(box[0]) - pad), max(0, int(box[1]) - pad)
    x1, y1 = min(W, int(math.ceil(box[2])) + pad), min(H, int(math.ceil(box[3])) + pad)
    rgb = cv2.cvtColor(im[y0:y1, x0:x1], cv2.COLOR_BGR2RGB)
    return np.ascontiguousarray(rgb), text


# ---------------------------------------------------------------- synthetic born-digital pages
WORDS = ("account accrued additional address agreement amount annual applicable approval asset audit authorised "
         "balance bank basis benefit billing board budget business capital carrier cash certificate charge client "
         "commission company compliance contract cost credit currency customer date debit delivery department "
         "deposit description discount document due employee equipment estimate expense facility fee filing "
         "finance freight fund goods gross income insurance interest inventory invoice issued item labour lease "
         "liability limit loan maintenance management margin material method month net notice number obligation "
         "office order outstanding owner payable payment pension period policy premium price principal product "
         "project purchase quantity quarter rate receipt received reference register remittance rent report "
         "reserve revenue review salary schedule section security service settlement shipment signature statement "
         "subtotal supplier support tax term total transaction transfer unit utility value vendor warranty week "
         "weight year the of and to in for on with by from at as is are was be this that which shall will may "
         "under all any each other such not or per within before after during upon including").split()
NAMES = "Acme Northwind Contoso Fabrikam Globex Initech Umbrella Vandelay Wayne Stark Hooli Tyrell".split()
STREETS = "Main Oak Pine Maple Cedar Elm Lake Hill Park River Market Church".split()
CITIES = "Springfield Riverton Fairview Georgetown Clinton Madison Salem Franklin Bristol Dover".split()


def _fonts():
    cands = [("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
             ("DejaVuSerif", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
             ("LiberationSans", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
             ("LiberationSerif", "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"),
             ("LiberationMono", "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"),
             ("LiberationSansNarrow", "/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Regular.ttf")]
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    names = []
    for n, p in cands:
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont(n, p))
                names.append(n)
            except Exception:  # noqa: BLE001
                pass
    return names or ["Helvetica", "Times-Roman", "Courier"]


def _money(r):
    v = r.choice([r.uniform(0.5, 99), r.uniform(100, 9999), r.uniform(10000, 999999)])
    return f"${v:,.2f}"


def _date(r):
    y, m, d = r.randint(2015, 2026), r.randint(1, 12), r.randint(1, 28)
    return r.choice([f"{m:02d}/{d:02d}/{y}", f"{d:02d}.{m:02d}.{y}", f"{y}-{m:02d}-{d:02d}"])


def _ident(r):
    a = "".join(r.choice("ABCDEFGHJKLMNPRSTUVWXYZ") for _ in range(r.randint(2, 3)))
    return r.choice([f"INV-{r.randint(2015, 2026)}-{r.randint(0, 99999):05d}", f"{a}{r.randint(10, 99)}-{r.randint(1000, 9999)}",
                     f"SN{r.randint(10, 99)}{a}{r.randint(100, 999)}", f"PO#{r.randint(100000, 999999)}"])


def _phone(r):
    return f"({r.randint(200, 999)}) {r.randint(200, 999)}-{r.randint(0, 9999):04d}"


def _sentence(r, n):
    w = [r.choice(WORDS) for _ in range(n)]
    w[0] = w[0].capitalize()
    for k in range(2, n - 1, 7):
        if r.random() < 0.25:
            w[k] += ","
    if r.random() < 0.2:
        w[r.randrange(n)] = str(r.randint(1, 2026))
    return " ".join(w) + "."


def synth_spec(i):
    """Deterministic content for base document i: list of (x_pt, y_pt_baseline, size, text), fields, page size."""
    r = random.Random(1000 + i)
    kind = ["invoice", "form", "report", "receipt", "tiny"][i % 5]
    fonts = _fonts()
    font = fonts[r.randrange(len(fonts))]
    W, H = 612.0, 792.0
    lines, fields = [], []
    y = H - 60

    def put(x, s, size, crit=None):
        lines.append((x, y, size, s))
        if crit:
            fields.append(crit)
    if kind == "receipt":
        W = 300.0
        H = 792.0
        y = H - 40
    base = {"invoice": r.uniform(8.5, 11), "form": r.uniform(8, 10.5), "report": r.uniform(8.5, 11.5),
            "receipt": r.uniform(7.5, 9.5), "tiny": r.uniform(5.0, 6.5)}[kind]
    comp = f"{r.choice(NAMES)} {r.choice(['Ltd', 'Inc.', 'LLC', 'GmbH', 'Corp.'])}"
    put(40, comp, base * 1.6)
    y -= base * 2.2
    addr = f"{r.randint(1, 9999)} {r.choice(STREETS)} Street, {r.choice(CITIES)} {r.randint(10000, 99999)}"
    put(40, addr, base)
    y -= base * 1.6
    if kind in ("invoice", "receipt"):
        inv, dt = _ident(r), _date(r)
        put(40, f"Invoice No: {inv}", base, inv)
        y -= base * 1.5
        put(40, f"Date: {dt}", base, dt)
        y -= base * 2.0
        n = r.randint(6, 18) if kind == "invoice" else r.randint(5, 14)
        for _ in range(n):
            desc = " ".join(r.choice(WORDS) for _ in range(r.randint(1, 4))).capitalize()
            qty = r.randint(1, 250)
            amt = _money(r)
            if kind == "invoice":
                put(40, desc, base)
                put(300, str(qty), base)
                put(W - 140, amt, base, amt)
            else:
                put(20, f"{qty} x {desc}"[:34], base)
                put(W - 95, amt, base, amt)
            y -= base * 1.45
        y -= base
        for lab in ("Subtotal", "Tax", "Total Due"):
            v = _money(r)
            put(W - 260 if kind == "invoice" else 20, lab + ":", base)
            put(W - 140 if kind == "invoice" else W - 95, v, base, v)
            y -= base * 1.5
    elif kind == "form":
        for _ in range(r.randint(10, 20)):
            lab = r.choice(["Account Number", "Phone", "Serial No.", "Reference", "Date of Birth", "Policy No.",
                            "Amount", "Name", "Employee ID", "Tax ID", "Due Date", "Contact"])
            val = {"Account Number": f"{r.randint(1000, 9999)}-{r.randint(1000, 9999)}-{r.randint(1000, 9999)}",
                   "Phone": _phone(r), "Serial No.": _ident(r), "Reference": _ident(r), "Date of Birth": _date(r),
                   "Policy No.": f"P{r.randint(1000000, 9999999)}", "Amount": _money(r),
                   "Name": f"{r.choice(NAMES)} {r.choice(STREETS)}", "Employee ID": f"E{r.randint(10000, 99999)}",
                   "Tax ID": f"{r.randint(10, 99)}-{r.randint(1000000, 9999999)}", "Due Date": _date(r),
                   "Contact": f"{r.choice(NAMES).lower()}@example.com"}[lab]
            col = r.choice([40, 320])
            put(col, lab + ":", base)
            put(col + r.uniform(95, 130), val, base, val if any(c.isdigit() for c in val) else None)
            y -= base * r.uniform(1.6, 2.4)
    else:
        two = kind == "report" and r.random() < 0.4
        colw = (W - 100) / 2 if two else W - 80
        from reportlab.pdfbase.pdfmetrics import stringWidth
        xs = [40, 40 + colw + 20] if two else [40]
        top = y
        for x in xs:
            y = top
            while y > 70:
                words = _sentence(r, r.randint(10, 30)).split()
                cur = ""
                for w in words:
                    nxt = (cur + " " + w).strip()
                    if stringWidth(nxt, font, base) > colw:
                        put(x, cur, base)
                        y -= base * 1.3
                        cur = w
                        if y <= 70:
                            break
                    else:
                        cur = nxt
                if cur and y > 70:
                    put(x, cur, base)
                    y -= base * 1.3
                y -= base * 0.6
                if kind == "tiny" and r.random() < 0.15:
                    v = _money(r)
                    put(x, f"Amount payable {v}", base, v)
                    y -= base * 1.3
    return {"kind": kind, "font": font, "W": W, "H": H, "lines": [l for l in lines if l[1] > 20], "fields": fields}


def _render(spec, dpi):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen import canvas
    import pypdfium2 as pdfium
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(spec["W"], spec["H"]))
    words = []
    s = dpi / 72.0
    for x, y, size, text in spec["lines"]:
        c.setFont(spec["font"], size)
        c.drawString(x, y, text)
        pos = 0
        for t in text.split(" "):
            if t:
                x0 = x + stringWidth(text[:pos], spec["font"], size)
                x1 = x0 + stringWidth(t, spec["font"], size)
                words.append({"t": t, "box": [x0 * s, (spec["H"] - y - 0.78 * size) * s, x1 * s,
                                              (spec["H"] - y + 0.22 * size) * s]})
            pos += len(t) + 1
    c.showPage()
    c.save()
    pdf = pdfium.PdfDocument(buf.getvalue())
    img = pdf[0].render(scale=s).to_pil().convert("RGB")
    pdf.close()
    return np.array(img), words


def _tf_words(words, fn, W, H):
    out = []
    for w in words:
        x0, y0, x1, y1 = w["box"]
        pts = [fn(x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1), ((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1))]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        b = [min(xs), min(ys), max(xs), max(ys)]
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if 0 <= cx < W and 0 <= cy < H:
            out.append({"t": w["t"], "box": b})
    return out


def degrade(spec, defect, seed):
    r = np.random.default_rng(seed)
    dpi = {"lowdpi": 100, "jpeg": 150}.get(defect, 200)
    rgb, words = _render(spec, dpi)
    H, W = rgb.shape[:2]
    if defect == "blur":
        rgb = cv2.GaussianBlur(rgb, (0, 0), float(r.uniform(1.2, 1.9)))
    elif defect == "noise":
        g = rgb.astype(np.float32) + r.normal(0, 22, rgb.shape[:2])[..., None]
        sp = r.random(rgb.shape[:2])
        g[sp < 0.006] = 0
        g[sp > 0.994] = 255
        rgb = np.clip(g, 0, 255).astype(np.uint8)
    elif defect == "skew":
        ang = float(r.uniform(2.0, 6.0) * r.choice([-1, 1]))
        M = cv2.getRotationMatrix2D((W / 2, H / 2), ang, 1.0)
        rgb = cv2.warpAffine(rgb, M, (W, H), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
        words = _tf_words(words, lambda x, y: (M[0, 0] * x + M[0, 1] * y + M[0, 2], M[1, 0] * x + M[1, 1] * y + M[1, 2]), W, H)
    elif defect == "curved":
        A, L, ph = float(r.uniform(10, 22)), float(W * r.uniform(0.9, 1.6)), float(r.uniform(0, 2 * math.pi))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        my = yy - A * np.sin(2 * np.pi * xx / L + ph)
        rgb = cv2.remap(rgb, xx, my.astype(np.float32), cv2.INTER_CUBIC, borderValue=(255, 255, 255))
        words = _tf_words(words, lambda x, y: (x, y + A * math.sin(2 * math.pi * x / L + ph)), W, H)
    elif defect == "jpeg":
        g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        ok, enc = cv2.imencode(".jpg", g, [cv2.IMWRITE_JPEG_QUALITY, int(r.integers(10, 18))])
        g = cv2.imdecode(enc, cv2.IMREAD_GRAYSCALE)
        rgb = cv2.cvtColor(g, cv2.COLOR_GRAY2RGB)
    elif defect == "faded":
        g = rgb.astype(np.float32)
        a = float(r.uniform(0.35, 0.5))
        grad = np.linspace(float(r.uniform(-40, 0)), float(r.uniform(0, 30)), W, dtype=np.float32)[None, :, None]
        g = 255 - (255 - g) * a - 25 + grad
        rgb = np.clip(g, 0, 255).astype(np.uint8)
    return np.ascontiguousarray(rgb), words


def synth_pages():
    out = []
    for i in range(N_SYNTH):
        for d in DEFECTS:
            out.append({"id": f"synth:{i}:{d}", "group": f"synth:{i}", "ds": "synth", "defect": d, "src": ("synth", i, d)})
    return out


def all_pages():
    ps = funsd_pages() + sroie_pages() + synth_pages()
    for p in ps:
        p["split"] = split_of(p["group"])
    return ps


def load(p):
    """-> rgb, words, fields, kind"""
    s = p["src"]
    if s[0] == "funsd":
        return _funsd_load(s[1], s[2]) + ("form_scan",)
    if s[0] == "sroie":
        return _sroie_load(s[1]) + ("receipt_scan",)
    spec = synth_spec(s[1])
    rgb, words = degrade(spec, s[2], seed=s[1] * 31 + DEFECTS.index(s[2]))
    return rgb, words, list(spec["fields"]), spec["kind"]


if __name__ == "__main__":
    import collections
    ps = all_pages()
    print(len(ps), collections.Counter(p["ds"] for p in ps), collections.Counter(p["split"] for p in ps))
    rs = odb_regions()
    print("odb regions", len(rs), collections.Counter(r["defect"] for r in rs))

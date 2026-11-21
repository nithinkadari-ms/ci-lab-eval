import os
import time

import requests

UA = {"User-Agent": "ci-lab-eval/1.0 (document parsing evaluation)"}
_last = {}


def get(url, delay=0.0, tries=4, timeout=120, stream=False, host_key=None):
    hk = host_key or url.split("/")[2]
    for k in range(tries):
        wait = _last.get(hk, 0) + delay - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[hk] = time.time()
        try:
            r = requests.get(url, headers=UA, timeout=timeout, stream=stream)
            if r.status_code == 200:
                return r
            if r.status_code in (404, 403, 410):
                return None
        except requests.RequestException:
            pass
        time.sleep(3 * (k + 1))
    return None


def download(url, dest, delay=0.0, min_bytes=1000):
    if os.path.exists(dest) and os.path.getsize(dest) >= min_bytes:
        return True
    r = get(url, delay=delay, stream=True)
    if r is None:
        return False
    tmp = dest + ".part"
    with open(tmp, "wb") as f:
        for ch in r.iter_content(1 << 16):
            f.write(ch)
    if os.path.getsize(tmp) < min_bytes:
        os.remove(tmp)
        return False
    os.replace(tmp, dest)
    return True


def is_pdf(path):
    try:
        with open(path, "rb") as f:
            return f.read(5) == b"%PDF-"
    except OSError:
        return False

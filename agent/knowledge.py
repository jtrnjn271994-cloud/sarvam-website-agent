#!/usr/bin/env python3
"""Read-only access to knowledge/ (Decisions Log row 41). The agent cites rows here and nowhere else.

Set KNOWLEDGE_DIR to point at another copy. Default: <project>/knowledge.
A model sees only the rows this module hands it. Code checks that every id it cites exists and that
every number written next to a KB id appears in that row.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envload  # noqa: F401
import csv
import fnmatch
import json
import os
import re
import functools

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB = os.environ.get("KNOWLEDGE_DIR") or os.path.join(PROJECT, "knowledge")

PRODUCT_LEDGERS = {
    "voice": ["validation-B1-voice.csv", "validation-K-stories.csv", "validation-I-proof.csv", "validation-G-partners.csv", "icp-*-rivals.csv", "icp-*-pain.csv"],
    "docs": ["validation-B2-docs.csv", "validation-I-proof.csv", "validation-K-stories.csv", "icp-*-rivals.csv"],
    "inference": ["validation-B3-inference.csv", "validation-L-hyperscalers.csv", "validation-E-benchmarks.csv", "validation-C-evidence.csv"],
    "speech": ["validation-H-saaras.csv", "validation-F-language-radar.csv", "validation-E-benchmarks.csv"],
    "translate": ["validation-F-language-radar.csv", "validation-H-saaras.csv"],
    "custom": ["validation-I-proof.csv", "validation-K-stories.csv", "validation-G-partners.csv"],
    "agents": ["validation-I-proof.csv", "validation-K-stories.csv", "validation-G-partners.csv"],
}


def version():
    p = os.path.join(KB, "VERSION")
    return open(p).read().strip() if os.path.isfile(p) else "none"


@functools.lru_cache(maxsize=1)
def index():
    p = os.path.join(KB, "index.json")
    return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else {}


@functools.lru_cache(maxsize=64)
def _rows(file):
    return list(csv.DictReader(open(os.path.join(KB, "ledgers", file), encoding="utf-8")))


def exists(kid):
    return kid in index()


def row(kid):
    meta = index().get(kid)
    if not meta:
        return None
    return next((r for r in _rows(os.path.basename(meta["file"])) if r.get("id") == kid), None)


def row_text(kid):
    r = row(kid)
    return " ".join(str(v) for v in (r or {}).values())


def rows_for(product, limit=60, width=240):
    """Rows a drafter may cite for a product: [(id, one-line text, status, label)]. PASS rows first."""
    pats = PRODUCT_LEDGERS.get(product) or ["validation-I-proof.csv", "validation-K-stories.csv"]
    out = []
    for kid, meta in index().items():
        f = os.path.basename(meta["file"])
        if any(fnmatch.fnmatch(f, p) for p in pats):
            r = row(kid) or {}
            txt = "; ".join("%s=%s" % (k, str(v)[:90]) for k, v in r.items() if v and k not in ("id", "status", "label", "notes", "checked_on", "date_read", "url", "source_url"))
            out.append((kid, txt[:width], meta["status"], meta["label"]))
    order = {"PASS": 0, "PASS-2ND": 1, "CALC": 2, "NUM-ONLY": 3, "UNCHECKED": 4}
    out.sort(key=lambda x: (order.get(x[2], 9), x[0]))
    return out[:limit]


def check_bullet_ids(bullet):
    """Problems with the KB ids in one positioning bullet. Tag form: [KB:V-01, CL-001 | LABEL]."""
    m = re.search(r"\[([^\[\]|]+)\|\s*([^\[\]]+)\]\s*$", bullet)
    if not m:
        return []
    probs, text = [], bullet[:m.start()]
    ids = [x.strip()[3:] for x in m.group(1).split(",") if x.strip().startswith("KB:")]
    for kid in ids:
        if not exists(kid):
            probs.append("cites KB:%s, which is not in knowledge/ (version %s)" % (kid, version()))
    if ids:
        src = " ".join(row_text(k) for k in ids if exists(k))
        norm = lambda t: t.replace(",", "")
        for n in re.findall(r"\d[\d,]*\.?\d*", text):
            n = n.rstrip(".,")
            if len(n) > 1 and norm(n) not in norm(src):
                probs.append("number %s is not in the cited KB row(s) (%s)" % (n, ", ".join(ids)))
    return probs

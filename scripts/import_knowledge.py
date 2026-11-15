#!/usr/bin/env python3
"""Build knowledge/ : a fixed, versioned snapshot of the checked research (Decisions Log row 41).

Run:  python3 scripts/import_knowledge.py [--source "<path to the research folder>"]
Plain Python, no model. It copies only what the agent may cite:
  - ledger CSVs whose rows carry a verification status (kept: PASS, PASS-2ND, NUM-ONLY, CALC, UNCHECKED;
    dropped: FAIL, WEAK, OLD-SOURCE, THEME). The planted-error test ledger is excluded.
  - the buying-committee tables (roles only) and the competitor check note.
Never copied: contact records, named-people ledgers, transcripts, PDFs, anything with an email.
Writes knowledge/manifest.json (source, hash, rows kept and dropped), knowledge/index.json (id -> file, status)
and knowledge/VERSION. The agent reads knowledge/ only; it never reads the research folder.
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
KB = os.path.join(PROJECT, "knowledge")
KEEP = {"PASS", "PASS-2ND", "NUM-ONLY", "CALC", "UNCHECKED"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def ledgers(src):
    out = []
    v = os.path.join(src, "validation")
    for f in sorted(os.listdir(v)):
        if f.startswith("ledger-") and f.endswith(".csv") and "negative-test" not in f:
            out.append(("validation-" + f[len("ledger-"):], os.path.join(v, f)))
    icp = os.path.join(src, "icp-round-2")
    for ind in sorted(os.listdir(icp)):
        d = os.path.join(icp, ind)
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.startswith("ledger-") and f.endswith(".csv") and "people" not in f:
                    out.append(("icp-%s-%s" % (ind, f[len("ledger-"):]), os.path.join(d, f)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=os.path.join(os.path.dirname(PROJECT), "02 Assets", "Research"))
    a = ap.parse_args()
    src = a.source
    if not os.path.isdir(src):
        sys.exit("research folder not found: " + src)
    if os.path.isdir(KB):
        shutil.rmtree(KB)
    os.makedirs(os.path.join(KB, "ledgers"))
    os.makedirs(os.path.join(KB, "buyers"))
    os.makedirs(os.path.join(KB, "notes"))
    manifest, index, rel = [], {}, lambda p: os.path.relpath(p, os.path.dirname(PROJECT))
    for name, path in ledgers(src):
        rows = list(csv.DictReader(open(path, encoding="utf-8")))
        if not rows or "id" not in rows[0] or "status" not in rows[0]:
            continue
        kept = [r for r in rows if (r.get("status") or "").strip() in KEEP and not EMAIL.search(" ".join(str(v) for v in r.values()))]
        dest = os.path.join("ledgers", name)
        with open(os.path.join(KB, dest), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(kept)
        for r in kept:
            index[r["id"]] = {"file": dest, "status": r["status"].strip(), "label": (r.get("label") or "").strip()}
        manifest.append({"file": dest, "source": rel(path), "source_sha256": sha(path), "rows_in_source": len(rows), "rows_kept": len(kept),
                         "rows_dropped": len(rows) - len(kept), "kind": "ledger"})
    icp = os.path.join(src, "icp-round-2")
    for ind in sorted(os.listdir(icp)):
        c = os.path.join(icp, ind, "committee.csv")
        if os.path.isfile(c):
            dest = os.path.join("buyers", "%s-committee.csv" % ind)
            shutil.copy(c, os.path.join(KB, dest))
            manifest.append({"file": dest, "source": rel(c), "source_sha256": sha(c), "rows_kept": len(list(csv.DictReader(open(c, encoding="utf-8")))), "kind": "buying committee (roles only)"})
    n = os.path.join(src, "sarvam-competitor-check-by-offering.md")
    if os.path.isfile(n):
        shutil.copy(n, os.path.join(KB, "notes", os.path.basename(n)))
        manifest.append({"file": "notes/" + os.path.basename(n), "source": rel(n), "source_sha256": sha(n), "kind": "note (rivals by offering)"})
    json.dump({"made": datetime.date.today().isoformat(), "rules": "Only rows with a verification status. No contacts, no named people, no transcripts. The agent reads this folder only.",
               "files": manifest}, open(os.path.join(KB, "manifest.json"), "w"), indent=1, ensure_ascii=False)
    json.dump(index, open(os.path.join(KB, "index.json"), "w"), ensure_ascii=False)
    h = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:12]
    open(os.path.join(KB, "VERSION"), "w").write("%s-%s\n" % (datetime.date.today().isoformat(), h))
    print("knowledge written: %d files, %d citable ids, version %s-%s" % (len(manifest), len(index), datetime.date.today().isoformat(), h))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Copy the buyer personas and the industry-by-product fit into this folder (library/personas.json).

Sources (read once, outside this folder):
  02 Assets/Research/icp-round-2/<industry>/committee.csv   buying committee roles per industry (8 industries)
  02 Assets/Engine/map-source/data/C.json, VERT.json         GTM map fit status per industry and product
The copy makes the agent folder self-contained for GitHub. Labels are kept as they are in the sources:
role text is analyst research, not buyer interviews.
Run: python3 -I agent/build_personas.py
"""
import csv
import datetime
import json
import os
import re

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(PROJECT)
ICP = os.path.join(ROOT, "02 Assets", "Research", "icp-round-2")
MAP = os.path.join(ROOT, "02 Assets", "Engine", "map-source", "data")
OUT = os.path.join(PROJECT, "library", "personas.json")
FIT_ORDER = {"lead": 0, "prove": 1, "attach": 2, "later": 3, "park": 4}
FIT_WORDS = {"lead": "Start here", "prove": "Test first", "attach": "Add-on", "later": "Later", "park": "Hold"}


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def main():
    verts = json.load(open(os.path.join(MAP, "VERT.json"), encoding="utf-8"))
    fit = json.load(open(os.path.join(MAP, "C.json"), encoding="utf-8"))
    inds = []
    for v in verts:
        rows = list(csv.DictReader(open(os.path.join(ICP, v["id"], "committee.csv"), encoding="utf-8")))
        roles = []
        for r in rows:
            roles.append({"key": "%s:%s" % (v["id"], slug(r["role"])), "role": r["role"].strip(),
                          "typical_titles": r.get("typical_titles", "").strip(), "owns": r.get("owns", "").strip(),
                          "cares_about": r.get("cares_about", "").strip(), "blocks_if": r.get("blocks_if", "").strip(),
                          "label": r.get("label", "").strip(), "source_url": r.get("source_url", "").strip()})
        inds.append({"id": v["id"], "name": v["name"], "sub": v.get("sub", ""), "roles": roles,
                     "fit": {p: fit[v["id"]][p]["s"] for p in fit[v["id"]]}})
    data = {"built": datetime.date.today().isoformat(),
            "note": "Buyer committees from icp-round-2 (analyst research, not buyer interviews) and fit statuses from the GTM map. Do not edit by hand; rebuild.",
            "fit_words": FIT_WORDS, "fit_order": FIT_ORDER, "industries": inds}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(data, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("wrote", os.path.relpath(OUT, PROJECT), "|", len(inds), "industries,", sum(len(i["roles"]) for i in inds), "roles")


if __name__ == "__main__":
    main()

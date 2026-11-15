#!/usr/bin/env python3
"""Real button destinations per page, found in the saved capture, and which goals they allow.

Kinds: console (sign-up or product console), contact (sales form), pricing, docs, explore (models, playground, demo).
Only links that exist on the saved page are used, so the writer can never invent a destination.
Run: python3 -I agent/destinations.py <page>
"""
import glob
import json
import os
import re
import sys
from urllib.parse import urlparse

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY_KIND = {"console": "console", "contact": "contact", "pricing": "pricing", "docs": "docs", "models": "explore"}


def kind_of(url):
    u = urlparse(url)
    host, path, frag = u.netloc.lower(), u.path.lower(), u.fragment.lower()
    if host.startswith("docs."):
        return "docs"
    if "contact-us" in path:
        return "contact"
    if "pricing" in path:
        return "pricing"
    if host.startswith("indus.") and ("playground" in path):
        return "explore"
    if host.startswith("indus."):
        return "console"
    if host.endswith("sarvam.ai") and (path.rstrip("/").endswith("/models") or "playground" in frag or path.startswith("/try/")):
        return "explore"
    return None


def latest_capture(page):
    caps = sorted(glob.glob(os.path.join(PROJECT, "pages", page, "capture", "*-live", "hero.json")))
    return json.load(open(caps[-1], encoding="utf-8")) if caps else None


def page_destinations(page):
    """{kind: {id, kind, url, live_label, what_it_is, in_hero}} — hero links first, then the page's own links."""
    prof = json.load(open(os.path.join(PROJECT, "pages", page, "profile.json"), encoding="utf-8"))
    if (prof.get("hero") or {}).get("cta_destinations"):
        out = {}
        for d in prof["hero"]["cta_destinations"]:
            k = LEGACY_KIND.get(d["id"], d["id"])
            out.setdefault(k, dict(d, kind=k, id=k, in_hero=None))
        return out
    cap = latest_capture(page)
    if not cap:
        return {}
    page_path = urlparse(prof["url"]).path.rstrip("/")
    cands = [(c["text"], c["href"], True) for c in cap["ctas"] if c.get("href")] + \
            [(l["text"], l["href"], False) for l in cap.get("links", [])]
    out = {}
    for text, href, in_hero in cands:
        k = kind_of(href)
        if not k:
            continue
        own = bool(page_path) and page_path in urlparse(href).path
        score = (2 if in_hero else 0) + (1 if own else 0)
        if k not in out or score > out[k]["_score"]:
            out[k] = {"id": k, "kind": k, "url": href, "live_label": text, "in_hero": in_hero, "_score": score,
                      "what_it_is": "A link found on the saved page, labelled '%s'. What the visitor sees there is not checked." % text}
    for d in out.values():
        d.pop("_score", None)
    return out


def goals_for(page):
    goals = json.load(open(os.path.join(PROJECT, "rules", "goals.json"), encoding="utf-8"))["goals"]
    dests = page_destinations(page)
    return [dict(g, available=g["kind"] in dests, destination=dests.get(g["kind"])) for g in goals]


if __name__ == "__main__":
    for g in goals_for(sys.argv[1]):
        d = g["destination"]
        print(("YES " if g["available"] else "no  ") + g["label"].ljust(48), (d["url"] + "  [" + d["live_label"] + "]") if d else "")

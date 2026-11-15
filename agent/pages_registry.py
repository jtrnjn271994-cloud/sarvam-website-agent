#!/usr/bin/env python3
"""Page register: create a folder per page in pages/registry.json and save each hero once.

Run:  python3 agent/pages_registry.py --sync            create missing page folders (never overwrites)
      python3 agent/pages_registry.py --capture         capture pages with no capture yet (one live load each)
      python3 agent/pages_registry.py --capture --page voice-agents
A new folder holds only profile.json with the URL and status. It has no page pack, so the writer
cannot run on it until a person approves its claims and buyer checklist.
"""
import argparse
import glob
import json
import os
import subprocess
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(PROJECT, "pages", "registry.json")


def registry():
    return json.load(open(REG, encoding="utf-8"))["pages"]


def sync():
    for p in registry():
        d = os.path.join(PROJECT, "pages", p["slug"])
        prof = os.path.join(d, "profile.json")
        if os.path.isfile(prof):
            print("keep   ", p["slug"])
            continue
        os.makedirs(d, exist_ok=True)
        json.dump({"page": p["slug"], "name": p["name"], "url": p["url"], "layer": p["layer"],
                   "status": "captured only: no page pack. The writer cannot run until a person approves claims and a buyer checklist."},
                  open(prof, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print("created", p["slug"])


def capture(only=None):
    for p in registry():
        if only and p["slug"] != only:
            continue
        caps = glob.glob(os.path.join(PROJECT, "pages", p["slug"], "capture", "*-live", "hero.json"))
        if caps and not only:
            print("skip   ", p["slug"], "(already captured)")
            continue
        print("capture", p["slug"], p["url"], flush=True)
        r = subprocess.run([sys.executable, os.path.join(PROJECT, "agent", "capture_hero.py"), "--page", p["slug"]],
                           cwd=PROJECT, capture_output=True, text=True, timeout=180)
        print("   " + (r.stdout.strip().replace("\n", "\n   ") or r.stderr.strip()[-400:]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sync", action="store_true")
    ap.add_argument("--capture", action="store_true")
    ap.add_argument("--page")
    a = ap.parse_args()
    if a.sync:
        sync()
    if a.capture:
        capture(a.page)

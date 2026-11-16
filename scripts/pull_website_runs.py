#!/usr/bin/env python3
"""Copy runs made on the website (saved in Supabase) to this machine, so you can commit them to GitHub.

  python3 -I scripts/pull_website_runs.py                  # list what the website has that this machine does not
  python3 -I scripts/pull_website_runs.py --write          # copy the website runs into pages/<page>/runs/
  python3 -I scripts/pull_website_runs.py --write --include-setup   # also copy page setup files made on the website

Safe by design:
  - It only reads Supabase. It never deletes or changes anything there.
  - It never overwrites a file on this machine. A file that exists here with different text is listed and skipped.
  - Paths must match the same safe pattern the website uses, so nothing is written outside pages/.
  - Keys come from .env and are never printed.
Afterwards: look at the runs in the console (./run-ui.sh), then git add, commit and push if you want them on GitHub.
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "agent"))
import envload  # noqa: E402,F401  (loads .env into the environment; prints nothing)

SAFE_PATH = re.compile(r"^pages/[a-z0-9-]+/(runs/probe3-\d{8}-\d{6}/(sandbox/)?|setup/|claims/|evidence/)[A-Za-z0-9._-]+$|^pages/[a-z0-9-]+/[A-Za-z0-9._-]+\.(json|csv)$|^pages/registry\.json$")


def sb(path):
    url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/" + path
    key = os.environ["SUPABASE_SERVICE_KEY"]
    req = urllib.request.Request(url, headers={"apikey": key, "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", help="copy the files (without it, only list them)")
    ap.add_argument("--include-setup", action="store_true", help="also copy setup, claims and evidence files")
    a = ap.parse_args()
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY"):
        if not os.environ.get(k):
            sys.exit("Missing %s in .env. Nothing was copied." % k)

    rows = sb("sarvam_agent_files?select=path,updated_at&order=path")
    new, same, differ, setup_skipped, unsafe = [], 0, [], [], 0
    for r in rows:
        p = r["path"]
        if not SAFE_PATH.match(p) or ".." in p:
            unsafe += 1
            continue
        if "/runs/" not in p and not a.include_setup:
            setup_skipped.append(p)
            continue
        new.append(p)

    to_copy = []
    for i in range(0, len(new), 40):
        chunk = new[i:i + 40]
        q = "sarvam_agent_files?select=path,content&path=in.(" + ",".join("%22" + urllib.parse.quote(p, safe="/._-") + "%22" for p in chunk) + ")"
        for r in sb(q):
            dest = os.path.join(ROOT, r["path"])
            if os.path.isfile(dest):
                if open(dest, encoding="utf-8", errors="replace").read() == r["content"]:
                    same += 1
                else:
                    differ.append(r["path"])
                continue
            to_copy.append((r["path"], r["content"]))

    runs = sorted({"/".join(p.split("/")[:4]) for p, _ in to_copy if "/runs/" in p})
    print("Website files in Supabase: %d" % len(rows))
    print("Already on this machine, same text: %d" % same)
    print("New here: %d files in %d run folders" % (len(to_copy), len(runs)))
    for r in runs:
        print("   " + r)
    for p, _ in to_copy:
        if "/runs/" not in p:
            print("   setup file: " + p)
    if differ:
        print("Skipped, a different copy is already here (compare by hand): %d" % len(differ))
        for p in differ:
            print("   " + p)
    if setup_skipped:
        print("Setup files on the website not copied (add --include-setup): %d" % len(setup_skipped))
        for p in setup_skipped:
            print("   " + p)
    if unsafe:
        print("Ignored, path not allowed: %d" % unsafe)

    if not a.write:
        print("\nNothing was written. Run again with --write to copy the new files.")
        return
    for p, content in to_copy:
        dest = os.path.join(ROOT, p)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "x", encoding="utf-8") as f:   # "x": fails rather than overwrite
            f.write(content)
    print("\nCopied %d files. Open ./run-ui.sh to look at them, then commit and push if you want them on GitHub." % len(to_copy))


if __name__ == "__main__":
    main()

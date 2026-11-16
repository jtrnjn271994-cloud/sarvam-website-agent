#!/usr/bin/env python3
"""Write a RUN-STORY.json for each website run that does not have a current one, and save it to Supabase.

Default is a dry run: it lists the website runs and makes no model call and no write.
  python3 -I scripts/backfill_website_stories.py            # dry run
  python3 -I scripts/backfill_website_stories.py --write    # one model call per run (about $0.001 each), then one upsert per story
It reads SUPABASE_URL, SUPABASE_SERVICE_KEY and OPENROUTER_API_KEY from .env (agent/envload). It prints no value.
It only ever writes rows whose path is pages/<page>/runs/<run>/RUN-STORY.json. It touches no other row.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROJECT, "agent"))
import envload  # noqa: E402,F401
import run_story  # noqa: E402

RUN_PATH = re.compile(r"^pages/([a-z0-9-]+)/runs/(probe3-\d{8}-\d{6})/([\w./-]+)$")
TABLE = "sarvam_agent_files"


def sb(method, path, body=None, prefer=None):
    url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/" + path
    key = os.environ["SUPABASE_SERVICE_KEY"]
    h = {"apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json"}
    if prefer:
        h["Prefer"] = prefer
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h, method=method), timeout=30) as r:
            t = r.read().decode("utf-8")
            return json.loads(t) if t else None
    except urllib.error.HTTPError as e:
        raise RuntimeError("storage error %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:200]))


def website_runs():
    """{(page, run): [paths]} for every run that has a probe3.json row."""
    rows = sb("GET", TABLE + "?select=path&path=like.pages/*/runs/*&limit=5000") or []
    runs = {}
    for r in rows:
        m = RUN_PATH.match(r["path"])
        if m:
            runs.setdefault((m.group(1), m.group(2)), []).append(r["path"])
    return {k: v for k, v in runs.items() if "pages/%s/runs/%s/probe3.json" % k in v}


def build_tree(page, run, paths):
    """A temp project: the run's files from Supabase, everything else linked to the real project."""
    tmp = tempfile.mkdtemp(prefix="story-backfill-")
    for name in ("rules", "skills", "knowledge", "library"):
        if os.path.exists(os.path.join(PROJECT, name)):
            os.symlink(os.path.join(PROJECT, name), os.path.join(tmp, name))
    os.makedirs(os.path.join(tmp, "pages", page, "runs"))
    reg = os.path.join(PROJECT, "pages", "registry.json")
    if os.path.exists(reg):
        os.symlink(reg, os.path.join(tmp, "pages", "registry.json"))
    for name in os.listdir(os.path.join(PROJECT, "pages", page)) if os.path.isdir(os.path.join(PROJECT, "pages", page)) else []:
        if name != "runs":
            os.symlink(os.path.join(PROJECT, "pages", page, name), os.path.join(tmp, "pages", page, name))
    for i in range(0, len(paths), 20):
        chunk = paths[i:i + 20]
        q = TABLE + "?select=path,content&path=in.(" + ",".join("%22" + urllib.parse.quote(p, safe="/._-") + "%22" for p in chunk) + ")"
        for r in sb("GET", q) or []:
            dest = os.path.join(tmp, r["path"])
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(r["content"])
    return tmp


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", help="list only (the default)")
    g.add_argument("--write", action="store_true", help="make the stories and save them")
    a = ap.parse_args()
    if not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY")):
        sys.exit("SUPABASE_URL and SUPABASE_SERVICE_KEY are not set (.env). Nothing done.")
    os.environ.pop("AGENT_HOSTED", None)   # this runs on your machine; its model calls go to a temp log, not a run log
    runs = website_runs()
    print("%d website run(s) found in %s" % (len(runs), TABLE))
    done = spent = 0
    for (page, run), paths in sorted(runs.items()):
        have = "pages/%s/runs/%s/RUN-STORY.json" % (page, run) in paths
        if not a.write:
            print("  %s/%s: %s" % (page, run, "has a story (checked for changes on --write)" if have else "no story yet: 1 model call on --write"))
            continue
        tmp = build_tree(page, run, paths)
        try:
            rec = run_story.write(page, run, root=tmp)
            path = os.path.join(tmp, "pages", page, "runs", run, run_story.NAME)
            rel = "pages/%s/runs/%s/%s" % (page, run, run_story.NAME)
            if not rec:
                print("  %s/%s: no story (no audit, or the check rejected it)" % (page, run))
                continue
            stored = rec.get("tries") is not None and rec.get("at")
            fresh = bool(stored) and (datetime.datetime.now() - datetime.datetime.fromisoformat(rec["at"])).total_seconds() < 600
            if not fresh:
                print("  %s/%s: story is current, nothing saved" % (page, run))
                continue
            row = {"path": rel, "page": page, "content": open(path, encoding="utf-8").read(), "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
            sb("POST", TABLE, [row], prefer="resolution=merge-duplicates,return=minimal")
            done += 1
            spent += float(rec.get("cost_usd") or 0)
            print("  %s/%s: story saved (tries %d, $%.5f)" % (page, run, rec["tries"], rec["cost_usd"]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    if a.write:
        print("%d story(ies) saved, model cost $%.4f" % (done, spent))
    else:
        print("Dry run: no model call, no write. Use --write to make and save the stories.")


if __name__ == "__main__":
    main()

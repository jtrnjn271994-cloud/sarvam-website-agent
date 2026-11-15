#!/usr/bin/env python3
"""Website (Vercel) mode for the console. Standard library only.

The website runs the same server code as the local console (app/server.py), with four differences:
  1. Files. The project ships read-only inside the function. Each request works in a writable copy in /tmp:
     code, rules and knowledge are links to the read-only copy; each page's setup, claims and evidence are copied;
     saved runs are links (read-only). Runs, approvals and setup files made on the website are saved to Supabase
     (table sarvam_agent_files) and loaded back into /tmp on the next request, on any server instance.
  2. Jobs. A run, a sandbox or a page setup draft runs inside the request (up to about 4.5 minutes), not in the
     background. Its log and result go to Supabase (table sarvam_agent_jobs), so status works across instances.
  3. Limits. One job at a time. A daily spend cap for the whole site and a daily run limit per visitor.
     Page setup (drafting and approving positioning and claims) needs the owner code (OWNER_TOKEN).
  4. No browser. Website runs take no screenshots and never load sarvam.ai. The sandbox reads the saved page's
     HTML instead of opening it in a browser, and the findings say so.

Settings (Vercel environment variables, never in a file in the repo):
  OPENROUTER_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, OWNER_TOKEN
  optional: DAILY_USD_CAP (default 3.00), RUNS_PER_VISITOR_PER_DAY (default 3), MAX_RUN_USD (default 1.00)

Local test (uses the same Supabase tables):  python3 app/hosted.py --port 8790
"""
import datetime
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BUNDLE = os.environ.get("AGENT_BUNDLE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.environ.get("AGENT_WORK") or "/tmp/sarvam-agent"
os.environ["AGENT_HOSTED"] = "1"
LINK = ["agent", "rules", "knowledge", "library", "skills", "templates", "schemas", "docs", "submission", "app", "tests", "README.md"]
TEXT = (".json", ".jsonl", ".md", ".csv", ".txt", ".html")
SAFE_PATH = re.compile(r"^pages/[a-z0-9-]+/(runs/probe3-\d{8}-\d{6}/(sandbox/)?|setup/|claims/|evidence/)[A-Za-z0-9._-]+$|^pages/[a-z0-9-]+/[A-Za-z0-9._-]+\.(json|csv)$|^pages/registry\.json$")
JOB_SECONDS = 265        # the function stops at 300 s; leave room to save the result
STALE_SECONDS = 330      # a "running" job older than this was cut off
CTX = threading.local()
SYNCED = {}
SYNC_LOCK = threading.Lock()


# ---------- the writable copy in /tmp ----------

def build_work():
    if os.path.isdir(os.path.join(WORK, "pages")):
        return
    tmp = WORK + ".building-%d" % os.getpid()
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(os.path.join(tmp, "pages"))
    for name in LINK:
        if os.path.exists(os.path.join(BUNDLE, name)):
            os.symlink(os.path.join(BUNDLE, name), os.path.join(tmp, name))
    src_pages = os.path.join(BUNDLE, "pages")
    for name in os.listdir(src_pages):
        src = os.path.join(src_pages, name)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(tmp, "pages", name))
            continue
        dst = os.path.join(tmp, "pages", name)
        os.makedirs(os.path.join(dst, "runs"))
        for child in os.listdir(src):
            s = os.path.join(src, child)
            if child == "runs":
                for r in os.listdir(s):
                    os.symlink(os.path.join(s, r), os.path.join(dst, "runs", r))   # saved runs stay read-only
            elif child == "capture":
                os.symlink(s, os.path.join(dst, child))
            elif os.path.isdir(s):
                shutil.copytree(s, os.path.join(dst, child))
            else:
                shutil.copy(s, os.path.join(dst, child))
    try:
        os.rename(tmp, WORK)
    except OSError:   # another thread built it first
        shutil.rmtree(tmp, ignore_errors=True)


build_work()
sys.path.insert(0, os.path.join(WORK, "app"))
import server  # noqa: E402  (the local console's code, working on the /tmp copy)


# ---------- Supabase (REST, service key, server side only) ----------

def sb(method, path, body=None, prefer=None):
    url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/" + path
    key = os.environ["SUPABASE_SERVICE_KEY"]
    h = {"apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json"}
    if prefer:
        h["Prefer"] = prefer
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            t = r.read().decode("utf-8")
            return json.loads(t) if t else None
    except urllib.error.HTTPError as e:
        raise RuntimeError("storage error %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:300]))


def hydrate():
    """Bring files saved by earlier website requests into this instance's /tmp copy."""
    rows = sb("GET", "sarvam_agent_files?select=path,updated_at")
    with SYNC_LOCK:
        want = [r["path"] for r in rows if SYNCED.get(r["path"]) != r["updated_at"] and SAFE_PATH.match(r["path"])]
        for i in range(0, len(want), 40):
            chunk = want[i:i + 40]
            q = "sarvam_agent_files?select=path,content,updated_at&path=in.(" + ",".join("%22" + urllib.parse.quote(p, safe="/._-") + "%22" for p in chunk) + ")"
            for r in sb("GET", q):
                dest = os.path.join(WORK, r["path"])
                parent = os.path.dirname(dest)
                if os.path.islink(parent):   # never write into a saved (read-only) run
                    continue
                os.makedirs(parent, exist_ok=True)
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(r["content"])
                SYNCED[r["path"]] = r["updated_at"]


def snapshot(page):
    out = {}
    root = os.path.join(WORK, "pages", page)
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if not os.path.islink(os.path.join(d, x))]
        for f in files:
            p = os.path.join(d, f)
            if f.endswith(TEXT) and not os.path.islink(p):
                out[os.path.relpath(p, WORK)] = os.path.getmtime(p)
    reg = os.path.join(WORK, "pages", "registry.json")
    if os.path.isfile(reg):
        out["pages/registry.json"] = os.path.getmtime(reg)
    return out


def push(before, page):
    """Save every text file that is new or changed since `before` to Supabase."""
    now = snapshot(page)
    rows = []
    for rel, m in now.items():
        if before.get(rel) == m or not SAFE_PATH.match(rel):
            continue
        rows.append({"path": rel, "page": page, "content": open(os.path.join(WORK, rel), encoding="utf-8", errors="replace").read(),
                     "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    for i in range(0, len(rows), 20):
        sb("POST", "sarvam_agent_files", rows[i:i + 20], prefer="resolution=merge-duplicates,return=minimal")
    with SYNC_LOCK:
        for r in rows:
            SYNCED[r["path"]] = None   # re-read the stored timestamp on the next hydrate; content is already local
    return [r["path"] for r in rows]


# ---------- jobs, the one-job lock and the spend caps ----------

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def iso(t):
    return urllib.parse.quote(t.isoformat())


def guard(kind):
    since = utcnow() - datetime.timedelta(seconds=STALE_SECONDS)
    if sb("GET", "sarvam_agent_jobs?select=id&status=eq.running&started_at=gt." + iso(since)):
        raise RuntimeError("a run or sandbox is already going on the website; one at a time. Try again in a few minutes.")
    day = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today = sb("GET", "sarvam_agent_jobs?select=cost_usd,ip_hash,kind,status&started_at=gte." + iso(day))
    cap = float(os.environ.get("DAILY_USD_CAP", "3.00"))
    spent = sum(float(r["cost_usd"] or 0) for r in today)
    if spent >= cap:
        raise RuntimeError("the website's daily spend cap ($%.2f) is used up. Try tomorrow, or run the agent on your own machine (see the README)." % cap)
    per = int(os.environ.get("RUNS_PER_VISITOR_PER_DAY", "3"))
    if kind == "run" and not CTX.owner and sum(1 for r in today if r["ip_hash"] == CTX.ip and r["kind"] == "run") >= per:
        raise RuntimeError("you have started %d runs today, the daily limit per visitor. Browse the saved runs, or run the agent on your own machine." % per)


def run_cost(paths):
    usd = 0.0
    for rel in paths:
        if rel.endswith("run-log.jsonl"):
            for line in open(os.path.join(WORK, rel), encoding="utf-8", errors="replace"):
                try:
                    usd += float(json.loads(line).get("cost") or 0)
                except ValueError:
                    pass
    return round(usd, 4)


def hosted_start_job(slug, cmd, kind, run):
    """Replaces server.start_job: run the job inside this request and save its files and log."""
    guard(kind)
    if kind == "run":
        cmd = cmd + ["--no-png"]
    job = sb("POST", "sarvam_agent_jobs", {"kind": kind, "page": slug, "run": run, "persona": CTX.body.get("persona"),
                                           "goal": CTX.body.get("goal"), "ip_hash": CTX.ip}, prefer="return=representation")[0]
    before = snapshot(slug)
    runs_before = set(os.listdir(os.path.join(WORK, "pages", slug, "runs")))
    proc = subprocess.Popen(cmd, cwd=WORK, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            env=dict(os.environ, PYTHONUNBUFFERED="1", TZ="Asia/Kolkata"))   # run names in India time, like local runs
    lines = []
    reader = threading.Thread(target=lambda: [lines.append(x) for x in proc.stdout], daemon=True)
    reader.start()
    start, last, timed_out = time.time(), 0.0, False
    while proc.poll() is None:
        if time.time() - start > JOB_SECONDS:
            proc.kill()
            timed_out = True
            break
        if time.time() - last > 4:
            sb("PATCH", "sarvam_agent_jobs?id=eq.%d" % job["id"], {"log": "".join(lines)[-20000:]}, prefer="return=minimal")
            last = time.time()
        time.sleep(0.5)
    proc.wait()
    reader.join(timeout=5)
    log = "".join(lines)
    if timed_out:
        log += "\nSTOPPED: the job passed the website's time limit (%d seconds). Run it on your own machine (see the README)." % JOB_SECONDS
    saved = push(before, slug)
    fresh = sorted(set(os.listdir(os.path.join(WORK, "pages", slug, "runs"))) - runs_before)
    ok = proc.returncode == 0 and not timed_out
    sb("PATCH", "sarvam_agent_jobs?id=eq.%d" % job["id"],
       {"status": "done" if ok else "failed", "finished_at": utcnow().isoformat(), "log": log[-20000:],
        "run": fresh[-1] if fresh else run, "cost_usd": run_cost(saved), "error": None if ok else "exit %s" % proc.returncode},
       prefer="return=minimal")
    return hosted_status()


server.start_job = hosted_start_job


def hosted_status():
    rows = sb("GET", "sarvam_agent_jobs?select=*&order=started_at.desc&limit=1")
    cap = float(os.environ.get("MAX_RUN_USD", "1.00"))
    if not rows:
        return {"running": False, "page": None, "started": None, "kind": None, "exit_code": None, "log": "", "new_run": None, "spend_cap_usd": cap}
    j = rows[0]
    started = datetime.datetime.fromisoformat(j["started_at"].replace("Z", "+00:00"))
    stale = j["status"] == "running" and (utcnow() - started).total_seconds() > STALE_SECONDS
    running = j["status"] == "running" and not stale
    return {"running": running, "page": j["page"], "started": started.strftime("%Y-%m-%d %H:%M UTC"), "kind": j["kind"],
            "exit_code": None if running else (0 if j["status"] == "done" else 1),
            "log": (j["log"] or "") + ("\nSTOPPED: this job was cut off by the website's time limit." if stale else ""),
            "new_run": j["run"], "spend_cap_usd": cap}


# ---------- HTTP ----------

def owner_ok(headers):
    tok = os.environ.get("OWNER_TOKEN") or ""
    got = headers.get("X-Owner-Token") or ""
    return bool(tok) and hmac.compare_digest(tok.encode(), got.encode())


def visitor(headers):
    ip = (headers.get("X-Forwarded-For") or headers.get("X-Real-Ip") or "unknown").split(",")[0].strip()
    salt = os.environ.get("OWNER_TOKEN") or "salt"
    return hashlib.sha256((salt + ip).encode()).hexdigest()[:16]


def read_only_run(page, run):
    return bool(run) and os.path.islink(os.path.join(WORK, "pages", page or "", "runs", run))


class handler(server.Handler):   # Vercel looks for a class named `handler`
    server_version = "AgentWebsite/1"

    def host_ok(self):
        return True

    def route(self):
        p = urlparse(self.path)
        path = p.path
        q = parse_qs(p.query)
        if path in ("/api/index", "/api/index.py") and q.get("p"):   # rewritten URL
            path = "/api/" + q["p"][0]
        return path, p.query

    def do_GET(self):
        path, query = self.route()
        try:
            if path == "/api/live":
                return self.send(200, {"hosted": True, "daily_usd_cap": float(os.environ.get("DAILY_USD_CAP", "3.00")),
                                       "runs_per_visitor_per_day": int(os.environ.get("RUNS_PER_VISITOR_PER_DAY", "3")),
                                       "max_run_usd": float(os.environ.get("MAX_RUN_USD", "1.00")),
                                       "key_set": bool(os.environ.get("OPENROUTER_API_KEY"))})
            hydrate()
            if path == "/api/status":
                return self.send(200, hosted_status())
        except RuntimeError as e:
            return self.send(503, {"error": str(e)})
        self.path = path + ("?" + query if query else "")
        return super().do_GET()

    def do_POST(self):
        origin = self.headers.get("Origin")
        host = (self.headers.get("Host") or "").split(":")[0]
        if self.headers.get("X-Agent-Console") != "1" or (origin and urlparse(origin).hostname != host):
            return self.send(403, {"error": "requests must come from this website"})
        path, _ = self.route()
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            CTX.body, CTX.ip, CTX.owner = body, visitor(self.headers), owner_ok(self.headers)
            page = body.get("page")
            if not page or not server.SLUG.match(page):
                raise ValueError("unknown page")
            hydrate()
            if path in ("/api/setup/draft", "/api/setup/approve") and not CTX.owner:
                return self.send(403, {"error": "page setup needs the owner code. Runs, approvals and the sandbox do not."})
            if path in ("/api/approve", "/api/sandbox") and read_only_run(page, body.get("run")):
                raise ValueError("this run was made on the owner's machine and is read-only on the website. Start a new run to approve and test a variant.")
            if path == "/api/start":
                return self.send(200, server.start_run(page, body.get("persona"), body.get("goal")))
            if path == "/api/sandbox":
                return self.send(200, server.start_sandbox(page, body.get("run")))
            if path == "/api/setup/draft":
                return self.send(200, server.start_setup(page, body.get("persona")))
            before = snapshot(page)
            if path == "/api/approve":
                if body.get("name"):
                    body["name"] = "a person"   # the website is public: never store a visitor's typed name
                out = server.approve(body)
            elif path == "/api/setup/approve":
                body["name"] = "the owner"
                out = server.setup_approve(body)
            else:
                return self.send(404, {"error": "not found"})
            push(before, page)
            return self.send(200, out)
        except ValueError as e:
            return self.send(400, {"error": str(e)})
        except RuntimeError as e:
            return self.send(409, {"error": str(e)})


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8790)
    a = ap.parse_args()

    class Local(handler):   # local test: also serve the page itself
        def do_GET(self):
            if urlparse(self.path).path in ("/", "/index.html"):
                return self.send(200, open(os.path.join(WORK, "app", "index.html"), "rb").read(), "text/html; charset=utf-8")
            return super().do_GET()
    print("website mode on http://127.0.0.1:%d (work copy %s)" % (a.port, WORK))
    ThreadingHTTPServer(("127.0.0.1", a.port), Local).serve_forever()


if __name__ == "__main__":
    main()

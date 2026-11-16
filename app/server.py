#!/usr/bin/env python3
"""Local console for the website agent. Standard library only.

Run (from the project folder):
  python3 app/server.py                 # opens http://127.0.0.1:8765
  python3 app/server.py --port 9000
  python3 app/server.py --export out/   # writes a read-only static copy (for a later Vercel deploy);
                                        # approver names become "a person"; FINDINGS.md is copied as written

What it does:
  - Shows each run as the 12 architecture steps: who acted, which model, calls, cost and result.
  - Shows the audit, the gap dossier, the variants with their gate results and the PNG pairs.
  - Shows the judge questions: universal ones, page ones, scope tags and the approval state.
  - Starts a new run of agent/probe3.py in the background (one at a time) and streams its log.
    Each run starts a fresh Python process, so code you edit in agent/ is used by the next run.

What it does not do:
  - It never approves anything. Approval (step 10) is not built yet.
  - It never serves .env or any file outside the allowed run, capture and rules files.
  - It listens on 127.0.0.1 only.
"""
import argparse
import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

APP = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(APP)
PAGES = os.path.join(PROJECT, "pages")
LOGS = os.path.join(PROJECT, "logs", "ui")
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RUN_NAME = re.compile(r"^probe3-\d{8}-\d{6}$")
DOCS = {"readme": "README.md", "architecture": "docs/architecture.md", "architecture-html": "docs/architecture.html", "jev": "submission/JEV-NOTE.md"}
FILE_NAME = re.compile(r"^[A-Za-z0-9._-]+\.(png|md|html|json|jsonl)$")
TYPES = {".png": "image/png", ".md": "text/plain; charset=utf-8", ".html": "text/html; charset=utf-8",
         ".json": "application/json; charset=utf-8", ".jsonl": "text/plain; charset=utf-8"}

sys.path.insert(0, os.path.join(PROJECT, "docs"))
import build_architecture as arch  # noqa: E402  (tables only; it writes nothing on import)
sys.path.insert(0, os.path.join(PROJECT, "agent"))
import shortlist  # noqa: E402
import page_setup as setup  # noqa: E402
import destinations as dst  # noqa: E402
import run_flow  # noqa: E402

STATE = {"proc": None, "page": None, "log": None, "started": None, "run_before": None}
LOCK = threading.Lock()

# Which log purposes belong to which architecture step (first matching prefix wins).
PURPOSE_STEP = [("audit live baseline judge2", "8"), ("audit live baseline", "4"), ("dossier", "5"),
                ("writer", "7"), ("gate2", "8"), ("audit variant", "8")]
BUILT = {"1": "built", "2": "built", "3": "saved", "4": "built", "5": "built", "6": "not built",
         "7": "built", "8": "built", "9": "partly built", "10": "built", "11": "built", "12": "partly built"}


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def front_matter(path):
    try:
        txt = open(path, encoding="utf-8").read()
    except OSError:
        return {}, ""
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, re.S)
    d = {}
    for line in (m.group(1) if m else "").split("\n"):
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            d[k.strip()] = v.strip().strip('"')
    return d, (m.group(2) if m else txt)


def pages():
    """Pages in registry order, with whether a page pack exists (only then can a run start)."""
    reg = {p["slug"]: p for p in (read_json(os.path.join(PAGES, "registry.json"), {}) or {}).get("pages", [])}
    order = list(reg) + sorted(d for d in os.listdir(PAGES) if d not in reg)
    out = []
    for d in order:
        prof = read_json(os.path.join(PAGES, d, "profile.json"))
        if SLUG.match(d) and prof:
            r = reg.get(d, {})
            out.append({"slug": d, "url": prof.get("url"), "name": prof.get("name") or r.get("name") or d,
                        "layer": r.get("layer"), "traffic_in": r.get("traffic_in"), "ready": setup.status(d)["ready"],
                        "captured": bool(setup.capture_dir(d)),
                        "status": r.get("status") or prof.get("status")})
    return out


def page_dir(slug):
    if not SLUG.match(slug or "") or not os.path.isfile(os.path.join(PAGES, slug, "profile.json")):
        raise ValueError("unknown page")
    return os.path.join(PAGES, slug)


def run_dir(slug, run):
    if not RUN_NAME.match(run or ""):
        raise ValueError("bad run name")
    d = os.path.join(page_dir(slug), "runs", run)
    if not os.path.isdir(d):
        raise ValueError("unknown run")
    return d


def runs(slug):
    out = []
    for d in sorted(glob.glob(os.path.join(page_dir(slug), "runs", "probe3-*")), reverse=True):
        name = os.path.basename(d)
        if not RUN_NAME.match(name):
            continue
        p = read_json(os.path.join(d, "probe3.json"), {})
        g2 = p.get("gate2") or {}
        out.append({"run": name, "cost_usd": p.get("cost_usd"), "calls": p.get("calls"),
                    "persona": (p.get("persona") or {}).get("key"), "goal": (p.get("goal") or {}).get("id"),
                    "complete": "cost_usd" in p, "writer": (p.get("roles") or {}).get("writer"),
                    "passed": [k for k, v in g2.items() if v.get("pass")], "variants": len(p.get("variants") or []),
                    "gaps": (p.get("audit") or {}).get("gaps")})
    return out


def questions(slug, key=None):
    q = read_json(os.path.join(PROJECT, "rules", "judge-questions.json"), {})
    th = read_json(os.path.join(PROJECT, "rules", "judge-thresholds.json"), {})
    prof = read_json(os.path.join(page_dir(slug), "profile.json"), {})
    cff = setup.checklist_file(slug, key) if key else None
    cf = os.path.relpath(cff, page_dir(slug)) if cff else None
    meta, body = front_matter(cff) if cff else ({}, "")
    appr = [e for e in setup.approvals(slug)["entries"] if key and e["part"] == "checklist:" + key and e["decision"] == "approve"]
    if key and setup.part_state(slug, "checklist:" + key) == "approved" and appr:
        meta["questions_approved_by"], meta["questions_approved_on"] = appr[-1]["name"], appr[-1]["at"]
    else:
        meta["questions_approved_by"], meta["questions_approved_on"] = "", ""
    block = re.search(r"## Questions the page must answer\n\n(.*?)\n\n##", body, re.S)
    tagged = re.findall(r"^- \[(hero|page)\] (.+)$", block.group(1) if block else "", re.M)
    return {"universal": [x for x in q.get("audit", {}).get("questions", []) if not x.get("fill")],
            "page_templates": [x for x in q.get("audit", {}).get("questions", []) if x.get("fill")],
            "gate2": q.get("gate2", {}).get("questions", []), "better_than_baseline": q.get("gate2", {}).get("better_than_baseline"),
            "note": q.get("note_v3"), "thresholds": th, "checklist_file": cf, "checklist_title": meta.get("title"),
            "checklist_label": meta.get("label"), "items": [{"scope": s, "text": t} for s, t in tagged],
            "main_objection": meta.get("main_objection"),
            "approved_by": meta.get("questions_approved_by"), "approved_on": meta.get("questions_approved_on")}


def steps_for(slug, run):
    d = run_dir(slug, run)
    p = read_json(os.path.join(d, "probe3.json"), {})
    calls = {}
    try:
        for line in open(os.path.join(d, "run-log.jsonl"), encoding="utf-8"):
            r = json.loads(line)
            step = next((s for pre, s in PURPOSE_STEP if r.get("purpose", "").startswith(pre)), "other")
            c = calls.setdefault(step, {"calls": 0, "cost": 0.0, "seconds": 0.0, "models": set()})
            c["calls"] += 1
            c["cost"] += r.get("cost") or 0
            c["seconds"] += r.get("seconds") or 0
            c["models"].add(r.get("answered_model") or r.get("asked_model"))
    except OSError:
        pass
    files = sorted(f for f in os.listdir(d) if FILE_NAME.match(f))
    out = []
    for n, name, who, model, reads, makes in arch.STEPS:
        c = calls.get(n)
        out.append({"n": n, "name": name, "who": who, "model_plan": model, "reads": reads, "makes": makes,
                    "built": BUILT.get(n, "not built"),
                    "calls": c["calls"] if c else 0, "cost": round(c["cost"], 4) if c else 0,
                    "seconds": round(c["seconds"], 1) if c else 0, "models": sorted(m for m in c["models"] if m) if c else []})
    approval = read_json(os.path.join(d, "approval.json"), {"entries": []})
    sandbox = read_json(os.path.join(d, "sandbox", "sandbox-results.json"))
    return {"steps": out, "probe": p, "files": files, "shortlist": shortlist.classify(p) if p.get("variants") else [],
            "approval": approval, "current_approval": shortlist.current_approval_of(approval.get("entries")), "sandbox": sandbox,
            "other_calls": {k: (v["calls"], round(v["cost"], 4)) for k, v in calls.items() if k == "other"}}


def capture_info(slug):
    caps = sorted(glob.glob(os.path.join(page_dir(slug), "capture", "*-live", "hero.json")))
    if not caps:
        return None
    h = read_json(caps[-1], {})
    folder = os.path.basename(os.path.dirname(caps[-1]))
    return {"folder": folder, "h1": h.get("h1"), "sub": h.get("sub"), "ctas": h.get("ctas"),
            "captured_at": h.get("captured_at"), "url": h.get("url"), "label": h.get("label")}


def status():
    with LOCK:
        proc = STATE["proc"]
        running = proc is not None and proc.poll() is None
        tail = ""
        if STATE["log"] and os.path.isfile(STATE["log"]):
            tail = open(STATE["log"], encoding="utf-8", errors="replace").read()[-20000:]
        new_run = None
        if STATE["page"]:
            now = [os.path.basename(x) for x in glob.glob(os.path.join(PAGES, STATE["page"], "runs", "probe3-*"))]
            fresh = sorted(set(now) - set(STATE["run_before"] or []))
            new_run = fresh[-1] if fresh else None
        if STATE.get("kind") in ("sandbox", "edit"):
            new_run = STATE.get("job_run")
        return {"running": running, "page": STATE["page"], "started": STATE["started"], "kind": STATE.get("kind"),
                "exit_code": None if (proc is None or running) else proc.returncode,
                "log": tail, "new_run": new_run, "spend_cap_usd": float(os.environ.get("MAX_RUN_USD", "1.00"))}


def approve(body):
    """A person's decision on one variant. Append-only; the latest entry counts. Rules are enforced here."""
    slug, run, name = body.get("page"), body.get("run"), (body.get("name") or "").strip()
    d = run_dir(slug, run)
    decision = body.get("decision")
    if decision not in ("approve", "reject", "revise"):
        raise ValueError("decision must be approve, reject or revise")
    name = name or "Console user"   # optional: the record keeps who clicked if they typed a name
    if len(name) > 80:
        raise ValueError("name is too long (80 characters at most)")
    p = read_json(os.path.join(d, "probe3.json"), {})
    groups = {x["name"]: x for x in shortlist.classify(p)}
    v = next((x for x in p.get("variants") or [] if x["name"] == body.get("variant")), None)
    if not v or v["name"] not in groups:
        raise ValueError("no such variant in this run")
    g = groups[v["name"]]
    if g["group"] == "failed_gate1":
        raise ValueError("a variant that failed Gate 1 (rules) cannot be chosen (Decisions Log row 33)")
    reason = (body.get("reason") or "").strip()
    note = (body.get("note") or "").strip()
    if decision == "approve" and g["group"] != "passed" and len(reason) < 10:
        raise ValueError("this variant did not pass Gate 2: type the reason you are choosing it (at least 10 characters)")
    if decision == "revise" and len(note) < 5:
        raise ValueError("type what the writer should change")
    png = os.path.join(d, "pair-%s.png" % v["name"])
    hosted = p.get("screenshots") == "not taken (website run)"   # the website takes no screenshots; the variant hash is the check
    if decision == "approve" and not hosted and not os.path.isfile(png):
        raise ValueError("no PNG pair for this variant, so it cannot be approved")
    entry = {"decision": decision, "variant": v["name"], "group_at_decision": g["group"], "reasons_shown": g["reasons"],
             "override": decision == "approve" and g["group"] != "passed", "name": name, "reason": reason, "note": note,
             "at": datetime.datetime.now().isoformat(timespec="seconds"),
             "variant_hash": shortlist.variant_hash(v), "png_hash": shortlist.file_hash(png) if os.path.isfile(png) else None,
             "made_by": "a person, on the website (no screenshot: website runs take none)" if hosted else "a person, in the local console"}
    path = os.path.join(d, "approval.json")
    with LOCK:
        data = read_json(path, {"note": "Append-only. The latest entry counts. Written only when a person clicks in the console.", "entries": []})
        data["entries"].append(entry)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, ensure_ascii=False)
    return data


def options(slug):
    """Dropdown options for one page: personas ordered by GTM fit for the page's product, and goals with real destinations."""
    page_dir(slug)
    reg = {p["slug"]: p for p in (read_json(os.path.join(PAGES, "registry.json"), {}) or {}).get("pages", [])}
    prod = (reg.get(slug) or {}).get("map_product")
    data = read_json(os.path.join(PROJECT, "library", "personas.json"), {"industries": []})
    inds = []
    for ind in data["industries"]:
        f = ind["fit"].get(prod) if prod else None
        inds.append({"id": ind["id"], "name": ind["name"], "fit": f, "fit_word": data["fit_words"].get(f) if f else "no fit data",
                     "roles": [{"key": r["key"], "role": r["role"], "titles": r["typical_titles"],
                               "checklist": setup.status(slug, r["key"])["parts"].get("checklist:" + r["key"], "missing")} for r in ind["roles"]]})
    inds.sort(key=lambda i: data["fit_order"].get(i["fit"], 9))
    goals = [{"id": g["id"], "label": g["label"], "kind": g["kind"], "available": g["available"],
              "url": (g["destination"] or {}).get("url"), "live_label": (g["destination"] or {}).get("live_label")} for g in dst.goals_for(slug)]
    bd = (read_json(os.path.join(PROJECT, "rules", "goals.json"), {}) or {}).get("buyer_default_goal", {})
    avail = {g["id"] for g in goals if g["available"]}
    gw = (read_json(os.path.join(PROJECT, "rules", "goals.json"), {}) or {}).get("buyer_goal_wording", {})
    gk = {g["id"]: g["kind"] for g in goals}
    for ind in inds:
        for r in ind["roles"]:
            slug_ = r["key"].split(":", 1)[1]
            prefs = next((v for k, v in bd.items() if k != "note" and slug_.startswith(k)), [])
            r["suggested_goal"] = next((x for x in prefs if x in avail), None)
            who = next((v for k, v in gw.get("buyers", {}).items() if slug_.startswith(k)), "visitors")
            order = ([r["suggested_goal"]] if r["suggested_goal"] else []) + [x["id"] for x in goals if x["id"] != r["suggested_goal"]]
            r["goals"] = [{"id": gid, "kind": gk[gid], "available": gid in avail,
                           "label": gw.get("templates", {}).get(gk[gid], "{buyers}").replace("{buyers}", ind["name"].lower().replace("&", "and") + " " + who if ind["id"] != "gcc" else who)} for gid in order]
    return {"industries": inds, "goals": goals, "map_product": prod}


def setup_info(slug, key):
    page_dir(slug)
    st = setup.status(slug, key or None)
    pf, promise = setup.positioning_file(slug)
    claims = []
    for f in sorted(glob.glob(os.path.join(PAGES, slug, "claims", "cl-*.md"))):
        m, _ = front_matter(f)
        evs = re.findall(r"EV-\d+", m.get("evidence_ids", ""))
        q = []
        for e in evs:
            ef = glob.glob(os.path.join(PAGES, slug, "evidence", "%s-*.md" % e.lower()))
            if ef:
                q.append(front_matter(ef[0])[0].get("quote", ""))
        claims.append({"id": m.get("id"), "text": m.get("text"), "label": m.get("label"), "keep": m.get("keep", ""), "quotes": q})
    cf = setup.checklist_file(slug, key) if key else None
    hist = setup.approvals(slug)["entries"]
    return {"status": st, "positioning": {"file": os.path.relpath(pf, PROJECT) if pf else None, "promise": promise,
                                          "check": setup.check_positioning(slug) if pf else [],
                                          "text": open(pf, encoding="utf-8").read() if pf else None},
            "claims": claims, "claims_check": read_json(os.path.join(PAGES, slug, "setup", "claims-check.json")),
            "checklist": {"file": os.path.relpath(cf, PROJECT) if cf else None, "text": open(cf, encoding="utf-8").read() if cf else None},
            "history": hist[-30:]}


def setup_approve(body):
    slug, part, name = body.get("page"), body.get("part") or "", (body.get("name") or "").strip()
    page_dir(slug)
    decision = body.get("decision")
    if decision not in ("approve", "reject"):
        raise ValueError("decision must be approve or reject")
    name = name or "Console user"   # optional: the record keeps who clicked if they typed a name
    if len(name) > 80:
        raise ValueError("name is too long (80 characters at most)")
    if part not in ("positioning", "claims") and not re.match(r"^checklist:[a-z]+:[a-z0-9-]+$", part):
        raise ValueError("unknown setup part")
    h = setup.part_hash(slug, part)
    if not h:
        raise ValueError("nothing to approve yet: draft it first")
    if part == "positioning" and decision == "approve":
        probs = setup.check_positioning(slug)
        if probs:
            raise ValueError("the positioning does not follow rules/positioning-structure.json yet: " + "; ".join(probs[:5]))
    note = (body.get("note") or "").strip()
    if decision == "reject" and len(note) < 5:
        raise ValueError("say what is wrong (it is kept with the record)")
    path = os.path.join(PAGES, slug, "setup", "approvals.json")
    with LOCK:
        data = read_json(path, {"note": "Append-only. Written only when a person clicks in the console. A part counts as approved while its file hash matches the latest approve.", "entries": []})
        data["entries"].append({"part": part, "decision": decision, "hash": h, "name": name, "note": note,
                                "at": datetime.datetime.now().isoformat(timespec="seconds"), "made_by": "a person, in the local console"})
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, ensure_ascii=False)
    return setup_info(slug, part.split(":", 1)[1] if part.startswith("checklist:") else body.get("persona"))


def start_setup(slug, key):
    page_dir(slug)
    if key and not setup.persona(key):
        raise ValueError("unknown persona")
    cmd = [sys.executable, os.path.join(PROJECT, "agent", "page_setup.py"), "--page", slug] + (["--persona", key] if key else [])
    return start_job(slug, cmd, "setup", None)


def start_sandbox(slug, run):
    d = run_dir(slug, run)
    if not shortlist.current_approval(d):
        raise ValueError("approve a variant first; the sandbox tests only an approved variant")
    return start_job(slug, [sys.executable, os.path.join(PROJECT, "agent", "sandbox_hero.py"), "--page", slug, "--run", run], "sandbox", run)


def start_edit(slug, run, body):
    """Step 9, edit and re-check: a person's own words, or a note the writer rewrites from. Gates 1 and 2 run again."""
    run_dir(slug, run)
    src = body.get("variant") or ""
    if not re.match(r"^[A-Z](-edit\d+)?$", src):
        raise ValueError("pick a variant to edit")
    note = (body.get("note") or "").strip()
    h1, sub, cta = [(body.get(k) or "").strip() for k in ("h1", "sub", "cta")]
    if not note and not (h1 or sub or cta):
        raise ValueError("change the H1, sub-line or button, or write a note for the writer")
    if any(len(x) > 400 for x in (note, h1, sub, cta)):
        raise ValueError("too long (400 characters at most per field)")
    cmd = [sys.executable, os.path.join(PROJECT, "agent", "edit_variant.py"), "--page", slug, "--run", run, "--from", src]
    cmd += ["--note", note] if note else ["--h1", h1, "--sub", sub, "--cta", cta]
    return start_job(slug, cmd, "edit", run)


def start_run(slug, key, goal):
    page_dir(slug)
    if not setup.persona(key or ""):
        raise ValueError("pick a buyer persona")
    g = next((x for x in dst.goals_for(slug) if x["id"] == goal), None)
    if not g or not g["available"]:
        raise ValueError("pick a goal that has a real destination on this page")
    st = setup.status(slug, key)
    if not st["ready"]:
        raise ValueError("approve the page setup first (positioning and claims): %s" % st["parts"])
    return start_job(slug, [sys.executable, os.path.join(PROJECT, "agent", "probe3.py"), "--page", slug, "--persona", key, "--goal", goal], "run", None)


def start_job(slug, cmd, kind, run):
    with LOCK:
        if STATE["proc"] is not None and STATE["proc"].poll() is None:
            raise RuntimeError("a run or sandbox is already going; one at a time")
        os.makedirs(LOGS, exist_ok=True)
        log = os.path.join(LOGS, "%s-%s-%s.txt" % (kind, slug, datetime.datetime.now().strftime("%Y%m%d-%H%M%S")))
        before = [os.path.basename(x) for x in glob.glob(os.path.join(PAGES, slug, "runs", "probe3-*"))]
        fh = open(log, "w", encoding="utf-8")
        env = dict(os.environ, PYTHONUNBUFFERED="1")
        STATE.update(proc=subprocess.Popen(cmd, cwd=PROJECT, stdout=fh, stderr=subprocess.STDOUT, env=env),
                     page=slug, log=log, started=datetime.datetime.now().isoformat(timespec="seconds"), run_before=before,
                     kind=kind, job_run=run)
    return status()


class Handler(BaseHTTPRequestHandler):
    server_version = "AgentConsole/1"

    def log_message(self, fmt, *args):
        pass

    def send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False, default=list).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def host_ok(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def do_GET(self):
        if not self.host_ok():
            return self.send(403, {"error": "local only"})
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"):
                return self.send(200, open(os.path.join(APP, "index.html"), "rb").read(), "text/html; charset=utf-8")
            if u.path == "/api/pages":
                return self.send(200, {"pages": pages(), "models": arch.MODELS, "mode": "live"})
            if u.path == "/api/runs":
                return self.send(200, {"runs": runs(q.get("page")), "capture": capture_info(q.get("page"))})
            if u.path == "/api/run":
                return self.send(200, steps_for(q.get("page"), q.get("run")))
            if u.path == "/api/options":
                return self.send(200, options(q.get("page")))
            if u.path == "/api/setup":
                return self.send(200, setup_info(q.get("page"), q.get("persona")))
            if u.path == "/api/questions":
                return self.send(200, questions(q.get("page"), q.get("persona")))
            if u.path == "/api/status":
                return self.send(200, status())
            if u.path == "/api/runflow":
                run_dir(q.get("page"), q.get("run"))
                return self.send(200, run_flow.mermaid(run_flow.gather(q.get("page"), q.get("run"), PROJECT)).encode("utf-8"), "text/plain; charset=utf-8")
            if u.path == "/api/runview":
                rd = run_dir(q.get("page"), q.get("run"))
                out = {"mermaid": run_flow.mermaid(run_flow.gather(q.get("page"), q.get("run"), PROJECT)),
                       "questions": [], "story": None, "questions_version": 1}
                try:   # Builder modules are imported lazily so the console starts without them
                    import run_questions
                    out["questions"] = run_questions.questions(q.get("page"), q.get("run"), PROJECT)
                except Exception:
                    pass
                try:
                    import run_story
                    out["story"] = run_story.load(q.get("page"), q.get("run"), PROJECT)
                except Exception:
                    pass
                try:
                    out["questions_version"] = json.load(open(os.path.join(rd, "probe3.json"), encoding="utf-8")).get("questions_version", 1)
                except Exception:
                    pass
                return self.send(200, out)
            if u.path == "/api/doc":
                f = DOCS.get(q.get("name", ""))
                if not f or not os.path.isfile(os.path.join(PROJECT, f)):
                    return self.send(404, {"error": "no such document"})
                return self.send(200, open(os.path.join(PROJECT, f), "rb").read(), TYPES[os.path.splitext(f)[1]])
            if u.path == "/api/file":
                name = q.get("name", "")
                if not FILE_NAME.match(name):
                    return self.send(400, {"error": "bad file name"})
                if q.get("capture"):
                    folder = q.get("capture")
                    if not re.match(r"^\d{4}-\d{2}-\d{2}-live$", folder):
                        return self.send(400, {"error": "bad capture"})
                    path = os.path.join(page_dir(q.get("page")), "capture", folder, name)
                elif q.get("sub") == "sandbox":
                    path = os.path.join(run_dir(q.get("page"), q.get("run")), "sandbox", name)
                else:
                    path = os.path.join(run_dir(q.get("page"), q.get("run")), name)
                if not os.path.isfile(path):
                    return self.send(404, {"error": "no such file"})
                return self.send(200, open(path, "rb").read(), TYPES[os.path.splitext(name)[1]])
            return self.send(404, {"error": "not found"})
        except ValueError as e:
            return self.send(400, {"error": str(e)})

    def do_POST(self):
        # Spending money needs a same-origin request: local host, our header, and no foreign Origin.
        origin = self.headers.get("Origin")
        if not self.host_ok() or self.headers.get("X-Agent-Console") != "1" or \
                (origin and urlparse(origin).hostname not in ("127.0.0.1", "localhost")):
            return self.send(403, {"error": "local console only"})
        u = urlparse(self.path)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            if u.path == "/api/start":
                return self.send(200, start_run(body.get("page"), body.get("persona"), body.get("goal")))
            if u.path == "/api/setup/draft":
                return self.send(200, start_setup(body.get("page"), body.get("persona")))
            if u.path == "/api/setup/approve":
                return self.send(200, setup_approve(body))
            if u.path == "/api/approve":
                return self.send(200, approve(body))
            if u.path == "/api/sandbox":
                return self.send(200, start_sandbox(body.get("page"), body.get("run")))
            if u.path == "/api/edit":
                return self.send(200, start_edit(body.get("page"), body.get("run"), body))
            return self.send(404, {"error": "not found"})
        except (ValueError, RuntimeError) as e:
            return self.send(409, {"error": str(e)})


def export(dest):
    """Write a read-only static copy: index.html plus data/*.json and the PNGs it shows. No run button."""
    dest = os.path.abspath(dest)
    if os.path.exists(dest) and os.listdir(dest):
        sys.exit("export folder must be empty or new: " + dest)
    os.makedirs(os.path.join(dest, "data"), exist_ok=True)

    def put(key, obj):
        with open(os.path.join(dest, "data", key + ".json"), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, default=list)

    ps = pages()
    put("pages", {"pages": ps, "models": arch.MODELS, "mode": "static"})
    for p in ps:
        s = p["slug"]
        rs = [r for r in runs(s) if r.get("complete")]   # the public copy shows finished runs only
        cap = capture_info(s)
        put("runs__" + s, {"runs": rs, "capture": cap})
        put("questions__" + s, questions(s))
        if cap:
            src = os.path.join(PAGES, s, "capture", cap["folder"], "hero-desktop.png")
            if os.path.isfile(src):
                os.makedirs(os.path.join(dest, "files", s, cap["folder"]), exist_ok=True)
                shutil.copy(src, os.path.join(dest, "files", s, cap["folder"], "hero-desktop.png"))
        for r in rs:
            info = steps_for(s, r["run"])
            for e in (info.get("approval") or {}).get("entries", []) + ([info["current_approval"]] if info.get("current_approval") else []):
                e["name"] = "a person"   # a static copy may become public: never publish the approver's name
            if info.get("sandbox") and info["sandbox"].get("approval"):
                info["sandbox"]["approval"]["name"] = "a person"
            put("run__%s__%s" % (s, r["run"]), info)
            os.makedirs(os.path.join(dest, "files", s, r["run"]), exist_ok=True)
            sf = os.path.join(PAGES, s, "runs", r["run"], "sandbox", "FINDINGS.md")
            if os.path.isfile(sf):
                os.makedirs(os.path.join(dest, "files", s, r["run"], "sandbox"), exist_ok=True)
                shutil.copy(sf, os.path.join(dest, "files", s, r["run"], "sandbox", "FINDINGS.md"))
            for f in info["files"]:
                if f.endswith((".png", ".md")):
                    shutil.copy(os.path.join(PAGES, s, "runs", r["run"], f), os.path.join(dest, "files", s, r["run"], f))
    shutil.copy(os.path.join(APP, "index.html"), os.path.join(dest, "index.html"))
    os.makedirs(os.path.join(dest, "files", "_docs"), exist_ok=True)
    for k, f in DOCS.items():
        if os.path.isfile(os.path.join(PROJECT, f)):
            shutil.copy(os.path.join(PROJECT, f), os.path.join(dest, "files", "_docs", k + os.path.splitext(f)[1]))
    # a static copy may become public: remove every approver name from every exported text file
    names = {"Console user"}
    for f in glob.glob(os.path.join(PAGES, "*", "runs", "*", "approval.json")) + glob.glob(os.path.join(PAGES, "*", "setup", "approvals.json")):
        for e in (read_json(f, {}) or {}).get("entries", []):
            if e.get("name"):
                names.add(e["name"])
    for root, _, fs in os.walk(dest):
        for fn in fs:
            if fn.endswith((".json", ".md", ".html")):
                fp = os.path.join(root, fn)
                t = open(fp, encoding="utf-8").read()
                t2 = t
                for n in names:
                    t2 = t2.replace(n, "a person")
                if t2 != t:
                    open(fp, "w", encoding="utf-8").write(t2)
    print("static copy written:", dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--export")
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    if a.export:
        return export(a.export)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    url = "http://127.0.0.1:%d/" % a.port
    print("Agent console on", url, "(Ctrl+C to stop)")
    if not a.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()

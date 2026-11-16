#!/usr/bin/env python3
"""A short, checked story of one run (4 to 6 plain sentences), saved as RUN-STORY.json in the run folder.

The reasoning model writes it from a facts list built from the run's own files. Code then checks it:
every number, variant name and question id must be in the facts, no approver name, no claims about real visitors.
A story that fails the check is retried twice with the reason. If it still fails, nothing is written.

Run:
  python3 -I agent/run_story.py --page voice-agents --run probe3-YYYYMMDD-HHMMSS   # one run (one model call, about $0.001)
  python3 -I agent/run_story.py --all                                              # every local run; skips runs whose facts did not change
  python3 -I agent/run_story.py --all --dry-run                                    # list what would be written, no model calls
  python3 -I agent/run_story.py --selftest                                         # no model calls
Interface for the console:  load(page, run, root=None) -> dict | None   (never raises)
The run, edit and sandbox scripts call write() at their end. write() never raises.
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "RUN-STORY.json"
MAX_TRIES = 3   # the first try and two retries

NUM_WORDS = {"two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}


def _json(path, default=None):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def run_dir(page, run, root=None):
    return os.path.join(root or PROJECT, "pages", page, "runs", run)


def load(page, run, root=None):
    """The saved story, or None. Never raises."""
    try:
        d = _json(os.path.join(run_dir(page, run, root), NAME))
        return d if isinstance(d, dict) and d.get("text") else None
    except Exception:
        return None


# ---------- facts ----------

def _clean_reason(r):
    return re.sub(r"\s*\(Decisions Log row \d+\)", "", str(r)).strip()


def facts(page, run, root=None):
    """A compact facts dict from the run's own files. Returns None if the run has no audit."""
    import run_questions
    import shortlist
    root = root or PROJECT
    rd = run_dir(page, run, root)
    p = _json(os.path.join(rd, "probe3.json"))
    if not p or not (p.get("audit") or {}).get("p"):
        return None
    a = p["audit"]
    try:
        sl = shortlist.classify(p) if p.get("variants") else []
    except Exception:
        sl = []
    g2 = p.get("gate2") or {}
    variants = []
    for x in sl:
        j = g2.get(x["name"]) or {}
        variants.append({"name": x["name"], "angle": x.get("angle"), "h1": x.get("h1"), "group": x.get("group"), "near_miss": bool(x.get("near_miss")),
                         "gain_jev": (x.get("gains") or {}).get("Jev"), "gain_judge2": (x.get("gains") or {}).get("Judge 2"),
                         "jev_better": (j.get("judge1") or {}).get("better"), "judge2_better": (j.get("judge2") or {}).get("better"),
                         "reasons": [_clean_reason(r) for r in x.get("reasons") or []]})
    edits = [{"name": e.get("name"), "from": e.get("from"), "by": "the writer" if e.get("kind") == "note" else "a person", "group": e.get("group")}
             for e in p.get("edits") or []]
    try:
        ap = shortlist.current_approval(rd)
    except Exception:
        ap = None
    qs = [{"id": q["id"], "text": q["text"], "verdict": q["verdict"], "jev_p": q["jev_p"], "gap": q["gap"], "skipped": q.get("skipped")} for q in run_questions.questions(page, run, root)]
    cap = str(p.get("live_capture") or "")
    cd = (_json(os.path.join(root, cap), {}) or {}).get("captured_at") or (re.search(r"(\d{4}-\d{2}-\d{2})", cap) or [None, ""])[1]
    f = {"page": page, "hero_saved_on": str(cd)[:10] or None, "buyer": (p.get("persona") or {}).get("buyer"), "goal": (p.get("goal") or {}).get("label"),
         "website_run": p.get("screenshots") == "not taken (website run)",
         "questions_version": p.get("questions_version") or 1,
         "audit_gaps": a.get("gaps") or [], "audit_unclear": a.get("unclear") or [], "questions": qs,
         "no_gap_found": not (a.get("gaps") or []),
         "gate1_rounds": len(p.get("gate1_rounds") or []), "variants": variants, "edits": edits,
         "approval": ({"variant": ap.get("variant"), "against_gate2": bool(ap.get("override")), "by": "a person"} if ap else None),
         "counts": {"gaps": len(a.get("gaps") or []), "variants": len([v for v in p.get("variants") or [] if not v.get("edited_from")]),
                    "edits": len(edits)}}
    sb = _json(os.path.join(rd, "sandbox", "sandbox-results.json"))
    if sb:
        f["sandbox"] = {"label": "SYNTHETIC", "variant": sb.get("variant"),
                        "tests": {k: (r or {}).get("result") for k, r in (sb.get("simulated") or {}).items()},
                        "checks_passed": (sb.get("browser") or {}).get("passed"), "check_mode": (sb.get("browser") or {}).get("mode")}
    return f


def facts_text(f):
    return json.dumps(f, ensure_ascii=False, sort_keys=True, indent=1)


def facts_hash(f):
    return hashlib.sha256(facts_text(f).encode("utf-8")).hexdigest()


def approver_names(page, run, root=None):
    """Names a person typed when approving, from the run files. The story must never contain them."""
    rd = run_dir(page, run, root)
    names = set()
    for e in (_json(os.path.join(rd, "approval.json"), {}) or {}).get("entries", []) or []:
        for k in ("name", "by"):
            if e.get(k):
                names.add(str(e[k]))
    p = _json(os.path.join(rd, "probe3.json"), {}) or {}
    for x in (p.get("page_questions") or {}).get("approved_by_on") or []:
        names.add(str(x))
    sb = _json(os.path.join(rd, "sandbox", "sandbox-results.json"), {}) or {}
    if (sb.get("approval") or {}).get("name"):
        names.add(str(sb["approval"]["name"]))
    return {n for n in names if len(n) >= 3 and n.strip().lower() != "a person" and not re.match(r"^[\d\-T:. ]+$", n)}


# ---------- the code check ----------

NUM_RE = re.compile(r"[\$₹]?\d[\d,]*(?:\.\d+)?%?")
QID_RE = re.compile(r"\b([AG][1-9])(?:-[A-Za-z]+(?:-[A-Za-z]+)*(?:-\d+)?)?")
EDIT_RE = re.compile(r"\b[A-Z]-edit\d+\b")
VAR_RE = re.compile(r"\b[Vv]ariants?\s+((?:[A-Z](?:-edit\d+)?)(?:(?:,\s*and|,|\s+and|\s+or|\s+&)\s+[A-Z](?:-edit\d+)?)*)\b")


def _nums(text):
    return {n.strip("$₹%").replace(",", "").rstrip(".") for n in NUM_RE.findall(text)}


def fnums_plain(f):
    """Numbers in the facts that are not part of a question id or a variant name (those digits are labels, not counts)."""
    t = json.dumps({k: v for k, v in f.items() if k not in ("questions", "audit_gaps", "audit_unclear", "variants", "edits", "approval")}, ensure_ascii=False)
    for q in f.get("questions") or []:
        t += " " + str(q.get("jev_p"))
    for v in f.get("variants") or []:
        t += " %s %s" % (v.get("gain_jev"), v.get("gain_judge2"))
    return _nums(t)


def check(story, f, approvers=()):
    """Return a list of problems. Empty means the story is accepted."""
    problems = []
    s = (story or "").strip()
    if not s:
        return ["the story is empty"]
    ftext = facts_text(f)
    fnums = _nums(ftext)
    names = {v["name"] for v in f.get("variants") or []} | {e["name"] for e in f.get("edits") or [] if e.get("name")}
    known_ids = {q["id"] for q in f.get("questions") or []}
    if f.get("variants"):
        known_ids |= {"G1-support", "G2-overreach", "G3-banned"}
    known_ids |= set(f.get("audit_gaps") or [])
    # question ids first, then variant names, then the plain numbers that are left
    rest = s
    for m in QID_RE.finditer(s):
        full, short = m.group(0), m.group(1)
        ok = full in known_ids if full != short else any(i == short or i.startswith(short + "-") for i in known_ids)
        if not ok:
            problems.append("question id %s is not in the facts" % full)
    rest = QID_RE.sub(" ", rest)
    for m in EDIT_RE.finditer(s):
        if m.group(0) not in names:
            problems.append("variant name %s is not in the facts" % m.group(0))
    for m in VAR_RE.finditer(s):
        for n in re.findall(r"[A-Z](?:-edit\d+)?", m.group(1)):
            if n not in names:
                problems.append("variant name %s is not in the facts" % n)
    rest = EDIT_RE.sub(" ", rest)
    rest = re.sub(r"\b(Gate|Test|Judge|Step|step|Round|round|Tests)\s+\d\b", " ", rest)
    rest = re.sub(r"\b[Qq]uestions? v\d\b|\bv\d\b|\bA/A\b", " ", rest)
    for n in sorted(_nums(rest) - fnums):
        problems.append("the number %s is not in the facts" % n)
    vs = f.get("variants") or []
    counts = {str(x) for x in (f.get("counts") or {}).values()} | {str(len(vs)), str(len(f.get("questions") or [])), str(len(f.get("audit_gaps") or [])), str(f.get("gate1_rounds") or 0)}
    for g in {v.get("group") for v in vs}:
        counts.add(str(len([v for v in vs if v.get("group") == g])))
    for w, d in NUM_WORDS.items():
        if re.search(r"\b%s\b" % w, s, re.I) and d not in counts and d not in fnums_plain(f):
            problems.append("the number word '%s' has no matching number in the facts" % w)
    for n in approvers:
        if n and re.search(re.escape(n), s, re.I):
            problems.append("the story names the approver '%s'; say 'a person'" % n)
    if re.search(r"\blive (hero|page|site|copy|version)\b", s, re.I):
        problems.append("the story says 'live hero' or 'live page'; the audit reads a saved copy. Write 'the hero' or \"today's hero (the saved copy from <date>)\"")
    if re.search(r"conversions?\b", s, re.I):
        problems.append("the story talks about conversions; no real visitor data exists")
    if re.search(r"\breal (visitors|users|customers|buyers)\b", s, re.I) and not re.search(r"\b(not|no|never|without)\b[^.]{0,40}\breal (visitors|users|customers|buyers)\b", s, re.I):
        problems.append("the story makes a claim about real visitors")
    if f.get("sandbox") and re.search(r"sandbox|simulat", s, re.I) and "synthetic" not in s.lower():
        problems.append("the story mentions the sandbox but not that its results are synthetic")
    if not f.get("sandbox") and re.search(r"sandbox (result|test|show)", s, re.I):
        problems.append("the story mentions sandbox results but the run has none")
    sentences = [x for x in re.split(r"(?<=[.!?])\s+", s) if x.strip()]
    if not 3 <= len(sentences) <= 8:
        problems.append("the story has %d sentences; write 4 to 6" % len(sentences))
    if len(s) > 1500 or "\n\n\n" in s or s.startswith(("#", "-", "*")):
        problems.append("the story must be plain text, no heading or list, under 1500 characters")
    return problems


# ---------- writing ----------

def _prompt(f):
    return ("=== TASK ===\nWrite the story of this run in 4 to 6 plain sentences, as the skill above says. Reply with the story text only.\n"
            "Use only the facts below. Copy every number exactly. Never name the person who approved. The audit reads the SAVED copy of the hero (see hero_saved_on in the facts), not the live page: never write 'live hero' or 'live page'; write 'the hero' or 'the hero (saved copy from <hero_saved_on>)'. If sandbox is in the facts, say its results are synthetic.\n\nFACTS (JSON):\n" + facts_text(f))


def _ask(f, rd, hosted):
    import llm
    import skills as skl
    sk, used = skl.load("run_story")
    old = llm.LOG_PATH
    llm.LOG_PATH = os.path.join(rd, "run-log.jsonl" if hosted else "story-log.jsonl")
    spent0 = llm.SPENT["usd"]
    cost, model, story, problems, tries = 0.0, "", "", [], 0
    try:
        base = [{"role": "user", "content": sk + "\n\n" + _prompt(f)}]
        msgs = list(base)
        for tries in range(1, MAX_TRIES + 1):
            r = llm.chat(msgs, role="reasoning", max_tokens=3000, temperature=0.3 if tries == 1 else 0.2, purpose="run story" + ("" if tries == 1 else " retry %d" % (tries - 1)))
            cost = llm.SPENT["usd"] - spent0   # counts every call, including one that llm.chat retried inside
            model, story = r.get("model") or model, r["text"].strip().strip('"').strip()
            problems = check(story, f, approver_names_cache["n"])
            if not problems:
                return story, model, cost, used, tries, []
            msgs = base + [{"role": "assistant", "content": story},
                           {"role": "user", "content": "The code check rejected this story: " + "; ".join(problems) + ". Write the story again. Fix only these problems. Reply with the story text only."}]
        return None, model, cost, used, tries, problems
    finally:
        llm.LOG_PATH = old


approver_names_cache = {"n": set()}


def write(page, run, root=None, force=False):
    """Write RUN-STORY.json into the run folder. Never raises. Returns the saved dict, or None."""
    try:
        root = root or PROJECT
        rd = run_dir(page, run, root)
        f = facts(page, run, root)
        if f is None:
            return None
        h = facts_hash(f)
        old = load(page, run, root)
        if old and old.get("facts_hash") == h and not force:
            return old
        approver_names_cache["n"] = approver_names(page, run, root)
        story, model, cost, used, tries, problems = _ask(f, rd, bool(os.environ.get("AGENT_HOSTED")))
        if story is None:
            print("run story not written for %s (the check rejected it %d times: %s)" % (run, tries, "; ".join(problems)[:300]))
            return None
        rec = {"text": story, "model": model, "cost_usd": round(cost, 5), "at": datetime.datetime.now().isoformat(timespec="seconds"),
               "facts_hash": h, "checked": True, "tries": tries, "skills": used}
        json.dump(rec, open(os.path.join(rd, NAME), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        return rec
    except Exception as e:
        print("run story not written (%s)" % str(e)[:200])
        return None


# ---------- command line ----------

def local_runs(root=None):
    root = root or PROJECT
    for rd in sorted(glob.glob(os.path.join(root, "pages", "*", "runs", "probe3-*"))):
        yield rd.split(os.sep)[-3], os.path.basename(rd)


def _selftest():
    ok = True

    def check_(c, msg):
        nonlocal ok
        print(("PASS " if c else "FAIL ") + msg)
        ok &= bool(c)
    f = {"page": "voice-agents", "buyer": "Business owner in Banks & lenders", "goal": "Start building", "audit_gaps": ["A3-proof", "A4-cta"],
         "questions": [{"id": "A3-proof", "verdict": "fail", "jev_p": 0.04}, {"id": "A4-cta", "verdict": "hold", "jev_p": 0.52}, {"id": "A7-checklist-item-1", "verdict": "fail", "jev_p": 0.1}],
         "variants": [{"name": "A", "group": "held", "gain_jev": 0.19, "gain_judge2": 0.26}, {"name": "B", "group": "failed_gate2"}, {"name": "A-edit1", "group": "held"}],
         "edits": [{"name": "A-edit1", "from": "A", "by": "a person"}], "approval": None, "counts": {"gaps": 2, "variants": 2, "edits": 1}}
    good = ("This run looked at the voice agents page for a bank collections lead. Jev found two gaps in the hero, A3-proof and A4-cta. "
            "The writer tried variants A and B. Variant A gained 0.19 with Jev and 0.26 with Judge 2, so a person must review it. "
            "Variant B failed Gate 2. A person edited A into A-edit1, and it was held too.")
    ap = {"Priya Rao", "Console user"}
    check_(check(good, f, ap) == [], "a clean story is accepted")
    bad_num = good.replace("0.19", "0.91")
    check_(any("0.91" in x for x in check(bad_num, f, ap)), "a planted wrong number is rejected")
    check_(any("variant name D" in x for x in check(good + " Variant D won.", f, ap)), "an unknown variant name is rejected")
    check_(any("A-edit9" in x for x in check(good + " A-edit9 passed.", f, ap)), "an unknown edit name is rejected")
    check_(any("A9-extra" in x or "A9" in x for x in check(good + " A9-extra failed.", f, ap)), "an unknown question id is rejected")
    check_(any("A5-positioning" in x for x in check(good + " A5-positioning passed.", f, ap)), "a question id that was not asked is rejected")
    check_(any("Priya Rao" in x for x in check(good + " Priya Rao approved it.", f, ap)), "an approver name is rejected")
    check_(any("number word" in x for x in check(good.replace("two gaps", "seven gaps"), f, ap)), "a wrong number word is rejected")
    check_(any("conversion" in x for x in check(good + " It lifted conversions.", f, ap)), "a conversion claim is rejected")
    check_(any("real visitors" in x for x in check(good + " Real visitors liked it.", f, ap)), "a real-visitor claim is rejected")
    check_(any("synthetic" in x for x in check(good + " The sandbox agreed.", dict(f, sandbox={"label": "SYNTHETIC"}), ap)), "a sandbox mention without 'synthetic' is rejected")
    check_(check(good + " The sandbox is synthetic: its visitors are simulated.", dict(f, sandbox={"label": "SYNTHETIC"}), ap) == [], "a sandbox mention with 'synthetic' is accepted")
    check_(any("live hero" in x for x in check(good + " The live hero has no proof.", f, ap)), "'live hero' is rejected")
    check_(any("live hero" in x for x in check(good + " The live page is weak.", f, ap)), "'live page' is rejected")
    check_(load("none", "none") is None, "load of a missing story gives None")
    print("run_story selftest: %s" % ("all passed" if ok else "FAILED"))
    return ok


if __name__ == "__main__":
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--page")
    ap_.add_argument("--run")
    ap_.add_argument("--all", action="store_true")
    ap_.add_argument("--dry-run", action="store_true")
    ap_.add_argument("--force", action="store_true", help="write again even if the facts did not change")
    ap_.add_argument("--selftest", action="store_true")
    a = ap_.parse_args()
    if a.selftest:
        sys.exit(0 if _selftest() else 1)
    runs = list(local_runs()) if a.all else ([(a.page, a.run)] if a.page and a.run else None)
    if runs is None:
        sys.exit("give --page and --run, or --all, or --selftest")
    todo = 0
    for pg, rn in runs:
        f = facts(pg, rn)
        if f is None:
            print("skip   %s/%s (no audit saved)" % (pg, rn))
            continue
        old = load(pg, rn)
        same = bool(old and old.get("facts_hash") == facts_hash(f)) and not a.force
        if same:
            print("skip   %s/%s (story is current)" % (pg, rn))
            continue
        todo += 1
        if a.dry_run:
            print("write  %s/%s (1 model call, up to %d with retries)" % (pg, rn, MAX_TRIES))
            continue
        rec = write(pg, rn, force=a.force)
        if rec:
            print("wrote  %s/%s | tries %d | cost $%.5f\n%s\n" % (pg, rn, rec["tries"], rec["cost_usd"], rec["text"]))
        else:
            print("FAILED %s/%s" % (pg, rn))
    if a.dry_run:
        print("%d run(s) would be written: %d to %d model calls" % (todo, todo, todo * MAX_TRIES))

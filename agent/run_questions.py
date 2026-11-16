#!/usr/bin/env python3
"""The exact questions Jev was asked in one run. Plain code, no model, never raises.

questions(page, run, root=None) -> list of {"id", "text", "source", "jev_p", "verdict", "gap"}, in the order A1 to A8.
Where the wording comes from, best first:
  recorded                   the run saved it (probe3.json audit.questions). New runs do.
  archive v1 / archive v2    rebuilt from rules/judge-questions-v<N>.json, N = the run's questions_version (none = 1)
  page checklist (rebuilt)   A7 item texts and the A8 objection, from the buyer checklist the run saved (page_questions)
Run:  python3 -I agent/run_questions.py --page voice-agents --run probe3-YYYYMMDD-HHMMSS
Test: python3 -I agent/run_questions.py --selftest
"""
import argparse
import json
import os
import re
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _json(path, default=None):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _key(qid):
    """Sort A1, A2 ... A8 in order, and A7-1, A7-2 ... by their number."""
    m = re.match(r"A(\d+)", qid)
    if not m:
        return (99, 0, qid)
    n = re.search(r"-(\d+)$", qid)
    return (int(m.group(1)), int(n.group(1)) if n else 0, qid)


def _archive(root, version):
    """{base id: template dict} from the archived question file of that version. Falls back to the live file."""
    for name in ("judge-questions-v%d.json" % version, "judge-questions.json"):
        d = _json(os.path.join(root, "rules", name))
        if d and (d.get("audit") or {}).get("questions"):
            ver = d.get("version", 1)
            return {x["id"]: x for x in d["audit"]["questions"]}, ("archive v%s" % ver)
    return {}, "archive v%d" % version


def questions(page, run, root=None):
    try:
        root = root or PROJECT
        probe = _json(os.path.join(root, "pages", page, "runs", run, "probe3.json"))
        if not probe:
            return []
        a = probe.get("audit") or {}
        p = a.get("p") or {}
        if not p:
            return []
        recorded = a.get("questions") or {}
        pq = probe.get("page_questions") or {}
        version = probe.get("questions_version") or 1
        tmpl, tmpl_src = _archive(root, int(version))
        verdict, gaps = a.get("verdict") or {}, set(a.get("gaps") or [])
        out = []
        for qid in sorted(p, key=_key):
            text, source = recorded.get(qid), "recorded"
            if not text:
                base = re.sub(r"-\d+$", "", qid) if qid.startswith("A7") else qid
                t = (tmpl.get(base) or tmpl.get(qid) or {}).get("text")
                items = pq.get("hero_items") or []
                if qid.startswith("A7-checklist-item") or (qid.startswith("A7") and t and "{item}" in t):
                    n = int(qid.split("-")[-1]) if qid.split("-")[-1].isdigit() else 0
                    item = items[n - 1] if 0 < n <= len(items) else None
                    text = t.replace("{item}", item) if (t and item) else None
                    source = "page checklist (rebuilt)"
                elif qid == "A8-objection":
                    obj = (pq.get("main_objection") or "").rstrip(".")
                    text = t.replace("{objection}", obj) if (t and obj) else None
                    source = "page checklist (rebuilt)"
                else:
                    text, source = t, tmpl_src
            if not text:
                continue
            out.append({"id": qid, "text": text, "source": source, "jev_p": p.get(qid), "verdict": verdict.get(qid), "gap": qid in gaps, "skipped": None})
        # questions the run did not ask: in the template (or recorded as skipped) but not in the audit
        asked_base = {re.sub(r"-\d+$", "", k) for k in p}
        want = {re.sub(r" \(.*$", "", x) for x in (pq.get("skipped") or [])} | {k for k in tmpl if k not in asked_base and k not in p}
        for base in want:
            if base in asked_base or base in p or base not in tmpl:
                continue
            t = tmpl[base].get("text") or ""
            if base == "A6-swap":
                why, src = "not asked: no rival heroes are saved for this page", tmpl_src
            elif base == "A7-checklist-item":
                why = "not asked: the buyer checklist was not approved" if not pq.get("approved") else "not asked: the buyer checklist has no hero questions"
                src = "page checklist (rebuilt)"
            elif base == "A8-objection":
                why = "not asked: the buyer checklist was not approved" if not pq.get("approved") else "not asked: the buyer checklist names no main objection"
                obj = (pq.get("main_objection") or "").rstrip(".")
                t = t.replace("{objection}", obj) if obj else t
                src = "page checklist (rebuilt)"
            else:
                why, src = "not asked in this run", tmpl_src
            out.append({"id": base, "text": t, "source": src, "jev_p": None, "verdict": None, "gap": False, "skipped": why})
        out.sort(key=lambda q: _key(q["id"]))
        return out
    except Exception:
        return []


def selftest():
    import shutil
    import tempfile
    ok = True

    def check(c, msg):
        nonlocal ok
        print(("PASS " if c else "FAIL ") + msg)
        ok &= bool(c)
    root = tempfile.mkdtemp(prefix="rq-selftest-")
    try:
        def w(rel, obj):
            path = os.path.join(root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            json.dump(obj, open(path, "w", encoding="utf-8"))
        v1 = {"version": 1, "audit": {"questions": [{"id": "A1-audience", "text": "Old A1?"}, {"id": "A4-cta", "text": "Old A4?"},
                                                     {"id": "A7-checklist-item", "text": "Does it answer {item}?", "fill": "item"},
                                                     {"id": "A8-objection", "text": "Does it answer {objection}?", "fill": "objection"}]}}
        w("rules/judge-questions-v1.json", v1)
        pqs = {"hero_items": ["Is it for lenders"], "main_objection": "The bot fails."}
        w("pages/x/runs/new/probe3.json", {"questions_version": 2, "page_questions": pqs, "audit": {
            "p": {"A1-audience": 0.5, "A7-checklist-item-1": 0.1}, "verdict": {"A1-audience": "pass", "A7-checklist-item-1": "fail"}, "gaps": [],
            "questions": {"A1-audience": "New A1?", "A7-checklist-item-1": "Does it answer Is it for lenders?"}}})
        w("pages/x/runs/old/probe3.json", {"page_questions": pqs, "audit": {
            "p": {"A8-objection": 0.2, "A7-checklist-item-1": 0.1, "A4-cta": 0.3, "A1-audience": 0.9},
            "verdict": {"A4-cta": "fail", "A1-audience": "pass"}, "gaps": ["A4-cta"]}})
        new = questions("x", "new", root)
        check([q["source"] for q in new] == ["recorded", "recorded"] and new[0]["text"] == "New A1?", "new run: wording is recorded")
        old = questions("x", "old", root)
        check([q["id"] for q in old] == ["A1-audience", "A4-cta", "A7-checklist-item-1", "A8-objection"], "old run: questions in order A1 to A8")
        check(old[0]["source"] == "archive v1" and old[0]["text"] == "Old A1?", "old run: A1 comes from the v1 archive")
        check(old[2]["source"] == "page checklist (rebuilt)" and old[2]["text"] == "Does it answer Is it for lenders?", "old run: A7 item text rebuilt")
        check(old[3]["text"] == "Does it answer The bot fails?", "old run: A8 objection filled in")
        check(old[1]["gap"] is True and old[1]["verdict"] == "fail" and old[1]["jev_p"] == 0.3, "gap, verdict and probability carried over")
        check(all(q["skipped"] is None for q in old), "an old run that asked everything has no skipped items")
        w("pages/x/runs/skip/probe3.json", {"page_questions": {"approved": False, "skipped": ["A6-swap (no rival heroes saved for this page)", "A7-checklist-item", "A8-objection"]},
                                            "audit": {"p": {"A1-audience": 0.5, "A4-cta": 0.2}, "verdict": {}, "gaps": []}})
        sq = questions("x", "skip", root)
        check([q["id"] for q in sq] == ["A1-audience", "A4-cta", "A7-checklist-item", "A8-objection"], "skipped questions sit in their place in the order")
        check(sq[2]["skipped"] == "not asked: the buyer checklist was not approved" and sq[0]["skipped"] is None and sq[2]["jev_p"] is None, "A7 skipped: checklist not approved; asked items have skipped None")
        w("pages/x/runs/skip2/probe3.json", {"page_questions": {"approved": True}, "audit": {"p": {"A1-audience": 0.5, "A4-cta": 0.3, "A5-positioning": 0.4}, "verdict": {}, "gaps": []}})
        w("rules/judge-questions-v1.json", dict(v1, audit={"questions": v1["audit"]["questions"] + [{"id": "A5-positioning", "text": "A5?"}, {"id": "A6-swap", "text": "A6?"}]}))
        s2 = questions("x", "skip2", root)
        check([q["id"] for q in s2] == ["A1-audience", "A4-cta", "A5-positioning", "A6-swap", "A7-checklist-item", "A8-objection"] and s2[3]["skipped"].endswith("saved for this page"), "skipped inferred from the template when the run records none; order A5, A6, A7, A8")
        check(questions("x", "missing", root) == [] and questions("nope", "nope", root) == [], "missing run gives an empty list")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("run_questions selftest: %s" % ("all passed" if ok else "FAILED"))
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--page")
    ap.add_argument("--run")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if not (a.page and a.run):
        sys.exit("give --page and --run, or --selftest")
    for q in questions(a.page, a.run):
        print("%-22s p=%s  %-14s %s  [%s]\n    %s" % (q["id"], "n/a" if q["jev_p"] is None else "%.2f" % q["jev_p"], q["verdict"], "GAP" if q["gap"] else "   ", q["source"], q["text"]) + ("\n    (%s)" % q["skipped"] if q.get("skipped") else ""))

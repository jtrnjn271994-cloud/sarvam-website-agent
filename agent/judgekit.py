#!/usr/bin/env python3
"""Shared judge inputs and verdicts. Calibration and the live run use the SAME state builders and
question wording, so pass lines set by calibration carry over. Standard library only."""
import json
import os
import re

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def norm(t):
    """Normalise money and unit forms before a judge sees them (INR vs the rupee sign, /1M vs per 1M)."""
    t = (t or "").replace("₹", "INR ").replace("Rs.", "INR ").replace("Rs ", "INR ")
    t = re.sub(r"\s*/\s*1M\b", " per 1M", t)
    t = t.replace("’", "'")
    return re.sub(r"\s+", " ", t).strip()


def questions():
    q = json.load(open(os.path.join(PROJECT, "rules", "judge-questions.json"), encoding="utf-8"))
    audit = {x["id"]: x for x in q["audit"]["questions"]}
    gate2 = {x["id"]: x for x in q["gate2"]["questions"]}
    return q, audit, gate2


def fragment_state(fragment, claim_id, claim_text, evidence_quote):
    return ["FRAGMENT: " + norm(fragment), "CLAIM %s: %s" % (claim_id, norm(claim_text)), "EVIDENCE QUOTE: " + norm(evidence_quote)]


def hero_state(h1, sub, cta, destination):
    return ["HERO HEADLINE (H1): " + norm(h1), "HERO SUB-LINE: " + norm(sub),
            "HERO MAIN BUTTON: %s (the button goes to: %s)" % (norm(cta), destination)]


def context_state(buyer, promise):
    return ["BUYER: " + buyer, "POSITIONING PROMISE: " + norm(promise)]


POLARITY_BAD = ("G2", "G3", "A6")


def is_bad(qid):
    return qid.startswith(POLARITY_BAD)


def thresholds():
    path = os.path.join(PROJECT, "rules", "judge-thresholds.json")
    return json.load(open(path)) if os.path.isfile(path) else None


def verdict(th, role, qid, p, gray=None):
    """Return pass, fail or hold (prefixed 'advisory-' when the judge could not separate this question in calibration).
    Uses the calibrated band: below it fails, above it passes, inside it holds for a person."""
    key = "A7-checklist-item" if qid.startswith("A7") else qid
    if p is None:
        return "hold"
    t = ((th or {}).get("judges", {}).get(role, {}) or {}).get(key)
    if not t:
        return "advisory-hold"
    if t["polarity"] == "good":
        lo, hi = t.get("fail_at"), t.get("pass_at")
        res = "pass" if hi is not None and p >= hi else "fail" if lo is not None and p <= lo else "hold"
        if t["advisory"]:
            res = "hold" if not (hi is not None and p >= max(hi, lo or 0)) and not (lo is not None and p <= min(lo, hi or 1)) else res
    else:
        flag, clean = t.get("flag_at"), t.get("clean_at")
        res = "fail" if flag is not None and p >= flag and (clean is None or p > clean) else "pass" if clean is not None and p <= clean and (flag is None or p < flag) else "hold"
    return ("advisory-" + res) if t["advisory"] else res

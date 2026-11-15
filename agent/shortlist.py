#!/usr/bin/env python3
"""Group a run's variants for the approval page (Decisions Log rows 33 and 34). No model calls.

Groups:
  passed        both judges say better than the live hero; no blocking verdict
  held          Gate 1 passed, and the judges disagree on "better", or the only blocker is a
                Jev banned-phrase fail (Gate 1 found no do-not-claim item, so it holds, row 34)
  failed_gate2  Gate 1 passed, and neither judge says better, or a non-advisory overreach fail
  failed_gate1  a rules failure in the last Gate 1 round: count and rule names only, never selectable
Every reason is built here from the run record. No model writes it.

Run:  python3 -I agent/shortlist.py <run folder>      prints the groups
      python3 -I agent/shortlist.py --selftest         checks the two 15 Nov runs
"""
import hashlib
import json
import os
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SELECTABLE = ("passed", "held", "failed_gate2")
JUDGE_NAME = {"judge1": "Jev", "judge2": "Judge 2"}


def variant_hash(v):
    """Hash of what the visitor sees and what it claims: H1, sub-line, button, destination, claim map."""
    keep = {k: v.get(k) for k in ("h1", "subline", "cta", "cta_destination", "map")}
    return hashlib.sha256(json.dumps(keep, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def latest_approval(run_folder):
    """The latest entry of the run's append-only approval.json, or None."""
    try:
        entries = json.load(open(os.path.join(run_folder, "approval.json"), encoding="utf-8"))["entries"]
    except (OSError, ValueError, KeyError):
        return None
    return entries[-1] if entries else None


def current_approval_of(entries):
    """The approve entry that counts: the latest approve, unless a later reject or revise names that same variant.
    A later approve of another variant replaces it (one variant goes to the sandbox)."""
    cur = None
    for e in entries or []:
        if e.get("decision") == "approve":
            cur = e
        elif cur and e.get("variant") == cur.get("variant"):
            cur = None
    return cur


def current_approval(run_folder):
    try:
        entries = json.load(open(os.path.join(run_folder, "approval.json"), encoding="utf-8"))["entries"]
    except (OSError, ValueError, KeyError):
        return None
    return current_approval_of(entries)


def _avg_targeted(j):
    t = j.get("targeted") or []
    return sum(j["delta"][k] for k in t) / len(t) if t else 0.0


def classify(probe):
    """Return a list of dicts, one per variant, in display order (groups, then best first)."""
    variants = probe.get("variants") or []
    g1_last = (probe.get("gate1_rounds") or [{}])[-1]
    g2 = probe.get("gate2") or {}
    out = []
    for v in variants:
        name = v["name"]
        item = {"name": name, "angle": v.get("angle"), "h1": v.get("h1"), "subline": v.get("subline"),
                "cta": v.get("cta"), "cta_destination": v.get("cta_destination"), "reasons": [], "score": None}
        issues = g1_last.get(name) or []
        if issues:
            item.update(group="failed_gate1", reasons=["Gate 1 (rules) failed: " + "; ".join(map(str, issues))])
            out.append(item)
            continue
        r = g2.get(name)
        if not r or "judge1" not in r or "judge2" not in r:
            item.update(group="failed_gate2", reasons=["Gate 2 did not run for this variant."])
            out.append(item)
            continue
        better = {j: bool(r[j].get("better")) for j in ("judge1", "judge2")}
        over_fail = {j: [f["fragment"] for f in r[j].get("fragments", []) if f["verdict"].get("G2-overreach") == "fail"] for j in better}
        banned_fail = {j: r[j].get("G3_verdict") == "fail" for j in better}
        gains = {j: _avg_targeted(r[j]) for j in better}
        item["score"] = round(sum(gains.values()) / 2, 3)
        item["gains"] = {JUDGE_NAME[j]: round(g, 2) for j, g in gains.items()}
        rule = json.load(open(os.path.join(PROJECT, "rules", "judge-questions.json"), encoding="utf-8"))["gate2"]["better_than_baseline"]

        def why(j):
            if better[j]:
                return "%s says better (average gain on the targeted gaps %+.2f)" % (JUDGE_NAME[j], gains[j])
            parts = []
            if gains[j] < rule["min_gain"]:
                parts.append("average gain on the targeted gaps %+.2f, below the %.2f needed" % (gains[j], rule["min_gain"]))
            drops = ["%s %+.2f" % (k, r[j]["delta"][k]) for k in r[j].get("held_out", []) if r[j]["delta"][k] < -rule["max_drop"]]
            if drops:
                parts.append("targeted gain %+.2f, but other questions dropped more than %.2f: %s" % (gains[j], rule["max_drop"], ", ".join(drops)))
            return "%s says not better (%s)" % (JUDGE_NAME[j], "; ".join(parts) or "see the scores")
        reasons = ["; ".join(why(j) for j in better) + "."]
        if any(over_fail.values()):
            frags = sorted({f for fs in over_fail.values() for f in fs})
            group = "failed_gate2"
            reasons.append("A judge's overreach answer failed on a calibrated (non-advisory) line for: " + "; ".join('"%s"' % f for f in frags) + ".")
        elif not any(better.values()):
            group = "failed_gate2"
        elif all(better.values()) and not any(banned_fail.values()):
            group = "passed"
        else:
            group = "held"
            if better["judge1"] != better["judge2"]:
                reasons.append("The judges disagree on whether it beats the live hero.")
            for j, bf in banned_fail.items():
                if bf:
                    reasons.append("%s flagged a banned phrase, but Gate 1 found no item from the do-not-claim list. "
                                   "Held for a person instead of blocked (Decisions Log row 34)." % JUDGE_NAME[j])
        near = group == "failed_gate2" and not any(over_fail.values()) and all(gains[j] >= rule["min_gain"] for j in better)
        if near:   # gains on the targeted gaps, but a question the live hero answered fell: worth a person's look (owner, 15 Nov 2026)
            lost = sorted({k for j in better for k in r[j].get("held_out", []) if r[j]["delta"][k] < -rule["max_drop"]})
            reasons.insert(0, "NEAR MISS. Both judges see the gain the gaps need (average +%.2f and +%.2f), but %s fell. Often this is wording, not meaning: read it before you decide." % (
                gains["judge1"], gains["judge2"], ", ".join(lost) or "another question"))
        item.update(group=group, reasons=reasons, near_miss=bool(near))
        out.append(item)
    order = {"passed": 0, "held": 1, "failed_gate2": 2, "failed_gate1": 3}
    out.sort(key=lambda x: (order[x["group"]], -(x["score"] if x["score"] is not None else -9)))
    return out


def selftest():
    want = {"probe3-20261115-183113": {"A": "passed", "B": "held", "C": "failed_gate2"},
            "probe3-20261115-184616": {"A": "held", "B": "held", "C": "failed_gate2"}}
    bad = 0
    for run, exp in want.items():
        p = os.path.join(PROJECT, "pages", "token-factory", "runs", run, "probe3.json")
        if not os.path.isfile(p):
            print("skip (missing):", run)
            continue
        got = {x["name"]: x["group"] for x in classify(json.load(open(p, encoding="utf-8")))}
        ok = got == exp
        bad += not ok
        print("%s %s %s" % ("PASS" if ok else "FAIL", run, got))
    # approval rules, in memory only
    A, rC, rA, B = ({"decision": "approve", "variant": "A"}, {"decision": "reject", "variant": "C"},
                    {"decision": "revise", "variant": "A"}, {"decision": "approve", "variant": "B"})
    for entries, want_v in (([A, rC], "A"), ([A, rA], None), ([A, B], "B"), ([A, B, rC], "B"), ([rC], None)):
        got_v = (current_approval_of(entries) or {}).get("variant")
        print("%s approval %s -> %s" % ("PASS" if got_v == want_v else "FAIL", [e["decision"] + " " + e["variant"] for e in entries], got_v))
        bad += got_v != want_v
    # a synthetic Gate 1 failure must never be selectable
    fake = {"variants": [{"name": "Z", "h1": "x"}], "gate1_rounds": [{"Z": ["new number: 42"]}], "gate2": {}}
    g = classify(fake)[0]["group"]
    print("%s gate1 failure -> %s" % ("PASS" if g == "failed_gate1" else "FAIL", g))
    bad += g != "failed_gate1"
    return bad == 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if selftest() else 1)
    run = sys.argv[1]
    for x in classify(json.load(open(os.path.join(run, "probe3.json"), encoding="utf-8"))):
        print(x["group"].ljust(13), x["name"], x["score"], "|", " ".join(x["reasons"]))

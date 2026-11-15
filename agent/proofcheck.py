"""The rule-based proof check (flow v2.1, step 6c). Code only. No model.

problems(lines, root, page) returns plain sentences. An empty list means every line holds up.
A line is a dict: text, claim_ids, label, and kind (product, number, comparison, signal, customer).
The rules, in order:
  1. Every claim id exists in the page claims. A line with no claim id fails.
  2. Every evidence note of a cited claim exists, and its quote is found word for word in its saved source.
  3. PROPOSED, UNCHECKED, AUDIT and SYNTHETIC never carry proof.
  4. A line holds a digit: code sets its kind to number.
  5. The label is strong enough for the kind (the ladder in docs/flow-v2-start-order.md). The weakest label of
     the line, its claims and their evidence is the one that counts. A line may not claim a stronger label than its claims.
  6. Every number in the line is in the cited claim text.
  7. An evidence note (cited by the line's evidence_ids, or by one of its claims) that cites a library id whose register row was added by the person is UNCHECKED.
     It never carries proof.
root is a project folder or the frozen mirror of one. Standard library only.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import libraryguard  # noqa: E402
import quote_match  # noqa: E402
import runlib  # noqa: E402

NEVER = ("PROPOSED", "UNCHECKED", "AUDIT", "SYNTHETIC")
KINDS = ("product", "number", "comparison", "signal", "customer")
# The lowest label each kind may carry. A rank of 3 is VENDOR (see common.STRENGTH). A rank of 1 is CALC.
LADDER = {"product": 3, "number": 1, "comparison": 0, "signal": 0, "customer": 0}
LADDER_TEXT = {"product": "VENDOR or stronger", "number": "CHECKED or CALC", "comparison": "CHECKED", "signal": "CHECKED", "customer": "CHECKED"}
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers_of(text):
    return [n.replace(",", "").rstrip(".") for n in NUMBER.findall(text or "")]


def rank(label):
    return common.STRENGTH.get(label, 99)


def added_by_person(root):
    """The library ids whose register row says 'added by the person'. Their label is UNCHECKED."""
    return set(r["id"] for r in libraryguard.load_register(root) if r.get("source", "").startswith(libraryguard.ADDED_PREFIX))


def problems(lines, root, page):
    added = added_by_person(root)
    claims = dict((c["id"], c) for c in runlib.load_claims(root, page))
    evidence = runlib.load_evidence(root, page)
    register = quote_match.load_register(root)
    out = []
    for n, line in enumerate(lines or []):
        where = "line %d" % (n + 1)
        text = str((line or {}).get("text") or "")
        ids = (line or {}).get("claim_ids") or []
        label = str((line or {}).get("label") or "")
        k = (line or {}).get("kind")
        kind = (line or {}).get("proof_kind") or (k if k != "claim" else None) or "product"
        if kind not in KINDS:
            out.append("%s: the kind '%s' is not one of %s." % (where, kind, ", ".join(KINDS)))
            continue
        if not ids:
            out.append("%s: it cites no claim id, so it carries no proof." % where)
            continue
        if label in NEVER:
            out.append("%s: the label %s never carries proof." % (where, label))
        for eid in (line or {}).get("evidence_ids") or []:
            lids = (evidence.get(eid) or {}).get("lib_ids")
            for lid in [x for x in (lids if isinstance(lids, list) else [lids]) if x in added]:
                out.append("%s: the line cites the evidence note %s, which cites %s, a file added by the person. Its label is UNCHECKED, which never carries proof." % (where, eid, lid))
        weakest = rank(label)
        claim_text = []
        for cid in ids:
            c = claims.get(cid)
            if c is None:
                out.append("%s: the claim id %s does not exist in the page claims." % (where, cid))
                continue
            claim_text.append(str(c.get("text") or ""))
            if c.get("status") == "rejected":
                out.append("%s: the claim %s is rejected." % (where, cid))
            if c.get("label") in NEVER:
                out.append("%s: the claim %s is %s, which never carries proof." % (where, cid, c.get("label")))
            weakest = max(weakest, rank(c.get("label")))
            if label and rank(label) < rank(c.get("label")):
                out.append("%s: the line label %s is stronger than the claim %s (%s)." % (where, label, cid, c.get("label")))
            for eid in c.get("evidence_ids") or []:
                fm = evidence.get(eid)
                if fm is None:
                    out.append("%s: the claim %s cites %s, which is not an evidence note." % (where, cid, eid))
                    continue
                weakest = max(weakest, rank(fm.get("label")))
                lids = fm.get("lib_ids") if isinstance(fm.get("lib_ids"), list) else [fm.get("lib_ids")]
                for lid in [x for x in lids if x in added]:
                    out.append("%s: the evidence note %s cites %s, a file added by the person. Its label is UNCHECKED, which never carries proof." % (where, eid, lid))
                ok, msg = quote_match.check_note(root, fm, register)
                if not ok:
                    out.append("%s: the quote of %s (claim %s) is not found in its saved source: %s." % (where, eid, cid, msg))
        if numbers_of(text):
            kind = "number"  # code decides: a line with a digit is a number line
        if rank(label) <= 6 and weakest > LADDER[kind] and label not in NEVER:
            out.append("%s: a %s line needs %s. Its weakest label is %s." % (where, kind, LADDER_TEXT[kind], next((k for k, v in common.STRENGTH.items() if v == weakest), "unknown")))
        have = set(numbers_of(" ".join(claim_text)))
        for num in numbers_of(text):
            if num not in have:
                out.append("%s: the number %s is not in the cited claim text. A line may not add a number." % (where, num))
    return out


def lines_of(output):
    """The proof lines of a step output. A position has proof lines. A variants object has the claim lines of the changed sections."""
    if not isinstance(output, dict):
        return []
    if isinstance(output.get("proof"), list):
        return [l for l in output["proof"] if isinstance(l, dict)]
    found = []
    for v in output.get("variants") or []:
        changed = set(v.get("changed_sections") or [])
        for sec in v.get("sections") or []:
            if sec.get("section") in changed:
                found += [l for l in sec.get("lines") or [] if isinstance(l, dict) and l.get("kind") == "claim"]
    return found

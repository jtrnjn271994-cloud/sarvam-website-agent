#!/usr/bin/env python3
"""Check the claim rule: no evidence id, no claim.

Run from anywhere:  python3 -I agent/check_claims.py
Check copy:         python3 -I agent/check_claims.py --text draft.md [--page <slug>]
Self test:          python3 -I agent/check_claims.py --selftest

Rules for every claim note that is not rejected:
  - it has text and at least one evidence id
  - every evidence id is an evidence note on the same page
  - no evidence note is AUDIT, withdrawn or superseded
  - the claim label is not stronger than its weakest evidence note
    (strongest to weakest: CHECKED, CALC, SEMRUSH, VENDOR, PROPOSED, UNCHECKED, AUDIT)
  - the text holds none of the phrases in pages/<page>/decisions/do-not-claim.md
    (one phrase on each line that starts with "- BAN:")
The --text mode lists each sentence with a number that has no [CL-NNN] or [EV-NNN] tag.
Standard library only.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

TAG = re.compile(r"\[(?:CL|EV)-\d{3}\]")
SPLIT = re.compile(r"(?<=[.!?])\s+(?!\[(?:CL|EV)-\d{3}\])|\n+")


def load_bans(project, page):
    path = os.path.join(project, "pages", page, "decisions", "do-not-claim.md")
    if not os.path.isfile(path):
        return []
    bans = []
    for line in common.read_text(path).splitlines():
        s = line.strip()
        if s.startswith("- BAN:") and s[6:].strip():
            bans.append(s[6:].strip())
    return bans


def check_page(project, page):
    errors = []
    ev = {}
    for path, fm, err in common.load_notes(project, page, "evidence"):
        if not err and fm.get("id"):
            ev[fm["id"]] = fm
    bans = load_bans(project, page)
    n = 0
    for path, fm, err in common.load_notes(project, page, "claims"):
        name = "pages/%s/claims/%s" % (page, os.path.basename(path))
        if err or not fm.get("id"):
            errors.append("%s: cannot read front matter" % name)
            continue
        n += 1
        if fm.get("status") == "rejected":
            continue
        cid = fm["id"]
        text = str(fm.get("text") or "").strip()
        ids = fm.get("evidence_ids")
        if not text:
            errors.append("%s: %s has no text" % (name, cid))
        if not isinstance(ids, list) or not ids:
            errors.append("%s: %s has no evidence id (no evidence id, no claim)" % (name, cid))
            ids = []
        worst = None
        for i in ids:
            note = ev.get(i)
            if note is None:
                errors.append("%s: %s cites %s, which is not an evidence note" % (name, cid, i))
                continue
            if note.get("label") == "AUDIT":
                errors.append("%s: %s cites %s, which is AUDIT and can never support a claim" % (name, cid, i))
            if note.get("status") in ("withdrawn", "superseded"):
                errors.append("%s: %s cites %s, which is %s" % (name, cid, i, note.get("status")))
            lab = note.get("label")
            if lab in common.STRENGTH and (worst is None or common.STRENGTH[lab] > common.STRENGTH[worst]):
                worst = lab
        label = fm.get("label")
        if label not in common.STRENGTH:
            errors.append("%s: %s label '%s' is not one of the seven" % (name, cid, label))
        elif worst is not None and common.STRENGTH[label] < common.STRENGTH[worst]:
            errors.append("%s: %s label %s is stronger than its weakest evidence (%s)" % (name, cid, label, worst))
        for b in bans:
            if b.lower() in text.lower():
                errors.append("%s: %s uses the banned phrase '%s'" % (name, cid, b))
    return errors, n


def check_text(text, known_ids=None):
    """Return the sentences that hold a number and have no tag. Also bad tags if known_ids is given."""
    out = []
    for s in SPLIT.split(text):
        s = s.strip()
        if not s:
            continue
        if re.search(r"\d", s) and not TAG.search(s):
            out.append(s)
        elif known_ids is not None:
            for t in TAG.findall(s):
                if t[1:-1] not in known_ids:
                    out.append("%s (tag %s does not exist)" % (s, t))
    return out


def run(project):
    errors, total = [], 0
    for page in common.list_pages(project):
        e, n = check_page(project, page)
        errors.extend(e)
        total += n
    for e in errors:
        print("ERROR   " + e)
    print("---")
    print("claims checked: %d%s" % (total, " (no claim notes exist yet)" if total == 0 else ""))
    print("errors: %d" % len(errors))
    return 1 if errors else 0


def run_text(project, path, page):
    if not os.path.isfile(path):
        print("ERROR   file not found: %s" % path)
        return 1
    known = None
    if page:
        known = set()
        for folder in ("evidence", "claims"):
            for _, fm, err in common.load_notes(project, page, folder):
                if fm.get("id"):
                    known.add(fm["id"])
    bad = check_text(common.read_text(path), known)
    for s in bad:
        print("UNTAGGED  " + s)
    print("---")
    print("sentences with a number and no tag: %d" % len(bad))
    return 1 if bad else 0


def selftest():
    st = common.SelfTest("check_claims")
    root = common.make_temp_project()
    pg = os.path.join(root, "pages", "p")
    try:
        def put(kind, name, text):
            common.write_file(os.path.join(pg, kind, name), text)
        put("evidence", "ev-001-a.md", common.evidence_text(id="EV-001", label="CHECKED"))
        put("evidence", "ev-002-b.md", common.evidence_text(id="EV-002", label="VENDOR"))
        put("evidence", "ev-003-c.md", common.evidence_text(id="EV-003", label="AUDIT"))
        put("evidence", "ev-004-d.md", common.evidence_text(id="EV-004", status="withdrawn"))
        put("evidence", "ev-005-e.md", common.evidence_text(id="EV-005", status="superseded"))
        put("decisions", "do-not-claim.md", "# Ban list\n- BAN: lowest price\n- not a ban line\n")

        def errs_for(**over):
            put("claims", "cl-001-a.md", common.claim_text(**over))
            return check_page(root, "p")[0]
        st.expect(errs_for(evidence_ids="[EV-001]", label="CHECKED") == [], "a good claim passes")
        st.expect(any("no evidence id" in e for e in errs_for(evidence_ids="[]")), "a claim with no evidence id is caught")
        st.expect(any("not an evidence note" in e for e in errs_for(evidence_ids="[EV-099]")), "a claim that cites a missing evidence note is caught")
        st.expect(any("AUDIT" in e for e in errs_for(evidence_ids="[EV-003]", label="AUDIT")), "a claim backed by AUDIT evidence is caught")
        st.expect(any("withdrawn" in e for e in errs_for(evidence_ids="[EV-004]")), "a claim backed by withdrawn evidence is caught")
        st.expect(any("superseded" in e for e in errs_for(evidence_ids="[EV-005]")), "a claim backed by superseded evidence is caught")
        st.expect(any("stronger than" in e for e in errs_for(evidence_ids="[EV-001, EV-002]", label="CHECKED")),
                  "a CHECKED claim on VENDOR evidence is caught")
        st.expect(errs_for(evidence_ids="[EV-001, EV-002]", label="VENDOR") == [], "a VENDOR claim on mixed evidence passes")
        st.expect(any("banned phrase" in e for e in errs_for(text="\"We offer the Lowest Price.\"")), "a banned phrase is caught")
        st.expect(any("no text" in e for e in errs_for(text="\"\"")), "a claim with empty text is caught")
        st.expect(errs_for(status="rejected", evidence_ids="[]") == [], "a rejected claim is skipped")
        put("claims", "cl-001-a.md", common.claim_text(evidence_ids="[]"))
        st.expect(run(root) == 1, "run() exits 1 on a planted bad claim")
        draft = "Costs fall 40% in a year. Nothing here. It runs 3 models. [CL-001] Latency is 120 ms [EV-001]."
        bad = check_text(draft)
        st.expect(bad == ["Costs fall 40% in a year."], "--text finds the untagged number and accepts a tag after the full stop")
        st.expect(any("does not exist" in s for s in check_text("It is 5 ms [EV-077].", {"EV-001"})), "--text finds a tag for an id that does not exist")
    finally:
        common.drop_temp(root)
    return st.done()


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--text" in argv and argv.index("--text") + 1 < len(argv):
        page = argv[argv.index("--page") + 1] if "--page" in argv and argv.index("--page") + 1 < len(argv) else None
        return run_text(common.PROJECT, argv[argv.index("--text") + 1], page)
    return run(common.PROJECT)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

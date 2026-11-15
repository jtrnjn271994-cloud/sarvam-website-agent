#!/usr/bin/env python3
"""Check that every evidence note's quote appears in its library file.

Run from anywhere:  python3 -I agent/quote_match.py [--page <slug>]
Self test:          python3 -I agent/quote_match.py --selftest

For each evidence note, the script reads `quote` and `lib_ids`. It looks up each id in
library/library-register.csv, opens the library file and compares the text with all white space
collapsed to one space. The quote must appear in at least one of the files.
A note that cites a validation ledger may also match in any ledger csv file under
library/validation-ledgers (raw text, or the text of each csv cell).
A note with label UNCHECKED must match too. The label says nobody checked the claim. It does not
excuse a quote that is not in the source.
Exit 1 if any quote is not found. Standard library only.
"""
import csv
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

SPACE = re.compile(r"\s+")
LEDGER_DIR = os.path.join("library", "validation-ledgers")


def collapse(text):
    return SPACE.sub(" ", str(text or "")).strip()


def load_register(project):
    path = os.path.join(project, "library", "library-register.csv")
    if not os.path.isfile(path):
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {(r.get("id") or "").strip(): r for r in csv.DictReader(f)}


def file_texts(path):
    """Return the collapsed text of a file. For a csv file, also the collapsed text of each cell."""
    raw = common.read_text(path)
    texts = [collapse(raw)]
    if path.lower().endswith(".csv"):
        try:
            for row in csv.reader(io.StringIO(raw)):
                texts.extend(collapse(c) for c in row)
        except csv.Error:
            pass
    return texts


def ledger_files(project):
    base = os.path.join(project, LEDGER_DIR)
    out = []
    for root, _, names in os.walk(base):
        out.extend(os.path.join(root, n) for n in sorted(names) if n.lower().endswith(".csv"))
    return sorted(out)


def is_ledger_note(fm, register):
    ids = fm.get("lib_ids") if isinstance(fm.get("lib_ids"), list) else []
    for i in ids:
        if LEDGER_DIR.replace(os.sep, "/") in str((register.get(i) or {}).get("library_path", "")):
            return True
    return "ledger" in str(fm.get("source", "")).lower() or "ledger" in str(fm.get("location", "")).lower()


def check_note(project, fm, register):
    """Return (ok, message)."""
    quote = collapse(fm.get("quote"))
    if not quote:
        return False, "no quote"
    ids = fm.get("lib_ids")
    if not isinstance(ids, list) or not ids:
        return False, "no lib_ids"
    searched = []
    for i in ids:
        row = register.get(i)
        if row is None:
            searched.append("%s (not in the register)" % i)
            continue
        path = os.path.join(project, row.get("library_path", ""))
        if not os.path.isfile(path):
            searched.append("%s (file missing: %s)" % (i, row.get("library_path")))
            continue
        searched.append(row.get("library_path"))
        if any(quote in t for t in file_texts(path)):
            return True, "found in %s" % row.get("library_path")
    if is_ledger_note(fm, register):
        for path in ledger_files(project):
            if any(quote in t for t in file_texts(path)):
                return True, "found in ledger %s" % os.path.relpath(path, project)
    return False, "quote not found in: %s" % "; ".join(searched)


def check_page(project, page):
    register = load_register(project)
    results = []
    for path, fm, err in common.load_notes(project, page, "evidence"):
        name = os.path.basename(path)
        if err or not fm.get("id"):
            results.append((name, "?", False, "cannot read front matter"))
            continue
        ok, msg = check_note(project, fm, register)
        results.append((fm["id"], fm.get("label", "?"), ok, msg))
    return results


def run(project, pages=None):
    bad = total = 0
    for page in (pages or common.list_pages(project)):
        for eid, label, ok, msg in check_page(project, page):
            total += 1
            if not ok:
                bad += 1
                print("ERROR   %s (%s): %s" % (eid, label, msg))
    print("---")
    print("evidence quotes checked: %d" % total)
    print("not found: %d" % bad)
    return 1 if bad else 0


def selftest():
    st = common.SelfTest("quote_match")
    root = common.make_temp_project()
    try:
        common.write_file(os.path.join(root, "library", "library-register.csv"),
                          "id,title,library_path\nLIB-001,a,library/a/one.md\nLIB-002,b,library/validation-ledgers/led.csv\n"
                          "LIB-003,c,library/a/gone.md\n")
        common.write_file(os.path.join(root, "library", "a", "one.md"), "The service  runs\nin India, said the page.\n")
        common.write_file(os.path.join(root, "library", "validation-ledgers", "led.csv"),
                          'id,quote\nX-1,"He said ""yes"" to the plan"\n')
        reg = load_register(root)
        st.expect(check_note(root, {"quote": "service runs in India", "lib_ids": ["LIB-001"]}, reg)[0],
                  "a quote matches after white space is collapsed")
        st.expect(not check_note(root, {"quote": "service runs in Asia", "lib_ids": ["LIB-001"]}, reg)[0],
                  "a quote that is not in the file is caught")
        st.expect(not check_note(root, {"quote": "x", "lib_ids": ["LIB-009"]}, reg)[0], "an id missing from the register is caught")
        st.expect(not check_note(root, {"quote": "x", "lib_ids": ["LIB-003"]}, reg)[0], "a missing library file is caught")
        st.expect(not check_note(root, {"quote": "", "lib_ids": ["LIB-001"]}, reg)[0], "an empty quote is caught")
        st.expect(check_note(root, {"quote": 'said "yes" to', "lib_ids": ["LIB-002"]}, reg)[0],
                  "a quote matches the text of a ledger csv cell")
        st.expect(check_note(root, {"quote": 'said "yes" to', "lib_ids": ["LIB-001"], "source": "ledger row X-1"}, reg)[0],
                  "a ledger-based note may match in any ledger csv")
        st.expect(not check_note(root, {"quote": 'said "yes" to', "lib_ids": ["LIB-001"], "source": "vendor page"}, reg)[0],
                  "a note that is not ledger-based does not match in a ledger it does not cite")
        common.write_file(os.path.join(root, "pages", "p", "evidence", "ev-001-a.md"),
                          common.evidence_text(id="EV-001", label="UNCHECKED", lib_ids="[LIB-001]", quote="\"runs in Asia\""))
        st.expect(run(root) == 1, "run() exits 1 on a planted bad quote, even when the label is UNCHECKED")
        common.write_file(os.path.join(root, "pages", "p", "evidence", "ev-001-a.md"),
                          common.evidence_text(id="EV-001", lib_ids="[LIB-001]", quote="\"runs in India\""))
        st.expect(run(root) == 0, "run() exits 0 when the quote is in the file")
    finally:
        common.drop_temp(root)
    return st.done()


def main(argv):
    if "--selftest" in argv:
        return selftest()
    pages = [argv[argv.index("--page") + 1]] if "--page" in argv and argv.index("--page") + 1 < len(argv) else None
    return run(common.PROJECT, pages)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

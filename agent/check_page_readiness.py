#!/usr/bin/env python3
"""Check that a page has the inputs the agent needs before it starts work.

Run from anywhere:  python3 -I agent/check_page_readiness.py --page <slug>
All pages:          python3 -I agent/check_page_readiness.py --all
Self test:          python3 -I agent/check_page_readiness.py --selftest

Reads pages/<slug>/profile.json, field needed_insights. Each item is an object
{id, label, path_glob, min_files, how_to_fill}. The script counts the files that match.
A path_glob that starts with library/ or skills/ is relative to the project root.
Any other path_glob is relative to the page folder.
Exit 1 if any item is MISSING. Person tasks print as PERSON and do not change the exit code.
Standard library only.
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

PERSON_FIELDS = ["goal", "buyer", "main_cta"]


def count_matches(project, page, pattern):
    if ".." in pattern.replace("\\", "/").split("/") or os.path.isabs(pattern):
        return -1
    root = project if pattern.startswith(("library/", "skills/")) else os.path.join(project, "pages", page)
    return len([p for p in glob.glob(os.path.join(root, pattern)) if os.path.isfile(p)])


def person_gaps(profile):
    gaps = []
    for field in PERSON_FIELDS:
        if not str(profile.get(field) or "").strip():
            gaps.append("field '%s' is empty" % field)
    if str(profile.get("status") or "").strip() in ("", "needs-confirmation"):
        gaps.append("status is still 'needs-confirmation'")
    return gaps


def check_page(project, page):
    """Return (lines, missing, person). lines is a list of printable strings."""
    profile = common.load_profile(project, page)
    if profile is None:
        return ["MISSING  profile.json is not found or does not parse: pages/%s/profile.json" % page], 1, 0
    lines, missing, person = [], 0, 0
    gaps = person_gaps(profile)
    for g in gaps:
        lines.append("PERSON   %s. A person must confirm it." % g)
        person += 1
    insights = profile.get("needed_insights")
    if not isinstance(insights, list) or not insights:
        lines.append("MISSING  needed_insights is empty or not a list")
        return lines, missing + 1, person
    for item in insights:
        if not isinstance(item, dict) or "id" not in item:
            lines.append("MISSING  a needed_insights entry is not an object with an id")
            missing += 1
            continue
        iid = item["id"]
        how = item.get("how_to_fill", "")
        if item.get("person_task"):
            if gaps:
                lines.append("PERSON   %s: %s" % (iid, how))
            else:
                lines.append("OK       %s" % iid)
            continue
        pattern = item.get("path_glob", "")
        need = item.get("min_files", 1)
        if not pattern or not isinstance(need, int):
            lines.append("MISSING  %s: path_glob or min_files is not set" % iid)
            missing += 1
            continue
        n = count_matches(project, page, pattern)
        if n < 0:
            lines.append("MISSING  %s: path_glob must stay inside the project" % iid)
            missing += 1
        elif n >= need:
            lines.append("OK       %s (%d of %d files: %s)" % (iid, n, need, pattern))
        else:
            lines.append("MISSING  %s (%d of %d files: %s). To fill: %s" % (iid, n, need, pattern, how))
            missing += 1
    return lines, missing, person


def run(project, pages):
    total_missing = 0
    for page in pages:
        print("page: %s" % page)
        lines, missing, person = check_page(project, page)
        for line in lines:
            print("  " + line)
        print("  result: %d missing, %d person tasks" % (missing, person))
        total_missing += missing
    return 1 if total_missing else 0


def selftest():
    st = common.SelfTest("check_page_readiness")
    root = common.make_temp_project()
    try:
        page = os.path.join(root, "pages", "demo")
        common.write_file(os.path.join(page, "evidence", "ev-001-a.md"), "x")
        common.write_file(os.path.join(root, "library", "brand", "rules", "r.md"), "x")
        profile = {
            "goal": "", "buyer": "a buyer", "main_cta": "go", "status": "needs-confirmation",
            "needed_insights": [
                {"id": "ev", "path_glob": "evidence/ev-*.md", "min_files": 1, "how_to_fill": "run A"},
                {"id": "more_ev", "path_glob": "evidence/ev-*.md", "min_files": 3, "how_to_fill": "run B"},
                {"id": "brand", "path_glob": "library/brand/rules/*.md", "min_files": 1, "how_to_fill": "run C"},
                {"id": "audit", "path_glob": "research/audit/*/x.md", "min_files": 1, "how_to_fill": "run D"},
                {"id": "confirmed", "person_task": True, "how_to_fill": "a person confirms"},
            ]}
        common.write_file(os.path.join(page, "profile.json"), __import__("json").dumps(profile))
        lines, missing, person = check_page(root, "demo")
        text = "\n".join(lines)
        st.expect("OK       ev (" in text, "a satisfied item prints OK")
        st.expect("MISSING  more_ev" in text and "run B" in text, "an item under its minimum prints MISSING with how_to_fill")
        st.expect("OK       brand" in text, "a glob that starts with library/ resolves from the project root")
        st.expect("MISSING  audit" in text and missing == 2, "an item with no files prints MISSING (2 missing in total)")
        st.expect("field 'goal' is empty" in text and "needs-confirmation" in text and person >= 2,
                  "an empty goal and an unconfirmed status print as person tasks")
        st.expect(run(root, ["demo"]) == 1, "the exit code is 1 when anything is MISSING")
        profile["needed_insights"] = [profile["needed_insights"][0]]
        profile["goal"] = "goal"
        profile["status"] = "confirmed"
        common.write_file(os.path.join(page, "profile.json"), __import__("json").dumps(profile))
        st.expect(run(root, ["demo"]) == 0, "the exit code is 0 when nothing is MISSING")
        profile["needed_insights"] = [{"id": "esc", "path_glob": "../x/*.md", "min_files": 1, "how_to_fill": "n"}]
        common.write_file(os.path.join(page, "profile.json"), __import__("json").dumps(profile))
        lines, missing, _ = check_page(root, "demo")
        st.expect(missing == 1 and "inside the project" in lines[0], "a path_glob that leaves the project is refused")
    finally:
        common.drop_temp(root)
    return st.done()


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--all" in argv:
        pages = [p for p in common.list_pages(common.PROJECT)
                 if os.path.isfile(os.path.join(common.PROJECT, "pages", p, "profile.json"))]
    elif "--page" in argv and argv.index("--page") + 1 < len(argv):
        pages = [argv[argv.index("--page") + 1]]
    else:
        print("Use --page <slug>, --all or --selftest")
        return 2
    return run(common.PROJECT, pages)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

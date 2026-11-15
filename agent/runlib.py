#!/usr/bin/env python3
"""Small helpers for run folders. Standard library only.

A run folder is pages/<page>/runs/<run-id>/. This file makes the run id, reads and writes json
and loads the evidence and claim notes of a page. Not run on its own, except for --selftest.
"""
import datetime
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

RUN_ID = re.compile(r"^(\d{4}-\d{2}-\d{2})-run-(\d{2,})$")


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def safe_id(value, what="id"):
    """Return a page or run id when it is a safe slug. Raise ValueError otherwise.
    Safe: letters, digits, dot, underscore and hyphen, starting with a letter or digit, and no "..".
    This is not the strict RUN_ID form: run ids made by hand (for example "r1") stay valid."""
    if not isinstance(value, str) or not SAFE_ID.match(value) or ".." in value:
        raise ValueError("Unsafe %s %r. Use letters, digits, dot, underscore and hyphen only, starting with a letter or digit." % (what, value))
    return value


def _inside(base, path):
    """True when the real path of `path` sits inside the real path of `base` (symlinks resolved)."""
    base_real, path_real = os.path.realpath(base), os.path.realpath(path)
    return path_real != base_real and os.path.commonpath([base_real, path_real]) == base_real


def runs_dir(project, page):
    safe_id(page, "page id")
    base = os.path.join(project, "pages", page, "runs")
    if not _inside(os.path.join(project, "pages"), base):
        raise ValueError("The runs folder of page %r resolves outside the project pages folder." % page)
    return base


def new_run_id(project, page, today=None):
    day = today or datetime.date.today().isoformat()
    top = 0
    base = runs_dir(project, page)
    if os.path.isdir(base):
        for name in os.listdir(base):
            m = RUN_ID.match(name)
            if m and m.group(1) == day:
                top = max(top, int(m.group(2)))
    return "%s-run-%02d" % (day, top + 1)


def run_path(project, page, run_id):
    """The folder of one run. Validates both ids and checks the real path stays inside pages/<page>/runs/."""
    base = runs_dir(project, page)
    safe_id(run_id, "run id")
    path = os.path.join(base, run_id)
    if not _inside(base, path):
        raise ValueError("Run id %r resolves outside pages/%s/runs/." % (run_id, page))
    return path


def jwrite(path, obj):
    common.write_file(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def jread(path, default=None):
    if not os.path.isfile(path):
        return default
    try:
        return common.load_json(path)
    except ValueError:
        return default


def load_evidence(project, page):
    """Return {EV-id: front matter} for every readable evidence note."""
    return {fm["id"]: fm for _, fm, err in common.load_notes(project, page, "evidence") if not err and fm.get("id")}


def load_claims(project, page):
    """Return a list of claim front matter dicts, sorted by id."""
    out = [fm for _, fm, err in common.load_notes(project, page, "claims") if not err and fm.get("id")]
    return sorted(out, key=lambda f: f["id"])


# ---------- draft hash and approval ----------

HASH_FILES = ["copy-A.json", "copy-B.json", "design-A.json", "design-B.json"]  # the four draft files. draft_hash lists these as "missing" when absent.
HASH_SHOWN = 16
VARIANT_NAMES = ("A", "B")
STALE_TEXT = "the draft changed after approval; new approval needed"

# The approval manifest: everything a person sees or that fixes the test. One approval ties to all of it.
RUN_MANIFEST_FILES = HASH_FILES + ["variants.json", "baseline.json", "position.json", "plan.json"]  # plan.json holds the metric, the arms and the decision rule
PREVIEW_DIR = "pages"  # the rendered preview pages and their assets, every file under it
PAGE_MANIFEST_FILES = ["brief.json", "render-map.json", "sandbox-baseline.json"]  # pages/<page>/. The brief is frozen into the run later (G25); until then it is hashed by path.
PROJECT_MANIFEST_FILES = ["agent/sandbox_demos.json"]  # the decision-rule and sandbox settings that plan.json is made from
# Left out on purpose, because they hold the hash or change on every resume: meta.json, review.html, review-digest.txt, report.md,
# APPROVAL-NEEDED.md, approvals.json, revise-request.json, step-state.json, run-log*.csv, cache/, prompts/, replies/, sandbox-*.json, screenshots/.
NOISE_NAMES = (".DS_Store",)
# An engine run (it has run-manifest.json) is approved over its own files. run-manifest.json holds the hashes of the frozen inputs, the flow and the code.
# The page folder and the project files are not read for an engine run: the run folder holds frozen copies of them.
ENGINE_MANIFEST = "run-manifest.json"
V2_RUN_FILES = [ENGINE_MANIFEST, "brief.json", "start-1-goal-page.json", "start-2-scope.json", "start-3-buyer.json", "start-4-test-type.json",
                "argument.json", "layout-manifest.json", "evidence-preview.html"]


def is_engine_run(run_dir):
    return os.path.isfile(os.path.join(run_dir, ENGINE_MANIFEST))


def _layout(run_dir):
    """Return (page_dir, project_dir) when run_dir sits at <project>/pages/<page>/runs/<run>. A part that is not there is None."""
    runs = os.path.dirname(os.path.abspath(run_dir))
    if os.path.basename(runs) != "runs":
        return None, None
    page_dir = os.path.dirname(runs)
    pages = os.path.dirname(page_dir)
    return page_dir, (os.path.dirname(pages) if os.path.basename(pages) == "pages" else None)


def manifest_entries(run_dir):
    """The approval manifest as a sorted list of (label, absolute path, exists). The label is the relative path shown to a person."""
    run_dir = os.path.abspath(run_dir)
    page_dir, project_dir = _layout(run_dir)
    items = [(n, os.path.join(run_dir, n)) for n in RUN_MANIFEST_FILES]
    engine_run = is_engine_run(run_dir)
    if engine_run:
        items += [(n, os.path.join(run_dir, n)) for n in V2_RUN_FILES]
    elif os.path.isfile(os.path.join(run_dir, "brief.json")):  # a brief frozen into the run. Covered when present.
        items.append(("brief.json", os.path.join(run_dir, "brief.json")))
    if page_dir and not engine_run:
        items += [("page/" + n, os.path.join(page_dir, n)) for n in PAGE_MANIFEST_FILES]
    if project_dir and not engine_run:
        items += [("project/" + n, os.path.join(project_dir, *n.split("/"))) for n in PROJECT_MANIFEST_FILES]
    pdir = os.path.join(run_dir, PREVIEW_DIR)
    found = []
    for base, dirs, files in os.walk(pdir):
        dirs.sort()
        for f in sorted(files):
            if f not in NOISE_NAMES:
                found.append(os.path.join(base, f))
    if found:
        for path in found:
            items.append((PREVIEW_DIR + "/" + os.path.relpath(path, pdir).replace(os.sep, "/"), path))
    elif not engine_run:
        items.append((PREVIEW_DIR + "/", os.path.join(pdir, "(no rendered pages)")))  # no rendered pages yet: recorded as MISSING
    return sorted((label, path, os.path.isfile(path)) for label, path in items)


def approval_manifest(run_dir):
    """The relative paths the draft hash covers, sorted. The review page and the run print this list."""
    return [label for label, _, _ in manifest_entries(run_dir)]


def manifest_summary(run_dir):
    """One plain sentence part that says what the hash covers: the named files, the missing ones marked, and the count of preview files."""
    entries = manifest_entries(run_dir)
    pre = PREVIEW_DIR + "/"
    named = ["%s%s" % (label, "" if exists else " (MISSING)") for label, _, exists in entries if not label.startswith(pre)]
    previews = [e for e in entries if e[0].startswith(pre)]
    n_prev = sum(1 for e in previews if e[2])
    return "%d files: %s, and %d rendered preview files under %s (%s)" % (
        len(named) + n_prev, ", ".join(named), n_prev, pre,
        ", ".join(l for l, _, ex in previews if ex) or "none yet, MISSING")


def draft_hash(run_dir):
    """One sha256 over the approval manifest, so an approval ties to everything a person saw and to the fixed test.
    Each file adds its relative path, its length and its bytes, in sorted path order. A missing file adds the path and MISSING.
    Return (full hex, missing names). The missing names are the four draft files only. Other absent files change the hash but do not block."""
    h = hashlib.sha256()
    for label, path, exists in manifest_entries(run_dir):
        if not exists:
            h.update(("%s\nMISSING\n" % label).encode("utf-8"))
            continue
        with open(path, "rb") as f:
            data = f.read()
        h.update(("%s\n%d\n" % (label, len(data))).encode("utf-8"))
        h.update(data)
    missing = [n for n in HASH_FILES if not os.path.isfile(os.path.join(run_dir, n))]
    return h.hexdigest(), missing


def short_hash(run_dir):
    return draft_hash(run_dir)[0][:HASH_SHOWN]


def variant_list(value, available=VARIANT_NAMES):
    """Turn the variant field of an approval into a list of names. Missing or 'both' means every variant."""
    if value is None or value == "" or value == []:
        return list(available)
    items = value if isinstance(value, (list, tuple)) else [value]
    out = []
    for x in items:
        x = str(x).strip()
        if x.lower() == "both":
            return list(available)
        if x not in out:
            out.append(x)
    return out


def read_approval(run_dir):
    """Read approvals.json and judge it against the draft files now in the folder. Never writes.

    Return a dict: status (none, approved, rejected, stale), approved (bool), variant (list or None), via, date,
    draft_hash, warning, inactive (list of variant names marked inactive).
    Rules: a hash that does not match the draft means STOP (stale). A rejection approves nothing and marks its variants inactive.
    The old form {"approved": true} holds no hash. It never approves: status stale, with a warning that an approval needs a current hash."""
    path = os.path.join(run_dir, "approvals.json")
    data = jread(path, None)
    base = {"status": "none", "approved": False, "via": None, "date": None, "variant": None, "draft_hash": None, "warning": None, "inactive": []}
    if not isinstance(data, dict):
        return base
    full, _ = draft_hash(run_dir)
    names = variant_list(data.get("variant"))
    decision = str(data.get("decision") or "").lower()
    if decision in ("approved", "rejected"):
        given = str(data.get("draft_hash") or "").strip().lower()
        out = dict(base, via=str(data.get("via") or "approvals.json"), date=data.get("date"), draft_hash=given or None, variant=names)
        if len(given) < HASH_SHOWN or not full.startswith(given):
            out.update(status="stale", warning="The approval file %s. %s." % ("has no draft_hash" if not given else "holds hash %s, but the draft hash is %s" % (given[:HASH_SHOWN], full[:HASH_SHOWN]), STALE_TEXT))
            return out
        if decision == "rejected":
            out.update(status="rejected", inactive=names)
            return out
        out.update(status="approved", approved=True)
        return out
    if data.get("approved") is True:
        # The old form {"approved": true} holds no draft hash. It is a historical record only. It never approves.
        return dict(base, status="stale", via=str(data.get("via") or "approvals.json"), date=data.get("date"),
                    warning="The approval file uses the old form {\"approved\": true}. An approval needs a current draft_hash. It is kept as a record and approves nothing. A person must approve again.")
    return base


def selftest():
    st = common.SelfTest("runlib")
    root = common.make_temp_project()
    try:
        st.expect(new_run_id(root, "p", "2026-11-14") == "2026-11-14-run-01", "the first run id of a day ends in 01")
        os.makedirs(os.path.join(run_path(root, "p", "2026-11-14-run-01")))
        os.makedirs(os.path.join(run_path(root, "p", "2026-11-13-run-07")))
        st.expect(new_run_id(root, "p", "2026-11-14") == "2026-11-14-run-02", "the next run id counts only the same day")
        for bad in ("../../x", "/abs", "a/b", "", "a..b"):
            try:
                run_path(root, "p", bad)
                st.expect(False, "run id %r is refused" % bad)
            except ValueError:
                st.expect(True, "run id %r is refused" % bad)
        try:
            run_path(root, "../p", "r1")
            st.expect(False, "a page id with .. is refused")
        except ValueError:
            st.expect(True, "a page id with .. is refused")
        st.expect(run_path(root, "p", "r1").endswith(os.path.join("pages", "p", "runs", "r1")), "a hand-made run id such as r1 stays valid")
        jwrite(os.path.join(root, "a", "b.json"), {"x": "é"})
        st.expect(jread(os.path.join(root, "a", "b.json")) == {"x": "é"}, "json round trip works")
        st.expect(jread(os.path.join(root, "none.json"), 5) == 5, "a missing file gives the default")
        common.write_file(os.path.join(root, "pages", "p", "evidence", "ev-001-a.md"), common.evidence_text())
        common.write_file(os.path.join(root, "pages", "p", "claims", "cl-001-a.md"), common.claim_text())
        st.expect(list(load_evidence(root, "p")) == ["EV-001"] and load_claims(root, "p")[0]["id"] == "CL-001",
                  "evidence and claim notes load")
        rd = run_path(root, "p", "2026-11-14-run-09")
        for f in HASH_FILES:
            jwrite(os.path.join(rd, f), {"f": f})
        h = draft_hash(rd)[0]
        st.expect(len(h) == 64 and short_hash(rd) == h[:16], "the draft hash is a sha256 and the shown form is its first 16 characters")
        st.expect(read_approval(rd)["status"] == "none", "no approvals.json means no approval")
        jwrite(os.path.join(rd, "approvals.json"), {"decision": "approved", "variant": "both", "draft_hash": h[:16], "date": "2026-11-14"})
        a = read_approval(rd)
        st.expect(a["status"] == "approved" and a["approved"] and a["variant"] == ["A", "B"], "a matching hash approves, and 'both' means every variant")
        jwrite(os.path.join(rd, "copy-A.json"), {"f": "changed"})
        a = read_approval(rd)
        st.expect(a["status"] == "stale" and not a["approved"] and STALE_TEXT in a["warning"], "a draft that changed after approval is stale and approves nothing")
        jwrite(os.path.join(rd, "approvals.json"), {"decision": "rejected", "variant": "A", "draft_hash": short_hash(rd)})
        a = read_approval(rd)
        st.expect(a["status"] == "rejected" and a["inactive"] == ["A"] and not a["approved"], "a rejection approves nothing and marks its variant inactive")
        jwrite(os.path.join(rd, "approvals.json"), {"approved": True})
        a = read_approval(rd)
        st.expect(a["status"] == "stale" and not a["approved"] and "needs a current draft_hash" in a["warning"], "the old form no longer approves, and the warning says an approval needs a current hash")
        jwrite(os.path.join(rd, "approvals.json"), {"decision": "approved", "variant": "A"})
        st.expect(read_approval(rd)["status"] == "stale", "an approval with no hash is not valid")
    finally:
        common.drop_temp(root)
    return st.done()


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else 2)

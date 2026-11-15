"""The library rules for a run. Standard library only. No model.

Step 3a builds the library inventory from library/library-register.csv and rules/library-tags.json.
The engine guard then checks every model prompt. A model step may read only:
  (a) files the inventory passed (their frozen copies), each with its full stamp (id, source, owner, tier, dates),
  (b) files in the page's saved capture folder,
  (c) the person's answers and outputs of earlier run steps (data packs, not files),
  (d) the page's claims and evidence notes, when each one cites a passed library id, names a passed file, or cites the capture,
  (e) the frozen skill files and the frozen run contract.
Only a row that is AUDIT is blocked: owner gpt, type audit, or the word audit in its source. The test reads the register
ROW, never the path. Third-party text (official pages, call transcripts, tender texts) may pass, with its stamp.
A row past its review_by date is stale and is not passed either. This module never reads a file for a model.
"""
import csv
import datetime
import os
import re

import common

RULES_REL = "rules/library-tags.json"
REGISTER_REL = "library/library-register.csv"
INDEX_REL = "library/INDEX.md"
CONTRACT_REL = "rules/run-contract.md"
INVENTORY_FILE = "library-inventory.json"
INVENTORY_TEXT = "library-inventory.txt"
RESOURCES_FILE = "start-3b-resources.json"
WORD = re.compile(r"[a-z0-9]+")
LIB_ID = re.compile(r"^LIB-([0-9]+)$")
ADDED_PREFIX = "added by the person"  # a register row whose source starts like this is evidence label UNCHECKED
INDEX_ROW = re.compile(r"^\|\s*\[([^\]]+)\]\(([^)]*)\)\s*\|\s*(.*?)\s*\|\s*([0-9]+)\s*\|\s*$")
TAG_KEYS = ("product", "industry", "category")


def load_rules(root):
    """The tag rules from a project folder (the frozen copy inside a run). {} when the file is missing."""
    path = os.path.join(root, *RULES_REL.split("/"))
    if not os.path.isfile(path):
        return {}
    return common.load_json(path)


def load_register(root):
    path = os.path.join(root, *REGISTER_REL.split("/"))
    if not os.path.isfile(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return [dict((k, (v or "").strip()) for k, v in r.items()) for r in csv.DictReader(f)]


def _words(text, n):
    return [w for w in WORD.findall(str(text or "").lower()) if len(w) >= n]


def _spec_hit(row, spec):
    path, title = row["library_path"].lower(), row["title"].lower()
    return (any(p in path for p in spec.get("path_contains") or []) or any(w in title for w in spec.get("title_words") or [])
            or row.get("relevance") in (spec.get("relevance") or []))


def _entries_for(text, entries):
    t = str(text or "").lower()
    return [e for e in entries if any(n in t or (len(t) >= 3 and t in n) for n in e.get("names") or [])]


def product_hit(row, product, rules):
    ents = _entries_for(product, rules.get("products") or [])
    if ents:
        return any(_spec_hit(row, e) for e in ents)
    ws = _words(product, rules.get("min_word_length", 4))
    hay = (row["title"] + " " + row["library_path"]).lower()
    return bool(ws) and all(w in hay for w in ws)


def industry_hit(row, vertical, rules):
    ents = _entries_for(vertical, rules.get("industries") or [])
    if ents:
        return any(_spec_hit(row, e) for e in ents)
    hay = (row["title"] + " " + row["library_path"]).lower()
    return any(w in hay for w in _words(vertical, rules.get("min_word_length", 4)))


def categories_of(row, rules):
    """The category words are matched against the file name and the title only, not the folder names (a folder like buyers-and-committees holds every kind)."""
    name_row = dict(row, library_path=os.path.basename(row["library_path"]))
    return [c["name"] for c in rules.get("categories") or [] if _spec_hit(name_row, c)]


def buyer_hit(row, role, rules, cats, ind):
    if ind and set(cats) & set(rules.get("buyer_categories") or []):
        return True
    hay = (row["title"] + " " + row["library_path"]).lower()
    return any(w in hay for w in _words(role, rules.get("min_word_length", 4)))


# ---------------------------------------------------------------- the audit rule and the other exclusions

def audit_reason(row, rules):
    """Why a register row is AUDIT, or ''. The rule reads the row: its owner, its type and its source. Never the path."""
    ex = rules.get("exclude") or {}
    why = []
    if row.get("owner", "").lower() in (ex.get("owners") or []):
        why.append("owner %s (AUDIT)" % row["owner"])
    if row.get("type", "").lower() in (ex.get("types") or []):
        why.append("type %s (AUDIT)" % row["type"])
    if any(w in row.get("source", "").lower() for w in ex.get("source_words") or []):
        why.append("source says audit (AUDIT)")
    return "; ".join(why)


def row_problems(row, rules, today, sha_of):
    """Every reason a row may not go to a model. Empty list: it may. sha_of(path) gives the sha256 of the file the run holds, or None."""
    why = []
    a = audit_reason(row, rules)
    if a:
        why.append(a + ", never sent to a model")
    if (rules.get("exclude") or {}).get("past_review_by") and row["review_by"] and row["review_by"] not in ("none",) and row["review_by"] < today:
        why.append("past review_by (%s)" % row["review_by"])
    if not why:
        sha = sha_of(row["library_path"])
        if sha is None:
            why.append("the file is missing at %s" % row["library_path"])
        elif sha != row["sha256"]:
            why.append("sha256 differs from the register (register %s, file %s)" % (row["sha256"][:12], sha[:12]))
    return why


def parse_added_tags(source):
    """The tags a person gave when adding a resource, from the source text: '; covers product: X; industry: Y; category: Z'."""
    out = {}
    for k in TAG_KEYS:
        m = re.search(r"%s: ([^;]*)" % k, source or "")
        if m and m.group(1).strip():
            out[k] = m.group(1).strip()
    return out


def is_added(row):
    return row.get("source", "").startswith(ADDED_PREFIX)


def _same(tag, wanted):
    a, b = str(tag or "").strip().lower(), str(wanted or "").strip().lower()
    return bool(a and b) and (a in b or b in a)


def stamp_of(row, matches, cats):
    return {"id": row["id"], "title": row["title"], "type": row["type"], "tier": row["tier"], "owner": row["owner"], "source": row["source"],
            "data_as_of": row["data_as_of"], "status": row["status"], "review_by": row["review_by"], "path": row["library_path"], "sha256": row["sha256"],
            "matches": matches, "categories": cats, "label": "UNCHECKED" if is_added(row) else None}


def build_inventory(rows, rules, product, vertical, role, today, sha_of, page=None, force_ids=()):
    """Return the inventory dict. sha_of(path) gives the sha256 of the file now, or None when it is missing. today is 'YYYY-MM-DD'.
    A file the person added for this page always reaches the prompt (with its UNCHECKED stamp), but it counts for the product or the industry
    only when the tags the person gave match. force_ids are register rows the person named (for example the positioning source)."""
    passed, excluded = [], []
    for row in rows:
        cats = categories_of(row, rules)
        added_here = bool(page) and is_added(row) and ("added-by-person/%s/" % page) in row["library_path"]
        if added_here:
            tags = parse_added_tags(row["source"])
            pr, ind, by = _same(tags.get("product"), product), _same(tags.get("industry"), vertical), False
            if tags.get("category") and tags["category"] not in cats:
                cats = cats + [tags["category"]]
        else:
            pr, ind = product_hit(row, product, rules), industry_hit(row, vertical, rules)
            by = buyer_hit(row, role, rules, cats, ind)
        named = row["id"] in force_ids
        if not (pr or ind or by or added_here or named):
            continue
        matches = [n for n, hit in (("product", pr), ("industry", ind), ("buyer", by), ("named", named)) if hit]
        why = row_problems(row, rules, today, sha_of)
        if why:
            excluded.append({"id": row["id"], "path": row["library_path"], "reason": "; ".join(why), "matches": matches, "owner": row["owner"], "source": row["source"]})
        else:
            passed.append(stamp_of(row, matches, cats))
    by_cat = {}
    for it in passed:
        for c in it["categories"]:
            by_cat.setdefault(c, []).append(it)
    names = [c["name"] for c in rules.get("categories") or []]
    dims = (("product", product), ("industry", vertical), ("buyer", role))
    missing = []
    for c in names:
        gone = ["%s '%s'" % (d, v) for d, v in dims if not any(d in it["matches"] for it in by_cat.get(c, []))]
        if gone:
            missing.append("%s: no usable file for %s" % (c, ", ".join(gone)))
    stop = []
    for d, v in dims[:2]:
        if not any(d in it["matches"] for it in passed):
            stop.append("the library holds no usable file for the %s '%s'. Research to add: %s for the %s '%s'"
                        % (d, v, ", ".join(names) or "any category", d, v))
    return {"step": "3a", "product": product, "vertical": vertical, "buyer": role, "today": today,
            "counts": {"matching": len(passed) + len(excluded), "passed": len(passed), "excluded": len(excluded)},
            "categories": by_cat, "passed": passed, "excluded": excluded, "missing": missing, "stop": stop}


def _in_ranges(lib_id, ranges):
    m = LIB_ID.match(lib_id)
    return bool(m) and any(LIB_ID.match(a) and LIB_ID.match(b) and int(LIB_ID.match(a).group(1)) <= int(m.group(1)) <= int(LIB_ID.match(b).group(1)) for a, b in ranges)


def select_groups(rows, rules, vertical, today, sha_of):
    """The three named input groups for generating a positioning (option B). Return (groups, excluded, empty).
    groups: {name: [stamp]}. A group is chosen by register ids, id ranges and folder rules from rules/library-tags.json. Audit, stale and changed rows are left out and named."""
    groups, excluded = {}, []
    for name, spec in (rules.get("input_groups") or {}).items():
        picked = []
        for row in rows:
            cats = categories_of(row, rules)
            hit = row["id"] in (spec.get("ids") or []) or _in_ranges(row["id"], spec.get("id_ranges") or [])
            for fr in spec.get("folder_rules") or []:
                if (fr.get("path_contains", "\0") in row["library_path"] and (not fr.get("needs_industry") or industry_hit(row, vertical, rules))
                        and (not fr.get("categories") or set(cats) & set(fr["categories"]))):
                    hit = True
            if not hit:
                continue
            why = row_problems(row, rules, today, sha_of)
            if why:
                excluded.append({"id": row["id"], "path": row["library_path"], "reason": "; ".join(why), "group": name})
            else:
                it = stamp_of(row, ["group"], cats)
                it["group"] = name
                picked.append(it)
        groups[name] = picked
    return groups, excluded, [n for n, v in groups.items() if not v]


def index_folders(text):
    """The folder table of library/INDEX.md: [{folder, path, what, files}]."""
    out = []
    for line in str(text or "").splitlines():
        m = INDEX_ROW.match(line)
        if m:
            out.append({"folder": m.group(1), "path": m.group(2), "what": m.group(3), "files": m.group(4)})
    return out


def text_view(inv):
    L = ["Library inventory (step 3a)", "Product: %s. Industry: %s. Buyer: %s." % (inv["product"], inv["vertical"], inv["buyer"]),
         "Files passed: %d. Files excluded: %d." % (inv["counts"]["passed"], inv["counts"]["excluded"]), ""]
    for cat in sorted(inv["categories"]):
        L.append("%s (%d)" % (cat, len(inv["categories"][cat])))
        for it in inv["categories"][cat]:
            L.append("  %s | %s | type %s | tier %s | owner %s | source %s | data_as_of %s | status %s | review_by %s | matches %s" % (
                it["id"], it["title"], it["type"], it["tier"], it["owner"], it["source"], it["data_as_of"] or "-", it["status"], it["review_by"] or "-", ", ".join(it["matches"]))
                     + (" | label UNCHECKED (added by the person)" if it.get("label") else ""))
    L.append("")
    L.append("Excluded (never sent to a model):")
    L += ["  %s | %s | %s" % (e["id"], e["path"], e["reason"]) for e in inv["excluded"]] or ["  none"]
    L.append("")
    L.append("Missing:")
    L += ["  " + m for m in inv["missing"]] or ["  none"]
    idx = inv.get("index") or {}
    L.append("")
    L.append("Library folders (library/INDEX.md, read only):")
    L += ["  %s: %s (%s files)" % (f["folder"], f["what"], f["files"]) for f in idx.get("folders") or []] or ["  no folder table found"]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- the guard

def current_inventory(run_dir):
    """The inventory of a run: step 3b's recomputed one when it made one, else step 3a's. The rows of the positioning input groups (option B) are added.
    None when step 3a made none."""
    import copy
    import runlib
    b = runlib.jread(os.path.join(run_dir, RESOURCES_FILE), None)
    inv = b.get("inventory") if isinstance(b, dict) and isinstance(b.get("inventory"), dict) else runlib.jread(os.path.join(run_dir, INVENTORY_FILE), None)
    if not isinstance(inv, dict):
        return None
    inv = copy.deepcopy(inv)
    have = set(r["id"] for r in inv["passed"])
    for rows in ((b or {}).get("groups") or {}).values():
        for r in rows:
            if r["id"] not in have:
                inv["passed"].append(dict(r))
                have.add(r["id"])
    return inv


def passed_ids(inv):
    return set(r["id"] for r in (inv or {}).get("passed") or [])


def passed_paths(inv):
    return set(r["path"] for r in (inv or {}).get("passed") or [])


def _as_list(v):
    return v if isinstance(v, list) else ([v] if v else [])


def note_status(root, page, inv):
    """Which claim and evidence notes may go into a prompt. Return (allowed_paths, excluded_ids).
    An evidence note needs a passed library id, or its quoted source must name a passed file (by path or file name), or it cites the page capture.
    A claim needs one allowed evidence note."""
    ids, paths = passed_ids(inv), passed_paths(inv)
    names = set(os.path.basename(p) for p in paths if len(os.path.basename(p)) >= 6)
    allowed, excluded, ok_ev = set(), [], set()
    for path, fm, err in common.load_notes(root, page, "evidence"):
        if err or not fm.get("id"):
            continue
        where = str(fm.get("location") or "") + " " + str(fm.get("source") or "")
        if (ids & set(_as_list(fm.get("lib_ids"))) or "capture/" in where or any(p in where for p in paths) or any(n in where for n in names)):
            allowed.add(common.rel(root, path))
            ok_ev.add(fm["id"])
        else:
            excluded.append(fm["id"])
    for path, fm, err in common.load_notes(root, page, "claims"):
        if err or not fm.get("id"):
            continue
        if ok_ev & set(_as_list(fm.get("evidence_ids"))):
            allowed.add(common.rel(root, path))
        else:
            excluded.append(fm["id"])
    return allowed, excluded


def audit_files(root, files, rules=None):
    """Of these library paths, the ones whose register row is AUDIT. Read from the register of the folder given (the frozen copy)."""
    rules = rules or load_rules(root)
    bad = set(r["library_path"] for r in load_register(root) if audit_reason(r, rules))
    return [f for f in files if f in bad]


def offenders(root, page, inv, files):
    """The files in a prompt that the guard does not allow. root is the frozen project folder of the run."""
    ok_paths, cap = passed_paths(inv), "pages/%s/capture/" % page
    notes, _ = note_status(root, page, inv)
    note_dirs = ("pages/%s/claims/" % page, "pages/%s/evidence/" % page)
    bad = []
    for rel in files:
        if rel in ok_paths or rel.startswith(cap) or rel.startswith("skills/") or rel == CONTRACT_REL:
            continue
        if rel.startswith(note_dirs) and rel in notes:
            continue
        bad.append(rel)
    return bad


def unrecorded_text(root, manifest_inputs, allowed_paths, prompt, skip=()):
    """The frozen files whose text sits in the assembled prompt although the guard did not allow them. A file counts when three 100-character
    samples (start, middle, end) are all found in the prompt. Return the file names."""
    found = []
    for rel in sorted(manifest_inputs):
        if rel in allowed_paths or rel in skip or rel.startswith(("skills/", "schemas/")):
            continue
        try:
            with open(os.path.join(root, *rel.split("/")), encoding="utf-8") as f:
                t = f.read().strip()
        except (OSError, UnicodeDecodeError):
            continue
        if len(t) < 300:
            continue
        n = len(t)
        samples = [t[:100], t[n // 2 - 50:n // 2 + 50], t[-100:]]
        if all(s in prompt for s in samples):
            found.append(rel)
    return found


def today_of(manifest):
    return str((manifest or {}).get("started") or datetime.date.today().isoformat())[:10]

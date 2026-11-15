"""Shared helpers for the check scripts. Standard library only.

Scripts add their own folder to sys.path, because `python3 -I` does not.
"""
import csv
import json
import os
import re
import shutil
import tempfile

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(AGENT_DIR)

LABELS = ["CHECKED", "CALC", "VENDOR", "SEMRUSH", "AUDIT", "PROPOSED", "UNCHECKED"]
# Strongest first. A claim may not be stronger than its weakest evidence.
STRENGTH = {"CHECKED": 0, "CALC": 1, "SEMRUSH": 2, "VENDOR": 3,
            "PROPOSED": 4, "UNCHECKED": 5, "AUDIT": 6}
KEY_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$")


def parse_value(raw):
    """Bare text, "quoted" text or an inline list like [A, B]."""
    v = raw.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [parse_value(p) for p in inner.split(",")]
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def parse_front_matter(text):
    """Return (dict, error). error is None when the block parses."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, "no front matter block (first line must be three dashes)"
    data = {}
    for i, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            return data, None
        if not line.strip():
            continue
        m = KEY_LINE.match(line)
        if not m:
            return data, "line %d is not 'key: value': %s" % (i, line[:40])
        data[m.group(1)] = parse_value(m.group(2))
    return data, "front matter block is not closed (missing closing three dashes)"


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def write_file(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def list_pages(project):
    base = os.path.join(project, "pages")
    if not os.path.isdir(base):
        return []
    return sorted(d for d in os.listdir(base)
                  if os.path.isdir(os.path.join(base, d)) and not d.startswith("."))


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_profile(project, page, raw=False):
    """Read the page profile. The page brief wins for the first buyer and the buttons, unless raw=True."""
    path = os.path.join(project, "pages", page, "profile.json")
    if not os.path.isfile(path):
        return None
    try:
        prof = load_json(path)
    except ValueError:
        return None
    if raw or not isinstance(prof, dict):
        return prof
    import brief as brief_mod
    b, err = brief_mod.load(project, page)
    if b is not None and not err and not brief_mod.problems(b, page, prof):
        return brief_mod.apply(prof, b)
    return prof


def note_files(project, page, folder):
    d = os.path.join(project, "pages", page, folder)
    if not os.path.isdir(d):
        return []
    return sorted(os.path.join(d, n) for n in os.listdir(d)
                  if n.endswith(".md") and n.lower() not in ("readme.md", "index.md"))


def load_notes(project, page, folder):
    """Return list of (path, front_matter_dict, error)."""
    out = []
    for p in note_files(project, page, folder):
        fm, err = parse_front_matter(read_text(p))
        out.append((p, fm, err))
    return out


def register_ids(project):
    path = os.path.join(project, "library", "library-register.csv")
    if not os.path.isfile(path):
        return None
    with open(path, newline="", encoding="utf-8") as f:
        return set((r.get("id") or "").strip() for r in csv.DictReader(f))


def rel(project, path):
    return os.path.relpath(path, project)


def make_temp_project():
    """A fresh temporary project folder with the library register and pages folder."""
    root = tempfile.mkdtemp(prefix="agent-selftest-")
    os.makedirs(os.path.join(root, "pages"))
    os.makedirs(os.path.join(root, "library"))
    write_file(os.path.join(root, "library", "library-register.csv"),
               "id,title\nLIB-001,one\nLIB-002,two\n")
    return root


def drop_temp(root):
    shutil.rmtree(root, ignore_errors=True)


class SelfTest(object):
    """Collect planted-input results. expect(True, ...) means the check behaved."""

    def __init__(self, name):
        self.name = name
        self.fails = 0
        self.total = 0

    def expect(self, ok, message):
        self.total += 1
        if ok:
            print("SELFTEST PASS: " + message)
        else:
            self.fails += 1
            print("SELFTEST FAIL: " + message)

    def done(self):
        print("%s selftest: %d of %d cases passed" % (self.name, self.total - self.fails, self.total))
        return 1 if self.fails else 0


def evidence_text(**over):
    fm = {"id": "EV-001", "title": "A fact", "type": "evidence", "tier": "2", "owner": "claude",
          "updated": "2026-11-13", "source": "vendor page", "data_as_of": "2026-11-13",
          "status": "current", "export": "yes", "review_by": "2026-12-13", "label": "VENDOR",
          "lib_ids": "[LIB-001]", "quote": "\"exact words\"", "location": "section 2",
          "supports": "the page can say X", "does_not_show": "any test result"}
    fm.update(over)
    return "---\n" + "\n".join("%s: %s" % (k, v) for k, v in fm.items() if v is not None) + "\n---\nBody.\n"


def claim_text(**over):
    fm = {"id": "CL-001", "title": "A claim", "type": "claim", "tier": "2", "owner": "claude",
          "updated": "2026-11-13", "status": "draft", "label": "VENDOR",
          "text": "\"The service runs in India.\"", "evidence_ids": "[EV-001]", "section": "hero"}
    fm.update(over)
    return "---\n" + "\n".join("%s: %s" % (k, v) for k, v in fm.items() if v is not None) + "\n---\nBody.\n"

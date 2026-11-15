#!/usr/bin/env python3
"""Load the skill for one step of flow.json. Standard library only.

Use:  python3 -I agent/skill_loader.py <step id> [--scale <scale skill>]   (prints a short summary)
Self test:  python3 -I agent/skill_loader.py --selftest

For a step the loader:
  1. reads flow.json and finds the step and its named skill,
  2. loads skills/<name>/SKILL.md and each reference file that the step's input_pack names,
  3. checks each file against its max_chars and the total against the step's max_total_chars,
  4. returns the text and a sha256 checksum.

Stops (it raises an error):
  SkillError  the step, flow.json or SKILL.md is missing.
  OverCap     a skill file is over its cap, or the skill is over the step total. Never cut an input without saying so.
A skill that is a stub (status: STUB) or that lacks a required reference file is not an error.
The result says so, and the caller uses its fallback prompt and logs it.
"""
import hashlib
import json
import os
import re
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CORE_CAP = 14000
DEFAULT_REF_CAP = 15000
LOG_HEADER = ["step", "skill", "checksum", "input_chars", "cap", "status"]


class SkillError(Exception):
    """The step, the flow file or the skill is missing."""


class OverCap(SkillError):
    """An input is over its cap. The run stops and names the input."""


def load_flow(project=None):
    path = os.path.join(project or PROJECT, "flow.json")
    if not os.path.isfile(path):
        raise SkillError("flow.json is missing in %s." % (project or PROJECT))
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_step(flow, step_id):
    for s in flow.get("steps", []):
        if s.get("id") == str(step_id):
            return s
    raise SkillError("Step '%s' is not in flow.json." % step_id)


def is_stub_text(text):
    head = "\n".join(text.splitlines()[:12])
    return re.search(r"^status:\s*STUB\s*$", head, re.M) is not None


def _skill_entries(step, skill, scale_skill):
    """The input_pack entries that point into skills/. Returns a list of (name, path, max_chars, required)."""
    out = []
    for e in step.get("input_pack", []):
        p = e.get("path", "")
        if not p.startswith("skills/"):
            continue
        if "{scale_skill}" in p:
            if not scale_skill:
                continue
            p = p.replace("{scale_skill}", scale_skill)
        if "{" in p:
            continue
        out.append((e.get("name"), p, int(e.get("max_chars") or DEFAULT_REF_CAP), bool(e.get("required"))))
    core = "skills/%s/SKILL.md" % skill
    if not any(p == core for _, p, _, _ in out):
        out.insert(0, ("skill_core", core, DEFAULT_CORE_CAP, True))
    return out


def load(project, step_id, data_chars=0, scale_skill=None, strict_data=False):
    """Return a dict: step, skill, text, checksum, files, skill_chars, input_chars, cap, status, fallback, missing.

    data_chars is the size of the data the caller adds to the prompt. It is counted in input_chars.
    A skill file over its own cap, or a skill over the step total, raises OverCap.
    Data over the step total sets status "over_cap_data". With strict_data=True it raises OverCap instead.
    """
    flow = load_flow(project)
    step = find_step(flow, step_id)
    skill = step.get("skill")
    if not skill:
        raise SkillError("Step '%s' names no skill in flow.json." % step_id)
    cap = int(step.get("max_total_chars") or 0)
    core_path = os.path.join(project, "skills", skill, "SKILL.md")
    if not os.path.isfile(core_path):
        raise SkillError("Skill '%s' for step '%s' is missing: %s." % (skill, step_id, os.path.relpath(core_path, project)))
    files, missing, parts = [], [], []
    for name, rel, max_chars, required in _skill_entries(step, skill, scale_skill):
        full = os.path.join(project, rel)
        if not os.path.isfile(full):
            if rel.endswith("/SKILL.md"):
                raise SkillError("Skill file '%s' for step '%s' is missing." % (rel, step_id))
            if required:
                missing.append(rel)
            continue
        with open(full, encoding="utf-8", errors="replace") as f:
            text = f.read()
        if len(text) > max_chars:
            raise OverCap("over_cap: stop. Input '%s' (%s) holds %d characters. Its cap is %d. Step %s." % (name, rel, len(text), max_chars, step_id))
        if required and not rel.endswith("/SKILL.md") and not text.strip():
            missing.append(rel + " (empty)")
            continue
        files.append((rel, text))
        parts.append("## SKILL FILE: %s\n\n%s" % (rel, text.strip()))
    skill_chars = sum(len(t) for _, t in files)
    if cap and skill_chars > cap:
        raise OverCap("over_cap: stop. The skill files for step %s hold %d characters. The step cap is %d." % (step_id, skill_chars, cap))
    core_text = files[0][1] if files else ""
    stub = is_stub_text(core_text)
    h = hashlib.sha256()
    for rel, text in files:
        h.update(rel.encode("utf-8") + b"\n" + text.encode("utf-8"))
    input_chars = skill_chars + int(data_chars or 0)
    status = "ok"
    if stub:
        status = "stub_fallback"
    elif missing:
        status = "refs_missing_fallback"
    if cap and input_chars > cap:
        if strict_data:
            raise OverCap("over_cap: stop. Step %s input holds %d characters (skill %d, data %d). The cap is %d." % (step_id, input_chars, skill_chars, data_chars, cap))
        status = "over_cap_data" if status == "ok" else status + "+over_cap_data"
    return {"step": str(step_id), "skill": skill, "text": "\n\n".join(parts), "checksum": h.hexdigest(), "files": [r for r, _ in files],
            "skill_chars": skill_chars, "input_chars": input_chars, "cap": cap, "status": status,
            "fallback": stub or bool(missing), "stub": stub, "missing": missing}


def row(res, step_label=None):
    """One run-log row as a list that matches LOG_HEADER."""
    return [step_label or res["step"], res["skill"], res["checksum"][:16], res["input_chars"], res["cap"], res["status"]]


def build_system(project, step_id, task_prompt, data_chars=0, label=None, scale_skill=None):
    """Return (system_text, log_row). The system prompt carries the step's skill.

    Real skill: the skill text, then the task prompt that fixes the output format.
    Stub skill, or a required reference missing: the task prompt alone, and the row says so.
    No flow.json in the project (a test project): the task prompt alone, status no_flow_fallback.
    Raises SkillError or OverCap for a missing SKILL.md or an over-cap skill file.
    """
    try:
        res = load(project, step_id, data_chars=data_chars, scale_skill=scale_skill)
    except SkillError as e:
        if str(e).startswith("flow.json is missing"):
            return task_prompt, [label or str(step_id), "", "", int(data_chars or 0), 0, "no_flow_fallback"]
        raise
    if res["fallback"]:
        return task_prompt, row(res, label)
    system = ("SKILL FOR THIS STEP (method; follow it)\n\n" + res["text"] + "\n\n---\nTASK AND OUTPUT FORMAT FOR THIS CALL\n\n" + task_prompt)
    return system, row(res, label)


def selftest():
    import shutil
    import tempfile
    ok = [True]

    def expect(c, msg):
        print(("SELFTEST PASS: " if c else "SELFTEST FAIL: ") + msg)
        ok[0] = ok[0] and bool(c)
    root = tempfile.mkdtemp(prefix="loader-selftest-")
    try:
        def w(rel, text):
            p = os.path.join(root, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
        flow = {"steps": [
            {"id": "1", "skill": "good", "max_total_chars": 500, "input_pack": [
                {"name": "skill_core", "path": "skills/good/SKILL.md", "max_chars": 200, "required": True},
                {"name": "ref", "path": "skills/good/references/examples.md", "max_chars": 100, "required": False},
                {"name": "data", "path": "pages/{page}/x.json", "max_chars": 10, "required": True}]},
            {"id": "2", "skill": "stubby", "max_total_chars": 500, "input_pack": []},
            {"id": "3", "skill": "absent", "max_total_chars": 500, "input_pack": []},
            {"id": "4", "skill": "big", "max_total_chars": 500, "input_pack": [{"name": "skill_core", "path": "skills/big/SKILL.md", "max_chars": 50, "required": True}]},
            {"id": "5", "skill": "needsref", "max_total_chars": 500, "input_pack": [
                {"name": "ref", "path": "skills/needsref/references/rubric.md", "max_chars": 100, "required": True}]},
            {"id": "6", "skill": None, "max_total_chars": 0, "input_pack": []}]}
        w("flow.json", json.dumps(flow))
        w("skills/good/SKILL.md", "---\nname: good\n---\nMethod text.\n")
        w("skills/good/references/examples.md", "Example.\n")
        w("skills/stubby/SKILL.md", "---\nname: stubby\nstatus: STUB\n---\nSTUB\n")
        w("skills/big/SKILL.md", "x" * 60)
        w("skills/needsref/SKILL.md", "---\nname: needsref\n---\nBody\n")
        a = load(root, "1", data_chars=100)
        b = load(root, "1", data_chars=100)
        expect(a["status"] == "ok" and "Method text." in a["text"] and "Example." in a["text"], "a real skill loads its core and its named reference")
        expect(a["checksum"] == b["checksum"] and len(a["checksum"]) == 64, "the checksum is a stable sha256")
        expect(load(root, "1", data_chars=900)["status"] == "over_cap_data", "data over the step cap is logged as over_cap_data")
        try:
            load(root, "1", data_chars=900, strict_data=True)
            expect(False, "strict data over the cap raises")
        except OverCap:
            expect(True, "strict data over the cap raises")
        expect(load(root, "2")["status"] == "stub_fallback", "a stub skill is reported as stub_fallback")
        expect(load(root, "5")["status"] == "refs_missing_fallback", "a missing required reference is reported")
        for sid, cls, what in (("3", SkillError, "a missing skill"), ("4", OverCap, "a skill file over its cap"),
                               ("6", SkillError, "a step with no skill"), ("99", SkillError, "an unknown step")):
            try:
                load(root, sid)
                expect(False, "%s raises" % what)
            except cls:
                expect(True, "%s raises" % what)
        sysm, r = build_system(root, "1", "TASK")
        expect("Method text." in sysm and sysm.rstrip().endswith("TASK") and r[5] == "ok", "build_system carries the skill, then the task prompt")
        sysm, r = build_system(root, "2", "TASK")
        expect(sysm == "TASK" and r[5] == "stub_fallback", "build_system uses only the task prompt for a stub")
        empty = tempfile.mkdtemp(prefix="loader-selftest-")
        try:
            sysm, r = build_system(empty, "1", "TASK")
            expect(sysm == "TASK" and r[5] == "no_flow_fallback", "a project with no flow.json falls back and says so")
        finally:
            shutil.rmtree(empty, ignore_errors=True)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("skill_loader selftest: %s" % ("all passed" if ok[0] else "FAILED"))
    return 0 if ok[0] else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if not argv:
        print("Use: python3 -I agent/skill_loader.py <step id> [--scale <scale skill>]")
        return 2
    scale = argv[argv.index("--scale") + 1] if "--scale" in argv and argv.index("--scale") + 1 < len(argv) else None
    try:
        r = load(PROJECT, argv[0], scale_skill=scale)
    except SkillError as e:
        print("STOP: %s" % e)
        return 1
    print("step %s, skill %s, status %s, skill chars %d, cap %d, checksum %s" % (r["step"], r["skill"], r["status"], r["skill_chars"], r["cap"], r["checksum"][:16]))
    print("files: %s" % ", ".join(r["files"]))
    if r["missing"]:
        print("missing required references: %s" % ", ".join(r["missing"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

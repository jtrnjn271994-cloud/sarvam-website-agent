#!/usr/bin/env python3
"""Load the skills for one step from skills/step-skills.json, in order. Standard library only.
Returns (text, used) where used = [{"skill", "sha256", "chars"}]. Over-cap skills stop the run (never cut silently)."""
import hashlib
import json
import os

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SkillError(Exception):
    pass


def load(step):
    cfg = json.load(open(os.path.join(PROJECT, "skills", "step-skills.json"), encoding="utf-8"))
    names = cfg["steps"].get(step)
    if names is None:
        raise SkillError("no skills listed for step '%s'" % step)
    parts, used = [], []
    for n in names:
        path = os.path.join(PROJECT, "skills", n, "SKILL.md")
        if not os.path.isfile(path):
            raise SkillError("skill file missing: skills/%s/SKILL.md" % n)
        t = open(path, encoding="utf-8").read()
        if len(t) > cfg["cap_chars_per_skill"]:
            raise SkillError("skill %s is %d chars, over the cap of %d" % (n, len(t), cfg["cap_chars_per_skill"]))
        parts.append("=== SKILL: %s ===\n%s" % (n, t))
        used.append({"skill": n, "sha256": hashlib.sha256(t.encode("utf-8")).hexdigest()[:16], "chars": len(t)})
    return "\n\n".join(parts), used


if __name__ == "__main__":
    for s in json.load(open(os.path.join(PROJECT, "skills", "step-skills.json")))["steps"]:
        txt, used = load(s)
        print("%-18s %6d chars  %s" % (s, len(txt), ", ".join(u["skill"] for u in used)))

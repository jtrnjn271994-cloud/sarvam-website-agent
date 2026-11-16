#!/usr/bin/env python3
"""The flow diagram of ONE run, in the same steps and words as the architecture (docs/architecture.html, section 1).

It reads only the run's own files, so it works for every run: old or new, local or website, finished or stopped.
Steps the run reached are drawn solid; steps not reached yet are grey and dashed. The template and every
scenario it must handle are in .claude/skills/run-architecture/SKILL.md.

Run:
  python3 agent/run_flow.py --page voice-agents --run probe3-YYYYMMDD-HHMMSS   # writes RUN-FLOW.md and RUN-FLOW.html in the run folder
  python3 agent/run_flow.py --all                                             # every run of every page
  python3 agent/run_flow.py --selftest                                        # every scenario in the skill file
The run, the edit and the sandbox scripts call write() at their end, so each run keeps its own diagram up to date.
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GROUP_WORDS = {"passed": "passed", "held": "held", "failed_gate2": "failed Gate 2", "failed_gate1": "failed Gate 1"}
HEAD = "flowchart TD\n    classDef todo fill:#f4f5f7,stroke:#aab,stroke-dasharray:4 3,color:#778\n    classDef gate stroke-width:3px\n    classDef stop fill:#FDE2E2,stroke:#D14B4B,color:#5a1010\n    classDef jev fill:#EADFFF,stroke:#7A4DD8\n    classDef j2 fill:#D9F3EC,stroke:#1E9E80\n"


def esc(t, n=90):
    t = re.sub(r"\s+", " ", re.sub(r'["<>{}\[\]|#;]', " ", str(t if t is not None else ""))).strip()
    return t[:n - 1] + "…" if n and len(t) > n else t


def _json(path, default=None):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def gather(page, run, root=PROJECT):
    """Everything the diagram needs, from files only. Missing files give empty values, never an error."""
    import shortlist
    rd = os.path.join(root, "pages", page, "runs", run)
    probe = _json(os.path.join(rd, "probe3.json"), {}) or {}
    reg = {p["slug"]: p for p in (_json(os.path.join(root, "pages", "registry.json"), {}) or {}).get("pages", [])}
    caps = sorted(glob.glob(os.path.join(root, "pages", page, "capture", "*-live", "hero.json")))
    hero = _json(caps[-1], {}) if caps else {}
    try:
        sl = shortlist.classify(probe) if probe.get("variants") else []
    except Exception:   # an odd old run must not break the diagram
        sl = []
    try:
        ap = shortlist.current_approval(rd)
    except Exception:
        ap = None
    return {"page_name": (reg.get(page) or {}).get("name") or page, "probe": probe, "shortlist": sl, "approval": ap,
            "sandbox": _json(os.path.join(rd, "sandbox", "sandbox-results.json")), "hero": hero,
            "files": sorted(os.listdir(rd)) if os.path.isdir(rd) else []}


def mermaid(info):
    """The diagram text. Pure function of gather()'s output, so the self-test can feed it any scenario."""
    p, sl, C, sb, hero = info["probe"], info["shortlist"], info["approval"], info["sandbox"], info["hero"] or {}
    a = p.get("audit") or {}
    v = a.get("verdict") or {}
    web = p.get("screenshots") == "not taken (website run)"
    rounds = p.get("gate1_rounds") or []
    g1 = rounds[-1] if rounds else {}
    edits = p.get("edits") or []
    first = [x for x in p.get("variants") or [] if not x.get("edited_from")]
    nogap = bool(p.get("audit")) and not (a.get("gaps") or [])
    L, E = [], []

    def node(i, lines, done, shape=""):
        t = "<br/>".join(esc(x) for x in lines if x is not None)
        body = '{"%s"}' % t if shape == "d" else '["%s"]' % t
        cls = ":::todo" if not done else {"g": ":::gate", "s": ":::stop", "jev": ":::jev", "j2": ":::j2"}.get(shape, "")
        L.append("    %s%s%s" % (i, body, cls))

    pq = p.get("page_questions") or {}
    node("S", ["1 Start (person)", "page: " + info["page_name"], "buyer: " + ((p.get("persona") or {}).get("buyer") or "not recorded"),
               "goal: " + ((p.get("goal") or {}).get("label") or "not recorded"), "started on the website" if web else "started in the local console"], True)
    node("C", ["2 Hero captured " + str(hero.get("captured_at") or "")[:10], "H1: " + (hero.get("h1") or ""), "the audit, writer and gates read this saved copy"], bool(hero))
    node("P", ["3 Page set up and approved", "positioning and claims approved by the owner",
               "buyer checklist approved: A7 and A8 asked" if pq.get("approved") else "buyer checklist not approved: A7 and A8 skipped"], bool(p))
    passed = [k for k, x in v.items() if "pass" in str(x)]
    qv = "questions v2" if p.get("questions_version") == 2 else "questions v1"
    node("A", ["4 AUDIT the saved hero (Jev only)", qv, "gaps: " + (", ".join(a.get("gaps") or []) or "none"), "already answered: " + (", ".join(passed) or "none")], bool(p.get("audit")))
    node("D", ["Gap found?"], bool(p.get("audit")), "d")
    if nogap:
        node("N", ["Stop: no gap", "nothing is written"], True, "s")
        E += ["S --> C --> P --> A --> D", "D -- no --> N"]
        return HEAD + "\n".join(L) + "\n" + "\n".join("    " + x for x in E) + "\n"
    dz = (p.get("dossier") or {}).get("text") or ""
    node("H", ["5 GAP DOSSIER", ("%d words; numbers, ids and quotes checked by code" % len(dz.split())) if dz else "not written"], bool(dz))
    node("T", ["6 TEST PLAN", "action: one click on the main button", "goal link: " + ((p.get("goal") or {}).get("kind") or "")], bool(dz))
    node("W", ["7 WRITER (Opus): %d variants" % len(first)] + ["%s: %s" % (x.get("name"), x.get("h1")) for x in first], bool(first))
    node("G1", ["Gate 1: RULES (no model)", "%d round(s)" % len(rounds)] + ["%s: %s" % (k, ("%d problem(s)" % len(pr)) if pr else "ok") for k, pr in g1.items()], bool(rounds), "g")
    scored = [x for x in sl if x["group"] != "failed_gate1"]
    reached2 = bool(p.get("gate2"))
    node("GJ", ["Jev", "honesty G1-G3, then A1-A8 on the variant"], reached2, "jev")
    node("GK", ["Judge 2: OpenAI gpt-6-luna-decisions", "honesty G1-G3, then A1-A8 on the variant"], reached2, "j2")
    node("G2", ["both say better?"] + ["%s: %s" % (x["name"], ("gain " + " / ".join("%+.2f" % g for g in x["gains"].values())) if x.get("gains") else "not scored") for x in scored],
         reached2, "g")
    if not scored and rounds:
        node("X", ["Every variant failed Gate 1", "edit one and check it again (step 9)"], True, "s")
    node("SL", ["Shortlist"] + ["%s: %s%s" % (x["name"], GROUP_WORDS.get(x["group"], x["group"]), " (near miss)" if x.get("near_miss") else "") for x in sl], bool(sl))
    pairs = len([f for f in info["files"] if f.startswith("pair-") and f.endswith(".png")])
    node("PX", ["8 Apply the words, check the button link", "website run: no screenshots, the text and its hash are shown" if web else "%d PNG pair(s) made" % pairs], bool(sl))
    node("AP", ["9 HUMAN approval", ("approved: variant %s%s" % (C["variant"], " (against Gate 2, reason given)" if C.get("override") else "")) if C else "waiting for a person"], bool(C), "g")
    if edits:
        node("ED", ["Edit and re-check"] + ["%s from %s (%s): %s" % (e.get("name"), e.get("from"), "writer rewrite" if e.get("kind") == "note" else "person's edit",
                                                                     "failed Gate 1" if e.get("gate1_problems") else "checked by both gates") for e in edits], True)
    if sb and sb.get("plan"):
        pl, sim, br = sb["plan"], sb.get("simulated") or {}, sb.get("browser") or {}
        name = {"enough": "Test 1", "too_few": "Test 2", "A/A check": "Test 3 (A/A)"}
        node("SP", ["10 SANDBOX PLAN", "%d visitor groups, lift %.1f%%, effective %.1f%%" % (len(pl.get("segments") or []), 100 * pl.get("declared_lift", 0), 100 * pl.get("effective_lift", 0))], True)
        node("SB", ["Simulate and check"] + ["%s: %s" % (name.get(k, k), r.get("result")) for k, r in sim.items()] +
             ["%s: baseline %s/%s, variant %s/%s" % ("page check" if "static" in str(br.get("mode", "")) else "browser sessions", (br.get("passed") or {}).get("baseline"),
                                                    br.get("sessions_per_arm"), (br.get("passed") or {}).get("variant"), br.get("sessions_per_arm"))], True)
        need = pl.get("visitors_needed_for_effective_lift")
        node("FD", ["11 FINDINGS (SYNTHETIC)", ("a real test needs {:,} visitors per arm".format(need)) if need else "no lift to detect", "NOT rolled out"], True)
    elif sb:
        node("SP", ["10 SANDBOX", "typed scenarios (older run)"], True)
        node("SB", ["Simulate and check"], True)
        node("FD", ["11 FINDINGS (SYNTHETIC)", "NOT rolled out"], True)
    else:
        node("SP", ["10 SANDBOX PLAN", "after a variant is approved"], False)
        node("SB", ["Simulate and check", "not run yet"], False)
        node("FD", ["11 FINDINGS", "not written yet"], False)
    node("DOC", ["12 Submission and docs", "README, architecture, Jev note"], True)
    E += ["S --> C --> P --> A --> D", "D -- yes --> H --> T --> W --> G1", "G1 -- fail, max 2 rounds --> W", "G1 -- pass --> GJ --> G2", "G1 -- pass --> GK --> G2", "G2 --> SL"]
    if not scored and rounds:
        E.append("G1 -- every variant failed --> X --> SL")
    E += ["SL --> PX --> AP"]
    if edits:
        E += ["AP -- edit --> ED", "ED --> G1"]
    E += ["AP -- approve --> SP --> SB --> FD --> DOC"]
    return HEAD + "\n".join(L) + "\n" + "\n".join("    " + x for x in E) + "\n"


HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Run flow</title><style>body{font-family:system-ui,sans-serif;margin:24px auto;max-width:1100px;padding:0 16px;color:#1a1a2e}
.mermaid{overflow-x:auto;border:1px solid #e3e6ec;border-radius:10px;padding:14px}</style></head><body>
<h1>%s: this run, step by step</h1><p>Run %s. Same steps as the architecture. Grey dashed = not reached yet.</p>
<pre class="mermaid">%s</pre><script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<script>mermaid.initialize({startOnLoad:true,securityLevel:"strict"});</script></body></html>
"""


def write(page, run, root=PROJECT):
    """Write RUN-FLOW.md and RUN-FLOW.html into the run folder. Never raises: a diagram must not stop a run."""
    try:
        info = gather(page, run, root)
        mm = mermaid(info)
        rd = os.path.join(root, "pages", page, "runs", run)
        open(os.path.join(rd, "RUN-FLOW.md"), "w", encoding="utf-8").write(
            "# %s: run %s, step by step\n\nSame steps as docs/architecture.html. Grey dashed = not reached yet.\n\n```mermaid\n%s```\n" % (info["page_name"], run, mm))
        open(os.path.join(rd, "RUN-FLOW.html"), "w", encoding="utf-8").write(HTML % (esc(info["page_name"]), esc(run), mm))
        return mm
    except Exception as e:
        print("run flow diagram not written (%s)" % e)
        return None


# ---------- self-test: every scenario in the skill file ----------

def _variant(n, h1="Headline"):
    return {"name": n, "h1": h1, "subline": "Sub.", "cta": "Go", "cta_destination": "docs", "map": []}


def _judge(better):
    return {"better": better, "hard_fail": False, "fragments": [], "G3_verdict": "pass", "delta": {"A1": 0.2 if better else 0.02}, "targeted": ["A1"], "held_out": []}


def scenarios():
    base = {"persona": {"buyer": "Buyer"}, "goal": {"label": "Goal", "kind": "docs"}, "audit": {"verdict": {"A1": "fail", "A7-x": "pass"}, "gaps": ["A1"]},
            "dossier": {"text": "word " * 200}, "page_questions": {"approved": True}, "questions_version": 2}
    S = {}
    S["no gap"] = dict(base, audit={"verdict": {"A1": "pass"}, "gaps": []}, dossier=None)
    S["all failed Gate 1"] = dict(base, variants=[_variant("A"), _variant("B")], gate1_rounds=[{"A": ["x"], "B": ["y"]}, {"A": ["x"], "B": ["y"]}], gate2={})
    S["near miss only"] = dict(base, variants=[_variant("A")], gate1_rounds=[{"A": []}], gate2={"A": {"judge1": _judge(False), "judge2": _judge(False)}})
    S["passed, waiting"] = dict(base, variants=[_variant("A")], gate1_rounds=[{"A": []}], gate2={"A": {"judge1": _judge(True), "judge2": _judge(True)}})
    S["edited"] = dict(S["all failed Gate 1"], variants=[_variant("A"), _variant("B"), dict(_variant("A-edit1"), edited_from="A")],
                       gate1_rounds=[{"A": ["x"], "B": ["y"], "A-edit1": []}], gate2={"A-edit1": {"judge1": _judge(True), "judge2": _judge(False)}},
                       edits=[{"name": "A-edit1", "from": "A", "kind": "note", "gate1_problems": []}])
    S["website run"] = dict(S["passed, waiting"], screenshots="not taken (website run)")
    S["stopped early"] = dict(base, dossier=None)
    S["questions v1 (old run)"] = {k: v for k, v in S["passed, waiting"].items() if k != "questions_version"}
    S["empty folder"] = {}
    return S


def selftest():
    import shortlist
    ok = True
    for name, probe in scenarios().items():
        sl = shortlist.classify(probe) if probe.get("variants") else []
        for ap, sb in ((None, None), ({"variant": "A", "override": True}, {"plan": {"segments": [1, 2], "declared_lift": 0.05, "effective_lift": 0.02, "visitors_needed_for_effective_lift": 50000},
                                                                         "simulated": {"enough": {"result": "clear"}, "A/A check": {"result": "inconclusive"}},
                                                                         "browser": {"mode": "static HTML check", "passed": {"baseline": 1, "variant": 1}, "sessions_per_arm": 1}})):
            try:
                mm = mermaid({"page_name": "Page \"X\" [test]", "probe": probe, "shortlist": sl, "approval": ap, "sandbox": sb, "hero": {}, "files": []})
                bad = [l for l in mm.split("\n")[4:] if l.strip() and l.count('"') % 2]
                need = ["S", "A", "D"] + (["N"] if name == "no gap" else ["AP", "DOC"])
                miss = [n for n in need if not re.search(r"^\s+%s[\[{]" % n, mm, re.M)]
                split = name == "no gap" or (all(re.search(r"^\s+%s[\[{]" % n, mm, re.M) for n in ("GJ", "GK", "G2")) and "GJ --> G2" in mm and "GK --> G2" in mm and "G2 --> SL" in mm)
                qv = ("questions v2" if probe.get("questions_version") == 2 else "questions v1") in mm
                ok_one = not bad and not miss and split and qv and (name != "all failed Gate 1" or " X[" in mm) and (name != "edited" or "AP -- edit --> ED" in mm)
            except Exception as e:
                ok_one, bad, miss = False, [str(e)], []
            ok &= ok_one
            print("%s %-18s %-12s %s" % ("PASS" if ok_one else "FAIL", name, "approved" if ap else "not approved", (bad or miss or "")))
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--page")
    ap.add_argument("--run")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if a.all:
        n = 0
        for rd in sorted(glob.glob(os.path.join(PROJECT, "pages", "*", "runs", "probe3-*"))):
            if write(rd.split(os.sep)[-3], os.path.basename(rd)):
                n += 1
        print("wrote the flow diagram for %d runs" % n)
    elif a.page and a.run:
        print(write(a.page, a.run) or "failed")
    else:
        sys.exit("give --page and --run, or --all, or --selftest")

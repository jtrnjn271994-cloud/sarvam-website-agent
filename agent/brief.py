#!/usr/bin/env python3
"""Read and check pages/<page>/brief.json (step 0). A person writes it. No code fills a field.

Run from anywhere:
  python3 -I agent/brief.py --page <slug>      shows what the brief still needs
Self test:
  python3 -I agent/brief.py --selftest

The brief holds the start answers in flow v2 order: goal, page_url, scope ("page" or "section:<name>"),
first_buyer, vertical, main_cta, offer_after_click, test_type ("message" or "design"), open_conflicts. agent/start.py asks them
and writes the file after the person types "yes".
The run stops before the bets step when the brief is missing, when goal, page_url, scope or test_type is empty or wrong,
when first_buyer or main_cta is empty, when offer_after_click is empty, or when open_conflicts is not empty. The brief wins over the page
profile for the first buyer and the main button. Standard library only.
"""
import json
import os
import re
import sys

CHECKLIST = re.compile(r"^BR-[0-9]+$")
TEST_TYPES = ("message", "design")


def scope_of(brief):
    """Return ('page', None), ('section', name) or (None, None) when the brief scope is missing or wrong."""
    sc = _text((brief or {}).get("scope"))
    if sc == "page":
        return "page", None
    if sc.startswith("section:") and sc[len("section:"):].strip():
        return "section", sc[len("section:"):].strip()
    return None, None


def path_of(project, page):
    return os.path.join(project, "pages", page, "brief.json")


def load(project, page):
    """Return (brief, error). brief is None when the file is missing. error is a plain sentence or None."""
    p = path_of(project, page)
    if not os.path.isfile(p):
        return None, None
    try:
        with open(p, encoding="utf-8") as f:
            obj = json.load(f)
    except (OSError, ValueError):
        return None, "pages/%s/brief.json is not valid JSON." % page
    if not isinstance(obj, dict):
        return None, "pages/%s/brief.json must hold one JSON object." % page
    return obj, None


def _text(v):
    return v.strip() if isinstance(v, str) else ""


def first_buyer_of(brief):
    """Return (role, checklist) as plain strings. Empty strings when the brief gives none."""
    fb = (brief or {}).get("first_buyer")
    if isinstance(fb, dict):
        return _text(fb.get("role")) or _text(fb.get("text")), _text(fb.get("checklist"))
    return _text(fb), ""


def source_of(brief):
    """'shortcut' (a profile role with its checklist id), 'typed' (a persona the person typed) or '' (an older brief)."""
    fb = (brief or {}).get("first_buyer")
    return _text(fb.get("source")) if isinstance(fb, dict) else ""


def problems(brief, page="<page>", profile=None, pending_ok=False):
    """Return a list of plain sentences. Each names what the person must write. An empty list means the run may go on.
    pending_ok: a typed persona may have no checklist id yet (step 3c drafts one). The run brief never gets this."""
    where = "pages/%s/brief.json" % page
    if brief is None:
        return ["%s is missing. A person must write it (template: agent/templates/page/brief.json). "
                "It needs goal, page_url, scope, first_buyer (one role and one checklist id), main_cta (one button label), "
                "offer_after_click, test_type and open_conflicts. Run: python3 -I agent/start.py --page %s" % (where, page)]
    out = []
    if not _text(brief.get("goal")):
        out.append("%s: goal is empty. Write what the page test should achieve (flow v2 step 1). Run: python3 -I agent/start.py --page %s" % (where, page))
    url = _text(brief.get("page_url"))
    if not url:
        out.append("%s: page_url is empty. Write the live page address (flow v2 step 1)." % where)
    elif not re.match(r"^https?://\S+$", url):
        out.append("%s: page_url '%s' is not a web address that starts with http:// or https://." % (where, url))
    if not _text(brief.get("scope")):
        out.append("%s: scope is empty. Write 'page' or 'section:<name>' (flow v2 step 2). Run: python3 -I agent/start.py --page %s" % (where, page))
    elif scope_of(brief)[0] is None:
        out.append("%s: scope '%s' is not 'page' or 'section:<name>'." % (where, _text(brief.get("scope"))))
    if not _text(brief.get("test_type")):
        out.append("%s: test_type is empty. Write 'message' or 'design' (flow v2 step 5). Run: python3 -I agent/start.py --page %s" % (where, page))
    elif _text(brief.get("test_type")) not in TEST_TYPES:
        out.append("%s: test_type '%s' is not 'message' or 'design'." % (where, _text(brief.get("test_type"))))
    role, checklist = first_buyer_of(brief)
    if not role:
        out.append("%s: first_buyer.role is empty. Write one buyer role." % where)
    elif re.search(r"\s(and|or)\s|[;/]", role):
        out.append("%s: first_buyer.role names more than one role ('%s'). Write one role." % (where, role))
    typed = source_of(brief) == "typed"
    if source_of(brief) in ("typed", "shortcut"):
        for k in ("decides", "must_see"):
            if not _text((brief.get("first_buyer") or {}).get(k)):
                out.append("%s: first_buyer.%s is empty. Write it in the buyer's own terms." % (where, k))
    if not checklist and typed and pending_ok:
        pass
    elif not checklist:
        out.append("%s: first_buyer.checklist is empty. Write one checklist id, such as BR-001." % where)
    elif not CHECKLIST.match(checklist):
        out.append("%s: first_buyer.checklist '%s' is not one checklist id like BR-001." % (where, checklist))
    elif profile and not typed:
        known = set((profile.get("audience_checklists") or {}).get("primary") or []) | set((profile.get("audience_checklists") or {}).get("secondary") or [])
        if known and checklist not in known:
            out.append("%s: first_buyer.checklist '%s' is not in the page profile checklists (%s)." % (where, checklist, ", ".join(sorted(known))))
    if not _text(brief.get("vertical")):
        out.append("%s: vertical is empty. Write the one vertical this test is for, in your own words (flow v2 step 3). Run: python3 -I agent/start.py --page %s" % (where, page))
    if not _text(brief.get("main_cta")):
        out.append("%s: main_cta is empty. Write the one button label that both arms use." % where)
    if not _text(brief.get("offer_after_click")):
        out.append("%s: offer_after_click is empty. Write what the buyer gets after the click, or 'UNKNOWN: <reason>'." % where)
    oc = brief.get("open_conflicts")
    if not isinstance(oc, list):
        out.append("%s: open_conflicts must be a list. Use [] when no conflict is open." % where)
    elif oc:
        out.append("%s: open_conflicts is not empty (%d). Close each conflict, then empty the list: %s" % (
            where, len(oc), " | ".join(str(x) for x in oc)))
    return out


def apply(profile, brief):
    """Return a copy of the profile where the brief wins for the first buyer and the buttons. Fills nothing that the brief leaves empty."""
    p = dict(profile or {})
    if not brief:
        return p
    role, checklist = first_buyer_of(brief)
    if role and checklist:
        p["primary_buyers"] = [{"role": role, "checklist": checklist}]
        ac = dict(p.get("audience_checklists") or {})
        ac["primary"] = [checklist]
        ac["secondary"] = [c for c in ac.get("secondary") or [] if c != checklist]
        p["audience_checklists"] = ac
        p["secondary_buyers"] = [b for b in p.get("secondary_buyers") or [] if not (isinstance(b, dict) and b.get("checklist") == checklist)]
    if _text(brief.get("main_cta")):
        p["main_cta"] = _text(brief.get("main_cta"))
    if _text(brief.get("second_cta")):
        p["second_cta"] = _text(brief.get("second_cta"))
    p["brief_applied"] = True
    return p


def view(brief):
    """What a model prompt carries from the brief. Short and exact."""
    role, checklist = first_buyer_of(brief)
    fb = {"role": role, "checklist": checklist}
    for k in ("decides", "must_see"):
        if _text(((brief or {}).get("first_buyer") or {}).get(k) if isinstance((brief or {}).get("first_buyer"), dict) else ""):
            fb[k] = _text(brief["first_buyer"][k])
    return {"product": _text((brief or {}).get("product")) or None, "first_buyer": fb, "vertical": _text((brief or {}).get("vertical")) or None, "main_cta": _text((brief or {}).get("main_cta")),
            "second_cta": _text((brief or {}).get("second_cta")) or None,
            "offer_after_click": _text((brief or {}).get("offer_after_click")),
            "scope": _text((brief or {}).get("scope")) or None, "test_type": _text((brief or {}).get("test_type")) or None,
            "rule": "Use main_cta as the main button in every arm. Serve first_buyer first."}


def selftest():
    import tempfile
    import shutil
    ok = []

    def expect(c, msg):
        ok.append(bool(c))
        print("%s  %s" % ("PASS" if c else "FAIL", msg))
    good = {"goal": "More clicks on the main button", "page_url": "https://example.com/p", "scope": "page", "test_type": "message",
            "first_buyer": {"role": "Engineering head", "checklist": "BR-001"}, "vertical": "GCCs and IT services", "main_cta": "Compare on your workload",
            "offer_after_click": "UNKNOWN: no booking flow is documented", "open_conflicts": []}
    prof = {"audience_checklists": {"primary": ["BR-002", "BR-001"], "secondary": ["BR-003"]}, "main_cta": "Old",
            "primary_buyers": [{"role": "Head of GCC", "checklist": "BR-002"}, {"role": "Engineering head", "checklist": "BR-001"}],
            "secondary_buyers": [{"role": "Risk", "checklist": "BR-003"}]}
    expect(problems(good, "p", prof) == [], "a full brief has no problem")
    expect(len(problems(None, "p")) == 1 and "missing" in problems(None, "p")[0], "a missing brief stops the run")
    expect(any("first_buyer.role is empty" in x for x in problems(dict(good, first_buyer={"role": "", "checklist": "BR-001"}), "p")), "an empty first buyer stops the run")
    expect(any("more than one role" in x for x in problems(dict(good, first_buyer={"role": "CTO or CFO", "checklist": "BR-001"}), "p")), "two roles stop the run")
    expect(any("main_cta is empty" in x for x in problems(dict(good, main_cta=" "), "p")), "an empty main_cta stops the run")
    expect(any("vertical is empty" in x for x in problems(dict(good, vertical=""), "p")) and any("vertical is empty" in x for x in problems({k: v for k, v in good.items() if k != "vertical"}, "p")), "an empty or missing vertical stops the run (G21)")
    expect(any("offer_after_click is empty" in x for x in problems(dict(good, offer_after_click=""), "p")), "an empty offer stops the run")
    expect(any("scope is empty" in x for x in problems(dict(good, scope=""), "p")), "an empty scope stops the run")
    expect(any("scope 'chapter'" in x for x in problems(dict(good, scope="chapter"), "p")) and problems(dict(good, scope="section:faq"), "p") == [], "a wrong scope stops the run and section:<name> passes")
    expect(any("test_type is empty" in x for x in problems(dict(good, test_type=""), "p")), "an empty test type stops the run")
    expect(any("test_type 'both'" in x for x in problems(dict(good, test_type="both"), "p")), "a test type other than message or design stops the run")
    expect(any("goal is empty" in x for x in problems(dict(good, goal=""), "p")) and any("page_url is empty" in x for x in problems(dict(good, page_url=""), "p")), "an empty goal or page address stops the run")
    expect(scope_of(good) == ("page", None) and scope_of(dict(good, scope="section:faq")) == ("section", "faq") and scope_of({}) == (None, None), "scope_of reads page and section scopes")
    expect(any("open_conflicts is not empty" in x and "two CTAs" in x for x in problems(dict(good, open_conflicts=["two CTAs"]), "p")), "an open conflict stops the run and is named")
    expect(any("not in the page profile" in x for x in problems(dict(good, first_buyer={"role": "x", "checklist": "BR-009"}), "p", prof)), "a checklist outside the profile stops the run")
    eff = apply(prof, good)
    expect(eff["main_cta"] == "Compare on your workload" and eff["primary_buyers"] == [{"role": "Engineering head", "checklist": "BR-001"}]
           and eff["audience_checklists"]["primary"] == ["BR-001"] and prof["main_cta"] == "Old", "the brief wins and the profile is not changed in place")
    expect(apply(prof, dict(good, main_cta="", first_buyer={"role": "", "checklist": ""}))["main_cta"] == "Old", "an empty brief field fills nothing")
    tmp = tempfile.mkdtemp(prefix="brief-selftest-")
    try:
        os.makedirs(os.path.join(tmp, "pages", "p"))
        expect(load(tmp, "p") == (None, None), "no file loads as None")
        with open(path_of(tmp, "p"), "w", encoding="utf-8") as f:
            f.write("{bad")
        expect(load(tmp, "p")[1] is not None, "a broken file gives an error sentence")
        with open(path_of(tmp, "p"), "w", encoding="utf-8") as f:
            json.dump(good, f)
        expect(load(tmp, "p")[0] == good, "a good file loads")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("---")
    print("%d checks, %d failed" % (len(ok), ok.count(False)))
    return 0 if all(ok) else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import common
    page = argv[argv.index("--page") + 1] if "--page" in argv and argv.index("--page") + 1 < len(argv) else None
    if not page:
        print("Use --page <slug>, or --selftest")
        return 2
    b, err = load(common.PROJECT, page)
    probs = [err] if err else problems(b, page, common.load_profile(common.PROJECT, page, raw=True))
    for p in probs:
        print("NEEDS   %s" % p)
    print("---")
    print("The brief is ready." if not probs else "The brief is not ready. A person must fix %d thing(s)." % len(probs))
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

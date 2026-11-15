#!/usr/bin/env python3
"""SYNTHETIC A/B sandbox. Simulated visitors only. Every output says SYNTHETIC.

Run from anywhere:
  python3 -I agent/sandbox.py --page <slug> --run-id <id>     (reads runs/<id>/sandbox-input.json: one test, or {"tests": [...]})
  python3 -I agent/sandbox.py --demo [--page <slug>]           (the two built-in demo scenarios)
Self test:  python3 -I agent/sandbox.py --selftest

What it does (rules/test-scope-rules.md):
  - One scope: page, section:<name> or action:<cta>. One primary action.
  - It fixes the visitors per arm, the seed and the pass rule BEFORE the run.
  - Each simulated visitor gets an arm and a segment from a stable hash of the seed and the id.
    The same seed gives the same split and the same result. It does not peek or stop early.
  - It reports the rate per arm and a two-proportion z test. Class: clear or inconclusive.
The simulation returns the lift we assumed, plus chance noise. It shows what a test of this size
could detect. It says nothing about real buyers and it proves nothing.
A page-scope test cannot show which section caused the result.
Segments come from profile.json (primary and supporting audiences) and the buyer checklists.
Standard library only.
"""
import hashlib
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import runlib  # noqa: E402

DEMO_FILE = os.path.join(common.AGENT_DIR, "sandbox_demos.json")
LABEL = "SYNTHETIC"
PAGE_LIMIT = ("A whole-page test cannot show which section caused the result. "
              "Run a section test, or a section ablation, to look at one section.")
ALWAYS_LIMITS = ["The visitors are simulated. The result does not predict what real buyers do.",
                 "The lift is an assumption we typed in. The simulation returns it with chance noise. It does not discover it.",
                 "Never write that this proved anything. Write: in this synthetic test."]


def unit(seed, salt, vid):
    """A stable number in [0, 1) from the seed, a salt and the visitor id."""
    digest = hashlib.sha256(("%s|%s|%s" % (seed, salt, vid)).encode("utf-8")).hexdigest()
    return int(digest[:13], 16) / float(16 ** 13)


def parse_scope(scope):
    if scope == "page":
        return "page", None
    for kind in ("section", "action"):
        if scope.startswith(kind + ":") and scope[len(kind) + 1:].strip():
            return kind, scope[len(kind) + 1:].strip()
    raise ValueError("scope must be page, section:<name> or action:<cta>")


def two_prop_test(x1, n1, x2, n2):
    """Two-proportion z test, pooled, two sided. Returns diff, 95% interval, z, p."""
    p1, p2 = x1 / float(n1), x2 / float(n2)
    pool = (x1 + x2) / float(n1 + n2)
    se0 = math.sqrt(pool * (1 - pool) * (1.0 / n1 + 1.0 / n2))
    z = (p2 - p1) / se0 if se0 > 0 else 0.0
    p = math.erfc(abs(z) / math.sqrt(2))
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    diff = p2 - p1
    return {"diff": diff, "ci_low": diff - 1.96 * se, "ci_high": diff + 1.96 * se, "z": z, "p": p,
            "relative": (diff / p1) if p1 > 0 else None}


def build_segments(project, page, cfg):
    """Segments from profile.json audiences. Each supporting audience lists the checklists that match it."""
    prof = common.load_profile(project, page) or {}
    primary = str(prof.get("primary_audience") or "primary audience")
    supporting = [str(s) for s in (prof.get("supporting_audiences") or [])]
    checklists = []
    for _, fm, err in common.load_notes(project, page, os.path.join("buyer-and-wedge", "checklists")):
        if not err and fm.get("id"):
            checklists.append((fm["id"], str(fm.get("title") or "")))

    def words(t):
        return set(w[:5] for w in __import__("re").findall(r"[a-z]{4,}", t.lower()))
    share = float(cfg.get("primary_share", 0.5))
    segs = [{"name": primary, "role": "primary", "weight": share if supporting else 1.0, "sensitivity": 1.0, "checklist_ids": []}]
    for s in supporting:
        ids = [cid for cid, title in checklists if words(s) & words(title)]
        segs.append({"name": s, "role": "supporting", "weight": (1.0 - share) / len(supporting),
                     "sensitivity": float(cfg.get("supporting_sensitivity", 0.5)), "checklist_ids": ids})
    return segs, len(checklists)


def pick_segment(segs, u):
    acc = 0.0
    for s in segs:
        acc += s["weight"]
        if u < acc:
            return s
    return segs[-1]


def simulate(arms, segs, seed, n_per_arm):
    """arms: list of {name, lift}. base rate is arm['base']. Returns per-arm counts. Stops when every arm has n_per_arm."""
    stats = dict((a["name"], {"n": 0, "clicks": 0, "segments": {}}) for a in arms)
    i = 0
    full = 0
    limit = 200 * n_per_arm * len(arms) + 1000
    while full < len(arms) and i < limit:
        i += 1
        vid = "v%07d" % i
        arm = arms[int(unit(seed, "arm", vid) * len(arms))]
        s = stats[arm["name"]]
        if s["n"] >= n_per_arm:
            continue
        seg = pick_segment(segs, unit(seed, "seg", vid))
        p = arm["base"] * (1.0 + arm["lift"] * seg["sensitivity"])
        click = unit(seed, "act", vid) < p
        s["n"] += 1
        s["clicks"] += 1 if click else 0
        g = s["segments"].setdefault(seg["name"], {"n": 0, "clicks": 0})
        g["n"] += 1
        g["clicks"] += 1 if click else 0
        if s["n"] == n_per_arm:
            full += 1
    return stats


def lift_for(variant, kind, name):
    if kind == "page":
        return float(variant["lift_relative"])
    if kind == "section":
        sl = variant.get("section_lifts") or {}
        if name not in sl:
            raise ValueError("variant %s has no assumed lift for section '%s'. Held: the section test." % (variant["name"], name))
        return float(sl[name])
    if "action_lift" not in variant:
        raise ValueError("variant %s has no assumed action_lift. Held: the action test." % variant["name"])
    return float(variant["action_lift"])


def classify(test, n_min_arm, alpha, min_n):
    return "clear" if (test["p"] < alpha and n_min_arm >= min_n) else "inconclusive"


def run_test(spec, segs):
    """spec: scope, primary_action, seed, visitors_per_arm, alpha, min_visitors_per_arm, base_rate, baseline name, variants, ablation."""
    kind, name = parse_scope(spec["scope"])
    n, alpha, min_n, base = int(spec["visitors_per_arm"]), float(spec["alpha"]), int(spec["min_visitors_per_arm"]), float(spec["base_rate"])
    variants = spec["variants"]
    arms = [{"name": "baseline", "base": base, "lift": 0.0}]
    for v in variants:
        arms.append({"name": v["name"], "base": base, "lift": lift_for(v, kind, name)})
    abl = spec.get("ablation") or {}
    abl_notes, abl_arms = [], []
    if abl.get("enabled"):
        if kind != "page" or not variants:
            abl_notes.append("Held: section ablations run only inside a page test with a variant.")
        else:
            v = variants[0]
            names = list((v.get("section_lifts") or {}))[:int(abl.get("cap", 3))]
            extra = len(names) * n
            total = (len(arms) + len(names)) * n
            if total > int(abl.get("visitor_cap_total", 40000)):
                abl_notes.append("Held: section ablations. %d simulated visitors would pass the cap of %d." % (total, int(abl.get("visitor_cap_total", 40000))))
            else:
                for s in names:
                    abl_arms.append({"name": "%s without %s" % (v["name"], s), "base": base,
                                     "lift": float(v["lift_relative"]) - float(v["section_lifts"][s]), "dropped": s})
                abl_notes.append("Ablations add %d simulated visitors. The section lifts are inputs, so this shows the method. "
                                 "It does not show which section works for real buyers." % extra)
    all_arms = arms + abl_arms
    stats = simulate(all_arms, segs, spec["seed"], n)
    out_arms = []
    for a in all_arms:
        s = stats[a["name"]]
        out_arms.append({"name": a["name"], "visitors": s["n"], "clicks": s["clicks"], "rate": s["clicks"] / float(s["n"]) if s["n"] else 0.0,
                         "segments": s["segments"], "ablation": "dropped" in a})
    by = dict((a["name"], a) for a in out_arms)
    comps = []
    for v in variants:
        b, x = by["baseline"], by[v["name"]]
        t = two_prop_test(b["clicks"], b["visitors"], x["clicks"], x["visitors"])
        t.update(arm=v["name"], vs="baseline", result=classify(t, min(b["visitors"], x["visitors"]), alpha, min_n))
        comps.append(t)
    ablations = []
    if abl_arms and variants:
        full = by[variants[0]["name"]]
        for a in abl_arms:
            x = by[a["name"]]
            t = two_prop_test(full["clicks"], full["visitors"], x["clicks"], x["visitors"])
            t.update(arm=a["name"], vs=variants[0]["name"], dropped=a["dropped"], result=classify(t, min(full["visitors"], x["visitors"]), alpha, min_n))
            ablations.append(t)
    limits = list(ALWAYS_LIMITS)
    if kind == "page":
        limits.insert(0, PAGE_LIMIT)
    if kind == "section":
        limits.insert(0, "Only section '%s' differs from the baseline. Other sections are the same." % name)
    if kind == "action":
        limits.insert(0, "Only the action '%s' differs from the baseline." % name)
    return {"label": LABEL, "scope": spec["scope"], "primary_action": spec["primary_action"], "seed": spec["seed"],
            "plan": {"visitors_per_arm": n, "alpha": alpha, "min_visitors_per_arm": min_n, "assumed_base_rate": base,
                     "rule": "clear if p < %s and each arm has at least %d visitors. Otherwise inconclusive." % (alpha, min_n)},
            "segments": [dict((k, s[k]) for k in ("name", "role", "weight", "sensitivity", "checklist_ids")) for s in segs],
            "assumptions": [{"arm": v["name"], "lift_relative": lift_for(v, kind, name), "note": v.get("note", "assumed, not measured")} for v in variants],
            "arms": out_arms, "comparisons": comps, "ablations": ablations, "ablation_notes": abl_notes, "limits": limits}


def load_demo_cfg():
    return common.load_json(DEMO_FILE)


def spec_from_scenario(cfg, scenario, scope="page", primary_action="main action click", section_names=None, variant_name="variant"):
    v = {"name": variant_name, "lift_relative": scenario["lift_relative"], "action_lift": scenario["action_lift"],
         "section_lifts": dict(scenario["section_lifts"]), "note": "assumed by the %s demo scenario" % scenario["name"]}
    if section_names:
        v["section_lifts"] = spread(scenario["lift_relative"], section_names)
    return {"scope": scope, "primary_action": primary_action, "seed": cfg["seed"], "visitors_per_arm": scenario["visitors_per_arm"],
            "alpha": cfg["alpha"], "min_visitors_per_arm": cfg["min_visitors_per_arm"], "base_rate": cfg["base_rate"],
            "variants": [v], "ablation": {"enabled": False, "cap": cfg.get("ablation_cap", 3), "visitor_cap_total": cfg.get("visitor_cap_total", 40000)}}


def spread(total, names):
    """Split a lift over sections: 60% to the first, the rest equal. An assumption, stated in the report."""
    if not names:
        return {}
    if len(names) == 1:
        return {names[0]: total}
    rest = total * 0.4 / (len(names) - 1)
    return dict([(names[0], total * 0.6)] + [(n, rest) for n in names[1:]])


def run_demos(project, page):
    cfg = load_demo_cfg()
    segs, _ = build_segments(project, page, cfg)
    results = []
    for sc in cfg["scenarios"]:
        r = run_test(spec_from_scenario(cfg, sc), segs)
        r["scenario"] = sc["name"]
        results.append(r)
    return results


def pct(x):
    return "%.2f%%" % (100.0 * x)


def result_lines(r):
    lines = ["%s A/B result. Scope: %s. Primary action: %s." % (LABEL, r["scope"], r["primary_action"]),
             "Plan (fixed before the run): %d simulated visitors per arm, seed %s, assumed baseline rate %s. %s" % (
                 r["plan"]["visitors_per_arm"], r["seed"], pct(r["plan"]["assumed_base_rate"]), r["plan"]["rule"]),
             "%-28s %-10s %-8s %s" % ("arm", "visitors", "clicks", "rate (SYNTHETIC)")]
    for a in r["arms"]:
        lines.append("%-28s %-10d %-8d %s" % (a["name"], a["visitors"], a["clicks"], pct(a["rate"])))
    for c in r["comparisons"]:
        rel = "n/a" if c["relative"] is None else "%+.1f%%" % (100 * c["relative"])
        lines.append("%s vs baseline: difference %+.2f points (95%% interval %+.2f to %+.2f), relative %s, z = %.2f, p = %.4f. Class: %s. (%s)"
                     % (c["arm"], 100 * c["diff"], 100 * c["ci_low"], 100 * c["ci_high"], rel, c["z"], c["p"], c["result"].upper(), LABEL))
    for c in r["ablations"]:
        lines.append("Ablation, drop '%s': difference vs the full variant %+.2f points, p = %.4f. Class: %s. (%s)"
                     % (c["dropped"], 100 * c["diff"], c["p"], c["result"].upper(), LABEL))
    lines.extend(r.get("ablation_notes", []))
    lines.append("Limits:")
    lines.extend("  - " + l for l in r["limits"])
    return lines


def approved_names(approval):
    """The variant names an approval covers. None means the approval names no variant, so all variants count."""
    v = (approval or {}).get("variant")
    if v is None or v == "" or v == []:
        return None
    items = [str(x) for x in (v if isinstance(v, (list, tuple)) else [v])]
    if any(x.strip().lower() == "both" for x in items):
        return None
    return items


def split_by_approval(pairs, approval):
    """pairs: [(variant dict with a name, scenario)], already paired with their scenarios.
    Return (tested, skipped_names, problem). With no 'variant' in the approval, every pair is tested (the old rule).
    A 'variant' that names no variant of the run holds the sandbox: tested is empty and problem says why."""
    names = approved_names(approval)
    if names is None:
        return list(pairs), [], None
    tested = [p for p in pairs if str(p[0]["name"]) in names]
    skipped = [str(p[0]["name"]) for p in pairs if str(p[0]["name"]) not in names]
    if not tested:
        return [], skipped, "The approval names variant %s. The run has no such variant. Held: the sandbox." % ", ".join(names)
    return tested, skipped, None


def not_tested_line(name):
    return "Variant %s: not approved, not tested" % name


def selftest():
    st = common.SelfTest("sandbox")
    pairs = [({"name": "A"}, "s0"), ({"name": "B"}, "s1")]
    t, sk, pr = split_by_approval(pairs, {"approved": True, "variant": "A"})
    st.expect([p[1] for p in t] == ["s0"] and sk == ["B"] and pr is None, "an approval for variant A tests A with its own scenario and skips B")
    t, sk, pr = split_by_approval(pairs, {"approved": True})
    st.expect(len(t) == 2 and sk == [] and pr is None, "an approval with no variant field tests every variant")
    t, sk, pr = split_by_approval(pairs, {"approved": True, "variant": "both"})
    st.expect(len(t) == 2 and sk == [] and pr is None, "an approval for both variants tests both")
    t, sk, pr = split_by_approval(pairs, {"approved": True, "variant": "Z"})
    st.expect(t == [] and "Held" in pr, "an approval for an unknown variant holds the sandbox")
    t, sk, pr = split_by_approval(pairs, {"approved": True, "variant": "B"})
    st.expect([p[1] for p in t] == ["s1"] and sk == ["A"], "an approval for B alone keeps B on its own scenario")
    st.expect(not_tested_line("B") == "Variant B: not approved, not tested", "the skip line reads as the rule says")
    st.expect(abs(unit(1, "arm", "v1") - unit(1, "arm", "v1")) == 0 and unit(1, "arm", "v1") != unit(2, "arm", "v1"),
              "the hash number is stable for one seed and changes with the seed")
    st.expect(all(0 <= unit(7, "a", "v%d" % i) < 1 for i in range(200)), "the hash number stays in [0, 1)")
    t = two_prop_test(100, 1000, 100, 1000)
    st.expect(abs(t["z"]) < 1e-9 and abs(t["p"] - 1.0) < 1e-9, "equal rates give z = 0 and p = 1")
    t = two_prop_test(100, 1000, 140, 1000)
    st.expect(2.5 < t["z"] < 3.0 and t["p"] < 0.01 and t["ci_low"] > 0, "a known gap (10% vs 14%) gives z near 2.7 and a small p")
    for bad in ("", "section:", "banner", "action:  "):
        try:
            parse_scope(bad)
            st.expect(False, "scope '%s' is refused" % bad)
        except ValueError:
            st.expect(True, "scope '%s' is refused" % bad)
    st.expect(parse_scope("section:hero") == ("section", "hero") and parse_scope("action:Try it") == ("action", "Try it"), "scope forms parse")
    root = common.make_temp_project()
    try:
        common.write_file(os.path.join(root, "pages", "p", "profile.json"),
                          '{"primary_audience": "Enterprise leaders who decide", "supporting_audiences": ["Platform leads who run the test", "Procurement buyers"]}')
        common.write_file(os.path.join(root, "pages", "p", "buyer-and-wedge", "checklists", "a.md"),
                          "---\nid: BR-001\ntitle: \"Platform lead checklist\"\n---\nx\n")
        cfg = load_demo_cfg()
        segs, n_lists = build_segments(root, "p", cfg)
        st.expect(len(segs) == 3 and abs(sum(s["weight"] for s in segs) - 1.0) < 1e-9 and segs[0]["role"] == "primary" and n_lists == 1,
                  "segments: one primary and each supporting audience, weights add to 1")
        st.expect(segs[1]["checklist_ids"] == ["BR-001"] and segs[2]["checklist_ids"] == [], "a checklist maps to the matching supporting audience")
        a = run_demos(root, "p")
        b = run_demos(root, "p")
        st.expect([r["arms"] for r in a] == [r["arms"] for r in b], "the same seed gives the same result")
        st.expect(a[0]["comparisons"][0]["result"] == "clear" and a[1]["comparisons"][0]["result"] == "inconclusive",
                  "demo scenarios: one clear, one inconclusive")
        st.expect(all(arm["visitors"] == r["plan"]["visitors_per_arm"] for r in a for arm in r["arms"]), "every arm holds exactly the planned visitors")
        text = "\n".join("\n".join(result_lines(r)) for r in a)
        st.expect(text.count(LABEL) >= 2 * 3 and "cannot show which section" in text, "output says SYNTHETIC and states the page-test limit")
        spec = spec_from_scenario(cfg, cfg["scenarios"][0], scope="section:hero")
        r = run_test(spec, segs)
        st.expect(r["assumptions"][0]["lift_relative"] == 0.3 and "cannot show which section" not in "\n".join(r["limits"]), "a section scope uses the section lift")
        try:
            run_test(spec_from_scenario(cfg, cfg["scenarios"][0], scope="section:nope"), segs)
            st.expect(False, "a section with no assumed lift is refused")
        except ValueError as e:
            st.expect("Held" in str(e), "a section with no assumed lift is refused and held")
        r = run_test(spec_from_scenario(cfg, cfg["scenarios"][0], scope="action:Try it"), segs)
        st.expect(r["assumptions"][0]["lift_relative"] == 0.4, "an action scope uses the action lift")
        spec = spec_from_scenario(cfg, cfg["scenarios"][1], scope="page")
        spec["ablation"]["enabled"] = True
        r = run_test(spec, segs)
        st.expect(len(r["ablations"]) == 3 and len(r["arms"]) == 5, "ablations add one arm for each section, up to the cap")
        spec["ablation"]["visitor_cap_total"] = 2000
        r = run_test(spec, segs)
        st.expect(r["ablations"] == [] and any("Held: section ablations" in n for n in r["ablation_notes"]), "ablations stop at the visitor cap")
        spec = spec_from_scenario(cfg, cfg["scenarios"][0], scope="action:x")
        spec["ablation"]["enabled"] = True
        st.expect(any("only inside a page test" in n for n in run_test(spec, segs)["ablation_notes"]), "ablations run only in a page test")
        spec = spec_from_scenario(cfg, cfg["scenarios"][0])
        spec["seed"] = 5
        c1 = run_test(spec, segs)["arms"]
        spec["seed"] = 6
        st.expect(c1 != run_test(spec, segs)["arms"], "a different seed gives a different split")
        st.expect(spread(0.5, ["a", "b", "c"]) == {"a": 0.3, "b": 0.1, "c": 0.1}, "a lift spreads 60% to the first section and the rest equally")
    finally:
        common.drop_temp(root)
    return st.done()


def main(argv):
    if "--selftest" in argv:
        return selftest()

    def arg(name, default=None):
        return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else default
    page = arg("--page", "")
    if "--demo" in argv:
        for r in run_demos(common.PROJECT, page):
            print("\n== demo scenario: %s ==" % r["scenario"])
            print("\n".join(result_lines(r)))
        return 0
    run_id = arg("--run-id")
    if not page or not run_id:
        print("Use --page <slug> --run-id <id>, or --demo, or --selftest")
        return 2
    path = os.path.join(runlib.run_path(common.PROJECT, page, run_id), "sandbox-input.json")
    spec = runlib.jread(path)
    if spec is None:
        print("Research gap. Missing: %s. Do more research with the run script (agent/run.py). Held: the sandbox test." % os.path.relpath(path, common.PROJECT))
        return 1
    specs = spec["tests"] if "tests" in spec else [spec]
    results = []
    for one in specs:
        segs, _ = build_segments(common.PROJECT, page, one)
        try:
            r = run_test(one, segs)
        except ValueError as e:
            print("STOPPED. %s" % e)
            return 1
        print("\n".join(result_lines(r)))
        results.append(r)
    runlib.jwrite(os.path.join(os.path.dirname(path), "sandbox-results.json"), {"label": LABEL, "tests": results})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Step 11: SYNTHETIC hero A/B sandbox for one approved variant. No model calls. Nothing reaches the live site.

Run:  python3 agent/sandbox_hero.py --page token-factory --run probe3-YYYYMMDD-HHMMSS
      python3 agent/sandbox_hero.py --selftest

It refuses to run unless a variant is currently approved (shortlist.current_approval) and its variant
hash and PNG hash still match the files (Decisions Log row 35).

Two kinds of numbers, kept apart in every output:
  1. SIMULATED RATES. A seeded simulation (agent/sandbox.py) with click rates we DECLARE in
     agent/sandbox_hero.json. Scenarios: clear and inconclusive, plus an A/A check (no lift).
     The simulation returns the lift we typed in, plus chance noise. It discovers nothing.
  2. BROWSER SESSIONS. A fixed number of Playwright sessions per arm on the LOCAL saved copy of the
     page. Each one checks that the right H1, sub-line and button load, clicks the main button and
     records where it would go. Every non-local request is aborted (inline scripts run, their outside calls are
     blocked), so no bot traffic reaches sarvam.ai. The click is stopped before it leaves.
Writes runs/<run>/sandbox/: events.jsonl, sandbox-results.json, FINDINGS.md.
"""
import argparse
import datetime
import glob
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import sandbox as sim  # noqa: E402
import shortlist  # noqa: E402

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSIONS_PER_ARM = 20
CONFIG = os.path.join(PROJECT, "agent", "sandbox_hero.json")
LABEL = "SYNTHETIC"

SWAP_JS = r"""
([h1, sub, cta, href]) => {
  const set = (el, txt) => {
    const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    let first = true, n;
    while ((n = w.nextNode())) { if (!n.textContent.trim()) continue; n.textContent = first ? txt : ""; first = false; }
    if (first) el.textContent = txt;
  };
  const q = s => document.querySelector(`[data-hero="${s}"]`);
  if (h1 !== null) set(q("h1"), h1);
  if (sub !== null) set(q("sub"), sub);
  if (cta !== null) { const a = document.querySelector("[data-main-cta]"); set(a, cta); a.setAttribute("href", href); }
  return true;
}
"""
CLICK_JS = r"""
() => {
  window.__clicked = null;
  document.addEventListener("click", e => {
    const a = e.target.closest('[data-main-cta]');
    if (a) { e.preventDefault(); e.stopPropagation(); window.__clicked = a.getAttribute("href"); }
  }, true);
}
"""
READ_JS = r"""
() => {
  const t = s => { const el = document.querySelector(`[data-hero="${s}"]`); return el ? el.innerText.replace(/\s+/g, " ").trim() : null; };
  const m = document.querySelector("[data-main-cta]");
  return {h1: t("h1"), sub: t("sub"), cta: m ? m.innerText.replace(/\s+/g, " ").trim() : null};
}
"""


def wilson(x, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = x / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def norm(t):
    return re.sub(r"\s+", " ", (t or "").replace("’", "'")).strip()


def load(page, run):
    base = os.path.join(PROJECT, "pages", page)
    rd = os.path.join(base, "runs", run)
    probe = json.load(open(os.path.join(rd, "probe3.json"), encoding="utf-8"))
    ap = shortlist.current_approval(rd)
    if not ap:
        sys.exit("REFUSED: no variant is currently approved. A person approves a variant in the console first.")
    v = next((x for x in probe["variants"] if x["name"] == ap["variant"]), None)
    png = os.path.join(rd, "pair-%s.png" % ap["variant"])
    if not v or shortlist.variant_hash(v) != ap["variant_hash"]:
        sys.exit("REFUSED: the variant changed after approval (hash mismatch).")
    if not os.path.isfile(png) or shortlist.file_hash(png) != ap["png_hash"]:
        sys.exit("REFUSED: the PNG pair changed after approval (hash mismatch).")
    groups = {x["name"]: x for x in shortlist.classify(probe)}
    if groups[v["name"]]["group"] == "failed_gate1":
        sys.exit("REFUSED: a Gate 1 failure cannot be tested.")
    prof = json.load(open(os.path.join(base, "profile.json"), encoding="utf-8"))
    dests = {d["id"]: d for d in (prof.get("hero") or {}).get("cta_destinations", [])}
    cap_dir = os.path.dirname(os.path.join(PROJECT, probe["live_capture"]))
    hero = json.load(open(os.path.join(cap_dir, "hero.json"), encoding="utf-8"))
    main = next(c for c in hero["ctas"] if c.get("href"))
    if probe.get("destinations"):   # newer runs save the goal's destination with the run
        dests = {k: d for k, d in probe["destinations"].items()}
    return dict(base=base, rd=rd, probe=probe, ap=ap, v=v, dests=dests, cap_dir=cap_dir, hero=hero, main=main,
                group=groups[v["name"]])


def local_copy(cap_dir, out_dir, main_index=0):
    """The saved page without its <base> tag, so relative links cannot resolve to the live site."""
    html = open(os.path.join(cap_dir, "snapshot.html"), encoding="utf-8").read()
    html = re.sub(r"<base [^>]*>", "", html, count=1)
    if html.count('data-hero="h1"') != 1 or html.count('data-hero="cta-%d"' % main_index) != 1:
        sys.exit("the saved page lost its data-hero markers; capture again")
    path = os.path.join(out_dir, "snapshot-local.html")
    open(path, "w", encoding="utf-8").write(html)
    return path


def browser_sessions(path, arms, events_path, main_index, n=SESSIONS_PER_ARM):
    from playwright.sync_api import sync_playwright
    url = "file://" + path
    rows, blocked = [], {"count": 0, "hosts": set()}
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        for arm in arms:
            for i in range(n):
                ctx = br.new_context(viewport={"width": 1280, "height": 900}, java_script_enabled=True)

                def guard(route):
                    u = route.request.url
                    if u.startswith("file://"):
                        return route.continue_()
                    blocked["count"] += 1
                    blocked["hosts"].add(re.sub(r"^\w+://([^/]+).*$", r"\1", u))
                    return route.abort()
                ctx.route("**/*", guard)
                pg = ctx.new_page()
                pg.goto(url, wait_until="domcontentloaded")
                start_url = pg.url
                pg.evaluate("i => document.querySelector('[data-hero=\"cta-' + i + '\"]').setAttribute('data-main-cta', '1')", main_index)
                pg.evaluate(CLICK_JS)
                if arm["swap"]:
                    pg.evaluate(SWAP_JS, arm["swap"])
                seen = pg.evaluate(READ_JS)
                pg.click('[data-main-cta]', timeout=5000, force=True)
                clicked = pg.evaluate("window.__clicked")
                left = pg.url != start_url or not start_url.startswith("file://")
                row = {"label": LABEL, "arm": arm["name"], "session": i + 1,
                       "h1_ok": norm(seen["h1"]) == norm(arm["expect"]["h1"]),
                       "sub_ok": norm(seen["sub"]) == norm(arm["expect"]["sub"]),
                       "button_ok": norm(seen["cta"]) == norm(arm["expect"]["cta"]),
                       "click_href": clicked, "href_ok": (clicked or "").rstrip("/") == (arm["expect"]["href"] or "").rstrip("/"), "left_local_page": left}
                rows.append(row)
                ctx.close()
        br.close()
    with open(events_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows, {"count": blocked["count"], "hosts": sorted(blocked["hosts"])}


def simulate(cfg, segs, lift, n, salt):
    arms = [{"name": "baseline", "base": cfg["base_rate"], "lift": 0.0},
            {"name": "variant", "base": cfg["base_rate"], "lift": lift}]
    st = sim.simulate(arms, segs, "%s-%s" % (cfg["seed"], salt), n)
    b, v = st["baseline"], st["variant"]
    t = sim.two_prop_test(b["clicks"], b["n"], v["clicks"], v["n"])
    res = {"visitors_per_arm": n, "declared_lift_relative": lift, "label": LABEL}
    for k, s in (("baseline", b), ("variant", v)):
        lo, hi = wilson(s["clicks"], s["n"])
        res[k] = {"visitors": s["n"], "clicks": s["clicks"], "rate": s["clicks"] / s["n"], "ci95": [lo, hi]}
    res.update(diff=t["diff"], diff_ci95=[t["ci_low"], t["ci_high"]], relative_lift=t["relative"], z=t["z"], p=t["p"],
               result=sim.classify(t, n, cfg["alpha"], cfg["min_visitors_per_arm"]))
    return res


import sandbox_plan as plan_mod  # noqa: E402

sample_needed = plan_mod.sample_needed
GOAL_WATCH = {
    "console": "a click on the main button that opens the console (start building)",
    "contact": "a click on the main button that opens the contact-sales page",
    "pricing": "a click on the main button that opens the pricing page",
    "docs": "a click on the main button that opens the documentation",
    "explore": "a click on the main button that opens the models or a demo",
}
SCENARIO_NAME = {"enough": "Test 1: the lift we expect, enough visitors", "too_few": "Test 2: the same lift, too few visitors",
                 "clear": "Test 1: big lift, many visitors", "inconclusive": "Test 2: small lift, few visitors", "A/A check": "Test 3: no difference (control)"}


def simulate(cfg, segs, lift, n, salt):
    arms = [{"name": "baseline", "base": cfg["base_rate"], "lift": 0.0},
            {"name": "variant", "base": cfg["base_rate"], "lift": lift}]
    st = sim.simulate(arms, segs, "%s-%s" % (cfg["seed"], salt), n)
    b, v = st["baseline"], st["variant"]
    t = sim.two_prop_test(b["clicks"], b["n"], v["clicks"], v["n"])
    res = {"visitors_per_arm": n, "declared_lift_relative": lift, "label": LABEL}
    for k, s in (("baseline", b), ("variant", v)):
        lo, hi = wilson(s["clicks"], s["n"])
        res[k] = {"visitors": s["n"], "clicks": s["clicks"], "rate": s["clicks"] / s["n"], "ci95": [lo, hi]}
    res.update(diff=t["diff"], diff_ci95=[t["ci_low"], t["ci_high"]], relative_lift=t["relative"], z=t["z"], p=t["p"],
               result=sim.classify(t, n, cfg["alpha"], cfg["min_visitors_per_arm"]))
    return res


def findings(D, sims, sessions, blocked, plan, narrative, narrative_by):
    v, ap, g = D["v"], D["ap"], D["group"]
    pct = lambda x: "%.2f%%" % (100 * x)
    ok = lambda arm: sum(r["h1_ok"] and r["sub_ok"] and r["button_ok"] and r["href_ok"] and not r["left_local_page"] for r in sessions if r["arm"] == arm)
    goal = D["probe"].get("goal", {})
    L = ["# Findings: hero A/B sandbox (%s)" % LABEL, "",
         "**Every number below comes from a simulation set up from this run's buyer, goal and judge scores, or from a scripted browser. None of it comes from real buyers.**", "",
         "## In plain words", "",
         "**Goal chosen:** %s. **What is counted:** %s. A visitor who clicks counts as 1; one who does not counts as 0. That is the only thing measured." % (
             goal.get("label", "not recorded"), GOAL_WATCH.get(goal.get("kind"), "a click on the main button")), "",
         "**Buyer this run targets:** %s." % D["probe"].get("persona", {}).get("buyer", "not recorded"), ""]
    if plan:
        L += ["**What the tests are.** They check the measuring method. They do not tell you that variant %s wins, because its lift is set from the judges' scores by a stated rule, so the simulation can only hand it back with chance noise:" % v["name"],
              ("- **Test 1** uses the lift we expect and the largest sample the sandbox allows (%s per arm). This lift is too small for that sample, so **inconclusive** is the correct answer here." % format(plan["scenarios"][0]["visitors_per_arm"], ","))
              if plan.get("capped") else "- **Test 1** uses the lift we expect and enough visitors for a real test to see it. A working method says **clear** in most such tests (about 8 or 9 in 10); chance can still give inconclusive.",
              "- **Test 2** uses the same lift with too few visitors. A working method should say **inconclusive**: too little data.",
              "- **Test 3** gives no lift (the page against itself). A working method must say **inconclusive**. If it says clear, the method invents wins.", ""]
        L += ["## How the simulation was set up for this run", "", narrative, "", "_Written by %s; code checked that every number is in the plan below._" % narrative_by, "",
              "### Who the simulated visitors are", "",
              "| Visitor group | Share of visitors | Goal fit | Reaction strength |", "|---|---|---|---|"]
        for s in plan["segments"]:
            L.append("| %s%s | %.0f%% | %.1f | %.2f |" % (s["name"], " (targeted)" if s["role"] == "targeted" else "", 100 * s["weight"], s["goal_fit"], s["sensitivity"]))
        r = plan["lift_rule"]
        L += ["", "Goal fit: how well the goal suits that role (1.0 best, 0.6 second best, 0.3 otherwise), from `rules/goals.json`. Reaction strength = goal fit x 1.0 for the targeted buyer, x %.1f for other roles. These are analyst proposals, not research." % D["cfg"]["supporting_sensitivity"], "",
              "### How the lift was set", "",
              "| Step | Value |", "|---|---|"]
        for k, val in plan["judge_gains"].items():
            L.append("| %s: average gain on the gaps this variant targets | %+.2f |" % (k, val))
        L += ["| Average of the two judges | %+.2f |" % plan["avg_gain"],
              "| Rule: declared lift = %.2f x average gain, at least %.0f%% and at most %.0f%% | %.1f%% |" % (r["lift_per_gain"], 100 * r["floor"], 100 * r["cap"], 100 * plan["declared_lift"]),
              "| Effective lift once every group's reaction strength is applied | %.1f%% |" % (100 * plan["effective_lift"]),
              "| Visitors per arm a real test needs to see that lift | %s |" % (format(plan["visitors_needed_for_effective_lift"], ",") if plan["visitors_needed_for_effective_lift"] else "no lift to detect"), "",
              ("**What this means for the run:** the expected lift is too small to see at the sandbox's largest sample. A real test would need %s visitors per arm. Two things raise the lift: a goal that fits this buyer better, or a variant whose judge gain is larger. Look at the Goal fit column: a low goal fit for the targeted buyer is the first thing to check." % format(plan["visitors_needed_for_effective_lift"], ",")) if plan.get("capped") else "**What this means for the run:** the expected lift is large enough to see with a realistic sample (Test 1).", "",
              "**Derived, not typed:** the visitor groups, their shares and reaction strengths, the lift, and the visitor counts for Tests 1 and 2. **Typed assumptions** (`agent/sandbox_hero.json`): the base click rate (%s, not measured on sarvam.ai), the half strength for other roles, the lift rule, and the goal-fit values." % pct(plan["base_rate"]), ""]
    L += ["## What was tested", "",
          "| Arm | H1 | Sub-line | Main button | Goes to |", "|---|---|---|---|---|",
          "| Baseline (live, captured %s) | %s | %s | %s | %s |" % (D["hero"].get("captured_at", "")[:10], D["hero"]["h1"], D["hero"]["sub"], D["main"]["text"], D["main"]["href"]),
          "| Variant %s | %s | %s | %s | %s |" % (v["name"], v["h1"], v["subline"], v["cta"], D["dests"][v["cta_destination"]]["url"]), "",
          "Approved by %s on %s. Group at approval: %s.%s" % (ap["name"], ap["at"], g["group"],
              (" Chosen by a person against a Gate 2 result. Reason given: \"%s\"" % ap["reason"]) if ap.get("override") else ""),
          "Test type: hero. The words and the main button change together, so a result cannot be credited to one of them alone (Decisions Log row 28).", "",
          "## 1. Simulated rates (seeded)", "",
          "Base click rate %s on the baseline. Seed %s. Two-sided two-proportion z test, alpha %s. A result counts as clear only with p below alpha and at least %d visitors per arm." % (
              pct(D["cfg"]["base_rate"]), D["cfg"]["seed"], D["cfg"]["alpha"], D["cfg"]["min_visitors_per_arm"]), "",
          "| Test | Visitors per arm | Lift we declared | Baseline rate (95% interval) | Variant rate (95% interval) | Difference (95% interval) | p | Result |",
          "|---|---|---|---|---|---|---|---|"]
    for name, r in sims.items():
        L.append("| %s | %s | %+.1f%% | %s (%s to %s) | %s (%s to %s) | %+.2f pts (%+.2f to %+.2f) | %s | %s |" % (
            SCENARIO_NAME.get(name, name), format(r["visitors_per_arm"], ","), 100 * r["declared_lift_relative"],
            pct(r["baseline"]["rate"]), pct(r["baseline"]["ci95"][0]), pct(r["baseline"]["ci95"][1]),
            pct(r["variant"]["rate"]), pct(r["variant"]["ci95"][0]), pct(r["variant"]["ci95"][1]),
            100 * r["diff"], 100 * r["diff_ci95"][0], 100 * r["diff_ci95"][1], "<0.0001" if r["p"] < 0.0001 else "%.4f" % r["p"], r["result"]))
    t1 = next(iter(sims.values()))
    if plan and t1["result"] != "clear" and not plan.get("capped"):
        L += ["", "**Test 1 came out inconclusive even though its sample was sized to see this lift.** That can happen: a test sized for 80 to 90 percent power still misses about 1 time in 6 or 10 by chance. It is not a fault in the method. It shows why a small lift can hide in a real test."]
    L += ["", "Test 3 runs the baseline against itself. It should be inconclusive; if it ever says clear, the test set-up is wrong.", "",
          "## 2. Browser sessions (local saved page, scripted)", "",
          "%d sessions per arm on the saved copy of the page. Each session loads the page, checks the hero text, clicks the main button and records where it would go. The click is stopped before it leaves." % SESSIONS_PER_ARM, "",
          "| Arm | Sessions | All checks passed | Button would go to |", "|---|---|---|---|"]
    for arm in ("baseline", "variant"):
        hrefs = sorted({str(r["click_href"]) for r in sessions if r["arm"] == arm})
        L.append("| %s | %d | %d | %s |" % (arm, sum(r["arm"] == arm for r in sessions), ok(arm), ", ".join(hrefs)))
    L += ["", "Requests to other hosts that the sandbox blocked: %d (hosts: %s). Nothing left the machine. The sessions check structure and links, not looks." % (
              blocked["count"], ", ".join(blocked["hosts"]) or "none"), "",
          "## 3. What a real test would need", "",
          "Base click rate assumed %s. Visitors per arm needed to see a lift reliably (alpha 0.05, power 80%%, calculated, not simulated):" % pct(D["cfg"]["base_rate"]), "",
          "| Lift you hope to detect | Visitors per arm | Visitors in both arms |", "|---|---|---|"] + [
              "| %+d%% | %s | %s |" % (100 * lf, format(sample_needed(D["cfg"]["base_rate"], lf), ","), format(2 * sample_needed(D["cfg"]["base_rate"], lf), ",")) for lf in (0.5, 0.25, 0.10, 0.05)] + [
          "", "## Limits", "",
          "- The visitors are simulated. The result does not predict what real buyers do.",
          "- The lift is set from the judges' scores by a rule. It is an assumption. The simulation returns it with chance noise; it does not discover it.",
          "- The browser sessions prove the variant page loads and its button points to the right place. They say nothing about whether people would click.",
          "- The judges (Jev and Judge 2) are general decision models, not trained for this work. Their scores chose the variant to test; they are not evidence of a lift.",
          "- A real test needs live traffic, an agreed sample size and a stopping rule fixed before the start.", ""]
    return "\n".join(L)


def main(page, run):
    D = load(page, run)
    cfg = json.load(open(CONFIG, encoding="utf-8"))
    D["cfg"] = cfg
    out = os.path.join(D["rd"], "sandbox")
    os.makedirs(out, exist_ok=True)
    import llm  # noqa: E402
    llm.LOG_PATH = os.path.join(out, "run-log.jsonl")
    plan = plan_mod.build(D["probe"], D["v"]["name"], cfg)
    narrative, narrative_by = (None, None)
    if plan:
        segs, scenarios = plan["segments"], plan["scenarios"]
        narrative, narrative_by = plan_mod.narrate(plan, llm)
        print("plan: %d visitor groups, declared lift %.1f%%, effective %.1f%%, visitors per arm %s" % (
            len(segs), 100 * plan["declared_lift"], 100 * plan["effective_lift"], [s["visitors_per_arm"] for s in scenarios]))
    else:   # an old run with no Gate 2 scores: the typed fallback
        segs, _ = sim.build_segments(PROJECT, page, cfg)
        scenarios = cfg["scenarios_fallback"]
    sims = {}
    for sc in scenarios:
        sims[sc["name"]] = simulate(cfg, segs, float(sc["lift_relative"]), int(sc["visitors_per_arm"]), sc["name"])
    big = max(int(s["visitors_per_arm"]) for s in scenarios)
    sims["A/A check"] = simulate(cfg, segs, 0.0, big, "aa")
    v = D["v"]
    dest = D["dests"][v["cta_destination"]]["url"]
    arms = [{"name": "baseline", "swap": None,
             "expect": {"h1": D["hero"]["h1"], "sub": D["hero"]["sub"], "cta": D["main"]["text"], "href": D["main"]["href"]}},
            {"name": "variant", "swap": [v["h1"], v["subline"], v["cta"], dest],
             "expect": {"h1": v["h1"], "sub": v["subline"], "cta": v["cta"], "href": dest}}]
    sessions, blocked = browser_sessions(local_copy(D["cap_dir"], out, D["main"]["index"]), arms, os.path.join(out, "events.jsonl"), D["main"]["index"])
    res = {"label": LABEL, "made": datetime.datetime.now().isoformat(timespec="seconds"), "run": run, "variant": v["name"],
           "approval": {k: D["ap"][k] for k in ("name", "at", "override", "reason", "variant_hash", "png_hash")},
           "group_at_approval": D["group"]["group"], "simulated": sims, "plan": plan, "plan_explained_by": narrative_by,
           "browser": {"sessions_per_arm": SESSIONS_PER_ARM, "passed": {a: sum(r["h1_ok"] and r["sub_ok"] and r["button_ok"] and r["href_ok"] and not r["left_local_page"] for r in sessions if r["arm"] == a) for a in ("baseline", "variant")},
                       "blocked_requests": blocked},
           "config": {k: cfg[k] for k in ("seed", "alpha", "min_visitors_per_arm", "base_rate")}}
    json.dump(res, open(os.path.join(out, "sandbox-results.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    open(os.path.join(out, "FINDINGS.md"), "w", encoding="utf-8").write(findings(D, sims, sessions, blocked, plan, narrative, narrative_by))
    for name, r in sims.items():
        print("%-12s n=%5d  baseline %.2f%%  variant %.2f%%  p=%.4f  %s" % (name, r["visitors_per_arm"], 100 * r["baseline"]["rate"], 100 * r["variant"]["rate"], r["p"], r["result"]))
    print("browser checks passed:", res["browser"]["passed"], "of", SESSIONS_PER_ARM, "per arm | blocked requests:", blocked["count"])
    print("wrote", os.path.relpath(out, PROJECT))
    if sims["A/A check"]["result"] != "inconclusive":
        sys.exit("A/A CHECK FAILED: the set-up shows a lift where none was declared")


def selftest():
    ok = True
    lo, hi = wilson(40, 1000)
    ok &= 0.029 < lo < 0.031 and 0.053 < hi < 0.055
    print("%s wilson(40,1000) = %.4f..%.4f" % ("PASS" if ok else "FAIL", lo, hi))
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--page")
    ap.add_argument("--run")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if not (a.page and re.match(r"^[a-z0-9-]+$", a.page) and a.run and re.match(r"^probe3-\d{8}-\d{6}$", a.run)):
        sys.exit("give --page and --run")
    main(a.page, a.run)

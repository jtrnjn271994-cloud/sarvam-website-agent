#!/usr/bin/env python3
"""Sandbox plan for one approved variant (Decisions Log row 40).

The plan is built from the run's own buyer, goal and judge scores, so it changes with every run:
  1. VISITOR GROUPS: the buyer this run targets, plus the other roles of the same industry (library/personas.json).
  2. REACTION STRENGTH of each group = how well the chosen goal fits that role (rules/goals.json, buyer_default_goal)
     x 1.0 for the targeted buyer or the 'supporting_sensitivity' for other roles (the variant was written for the targeted buyer).
  3. DECLARED LIFT = lift_per_gain x the judges' average gain on the targeted gaps, capped (agent/sandbox_hero.json).
  4. VISITORS PER ARM for each test = what a real test needs to detect that lift (calculated).
A reasoning model then explains the set-up in plain words; code checks that every number it writes is in the plan.
The base click rate stays an assumption. Nothing here is measured on sarvam.ai.
"""
import json
import math
import os
import re

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sample_needed(base, lift, alpha_z=1.959964, power_z=0.841621):
    """Visitors per arm for a two-sided two-proportion test (alpha 0.05, power 0.80). A plain calculation."""
    if lift <= 0:
        return None
    p1, p2 = base, base * (1 + lift)
    return int(math.ceil((alpha_z + power_z) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / (p2 - p1) ** 2))


def _goal_fit(role_key, goal_id, goals_cfg, fits):
    slug = role_key.split(":", 1)[1]
    prefs = next((v for k, v in goals_cfg.get("buyer_default_goal", {}).items() if k != "note" and slug.startswith(k)), [])
    idx = prefs.index(goal_id) if goal_id in prefs else len(fits) - 1
    return fits[min(idx, len(fits) - 1)]


def build(probe, variant_name, cfg):
    """Return the plan dict, or None when the run has no Gate 2 scores to derive a lift from."""
    g2 = (probe.get("gate2") or {}).get(variant_name) or {}
    gains = {}
    for j, label in (("judge1", "Jev"), ("judge2", "Judge 2")):
        r = g2.get(j) or {}
        t = r.get("targeted") or []
        if t and r.get("delta"):
            gains[label] = sum(r["delta"][k] for k in t) / len(t)
    if not gains or not (probe.get("persona") or {}).get("key"):
        return None
    goals_cfg = json.load(open(os.path.join(PROJECT, "rules", "goals.json"), encoding="utf-8"))
    P = json.load(open(os.path.join(PROJECT, "library", "personas.json"), encoding="utf-8"))
    pk, goal = probe["persona"]["key"], probe["goal"]["id"]
    ind = next((i for i in P["industries"] if i["id"] == pk.split(":")[0]), None)
    if not ind:
        return None
    fits = cfg["goal_fit"]
    share = float(cfg["primary_share"])
    others = [r for r in ind["roles"] if r["key"] != pk]
    prim = next(r for r in ind["roles"] if r["key"] == pk)
    segs = [{"name": prim["role"], "industry": ind["name"], "role": "targeted", "weight": share if others else 1.0,
             "goal_fit": _goal_fit(pk, goal, goals_cfg, fits), "strength": 1.0}]
    for r in others:
        segs.append({"name": r["role"], "industry": ind["name"], "role": "other", "weight": (1 - share) / len(others),
                     "goal_fit": _goal_fit(r["key"], goal, goals_cfg, fits), "strength": float(cfg["supporting_sensitivity"])})
    for s in segs:
        s["sensitivity"] = round(s["goal_fit"] * s["strength"], 4)
    avg = sum(gains.values()) / len(gains)
    lift = 0.0 if avg <= 0 else max(cfg["lift_floor"], min(cfg["lift_cap"], cfg["lift_per_gain"] * avg))
    eff = sum(s["weight"] * s["sensitivity"] for s in segs) * lift
    need = sample_needed(cfg["base_rate"], eff) if eff > 0 else None
    cap = int(cfg["max_visitors_per_arm"])
    if need:
        enough = min(cap, int(math.ceil(need * cfg["enough_factor"] / 100.0) * 100))
        few = max(400, int(round(enough * cfg["few_factor"] / 100.0) * 100))
    else:
        enough, few = 8000, 800
    return {"segments": segs, "judge_gains": {k: round(v, 3) for k, v in gains.items()}, "avg_gain": round(avg, 3),
            "lift_rule": {"lift_per_gain": cfg["lift_per_gain"], "floor": cfg["lift_floor"], "cap": cfg["lift_cap"]},
            "declared_lift": round(lift, 4), "effective_lift": round(eff, 4), "base_rate": cfg["base_rate"],
            "visitors_needed_for_effective_lift": need, "capped": bool(need and need > cap),
            "goal": probe["goal"], "persona": probe["persona"].get("buyer"),
            "scenarios": [{"name": "enough", "visitors_per_arm": enough, "lift_relative": lift},
                          {"name": "too_few", "visitors_per_arm": few, "lift_relative": lift}]}


def facts(plan):
    """Plain-text facts. Every number the explanation may use is in here."""
    pc = lambda x: "%.0f%%" % (100 * x)
    L = ["Goal: %s." % plan["goal"]["label"], "Base click rate assumed: %.1f%%." % (100 * plan["base_rate"])]
    for s in plan["segments"]:
        L.append("Visitor group: %s (%s), %s of visitors, goal fit %.1f, reaction strength %.2f%s." % (
            s["name"], s["industry"], pc(s["weight"]), s["goal_fit"], s["sensitivity"], ", the buyer this run targets" if s["role"] == "targeted" else ""))
    for k, v in plan["judge_gains"].items():
        L.append("%s average gain on the targeted gaps: %+.2f." % (k, v))
    r = plan["lift_rule"]
    L.append("Average of the judges: %+.2f. Rule: declared lift = %.2f x average gain, at least %s and at most %s. Declared lift: %s." % (
        plan["avg_gain"], r["lift_per_gain"], pc(r["floor"]), pc(r["cap"]), pc(plan["declared_lift"])))
    L.append("Effective lift across all visitor groups: %.1f%%." % (100 * plan["effective_lift"]))
    if plan["visitors_needed_for_effective_lift"]:
        L.append("Visitors per arm a real test needs for that lift: %s." % format(plan["visitors_needed_for_effective_lift"], ","))
    for sc in plan["scenarios"]:
        L.append("Test %s: %s visitors per arm." % (sc["name"], format(sc["visitors_per_arm"], ",")))
    return "\n".join(L)


def _nums(text):
    return {n.rstrip(".,%") for n in re.findall(r"\d[\d,]*\.?\d*%?", text)}


def template_text(plan):
    t = next(s for s in plan["segments"] if s["role"] == "targeted")
    return ("The simulated visitors are %s and the other roles in the same industry. The %s makes up %.0f%% of visitors and reacts at full strength, "
            "because the variant was written for that buyer. Every other role reacts at half strength, scaled by how well the goal \"%s\" fits that role. "
            "The lift is not typed in. It is set from the judges' average gain on the gaps this variant targets (%+.2f), by a fixed rule. "
            "The base click rate is an assumption." % (plan["persona"], t["name"], 100 * t["weight"], plan["goal"]["label"], plan["avg_gain"]))


def narrate(plan, llm):
    """Reasoning-model explanation in plain English. Falls back to the template if a number is not in the plan."""
    F = facts(plan)
    prompt = ("=== TASK ===\nExplain in 110 to 160 plain English words, for a marketer who knows no statistics, how this synthetic A/B simulation was set up "
              "for THIS buyer and THIS goal. Cover: who the simulated visitors are and why the targeted buyer reacts most; how the goal fit changes each group's "
              "reaction; how the lift was set from the judges' scores (and that it is an assumption, not a finding); what is counted (a click on the main button). "
              "Use ONLY the facts below. Write no number that is not in the facts. No headings, no lists.\n\nFACTS:\n" + F)
    try:
        r = llm.chat([{"role": "user", "content": prompt}], role="reasoning", max_tokens=3000, temperature=0.2, purpose="sandbox plan explanation")
        text = r["text"].strip()
        if _nums(text) <= _nums(F) | {"1", "2", "3"} and len(text.split()) > 40:
            return text, "reasoning model"
    except Exception as e:  # prose is a nicety; the numbers come from code
        print("sandbox plan explanation: model call failed (%s); using the template" % e)
    return template_text(plan), "template (the model's text used a number outside the plan, or the call failed)"

#!/usr/bin/env python3
"""PROBE v2 (not the final engine): one pass of steps 4, 7 and 8 on a page hero.
v2 fixes found in v1: claim map per fragment, no scores in the writer prompt, Gate 1 absolute-word and qualifier rules, locked CTA on both arms.
Audit the baseline hero with Jev, let the writer draft variants from allowed claims,
run lite Gate 1 (rules), run Gate 2 with both judges, and compare each variant with the baseline.
All pass lines are PROVISIONAL (0.5). Calibration (S4) has not been done.
Run: python3 -I agent/probe.py --page token-factory"""
import argparse
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import llm  # noqa: E402

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROVISIONAL = 0.5


def fm(path):
    """Tiny front-matter reader: returns (dict, body)."""
    txt = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, re.S)
    d = {}
    if m:
        for line in m.group(1).split("\n"):
            if ":" in line and not line.startswith(" "):
                k, v = line.split(":", 1)
                d[k.strip()] = v.strip().strip('"')
        return d, m.group(2)
    return d, txt


def load_page(page):
    base = os.path.join(PROJECT, "pages", page)
    cap = json.load(open(os.path.join(base, "capture", sorted(os.listdir(os.path.join(base, "capture")))[-1], "capture.json")))
    hero = next(b for b in cap["blocks"] if b["kind"] == "hero")
    lines = hero["lines"]
    h1 = next(l["text"] for l in lines if l.get("role") == "heading")
    sub = next(l["text"] for l in lines if l.get("role") not in ("heading", "cta", "button", "link") and l["text"] != h1)
    ctas = [l["text"] for l in lines if l.get("role") in ("cta", "button", "link")]
    claims, evidence = {}, {}
    for f in sorted(os.listdir(os.path.join(base, "claims"))):
        if f.startswith("cl-"):
            d, _ = fm(os.path.join(base, "claims", f))
            claims[d["id"]] = d
    for f in sorted(os.listdir(os.path.join(base, "evidence"))):
        if f.startswith("ev-"):
            d, _ = fm(os.path.join(base, "evidence", f))
            evidence[d["id"]] = d
    banned = re.findall(r"^- BAN: (.+)$", open(os.path.join(base, "decisions", "do-not-claim.md"), encoding="utf-8").read(), re.M)
    prof = json.load(open(os.path.join(base, "profile.json")))
    hero_cfg = prof["hero"]
    _, chk = fm(os.path.join(base, hero_cfg["checklist_file"]))
    items = re.search(r"## Questions the page must answer\n\n(.*?)\n\n##", chk, re.S).group(1)
    items = [re.sub(r"^- ", "", l).rstrip("?") for l in items.split("\n") if l.startswith("- ")]
    ctx = open(os.path.join(base, "context-pack.md"), encoding="utf-8").read()
    promise = re.search(r'Promise, exact words: "(.+?)"', ctx).group(1)
    import csv
    rivals = []
    for r in csv.DictReader(open([os.path.join(base, "research", f) for f in os.listdir(os.path.join(base, "research")) if f.startswith("rival-claims")][0], encoding="utf-8")):
        rivals.append("%s: %s. %s" % (r["rival"], r["headline"], r["subheadline"]))
    brief = json.load(open(os.path.join(base, "brief.json")))
    return dict(h1=h1, sub=sub, ctas=ctas, claims=claims, evidence=evidence, banned=banned, items=items,
                promise=promise, rivals=rivals[:hero_cfg["rival_count"]], brief=brief, base=base, hero=hero_cfg)


def hero_state(h1, sub, cta):
    return ["HERO HEADLINE (H1): " + h1, "HERO SUB-LINE: " + sub, "HERO MAIN BUTTON: " + cta]


def audit_questions(Q, items):
    qs = {}
    for q in Q["audit"]["questions"]:
        if q.get("repeat_for"):
            for i, it in enumerate(items):
                qs["%s-%d" % (q["id"], i + 1)] = q["text"].replace("{item}", it)
        else:
            qs[q["id"]] = q["text"]
    return qs


def p(a, k):
    v = a["answers"][k]["p"]
    return -1.0 if v is None else v


def good(qid, prob):
    """Pass test with polarity. Provisional line 0.5."""
    return prob < PROVISIONAL if qid.startswith("A6") or qid.startswith("G2") or qid.startswith("G3") else prob >= PROVISIONAL


def parse_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0))


def main():
    import gate1
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default="token-factory")
    args = ap.parse_args()
    D = load_page(args.page)
    Q = json.load(open(os.path.join(PROJECT, "rules", "judge-questions.json")))
    GP = json.load(open(os.path.join(PROJECT, "rules", "gap-prose.json")))
    run = os.path.join(D["base"], "runs", "probe2-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(run)
    llm.LOG_PATH = os.path.join(run, "run-log.jsonl")
    out = {"label": "PROBE v2, provisional pass line %.2f, uncalibrated" % PROVISIONAL, "roles": llm.roles()}
    locked_cta = D["brief"]["main_cta"]
    real_cta = D["hero"]["baseline_main_cta"]
    buyer = "BUYER: " + D["brief"]["first_buyer"]["role"] + " at a GCC or IT services firm"
    posit = "POSITIONING PROMISE: " + D["promise"]
    print("BASELINE HERO (live)\n  H1 :", D["h1"], "\n  SUB:", D["sub"], "\n  CTAs:", D["ctas"])

    aq = audit_questions(Q, D["items"])
    a_base = llm.decide("judge1", [buyer, posit] + hero_state(D["h1"], D["sub"], real_cta), aq, "audit baseline (live CTA)")
    out["audit"] = {"model": a_base["model"], "p": {k: a_base["answers"][k]["p"] for k in aq}}
    req = ["A2-value", "A3-proof", "A4-cta", "A1-audience"]
    fails = sorted([(p(a_base, k), k) for k in req if not good(k, p(a_base, k))])
    items_p = sorted([(p(a_base, k), k, D["items"][int(k.split("-")[-1]) - 1]) for k in aq if k.startswith("A7")])
    print("\nAUDIT (Jev, provisional line 0.50)")
    for k in aq:
        print("  %-20s p=%.2f %s" % (k, p(a_base, k), "" if good(k, p(a_base, k)) else "<-- below line"))
    print("GAP?", "YES: " + ", ".join(k for _, k in fails) if fails else "NO required failure")
    if not fails:
        out["stopped"] = "no gap"
        json.dump(out, open(os.path.join(run, "probe.json"), "w"), indent=1)
        return
    targeted = [k for _, k in fails] + [items_p[0][1]]
    miss = items_p[0][2]

    allowed = [D["claims"][c] for c in D["hero"]["claim_ids"] if c in D["claims"]]
    claim_txt = "\n".join("- %s [%s]: %s (evidence quote: %s)" % (c["id"], c["label"], c["text"],
                          "; ".join(D["evidence"][e]["quote"] for e in re.findall(r"EV-\d+", c["evidence_ids"]) if D["evidence"].get(e, {}).get("quote"))[:400]) for c in allowed)
    gap_txt = "\n".join("- " + GP[k] for _, k in fails if k in GP)
    base_for_compare = hero_state(D["h1"], D["sub"], locked_cta)
    prompt = f"""You write hero copy for a Sarvam product page. The reader is: {D['brief']['first_buyer']['role']} at a GCC or IT services firm.
BASELINE HERO
H1: {D['h1']}
Sub-line: {D['sub']}

WHAT IS WRONG WITH IT
{gap_txt}
The buyer asks: "{miss}"

POSITIONING PROMISE (use its idea, not necessarily its words): {D['promise']}
The main button text is fixed: "{locked_cta}". After the click the buyer gets this: {D['brief']['offer_after_click']}

YOU MAY ONLY USE THESE CLAIMS. Keep every condition a claim states, such as "on request" or "agreed by contract". Do not add any number, name, comparison or guarantee. Do not use "never", "always", "all", "every" or "guaranteed" unless the claim uses that word.
{claim_txt}

NEVER USE these banned claims, even in other words: {'; '.join(D['banned'])}
Plain English. Short sentences. No filler such as seamless, robust, cutting-edge. The H1 must be at most 14 words.

Write 2 different variants of H1 and sub-line. Every sentence must be covered by a fragment in "map" with the claim id it relies on. A fragment is copied exactly from your H1 or sub-line. Reply with JSON only:
{{"variants":[{{"name":"A","h1":"...","subline":"...","cta":"{locked_cta}","map":[{{"fragment":"exact text","claim":"CL-001"}}],"why":"one sentence"}},{{"name":"B", ...}}]}}"""
    baseline_texts = [D["h1"], D["sub"]]
    print("\nWRITER (%s) drafting..." % llm.roles()["writer"])
    messages = [{"role": "user", "content": prompt}]
    variants, rounds = None, []
    for rnd in range(3):
        w = llm.chat(messages, max_tokens=2200, temperature=0.5, purpose="variants round %d" % (rnd + 1))
        for attempt in range(3):   # the writer sometimes returns broken JSON: ask it to repair, never crash
            try:
                variants = parse_json(w["text"])["variants"]
                break
            except (ValueError, KeyError, AttributeError) as e:
                print("  writer JSON problem (%s). Asking for a repair." % str(e)[:60])
                if attempt == 2:
                    raise SystemExit("writer could not return valid JSON in 3 tries")
                messages = messages + [{"role": "assistant", "content": w["text"]}, {"role": "user", "content": "That was not valid JSON (%s). Return the complete JSON again. Escape any double quote inside a string." % str(e)[:80]}]
                w = llm.chat(messages, max_tokens=2200, temperature=0.2, purpose="json repair")
        probs = {v["name"]: gate1.check(v, D["claims"], D["evidence"], D["banned"], locked_cta, baseline_texts, D["hero"].get("claim_qualifiers", [])) for v in variants}
        rounds.append({"round": rnd + 1, "gate1": probs})
        print("  round %d Gate 1: %s" % (rnd + 1, {k: (len(v) or "ok") for k, v in probs.items()}))
        bad = {k: v for k, v in probs.items() if v}
        if not bad or rnd == 2:
            break
        # send back only the failed rule names, never judge scores
        fb = "\n".join("Variant %s failed Gate 1: %s" % (k, "; ".join(v)) for k, v in bad.items())
        messages = messages + [{"role": "assistant", "content": w["text"]}, {"role": "user", "content": "Gate 1 rejected some lines. Fix only what failed and return the full JSON again.\n" + fb}]
    out["writer"] = {"model": w["model"], "rounds": rounds}
    out["variants"] = variants

    gq = {g["id"]: g["text"] for g in Q["gate2"]["questions"]}
    results = {}
    for v in variants:
        res = {"gate1_problems": gate1.check(v, D["claims"], D["evidence"], D["banned"], locked_cta, baseline_texts, D["hero"].get("claim_qualifiers", []))}
        for role in ("judge1", "judge2"):
            r = {"fragments": []}
            for m in v.get("map", []):
                cid = m["claim"]
                if cid not in D["claims"]:
                    continue
                evq = " | ".join(D["evidence"][e]["quote"] for e in re.findall(r"EV-\d+", D["claims"][cid]["evidence_ids"]) if D["evidence"].get(e, {}).get("quote"))
                st = ["FRAGMENT: " + m["fragment"], "CLAIM %s: %s" % (cid, D["claims"][cid]["text"]), "EVIDENCE QUOTE: " + evq]
                a = llm.decide(role, st, {"G1-support": gq["G1-support"], "G2-overreach": gq["G2-overreach"]}, "gate2 fragment %s %s" % (cid, v["name"]))
                r["fragments"].append({"fragment": m["fragment"], "claim": cid, "support": p(a, "G1-support"), "overreach": p(a, "G2-overreach")})
            st = hero_state(v["h1"], v["subline"], v["cta"]) + ["DO-NOT-CLAIM LIST: " + "; ".join(D["banned"]), buyer, "BUYER QUESTION THE HERO MUST ANSWER: " + miss]
            a = llm.decide(role, st, {"G3-banned": gq["G3-banned"], "G5-buyer": gq["G5-buyer"]}, "gate2 banned/buyer " + v["name"])
            r["G3-banned"], r["G5-buyer"] = p(a, "G3-banned"), p(a, "G5-buyer")
            av = llm.decide(role, [buyer, posit] + hero_state(v["h1"], v["subline"], v["cta"]), aq, "audit variant %s" % v["name"])
            ab = llm.decide(role, [buyer, posit] + base_for_compare, aq, "audit baseline with locked CTA (%s)" % role)
            r["audit_variant"] = {k: p(av, k) for k in aq}
            r["audit_baseline"] = {k: p(ab, k) for k in aq}
            res[role] = r
        results[v["name"]] = res
    out["gate2"] = results

    def delta(r, k):
        d = r["audit_variant"][k] - r["audit_baseline"][k]
        return -d if k.startswith("A6") else d   # A6 is bad-when-high: flip the sign so + is always better
    print("\nVARIANTS (baseline arm carries the locked CTA '%s', so only words differ)" % locked_cta)
    summary = {}
    for v in variants:
        res = results[v["name"]]
        print("\n--- Variant %s ---\n  H1 : %s\n  SUB: %s\n  CTA: %s\n  why: %s" % (v["name"], v["h1"], v["subline"], v["cta"], v.get("why")))
        print("  Gate 1 problems:", res["gate1_problems"] or "none")
        verdict = {"gate1": not res["gate1_problems"]}
        for role in ("judge1", "judge2"):
            r = res[role]
            frag_ok = all(f["support"] >= PROVISIONAL and f["overreach"] < PROVISIONAL for f in r["fragments"])
            print("  %s fragments:" % role)
            for f in r["fragments"]:
                print("     %-4s support %.2f  overreach %.2f  | %s" % (f["claim"], f["support"], f["overreach"], f["fragment"][:70]))
            safe = frag_ok and r["G3-banned"] < PROVISIONAL
            tg = {k: round(delta(r, k), 2) for k in targeted}
            held = {k: round(delta(r, k), 2) for k in aq if k not in targeted}
            lead_gain = delta(r, items_p[0][1])
            better = lead_gain >= Q["gate2"]["better_than_baseline"]["min_gain"] and all(x >= -Q["gate2"]["better_than_baseline"]["max_drop"] for x in held.values())
            verdict[role] = {"safe": safe, "better": better, "targeted_delta": tg, "heldout_delta": held, "G3": r["G3-banned"], "G5": r["G5-buyer"]}
            print("    banned %.2f | answers buyer question %.2f | safe=%s" % (r["G3-banned"], r["G5-buyer"], safe))
            print("    targeted deltas %s\n    held-out deltas %s -> better=%s" % (tg, held, better))
        verdict["pass_both"] = all([verdict["gate1"], verdict["judge1"]["safe"], verdict["judge2"]["safe"], verdict["judge1"]["better"], verdict["judge2"]["better"]])
        verdict["judges_disagree"] = verdict["judge1"]["safe"] != verdict["judge2"]["safe"] or verdict["judge1"]["better"] != verdict["judge2"]["better"]
        summary[v["name"]] = verdict
        print("  => pass Gate 1 + both judges + better than baseline:", verdict["pass_both"], "| judges disagree:", verdict["judges_disagree"])
    out["summary"] = summary
    json.dump(out, open(os.path.join(run, "probe.json"), "w"), indent=1, ensure_ascii=False)
    cost = sum((json.loads(l).get("cost") or 0) for l in open(os.path.join(run, "run-log.jsonl")))
    print("\nrun folder:", os.path.relpath(run, PROJECT), "| total cost about $%.4f" % cost)


if __name__ == "__main__":
    main()

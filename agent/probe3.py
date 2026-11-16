#!/usr/bin/env python3
"""PROBE v3 on the LIVE baseline. Not the final engine (no approval page, no sandbox yet).
Steps: live hero capture (read) -> Jev audit with calibrated lines -> gap dossier (writer + skills)
-> writer draft pass (skills) -> edit pass (skills) -> Gate 1 rules loop -> Gate 2 (Jev + Judge 2,
calibrated lines) -> baseline vs variant PNG pairs from one live load.
Run: python3 agent/probe3.py --page <slug> --persona <industry:role> --goal <goal id>   (needs Playwright for the PNG step)
The page setup (positioning, claims) must be approved in the console first; the persona checklist enables A7 and A8."""
import argparse
import csv
import datetime
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate1  # noqa: E402
import judgekit as jk  # noqa: E402
import llm  # noqa: E402
import skills as skl  # noqa: E402
import shortlist  # noqa: E402
import page_setup as setup  # noqa: E402
import destinations  # noqa: E402

PROJECT = jk.PROJECT


def band_text(b):
    """The calibrated band for one judge question, as shown in the dossier table."""
    if not b:
        return "no band (advisory)"
    adv = ", advisory" if b.get("advisory") else ""
    if b.get("polarity") == "bad":
        return "flag at %.2f, clean at %.2f%s" % (b["flag_at"], b["clean_at"], adv)
    return "pass at %.2f, fail at %.2f%s" % (b["pass_at"], b["fail_at"], adv)


def fm(path):
    txt = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, re.S)
    d = {}
    for line in (m.group(1) if m else "").split("\n"):
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            d[k.strip()] = v.strip().strip('"')
    return d, (m.group(2) if m else txt)


def load(page, persona_key, goal_id):
    """Everything one run needs, from the page folder and its approved setup. No page names in this code."""
    base = os.path.join(PROJECT, "pages", page)
    prof = json.load(open(os.path.join(base, "profile.json")))
    st = setup.status(page, persona_key)
    if not st["ready"]:
        sys.exit("SETUP NOT APPROVED for %s: %s. Approve the positioning and claims in the console (Page setup)." % (page, st["parts"]))
    p = setup.persona(persona_key)
    if not p:
        sys.exit("unknown persona: %s" % persona_key)
    goals = {g["id"]: g for g in destinations.goals_for(page)}
    g = goals.get(goal_id)
    if not g or not g["available"]:
        sys.exit("goal %s has no real destination on this page" % goal_id)
    live = sorted(glob.glob(os.path.join(base, "capture", "*-live", "hero.json")))[-1]
    hero = json.load(open(live))
    main = next(c for c in hero["ctas"] if c.get("href"))
    all_dests = destinations.page_destinations(page)
    base_dest = next((d for d in all_dests.values() if d["url"] == main["href"]), None) or \
        {"id": "live", "url": main["href"], "live_label": main["text"], "what_it_is": "The live button's link. What the visitor sees there is not checked."}
    dests = {g["kind"]: dict(g["destination"], id=g["kind"])}          # the goal decides where the variant's button goes
    claims = {fm(f)[0]["id"]: fm(f)[0] for f in glob.glob(os.path.join(base, "claims", "cl-*.md"))}
    ev = {fm(f)[0]["id"]: fm(f)[0] for f in glob.glob(os.path.join(base, "evidence", "ev-*.md"))}
    own_dnc = os.path.join(base, "decisions", "do-not-claim.md")
    dnc = own_dnc if os.path.isfile(own_dnc) else os.path.join(PROJECT, "rules", "do-not-claim.md")
    banned = re.findall(r"^- BAN: (.+)$", open(dnc, encoding="utf-8").read(), re.M)
    cfg = dict(json.load(open(os.path.join(PROJECT, "rules", "hero-policy.json"))))
    cfg.update(prof.get("hero") or {})
    cfg["claim_ids"] = [c for c in (cfg.get("claim_ids") or sorted(claims)) if c in claims]
    items, items_page, objection = [], [], ""
    cf = setup.checklist_file(page, persona_key)
    if cf:
        chk_meta, chk = fm(cf)
        block = re.search(r"## Questions the page must answer\n\n(.*?)\n\n##", chk, re.S).group(1)
        tagged = re.findall(r"^- \[(hero|page)\] (.+?)\??$", block, re.M)
        untagged = [l for l in block.split("\n") if l.startswith("- ") and not re.match(r"^- \[(hero|page)\] ", l)]
        if untagged:
            sys.exit("checklist items need a [hero] or [page] tag: %s" % untagged)
        items = [q for t, q in tagged if t == "hero"]
        items_page = [q for t, q in tagged if t == "page"]
        objection = chk_meta.get("main_objection", "")
    q_approved = st["questions_ready"]
    ap = [e for e in setup.approvals(page)["entries"] if e["part"] == "checklist:" + persona_key]
    _, promise = setup.positioning_file(page)
    rivals = []
    rf = glob.glob(os.path.join(base, "research", "rival-claims-*.csv"))
    if rf:
        rivals = ["%s: %s. %s" % (r["rival"], r["headline"], r["subheadline"]) for r in csv.DictReader(open(rf[0], encoding="utf-8"))][:cfg.get("rival_count", 6)]
    return dict(base=base, prof=prof, cfg=cfg, hero=hero, live_path=live, cta=main["text"], cta_dest=base_dest, main_index=main["index"],
                dests=dests, goal=g, persona=p, persona_key=persona_key, buyer=setup.buyer_text(p),
                claims=claims, ev=ev, banned=banned, items=items, items_page=items_page,
                objection=objection, q_approved=q_approved,
                q_approval=(ap[-1]["name"], ap[-1]["at"]) if (q_approved and ap) else ("", ""),
                promise=promise, rivals=rivals)


def quote_of(D, cid):
    return " | ".join(D["ev"][e]["quote"] for e in re.findall(r"EV-\d+", D["claims"][cid]["evidence_ids"]) if D["ev"].get(e, {}).get("quote"))


def audit(D, role, h1, sub, cta, dest_txt, aq, purpose):
    st = jk.context_state(D["buyer"], D["promise"]) + jk.hero_state(h1, sub, cta, dest_txt) + (["RIVAL HEROES: " + " || ".join(D["rivals"])] if D["rivals"] else [])
    r = llm.decide(role, st, aq, purpose)
    return {k: r["answers"][k]["p"] for k in aq}


def audit_questions(D, Q):
    """The audit questions for this page and buyer: A1 to A6, plus A7 and A8 once the buyer checklist is approved."""
    aq, skipped = {}, []
    for qd in Q["audit"]["questions"]:
        if qd["id"] == "A6-swap" and not D["rivals"]:
            skipped.append("A6-swap (no rival heroes saved for this page)")
            continue
        if qd.get("fill") and not D["q_approved"]:
            skipped.append(qd["id"])   # page-specific questions wait for a person to approve them
            continue
        if qd.get("fill") == "item":
            for i, it in enumerate(D["items"]):
                aq["%s-%d" % (qd["id"], i + 1)] = qd["text"].replace("{item}", it)
        elif qd.get("fill") == "objection":
            if D["objection"]:
                aq[qd["id"]] = qd["text"].replace("{objection}", D["objection"].rstrip("."))
        else:
            aq[qd["id"]] = qd["text"]
    return aq, skipped


def gate2_score(D, v, aq, th, Q, g2_q, a_base, a_base2, targeted):
    """Gate 2 for one variant: both judges, the same rules for a first draft and for a person's edit."""
    dtxt = D["dests"][v["cta_destination"]]["what_it_is"]
    r = {}
    for role in ("judge1", "judge2"):
        fr = []
        for m in v["map"]:
            a = llm.decide(role, jk.fragment_state(m["fragment"], m["claim"], D["claims"][m["claim"]]["text"], quote_of(D, m["claim"])),
                           {k: g2_q[k]["text"] for k in ("G1-support", "G2-overreach")}, "gate2 %s %s" % (v["name"], m["claim"]))
            ps = {k: a["answers"][k]["p"] for k in ("G1-support", "G2-overreach")}
            fr.append({"fragment": m["fragment"], "claim": m["claim"], "p": ps, "verdict": {k: jk.verdict(th, role, k, p) for k, p in ps.items()}})
        b = llm.decide(role, ["HERO TEXT: " + jk.norm(v["h1"] + " " + v["subline"]), "DO-NOT-CLAIM LIST: " + "; ".join(D["banned"])],
                       {"G3-banned": g2_q["G3-banned"]["text"]}, "gate2 banned " + v["name"])
        pb = b["answers"]["G3-banned"]["p"]
        av = audit(D, role, v["h1"], v["subline"], v["cta"], dtxt, aq, "audit variant %s" % v["name"])
        ab = a_base if role == "judge1" else a_base2
        sign = lambda k: -1 if jk.is_bad(k) else 1
        delta = {k: round(sign(k) * (av[k] - ab[k]), 2) for k in aq}
        held = [k for k in aq if k not in targeted]
        hard_fail = [f for f in fr if f["verdict"]["G2-overreach"] == "fail"] + ([1] if jk.verdict(th, role, "G3-banned", pb) == "fail" else [])
        rule = Q["gate2"]["better_than_baseline"]
        better = sum(delta[k] for k in targeted) / len(targeted) >= rule["min_gain"] and all(delta[k] >= -rule["max_drop"] for k in held)
        r[role] = {"fragments": fr, "G3": pb, "G3_verdict": jk.verdict(th, role, "G3-banned", pb), "audit_variant": av, "audit_baseline": ab,
                   "delta": delta, "targeted": targeted, "held_out": held, "better": better, "hard_fail": bool(hard_fail),
                   "variant_verdicts": {k: jk.verdict(th, role, k, p) for k, p in av.items()}}
    r["pass"] = not r["judge1"]["hard_fail"] and not r["judge2"]["hard_fail"] and r["judge1"]["better"] and r["judge2"]["better"]
    r["disagree"] = r["judge1"]["better"] != r["judge2"]["better"] or r["judge1"]["hard_fail"] != r["judge2"]["hard_fail"]
    return r


def parse_json(text):
    """Take the first complete JSON object in the reply. Tolerates code fences and prose before or after it."""
    t = re.sub(r"```(?:json)?", "", text or "")
    i = t.find("{")
    if i < 0:
        raise ValueError("no JSON object in the reply")
    obj, _ = json.JSONDecoder().raw_decode(t[i:])
    if not isinstance(obj, dict) or not isinstance(obj.get("variants"), list):
        raise ValueError("JSON has no 'variants' list")
    return obj


def ask_json(messages, purpose, max_tokens=3000):
    w = llm.chat(messages, max_tokens=max_tokens, temperature=0.5, purpose=purpose)
    for attempt in range(3):
        try:
            return parse_json(w["text"]), messages + [{"role": "assistant", "content": w["text"]}]
        except (ValueError, AttributeError) as e:
            if attempt == 2:
                if llm.LOG_PATH:
                    with open(os.path.join(os.path.dirname(llm.LOG_PATH), "writer-bad-reply.txt"), "w", encoding="utf-8") as f:
                        f.write(w["text"])
                raise SystemExit("writer could not return valid JSON in 3 tries (%s); last reply saved as writer-bad-reply.txt" % e)
            messages = messages + [{"role": "assistant", "content": w["text"]}, {"role": "user", "content": "Not valid JSON (%s). Return the complete JSON only." % str(e)[:80]}]
            w = llm.chat(messages, max_tokens=max_tokens, temperature=0.2, purpose=purpose + " json repair")


def rules_block(D):
    allowed = [D["claims"][c] for c in D["cfg"]["claim_ids"] if c in D["claims"]]
    claims = "\n".join("- %s [%s]: %s (evidence quote: %s)" % (c["id"], c["label"], c["text"], quote_of(D, c["id"])[:400]) for c in allowed)
    dests = "\n".join("- %s: %s (label on the live page: '%s')" % (d["id"], d["what_it_is"], d["live_label"]) for d in D["dests"].values())
    quals = "\n".join("- %s: %s" % (q["claim"], q["why"]) for q in D["cfg"].get("claim_qualifiers", []))
    return f"""=== HARD RULES. THESE OVERRIDE EVERY SKILL ABOVE. ===
1. Use ONLY these claims. Every sentence must rely on one. No testimonial, customer name, statistic, comparison, urgency or guarantee that is not in a claim.
{claims}
2. Keep every condition a claim states ("on request", "agreed by contract", "for enterprise deployments"). Per-claim conditions:
{quals}
3. Never use "never", "always", "all", "every", "any" or "guaranteed" unless the cited claim uses that word.
4. Banned, even in other words: {'; '.join(D['banned'])}. Also never: sovereign cloud, Sarvam Train, Epoch Builder Edition.
5. The main button must go to ONE of these real destinations, and its label must say what the visitor gets there:
{dests}
6. Never name a third-party model (DeepSeek, Qwen, Llama, Mistral, Gemma, Kimi, GLM). Sarvam is an India platform: speak in business terms. Never use these stretches: {', '.join(D['cfg']['stretch_phrases'])}.\n7. H1 at most 14 words. Sub-line at most 3 sentences. Button at most 5 words. Plain English.
8. Return a claim map: every sentence of H1 and sub-line is covered by a fragment copied EXACTLY from your text, with the claim id it relies on.
9. Write fresh hero copy in this buyer's words. Do NOT paste a claim sentence as the headline or sub-line: the claims are your facts, not your copy. The H1 says what the buyer gets; the sub-line backs it with one or two facts; the button says what happens next. Keep the positioning promise's idea."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", required=True)
    ap.add_argument("--persona", required=True, help="industry:role key from library/personas.json")
    ap.add_argument("--goal", required=True, help="goal id from rules/goals.json")
    ap.add_argument("--no-png", action="store_true")
    args = ap.parse_args()
    if os.environ.get("AGENT_HOSTED"):
        args.no_png = True   # the website never loads sarvam.ai: no screenshots there
    D = load(args.page, args.persona, args.goal)
    th = jk.thresholds()
    Q, audit_q, g2_q = jk.questions()
    run = os.path.join(D["base"], "runs", "probe3-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(run)
    llm.LOG_PATH = os.path.join(run, "run-log.jsonl")
    out = {"label": "PROBE v3 on the live baseline. Calibrated lines from rules/judge-thresholds.json (small self-written case set).",
           "roles": llm.roles(), "knowledge_version": __import__("knowledge").version(), "questions_version": Q.get("version", 1), "live_capture": os.path.relpath(D["live_path"], PROJECT), "skills": {},
           "page": args.page, "persona": {"key": D["persona_key"], "buyer": D["buyer"], "label": D["persona"]["label"]},
           "goal": {"id": D["goal"]["id"], "label": D["goal"]["label"], "kind": D["goal"]["kind"]},
           "destinations": D["dests"], "baseline_destination": D["cta_dest"], "main_cta_index": D["main_index"],
           "screenshots": "not taken (website run)" if os.environ.get("AGENT_HOSTED") else ("not taken (--no-png)" if args.no_png else "taken")}
    h1, sub, cta = D["hero"]["h1"], D["hero"]["sub"], D["cta"]
    base_dest_txt = D["cta_dest"]["what_it_is"] if D["cta_dest"] else "unknown"
    print("LIVE BASELINE\n  H1 : %s\n  SUB: %s\n  BTN: %s -> %s" % (h1, sub, cta, base_dest_txt))

    # 4 audit (Jev only)
    aq, skipped = audit_questions(D, Q)
    out["page_questions"] = {"approved": D["q_approved"], "approved_by_on": D["q_approval"], "hero_items": D["items"],
                             "page_items_out_of_hero_scope": D["items_page"], "main_objection": D["objection"], "skipped": skipped}
    if skipped:
        late = [x for x in skipped if x.startswith(("A7", "A8"))]
        print("QUESTIONS SKIPPED: %s.%s" % (skipped, " Approve the buyer checklist in the console (Page setup) to ask A7 and A8." if late else ""))
    a_base = audit(D, "judge1", h1, sub, cta, base_dest_txt, aq, "audit live baseline")
    v_base = {k: jk.verdict(th, "judge1", k, p) for k, p in a_base.items()}
    req = ["A1-audience", "A2-value", "A3-proof", "A4-cta"]
    print("\nAUDIT (Jev, calibrated lines)")
    for k in aq:
        print("  %-20s p=%.2f  %s" % (k, a_base[k], v_base[k]))
    gaps = [k for k in req if v_base[k].endswith("fail")]
    unclear = [k for k in req if v_base[k].endswith("hold")]
    gaps = gaps + [k for k in unclear if k not in gaps]   # a hold on a required question is a possible gap: the writer works on it, the person sees it labelled
    items_fail = [k for k in aq if k.startswith("A7") and (v_base[k].endswith("fail") or v_base[k].endswith("hold"))]
    out["audit"] = {"p": a_base, "verdict": v_base, "gaps": gaps, "unclear": unclear}
    out["thresholds_used"] = th
    if not gaps:
        print("NO GAP on the required questions. Stop: nothing is written.", "Unclear:", unclear)
        json.dump(out, open(os.path.join(run, "probe3.json"), "w"), indent=1)
        __import__("run_flow").write(args.page, os.path.basename(run))
        return
    lead_item = sorted(items_fail, key=lambda k: a_base[k])[0] if items_fail else None
    lead_txt = D["items"][int(lead_item.split("-")[-1]) - 1] if lead_item else None
    obj_gap = "A8-objection" in v_base and (v_base["A8-objection"].endswith("fail") or v_base["A8-objection"].endswith("hold"))
    need_line = ('The buyer asks: "%s".' % lead_txt if lead_txt else "") + (' The buyer worries: "%s"' % D["objection"] if obj_gap else "")
    kept_items = [D["items"][int(k.split("-")[-1]) - 1] for k in aq if k.startswith("A7") and v_base[k].endswith("pass")]
    keep_line = (' KEEP: the live hero already answers these buyer questions, and the judges score them again on every variant. Every variant must still answer each one in the same plain terms: %s.' % "; ".join('"%s"' % t for t in kept_items)) if kept_items else ""
    need_line += keep_line
    out["audit"].update({"lead_item": lead_item, "lead_txt": lead_txt, "objection_gap": obj_gap})
    GP = json.load(open(os.path.join(PROJECT, "rules", "gap-prose.json")))
    print("GAP: %s | buyer question answered worst: %s" % (", ".join(gaps), lead_txt))

    # 5 gap dossier (writer + dossier skills). No numbers: code adds the table.
    sk, used = skl.load("dossier")
    out["skills"]["dossier"] = used
    dossier_prompt = sk + "\n\n=== TASK ===\nWrite the gap dossier for a reviewer. Explain WHY the hero has a gap for this buyer, in plain English, 150 to 250 words. " \
        "Cover: what the hero says now (quote it exactly), which buyer need it fails and why that matters to this buyer, what evidence we hold (cite claim ids), " \
        "the hypothesis in the form 'If we change X for buyer Y, more of them click the hero's main button, because E' (the variant writes a new button, so do not name the current button text in the hypothesis),what we do not know (we have no internal analytics, so the real click rate is unknown), " \
        "and what result would prove the hypothesis wrong. Quote the buyer question EXACTLY as given below; never paraphrase it in quotation marks and never invent a buyer quote. Do NOT write any number or percentage: the code adds the audit table. Do not name any third-party model. Do not invent facts.\n\n" \
        "BUYER: %s\nHERO H1: %s\nHERO SUB-LINE: %s\nHERO BUTTON: %s (goes to %s)\nFAILED NEEDS: %s\nBUYER QUESTION ANSWERED WORST: %s\nPOSITIONING PROMISE (PROPOSED, not buyer-validated): %s\nCLAIMS WE HOLD: %s" % (
            D["buyer"], h1, sub, cta, base_dest_txt, "; ".join(GP[k] for k in gaps), (lead_txt or "none asked (page questions not approved)") + (" | MAIN OBJECTION NOT ANSWERED: " + D["objection"] if obj_gap else ""), D["promise"],
            "; ".join("%s: %s" % (c, D["claims"][c]["text"]) for c in D["cfg"]["claim_ids"]))
    dz = llm.chat([{"role": "user", "content": dossier_prompt}], role="reasoning", max_tokens=4000, temperature=0.3, purpose="dossier")["text"].strip()
    allowed_digits = h1 + sub + " ".join(D["claims"][c]["text"] for c in D["cfg"]["claim_ids"])
    dz_ids = re.findall(r"(?:CL|EV)[-\u2011\u2010]\d+", dz)
    bad_ids = [i for i in dz_ids if re.sub(r"[\u2011\u2010]", "-", i) not in D["claims"] and re.sub(r"[\u2011\u2010]", "-", i) not in D["ev"]]
    bad_nums = [n for n in re.findall(r"\d[\d.,%]*", re.sub(r"(?:CL|EV)[-\u2011\u2010]\d+", "", dz)) if n.rstrip(".,") not in allowed_digits] + bad_ids
    srcs = [h1, sub, cta, D["promise"], D["objection"]] + D["items"] + D["items_page"] + [D["claims"][c]["text"] for c in D["cfg"]["claim_ids"]] + [GP[k] for k in GP]
    prose_problems = bad_nums + gate1.quote_issues(dz, srcs) + gate1.policy_issues(dz, D["cfg"])
    for attempt in range(2):
        if not prose_problems:
            break
        try:
            dz = llm.chat([{"role": "user", "content": dossier_prompt}, {"role": "assistant", "content": dz},
                           {"role": "user", "content": "The prose check rejected this: " + "; ".join(prose_problems) + ". Rewrite the dossier and fix only these problems."}],
                          role="reasoning", max_tokens=4000, temperature=0.2, purpose="dossier fix")["text"].strip()
        except llm.LLMError as e:   # the dossier is prose for a reader: keep the last draft, show the problems, do not stop the run
            print("  dossier fix failed (%s); keeping the last draft with its problems listed" % e)
            break
        bad_nums = [n for n in re.findall(r"\d[\d.,%]*", re.sub(r"(?:CL|EV)[-\u2011\u2010]\d+", "", dz)) if n.rstrip(".,") not in allowed_digits]
        prose_problems = bad_nums + gate1.quote_issues(dz, srcs) + gate1.policy_issues(dz, D["cfg"])
    out["dossier"] = {"text": dz, "prose_problems_left": prose_problems}
    print("\nDOSSIER (reasoning model, %d words). Prose check problems left: %s" % (len(dz.split()), prose_problems or "none"))

    # 7 writer: draft pass then edit pass, then Gate 1 loop
    rb = rules_block(D)
    sk_d, used_d = skl.load("writer_draft")
    sk_e, used_e = skl.load("writer_edit")
    out["skills"]["writer_draft"], out["skills"]["writer_edit"] = used_d, used_e
    task = f"""=== TASK ===
Write 3 hero variants (H1, sub-line, main button) for this page and buyer. Use the skills above to choose a strong angle; give each variant a DIFFERENT angle.
BUYER: {D['buyer']}
LIVE HERO: H1 "{h1}" / sub-line "{sub}" / button "{cta}" (goes to {base_dest_txt})
WHAT IS WRONG (from the audit): {' '.join(GP[k] for k in gaps)} {need_line}
POSITIONING PROMISE (approved by a person; it is not a claim): {D['promise']}
KEEP THE PROMISE: the judges score every variant on whether the hero carries this promise (question A5) and speaks to this buyer's situation (A1). Naming the buyer is not needed; describing their situation is. A variant that fixes the gaps but drops the promise fails Gate 2. Put the promise's core idea in the H1 or the first sub-line sentence, using only the parts of it that a claim backs.
Reply with JSON only:
{{"variants":[{{"name":"A","angle":"...","h1":"...","subline":"...","cta":"...","cta_destination":"one destination id","map":[{{"fragment":"exact text","claim":"CL-001"}}],"why":"one sentence"}}]}}"""
    draft, _ = ask_json([{"role": "user", "content": sk_d + "\n\n" + rb + "\n\n" + task}], "writer draft")
    print("\nWRITER draft pass: %d variants, angles: %s" % (len(draft["variants"]), [v.get("angle") for v in draft["variants"]]))
    edit_task = "=== TASK ===\nEdit these hero variants with the editing skills above: cut filler, make each line concrete and plain, keep each angle. " \
                "Do not add facts. Return the same JSON shape with a FRESH claim map whose fragments are copied exactly from the edited text.\n\nDRAFT:\n" + json.dumps(draft, ensure_ascii=False)
    msgs = [{"role": "user", "content": sk_e + "\n\n" + rb + "\n\n" + edit_task}]
    edited, msgs = ask_json(msgs, "writer edit")
    variants = edited["variants"]
    baseline_texts = [h1, sub]
    quals = D["cfg"].get("claim_qualifiers", [])
    rounds = []
    for rnd in range(2):
        probs = {v["name"]: gate1.check(v, D["claims"], D["ev"], D["banned"], list(D["dests"]), baseline_texts, quals, D["cfg"]) for v in variants}
        rounds.append(probs)
        print("  Gate 1 round %d: %s" % (rnd + 1, {k: (len(p) or "ok") for k, p in probs.items()}))
        bad = {k: p for k, p in probs.items() if p}
        if not bad or rnd == 1:
            break
        fb = "\n".join("Variant %s failed Gate 1: %s" % (k, "; ".join(p)) for k, p in bad.items())
        edited, msgs = ask_json(msgs + [{"role": "user", "content": "Gate 1 rejected some lines. Fix only what failed. Return the full JSON again.\n" + fb}], "writer gate1 fix")
        variants = edited["variants"]
    out["variants"], out["gate1_rounds"] = variants, rounds
    passed1 = [v for v in variants if not rounds[-1].get(v["name"])]

    # 8 Gate 2: both judges, calibrated lines. Variants are scored in parallel; the baseline is audited once per judge.
    res = {}
    a_base2 = audit(D, "judge2", h1, sub, cta, base_dest_txt, aq, "audit live baseline judge2") if passed1 else {}

    targeted = gaps + ([lead_item] if lead_item else []) + (["A8-objection"] if obj_gap else [])

    def score(v):
        return v["name"], gate2_score(D, v, aq, th, Q, g2_q, a_base, a_base2, targeted)

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max(1, len(passed1))) as ex:
        for name, r in ex.map(score, passed1):
            res[name] = r
    res = {v["name"]: res[v["name"]] for v in passed1}   # keep the variant order
    out["gate2"] = res

    print("\nVARIANTS")
    for v in variants:
        print("\n--- %s (%s) ---\n  H1 : %s\n  SUB: %s\n  BTN: %s -> %s" % (v["name"], v.get("angle"), v["h1"], v["subline"], v["cta"], v.get("cta_destination")))
        if rounds[-1].get(v["name"]):
            print("  Gate 1: FAILED %s" % rounds[-1][v["name"]])
            continue
        r = res[v["name"]]
        for role in ("judge1", "judge2"):
            x = r[role]
            print("  %s: overreach flags %s | banned %s | targeted %s | held-out %s | better=%s" % (
                role, [f["verdict"]["G2-overreach"] for f in x["fragments"]], x["G3_verdict"],
                {k: x["delta"][k] for k in x["targeted"]}, {k: x["delta"][k] for k in x["held_out"] if abs(x["delta"][k]) >= 0.05}, x["better"]))
        grp = {x["name"]: x["group"] for x in shortlist.classify({"variants": variants, "gate1_rounds": rounds, "gate2": res})}
        print("  => group: %s | judges disagree: %s" % (grp.get(v["name"]), r["disagree"]))

    # PNG pairs from one live load (read only, no clicks)
    if not args.no_png and passed1:
        from playwright.sync_api import sync_playwright
        clip = dict(D["hero"]["hero_clip"]); clip["height"] = min(clip["height"] + 220, 1400)
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            pg = br.new_page(viewport={"width": 1280, "height": 900})
            try:
                pg.goto(D["hero"]["url"], wait_until="networkidle", timeout=45000)
            except Exception:   # pages with live demos never go quiet: same single load, read once loaded
                pg.wait_for_load_state("load", timeout=30000)
                pg.wait_for_timeout(4000)
            pg.wait_for_timeout(1200)
            mark = """() => { const h1=[...document.querySelectorAll('h1')].find(e=>e.getBoundingClientRect().height>0); h1.setAttribute('data-hero','h1');
              let box=h1.parentElement; for(let i=0;i<6&&box;i++){ if([...box.querySelectorAll('a,button')].some(b=>b.innerText.trim())) break; box=box.parentElement;}
              const p=[...box.querySelectorAll('p')].find(p=>p.innerText.trim() && (h1.compareDocumentPosition(p)&4)); if(p) p.setAttribute('data-hero','sub');
              const a=[...box.querySelectorAll('a')].find(a=>a.innerText.trim()); if(a) a.setAttribute('data-hero','cta'); }"""
            pg.evaluate("""() => { document.querySelectorAll('body *').forEach(e => { const s = getComputedStyle(e);
                if ((s.position === 'fixed' || s.position === 'sticky') && /cookie|privacy|consent/i.test(e.innerText || '') && e.getBoundingClientRect().top > 200) e.style.display = 'none'; }); }""")
            pg.evaluate(mark)
            pg.screenshot(path=os.path.join(run, "hero-baseline.png"), clip=clip)
            for v in passed1:
                pg.evaluate("""(t) => { const set=(sel,txt)=>{const e=document.querySelector(sel); if(!e) return;
                    const walker=document.createTreeWalker(e,NodeFilter.SHOW_TEXT); let n, first=true; const nodes=[]; while(n=walker.nextNode()) if(n.nodeValue.trim()) nodes.push(n);
                    if(nodes.length){ nodes[0].nodeValue=txt; nodes.slice(1).forEach(x=>x.nodeValue=''); } else e.textContent=txt; };
                    set('[data-hero=h1]', t.h1); set('[data-hero=sub]', t.sub); set('[data-hero=cta]', t.cta); }""",
                            {"h1": v["h1"], "sub": v["subline"], "cta": v["cta"]})
                pg.wait_for_timeout(150)
                pg.screenshot(path=os.path.join(run, "hero-variant-%s.png" % v["name"]), clip=clip)
            # side-by-side sheets
            grp = {x["name"]: x["group"] for x in shortlist.classify({"variants": variants, "gate1_rounds": rounds, "gate2": res})}
            for v in passed1:
                r = res[v["name"]]
                html = """<html><body style="margin:0;font:14px system-ui;background:#f4f5f8;color:#1a1d26"><div style="padding:18px 22px">
                <div style="font-size:18px;font-weight:700">%s hero: baseline vs variant %s</div>
                <div style="color:#5b6472;margin:4px 0 14px">Buyer: %s. Goal: %s. Words and button both change (Decisions Log row 28). Group: %s. Judges disagree: %s.</div>
                <div style="display:flex;gap:16px"><div style="flex:1"><div style="font-weight:600;margin-bottom:6px">Baseline (live, captured %s)</div><img src="hero-baseline.png" style="width:100%%;border:1px solid #ccd"></div>
                <div style="flex:1"><div style="font-weight:600;margin-bottom:6px">Variant %s (%s)</div><img src="hero-variant-%s.png" style="width:100%%;border:1px solid #ccd"></div></div>
                <table style="margin-top:14px;border-collapse:collapse;background:#fff;width:100%%"><tr><th style="text-align:left;padding:6px;border:1px solid #dde">Part</th><th style="text-align:left;padding:6px;border:1px solid #dde">Baseline</th><th style="text-align:left;padding:6px;border:1px solid #dde">Variant</th></tr>
                <tr><td style="padding:6px;border:1px solid #dde">H1</td><td style="padding:6px;border:1px solid #dde">%s</td><td style="padding:6px;border:1px solid #dde">%s</td></tr>
                <tr><td style="padding:6px;border:1px solid #dde">Sub-line</td><td style="padding:6px;border:1px solid #dde">%s</td><td style="padding:6px;border:1px solid #dde">%s</td></tr>
                <tr><td style="padding:6px;border:1px solid #dde">Button</td><td style="padding:6px;border:1px solid #dde">%s</td><td style="padding:6px;border:1px solid #dde">%s (goes to: %s)</td></tr></table>
                </div></body></html>""" % (D["prof"].get("name") or args.page, v["name"], D["buyer"], D["goal"]["label"], grp.get(v["name"]), r["disagree"], D["hero"].get("captured_at", "")[:10], v["name"], v.get("angle", ""), v["name"], h1, v["h1"], sub, v["subline"], cta, v["cta"], v["cta_destination"])
                hp = os.path.join(run, "pair-%s.html" % v["name"])
                open(hp, "w", encoding="utf-8").write(html)
                p2 = br.new_page(viewport={"width": 1600, "height": 900})
                p2.goto("file://" + hp)
                p2.wait_for_timeout(300)
                p2.screenshot(path=os.path.join(run, "pair-%s.png" % v["name"]), full_page=True)
                p2.close()
            br.close()
        print("\nPNG pairs:", [os.path.relpath(os.path.join(run, "pair-%s.png" % v["name"]), PROJECT) for v in passed1])

    open(os.path.join(run, "GAP-DOSSIER.md"), "w", encoding="utf-8").write(
        "# Gap dossier (PROBE)\n\n" + dz + "\n\n## Audit method\n\n| Question | Asked | Jev probability | Calibrated band | Result |\n|---|---|---|---|---|\n" +
        "\n".join("| %s | %s | %.2f | %s | %s |" % (k, aq[k].replace("|", "/"), a_base[k],
                  band_text(th["judges"]["judge1"].get("A7-checklist-item" if k.startswith("A7") else k)), v_base[k]) for k in aq) +
        "\n\nPage questions: " + ("approved by %s on %s" % D["q_approval"] if D["q_approved"] else "NOT approved by a person in the console, so the buyer-checklist questions (A7) and the main-objection question (A8) were not asked") + ". Out of hero scope (the page body must answer these): " + ("; ".join(D["items_page"]) or "none") + "." +
        "\n\nHow to read the band: a good-direction question passes at or above the pass line and fails at or below the fail line; between the two it is held for a person. A bad-direction question (A6) flags at or above the flag line. 'Advisory' means the calibration cases did not separate cleanly, so the result informs but never blocks." +
        "\n\nLimits: Jev and Judge 2 are general decision models. We did not train or fine-tune either one for this program. The pass lines come from a small set of examples that we wrote. The probabilities are an audit signal, not an assurance. A person makes every approval.\n")
    out["shortlist"] = shortlist.classify(out)
    print("\nAPPROVAL GROUPS (Decisions Log rows 33, 34)")
    for x in out["shortlist"]:
        print("  %-13s %s  %s" % (x["group"], x["name"], " ".join(x["reasons"])))
    out["cost_usd"] = round(llm.SPENT["usd"], 4)
    out["calls"] = llm.SPENT["calls"]
    json.dump(out, open(os.path.join(run, "probe3.json"), "w"), indent=1, ensure_ascii=False)
    __import__("run_flow").write(args.page, os.path.basename(run))   # this run's diagram, same steps as the architecture
    print("\nrun folder: %s | %d calls | cost $%.4f" % (os.path.relpath(run, PROJECT), llm.SPENT["calls"], llm.SPENT["usd"]))


if __name__ == "__main__":
    main()

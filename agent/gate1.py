#!/usr/bin/env python3
"""Gate 1: rule checks on a variant. No model. Same answer every time.

A variant is {"h1", "subline", "cta", "map": [{"fragment", "claim"}]}.
Checks: claim ids exist; every sentence is mapped or is baseline text; no banned phrase;
no new number; no absolute word the claim does not use; qualifiers kept; the button goes to a real
destination; length limits (H1 14 words, sub-line 3 sentences, button 5 words).
Self test: python3 -I agent/gate1.py --selftest
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(os.path.dirname(HERE), "rules")


def _rules(name):
    return json.load(open(os.path.join(RULES, name), encoding="utf-8"))


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def claim_source(cid, claims, evidence):
    c = claims.get(cid)
    if not c:
        return ""
    ev = " ".join(evidence.get(e, {}).get("quote", "") for e in re.findall(r"EV-\d+", c.get("evidence_ids", "")))
    return (c.get("text", "") + " " + ev).lower()


def policy_issues(text, policy):
    """Page policy: no third-party model names (row 30) and no stretch phrases from the claims' 'Do not stretch it' notes."""
    out, low = [], " " + (text or "").lower() + " "
    pol = policy or {}
    if pol.get("no_third_party_model_names"):
        for w in pol.get("model_name_words", []):
            if re.search(r"\b%s\b" % re.escape(w), low):
                out.append("names a third-party model ('%s'): not allowed in the hero" % w)
    for ph in pol.get("stretch_phrases", []):
        if ph.lower() in low:
            out.append("stretch phrase '%s' goes beyond what the claims allow" % ph)
    return out


def quote_issues(text, sources):
    """Every quoted passage in prose must be copied exactly from a source text (hero, claims, checklist, promise)."""
    norm = lambda s: re.sub(r"\s+", " ", s.replace("\u2019", "'").replace("\u2011", "-")).strip().lower()
    pool = norm(" || ".join(sources))
    bad = []
    for q in re.findall(r"[\u201c\"]([^\u201d\"]{6,})[\u201d\"]", text or ""):
        if norm(q).rstrip(".?") not in pool:
            bad.append("quoted text not found in any source: '%s'" % q[:70])
    return bad


def check(variant, claims, evidence, banned, destinations, baseline_texts, claim_qualifiers=(), policy=None):
    """destinations: the allowed button destination ids (profile.hero.cta_destinations). Row 28: the writer picks the button."""
    """Return a list of problem strings. An empty list means the variant passes Gate 1."""
    problems = []
    absolute = _rules("absolute-words.json")["absolute_words"]
    quals = _rules("qualifiers.json")["qualifiers"]
    h1, sub = variant["h1"], variant["subline"]
    full = (h1 + " " + sub).lower()
    for ph in banned + ["Sarvam Train", "Epoch Builder Edition", "sovereign cloud"]:
        if ph.lower() in full:
            problems.append("banned phrase: " + ph)
    if not (variant.get("cta") or "").strip():
        problems.append("no button label")
    if variant.get("cta_destination") not in destinations:
        problems.append("button destination '%s' is not a real destination on the page" % variant.get("cta_destination"))
    if len((variant.get("cta") or "").split()) > 5:
        problems.append("button label is longer than 5 words")
    if len(h1.split()) > 14:
        problems.append("H1 is longer than 14 words")
    if len(sentences(sub)) > 3:
        problems.append("sub-line has more than 3 sentences")
    problems += policy_issues(h1 + " " + sub + " " + (variant.get("cta") or ""), policy)
    cmap = variant.get("map") or []
    if not cmap:
        problems.append("no claim map")
    for m in cmap:
        frag, cid = m.get("fragment", ""), m.get("claim", "")
        if cid not in claims:
            problems.append("claim id does not exist: %s" % cid)
            continue
        if frag.lower() not in full:
            problems.append("fragment is not in the hero text: '%s'" % frag[:50])
        src = claim_source(cid, claims, evidence)
        for w in absolute:
            if re.search(r"\b%s\b" % re.escape(w), frag.lower()) and not re.search(r"\b%s\b" % re.escape(w), src):
                problems.append("absolute word '%s' in a fragment citing %s, but the claim does not use it: '%s'" % (w, cid, frag[:60]))
        ctext = claims[cid].get("text", "").lower()   # the claim text only, not the evidence quote
        for q in quals:
            if q["in_claim"] in ctext and not any(a in frag.lower() for a in q["fragment_needs_any"]):
                problems.append("fragment citing %s drops the qualifier '%s': '%s'" % (cid, q["in_claim"], frag[:60]))
        for kr in (policy or {}).get("keep_rules", []):
            if kr["claim"] == cid and any(w in frag.lower() for w in kr["if_any"]) and not any(w in frag.lower() for w in kr["needs_any"]):
                problems.append("fragment citing %s widens its scope: %s ('%s')" % (cid, kr["why"], frag[:60]))
        for q in claim_qualifiers:
            if q["claim"] == cid and not any(a in frag.lower() for a in q["fragment_needs_any"]):
                problems.append("fragment citing %s must keep: %s ('%s')" % (cid, q["why"], frag[:60]))
    # every sentence must be mapped or be baseline text
    frags = [m.get("fragment", "").lower() for m in cmap]
    for s in sentences(h1) + sentences(sub):
        sl = s.lower().rstrip(".")
        if any(sl in b.lower() for b in baseline_texts):
            continue
        if not any((f and (f in sl or sl in f)) for f in frags):
            problems.append("sentence has no claim: '%s'" % s[:60])
    cited = " ".join(claim_source(m.get("claim", ""), claims, evidence) for m in cmap) + " " + " ".join(baseline_texts).lower()
    for num in re.findall(r"\d[\d,.]*%?", h1 + " " + sub):
        if num.lower() not in cited:
            problems.append("new number not in a cited claim or the baseline: " + num)
    return problems


def _selftest():
    claims = {"CL-002": {"text": "Model inference runs on Sarvam-operated GPUs in India, and requests do not go to the original model maker's overseas API.", "evidence_ids": "[EV-009]"},
              "CL-003": {"text": "Sarvam offers a 99.95% uptime SLA for enterprise deployments, agreed by contract.", "evidence_ids": "[EV-010]"},
              "CL-004": {"text": "Zero data retention is available on request, under an agreed arrangement.", "evidence_ids": "[EV-011]"}}
    ev = {"EV-009": {"quote": "Inference runs on Sarvam GPUs in India."}, "EV-010": {"quote": "99.95% uptime SLA."}, "EV-011": {"quote": "Zero data retention on request."}}
    ok = True

    def expect(name, variant, want_substr):
        nonlocal ok
        pr = check(variant, claims, ev, ["sovereign cloud"], ["console", "models"], [])
        hit = any(want_substr in x for x in pr) if want_substr else not pr
        print("%s %s" % ("PASS" if hit else "FAIL", name), "" if hit else pr)
        ok = ok and hit
    base = {"h1": "Run models in India.", "subline": "Zero data retention is available on request.", "cta": "See the models", "cta_destination": "models",
            "map": [{"fragment": "Run models in India", "claim": "CL-002"}, {"fragment": "Zero data retention is available on request", "claim": "CL-004"}]}
    expect("clean variant passes", base, None)
    expect("absolute word 'never' is blocked", {**base, "subline": "Your prompts never leave the country.", "map": [{"fragment": "Run models in India", "claim": "CL-002"}, {"fragment": "Your prompts never leave the country", "claim": "CL-002"}]}, "absolute word 'never'")
    expect("dropped qualifier 'by contract' is blocked", {**base, "subline": "Backed by a 99.95% uptime SLA.", "map": [{"fragment": "Run models in India", "claim": "CL-002"}, {"fragment": "Backed by a 99.95% uptime SLA", "claim": "CL-003"}]}, "drops the qualifier")
    expect("fake claim id is blocked", {**base, "map": [{"fragment": "Run models in India", "claim": "CL-999"}]}, "does not exist")
    expect("banned phrase is blocked", {**base, "h1": "Your sovereign cloud for models."}, "banned phrase")
    expect("new number is blocked", {**base, "h1": "Run models in India at 40% less cost."}, "new number")
    expect("unmapped sentence is blocked", {**base, "subline": "Zero data retention is available on request. Trusted by everyone."}, "sentence has no claim")
    expect("unknown button destination is blocked", {**base, "cta": "Compare on your workload", "cta_destination": "sizing"}, "not a real destination")
    expect("long H1 is blocked", {**base, "h1": "Run models in India " + "and more words here " * 4 + "."}, "longer than 14 words")
    claims["CL-011"] = {"text": "Token Factory lists DeepSeek V4.1 Flash 1017 at INR 14 per 1M input tokens.", "evidence_ids": "[EV-015]"}
    ev["EV-015"] = {"quote": "INR 14 per 1M input tokens"}
    pq = [{"claim": "CL-011", "fragment_needs_any": ["deepseek v4.1 flash"], "why": "price is for one named model"}]
    pv = {**base, "h1": "From INR 14/1M input tokens.", "map": [{"fragment": "From INR 14/1M input tokens", "claim": "CL-011"}], "subline": "Zero data retention is available on request.", }
    pv["map"].append({"fragment": "Zero data retention is available on request", "claim": "CL-004"})
    r1 = check(pv, claims, ev, [], ["console", "models"], [], pq)
    r2 = check({**pv, "h1": "DeepSeek V4.1 Flash at INR 14/1M input tokens.", "map": [{"fragment": "DeepSeek V4.1 Flash at INR 14/1M input tokens", "claim": "CL-011"}, pv["map"][1]]}, claims, ev, [], ["console", "models"], [], pq)
    for nm, got, want in (("bare price without the model name is blocked", r1, True), ("price with the model name passes", r2, False)):
        hit = bool(got) == want
        print("%s %s" % ("PASS" if hit else "FAIL", nm), "" if hit else got)
        ok = ok and hit
    pol = {"no_third_party_model_names": True, "model_name_words": ["deepseek", "qwen"], "stretch_phrases": ["drop-in", "existing code works"],
           "keep_rules": [{"claim": "CL-002", "if_any": ["forward", "overseas"], "needs_any": ["original model"], "why": "scope"}]}
    for nm, v, want in (
        ("third-party model name is blocked", {**base, "h1": "Run DeepSeek models in India."}, "third-party model"),
        ("stretch phrase is blocked", {**base, "subline": "Your existing code works. Zero data retention is available on request."}, "stretch phrase"),
        ("widened CL-002 scope is blocked", {**base, "subline": "Requests are not forwarded overseas.", "map": [{"fragment": "Run models in India", "claim": "CL-002"}, {"fragment": "Requests are not forwarded overseas", "claim": "CL-002"}]}, "widens its scope"),
        ("CL-002 with 'original model' passes", {**base, "subline": "Requests do not go to the original model maker's overseas API.", "map": [{"fragment": "Run models in India", "claim": "CL-002"}, {"fragment": "Requests do not go to the original model maker's overseas API", "claim": "CL-002"}]}, None)):
        pr = check(v, claims, ev, ["sovereign cloud"], ["console", "models"], [], (), pol)
        hit = any(want in x for x in pr) if want else not pr
        print("%s %s" % ("PASS" if hit else "FAIL", nm), "" if hit else pr)
        ok = ok and hit
    qi = quote_issues('The buyer asks "Is it a drop-in replacement?" and the hero says "Run models in India".', ["Run models in India.", "Does the page say the API is OpenAI-compatible?"])
    hit = len(qi) == 1 and "drop-in" in qi[0]
    print("%s invented quote in prose is caught" % ("PASS" if hit else "FAIL"), "" if hit else qi)
    ok = ok and hit
    print("gate1 selftest:", "ALL PASS" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)

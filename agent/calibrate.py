#!/usr/bin/env python3
"""--calibrate: set a pass line per judge and per question from labelled cases.

Cases: tests/calibration/cases.json (built by --build from tests/jev-cases/*.json plus cases we wrote).
Rule for each judge and question, on the fit cases only:
  good-polarity questions (support, audit): the line sits just above the highest failure case,
      so no failure case passes. Recall = share of good cases at or above the line.
  bad-polarity questions (overreach, banned): the line sits at the lowest bad case,
      so every bad case is flagged. False flags = share of clean cases at or above the line.
  A question is ADVISORY for a judge when recall is 0, or when more than half the clean cases are flagged.
Held-out cases are never used to set a line. They are scored afterwards and reported.
Writes rules/judge-thresholds.json and tests/calibration/results.json.
Run: python3 -I agent/calibrate.py --build   then   python3 -I agent/calibrate.py --page token-factory
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import judgekit as jk  # noqa: E402
import llm  # noqa: E402

PROJECT = jk.PROJECT
CASES = os.path.join(PROJECT, "tests", "calibration", "cases.json")


def fm(path):
    txt = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    d = {}
    for line in (m.group(1) if m else "").split("\n"):
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            d[k.strip()] = v.strip().strip('"')
    return d


def build(page):
    base = os.path.join(PROJECT, "pages", page)
    claims = {fm(f)["id"]: fm(f) for f in glob.glob(os.path.join(base, "claims", "cl-*.md"))}
    ev = {fm(f)["id"]: fm(f) for f in glob.glob(os.path.join(base, "evidence", "ev-*.md"))}

    def frag_case(cid, line, support, overreach, src, holdout=False, why=""):
        c = claims[cid]
        quote = " | ".join(ev[e]["quote"] for e in re.findall(r"EV-\d+", c["evidence_ids"]) if ev.get(e, {}).get("quote"))
        return {"id": src, "kind": "fragment", "fragment": line, "claim": cid, "claim_text": c["text"], "evidence_quote": quote,
                "expected": {"G1-support": support, "G2-overreach": overreach}, "holdout": holdout, "why": why, "source": src}

    cases = []
    jc_map = {"jc-01": "CL-001", "jc-02": "CL-001", "jc-03": "CL-006", "jc-05": "CL-004",
              "jc-06": "CL-002", "jc-07": "CL-011", "jc-08": "CL-003", "jc-12": "CL-008"}
    hold = {"jc-03", "jc-06"}
    for f in sorted(glob.glob(os.path.join(PROJECT, "tests", "jev-cases", "jc-*.json"))):
        j = json.load(open(f))
        m = re.search(r"line[^']*'(.+)'\s*\??\s*$", j["question"], re.S)
        if not m:
            continue
        line = m.group(1)
        if j["id"] in jc_map:
            yes = j["expected"] == "yes"
            cases.append(frag_case(jc_map[j["id"]], line, "yes" if yes else "no", "no" if yes else "yes", j["id"],
                                   j["id"] in hold, j.get("why", "")))
        elif j["id"] in ("jc-04", "jc-09"):
            cases.append({"id": j["id"], "kind": "banned", "line": line, "expected": {"G3-banned": "yes"}, "holdout": False,
                          "why": j.get("why", ""), "source": j["id"]})
    # cases we wrote (owner-accepted standard, Decisions Log row 24)
    cases += [
        frag_case("CL-005", "ISO 27001:2022 certified and SOC 2 Type II attested.", "yes", "no", "own-F1", True, "exact restatement"),
        frag_case("CL-004", "Zero data retention is available on request.", "yes", "no", "own-F2", False, "keeps 'on request'"),
        frag_case("CL-002", "Your prompts never leave the country.", "no", "yes", "own-F3", False, "'never' and 'the country' are wider than requests not going to the model maker's overseas API"),
        frag_case("CL-003", "Backed by a 99.95% uptime SLA.", None, "yes", "own-F4", False, "drops 'enterprise deployments, agreed by contract'"),
        frag_case("CL-011", "DeepSeek V4.1 Flash at ₹14 per 1M input tokens.", "yes", "no", "own-F5", False, "rupee sign vs INR"),
        frag_case("CL-011", "From INR 14 per 1M input tokens.", None, "yes", "own-F6", False, "implies the lowest price across all models"),
        {"id": "own-B1", "kind": "banned", "line": "Run leading open models on Sarvam's GPUs in India.", "expected": {"G3-banned": "no"}, "holdout": False, "why": "clean", "source": "own"},
        {"id": "own-B2", "kind": "banned", "line": "Zero data retention is available on request.", "expected": {"G3-banned": "no"}, "holdout": False, "why": "clean", "source": "own"},
        {"id": "own-B3", "kind": "banned", "line": "A sovereign cloud for your AI inference, hosted in India.", "expected": {"G3-banned": "yes"}, "holdout": False, "why": "paraphrase of 'sovereign cloud'", "source": "own"},
        {"id": "own-B4", "kind": "banned", "line": "One API key for every model in the catalogue.", "expected": {"G3-banned": "no"}, "holdout": False, "why": "clean", "source": "own"},
    ]
    dest_models = "the model catalogue page"
    heroes = [
        ("own-A2-yes", "A2-value", "yes", "Run open models on Sarvam GPUs in India through one OpenAI-compatible API.", "Pick shared or dedicated capacity.", "See the models", dest_models),
        ("own-A2-no", "A2-value", "no", "The future of intelligence, built here.", "Unlock what comes next.", "Learn more", dest_models),
        ("own-A3-yes", "A3-proof", "yes", "Open models served in India.", "ISO 27001:2022 certified and SOC 2 Type II attested.", "See the models", dest_models),
        ("own-A3-no", "A3-proof", "no", "Open models served in India.", "Fast, private and ready for your team.", "See the models", dest_models),
        ("own-A4-yes", "A4-cta", "yes", "Open models served in India.", "Pick a model and read its price per 1M tokens.", "Browse the model catalogue", dest_models),
        ("own-A4-no", "A4-cta", "no", "Open models served in India.", "Pick a model that fits.", "Go", dest_models),
        ("own-A1-yes", "A1-audience", "yes", "For engineering teams that move production model workloads to an India-served API.", "Open models through one OpenAI-compatible API.", "See the models", dest_models),
        ("own-A1-no", "A1-audience", "no", "AI for everyone.", "Something for every need.", "See the models", dest_models),
        ("own-A1-yes2", "A1-audience", "yes", "Engineering leaders: serve your production model workloads from India.", "Open models through one OpenAI-compatible API.", "See the models", dest_models),
        ("own-A1-yes3", "A1-audience", "yes", "Built for AI platform teams at GCCs and IT services firms.", "Serve open models on GPUs in India.", "See the models", dest_models),
        ("own-A1-no2", "A1-audience", "no", "Models for the modern world.", "Fast and simple.", "See the models", dest_models),
        ("own-A2-yes2", "A2-value", "yes", "Serve open models from GPUs in India with one API key.", "Change the model name to switch models.", "See the models", dest_models),
        ("own-A2-no2", "A2-value", "no", "Where ideas meet scale.", "Built for what is next.", "See the models", dest_models),
        ("own-A2-no3", "A2-value", "no", "Innovation without limits.", "The platform for tomorrow.", "See the models", dest_models),
        ("own-A3-yes2", "A3-proof", "yes", "Open models served in India.", "99.95% uptime SLA for enterprise deployments, agreed by contract.", "See the models", dest_models),
        ("own-A3-no2", "A3-proof", "no", "Open models served in India.", "Trusted, secure and reliable.", "See the models", dest_models),
        ("own-A3-no3", "A3-proof", "no", "Open models served in India.", "Teams love how easy it is.", "See the models", dest_models),
        ("own-A4-yes2", "A4-cta", "yes", "Open models served in India.", "Prices are listed per 1M tokens.", "Compare pricing", "the Token Factory pricing page"),
        ("own-A4-yes3", "A4-cta", "yes", "Open models served in India.", "Tell us about your workload.", "Discuss your requirements", "a contact form for Token Factory inference"),
        ("own-A4-no2", "A4-cta", "no", "Open models served in India.", "Built for teams.", "Click here", "the product console"),
        # added 16 Nov 2026 (questions v2): A1 is about the buyer's situation, not a label
        ("own-A1-yes-sit1", "A1-audience", "yes", "Move production model workloads to India without rewriting your code.", "Open models through one OpenAI-compatible API.", "See the models", dest_models),
        ("own-A1-yes-sit2", "A1-audience", "yes", "Keep inference data in India and keep the API your code already calls.", "Change one line: the base URL.", "See the models", dest_models),
        ("own-A1-no-label1", "A1-audience", "no", "For enterprises.", "AI for every need.", "See the models", dest_models),
        ("own-A1-no-label2", "A1-audience", "no", "Built for banks.", "The future of AI.", "See the models", dest_models),
        ("own-A4-no-learn", "A4-cta", "no", "Open models served in India.", "Pick a model and read its price per 1M tokens.", "Learn more", dest_models),
    ]
    for cid, q, exp, h1, sub, cta, dest in heroes:
        cases.append({"id": cid, "kind": "audit", "question": q, "h1": h1, "sub": sub, "cta": cta, "destination": dest,
                      "expected": {q: exp}, "holdout": False, "source": "own"})
    # A7 (buyer question) and A8 (main objection): the fill text varies, so the band is about answering ANY given question.
    bland = ("Frontier open models.", "Fast, simple and ready for your team.", "Get started", "the product console")
    filled = [
        ("own-A7-yes1", "A7-checklist-item", "item", "Does the page say where inference runs", "yes", "Open models served in India.", "Inference runs on GPUs in India.", "See the models", dest_models),
        ("own-A7-yes2", "A7-checklist-item", "item", "Does the page say the API is OpenAI-compatible", "yes", "Open models on one API.", "The API is OpenAI-compatible: change the endpoint, key and model.", "Read the API guide", "the API documentation"),
        ("own-A7-yes3", "A7-checklist-item", "item", "Does the page show a price per 1M tokens, or link to prices", "yes", "Open models served in India.", "Every model lists its price per 1M tokens.", "Compare pricing", "the Token Factory pricing page"),
        ("own-A7-yes4", "A7-checklist-item", "item", "Does the page say how to test one workload", "yes", "Test one workload before you commit.", "Send a sample of your own workload and compare cost and latency.", "Start a test", "the product console"),
        ("own-A7-yes5", "A7-checklist-item", "item", "Does the page say the service has an uptime commitment", "yes", "Open models served in India.", "A 99.95% uptime SLA for enterprise deployments, agreed by contract.", "See the models", dest_models),
        ("own-A7-no1", "A7-checklist-item", "item", "Does the page say where inference runs") + ("no",) + bland,
        ("own-A7-no2", "A7-checklist-item", "item", "Does the page say the API is OpenAI-compatible") + ("no",) + bland,
        ("own-A7-no3", "A7-checklist-item", "item", "Does the page show a price per 1M tokens, or link to prices") + ("no",) + bland,
        ("own-A7-no4", "A7-checklist-item", "item", "Does the page say how to test one workload") + ("no",) + bland,
        ("own-A7-no5", "A7-checklist-item", "item", "Does the page say the service has an uptime commitment") + ("no",) + bland,
        ("own-A8-yes1", "A8-objection", "objection", "The model may fail our own test set", "yes", "Open models served in India.", "Test any model on a sample of your own data before you commit.", "Start a test", "the product console"),
        ("own-A8-yes2", "A8-objection", "objection", "Our data may leave India", "yes", "Inference runs on GPUs in India.", "Requests do not go to the original model maker's overseas API.", "See the models", dest_models),
        ("own-A8-yes3", "A8-objection", "objection", "Switching APIs will take too much engineering work", "yes", "Open models on an OpenAI-compatible API.", "Change the endpoint, key and model, then test your calls.", "Read the API guide", "the API documentation"),
        ("own-A8-yes4", "A8-objection", "objection", "We cannot predict the bill", "yes", "Open models served in India.", "Each model lists its price per 1M input and output tokens.", "Compare pricing", "the Token Factory pricing page"),
        ("own-A8-yes5", "A8-objection", "objection", "The service may go down in production", "yes", "Open models served in India.", "A 99.95% uptime SLA for enterprise deployments, agreed by contract.", "See the models", dest_models),
        ("own-A8-no1", "A8-objection", "objection", "The model may fail our own test set") + ("no",) + bland,
        ("own-A8-no2", "A8-objection", "objection", "Our data may leave India") + ("no",) + bland,
        ("own-A8-no3", "A8-objection", "objection", "Switching APIs will take too much engineering work") + ("no",) + bland,
        ("own-A8-no4", "A8-objection", "objection", "We cannot predict the bill") + ("no",) + bland,
        ("own-A8-no5", "A8-objection", "objection", "The service may go down in production") + ("no",) + bland,
    ]
    for cid, q, fk, fv, exp, h1, sub, cta, dest in filled:
        cases.append({"id": cid, "kind": "audit", "question": q, "fill": {fk: fv}, "h1": h1, "sub": sub, "cta": cta, "destination": dest,
                      "expected": {q: exp}, "holdout": False, "source": "own"})
    os.makedirs(os.path.dirname(CASES), exist_ok=True)
    json.dump({"built": datetime.date.today().isoformat(), "page": page,
               "note": "Labels are ours (owner-accepted standard, Decisions Log row 24). The judges were never trained on them.",
               "cases": cases}, open(CASES, "w"), indent=2, ensure_ascii=False)
    print("built %d cases (%d held out) -> %s" % (len(cases), sum(c["holdout"] for c in cases), os.path.relpath(CASES, PROJECT)))


def run(page):
    data = json.load(open(CASES))
    _, audit_q, g2_q = jk.questions()
    base = os.path.join(PROJECT, "pages", page)
    banned = re.findall(r"^- BAN: (.+)$", open(os.path.join(base, "decisions", "do-not-claim.md"), encoding="utf-8").read(), re.M)
    brief = json.load(open(os.path.join(base, "brief.json")))
    buyer = brief["first_buyer"]["role"] + " at a GCC or IT services firm"
    ctx = open(os.path.join(base, "context-pack.md"), encoding="utf-8").read()
    promise = re.search(r'Promise, exact words: "(.+?)"', ctx).group(1)
    os.makedirs(os.path.join(PROJECT, "tests", "calibration"), exist_ok=True)
    llm.LOG_PATH = os.path.join(PROJECT, "tests", "calibration", "calibration-log.jsonl")
    scores = []   # (role, qid, case_id, p, expected, holdout)
    for c in data["cases"]:
        for role in ("judge1", "judge2"):
            if c["kind"] == "fragment":
                st = jk.fragment_state(c["fragment"], c["claim"], c["claim_text"], c["evidence_quote"])
                qs = {k: g2_q[k]["text"] for k in ("G1-support", "G2-overreach")}
            elif c["kind"] == "banned":
                st = ["HERO TEXT: " + jk.norm(c["line"]), "DO-NOT-CLAIM LIST: " + "; ".join(banned)]
                qs = {"G3-banned": g2_q["G3-banned"]["text"]}
            else:
                st = jk.context_state(buyer, promise) + jk.hero_state(c["h1"], c["sub"], c["cta"], c["destination"])
                txt = audit_q[c["question"]]["text"]
                for fk, fv in (c.get("fill") or {}).items():
                    txt = txt.replace("{%s}" % fk, fv)
                qs = {c["question"]: txt}
            r = llm.decide(role, st, qs, "calibrate " + c["id"])
            for q, exp in c["expected"].items():
                if exp is None:
                    continue
                scores.append({"role": role, "q": q, "case": c["id"], "p": r["answers"][q]["p"], "expected": exp, "holdout": c["holdout"]})
    th = {"date": datetime.date.today().isoformat(), "gray_zone": None, "judges": {},
          "method": "Bands: the hold band lies between the highest failure case and the lowest good case (fit cases only). Advisory when they overlap.",
          "note": "Set by agent/calibrate.py from tests/calibration/cases.json. Small, self-written case set: an audit signal, not an assurance."}
    for role in ("judge1", "judge2"):
        th["judges"][role] = {"model": llm.roles()[role]}
        for q in sorted(set(s["q"] for s in scores)):
            fit = [s for s in scores if s["role"] == role and s["q"] == q and not s["holdout"] and s["p"] is not None]
            if jk.is_bad(q):
                bad = [s["p"] for s in fit if s["expected"] == "yes"]; clean = [s["p"] for s in fit if s["expected"] == "no"]
                fa, ca = (min(bad) if bad else None), (max(clean) if clean else None)
                th["judges"][role][q] = {"polarity": "bad", "flag_at": fa, "clean_at": ca, "advisory": not (fa is not None and ca is not None and fa > ca), "n_fit": len(fit)}
            else:
                good = [s["p"] for s in fit if s["expected"] == "yes"]; fail = [s["p"] for s in fit if s["expected"] == "no"]
                pa, fa = (min(good) if good else None), (max(fail) if fail else None)
                th["judges"][role][q] = {"polarity": "good", "pass_at": pa, "fail_at": fa, "advisory": not (pa is not None and fa is not None and pa > fa), "n_fit": len(fit)}
        if "A2-value" in th["judges"][role] and "A7-checklist-item" not in th["judges"][role]:
            th["judges"][role]["A7-checklist-item"] = dict(th["judges"][role]["A2-value"], advisory=True, note="no own cases; borrows the A2-value band; advisory")
    for s in scores:
        t = th["judges"][s["role"]].get(s["q"])
        v = jk.verdict(th, s["role"], s["q"], s["p"])
        want = ("fail" if s["expected"] == "yes" else "pass") if jk.is_bad(s["q"]) else ("pass" if s["expected"] == "yes" else "fail")
        s["verdict"], s["want"] = v, want
        s["correct"] = v.replace("advisory-", "") == want
    json.dump(th, open(os.path.join(PROJECT, "rules", "judge-thresholds.json"), "w"), indent=2)
    json.dump({"scores": scores}, open(os.path.join(PROJECT, "tests", "calibration", "results.json"), "w"), indent=2)
    for role in ("judge1", "judge2"):
        print("\n%s (%s)" % (role, llm.roles()[role]))
        for q, t in th["judges"][role].items():
            if q == "model":
                continue
            rows = [s for s in scores if s["role"] == role and s["q"] == q]
            band = ("fail<=%.2f pass>=%.2f" % (t["fail_at"], t["pass_at"])) if t["polarity"] == "good" else ("clean<=%.2f flag>=%.2f" % (t["clean_at"], t["flag_at"]))
            print("  %-14s n=%-2d %-24s %s" % (q, t["n_fit"], band, "ADVISORY (cases overlap)" if t["advisory"] else "separates"))
        ho = [s for s in scores if s["role"] == role and s["holdout"]]
        print("  held-out: %d of %d correct (%s)" % (sum(s["correct"] for s in ho), len(ho), ", ".join("%s %s->%s" % (s["case"], s["q"], s["verdict"]) for s in ho)))
    print("\ncost $%.4f over %d calls. * = held out" % (llm.SPENT["usd"], llm.SPENT["calls"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default="token-factory")
    ap.add_argument("--build", action="store_true")
    a = ap.parse_args()
    build(a.page) if a.build else run(a.page)

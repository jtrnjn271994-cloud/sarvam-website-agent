#!/usr/bin/env python3
"""Step 9, edit and re-check: a person changes one variant, or asks the writer to rewrite it, and the new
version goes through Gate 1 and Gate 2 again with the run's own rules. It is added to the run as a new
variant (for example B-edit1). The original stays as it was. Nothing is approved here.

Two ways in:
  a person's edit:   python3 agent/edit_variant.py --page P --run R --from B --h1 "..." --sub "..." --cta "..."
  a writer rewrite:  python3 agent/edit_variant.py --page P --run R --from B --note "describe the buyer's situation in the headline"

Gate 1 is not relaxed: a person's edit that breaks a rule is recorded with its problems and cannot be approved.
"""
import argparse
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate1  # noqa: E402
import judgekit as jk  # noqa: E402
import llm  # noqa: E402
import probe3  # noqa: E402
import shortlist  # noqa: E402
import skills as skl  # noqa: E402

PROJECT = jk.PROJECT
MAX_EDITS = 5
HOSTED = bool(os.environ.get("AGENT_HOSTED"))


def map_text(D, v, src):
    """Claim map for the new text: keep fragments still found word for word, ask the writer to map only the rest."""
    text = v["h1"] + " " + v["subline"]
    kept = [m for m in src.get("map", []) if m["fragment"] in text]
    covered = " ".join(m["fragment"] for m in kept)
    loose = [s for s in gate1.sentences(text) if s.strip() and s.strip() not in covered]
    if not loose:
        return kept
    ask = (probe3.rules_block(D) + "\n\n=== TASK ===\nDo NOT change the hero text. Return the claim map for it: for each sentence listed under MAP THESE, "
           "copy a fragment EXACTLY from the text and give the one claim id it relies on. If no claim supports a sentence, still map it to the closest claim; "
           "the rule check will judge it.\nReply with JSON only: {\"variants\":[{\"map\":[{\"fragment\":\"exact text\",\"claim\":\"CL-001\"}]}]}\n\n"
           "HERO H1: %s\nHERO SUB-LINE: %s\nMAP THESE:\n%s" % (v["h1"], v["subline"], "\n".join("- " + s for s in loose)))
    got, _ = probe3.ask_json([{"role": "user", "content": ask}], "edit claim map")
    new = [m for m in (got["variants"][0].get("map") or []) if isinstance(m, dict) and m.get("fragment") and m.get("claim")]
    return kept + new


def rewrite(D, src, note, probe):
    """The writer rewrites one variant from the person's note, with the same skills and hard rules as the run."""
    sk, _ = skl.load("writer_edit")
    gaps = (probe.get("audit") or {}).get("gaps") or []
    task = ("=== TASK ===\nRewrite ONE hero variant. A person reviewed it and asks for this change: \"%s\".\n"
            "Keep its angle unless the note says otherwise. Keep everything the rules require. The audit gaps are: %s.\n"
            "POSITIONING PROMISE (approved by a person; it is not a claim): %s\n"
            "CURRENT VARIANT: %s\n"
            "Reply with JSON only, one variant, with a fresh claim map copied exactly from your new text:\n"
            "{\"variants\":[{\"name\":\"%s\",\"angle\":\"...\",\"h1\":\"...\",\"subline\":\"...\",\"cta\":\"...\",\"cta_destination\":\"%s\",\"map\":[{\"fragment\":\"exact text\",\"claim\":\"CL-001\"}],\"why\":\"one sentence\"}]}") % (
        note, ", ".join(gaps), D["promise"], json.dumps({k: src.get(k) for k in ("h1", "subline", "cta", "cta_destination", "angle")}, ensure_ascii=False),
        src["name"], src.get("cta_destination"))
    msgs = [{"role": "user", "content": sk + "\n\n" + probe3.rules_block(D) + "\n\n" + task}]
    out, msgs = probe3.ask_json(msgs, "edit writer rewrite")
    return out["variants"][0], msgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--from", dest="src", required=True)
    ap.add_argument("--note")
    ap.add_argument("--h1")
    ap.add_argument("--sub")
    ap.add_argument("--cta")
    a = ap.parse_args()
    if not re.match(r"^[a-z0-9-]+$", a.page) or not re.match(r"^probe3-\d{8}-\d{6}$", a.run):
        sys.exit("bad page or run")
    rd = os.path.join(PROJECT, "pages", a.page, "runs", a.run)
    path = os.path.join(rd, "probe3.json")
    probe = json.load(open(path, encoding="utf-8"))
    src = next((x for x in probe.get("variants") or [] if x["name"] == a.src), None)
    if not src:
        sys.exit("no variant %s in this run" % a.src)
    edits = probe.setdefault("edits", [])
    if len(edits) >= MAX_EDITS:
        sys.exit("this run already has %d edits, the limit. Start a new run." % MAX_EDITS)
    note = (a.note or "").strip()
    if not note and not (a.h1 or a.sub or a.cta):
        sys.exit("give a note for the writer, or a changed H1, sub-line or button")

    D = probe3.load(a.page, probe["persona"]["key"], probe["goal"]["id"])
    th = jk.thresholds()
    Q, _, g2_q = jk.questions()
    aq_now, _ = probe3.audit_questions(D, Q)
    saved = list((probe.get("audit") or {}).get("p") or {})
    missing = [k for k in saved if k not in aq_now]
    if missing:
        sys.exit("the page's buyer questions changed since this run (%s). Start a new run to edit against the current questions." % ", ".join(missing))
    aq = {k: aq_now[k] for k in saved}
    llm.LOG_PATH = os.path.join(rd, "run-log.jsonl")
    base = src["name"].split("-edit")[0]
    n = 1 + sum(1 for x in probe["variants"] if x["name"].startswith(base + "-edit"))
    name = "%s-edit%d" % (base, n)
    print("EDIT %s from %s (%s)" % (name, src["name"], "writer rewrite from the person's note" if note else "the person's own words"))

    if note:
        v, msgs = rewrite(D, src, note, probe)
    else:
        v = {"h1": (a.h1 or src["h1"]).strip(), "subline": (a.sub if a.sub is not None else src["subline"]).strip(),
             "cta": (a.cta or src["cta"]).strip(), "cta_destination": src.get("cta_destination"), "angle": src.get("angle")}
        v["map"] = map_text(D, v, src)
    v.update(name=name, edited_from=src["name"], edit_kind="note" if note else "person")
    if v.get("cta_destination") not in D["dests"]:
        v["cta_destination"] = src.get("cta_destination")
    print("  H1 : %s\n  SUB: %s\n  BTN: %s" % (v["h1"], v["subline"], v["cta"]))

    quals = D["cfg"].get("claim_qualifiers", [])
    check = lambda x: gate1.check(x, D["claims"], D["ev"], D["banned"], list(D["dests"]), [D["hero"]["h1"], D["hero"]["sub"]], quals, D["cfg"])
    problems = check(v)
    if problems and note:   # the writer gets one fix round, as in a run
        print("  Gate 1 problems, one fix round: %s" % problems)
        fixed, _ = probe3.ask_json(msgs + [{"role": "user", "content": "Gate 1 rejected some lines. Fix only what failed. Return the full JSON again.\n" + "; ".join(map(str, problems))}], "edit writer gate1 fix")
        keep = {k: v[k] for k in ("name", "edited_from", "edit_kind")}
        v = dict(fixed["variants"][0], **keep)
        problems = check(v)
    print("  Gate 1: %s" % ("; ".join(map(str, problems)) if problems else "passed"))

    probe["variants"].append(v)
    probe["gate1_rounds"][-1][name] = problems
    if not problems:
        a_base = probe["audit"]["p"]
        a_base2 = next((r["judge2"]["audit_baseline"] for r in (probe.get("gate2") or {}).values() if r.get("judge2", {}).get("audit_baseline")), None)
        if not a_base2 or any(k not in a_base2 for k in aq):
            h = D["hero"]
            a_base2 = probe3.audit(D, "judge2", h["h1"], h["sub"], D["cta"], D["cta_dest"]["what_it_is"] if D["cta_dest"] else "unknown", aq, "audit live baseline judge2")
        au = probe["audit"]
        targeted = (au.get("gaps") or []) + ([au["lead_item"]] if au.get("lead_item") else []) + (["A8-objection"] if au.get("objection_gap") else [])
        probe.setdefault("gate2", {})[name] = probe3.gate2_score(D, v, aq, th, Q, g2_q, a_base, a_base2, targeted)
    probe["shortlist"] = shortlist.classify(probe)
    grp = next(x for x in probe["shortlist"] if x["name"] == name)
    edits.append({"name": name, "from": src["name"], "kind": v["edit_kind"], "note": note, "at": datetime.datetime.now().isoformat(timespec="seconds"),
                  "gate1_problems": problems, "group": grp["group"], "cost_usd": round(llm.SPENT["usd"], 4), "made_by": "a person asked for it" + (" on the website" if HOSTED else " in the local console")})
    probe["cost_usd"] = round(float(probe.get("cost_usd") or 0) + llm.SPENT["usd"], 4)
    json.dump(probe, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  => group: %s. %s" % (grp["group"], " ".join(grp["reasons"])))

    if not HOSTED and not problems:
        try:
            pngs(rd, D, v, probe, grp)
        except Exception as e:   # the PNG is a convenience; the approval page says when it is missing
            print("  PNG pair not made (%s)" % e)
    __import__("run_flow").write(a.page, a.run)
    print("edit done | cost $%.4f" % llm.SPENT["usd"])


def pngs(rd, D, v, probe, grp):
    """PNG pair on the owner's machine, made the same way as in a run: one read-only load of the live page
    (no clicks), the variant's words swapped into the hero, one screenshot. The saved copy cannot be used here:
    its styles do not load offline, so it would draw unstyled. The website never does this (HOSTED)."""
    from playwright.sync_api import sync_playwright
    clip = dict(D["hero"]["hero_clip"]); clip["height"] = min(clip["height"] + 220, 1400)
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(viewport={"width": 1280, "height": 900})
        try:
            pg.goto(D["hero"]["url"], wait_until="networkidle", timeout=45000)
        except Exception:   # pages with live demos never go quiet: read once loaded
            pg.wait_for_load_state("load", timeout=30000)
            pg.wait_for_timeout(4000)
        pg.wait_for_timeout(1200)
        pg.evaluate("""() => { document.querySelectorAll('body *').forEach(e => { const s = getComputedStyle(e);
            if ((s.position === 'fixed' || s.position === 'sticky') && /cookie|privacy|consent/i.test(e.innerText || '') && e.getBoundingClientRect().top > 200) e.style.display = 'none'; }); }""")
        pg.evaluate("""() => { const h1=[...document.querySelectorAll('h1')].find(e=>e.getBoundingClientRect().height>0); h1.setAttribute('data-hero','h1');
            let box=h1.parentElement; for(let i=0;i<6&&box;i++){ if([...box.querySelectorAll('a,button')].some(b=>b.innerText.trim())) break; box=box.parentElement;}
            const p=[...box.querySelectorAll('p')].find(p=>p.innerText.trim() && (h1.compareDocumentPosition(p)&4)); if(p) p.setAttribute('data-hero','sub');
            const a=[...box.querySelectorAll('a')].find(a=>a.innerText.trim()); if(a) a.setAttribute('data-hero','cta'); }""")
        if not os.path.isfile(os.path.join(rd, "hero-baseline.png")):
            pg.screenshot(path=os.path.join(rd, "hero-baseline.png"), clip=clip)
        pg.evaluate("""(t) => { const set=(sel,txt)=>{const e=document.querySelector(sel); if(!e) return;
            const w=document.createTreeWalker(e,NodeFilter.SHOW_TEXT); let n; const ns=[]; while(n=w.nextNode()) if(n.nodeValue.trim()) ns.push(n);
            if(ns.length){ ns[0].nodeValue=txt; ns.slice(1).forEach(x=>x.nodeValue=''); } else e.textContent=txt; };
            set('[data-hero=h1]', t.h1); set('[data-hero=sub]', t.sub); set('[data-hero=cta]', t.cta); }""",
                    {"h1": v["h1"], "sub": v["subline"], "cta": v["cta"]})
        pg.wait_for_timeout(150)
        pg.screenshot(path=os.path.join(rd, "hero-variant-%s.png" % v["name"]), clip=clip)
        sheet = os.path.join(rd, "pair-%s.html" % v["name"])
        open(sheet, "w", encoding="utf-8").write(
            """<html><body style="margin:0;font:14px system-ui;background:#f4f5f8;color:#1a1d26"><div style="padding:18px 22px">
            <div style="font-size:18px;font-weight:700">Baseline vs variant %s (edited from %s)</div>
            <div style="color:#5b6472;margin:4px 0 14px">Buyer: %s. Goal: %s. Group: %s.</div>
            <div style="display:flex;gap:16px"><div style="flex:1"><div style="font-weight:600;margin-bottom:6px">Baseline (live)</div><img src="hero-baseline.png" style="width:100%%;border:1px solid #ccd"></div>
            <div style="flex:1"><div style="font-weight:600;margin-bottom:6px">Variant %s</div><img src="hero-variant-%s.png" style="width:100%%;border:1px solid #ccd"></div></div>
            <table style="margin-top:14px;border-collapse:collapse;background:#fff;width:100%%"><tr><th style="text-align:left;padding:6px;border:1px solid #dde">Part</th><th style="text-align:left;padding:6px;border:1px solid #dde">Baseline</th><th style="text-align:left;padding:6px;border:1px solid #dde">Variant</th></tr>
            <tr><td style="padding:6px;border:1px solid #dde">H1</td><td style="padding:6px;border:1px solid #dde">%s</td><td style="padding:6px;border:1px solid #dde">%s</td></tr>
            <tr><td style="padding:6px;border:1px solid #dde">Sub-line</td><td style="padding:6px;border:1px solid #dde">%s</td><td style="padding:6px;border:1px solid #dde">%s</td></tr>
            <tr><td style="padding:6px;border:1px solid #dde">Button</td><td style="padding:6px;border:1px solid #dde">%s</td><td style="padding:6px;border:1px solid #dde">%s</td></tr></table>
            </div></body></html>""" % (v["name"], v["edited_from"], D["buyer"], D["goal"]["label"], grp["group"], v["name"], v["name"],
                                       D["hero"]["h1"], v["h1"], D["hero"]["sub"], v["subline"], D["cta"], v["cta"]))
        p2 = br.new_page(viewport={"width": 1600, "height": 900})
        p2.goto("file://" + sheet)
        p2.wait_for_timeout(300)
        p2.screenshot(path=os.path.join(rd, "pair-%s.png" % v["name"]), full_page=True)
        br.close()
    print("  PNG pair:", "pair-%s.png" % v["name"])


if __name__ == "__main__":
    main()

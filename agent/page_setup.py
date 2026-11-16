#!/usr/bin/env python3
"""Page setup: everything a run needs for one page and one buyer persona, drafted, checked and then approved
by a person in the console. The reasoning model (Gemini) drafts; code checks; a person approves.

Parts (each approved separately, by file hash, in pages/<page>/setup/approvals.json):
  positioning        loaded if the page already has one (context-pack.md), else drafted with the positioning skills
  claims             claims with EXACT quotes from the saved page text; code drops any quote not found word for word
  checklist:<persona> buyer questions for this persona on this page, tagged [hero] or [page], plus a main objection
                      copied word for word from the persona's research row
Run:  python3 agent/page_setup.py --page voice-agents --persona bfsi:technical-evaluator [--part all|positioning|claims|checklist]
      python3 agent/page_setup.py --page voice-agents --status [--persona ...]
"""
import argparse
import datetime
import glob
import hashlib
import html
import json
import os
import re
import sys
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate1
import knowledge as kb  # noqa: E402
import llm  # noqa: E402
import skills as skl  # noqa: E402

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSONAS = os.path.join(PROJECT, "library", "personas.json")


# ---------- shared helpers (also used by the server and probe3) ----------
def norm(t):
    t = html.unescape(t or "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = t.replace("‑", "-").replace("‐", "-").replace("–", "-").replace(" ", " ")
    return re.sub(r"\s+", " ", t).strip()


def sha(path_or_text, is_text=False):
    data = path_or_text.encode("utf-8") if is_text else open(path_or_text, "rb").read()
    return hashlib.sha256(data).hexdigest()


def persona(key):
    data = json.load(open(PERSONAS, encoding="utf-8"))
    for ind in data["industries"]:
        for r in ind["roles"]:
            if r["key"] == key:
                return dict(r, industry=ind["name"], industry_id=ind["id"])
    return None


def buyer_text(p):
    return "%s (%s) in %s" % (p["role"], p["typical_titles"] or "titles not listed", p["industry"])


def page_base(page):
    return os.path.join(PROJECT, "pages", page)


def setup_dir(page):
    d = os.path.join(page_base(page), "setup")
    os.makedirs(d, exist_ok=True)
    return d


def capture_dir(page):
    caps = sorted(glob.glob(os.path.join(page_base(page), "capture", "*-live", "hero.json")))
    return os.path.dirname(caps[-1]) if caps else None


def positioning_file(page):
    """(path, promise) for the page's positioning. Saved page pack first, then a setup draft."""
    for rel in ("context-pack.md", os.path.join("setup", "positioning.md")):
        p = os.path.join(page_base(page), rel)
        if os.path.isfile(p):
            m = re.search(r'Promise, exact words: "(.+?)"', open(p, encoding="utf-8").read())
            if m:
                return p, m.group(1)
    return None, None


def structure_rule():
    return json.load(open(os.path.join(PROJECT, "rules", "positioning-structure.json"), encoding="utf-8"))


def check_positioning(page):
    """Problems with the page's positioning against rules/positioning-structure.json. Empty list = passes."""
    f, promise = positioning_file(page)
    if not f:
        return ["no positioning file"]
    R = structure_rule()
    text = open(f, encoding="utf-8").read()
    probs = []
    if not promise:
        probs.append('section 1 has no line: Promise, exact words: "..."')
    elif len(promise.split()) > 30:
        probs.append("the promise is %d words (30 at most)" % len(promise.split()))
    heads = [(m.start(), m.group(1).strip()) for m in re.finditer(r"^## (.+)$", text, re.M)]
    found = {}
    for i, (pos, h) in enumerate(heads):
        m = re.match(r"(\d+)\.\s*(.+)", h)
        if m:
            end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
            found[int(m.group(1))] = (m.group(2), text[pos:end])
    labels = set(R["labels"])
    for s in R["sections"]:
        if s["n"] not in found:
            probs.append("missing section %d: %s" % (s["n"], s["heading"]))
            continue
        name, body = found[s["n"]]
        if norm(name).lower() != norm(s["heading"]).lower():
            probs.append("section %d is titled '%s'; the rule says '%s'" % (s["n"], name, s["heading"]))
        bullets = re.findall(r"^- (.+)$", body, re.M)
        if len(bullets) < s["min_bullets"]:
            probs.append("section %d has %d bullets (at least %d)" % (s["n"], len(bullets), s["min_bullets"]))
        for b in bullets:
            m = re.search(r"\[([^\[\]|]+)\|\s*([^\[\]]+)\]\s*$", b)
            if not m:
                probs.append("section %d bullet has no [source | LABEL] tag: '%s'" % (s["n"], b[:60]))
                continue
            probs += ["section %d: %s" % (s["n"], x) for x in kb.check_bullet_ids("- " + b)]
            bad = [x.strip() for x in m.group(2).split(",") if x.strip() not in labels]
            if bad:
                probs.append("section %d uses an unknown label %s: '%s'" % (s["n"], bad, b[:50]))
            if s["n"] == 8 and not re.match(r"(Market signal\.|Reading:)", b):
                probs.append("section 8 bullet must start with 'Market signal.' or 'Reading:': '%s'" % b[:50])
    try:
        hero = hero_of(page)
        if promise and overlap(promise, hero["h1"] + " " + (hero.get("sub") or "")) > 0.6:
            probs.append("the promise restates the live hero (over 60% shared words)")
    except (OSError, KeyError, ValueError):
        pass
    return probs


def checklist_file(page, key):
    idx = os.path.join(page_base(page), "setup", "checklists.json")
    m = json.load(open(idx, encoding="utf-8")) if os.path.isfile(idx) else {}
    if key in m:
        return os.path.join(page_base(page), m[key])
    p = os.path.join(page_base(page), "setup", "checklists", key.replace(":", "--") + ".md")
    return p if os.path.isfile(p) else None


def claims_files(page):
    return sorted(glob.glob(os.path.join(page_base(page), "claims", "cl-*.md"))) + \
        sorted(glob.glob(os.path.join(page_base(page), "evidence", "ev-*.md")))


def claims_hash(page):
    files = claims_files(page)
    return sha("".join(os.path.basename(f) + open(f, encoding="utf-8").read() for f in files), True) if files else None


def approvals(page):
    p = os.path.join(page_base(page), "setup", "approvals.json")
    return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else {"entries": []}


def part_hash(page, part):
    if part == "positioning":
        f, _ = positioning_file(page)
        return sha(f) if f else None
    if part == "claims":
        return claims_hash(page)
    if part.startswith("checklist:"):
        f = checklist_file(page, part.split(":", 1)[1])
        return sha(f) if f else None
    return None


def part_state(page, part):
    """'missing', 'draft' (never approved), 'changed' (edited after approval) or 'approved'."""
    h = part_hash(page, part)
    if not h:
        return "missing"
    mine = [e for e in approvals(page)["entries"] if e["part"] == part]
    if not mine:
        return "draft"
    return "approved" if mine[-1]["hash"] == h and mine[-1]["decision"] == "approve" else "changed"


def status(page, key=None):
    parts = ["positioning", "claims"] + (["checklist:" + key] if key else [])
    st = {p: part_state(page, p) for p in parts}
    return {"parts": st, "ready": st.get("positioning") == "approved" and st.get("claims") == "approved",
            "questions_ready": bool(key) and st.get("checklist:" + key) == "approved"}


# ---------- page text ----------
class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template", "head"}
    BLOCK = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "section", "br", "tr", "td", "th", "a", "button", "span"}

    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def page_text(page):
    cd = capture_dir(page)
    out = os.path.join(cd, "page-text.txt")
    if not os.path.isfile(out):
        p = _Text()
        p.feed(open(os.path.join(cd, "snapshot.html"), encoding="utf-8").read())
        lines, seen = [], set()
        for l in "".join(p.out).split("\n"):
            l = norm(l)
            if len(l) > 2 and l not in seen:
                seen.add(l)
                lines.append(l)
        open(out, "w", encoding="utf-8").write("\n".join(lines))
    return open(out, encoding="utf-8").read()


def parse_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0))


def ask(prompt, purpose, max_tokens=4000):
    r = llm.chat([{"role": "user", "content": prompt}], role="reasoning", max_tokens=max_tokens, temperature=0.2, purpose=purpose)
    for attempt in range(2):
        try:
            return parse_json(r["text"])
        except (ValueError, AttributeError):
            r = llm.chat([{"role": "user", "content": prompt}, {"role": "assistant", "content": r["text"]},
                          {"role": "user", "content": "That was not valid JSON. Reply with the JSON object only."}],
                         role="reasoning", max_tokens=max_tokens, temperature=0, purpose=purpose + " json repair")
    return parse_json(r["text"])


def hero_of(page):
    return json.load(open(os.path.join(capture_dir(page), "hero.json"), encoding="utf-8"))


def banned():
    return re.findall(r"^- BAN: (.+)$", open(os.path.join(PROJECT, "rules", "do-not-claim.md"), encoding="utf-8").read(), re.M)


def policy():
    return json.load(open(os.path.join(PROJECT, "rules", "hero-policy.json"), encoding="utf-8"))


def prose_problems(text, sources):
    src = " ".join(sources)
    nums = [n for n in re.findall(r"\d[\d.,%]*", text) if n.rstrip(".,") not in src]
    return ["number not in the page: " + n for n in nums] + gate1.quote_issues(text, sources) + gate1.policy_issues(text, policy())


# ---------- drafting ----------
def overlap(a, b):
    """Share of a's content words that also appear in b."""
    w = lambda t: {x for x in re.findall(r"[a-z0-9₹.]+", norm(t).lower()) if len(x) > 3}
    wa = w(a)
    return len(wa & w(b)) / len(wa) if wa else 0.0


def draft_positioning(page):
    """Draft the page's positioning pack to rules/positioning-structure.json (Decisions Log row 39).
    The reasoning model writes it with the positioning skills; code checks structure, labels, numbers and the promise."""
    f, promise = positioning_file(page)
    if f:
        print("positioning: saved (%s)" % os.path.relpath(f, PROJECT))
        return
    if not claims_files(page):
        draft_claims(page)   # the pack cites claim ids, so claims come first
    prof = json.load(open(os.path.join(page_base(page), "profile.json"), encoding="utf-8"))
    text, hero = page_text(page), hero_of(page)
    R = structure_rule()
    sk, used = skl.load("positioning_draft")
    claims = []
    for cf in claims_files(page):
        m = re.search(r'^id: (\S+)$', open(cf, encoding="utf-8").read(), re.M)
        t = re.search(r'^text: "(.*)"$', open(cf, encoding="utf-8").read(), re.M)
        if m and t:
            claims.append("%s: %s" % (m.group(1), t.group(1)))
    dnc = open(os.path.join(PROJECT, "rules", "do-not-claim.md"), encoding="utf-8").read()
    example = open(os.path.join(PROJECT, "pages", "voice-agents", "setup", "positioning.md"), encoding="utf-8").read()
    example = example.split("\n## 6.")[0] + "\n(... sections 6 to 12 follow the same pattern ...)"
    sections = "\n".join("## %d. %s  (at least %d bullets) must cover: %s" % (x["n"], x["heading"], x["min_bullets"], x["must_cover"]) for x in R["sections"])
    reg = os.path.join(page_base(page), "source-register.csv")
    if not os.path.isfile(reg):
        open(reg, "w", encoding="utf-8").write(
            "id,source,path_or_url,date,label,use,status\n"
            "SRC-P01,Saved page text (capture),%s,%s,VENDOR,Page wording and hero,read in full\n"
            "SRC-P02,Do-not-claim rules,rules/do-not-claim.md,%s,PROPOSED,Banned and unproven claims,read\n"
            % (os.path.relpath(os.path.join(capture_dir(page), "page-text.txt"), page_base(page)), hero.get("captured_at", "")[:10], datetime.date.today()))
    sources = open(reg, encoding="utf-8").read()
    prod = next((x.get("map_product") for x in (json.load(open(os.path.join(PROJECT, "pages", "registry.json"), encoding="utf-8")).get("pages", [])) if x["slug"] == page), None)
    kb_rows = "\n".join("KB:%s [%s, %s] %s" % r for r in kb.rows_for(prod, limit=60))
    prompt = sk + """

=== TASK ===
Write the positioning pack for ONE product page, in Markdown, following the STRUCTURE exactly: the 12 "## n. Heading" sections, in order, with these exact headings.
RULES (code checks every one; a failed check sends the draft back):
- %s
- Allowed labels: %s. Use VENDOR for what the page says, PROPOSED for your positioning choices, UNCHECKED for anything you could not check.
- %s
- %s
- Use ONLY the PAGE TEXT, the CLAIMS and the SOURCES below. Cite claim ids (CL-...) for page facts and SRC ids for sources. Do not add customers, numbers, rivals' facts or comparisons that these do not state. Where you lack a fact (rivals, market signals, what happens after the button), write a bullet that says so and label it UNCHECKED: that is correct, not a failure.
- Plain English, short sentences, one idea per sentence. No "seamless", "robust", "cutting-edge", "solution".
- Never name a third-party model. Respect the DO-NOT-CLAIM rules.
Reply with the Markdown only, starting with "# Page context pack: %s".

STRUCTURE:
%s

FORMAT EXAMPLE (another page; copy the shape, not the facts):
%s

PRODUCT: %s (%s)
LIVE HERO: %s / %s
CLAIMS (approved facts this page states):
%s
SOURCES (source register):
%s
KNOWLEDGE BASE ROWS (checked research, version %s). The ONLY outside facts you may use. Cite one as KB:<id> inside the bullet's tag, e.g. [KB:V-01, CL-001 | CHECKED]. A number next to a KB id must appear in that row. Do not use any fact that is neither on the page nor in these rows:
%s
DO-NOT-CLAIM RULES:
%s
PAGE TEXT (saved %s):
%s""" % (R["bullet_rule"], ", ".join(R["labels"]), R["promise_rule"], R["market_signal_rule"], prof.get("name"), sections, example,
         prof.get("name"), prof.get("url"), hero["h1"], hero["sub"], "\n".join(claims), sources, kb.version(), kb_rows, dnc[:4000], hero.get("captured_at", "")[:10], text[:14000])
    out = os.path.join(setup_dir(page), "positioning.md")
    head = ["---", "label: PROPOSED", "made_by: reasoning model (%s), page_setup.py, %s, to rules/positioning-structure.json" % (llm.roles()["reasoning"], datetime.date.today()),
            "skills: " + ", ".join(u["skill"] for u in used), "sources: source-register.csv", "knowledge_version: " + kb.version()]
    msgs = [{"role": "user", "content": prompt}]
    probs = ["not drafted"]
    for attempt in range(3):
        r = llm.chat(msgs, role="reasoning", max_tokens=7000, temperature=0.2, purpose="setup positioning pack")
        body = r["text"].strip()
        body = re.sub(r"^```(?:markdown|md)?\s*|\s*```$", "", body)
        open(out, "w", encoding="utf-8").write("\n".join(head + ["checks_left: pending", "---", "", body]) + "\n")
        probs = check_positioning(page)
        nums = [n for n in re.findall(r"\d[\d.,%%]*\d|\d", re.sub(r"\[[^\]]*\]|^## \d+\.|CL-\d+|SRC-\w+", "", body, flags=re.M))
                if n not in text and n not in " ".join(claims) and n not in dnc]
        probs += ["number not in the page, the claims or the rules: %s" % n for n in sorted(set(nums))[:8]]
        if not probs:
            break
        msgs = msgs + [{"role": "assistant", "content": r["text"]},
                       {"role": "user", "content": "Code rejected this draft: " + "; ".join(probs[:20]) + ". Fix only these problems and return the full Markdown again."}]
    open(out, "w", encoding="utf-8").write("\n".join(head + ["checks_left: " + ("; ".join(probs) or "none"), "---", "", body]) + "\n")
    print("positioning: drafted -> %s | checks left: %s" % (os.path.relpath(out, PROJECT), probs or "none"))


def draft_claims(page):
    if claims_files(page):
        print("claims: saved (%d files)" % len(claims_files(page)))
        return
    text = page_text(page)
    prof = json.load(open(os.path.join(page_base(page), "profile.json"), encoding="utf-8"))
    prompt = """=== TASK ===
List the factual claims this product page makes, so a hero writer can use ONLY these. 6 to 12 claims.
For each claim give:
- "text": the claim in one plain sentence, adding nothing the quote does not say,
- "quote": the EXACT words from the PAGE TEXT that support it (copy them character for character, one continuous span, 5 to 40 words),
- "keep": any condition in the quote that must stay attached ("on request", "from", "up to", "for enterprise"), or "".
Skip marketing adjectives with no checkable content. Skip third-party model names. Skip customer logos unless the page states what the customer did.
Return JSON only: {"claims": [{"text": "...", "quote": "...", "keep": "..."}]}

PRODUCT: %s (%s)
PAGE TEXT:
%s""" % (prof.get("name"), prof.get("url"), text[:16000])
    d = ask(prompt, "setup claims", max_tokens=5000)
    nt = norm(text)
    kept, dropped = [], []
    for c in d.get("claims", []):
        q, t = norm(c.get("quote")), norm(c.get("text"))
        why = []
        if not q or q not in nt:
            why.append("quote not found word for word on the page")
        why += ["number not in the quote: " + n for n in re.findall(r"\d[\d.,%]*", t) if n.rstrip(".,") not in q]
        why += gate1.policy_issues(t, policy())
        (dropped if why else kept).append(dict(c, text=t, quote=q, why=why))
    cd, ed = os.path.join(page_base(page), "claims"), os.path.join(page_base(page), "evidence")
    os.makedirs(cd, exist_ok=True)
    os.makedirs(ed, exist_ok=True)
    cap = hero_of(page)
    for i, c in enumerate(kept, 1):
        cid, eid = "CL-%03d" % i, "EV-%03d" % i
        slug = re.sub(r"[^a-z0-9]+", "-", c["text"].lower())[:40].strip("-")
        open(os.path.join(cd, "cl-%03d-%s.md" % (i, slug)), "w", encoding="utf-8").write(
            '---\nid: %s\ntype: claim\nlabel: VENDOR\ntext: "%s"\nevidence_ids: [%s]\nkeep: "%s"\nmade_by: page_setup.py (reasoning model draft, quote checked by code)\n---\n\nThe page says this. It is the vendor\'s own statement, not checked by us.\n'
            % (cid, c["text"].replace('"', "'"), eid, (c.get("keep") or "").replace('"', "'")))
        open(os.path.join(ed, "ev-%03d-%s.md" % (i, slug)), "w", encoding="utf-8").write(
            '---\nid: %s\ntype: evidence\nlabel: VENDOR\nsource: "%s"\ncaptured: "%s"\nquote: "%s"\n---\n\nQuote found word for word in the saved page text.\n'
            % (eid, cap.get("url"), cap.get("captured_at", ""), c["quote"].replace('"', "'")))
    json.dump({"kept": len(kept), "dropped": dropped, "made": datetime.datetime.now().isoformat(timespec="seconds")},
              open(os.path.join(setup_dir(page), "claims-check.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("claims: kept %d, dropped %d (quote or number not on the page)" % (len(kept), len(dropped)))


def draft_checklist(page, key):
    if checklist_file(page, key):
        print("checklist %s: saved" % key)
        return
    p = persona(key)
    if not p:
        sys.exit("unknown persona: " + key)
    text, hero = page_text(page), hero_of(page)
    prof = json.load(open(os.path.join(page_base(page), "profile.json"), encoding="utf-8"))
    prompt = """=== TASK ===
Write the questions this buyer asks when they land on this product page, so a judge can check whether the page answers them.
Write 4 to 6 yes/no questions, each starting "Does the page say" or "Does the page show". Base them on the BUYER ROW. Tag each:
- "hero" if the first screen (headline, one sub-line, one button) could fairly answer it,
- "page" if only the rest of the page could.
Then pick the buyer's main objection: copy ONE phrase EXACTLY from BLOCKS_IF (character for character).
Return JSON only: {"questions": [{"q": "...?", "scope": "hero"}], "main_objection": "..."}

PRODUCT: %s
HERO NOW: %s / %s
BUYER ROW (analyst research, not interviews): role %s; titles %s; owns %s; CARES_ABOUT %s; BLOCKS_IF %s
PAGE TEXT (for context only):
%s""" % (prof.get("name"), hero["h1"], hero["sub"], p["role"], p["typical_titles"], p["owns"], p["cares_about"], p["blocks_if"], text[:8000])
    d = ask(prompt, "setup checklist " + key)
    obj = norm(d.get("main_objection"))
    obj_ok = bool(obj) and obj.lower() in norm(p["blocks_if"]).lower()
    qs = [x for x in d.get("questions", []) if x.get("scope") in ("hero", "page") and x.get("q", "").startswith("Does the page")]
    out = os.path.join(setup_dir(page), "checklists", key.replace(":", "--") + ".md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    body = ["---", 'id: "%s"' % key, 'title: "%s"' % buyer_text(p).replace('"', "'"), "type: buyer-checklist", "label: PROPOSED",
            'main_objection: "%s"' % (obj if obj_ok else "").replace('"', "'"),
            'source: "%s"' % (p["source_url"] or "icp-round-2 committee.csv"), "made_by: page_setup.py (reasoning model draft)", "---", "",
            "# %s" % buyer_text(p), "",
            "PROPOSED. Drafted from the buyer research row. A person approves it in the console before the audit asks these questions.",
            "" if obj_ok else "The main objection was not copied word for word from the research row, so it was left empty.", "",
            "## Questions the page must answer", ""] + ["- [%s] %s" % (x["scope"], x["q"].rstrip()) for x in qs] + \
           ["", "## Research row", "", "- Cares about: " + p["cares_about"], "- Blocks if: " + p["blocks_if"], "- Label: " + p["label"], ""]
    open(out, "w", encoding="utf-8").write("\n".join(body))
    print("checklist %s: drafted %d questions, objection %s" % (key, len(qs), "copied" if obj_ok else "left empty"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", required=True)
    ap.add_argument("--persona")
    ap.add_argument("--part", default="all")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if not re.match(r"^[a-z0-9-]+$", a.page) or not os.path.isfile(os.path.join(page_base(a.page), "profile.json")):
        sys.exit("unknown page")
    if a.status:
        print(json.dumps(status(a.page, a.persona), indent=1))
        return
    if not capture_dir(a.page):
        sys.exit("capture the page first (agent/pages_registry.py --capture --page %s)" % a.page)
    llm.LOG_PATH = os.path.join(setup_dir(a.page), "setup-log.jsonl")
    page_text(a.page)
    if a.part in ("all", "claims"):
        draft_claims(a.page)
    if a.part in ("all", "positioning"):
        draft_positioning(a.page)
    if a.part in ("all", "checklist") and a.persona:
        draft_checklist(a.page, a.persona)
    print("cost $%.4f over %d calls" % (llm.SPENT["usd"], llm.SPENT["calls"]))
    print(json.dumps(status(a.page, a.persona)))


if __name__ == "__main__":
    main()

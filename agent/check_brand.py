#!/usr/bin/env python3
"""Check a draft against the brand rules, as far as code can.

Run from anywhere:  python3 -I agent/check_brand.py --file draft.html [--page <slug>]
Default (no file):  python3 -I agent/check_brand.py   (checks that the rule data loads)
Self test:          python3 -I agent/check_brand.py --selftest

Rules (data in agent/brand_patterns.json and in the page profile):
  1. Every hex colour is in the brand tokens file in the library.
  2. The company is "<full name>" on first mention and "<short name>" after.
  3. Banned phrases never appear. A line with the word "compute" needs a source tag.
  4. No model name in the title (html title tag, or the first Markdown heading).
  5. Product names (profile field product_names) appear exactly as written.
  6. Each font-family value uses only the allowed font families, plus generic fallbacks.
Prints each failure with its line number. Standard library only.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

HEX = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")


def norm_hex(h):
    h = h.lower()
    if len(h) in (4, 5):
        h = "#" + "".join(c * 2 for c in h[1:])
    return h[:7] if len(h) == 9 else h


def load_rules(project):
    return common.load_json(os.path.join(common.AGENT_DIR, "brand_patterns.json"))


def load_palette(project, rules):
    files = sorted(glob.glob(os.path.join(project, rules["tokens_glob"])))
    found = set()
    for f in files:
        for h in HEX.findall(common.read_text(f)):
            found.add(norm_hex(h))
    return found, files


def product_names(project, page):
    pages = [page] if page else common.list_pages(project)
    names = []
    for p in pages:
        prof = common.load_profile(project, p) or {}
        names.extend(n for n in (prof.get("product_names") or []) if isinstance(n, str) and n.strip())
    return names


def check_text(text, rules, colours, names, is_html):
    """Return a list of (line_number, message)."""
    out = []
    lines = text.splitlines()
    tag = re.compile(rules["source_tag_pattern"], re.I)
    full, short = rules["company_full"], rules["company_short"]
    seen_first = False
    for n, line in enumerate(lines, start=1):
        for h in HEX.findall(line):
            col = line.find(h)
            if line[max(0, col - 6):col] == 'href="':
                continue
            if norm_hex(h) not in colours:
                out.append((n, "colour %s is not in the brand tokens file" % h))
        for m in re.finditer(r"\b%s\b" % re.escape(short), line):
            is_full = line.startswith(full, m.start())
            if not seen_first:
                seen_first = True
                if not is_full:
                    out.append((n, "first mention must be '%s', not '%s'" % (full, short)))
            elif is_full:
                out.append((n, "use '%s' after the first mention, not '%s'" % (short, full)))
        for phrase in rules["banned_phrases"]:
            if phrase.lower() in line.lower():
                out.append((n, "banned phrase '%s'" % phrase))
        word = rules["word_needs_source_tag"]
        if re.search(r"\b%s\b" % re.escape(word), line, re.I) and not tag.search(line):
            out.append((n, "the word '%s' needs a source tag on the same line" % word))
        for decl in re.findall(r"font-family\s*:\s*([^;}]+)", line, re.I):
            for fam in decl.split(","):
                fam = fam.strip().strip("\"'").strip()
                allowed = [f.lower() for f in rules.get("allowed_fonts", [])] + rules.get("generic_font_words", [])
                if fam and rules.get("allowed_fonts") and fam.lower() not in allowed and not fam.lower().startswith("var("):
                    out.append((n, "font '%s' is not an allowed font family" % fam))
        for name in names:
            pattern = r"\b" + r"[\s\-_]*".join(re.escape(w) for w in re.split(r"[\s\-_]+", name.strip())) + r"\b"
            for m in re.finditer(pattern, line, re.I):
                if m.group(0) != name:
                    out.append((n, "product name '%s' must be written exactly as '%s'" % (m.group(0), name)))
    title, tline = None, 0
    if is_html:
        m = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
        if m:
            title, tline = m.group(1), text[:m.start()].count("\n") + 1
    else:
        for n, line in enumerate(lines, start=1):
            if line.startswith("# "):
                title, tline = line[2:], n
                break
    if title:
        for w in rules["model_name_words"]:
            if re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(w), title, re.I):
                out.append((tline, "model name '%s' in the title" % w))
    return sorted(set(out))


def run_file(project, path, page=None):
    if not os.path.isfile(path):
        print("ERROR   file not found: %s" % path)
        return 1
    rules = load_rules(project)
    colours, files = load_palette(project, rules)
    if not files:
        print("ERROR   brand tokens file not found: %s" % rules["tokens_glob"])
        return 1
    fails = check_text(common.read_text(path), rules, colours, product_names(project, page),
                       path.lower().endswith((".html", ".htm")))
    for n, msg in fails:
        print("FAIL    line %d: %s" % (n, msg))
    print("---")
    print("failures: %d" % len(fails))
    return 1 if fails else 0


def run_default(project):
    rules = load_rules(project)
    colours, files = load_palette(project, rules)
    if not files or not colours:
        print("ERROR   brand tokens file not found or holds no colours: %s" % rules["tokens_glob"])
        return 1
    print("rule data loads; %d palette colours from %d file(s). Use --file to check a draft." % (len(colours), len(files)))
    return 0


def selftest():
    st = common.SelfTest("check_brand")
    rules = {"company_full": "Acme Corp", "company_short": "Acme", "banned_phrases": ["Acme Train", "cloud nine"],
             "word_needs_source_tag": "compute", "source_tag_pattern": "\\[(?:CL|EV|LIB)-\\d+\\]|\\bsource:",
             "model_name_words": ["llama"], "tokens_glob": "x",
             "allowed_fonts": ["Acme Sans"], "generic_font_words": ["sans-serif"]}
    colours = {"#112233", "#ffffff"}
    names = ["Fast Lane"]

    def fails(text, html=False):
        return check_text(text, rules, colours, names, html)
    good = "Acme Corp builds tools. Acme ships Fast Lane. color #112233 and #fff. compute [EV-001]\n"
    st.expect(fails(good) == [], "a clean draft passes (a 3-digit hex expands to match)")
    st.expect(any("#abcdef" in m for _, m in fails("Acme Corp. color #abcdef\n")), "a hex colour not in the tokens file is caught")
    st.expect(fails('Acme Corp. <a href="#abc123">x</a>\n') == [], "an anchor link is not read as a colour")
    st.expect(any("first mention" in m for _, m in fails("Acme builds tools.\n")), "a short name on first mention is caught")
    st.expect(any("after the first mention" in m for _, m in fails("Acme Corp one.\nAcme Corp two.\n")), "the full name after the first mention is caught")
    st.expect(any("banned phrase 'Acme Train'" in m for _, m in fails("Acme Corp offers Acme Train today.\n")), "a banned phrase is caught")
    r = fails("Acme Corp.\nWe sell compute at scale.\n")
    st.expect(any(n == 2 and "compute" in m for n, m in r), "the word 'compute' with no source tag is caught, with its line number")
    r = fails("# Llama on Acme Corp\ntext\n")
    st.expect(any(n == 1 and "title" in m for n, m in r), "a model name in a Markdown title is caught")
    r = fails("<html>\n<title>Run llama fast</title>\n</html>\nAcme Corp\n", html=True)
    st.expect(any(n == 2 and "title" in m for n, m in r), "a model name in an html title tag is caught")
    r = fails("Acme Corp sells FastLane and fast-lane.\n")
    st.expect(sum("product name" in m for _, m in r) == 2, "product names written in a wrong form are caught")
    r = fails("Acme Corp\nbody { font-family: 'Acme Sans', Arial, sans-serif; }\n")
    st.expect(any(n == 2 and "Arial" in m for n, m in r) and len(r) == 1, "a font outside the allowed families is caught, fallbacks pass")
    return st.done()


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--file" in argv and argv.index("--file") + 1 < len(argv):
        page = argv[argv.index("--page") + 1] if "--page" in argv and argv.index("--page") + 1 < len(argv) else None
        return run_file(common.PROJECT, argv[argv.index("--file") + 1], page)
    return run_default(common.PROJECT)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

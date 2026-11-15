#!/usr/bin/env python3
"""Create a new page folder from agent/templates/page/.

Run from anywhere:
  python3 -I agent/new_page.py --page <kebab-case-slug> --url <url> [--name "Page name"]
Self test:
  python3 -I agent/new_page.py --selftest

The script never guesses the goal, the buyer or the CTAs. A person fills them.
It refuses to overwrite a page that exists. It ends with the readiness check.
Standard library only.
"""
import argparse
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import check_page_readiness  # noqa: E402

TEMPLATE = os.path.join(common.AGENT_DIR, "templates", "page")
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def create_page(project, slug, url, name=None):
    """Return (ok, message)."""
    if not SLUG.match(slug or ""):
        return False, "slug must be kebab-case, like my-page-name: %s" % slug
    if not re.match(r"^https?://[^\s/]+", url or ""):
        return False, "url must start with http:// or https://"
    dest = os.path.join(project, "pages", slug)
    if os.path.exists(dest):
        return False, "pages/%s already exists. Nothing was changed." % slug
    if not os.path.isdir(TEMPLATE):
        return False, "template folder is missing: agent/templates/page"
    os.makedirs(dest)
    for entry in sorted(os.listdir(TEMPLATE)):
        src = os.path.join(TEMPLATE, entry)
        if entry == "profile.template.json":
            continue
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(dest, entry))
        elif os.path.isfile(src):
            # Loose templates keep their template name. A person or the
            # context-pack-builder skill fills them and saves the real file.
            shutil.copy2(src, os.path.join(dest, entry))
    with open(os.path.join(TEMPLATE, "profile.template.json"), encoding="utf-8") as f:
        profile = json.load(f)
    profile["page"] = slug
    profile["name"] = name or ""
    profile["url"] = url
    common.write_file(os.path.join(dest, "profile.json"), json.dumps(profile, indent=2, ensure_ascii=False) + "\n")
    common.write_file(os.path.join(dest, "README.md"),
                      "# %s\n\nPage folder for %s. A person must confirm the goal, the buyer and the CTAs in profile.json.\n"
                      % (name or slug, url))
    return True, "created pages/%s" % slug


def main(argv):
    ap = argparse.ArgumentParser(description="Create a new page folder from the template.")
    ap.add_argument("--page")
    ap.add_argument("--url")
    ap.add_argument("--name")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.page or not a.url:
        print("Use --page <slug> --url <url> [--name \"Page name\"]")
        return 2
    ok, msg = create_page(common.PROJECT, a.page, a.url, a.name)
    print(msg)
    if not ok:
        return 1
    print("The goal, buyer and CTAs are empty on purpose. A person must fill them.")
    print("Readiness check:")
    check_page_readiness.run(common.PROJECT, [a.page])
    return 0


def selftest():
    st = common.SelfTest("new_page")
    root = common.make_temp_project()
    try:
        ok, _ = create_page(root, "demo-page", "https://example.com", "Demo page")
        base = os.path.join(root, "pages", "demo-page")
        st.expect(ok and all(os.path.isfile(os.path.join(base, d, "README.md"))
                             for d in ["research", "buyer-and-wedge", "evidence", "claims", "decisions", "runs"]),
                  "a new page gets all six subfolders with a README")
        st.expect(os.path.isfile(os.path.join(base, "context-pack.template.md"))
                  and not os.path.exists(os.path.join(base, "context-pack.md")),
                  "the context pack template is copied under its template name")
        profile = common.load_json(os.path.join(base, "profile.json"))
        st.expect(profile["goal"] == "" and profile["buyer"] == "" and profile["main_cta"] == ""
                  and profile["status"] == "needs-confirmation", "goal, buyer and CTAs stay empty and status needs confirmation")
        st.expect(profile["url"] == "https://example.com" and profile["page"] == "demo-page", "the url and slug are written")
        ok2, msg2 = create_page(root, "demo-page", "https://example.com")
        st.expect(not ok2 and "already exists" in msg2, "a second run on the same slug is refused")
        st.expect(not create_page(root, "Bad_Slug", "https://example.com")[0], "a slug that is not kebab-case is refused")
        st.expect(not create_page(root, "other-page", "example.com")[0], "a url without a scheme is refused")
        st.expect(not os.path.exists(os.path.join(root, "pages", "other-page")), "a refused run creates no folder")
        lines, missing, person = check_page_readiness.check_page(root, "demo-page")
        st.expect(missing >= 1 and person >= 1, "the readiness check reports gaps on a new page")
    finally:
        common.drop_temp(root)
    return st.done()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

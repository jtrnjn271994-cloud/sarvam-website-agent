#!/usr/bin/env python3
"""Step 2: capture the hero of a live page ONCE (desktop, 1280 wide). No page name in this code.

Saves to pages/<page>/capture/<date>-live/:
  hero.json         H1, sub-line, hero buttons with hrefs, every page link, hero box, selectors used
  hero-desktop.png  screenshot of the hero box
  page-desktop.png  full-page screenshot (reference only)
  snapshot.html     the rendered HTML with a <base> tag, for local bot runs later
Also diffs the live hero against the newest older capture and prints any change.
Run: python3 -I agent/capture_hero.py --page token-factory
"""
import argparse
import datetime
import json
import os
import sys

from playwright.sync_api import sync_playwright

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

JS = r"""
() => {
  const vis = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const h1 = [...document.querySelectorAll('h1')].find(vis);
  if (!h1) return {error: 'no visible h1'};
  // hero box: climb from the h1 until the box holds at least one link or button with text
  let box = h1.parentElement;
  for (let i = 0; i < 6 && box; i++) {
    const btns = [...box.querySelectorAll('a,button')].filter(b => vis(b) && b.innerText.trim());
    if (btns.length) break;
    box = box.parentElement;
  }
  const txt = el => el.innerText.replace(/\s+/g, ' ').trim();
  const after = [...box.querySelectorAll('p')].filter(p => vis(p) && txt(p) &&
                   (h1.compareDocumentPosition(p) & Node.DOCUMENT_POSITION_FOLLOWING));
  const sub = after[0];
  const btns = [...box.querySelectorAll('a,button')].filter(b => vis(b) && txt(b));
  const r = box.getBoundingClientRect();
  const links = [...document.querySelectorAll('a[href]')].filter(a => txt(a)).map(a => ({text: txt(a).slice(0, 80), href: a.href}));
  h1.setAttribute('data-hero', 'h1');
  if (sub) sub.setAttribute('data-hero', 'sub');
  btns.forEach((b, i) => b.setAttribute('data-hero', 'cta-' + i));
  return {
    h1: txt(h1), sub: sub ? txt(sub) : null,
    ctas: btns.map((b, i) => ({index: i, text: txt(b), href: b.href || null, tag: b.tagName.toLowerCase()})),
    box: {x: Math.max(0, r.left + scrollX), y: Math.max(0, r.top + scrollY), width: r.width, height: r.height},
    links: links,
    title: document.title
  };
}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", required=True)
    args = ap.parse_args()
    base = os.path.join(PROJECT, "pages", args.page)
    prof = json.load(open(os.path.join(base, "profile.json")))
    url = prof.get("url") or json.load(open(os.path.join(base, "brief.json")))["page_url"]
    out = os.path.join(base, "capture", datetime.date.today().isoformat() + "-live")
    os.makedirs(out, exist_ok=True)
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(viewport={"width": 1280, "height": 900})
        try:
            pg.goto(url, wait_until="networkidle", timeout=45000)
            pg.wait_for_timeout(1500)
        except Exception:   # pages with live demos or streams never go quiet: the same single load, read once it has loaded
            pg.wait_for_load_state("load", timeout=30000)
            pg.wait_for_timeout(4000)
        data = pg.evaluate(JS)
        if data.get("error"):
            sys.exit("capture failed: " + data["error"])
        b = data["box"]
        clip = {"x": 0, "y": 0, "width": 1280, "height": min(max(b["y"] + b["height"] + 24, 500), 1400)}
        pg.screenshot(path=os.path.join(out, "hero-desktop.png"), clip=clip)
        pg.screenshot(path=os.path.join(out, "page-desktop.png"), full_page=True)
        html = pg.content().replace("<head>", '<head><base href="%s">' % url, 1)
        open(os.path.join(out, "snapshot.html"), "w", encoding="utf-8").write(html)
        br.close()
    data.update({"url": url, "captured_at": datetime.datetime.now().isoformat(timespec="seconds"),
                 "viewport": "1280x900", "hero_clip": clip,
                 "selectors": {"h1": "[data-hero=h1]", "sub": "[data-hero=sub]", "cta": "[data-hero^=cta-]"},
                 "label": "LIVE CAPTURE. Loaded once. No bot traffic goes to this URL."})
    json.dump(data, open(os.path.join(out, "hero.json"), "w"), indent=2, ensure_ascii=False)
    print("H1  :", data["h1"])
    print("SUB :", data["sub"])
    print("CTAs:", [(c["text"], c["href"]) for c in data["ctas"]])
    print("links on page:", len(data["links"]))
    # diff against the newest older capture
    older = sorted(d for d in os.listdir(os.path.join(base, "capture")) if d != os.path.basename(out))
    if older:
        oc = os.path.join(base, "capture", older[-1], "capture.json")
        if os.path.isfile(oc):
            hero = next(x for x in json.load(open(oc))["blocks"] if x["kind"] == "hero")
            old_h1 = next(l["text"] for l in hero["lines"] if l.get("role") == "heading").strip()
            old_sub = next(l["text"] for l in hero["lines"] if l.get("role") == "text").strip()
            print("\nDIFF vs %s: H1 %s | sub-line %s" % (older[-1], "same" if old_h1 == data["h1"] else "CHANGED (was: %s)" % old_h1,
                  "same" if old_sub == (data["sub"] or "") else "CHANGED (was: %s)" % old_sub))
    print("saved:", os.path.relpath(out, PROJECT))


if __name__ == "__main__":
    main()

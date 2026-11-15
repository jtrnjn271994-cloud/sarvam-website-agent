#!/usr/bin/env python3
"""Step 1a. Capture one live page fully: text, controls, images, layout facts and motion facts for each section.

Capture (needs Playwright, so run with plain python3, one page, no login):
  python3 agent/capture.py --page <slug> [--url URL] [--date YYYY-MM-DD]
Check a saved capture (no network, works with -I):
  python3 -I agent/capture.py --check pages/<slug>/capture/<date>
Self test (the pure parts run with -I; the browser part runs only when Playwright is importable):
  python3 -I agent/capture.py --selftest

Writes pages/<slug>/capture/<date>/ :
  capture.json            blocks in page order (see below), page facts, fidelity result, sha256
  capture.sha256          the hash of capture.json without its own hash field
  live-1280.png, live-390.png   full-page screenshots of the page as a visitor first sees it (FAQ closed)
  blocks/<name>-<width>.png      one screenshot for each block (FAQ and tabs opened)
A dated folder is never overwritten. The script opens every FAQ item, tab and drop-down before it reads the page.
One block = one top-level section of the page. A block holds:
  name, dom_id, kind, heading, headings, text (clean), lines (each line: text, role, tag, item), controls, images,
  faq (question and answer), tabs, layout {"1280": {...}, "390": {...}}, motion {...}, screenshots.
The file also satisfies schemas/capture.schema.json (url, captured_on, review_by, widths, blocks, click_path, seo).
"""
import datetime
import hashlib
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
WIDTHS = (1280, 390)
HEIGHTS = {1280: 800, 390: 844}
REVIEW_DAYS = 30
# Product and brand names that hold a lower-case letter followed by an upper-case letter on purpose.
CAMEL_OK = re.compile(r"^(OpenAI|DeepSeek|MiniMax|OpenRouter|GitHub|LinkedIn|YouTube|PyTorch|NVIDIA|HuggingFace|LangChain|LlamaIndex|"
                      r"JavaScript|TypeScript|FastAPI|SDKs?|APIs?|GPUs?|LLMs?|SLMs?|vLLM|iOS|macOS|OpenAPI|ChatGPT|WhatsApp|"
                      r"PhonePe|EmbeddingGemma|GPT-OSS|OpenClaw|ServiceNow|SambaNova|IndiaAI|AI4Bharat|BharatGen|HCLTech|DevOps|RAG|CPUs?)$")

# ---------------------------------------------------------------------------------------------------------------
# The browser side. One function reads one page state. All reads use computed styles. Nothing is clicked here.
# ---------------------------------------------------------------------------------------------------------------
EXTRACT_JS = r"""
(opts) => {
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  const vis = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const slug = s => norm(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').split('-').slice(0, 5).join('-');
  const main = document.querySelector('main') || document.body;
  let secs = Array.from(main.querySelectorAll('section')).filter(s => !s.parentElement.closest('section') && vis(s));
  if (secs.length < 2) {
    let kids = Array.from(main.children).filter(vis);
    while (kids.length === 1 && kids[0].children.length > 1) kids = Array.from(kids[0].children).filter(vis);
    secs = kids.filter(k => k.getBoundingClientRect().height > 80);
  }
  const FAQ_TRIGGER = 'button[aria-expanded]:not([aria-haspopup]), summary';
  const isControl = el => el.matches('a[href], button, [role=button], summary');
  const kindOf = el => {
    if (el.matches('[aria-expanded]:not([aria-haspopup]), summary')) return 'accordion';
    if (el.matches('[role=tab]')) return 'tab';
    if (el.matches('[aria-haspopup]')) return 'menu';
    return el.tagName === 'A' ? 'link' : 'button';
  };
  const labelOf = el => norm(el.innerText || el.textContent) || norm(el.getAttribute('aria-label')) || norm(el.getAttribute('title'));
  const filled = c => c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent';
  const look = el => { const s = getComputedStyle(el);
    const bordered = parseFloat(s.borderTopWidth) > 0 && s.borderTopStyle !== 'none';
    const pill = parseFloat(s.borderTopLeftRadius) >= 8;
    return (filled(s.backgroundColor) && pill) ? 'filled' : ((bordered && pill) ? 'outline' : 'text'); };
  // Lines: the page text as blocks. A control or an image role-label is one unit. A flex or block child is its own line.
  function lines(sec, itemEls) {
    const out = []; let cur = [];
    const itemOf = el => { for (let i = 0; i < itemEls.length; i++) if (itemEls[i].contains(el)) return i; return -1; };
    let curItem = -1;
    const flush = (role, tag) => { const t = norm(cur.join(' ')); if (t) out.push({text: t, role: role || 'text', tag: tag || '', item: curItem}); cur = []; };
    const walk = (n, inCtl) => {
      if (n.nodeType === 3) { cur.push(n.nodeValue); return; }
      if (n.nodeType !== 1) return;
      const tag = n.tagName;
      if (['SCRIPT','STYLE','NOSCRIPT','TEMPLATE','CANVAS','VIDEO','PICTURE','IMG','SVG','svg'].includes(tag)) return;
      if (n.getAttribute('aria-hidden') === 'true') return;
      const cs = getComputedStyle(n);
      if (cs.display === 'none' || cs.visibility === 'hidden') return;
      if (n.getAttribute('role') === 'img' && n.getAttribute('aria-label')) { flush(); curItem = itemOf(n); cur.push(n.getAttribute('aria-label')); flush('text', 'seal'); return; }
      if (n.matches('summary, button[aria-expanded]:not([aria-haspopup])')) { flush(); curItem = itemOf(n); cur.push(labelOf(n)); flush('question', tag.toLowerCase()); return; }
      if (isControl(n) && cs.display !== 'inline' && !(n.matches('a[href]') && (n.innerText || '').trim().split('\n').filter(x => x.trim()).length > 2)) { flush(); curItem = itemOf(n); const l = labelOf(n); if (l) { cur.push(l); flush('cta', 'a'); } return; }
      const inline = cs.display === 'inline' || cs.display === 'contents';
      if (!inline) { flush(); curItem = itemOf(n); }
      const role = /^H[1-6]$/.test(tag) ? 'heading' : (n.getAttribute('role') === 'region' && n.hasAttribute('aria-labelledby') ? 'answer' : null);
      const before = out.length;
      for (const c of n.childNodes) walk(c, inCtl);
      if (!inline) { flush(/^H[1-6]$/.test(tag) ? 'heading' : 'text', tag.toLowerCase()); }
      if (role === 'answer') { for (let i = before; i < out.length; i++) if (out[i].role === 'text') out[i].role = 'answer'; }
      if (role === 'heading') { for (let i = before; i < out.length; i++) if (out[i].role === 'text') { out[i].role = 'heading'; out[i].tag = tag.toLowerCase(); } }
    };
    walk(sec, false); flush();
    // a heading tag inside a flex child can leave the role as text. Mark any line whose text equals a heading's text.
    const hs = new Set(Array.from(sec.querySelectorAll('h1,h2,h3,h4,h5,h6')).map(h => norm(h.innerText)));
    out.forEach(l => { if (l.role === 'text' && hs.has(l.text)) l.role = 'heading'; });
    return out;
  }
  // items: the repeating child boxes of the widest row in the section (cards, steps, tiles).
  function findItems(sec) {
    let best = {n: 1, els: [], parent: null};
    const q = [];
    q.push([sec, 0]);
    while (q.length) {
      const [el, d] = q.shift();
      if (d > 6) continue;
      const kids = Array.from(el.children).filter(k => vis(k) && k.getBoundingClientRect().width >= 100 && k.getBoundingClientRect().height >= 40);
      if (kids.length >= 2) {
        const rows = {};
        kids.forEach(k => { const t = Math.round(k.getBoundingClientRect().top / 12); (rows[t] = rows[t] || []).push(k); });
        Object.values(rows).forEach(r => { if (r.length > best.n) best = {n: r.length, els: kids, parent: el}; });
      }
      Array.from(el.children).forEach(k => q.push([k, d + 1]));
    }
    return best;
  }
  const px = v => parseFloat(v) || 0;
  const fontOf = el => { if (!el) return null; const s = getComputedStyle(el);
    return {family: s.fontFamily.split(',')[0].replace(/["']/g, '').trim(), size: s.fontSize, weight: s.fontWeight, line_height: s.lineHeight,
            letter_spacing: s.letterSpacing, color: s.color, align: s.textAlign}; };
  const boxOf = el => { if (!el) return null; const s = getComputedStyle(el);
    return {background: s.backgroundColor, radius: s.borderTopLeftRadius, border: s.borderTopWidth + ' ' + s.borderTopStyle + ' ' + s.borderTopColor,
            shadow: s.boxShadow, padding: [s.paddingTop, s.paddingRight, s.paddingBottom, s.paddingLeft]}; };
  const BG_URL = /url\(["']?([^"')]+)["']?\)/g;
  const MOTION_CLS = /(^|[-:_])(reveal|revealed|fade|in-view|inview|visible|animate|aos|paused|seen|current|stagger|marquee|ticker|parallax|slide|zoom)([-:_]|$)|has-card-reveal|heading-reveal/i;
  const firstFn = v => ((v || '').match(/cubic-bezier\([^)]*\)|steps\([^)]*\)|[a-z-]+/) || [''])[0];
  window.__cap = window.__cap || {};
  const outSecs = secs.map((sec, idx) => {
    const r = sec.getBoundingClientRect(); const cs = getComputedStyle(sec);
    const headingEl = sec.querySelector('h1,h2,h3');
    const items = findItems(sec);
    const itemIdx = el => { for (let i = 0; i < items.els.length; i++) if (items.els[i].contains(el)) return i; return -1; };
    const meta = el => { const b = el.getBoundingClientRect(); const cs2 = getComputedStyle(el);
      return {item: itemIdx(el), box: {x: Math.round(b.left), y: Math.round(b.top - r.top), w: Math.round(b.width), h: Math.round(b.height)},
              decor: el.getAttribute('aria-hidden') === 'true' || cs2.position === 'absolute' || cs2.position === 'fixed'}; };
    const ls = lines(sec, items.els);
    // controls
    const ctlAll = Array.from(sec.querySelectorAll('a[href], button, [role=button], [role=tab], summary')).filter(vis);
    const ctlEls = ctlAll.filter(el => !ctlAll.some(o => o !== el && o.contains(el)));  // a button inside a link is one control: keep the link
    const controls = ctlEls.map(el => { const b = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return {label: labelOf(el), kind: kindOf(el), item: itemIdx(el), padding: [s.paddingTop, s.paddingRight, s.paddingBottom, s.paddingLeft],
              href: el.tagName === 'A' ? el.href : null, target: el.getAttribute('target') || null,
              look: look(el.querySelector('button, [role=button]') || el), expanded: el.hasAttribute('aria-expanded') ? el.getAttribute('aria-expanded') : null,
              box: {x: Math.round(b.left), y: Math.round(b.top + scrollY), w: Math.round(b.width), h: Math.round(b.height)},
              font_size: s.fontSize, color: s.color, background: s.backgroundColor, radius: s.borderTopLeftRadius,
              area: Math.round(b.width * b.height)}; });
    // images and media
    const images = [];
    sec.querySelectorAll('img').forEach(i => { const b = i.getBoundingClientRect(); images.push(Object.assign(meta(i), {kind: 'img', src: i.currentSrc || i.src, alt: i.getAttribute('alt'), natural: [i.naturalWidth, i.naturalHeight], rendered: [Math.round(b.width), Math.round(b.height)], visible: vis(i), loading: i.getAttribute('loading')})); });
    sec.querySelectorAll('video').forEach(v => { const b = v.getBoundingClientRect(); images.push(Object.assign(meta(v), {kind: 'video', src: v.currentSrc || v.getAttribute('src') || '', poster: v.getAttribute('poster') || '', rendered: [Math.round(b.width), Math.round(b.height)], autoplay: v.autoplay, loop: v.loop, muted: v.muted})); });
    sec.querySelectorAll('canvas').forEach(c => { const b = c.getBoundingClientRect(); images.push(Object.assign(meta(c), {kind: 'canvas', rendered: [Math.round(b.width), Math.round(b.height)], pixels: [c.width, c.height]})); });
    let svgBig = 0, svgAll = 0;
    sec.querySelectorAll('svg').forEach(s => { svgAll++; const b = s.getBoundingClientRect(); if (b.width >= 48 && b.height >= 48) { svgBig++; images.push(Object.assign(meta(s), {kind: 'svg', label: s.getAttribute('aria-label') || norm((s.querySelector('title') || {}).textContent) || null, rendered: [Math.round(b.width), Math.round(b.height)]})); } });
    const bgs = [];
    sec.querySelectorAll('*').forEach(e => { const bi = getComputedStyle(e).backgroundImage; if (bi && bi !== 'none') { let m; BG_URL.lastIndex = 0; while ((m = BG_URL.exec(bi))) bgs.push(m[1].slice(0, 200)); } });
    // layout
    const firstP = Array.from(sec.querySelectorAll('p')).find(vis);
    const firstItem = items.els[0] && items.n >= 2 ? items.els.find(k => Math.round(k.getBoundingClientRect().top / 12) === Math.round(items.els[0].getBoundingClientRect().top / 12)) : null;
    const container = items.parent ? items.parent : sec;
    const cc = getComputedStyle(container);
    const layout = {
      box: {top: Math.round(r.top + scrollY), height: Math.round(r.height), width: Math.round(r.width)},
      section: {background: cs.backgroundColor, background_image: cs.backgroundImage === 'none' ? null : cs.backgroundImage.slice(0, 240),
                padding: [cs.paddingTop, cs.paddingRight, cs.paddingBottom, cs.paddingLeft], radius: cs.borderTopLeftRadius,
                display: cs.display, gap: cs.rowGap, text_align: cs.textAlign},
      inner_width: (() => { let w = 0; Array.from(sec.children).forEach(k => { w = Math.max(w, k.getBoundingClientRect().width); }); return Math.round(w || r.width); })(),
      columns: items.n, items: items.els.length,
      container: {display: cc.display, flex_direction: cc.flexDirection, grid_columns: cc.gridTemplateColumns === 'none' ? null : cc.gridTemplateColumns.slice(0, 160), row_gap: cc.rowGap, column_gap: cc.columnGap},
      heading: fontOf(headingEl), body: fontOf(firstP), item_box: boxOf(firstItem),
      heading_align: headingEl ? getComputedStyle(headingEl).textAlign : null,
      heading_top: headingEl ? Math.round(headingEl.getBoundingClientRect().top - r.top) : null,
      item_heading: firstItem ? fontOf(firstItem.querySelector('h3,h4,h5')) : null, item_body: firstItem ? fontOf(firstItem.querySelector('p, span')) : null,
      faq: (() => { const t = sec.querySelector('button[aria-expanded]:not([aria-haspopup]), summary'); if (!t) return null;
        const id = t.getAttribute('aria-controls'); const reg = id ? document.getElementById(id) : null; const row = t.closest('h3') ? t.closest('h3').parentElement : t.parentElement; const rs = getComputedStyle(row);
        return {question: fontOf(t), answer: reg ? fontOf(reg.querySelector('span, p, div') || reg) : null, row_border_bottom: rs.borderBottomWidth + ' ' + rs.borderBottomStyle + ' ' + rs.borderBottomColor, trigger_padding: [getComputedStyle(t).paddingTop, getComputedStyle(t).paddingBottom]}; })(),
      cta_size: controls[0] ? controls[0].font_size : null
    };
    // motion: running animations and transitions, animation names, transitions with a duration, reveal classes
    const anims = []; const seenA = {};
    try { sec.getAnimations({subtree: true}).forEach(a => { const e = a.effect; const t = e && e.getTiming ? e.getTiming() : {};
        const name = a.animationName || a.transitionProperty || 'script'; const kind = a.animationName ? 'css-animation' : (a.transitionProperty ? 'css-transition' : 'script');
        const key = kind + '|' + name + '|' + t.duration; if (seenA[key]) { seenA[key].count++; return; }
        seenA[key] = {kind, name, duration_ms: typeof t.duration === 'number' ? Math.round(t.duration) : String(t.duration), iterations: String(t.iterations), delay_ms: Math.round(t.delay || 0), easing: t.easing || '', play_state: a.playState, count: 1};
        anims.push(seenA[key]); }); } catch (e) {}
    const animNames = {}; const trans = {}; const clsTokens = {}; let reducedGuard = 0;
    sec.querySelectorAll('*').forEach(e => { const s = getComputedStyle(e);
      if (s.animationName && s.animationName !== 'none') { const k = s.animationName + '|' + s.animationDuration + '|' + s.animationIterationCount + '|' + firstFn(s.animationTimingFunction); animNames[k] = (animNames[k] || 0) + 1; }
      const durs = s.transitionDuration.split(',').map(x => parseFloat(x) * (x.indexOf('ms') > -1 ? 1 : 1000));
      if (durs.some(d => d > 0)) { const k = s.transitionProperty.split(',').slice(0, 3).join(',') + '|' + s.transitionDuration.split(',')[0].trim() + '|' + firstFn(s.transitionTimingFunction); trans[k] = (trans[k] || 0) + 1; }
      (typeof e.className === 'string' ? e.className : '').split(/\s+/).forEach(t => { if (t && MOTION_CLS.test(t) && t.length < 60) clsTokens[t] = (clsTokens[t] || 0) + 1; });
      if (/motion-reduce/.test(typeof e.className === 'string' ? e.className : '')) reducedGuard++; });
    const marquee = Object.keys(animNames).some(k => /marquee|ticker|scroll|loop/i.test(k)) || Object.keys(clsTokens).some(t => /marquee|ticker/i.test(t));
    const lottie = !!sec.querySelector('lottie-player, dotlottie-player, [data-lottie], [class*=lottie]');
    const svgAnim = sec.querySelectorAll('animate, animateTransform, animateMotion').length;
    const motion = {
      animations: anims,
      animation_names: Object.keys(animNames).map(k => { const p = k.split('|'); return {name: p[0], duration: p[1], iterations: p[2], easing: p[3], elements: animNames[k]}; }),
      transitions: Object.keys(trans).slice(0, 24).map(k => { const p = k.split('|'); return {property: p[0], duration: p[1], easing: p[2], elements: trans[k]}; }),
      motion_classes: clsTokens,
      reduced_motion_guards: reducedGuard,
      media: {video: sec.querySelectorAll('video').length, canvas: sec.querySelectorAll('canvas').length, lottie: lottie, svg_animate_elements: svgAnim, marquee: marquee, svg_total: svgAll, svg_large: svgBig},
      scroll: {}
    };
    // pre-scroll snapshot, kept in window.__cap so the second read can compare
    const all = Array.from(sec.querySelectorAll('*'));
    if (opts && opts.pre) { window.__cap[idx] = {classes: all.map(e => (typeof e.className === 'string' ? e.className : '')), opacity: all.map(e => parseFloat(getComputedStyle(e).opacity)),
                             transform: all.map(e => getComputedStyle(e).transform !== 'none'), data: all.map(e => Array.from(e.attributes).filter(a => /^data-/.test(a.name) && MOTION_CLS.test(a.name + a.value)).map(a => a.name + '=' + a.value).join(' ')) }; }
    else if (window.__cap[idx]) { const pre = window.__cap[idx]; const hidden_then_shown = [], cls = {appeared: {}, removed: {}}; let moved = 0, dchg = {};
      all.forEach((e, i) => { const o = parseFloat(getComputedStyle(e).opacity); if (pre.opacity[i] !== undefined && pre.opacity[i] < 0.05 && o > 0.95) hidden_then_shown.push(1);
        if (pre.transform[i] !== undefined && pre.transform[i] && getComputedStyle(e).transform === 'none') moved++;
        const a = new Set((pre.classes[i] || '').split(/\s+/)), b = new Set((typeof e.className === 'string' ? e.className : '').split(/\s+/));
        b.forEach(t => { if (t && !a.has(t)) cls.appeared[t] = (cls.appeared[t] || 0) + 1; }); a.forEach(t => { if (t && !b.has(t)) cls.removed[t] = (cls.removed[t] || 0) + 1; });
        const dd = Array.from(e.attributes).filter(x => /^data-/.test(x.name) && MOTION_CLS.test(x.name + x.value)).map(x => x.name + '=' + x.value).join(' ');
        if (pre.data[i] !== undefined && pre.data[i] !== dd) dchg[(pre.data[i] || '(none)') + ' -> ' + (dd || '(none)')] = (dchg[(pre.data[i] || '(none)') + ' -> ' + (dd || '(none)')] || 0) + 1; });
      motion.scroll = {faded_in_elements: hidden_then_shown.length, transform_cleared_elements: moved, classes_appeared: cls.appeared, classes_removed: cls.removed, data_changes: dchg}; }
    const name = (sec.id || '').trim() || slug(headingEl ? headingEl.innerText : '') || ('section-' + (idx + 1));
    return {index: idx, dom_id: sec.id || null, name: name, tag: sec.tagName.toLowerCase(), heading: headingEl ? norm(headingEl.innerText) : '',
            headings: Array.from(sec.querySelectorAll('h1,h2,h3,h4,h5,h6')).filter(vis).map(h => ({tag: h.tagName.toLowerCase(), text: norm(h.innerText)})),
            lines: ls, controls: controls, images: images, background_images: Array.from(new Set(bgs)).slice(0, 12),
            expected: {controls: ctlEls.length, accordion_triggers: sec.querySelectorAll(FAQ_TRIGGER).length, tabs: sec.querySelectorAll('[role=tab]').length},
            layout: layout, motion: motion};
  });
  return {sections: outSecs, doc_height: Math.max(document.body.scrollHeight, document.documentElement.scrollHeight), expected_sections: secs.length};
}
"""

PAGE_JS = r"""
() => {
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  const meta = document.querySelector('meta[name="description"]');
  const types = [];
  document.querySelectorAll('script[type="application/ld+json"]').forEach(s => { try { const walk = o => { if (Array.isArray(o)) o.forEach(walk); else if (o && typeof o === 'object') { if (o['@type']) [].concat(o['@type']).forEach(t => types.push(String(t))); if (o['@graph']) walk(o['@graph']); } }; walk(JSON.parse(s.textContent)); } catch (e) {} });
  const kf = new Set(); let sheets = 0, blocked = 0; const kfCss = {}; const revealCss = [];
  const eachRule = (rules, fn) => Array.from(rules).forEach(r => { fn(r); if (r.cssRules && r.type !== CSSRule.KEYFRAMES_RULE) eachRule(r.cssRules, fn); });
  Array.from(document.styleSheets).forEach(ss => { sheets++; try { eachRule(ss.cssRules, r => {
      if (r.type === CSSRule.KEYFRAMES_RULE) { kf.add(r.name); if (r.cssText.length < 900 && Object.keys(kfCss).length < 80) kfCss[r.name] = r.cssText; }
      else if (r.type === CSSRule.STYLE_RULE && /reveal|is-seen|is-current/.test(r.selectorText || '') && r.cssText.length < 700 && revealCss.length < 40) revealCss.push(r.cssText); }); } catch (e) { blocked++; } });
  const fonts = Array.from(new Set(Array.from(document.fonts).filter(f => f.status === 'loaded').map(f => f.family.replace(/["']/g, ''))));
  const cs = getComputedStyle(document.body);
  const canon = document.querySelector('link[rel=canonical]');
  const header = document.querySelector('header');
  const nav = {sticky: false};
  if (header) { let e = header; while (e && e !== document.documentElement) { const p = getComputedStyle(e).position; if (p === 'fixed' || p === 'sticky') { nav.sticky = true; break; } e = e.parentElement; } }
  return {title: document.title, meta_description: meta ? meta.content : '', h1_count: document.querySelectorAll('h1').length, json_ld_types: Array.from(new Set(types)),
          canonical: canon ? canon.href : '', lang: document.documentElement.lang || '', final_url: location.href,
          keyframes: Array.from(kf), keyframes_css: kfCss, reveal_css: revealCss, stylesheets: sheets, stylesheets_unreadable: blocked, fonts_loaded: fonts,
          body: {font: cs.fontFamily.split(',')[0].replace(/["']/g, ''), size: cs.fontSize, color: cs.color, background: cs.backgroundColor},
          nav: nav, scripts_with_lottie: Array.from(document.scripts).some(s => /lottie/i.test(s.src))};
}
"""

LINKS_JS = r"""
(rootSel) => {
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  const root = document.querySelector(rootSel) || document.body;
  const vis = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  return Array.from(root.querySelectorAll('a[href]')).filter(vis).map(a => ({label: norm(a.innerText) || norm(a.getAttribute('aria-label')), href: a.href}));
}
"""

# ---------------------------------------------------------------------------------------------------------------
# Pure helpers. No browser. These run in the self test.
# ---------------------------------------------------------------------------------------------------------------
DOUBLE_RUN = re.compile(r"\b((?:\S+ ){1,3}?\S+)\s+\1\b|\b(\S+) \2\b")


def clean_text(text):
    """One space between words. No stray controls. Nothing else is changed."""
    return re.sub(r"\s+", " ", re.sub(r"[​­﻿]", "", str(text or ""))).strip()


def doubled_pairs(text):
    """Find 'ISO ISO 27001 27001' (interleaved doubles) and 'word word' runs. Return the matched strings."""
    toks = text.split()
    hits = []
    for i in range(len(toks) - 3):
        if toks[i] == toks[i + 1] and toks[i + 2] == toks[i + 3] and toks[i] != toks[i + 2]:
            hits.append(" ".join(toks[i:i + 4]))
    for i in range(len(toks) - 1):
        a, b = toks[i], toks[i + 1]
        if a == b and re.match(r"^[A-Za-z0-9]{2,}$", a) and not a.lower() in ("that", "had", "very"):
            hits.append("%s %s" % (a, b))
    return hits


def run_joined(text):
    """Find menu-like words joined without a space, like 'ProductsDevelopers'. Known brand names are skipped."""
    hits = []
    for tok in re.findall(r"[A-Za-z][A-Za-z0-9'-]+", text):
        if re.search(r"[a-z][A-Z][a-z]", tok) and not CAMEL_OK.match(tok):
            hits.append(tok)
    return hits


def block_text(block):
    return " ".join(l["text"] for l in block.get("lines") or [])


def canonical_hash(obj):
    body = dict((k, v) for k, v in obj.items() if k != "sha256")
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def fidelity(cap, folder=None):
    """Return (faults, checks_run). A fault is a plain sentence that names the block, the item or the control."""
    faults, ran = [], []

    def ck(name):
        ran.append(name)
    blocks = cap.get("blocks") or []
    exp = (cap.get("page") or {}).get("expected_sections")
    ck("block count")
    if not blocks:
        faults.append("block count: the capture holds no block.")
    if exp is not None and exp != len(blocks):
        faults.append("block count: the page has %s top-level sections and the capture holds %s blocks." % (exp, len(blocks)))
    per_w = (cap.get("page") or {}).get("sections_by_width") or {}
    for w, names in per_w.items():
        if names != [b.get("name") for b in blocks]:
            faults.append("block count: the %s px pass found sections %s. The 1280 pass found %s." % (w, names, [b.get("name") for b in blocks]))
    names = [b.get("name") for b in blocks]
    if len(set(names)) != len(names):
        faults.append("block names: two blocks share a name (%s)." % ", ".join(sorted(set(n for n in names if names.count(n) > 1))))
    ck("faq answers")
    for b in blocks:
        exp_acc = (b.get("expected") or {}).get("accordion_triggers", 0)
        faq = b.get("faq") or []
        tog = b.get("toggles") or []
        if exp_acc != len(faq) + len(tog):
            faults.append("faq: block '%s' has %d question buttons and the capture holds %d answers." % (b.get("name"), exp_acc, len(faq) + len(tog)))
        for t in tog:
            if not t.get("opened"):
                faults.append("faq: block '%s', the show-more button '%s' was not opened." % (b.get("name"), t.get("label")))
        txt = block_text(b)
        for i, f in enumerate(faq, 1):
            if len(clean_text(f.get("answer"))) < 10:
                faults.append("faq: block '%s', question %d ('%s') has no answer text." % (b.get("name"), i, clean_text(f.get("question"))[:60]))
            elif not f.get("opened"):
                faults.append("faq: block '%s', question %d ('%s') was not opened." % (b.get("name"), i, clean_text(f.get("question"))[:60]))
            elif clean_text(f["answer"])[:40] not in txt:
                faults.append("faq: block '%s', the answer to '%s' is not in the block text." % (b.get("name"), clean_text(f.get("question"))[:60]))
        exp_tabs = (b.get("expected") or {}).get("tabs", 0)
        if exp_tabs != len(b.get("tabs") or []):
            faults.append("tabs: block '%s' has %d tabs and the capture holds %d tab panels." % (b.get("name"), exp_tabs, len(b.get("tabs") or [])))
    ck("controls")
    for b in blocks:
        cs = b.get("controls_detail") or []
        exp_c = (b.get("expected") or {}).get("controls", 0)
        if exp_c != len(cs):
            faults.append("controls: block '%s' has %d controls on the page and the capture holds %d." % (b.get("name"), exp_c, len(cs)))
        for c in cs:
            if not clean_text(c.get("label")):
                faults.append("controls: block '%s' holds a %s with no label (target %s)." % (b.get("name"), c.get("kind"), c.get("href")))
            if c.get("kind") == "link" and not c.get("href"):
                faults.append("controls: block '%s', link '%s' has no target." % (b.get("name"), c.get("label")))
        shown = set(clean_text(l["text"]) for l in b.get("lines") or [] if l.get("role") in ("cta", "question"))
        for c in cs:
            lab = clean_text(c.get("label"))
            if c.get("kind") in ("button", "accordion") and lab and lab not in shown and lab not in block_text(b):
                faults.append("controls: block '%s', button '%s' is missing from the block text." % (b.get("name"), lab))
    ck("text clean")
    for b in blocks:
        t = block_text(b)
        if not clean_text(t):
            faults.append("text: block '%s' has no text." % b.get("name"))
        for d in doubled_pairs(t):
            faults.append("text: block '%s' holds a doubled run '%s'." % (b.get("name"), d))
        for r in run_joined(t):
            faults.append("text: block '%s' holds joined words '%s'." % (b.get("name"), r))
        if "  " in t:
            faults.append("text: block '%s' holds a double space." % b.get("name"))
    ck("images")
    for b in blocks:
        for im in b.get("images_detail") or []:
            if im.get("kind") == "img" and not im.get("src"):
                faults.append("images: block '%s' holds an image with no source." % b.get("name"))
    ck("layout and motion facts")
    for b in blocks:
        for w in (cap.get("widths") or []):
            if not (b.get("layout") or {}).get(str(w)):
                faults.append("layout: block '%s' has no layout facts at %s px." % (b.get("name"), w))
        if "animations" not in (b.get("motion") or {}):
            faults.append("motion: block '%s' has no motion facts." % b.get("name"))
    ck("page facts")
    seo = cap.get("seo") or {}
    if not seo.get("title"):
        faults.append("page facts: the title is empty.")
    if seo.get("h1_count") != 1:
        faults.append("page facts: the page has %s H1 elements, not 1." % seo.get("h1_count"))
    ck("screenshots")
    if folder is not None:
        for w in cap.get("widths") or []:
            p = os.path.join(folder, "live-%s.png" % w)
            if not os.path.isfile(p) or os.path.getsize(p) < 2000:
                faults.append("screenshots: live-%s.png is missing or empty." % w)
        for b in blocks:
            for s in b.get("screenshots") or []:
                p = os.path.join(folder, s)
                if not os.path.isfile(p) or os.path.getsize(p) < 500:
                    faults.append("screenshots: %s is missing or empty." % s)
    ck("hash")
    if cap.get("sha256") and cap["sha256"] != canonical_hash(cap):
        faults.append("hash: capture.json changed after the hash was written.")
    elif not cap.get("sha256"):
        faults.append("hash: capture.json has no sha256.")
    return faults, ran


def apply_names(blocks, names_map):
    """Rename blocks by the page's capture_names map (dom id or capture name -> readable name). The first block is 'hero'."""
    used = set()
    for i, b in enumerate(blocks):
        n = b.get("name")
        if i == 0:
            n = "hero"
        elif names_map and (b.get("dom_id") in names_map or n in names_map):
            n = names_map.get(b.get("dom_id")) or names_map.get(n)
        while n in used:
            n = n + "-2"
        used.add(n)
        b["name"] = n
    return blocks


def kind_of(b):
    """A coarse kind from the schema's list, read from the facts. A hint for the person, not a rule."""
    n = (b.get("name") or "")
    if n == "hero":
        return "hero"
    if b.get("faq") and len(b["faq"]) >= 3:
        return "faq"
    if b.get("tabs"):
        return "tabs"
    if (b.get("layout") or {}).get("1280", {}).get("columns", 1) >= 3:
        return "cards"
    if n in ("footer", "close"):
        return "cta"
    return "other" if not b.get("lines") else "text"


def assemble(url, today, pages_1280, pages_390, page_facts, extras, names_map):
    """Build the capture dict from the two width passes and the opened items. extras: {name: {faq, tabs}} keyed by block index."""
    blocks = []
    p390 = dict((s["index"], s) for s in pages_390["sections"])
    for s in pages_1280["sections"]:
        i = s["index"]
        e = extras.get(i, {})
        faq = e.get("faq") or []
        b = {"id": "b%02d" % (i + 1), "name": s["name"], "dom_id": s["dom_id"], "kind": "other", "heading": s["heading"], "headings": s["headings"],
             "text": clean_text(" ".join(l["text"] for l in s["lines"])), "lines": s["lines"],
             "controls": [c["label"] for c in s["controls"] if c["label"]], "controls_detail": s["controls"],
             "images": len(s["images"]), "images_detail": s["images"], "background_images": s["background_images"],
             "opened": bool(faq or e.get("tabs") or e.get("toggles")), "faq": faq, "tabs": e.get("tabs") or [], "toggles": e.get("toggles") or [], "expected": s["expected"],
             "layout": {"1280": s["layout"], "390": (p390.get(i) or {}).get("layout")},
             "layout_counts_390": {"controls": len((p390.get(i) or {}).get("controls") or []), "lines": len((p390.get(i) or {}).get("lines") or [])},
             "motion": s["motion"], "motion_390": (p390.get(i) or {}).get("motion"), "screenshots": []}
        blocks.append(b)
    apply_names(blocks, names_map)
    for b in blocks:
        b["kind"] = kind_of(b)
    d = datetime.date.fromisoformat(today)
    cap = {"url": url, "captured_on": today, "review_by": (d + datetime.timedelta(days=REVIEW_DAYS)).isoformat(), "widths": list(WIDTHS),
           "blocks": blocks, "click_path": extras.get("click_path") or [],
           "seo": {"title": page_facts.get("title"), "meta_description": page_facts.get("meta_description"), "h1_count": page_facts.get("h1_count"),
                   "json_ld_types": page_facts.get("json_ld_types")},
           "page": dict(page_facts, expected_sections=pages_1280["expected_sections"], doc_height_1280=pages_1280["doc_height"], doc_height_390=pages_390["doc_height"],
                        sections_by_width={"390": [b["name"] for b in blocks][:len(pages_390["sections"])] if len(pages_390["sections"]) == len(blocks) else
                                           ["(%d sections)" % len(pages_390["sections"])]}),
           "header": extras.get("header") or {}, "footer": extras.get("footer") or {},
           "self_check": {"gaps": []}}
    return cap


# ---------------------------------------------------------------------------------------------------------------
# The browser run
# ---------------------------------------------------------------------------------------------------------------
def goto(page, url):
    try:
        page.goto(url, wait_until="networkidle", timeout=45000)
    except Exception:  # noqa: BLE001
        page.goto(url, wait_until="load", timeout=45000)


def scroll_through(page):
    h = page.evaluate("Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
    for y in range(0, min(h, 40000), 500):
        page.evaluate("window.scrollTo(0,%d)" % y)
        page.wait_for_timeout(140)
    page.wait_for_timeout(600)


def open_items(page, sec_index):
    """Open every FAQ item, tab and show-more button in section sec_index. Return (faq, tabs, toggles). Each answer is read right after its click."""
    faq, tabs, toggles = [], [], []
    n = page.evaluate("""(i) => { const main = document.querySelector('main') || document.body;
        const secs = Array.from(main.querySelectorAll('section')).filter(s => !s.parentElement.closest('section'));
        const s = secs[i]; return s ? s.querySelectorAll('button[aria-expanded]:not([aria-haspopup]), summary').length : 0; }""", sec_index)
    for k in range(n):
        res = page.evaluate("""([i, k]) => { const main = document.querySelector('main') || document.body;
            const secs = Array.from(main.querySelectorAll('section')).filter(s => !s.parentElement.closest('section'));
            const t = secs[i].querySelectorAll('button[aria-expanded]:not([aria-haspopup]), summary')[k];
            t.scrollIntoView({block: 'center'});
            const q = (t.innerText || '').replace(/\\s+/g, ' ').trim();
            const was = t.tagName === 'SUMMARY' ? t.parentElement.open : t.getAttribute('aria-expanded') === 'true';
            if (!was) t.click();
            return {q: q, was: was}; }""", [sec_index, k])
        page.wait_for_timeout(450)
        ans = page.evaluate("""([i, k]) => { const main = document.querySelector('main') || document.body;
            const secs = Array.from(main.querySelectorAll('section')).filter(s => !s.parentElement.closest('section'));
            const t = secs[i].querySelectorAll('button[aria-expanded]:not([aria-haspopup]), summary')[k];
            const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
            let region = null;
            if (t.tagName === 'SUMMARY') region = t.parentElement;
            else { const id = t.getAttribute('aria-controls'); region = id ? document.getElementById(id) : null; }
            const open = t.tagName === 'SUMMARY' ? t.parentElement.open : t.getAttribute('aria-expanded') === 'true';
            let text = region ? norm(region.innerText || region.textContent) : '';
            if (t.tagName === 'SUMMARY') text = norm(text.replace(norm(t.innerText), ''));
            const links = region ? Array.from(region.querySelectorAll('a[href]')).map(a => ({label: norm(a.innerText), href: a.href})) : [];
            return {open: open, text: text, links: links, has_region: !!region && region.getAttribute('role') !== null || (t.tagName === 'SUMMARY')}; }""", [sec_index, k])
        if ans["has_region"]:
            faq.append({"question": res["q"], "answer": ans["text"], "links": ans["links"], "opened": bool(ans["open"])})
        else:  # a show-more button with no answer box: record it as a toggle. The newly shown items are in the block text.
            toggles.append({"label": res["q"], "opened": bool(ans["open"])})
    nt = page.evaluate("""(i) => { const main = document.querySelector('main') || document.body;
        const secs = Array.from(main.querySelectorAll('section')).filter(s => !s.parentElement.closest('section'));
        return secs[i] ? secs[i].querySelectorAll('[role=tab]').length : 0; }""", sec_index)
    for k in range(nt):
        page.evaluate("""([i, k]) => { const main = document.querySelector('main') || document.body;
            const secs = Array.from(main.querySelectorAll('section')).filter(s => !s.parentElement.closest('section'));
            secs[i].querySelectorAll('[role=tab]')[k].click(); }""", [sec_index, k])
        page.wait_for_timeout(350)
        tabs.append(page.evaluate("""([i, k]) => { const main = document.querySelector('main') || document.body;
            const secs = Array.from(main.querySelectorAll('section')).filter(s => !s.parentElement.closest('section'));
            const t = secs[i].querySelectorAll('[role=tab]')[k]; const id = t.getAttribute('aria-controls'); const p = id ? document.getElementById(id) : null;
            return {label: (t.innerText || '').replace(/\\s+/g, ' ').trim(), panel_text: p ? (p.innerText || '').replace(/\\s+/g, ' ').trim() : ''}; }""", [sec_index, k]))
    # leave every item open so the block screenshot shows the answers
    page.evaluate("""(i) => { const main = document.querySelector('main') || document.body;
        const secs = Array.from(main.querySelectorAll('section')).filter(s => !s.parentElement.closest('section'));
        secs[i].querySelectorAll('button[aria-expanded="false"]:not([aria-haspopup])').forEach(b => b.click());
        secs[i].querySelectorAll('details:not([open])').forEach(d => d.open = true); }""", sec_index)
    page.wait_for_timeout(450)
    return faq, tabs, toggles


def open_menus(page):
    """Open each header drop-down and read the links it shows. Return a dict."""
    out = {"menus": [], "links_always_shown": []}
    out["links_always_shown"] = page.evaluate(LINKS_JS, "header")
    btns = page.query_selector_all("header button[aria-haspopup]")
    for b in btns:
        try:
            label = (b.get_attribute("aria-label") or b.inner_text() or "").strip()
            before = set((l["label"], l["href"]) for l in page.evaluate(LINKS_JS, "body"))
            b.click()
            page.wait_for_timeout(450)
            after = page.evaluate(LINKS_JS, "body")
            new = [l for l in after if (l["label"], l["href"]) not in before]
            out["menus"].append({"menu": label, "links": new})
            page.keyboard.press("Escape")
            page.wait_for_timeout(250)
            if b.get_attribute("aria-expanded") == "true":
                b.click()
                page.wait_for_timeout(250)
        except Exception as e:  # noqa: BLE001
            out["menus"].append({"menu": "(error)", "links": [], "error": str(e)[:160]})
    return out


def run_capture(project, page_slug, url, today, names_map, out_print=print):
    from playwright.sync_api import sync_playwright
    folder = os.path.join(project, "pages", page_slug, "capture", today)
    if os.path.exists(os.path.join(folder, "capture.json")):
        out_print("STOP   %s already exists. A dated folder is never overwritten. Use a new date." % common.rel(project, folder))
        return 1
    os.makedirs(os.path.join(folder, "blocks"), exist_ok=True)
    passes, shots = {}, {}
    extras, page_facts = {}, {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for w in WIDTHS:
                ctx = browser.new_context(viewport={"width": w, "height": HEIGHTS[w]}, user_agent=UA)
                pg = ctx.new_page()
                goto(pg, url)
                pg.wait_for_timeout(1800)
                pre = pg.evaluate(EXTRACT_JS, {"pre": True})  # before any scroll: the state a scroll effect starts from
                scroll_through(pg)
                pg.evaluate("window.scrollTo(0,0)")
                pg.wait_for_timeout(500)
                if w == WIDTHS[0]:
                    page_facts = pg.evaluate(PAGE_JS)
                pg.screenshot(path=os.path.join(folder, "live-%d.png" % w), full_page=True)  # the page as a visitor first sees it
                if w == WIDTHS[0]:
                    extras["header"] = open_menus(pg)
                    for s in pre["sections"]:
                        faq, tabs, toggles = open_items(pg, s["index"])
                        if faq or tabs or toggles:
                            extras[s["index"]] = {"faq": faq, "tabs": tabs, "toggles": toggles}
                    pg.evaluate("window.scrollTo(0,0)")
                    pg.wait_for_timeout(400)
                after = pg.evaluate(EXTRACT_JS, {"pre": False})
                passes[w] = after
                for s in after["sections"]:
                    el = pg.query_selector_all("main section")
                    try:
                        handle = pg.evaluate_handle("""(i) => { const main = document.querySelector('main') || document.body;
                            return Array.from(main.querySelectorAll('section')).filter(s => !s.parentElement.closest('section'))[i]; }""", s["index"])
                        rel = "blocks/%s-%d.png" % (s["name"], w)
                        handle.as_element().screenshot(path=os.path.join(folder, rel))
                        shots.setdefault(s["index"], []).append(rel)
                    except Exception as e:  # noqa: BLE001
                        out_print("WARN   block %s at %d px: screenshot failed: %s" % (s["name"], w, str(e)[:100]))
                if w == WIDTHS[0]:
                    extras["footer"] = {"links": pg.evaluate(LINKS_JS, "footer")}
                ctx.close()
                time.sleep(2)
        finally:
            browser.close()
    cap = assemble(url, today, passes[1280], passes[390], page_facts, extras, names_map)
    # sections_by_width: record the names the 390 pass saw, so a different count shows as a fault
    names390 = [s["name"] for s in passes[390]["sections"]]
    cap["page"]["sections_by_width"] = {"390": names390} if len(names390) != len(cap["blocks"]) else {}
    for b, s in zip(cap["blocks"], passes[1280]["sections"]):
        b["screenshots"] = ["blocks/%s-%d.png" % (b["name"], w) for w in WIDTHS]
        # files were named with the raw name. Rename them to the final block name.
        for w in WIDTHS:
            src = os.path.join(folder, "blocks", "%s-%d.png" % (s["name"], w))
            dst = os.path.join(folder, "blocks", "%s-%d.png" % (b["name"], w))
            if src != dst and os.path.isfile(src):
                os.replace(src, dst)
    for c in (cap["header"].get("menus") or []):
        cap["click_path"].append({"control": c["menu"], "target_url": "", "status": "captured" if not c.get("error") else "failed"})
    hero = cap["blocks"][0] if cap["blocks"] else {}
    for c in hero.get("controls_detail") or []:
        if c["kind"] in ("link", "button") and c.get("href"):
            cap["click_path"].append({"control": c["label"] or "(no label)", "target_url": c["href"], "status": "not_collected"})
    faults, ran = fidelity(dict(cap, sha256=None), folder)
    faults = [f for f in faults if not f.startswith("hash:")]
    cap["fidelity"] = {"ok": not faults, "faults": faults, "checks_run": ran}
    cap["sha256"] = canonical_hash(cap)
    common.write_file(os.path.join(folder, "capture.json"), json.dumps(cap, indent=1, ensure_ascii=False) + "\n")
    common.write_file(os.path.join(folder, "capture.sha256"), "%s  capture.json (sha256 of the JSON without its sha256 field)\n" % cap["sha256"])
    out_print("WROTE   %s (%d blocks)" % (common.rel(project, os.path.join(folder, "capture.json")), len(cap["blocks"])))
    out_print("fidelity: %s" % ("PASS" if not faults else "%d fault(s)" % len(faults)))
    for f in faults:
        out_print("FAULT   %s" % f)
    return 0 if not faults else 1


def check_folder(folder, out_print=print):
    path = os.path.join(folder, "capture.json")
    if not os.path.isfile(path):
        out_print("ERROR   %s is missing." % path)
        return 1
    cap = common.load_json(path)
    faults, ran = fidelity(cap, folder)
    for f in faults:
        out_print("FAULT   %s" % f)
    out_print("checks: %s" % ", ".join(ran))
    out_print("fidelity: %s" % ("PASS" if not faults else "%d fault(s)" % len(faults)))
    return 0 if not faults else 1


# ---------------------------------------------------------------------------------------------------------------
def _good_cap():
    lines = [{"text": "Hero line", "role": "heading", "tag": "h1", "item": -1}, {"text": "Questions", "role": "heading", "tag": "h2", "item": -1},
             {"text": "What is X?", "role": "question", "tag": "button", "item": 0}, {"text": "X is a thing you can use today.", "role": "answer", "tag": "div", "item": 0}]
    blocks = [
        {"name": "hero", "lines": [lines[0], {"text": "Go now", "role": "cta", "tag": "a", "item": -1}], "expected": {"controls": 1, "accordion_triggers": 0, "tabs": 0},
         "controls_detail": [{"label": "Go now", "kind": "link", "href": "https://e.com/go"}], "images_detail": [{"kind": "img", "src": "https://e.com/a.png"}],
         "layout": {"1280": {"columns": 1}, "390": {"columns": 1}}, "motion": {"animations": []}, "faq": [], "tabs": [], "screenshots": []},
        {"name": "faq", "lines": lines[1:], "expected": {"controls": 1, "accordion_triggers": 1, "tabs": 0},
         "controls_detail": [{"label": "What is X?", "kind": "accordion", "href": None}], "images_detail": [],
         "layout": {"1280": {"columns": 1}, "390": {"columns": 1}}, "motion": {"animations": []},
         "faq": [{"question": "What is X?", "answer": "X is a thing you can use today.", "opened": True}], "tabs": [], "screenshots": []}]
    cap = {"url": "https://e.com", "widths": [1280, 390], "blocks": blocks, "seo": {"title": "T", "h1_count": 1},
           "page": {"expected_sections": 2, "sections_by_width": {}}}
    cap["sha256"] = canonical_hash(cap)
    return cap


def selftest():
    import copy
    import tempfile
    import shutil
    st = common.SelfTest("capture")
    cap = _good_cap()
    f, ran = fidelity(cap)
    st.expect(f == [], "a clean capture has no fault (%s)" % "; ".join(f))
    st.expect(clean_text("a ​ b\n  c") == "a b c", "clean_text keeps one space between words")
    st.expect(doubled_pairs("ISO ISO 27001 27001 certified") and not doubled_pairs("ISO 27001 and SOC 2 Type II"), "an interleaved double like 'ISO ISO 27001 27001' is found, a clean run is not")
    st.expect(run_joined("Products Developers ProductsDevelopers OpenAI-compatible") == ["ProductsDevelopers"], "joined menu words are found and brand names are skipped")
    c = copy.deepcopy(cap)
    c["page"]["expected_sections"] = 3
    st.expect(any("block count" in x and "3 top-level" in x for x in fidelity(c)[0]), "a missing block fails with the counts")
    c = copy.deepcopy(cap)
    c["blocks"][1]["faq"] = []
    st.expect(any("faq: block 'faq' has 1 question buttons" in x for x in fidelity(c)[0]), "a FAQ answer that is not captured fails with the block name")
    c = copy.deepcopy(cap)
    c["blocks"][1]["faq"][0]["answer"] = ""
    st.expect(any("has no answer text" in x for x in fidelity(c)[0]), "an empty FAQ answer fails with the question")
    c = copy.deepcopy(cap)
    c["blocks"][0]["controls_detail"] = []
    st.expect(any("controls: block 'hero' has 1 controls" in x for x in fidelity(c)[0]), "a missing control fails with the block name")
    c = copy.deepcopy(cap)
    c["blocks"][0]["lines"].append({"text": "ISO ISO 27001 27001", "role": "text", "tag": "p", "item": -1})
    st.expect(any("doubled run" in x for x in fidelity(c)[0]), "a doubled run in the text fails")
    c = copy.deepcopy(cap)
    c["blocks"][0]["lines"].append({"text": "ProductsDevelopersResources", "role": "text", "tag": "p", "item": -1})
    st.expect(any("joined" in x for x in fidelity(c)[0]), "joined words in the text fail")
    c = copy.deepcopy(cap)
    c["blocks"][1]["motion"] = {}
    st.expect(any("no motion facts" in x for x in fidelity(c)[0]), "a block with no motion facts fails")
    c = copy.deepcopy(cap)
    c["blocks"][0]["name"] = "faq"
    st.expect(any("share a name" in x for x in fidelity(c)[0]), "two blocks with one name fail")
    c = copy.deepcopy(cap)
    c["seo"]["title"] = "Changed"
    st.expect(any("hash: capture.json changed" in x for x in fidelity(c)[0]), "a changed file fails the hash check")
    tmp = tempfile.mkdtemp(prefix="capture-selftest-")
    try:
        st.expect(any("live-1280.png is missing" in x for x in fidelity(cap, tmp)[0]), "a missing screenshot fails")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bl = [{"name": "x", "dom_id": None}, {"name": "platform", "dom_id": "platform"}, {"name": "build-with-frontier", "dom_id": None}]
    apply_names(bl, {"platform": "scales-with-demand", "build-with-frontier": "close"})
    st.expect([b["name"] for b in bl] == ["hero", "scales-with-demand", "close"], "block names follow the page's capture_names map and the first block is the hero")
    # the browser part runs only when Playwright can be imported (it cannot under python3 -I)
    try:
        from playwright.sync_api import sync_playwright
    except Exception:  # noqa: BLE001
        print("SKIP    browser self test: Playwright is not importable here (run with plain python3 to include it)")
        return st.done()
    html = """<html><head><title>T</title><meta name="description" content="D"><style>
      @keyframes slide { from { transform: translateX(0);} to { transform: translateX(-50px);} }
      .mq { animation: slide 4s linear infinite; } .btn { background:#06f; color:#fff; border-radius:20px; padding:8px 16px; display:inline-block; transition: background 200ms ease; }
      .acc-p { height:0; overflow:hidden; } </style></head><body><main>
      <section id="top"><h1>Big</h1><p>Sub line here for all.</p><a class="btn" href="/go">Get started</a><div class="mq">Marquee text</div></section>
      <section id="cards" style="display:flex;gap:16px"><div style="width:200px;height:100px"><h3>One</h3><p>First card.</p></div><div style="width:200px;height:100px"><h3>Two</h3><p>Second card.</p></div><div style="width:200px;height:100px"><h3>Three</h3><p>Third card.</p></div></section>
      <section id="faq"><h2>FAQ</h2><div><h3><button aria-expanded="false" aria-controls="p1" onclick="this.setAttribute('aria-expanded','true');document.getElementById('p1').style.height='auto'">Why X?</button></h3><div id="p1" class="acc-p" role="region" aria-labelledby="b1"><span>Because X is useful in many cases. <a href="/more">More</a></span></div></div></section>
      </main></body></html>"""
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 800})
        pg.set_content(html)
        pg.wait_for_timeout(300)
        d = pg.evaluate(EXTRACT_JS, {"pre": False})
        faq, tabs, toggles = open_items(pg, 2)
        pf = pg.evaluate(PAGE_JS)
        b.close()
    names = [s["name"] for s in d["sections"]]
    st.expect(names == ["top", "cards", "faq"] and d["expected_sections"] == 3, "the browser read finds the three sections in order (%s)" % names)
    st.expect(d["sections"][1]["layout"]["columns"] == 3, "three cards in a row read as 3 columns")
    st.expect(any(a["name"] == "slide" for a in d["sections"][0]["motion"]["animations"]), "a running CSS animation is recorded")
    st.expect(any(a["name"] == "slide" and a["kind"] == "css-animation" for a in d["sections"][0]["motion"]["animations"]), "the animation name and kind are recorded")
    st.expect(any(c["label"] == "Get started" and c["look"] == "filled" and c["href"].endswith("/go") for c in d["sections"][0]["controls"]), "a button keeps its label, target and look")
    st.expect(len(faq) == 1 and faq[0]["answer"].startswith("Because X is useful") and faq[0]["opened"], "opening a FAQ item reads its answer")
    st.expect(pf["h1_count"] == 1 and pf["title"] == "T" and "slide" in pf["keyframes"], "page facts: title, H1 count and keyframes")
    return st.done()


def shoot(html_file, prefix):
    """Screenshot a local HTML file at the capture widths. Reads the local file only. Waits so reveal effects finish."""
    from playwright.sync_api import sync_playwright
    url = "file://" + os.path.abspath(html_file)
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w in WIDTHS:
            ctx = b.new_context(viewport={"width": w, "height": HEIGHTS[w]})
            pg = ctx.new_page()
            pg.goto(url, wait_until="load")
            h = pg.evaluate("Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
            for y in range(0, min(h, 40000), 500):
                pg.evaluate("window.scrollTo(0,%d)" % y)
                pg.wait_for_timeout(120)
            pg.evaluate("window.scrollTo(0,0)")
            pg.wait_for_timeout(700)
            pg.screenshot(path="%s-%d.png" % (prefix, w), full_page=True)
            print("WROTE   %s-%d.png (page height %d px)" % (prefix, w, h))
            ctx.close()
        b.close()
    return 0


def main(argv):
    if "--selftest" in argv:
        return selftest()

    def arg(name, default=None):
        return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else default
    if "--screenshot" in argv:  # --screenshot FILE.html PREFIX : writes PREFIX-1280.png and PREFIX-390.png (full page)
        i = argv.index("--screenshot")
        return shoot(argv[i + 1], argv[i + 2])
    if "--check" in argv:
        return check_folder(arg("--check"))
    page = arg("--page")
    if not page:
        print("Use: python3 agent/capture.py --page <slug> [--url URL] [--date YYYY-MM-DD]   (plain python3, not -I)")
        return 2
    prof = common.load_profile(common.PROJECT, page, raw=True) or {}
    url = arg("--url") or prof.get("url")
    if not url:
        print("ERROR   no URL. Pass --url or set url in pages/%s/profile.json." % page)
        return 2
    today = arg("--date") or datetime.date.today().isoformat()
    names_map = {}
    mp = prof.get("baseline_map")
    if mp and os.path.isfile(os.path.join(common.PROJECT, mp)):
        names_map = (common.load_json(os.path.join(common.PROJECT, mp)).get("capture_names") or {})
    return run_capture(common.PROJECT, page, url, today, names_map)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

# Sarvam design tokens (from the live site's style sheets)

13 Nov 2026 · VENDOR. Read from the 3 style sheets linked by https://www.sarvam.ai/token-factory. Values are exact as written in the CSS. Not yet checked on a rendered page in a browser.

## Text and surface colours

| Token | Value | Use (our reading) |
|---|---|---|
| --color-tx | #1f1f1f | Main text |
| --color-tx-secondary | #3d3d3d | Second-level text |
| --color-tx-tertiary | #666 | Quiet text |
| --color-tx-inverse | #faf8f5 | Text on dark surfaces |
| --color-tx-brand | #29211d | Brand text |
| --color-tx-accent | #c4733d | Accent text |
| --color-sf | #fcfcfc | Page surface |
| --color-sf-secondary | #f5f5f5 | Panel surface |
| --color-sf-tertiary | #f0f0f0 | Panel surface, code header |
| --color-sf-quaternary | #e6e6e6 | Panel surface |
| --color-st | #e6e6e6 | Strokes and borders |
| --color-st-secondary | #f0f0f0 | Light strokes |

## Brand colours

| Token | Value |
|---|---|
| --color-br-orange | #d5650f |
| --color-br-blue | #393cc1 |
| --color-br-green | #4cd964 |
| --color-br-purple | #9b5de5 |
| --color-br-pink | #ff69b4 |
| --color-br-yellow | gold |
| --color-sr-black | #141414 |
| --color-sr-slate | #2a2c33 |
| --color-sr-white | #fff |
| Grey scale | --color-sr-grey-50 #f9f9f9, 100 #f5f5f5, 200 #f0f0f0, 300 #e6e6e6, 400 #ccc, 500 #b3b3b3, 600 #999, 700 #666, 800 #525252, 900 #3d3d3d, 950 #292929 |

## Gradients (top to bottom)

| Token | Value |
|---|---|
| --gradient-orange | #d5650f to #eaaf1c |
| --gradient-orange-medium | #e29357 to #f0c760 |
| --gradient-orange-light | #f2d1b7 to #f9e7bb |
| --gradient-blue | #bed2ff to --color-br-blue |
| --gradient-blue-medium | #dde7ff to #a6a7e3 |
| --gradient-blue-light | #f4f7ff to #bed2ff |
| --gradient-green / pink | defined with medium and light steps (see CSS) |

This matches the brand page idea of a blue-to-orange spectrum (paraphrase, UNCHECKED).

## Type

| Token | Value |
|---|---|
| --font-matter | "Matter", sans-serif (body and card headings) |
| --font-season-mix | "Season Mix", sans-serif (section headings) |
| --font-matter-mono | "Matter Mono", monospace |
| --font-matter-semi-mono | "Matter Semi Mono", monospace |
| --text-heading-card | 20px |

From the page code (class names): section headings use Season Mix, medium weight, 28 px on phones and 36 px at the medium breakpoint, line height 1.2, letter spacing -0.02em.

## Shape, depth and motion

| Token | Value |
|---|---|
| --radius-card | var(--radius-2xl) (value not extracted) |
| --radius-card-lg | var(--radius-4xl) = 32px |
| --shadow-card | 0px 0px 40px 0px #0000000f |
| --shadow-card-hover | 0px 8px 40px -4px #0000001f |
| --shadow-inset-border | inset 0 -1px 0px #0000000d |
| Durations | instant .1s, fast .15s, normal .2s, moderate .3s, slow .5s, entrance .7s |

## Code block theme

Background #fafafa, header --color-sf-tertiary, border --color-st, text #1f1f1f, keywords #33c, functions #212191, constants #a5460f, comments #666, line highlight #eef0fd with a #6366f1 bar.

## How we use this

- Every draft layout takes its colours, fonts and radii from this file. A rule check flags any colour or font that is not in it.
- Brand colours are for accents and gradients. Body text stays on the tx tokens.
- Open question: which tokens the Token Factory page actually uses at the hero. Check on a rendered page.

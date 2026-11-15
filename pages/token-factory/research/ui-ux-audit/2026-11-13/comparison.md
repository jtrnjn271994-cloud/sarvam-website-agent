---
title: "UI/UX audit comparison: Token Factory page and rivals"
type: ui-ux-audit
tier: 2
owner: claude
updated: 2026-11-13
source: "rendered with Chromium via Playwright; script agent/crawl_page_layout.py"
data_as_of: 2026-11-13
status: current
export: no (screenshots and third-party page content)
review_by: 2026-12-13
---

Audit version: 2026-11-13

Layout facts are VENDOR. Gap readings are PROPOSED.

# Comparison of nine pages

Each page has its own note in this folder. Counts and positions come from the Chromium render at 1440 px unless the row says another width.

## 1. One row per page

| Page | Hero headline | Sections | Main CTA and position | Proof types | Code sample | Pricing link or table | Comparison table | Interactive element | Mobile hero CTA visible without scroll |
|---|---|---|---|---|---|---|---|---|---|
| Sarvam Token Factory | Frontier open models. Served with speed, scale and privacy. | 9 | Explore models at 4.7% (y 449) | numbers; certifications (ISO 27001:2022, SOC 2 Type II); SLA heading; no customer names seen | yes (1) | link: API Pricing; Compare pricing | no | tabs, drop-down, FAQ | yes (y 514) |
| Nebius Token Factory | Enterprise inference for open-source AI | 1 block (order not captured) | Start building now at 5.7% (y 436) | number blocks and logo strip flagged; text not captured | yes (1) | link: AI Cloud pricing; How does your pricing compare to other providers?; Pricing | no | carousel, contact form, FAQ questions | yes (y 368) |
| E2E Networks Blaze | One API. Tokens on demand. No capacity planning. | 9 | Request access at 6.0% (y 517) | number blocks flagged; no customer section found | yes (3) | link: GPU Pricing; Pricing; Pricing (USD) | yes | code tabs, FAQ, form | yes (y 550) |
| Fireworks AI Inference | Exceptional inference. Your frontier. | 10 | Start building at 9.5% (y 625) | logo strips, number blocks flagged; text not captured | no | link: Pricing; See pricing → | no | carousels, FAQ | yes (y 408) |
| Together AI Dedicated | Dedicated inference, tuned for production | 10 | GET STARTED at 5.0% (y 496) | customer section, logo strips, number blocks flagged | no | link: GPU cluster pricing; Pricing; Pricing overview | no | carousel, FAQ | yes (y 374) |
| Together AI Serverless | The fastest way to run open‑source models on demand | 8 | GET STARTED at 5.9% (y 496) | customer section, logo strips, number blocks flagged | yes (4) | link: Pricing; Pricing overview | no | carousel, form | yes (y 416) |
| Yotta Shakti Cloud | Experience the Power of Shakti Cloud | 9 | Start your journey now at 22.7% (y 3618) (768 px) | testimonial section ('Voices of Transformation'), number blocks flagged | no | link: Pricing | no | video, carousels | no |
| Yotta Shakti Studio | none in page code | 8 | Get started now at 18.3% (y 1168) (768 px) | none flagged | no | link: Pricing | no | video, carousels | not captured |
| Krutrim Cloud | Deploy AI with One-Click GPUs | 7 | Get GPU instance at 7.9% (y 467) | number block flagged; no customer section found | no | link: Pricing | no | FAQ | yes (y 486) |

Notes on the table:

- Yotta Shakti Cloud and Studio were blocked at 1440 px (and Studio at 390 px), so those rows use 768 px.
- Yotta Shakti Studio has no h1 in the page code. Its heading text is in section 2.
- Proof types come from section headings and flags. Only the Sarvam page text was read in full. Scout text reads are in [rival-claims-13Nov2026.csv](../../rival-claims-13Nov2026.csv).
- 'Mobile hero CTA' checks the CTA text from column 4 at 390 px wide, 844 px first-screen height.

## 2. Section-order matrix

Cell = position number in the section list of that page. '-' = no section heading of that type. 'link' = a link only, no section. 'n/c' = not captured.

| Section type | Sarvam | Nebius | E2E | Fireworks | Together ded. | Together svl. | Yotta Cloud | Yotta Studio | Krutrim |
|---|---|---|---|---|---|---|---|---|---|
| Hero | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Numbers or benchmarks | 3 | n/c | 5 | 3 | 6 | 2, 5 | 4 | - | 3 |
| Models | 5 | n/c | 5 | 4, 5 | 3 | 3 | - | - | - |
| Pricing | 5 (link) | link | link | 8 (link) | link | link | link | link | link |
| Use cases or workloads | 4 | n/c | - | - | - | - | - | 5 | - |
| Code or API sample | 6 | n/c | 6 | - | - | 4 | - | - | - |
| Deployment options | - | n/c | - | 6 | 7 | 6 | - | - | - |
| Security or compliance | 7 | n/c | - | - | - | - | - | - | - |
| Customers or testimonials | - | n/c | - | 2, 8 | 9 | 8 | 8 | - | - |
| FAQ | 8 | n/c | 8 | 10 | 10 | - | - | 7 (no heading) | 6 |
| Closing CTA | 9 | n/c | 9 | - | 8 (no heading) | 7 (no heading) | 9 | 8 | 7 |

## 3. Gaps between the Sarvam page and the rivals

1. The Sarvam page shows no customer names or customer logos in the sections viewed. Fireworks, Together AI and Yotta Shakti Cloud have a customer or testimonial section. Sources: [sarvam-token-factory](sarvam-token-factory.md), [fireworks-inference](fireworks-inference.md), [together-dedicated](together-dedicated.md), [yotta-shakti-cloud](yotta-shakti-cloud.md). PROPOSED.
2. The Sarvam page has no section that compares deployment options. Fireworks and both Together AI pages have a 'Deployment options' section. Sources: [sarvam-token-factory](sarvam-token-factory.md), [fireworks-inference](fireworks-inference.md), [together-dedicated](together-dedicated.md), [together-serverless](together-serverless.md). PROPOSED.
3. The Sarvam top bar has no top-level Pricing link (its menus were not opened). Together AI, Yotta Shakti and Krutrim show 'Pricing' in the top bar, and Nebius shows 'Pricing' among its top-bar buttons. Sarvam links pricing at 50.7% of the page ('Compare pricing') and in the footer. Sources: [sarvam-token-factory](sarvam-token-factory.md), [together-dedicated](together-dedicated.md), [krutrim-ai-cloud](krutrim-ai-cloud.md), [nebius-token-factory](nebius-token-factory.md). PROPOSED.
4. The Sarvam page has no comparison table. E2E Blaze has two tables, one on what a team stops operating and one on models. Sources: [sarvam-token-factory](sarvam-token-factory.md), [e2e-blaze](e2e-blaze.md). PROPOSED.
5. The Sarvam hero styles 'Explore models' as the primary button and 'Get Started' as the second. E2E Blaze and Krutrim style 'Request access' and 'Get GPU instance' as the primary button. Nebius and Fireworks put 'Start building now' and 'Start building' first in the row. Sources: [sarvam-token-factory](sarvam-token-factory.md), [nebius-token-factory](nebius-token-factory.md), [e2e-blaze](e2e-blaze.md), [fireworks-inference](fireworks-inference.md), [krutrim-ai-cloud](krutrim-ai-cloud.md). PROPOSED.
6. Two Sarvam sections carry content the crawl found on few rivals: a speed chart against Fireworks and a security section with two certification badges. Rival notes show number blocks, but their text was not captured, so a like-for-like read needs a second pass. Sources: [sarvam-token-factory](sarvam-token-factory.md), [fireworks-inference](fireworks-inference.md), [nebius-token-factory](nebius-token-factory.md). PROPOSED.

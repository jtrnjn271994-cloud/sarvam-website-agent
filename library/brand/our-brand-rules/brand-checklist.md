# Sarvam brand checklist

Draft · 13 Nov 2026 · every draft and layout must pass this list before a person reviews it.

## Sources

| Source | What it gives | Status |
|---|---|---|
| https://www.sarvam.ai/brand-guidelines ("Sarvam Design Guidelines") | Logo, name and language rules for third-party material | Read in full on 13 Nov 2026 (HTTP 200). VENDOR. |
| https://www.sarvam.ai/brand | Brand story, visual philosophy | Loaded 13 Nov 2026. A scout paraphrased it. **Re-read before quoting.** |
| Saved page copy of sarvam.ai/token-factory (12 Nov 2026) | Fonts, heading sizes, section order | Read from page code by a scout. Class names only. **Check in a browser.** |

## A. Rules stated by Sarvam (quoted from /brand-guidelines)

**Names and language**
- "Refer to products by their exact names as published."
- Do not "modify or abbreviate product names (Doc Agents, Voice Agents, etc.)".
- "Refer to us as 'Sarvam AI' on first mention, 'Sarvam' thereafter."
- Describe Sarvam AI as "an Indic language AI company".
- Do not "claim ownership of models or technology developed by Sarvam AI".
- "We do not permit model names in application titles as this may confuse end users."
- Do not use the Sarvam AI name "to imply endorsement of your product".
- Press mission line: to make artificial intelligence accessible and useful for every Indian (the page text was cut here in our extract).
- Vision line on the brand page: "AI for all from India".

**Logo (third-party use; our page keeps these rules)**
- Use only the official files. Never recreate or change the logo.
- Wordmark: black on light backgrounds, white on dark. No accent colours, gradients, shadows or borders.
- Logomark: only where the brand is already established, such as product UI.
- Do not use the wordmark and the logomark together in one lockup.
- Keep clear space. Do not place a mark on a low-contrast or busy background.

## B. Visual style seen on the live Token Factory page (UNCHECKED until a browser run)

- Fonts: Matter (body), Season Mix (section headings), Matter Mono and Matter Semi Mono.
- Section headings: Season Mix, medium weight, 28 px on phones and 36 px from the medium breakpoint, line height 1.2, letter spacing -0.02em.
- Card headings: Matter, 20 px, medium.
- One card style uses a 14 px corner radius.
- Section order: hero, platform, performance, use cases, models, deployments, security, FAQ and closing call to action.
- Brand story page (paraphrase, UNCHECKED): a blue-to-orange spectrum, smooth shifts in light and tone, grounded and modern, no nostalgia or spectacle.
- **Colours and tokens:** found in the site's style sheets. See `brand-tokens-13Nov2026.md` (text, surface, brand colours, gradients, fonts, shadows, radii).

## C. Checks for every draft and layout

| # | Check | How |
|---|---|---|
| 1 | Product names appear exactly as published (for example "Token Factory", "Voice Agents") | Rule |
| 2 | First mention "Sarvam AI", later "Sarvam" | Rule |
| 3 | No claim of owning other makers' models | Rule + Jev |
| 4 | No model name in a page or application title | Rule |
| 5 | No wordmark in colour, no wordmark and logomark together | Review |
| 6 | Fonts come from the Matter and Season Mix families | Browser test |
| 7 | Headings, spacing and corner radius stay close to the live page | Browser test |
| 8 | Colours come from `brand-tokens-13Nov2026.md`, not from guesses | Rule (scan for hex values not in the token file) |
| 9 | Text follows the plain-writing rule | Rule |

## D. What this means for the naming question

Sarvam's own guideline says to use product names exactly as published and not to modify them. So a Token Factory rename is not ours to make. Inside this assignment we test the plain words around the name. We offer a naming view as a finding, labelled PROPOSED.

## E. Open items

1. Check the tokens on a rendered page in a browser. Chrome is not installed for Playwright. Ask the user before installing it.
2. Re-read the brand story page and quote its exact words.
3. Ask the user if the brand story page's "blue-to-orange spectrum" should guide our layout.

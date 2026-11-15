# Brand rules

Draft, 13 Nov 2026. These rules apply to every Sarvam page the agent drafts or lays out. They come from [the brand checklist](../library/brand/our-brand-rules/brand-checklist.md). The colour list is in [the token file](../library/brand/our-brand-rules/brand-tokens-13Nov2026.md).

Each check is a code check or a human review. A code check runs without a model. A human review needs a person.

## Checks

| # | Check | Type |
|---|---|---|
| 1 | Product names appear exactly as published. Example: "Token Factory", "Voice Agents". Do not change or shorten them. | code check |
| 2 | First mention is "Sarvam AI". Later mentions are "Sarvam". | code check |
| 3 | The page does not claim ownership of models made by other makers. | human review |
| 4 | No model name appears in a page title or application title. | code check |
| 5 | The wordmark is not recreated, and it is not coloured. The wordmark and logomark never share one lockup. | human review |
| 6 | Every colour comes from the token file. A hex scan finds any value not listed there. | code check |
| 7 | Fonts come from the Matter and Season Mix families. | code check |
| 8 | Text follows the plain-writing skill (short sentences, active voice). | human review |
| 9 | The word "compute" appears only when a checked source supports it. | code check |

## What Sarvam says

These lines come from https://www.sarvam.ai/brand-guidelines. We quote them exactly.

- "Refer to products by their exact names as published."
- Do not "modify or abbreviate product names (Doc Agents, Voice Agents, etc.)".
- "Refer to us as 'Sarvam AI' on first mention, 'Sarvam' thereafter."
- Do not "claim ownership of models or technology developed by Sarvam AI".
- "We do not permit model names in application titles as this may confuse end users."
- Use the Sarvam AI name only without implying endorsement of another product.

## Notes

- Check 1 needs a list of published product names. A person keeps that list. Code compares against it.
- Check 3 is a human review because code cannot judge intent. A Jev yes/no check may help a person.
- Check 6 reads hex values. A colour name such as "gold" needs a manual match to the token file.
- Logo rules: use only official files. Black wordmark on light, white on dark. See the checklist for the full list.
- The demo page also follows [demo page rules](demo-page-rules.md).

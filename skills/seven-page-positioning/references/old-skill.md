---
name: seven-page-positioning
description: Build the seven-page positioning for one page from evidence notes and buyer profiles. Makes three buyer bets and picks two with a score sheet.
origin: written for this project, 13 Nov 2026
author: Claude, for the user
license: personal, project use
changed_by_us: yes
copied_on: 2026-11-13
---

# Seven-page positioning

## Purpose
Write the seven-page positioning for one page. Produce 3 buyer bets. Pick 2 with a score sheet a person can read.

## Inputs
- Evidence notes: `pages/<page>/evidence/`.
- Buyer profiles: `pages/<page>/buyer-and-wedge/buyer.json`.
- Rival data: `pages/<page>/research/`.
- Wording style only: the two Sarvam seven-page documents in [library/positioning](../../../library/positioning/README.md). Copy their style, not their claims.

## Steps
1. List the evidence ids you may cite. Skip AUDIT and UNCHECKED items.
2. Write 3 buyer bets. Each states: the buyer problem, the alternative, the reason to choose Sarvam, the first workload.
3. Build the score sheet (see below). Take every input from files. Do not invent an input.
4. Pick the 2 highest bets. A person may overrule the pick.
5. Write the seven pages for the chosen bets, using the headings below.
6. Run the claim check: [claim-evidence-check](../../claim-evidence-check/SKILL.md).

## Headings (use exactly)
1. Where it fits
2. From TAM to a first purchase
3. The alternative determines the position
4. How the stack changes the work
5. The entry hypothesis
6. Distinct routes into enterprise work
7. Prove the first workflow, then earn expansion

## Score sheet
| Bet | Evidence coverage | Rival overlap | Buyer-profile fit | Total |
|---|---|---|---|---|
| A | 4 of 6 claims cited | 2 rivals say the same | 3 of 4 profile needs met | 9 |

- Evidence coverage: count of claims with a CHECKED or VENDOR id.
- Rival overlap: count of rivals with the same promise. Fewer is better.
- Buyer-profile fit: count of profile needs the bet meets.
- A person can recount each cell from the files.

## Output
File `pages/<page>/runs/<run-id>/positioning.md` with the 7 headings, plus `bets.md` with the 3 bets and the score sheet.
Example line: "Token Factory serves open-weight models in India through one API (VENDOR, EV-012)."

## Labels
Use CHECKED, CALC, VENDOR, SEMRUSH, PROPOSED, UNCHECKED from [evidence labels](../../../rules/evidence-labels.md). Mark every bet PROPOSED.

## Guards
- Every number cites an evidence id.
- An unknown fact reads "not in our research".
- AUDIT items are never evidence.
- Follow the [brand rules](../../../rules/brand-rules.md) and the plain-writing skill.

## It must not
- Invent a score input, a number, a quote or a customer.
- Claim lower cost without a checked source.
- Copy claims from the library seven-page documents.

## Model
Use the model set for this step in `agent/models.json`. Do not name a model here.

## Manual mode
1. Open a chat tool. Paste this prompt: "Follow skills/seven-page-positioning/SKILL.md. Use only the evidence notes I paste below."
2. Paste the evidence notes and the buyer profile.
3. Save the answer as `bets.md` and `positioning.md` in the run folder.

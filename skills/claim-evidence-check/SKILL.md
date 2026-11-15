---
name: claim-evidence-check
description: Check each claim for an evidence id, a label and a matching quote. Run agent/check_claims.py (planned) or check by hand.
origin: written for this project, 13 Nov 2026
author: Claude, for the user
license: personal, project use
changed_by_us: yes
copied_on: 2026-11-13
---

# Claim evidence check

## Purpose
Make sure every claim in a draft has support. Remove or flag the rest.

## Inputs
- `claims.csv` from the copy step.
- Evidence notes and the library register.

## Steps
1. For each claim, read its evidence ids. No id means no claim. Remove it.
2. Check that each id exists in the evidence notes.
3. Check the label. AUDIT is never evidence. UNCHECKED is not allowed in page copy.
4. Check that a withdrawn or superseded source is not cited.
5. For a quote, check that the words match the source exactly.
6. For a number, check that it matches the source or a CALC with shown inputs.
7. Write the result for each claim: pass, fail or flag.

## Run it
- Code (planned, not built): `python3 -I agent/check_claims.py pages/<page>/runs/<run-id>/claims.csv`.
- By hand: follow the steps above and write the result column yourself.

## Output
`claim-check.csv`: claim_id, evidence_ids, label, result, reason.

| claim_id | evidence_ids | label | result | reason |
|---|---|---|---|---|
| C-01 | EV-012 | VENDOR | pass | quote matches |
| C-02 | none | PROPOSED | fail | no evidence id |

## Labels
CHECKED, CALC, VENDOR, SEMRUSH, AUDIT, PROPOSED, UNCHECKED. See [evidence labels](../../rules/evidence-labels.md).

## Guards
- The check reads files. It never fixes a claim itself.
- A failed claim goes back to the copy step.

## It must not
- Pass a claim because it sounds right.
- Accept AUDIT as evidence.
- Edit the evidence note.

## Model
Code does the checks. When a model helps with quote matching, Use the model set for this step in `agent/models.json`. Do not name a model here.

## Manual mode
1. Paste this prompt: "Follow skills/claim-evidence-check/SKILL.md for the claims below."
2. Paste the claims and the evidence notes.
3. Save the answer as `claim-check.csv`.

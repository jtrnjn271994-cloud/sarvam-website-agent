---
name: buyer-profile-validation
description: Turn buyer-role checklists into rule questions and narrow Jev questions. Explains how simulated visitor segments are used.
origin: written for this project, 13 Nov 2026
author: Claude, for the user
license: personal, project use
changed_by_us: yes
copied_on: 2026-11-13
---

# Buyer profile validation

## Purpose
Check a page against what each buyer role needs. Turn each need into a yes/no question.

## Inputs
- `pages/<page>/buyer-and-wedge/buyer.json` (roles, needs, objections).
- The page copy or the built page.

## Steps
1. List each role and its needs from the buyer file.
2. Write one rule question for each need. A script can answer it. Example: "Does the page show a code sample?"
3. Write one Jev question for each need that needs judgment. See [jev-decision-test](../jev-decision-test/SKILL.md).
4. Answer the rule questions from the page text.
5. Collect the Jev answers.
6. Make simulated visitor segments from the roles. Use them in the test only.

## Output
`buyer-check.md` with a table.

| Role | Need | Question | Type | Answer |
|---|---|---|---|---|
| Head of AI platform | A code sample | Does the page show a code sample? | rule | yes |
| GCC head | Data location | Is the data location clear? | Jev | no |

## Labels
Buyer needs keep the labels from [evidence labels](../../rules/evidence-labels.md). Most are PROPOSED. Segments in a test are SYNTHETIC.

## Guards
- Simulated segments are SYNTHETIC. They never back a claim about real buyers.
- A need marked PROPOSED stays PROPOSED until a person checks it.

## It must not
- Invent a buyer quote.
- Treat a simulated visitor as a real buyer.
- Ask Jev a broad question.

## Model
Use the model set for this step in `agent/models.json`. Do not name a model here.

## Manual mode
1. Paste this prompt: "Follow skills/buyer-profile-validation/SKILL.md."
2. Paste the buyer file and the page text.
3. Save the answer as `buyer-check.md`.

---
name: page-copy-draft
description: Draft whole-page copy from a chosen bet, section by section, with evidence ids beside each line.
origin: written for this project, 13 Nov 2026
author: Claude, for the user
license: personal, project use
changed_by_us: yes
copied_on: 2026-11-13
---

# Page copy draft

## Purpose
Write copy for the whole page from one chosen bet. Every line has evidence ids in a table.

## Inputs
- The chosen bet and `positioning.md` from [seven-page-positioning](../seven-page-positioning/SKILL.md).
- Evidence notes and buyer profile for the page.
- The [brand rules](../../rules/brand-rules.md).

## Steps
1. List the sections of the new page, in order.
2. For each section, write the copy lines.
3. Next to each line, write its evidence ids and label.
4. For industry tiles, show only a checked fact, or an example workload labelled PROPOSED.
5. Run the brand checks and the plain-writing check.
6. Write the claims list. Run [claim-evidence-check](../claim-evidence-check/SKILL.md).

## Output
Two files in `pages/<page>/runs/<run-id>/`: `copy.md` and `claims.csv`.

Example `copy.md` row:

| Section | Line | Evidence ids | Label |
|---|---|---|---|
| Hero | Run open-weight models in India through one API. | EV-012 | VENDOR |

Example `claims.csv` columns: claim_id, text, evidence_ids, label, status.

## Labels
CHECKED, CALC, VENDOR, SEMRUSH, PROPOSED, UNCHECKED. See [evidence labels](../../rules/evidence-labels.md).

## Guards
- No cost claim without a checked source.
- No line without an evidence id. A line with only PROPOSED stays marked as a draft idea.
- First mention "Sarvam AI", later "Sarvam". Product names exact.
- Avoid the word "compute" unless a checked source supports it.
- Short sentences, active voice.

## It must not
- Invent a number, a quote, a customer or a result.
- Put a model name in a page title.
- Use AUDIT items as evidence.

## Model
Use the model set for this step in `agent/models.json`. Do not name a model here.

## Manual mode
1. Paste this prompt: "Follow skills/page-copy-draft/SKILL.md for the bet below."
2. Paste the bet, the evidence notes and the brand rules.
3. Save the answer as `copy.md` and `claims.csv` in the run folder.

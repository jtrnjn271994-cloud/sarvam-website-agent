---
name: seven-page-positioning
description: Make one position for a page (first buyer, category, alternatives, one main claim, proof, swap test, weak points), then three bets that carry it.
origin: wrapper, written for this project, 2026-11-14. Method sources are copied exact in references/source/ (see Sources).
author: project builder
license: personal, project use (copied sources keep their own licences, see Sources)
changed_by_us: yes
copied_on: 2026-11-14
step: 3a
role: writer
schema: schemas/position.schema.json
---

# Seven-page positioning

## Purpose
This step turns the brief, the insight and the rival rows into one position, then into three bets.
Step 3b needs the position. The page work needs the bets. A person signs the position at step 9.

## When this step runs
- Step 3a. The step before is 2 (insight). The step after is 3b (message house).
- It does not stop for a person. The person sees the position after 3b.
- Today `agent/run.py` calls this skill for the bets prompt (`generate_bets`). The task prompt at the end of the call fixes the JSON keys. Follow it.

## Inputs
- `skill_core`: this file.
- `ref_examples`, `ref_failures`, `ref_checklist`: good and bad positions, the mistakes seen so far, the yes/no list.
- `run_contract`: `rules/run-contract.md`.
- `brief`, `insight`, `rivals`, `claims_index`, `do_not_claim`: the facts. Nothing else is a fact.

## Method
1. Name the first buyer. Copy the role from the brief. If the brief names two, stop and write both in `self_check.gaps`. (source: `references/source/product-marketing-context/SKILL.md`, sections "2. Target Audience" and "3. Personas")
2. Name the category the buyer uses to find the product. Use the buyer's word, not ours. (source: `references/source/product-marketing-context/SKILL.md`, section "1. Product Overview"; `references/source/revenue-centric-design/references/positioning-icp-and-gtm.md`, section "Pick a deliberately under-served niche as your ICP")
3. List the alternatives the buyer compares. Take them from buyer words and the insight, not from our rival list. Mark each as direct, secondary or indirect. (source: `references/source/product-marketing-context/SKILL.md`, sections "5. Competitive Landscape" and "8. Switching Dynamics"; project path `skills/competitors/SKILL.md`)
4. Write one main claim. One sentence. A reader can prove it true or false. Do not compete on the commodity. (source: `references/source/revenue-centric-design/references/ai-era-differentiation.md`, section "Same engine, different UX: don't compete on the commodity"; `references/source/product-marketing-context/SKILL.md`, section "6. Differentiation")
5. Attach proof lines to the claim. Each line has an evidence id and a label. Mark an unsupported line as an assumption. Never use an AUDIT note as proof. (source: `references/source/product-marketing-context/SKILL.md`, section "11. Proof Points"; `references/source/strategist/strategist.md`, "Process" step 2)
6. Run the swap test against each rival row, one row at a time. Ask: can this rival print the claim word for word? Give the answer and a reason for each row. A "yes" means rewrite the claim. (source: `skills/copywriting-marketingskills/SKILL.md`, section "Drafting Protocol", three-question gate; lesson L09 in `docs/lessons.md`)
7. Name the three weakest points of the position. Say where a rival is better. (source: `references/source/competitor-alternatives/SKILL.md`, section "1. Honesty Builds Trust"; `references/source/revenue-centric-design/references/ai-era-differentiation.md`, section "A validated idea is a short-term game")
8. Write three bets. Each bet carries the same position from a different angle and a different page structure. Use the BASELINE section names. (project addition: the run builds pages from bets, so the position must become a section plan)
9. Check the limits: the do-not-claim list, "what the position does not claim", no lower-cost claim. (source: `rules/run-contract.md`, hard rule 8)
   If no claim backs a scale the promise names (for example speed), drop that section and list the scale under `gaps`. Never write a number or word that implies it.
10. Fill `self_check`. Name each gap you could not fill. Do not guess. (source: `rules/run-contract.md`, hard rule 10)

## Output format
Reply with one JSON object. It has three top-level keys:
- `bets`: a list of three bets. `agent/run.py` parses this block into the page variants. The keys of each bet are listed under "The bets block" below.
- `position`: one object, the position that all three bets carry. The run checks it against `schemas/position.schema.json` and saves it as `position.json` in the run folder. A person reads it in the report and on the review page. Step 3b needs it. A position that fails the schema is not saved, and the report names the problems.
- `self_check`: the block that `rules/run-contract.md` requires. The run rejects a reply without it. The `position` object also holds its own `self_check`, because the schema requires it.

The position block. Its schema is `schemas/position.schema.json`. Filled:

```json
{
  "first_buyer": {"text": "AI platform lead at a GCC or IT services firm", "evidence_ids": ["EV-001"], "label": "PROPOSED", "reason": "Named in the brief. One buyer only. No buyer interview exists, so the label stays PROPOSED."},
  "category": {"text": "Managed model inference: an API that runs a model for an application", "evidence_ids": ["EV-008"], "label": "PROPOSED", "reason": "The context pack names this category. It is not GPU rental."},
  "alternatives": [{"text": "Keep an internal serving stack", "evidence_ids": ["EV-001"], "label": "PROPOSED", "reason": "Tech Mahindra says clients move work step by step."}],
  "main_claim": {"text": "Put a production model workload on an India-served API, then prove it meets your quality, speed and cost bar.", "evidence_ids": ["EV-007", "EV-008"], "label": "PROPOSED", "reason": "A test promise. The API facts are VENDOR."},
  "proof": [{"text": "Open models through an OpenAI-compatible API.", "evidence_ids": ["EV-008"], "label": "VENDOR", "reason": "CL-001, from the Sarvam page."}],
  "swap_test": [{"rival_id": "EV-019", "rival_could_print": false, "reason": "E2E Blaze states India, INR and an OpenAI-compatible API. It does not offer a workload test on the page we hold."}],
  "weak_points": ["No named Token Factory customer.", "No matched quality, speed and cost test.", "The step after the main button is unknown."],
  "self_check": {"promise_used": "Put a production model workload on an India-served API, then prove it meets your quality, speed and cost bar.", "alternative_beaten": "Keep an internal serving stack", "evidence_ids_used": ["EV-001", "EV-007", "EV-008", "EV-019"], "swap_test": [{"line": "main claim", "rival_could_print": false, "why": "No rival row leads with a workload test."}], "audiences_served": [{"section": "hero", "audiences": ["primary"]}], "rules_checked": ["do-not-claim", "no lower-cost claim"], "gaps": ["Rival pages need a re-read."]}
}
```

The bets block. The run parses `{"bets":[...],"position":{...},"self_check":{...}}`. Each bet keeps the keys `id`, `title`, `idea`, `headline`, `positioning_link`, `alternative_beaten`, `why_not_generic`, `positioning_fit`, `lead_cta`, `claim_ids`, `evidence_ids`, `section_plan`, `baseline_change`, as the task prompt lists them.
Set `headline` from the main claim. Set `positioning_link` to the part of the position that the bet executes. Set `lead_cta` to the brief's `main_cta`, word for word, in all three bets.
In `swap_test`, `rival_could_print` is `true`, `false` or `null`. Use `null` when we do not hold the rival's text. Start the reason with "UNKNOWN:". The report then shows UNKNOWN, not "no".

## Good example
A main claim whose swap test says "no" for every rival row, each with its reason. Three weak points are named. Proof lines carry ids and labels.
Why it is good: a person can check every row against the files. See `references/examples.md`.

## Bad example
"Run open models on GPUs in India." E2E Blaze can print it word for word (EV-019).
Why it fails: `swap_test_each_rival` and the Jev swap test catch it. Context pack section 11 rejected this line by hand.

## Checks the code runs after
- `schema`: the reply fits `schemas/position.schema.json`.
- `evidence_ids_exist`: each evidence id is a note on file.
- `labels_valid`: each label is on the list in `rules/evidence-labels.md`.
- `swap_test_each_rival`: there is one swap row for each rival row.
- `do_not_claim`: no phrase from the ban list appears.
- `jev_swap_test`: Jev must say a rival cannot print the main claim.

## What a person decides
- Is the first buyer right, and is it one buyer?
- Does the main claim pass the swap test in the person's own reading?
- Are the three weak points honest?

## Sources

| File | Origin | Licence | Export |
|---|---|---|---|
| `references/source/product-marketing-context/SKILL.md` | `~/.claude/skills/synced/<id>/product-marketing-context/SKILL.md` | personal, no export | no |
| `references/source/competitor-alternatives/SKILL.md` | `~/.claude/skills/synced/<id>/competitor-alternatives/SKILL.md` | personal, no export | no |
| `references/source/revenue-centric-design/references/positioning-icp-and-gtm.md` | `~/.claude/plugins/synced/<id>/revenue-centric-design/skills/revenue-centric-design/references/positioning-icp-and-gtm.md` | Revenue-Centric Design LICENSE terms (permission with conditions), no export | no |
| `references/source/revenue-centric-design/references/ai-era-differentiation.md` | same folder, `ai-era-differentiation.md` | Revenue-Centric Design LICENSE terms (permission with conditions), no export | no |
| `references/source/revenue-centric-design/LICENSE` | same skill folder, `LICENSE` | Revenue-Centric Design LICENSE terms | no |
| `references/source/strategist/strategist.md` | `~/.claude/plugins/synced/<id>/marketing-team/agents/strategist.md` | personal, no export | no |
| `skills/product-marketing/SKILL.md` | `skills/product-marketing/SKILL.md` | MIT | yes |
| `skills/competitors/SKILL.md` | `skills/competitors/SKILL.md` | MIT | yes |
| `skills/customer-research/SKILL.md` | `skills/customer-research/SKILL.md` | MIT | yes |
| `skills/copywriting-marketingskills/SKILL.md` | `skills/copywriting-marketingskills/SKILL.md` | MIT | yes |

`<id>` is `77a380fa-0200-4b5e-b804-662cfa9bac49_1d67fb93-69fd-4173-b9af-37060ff23cc8`. Checksums are in `references/SOURCES.md`. The old 73-line skill is in `references/old-skill.md`.
When a source file is absent, write "source absent: <path>. Use the method steps above only."

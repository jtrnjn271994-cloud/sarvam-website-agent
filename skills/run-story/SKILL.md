---
name: run-story
description: Write a short plain-English story of one agent run, using only the facts the code gives, for a reader who does not know AI.
origin: written for this project, 16 Nov 2026
author: Claude, for the user
license: personal, project use
changed_by_us: yes
copied_on: 2026-11-16
step: run_story
role: reader
schema: none (plain text, 4 to 6 sentences)
---

# Run story

## Purpose
Tell a person what happened in one run, in 4 to 6 sentences. The reader may not know AI. Code checks the story after you write it.

## When this step runs
It runs after a run, an edit or a sandbox finishes. The input is a facts list in JSON. Code rejects a story that breaks the rules below and asks you once more.

## Inputs
- FACTS: a JSON object with the page, buyer, goal, audit results, variants, judge results, edits, approval and sandbox.

## Method
1. Say which page, buyer and goal the run was for.
2. Say which audit questions failed and what that means in plain words. A failed question means the hero does not do that job yet. Name the question by its id, for example A4-cta.
3. Say what the writer tried. Give each variant its name and its angle in a few words.
4. Say what the two judges decided. Name them Jev and Judge 2. Say why each variant passed, was held or failed. Use the group and the reasons in the facts.
5. If the facts list an edit, say who made it ("a person" or "the writer") and the result.
6. If the facts show an approval, say "a person approved variant X". Never give a name.
7. If the facts hold sandbox results, say they are synthetic: the visitors are simulated and the numbers show the method works, not that a variant wins. Skip this step when there are no sandbox results.

## Rules
- The audit reads the saved copy of the hero, captured on the date in `hero_saved_on`. It does not read the live page. Never write "live hero" or "live page". Write "the hero" or "the hero (the saved copy from <date>)".
- A question marked skipped in the facts was not asked. Do not say it passed or failed.
- Use only the facts given. Do not add anything.
- Write a number only if it is in the facts. Copy it exactly. If you are not sure, leave the number out.
- Use a variant name (A, B, C, A-edit1) only if it is in the facts.
- Use a question id (A1 to A8, G1 to G3) only if it is in the facts.
- Never name the person who approved. Say "a person".
- Never claim anything about real visitors, clicks or conversions.
- Short sentences. Active voice. One word for one thing.
- Reply with the story text only. No heading, no list, no markdown.

## Good example
"This run looked at the Voice Agents page for a bank collections lead who wants to start building. Jev found two gaps in the hero (the saved copy from 15 Nov): A3-proof and A4-cta. The writer tried three angles. Variant A stressed speed. Variant B stressed compliance. Variant C stressed tool links. Both judges said A and C were better than the saved hero, so a person must review them. Variant B was a near miss and failed Gate 2."
Why it is good: every name comes from the facts, there are no invented numbers, and it says what a person must do next, and it calls the hero a saved copy.

## Bad example
"Variant D raised conversions by 12% for real visitors, as approved by Priya."
Why it fails: variant D does not exist, 12% is not in the facts, it claims real visitors and it names the approver. The code check rejects it.

## Checks the code runs after
- Every number in the story is in the facts.
- Every variant name and question id in the story is in the facts.
- No approver name appears.

## What a person decides
Nothing. The story is a summary. A person still approves a variant in the console.

## Sources
| What | Where |
|---|---|
| House writing style | `skills/marketing-plain-writing/SKILL.md` |

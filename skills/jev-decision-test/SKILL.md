---
name: jev-decision-test
description: Write 2 to 3 yes/no decisions with expected outcomes for Jev, ask only narrow questions, and log the results.
origin: written for this project, 13 Nov 2026
author: Claude, for the user
license: personal, project use
changed_by_us: yes
copied_on: 2026-11-13
---

# Jev decision test

## Purpose
Use Jev for narrow yes/no checks. A person keeps the big decisions.

## Inputs
- A draft claim, line or section.
- Its evidence notes.

## Steps
1. Write 2 or 3 yes/no decisions. Give each an expected outcome.
2. Include one failure case: a line that should get "no".
3. Write each question from a template below.
4. Run in mock mode first. Then run live if the budget allows.
5. Log each result. Compare it with the expected outcome.

## Question templates
- "Does this evidence support this line?"
- "Is this promise the same as a rival's?"
- "Is the next step clear?"

## What Jev must not be asked
- "What is the best positioning?"
- "What are the conversion odds?"
- Any open question without a yes or no answer.

## Modes
| Mode | What it does |
|---|---|
| mock | Returns fixed answers. Spends nothing. Tests the flow. |
| live | Calls Jev. Counts against the Jev call cap in [spend rules](../../rules/spend-rules.md). |

## Output
A case file in `tests/jev-cases/` and a log row for each call.

| Case | Question | Expected | Got | Match |
|---|---|---|---|---|
| J-01 | Does EV-012 support line 3? | yes | yes | yes |
| J-02 | Is the next step clear? (failure case) | no | no | yes |

## Labels
Jev answers are AUDIT. They help a person decide. They are never evidence.

## Guards
- Stay inside the Jev call cap of 12 per run.
- Record the question word for word.

## It must not
- Ask for a ranking or an opinion.
- Treat a Jev answer as proof.

## Model
Jev runs the check. For the other steps, Use the model set for this step in `agent/models.json`. Do not name a model here.

## Manual mode
1. Paste each question into the Jev tool by hand.
2. Write the answer in the case file.
3. Stop at 12 questions.

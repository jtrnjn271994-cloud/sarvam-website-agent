---
name: run-architecture
description: Generate, update or check the architecture diagrams of the Sarvam website agent, above all the per-run flow diagram drawn by agent/run_flow.py. Use when a run, an edit or a sandbox finishes, when the agent's flow changes (a step, a gate or a judge), when the per-run diagram looks wrong or is missing, or when someone asks for the architecture of the whole agent or of one run.
---

# Run architecture: one template, every run

Written for: whoever changes the agent (a person or Claude Code). The overall architecture and the diagram of each run must say the same thing in the same words.

## The two documents

1. **The overall architecture.** `docs/architecture.html` and `docs/architecture.md`, built by `python3 -I docs/build_architecture.py`. It is the one to share. On the website: `/architecture.html`. It shows the whole run step by step, the three layers, who asks which questions at each check, the sandbox and findings, where things live, the fleet, the skills each step uses and how each run's diagram is made. No tables.
2. **The diagram of one run.** `RUN-FLOW.md` and `RUN-FLOW.html` in each run folder, built by `agent/run_flow.py`. The console's "Sandbox and findings" tab draws the same text from `/api/runflow`.

## What the per-run diagram is

It is the overall template filled in with one run's own facts. Plain code draws it. **A model never draws it and never adds a step.** If a step is not in the template, it is not in the diagram. Never invent a step, a node or a fact.

`probe3.py`, `edit_variant.py` and `sandbox_hero.py` call `run_flow.write()` when they finish. So every run, every edit and every sandbox brings the run's own diagram up to date. Nobody types a diagram by hand.

## When to use this skill

- You change a step, a gate, a judge or a question set, and the diagram must follow.
- A run's diagram is missing, wrong or shows a "Syntax error".
- A new field is added to `probe3.json` and a node should show it.
- Someone asks how one run went through the agent.

## The template, in order

Keep these numbers, names and this order in both documents:

Start (person) → 2 Capture the hero (15 Nov: the saved copy every later step reads) → 3 Page set up and approved (page setup branch: Gemini drafts, rules check, the owner approves) → 4 AUDIT the saved hero (Jev only, A1 to A8, shows the question version) → Gap found? (no: stop, nothing is written) → 5 GAP DOSSIER → 6 TEST PLAN → 7 WRITER (Opus) → Gate 1: RULES (no model), at most 2 rounds, a failed variant goes back to the writer → Gate 2, two boxes side by side: Jev, and Judge 2 (OpenAI gpt-6-luna-decisions), both feeding one node "both say better?" → Shortlist → 8 Apply the words, check the button link (the picture step) → 9 HUMAN approval (edit loop: Edit and re-check, back to Gate 1) → 10 SANDBOX PLAN → Simulate and check → 11 FINDINGS (SYNTHETIC) → 12 Submission and docs.

Gate 1 and Gate 2 carry no number.

## Which field fills which node

All values come from `gather()` in `agent/run_flow.py`. It reads the run folder only.

- **Start:** `probe3.json` fields `persona.buyer`, `goal.label`, `screenshots` (the text "not taken (website run)" means a website run), and the page name from `pages/registry.json`.
- **Capture:** the newest `pages/<page>/capture/*-live/hero.json`: `captured_at` and `h1`.
- **Page set up:** `page_questions.approved` (true means A7 and A8 are asked).
- **Audit:** `audit.gaps`, `audit.verdict` (the keys with "pass" are the already-answered ones) and `questions_version`. Version 2 shows "questions v2". A missing field shows "questions v1".
- **Gap found?:** empty `audit.gaps` ends the diagram at "Stop: no gap".
- **Dossier:** `dossier.text` (word count).
- **Test plan:** `goal.kind`.
- **Writer:** `variants` without `edited_from` (name and headline).
- **Gate 1:** `gate1_rounds` (the number of rounds and, for the last round, each variant's problem count).
- **Jev and Judge 2 boxes:** drawn solid when `gate2` exists, otherwise grey and dashed.
- **Both say better?:** `shortlist.classify(probe)` over the variants that passed Gate 1: each variant's `gains` from the judge deltas. Variants that failed Gate 1 are not listed.
- **Shortlist:** the group of each variant (passed, held, failed Gate 2, failed Gate 1) and the near-miss flag.
- **Apply the words:** the count of `pair-*.png` files in the run folder, or the website-run note.
- **Human approval:** the current approval record (`shortlist.current_approval`): the variant and the override flag.
- **Edit and re-check:** `edits` (name, source variant, kind, `gate1_problems`).
- **Sandbox plan, Simulate and check, Findings:** `sandbox/sandbox-results.json`: `plan`, `simulated`, `browser`.
- **Submission and docs:** always drawn.

## Drawing rules

- Steps the run reached are solid. Steps not reached are grey and dashed (`:::todo`). This applies to all three Gate 2 nodes.
- Gates and the approval have a thick border (`:::gate`). Stops are red (`:::stop`).
- Colour by role: Jev is purple (fill #EADFFF, stroke #7A4DD8, class `jev`). Judge 2 is green (fill #D9F3EC, stroke #1E9E80, class `j2`).
- Each node holds the run's facts. Text is cleaned before it goes in a node (no quotes, brackets, pipes, hashes or semicolons) and cut at 90 characters.
- Mermaid version 10.9.1, loaded from the CDN in `RUN-FLOW.html`.
- No tables in the diagram.

## Every scenario the diagram must handle

`python3 -I agent/run_flow.py --selftest` checks each one, approved and not approved. It also checks that the split Gate 2 (Jev, Judge 2, both say better?) and the question version appear.

| Scenario | What the diagram shows |
|---|---|
| No gap | Stops at "Stop: no gap"; nothing after it |
| Every variant failed Gate 1 | A red "Every variant failed Gate 1" node that points to the shortlist and step 9: edit one |
| Near misses only | Shortlist says "failed Gate 2 (near miss)"; approval waits, or shows "against Gate 2, reason given" |
| Held variant | Shortlist says "held" |
| Passed, waiting for a person | Steps 1 to 8 solid; step 9 onwards dashed |
| Edited variants | An "Edit and re-check" node with each edit (person's words or writer rewrite) and a loop back to Gate 1 |
| Approved | Step 9 shows the approved variant |
| Sandbox done | Steps 10 and 11 show the tests; findings say SYNTHETIC |
| Website run | Step 8 says "no screenshots"; the sandbox says "page check" |
| Owner's machine run | Step 8 counts the PNG pairs; the sandbox says "browser sessions" |
| Stopped early (crash, time limit) | Steps after the last saved one are dashed |
| Old run, typed sandbox | "typed scenarios (older run)" |
| Question version 2 | The audit node says "questions v2" |
| Question version 1 (old run, no field) | The audit node says "questions v1" |
| Empty or broken run folder | Still draws; missing parts are dashed |

## Fail-safe rules

- The diagram reads only the run's own files. It calls no model and costs nothing.
- `write()` never raises. If drawing fails, it prints one line and the run goes on.
- A missing or broken field draws as "not reached" (grey and dashed). Nothing fails.
- Old runs still draw. Fields they lack get the old meaning (no `questions_version` means v1; no `judge1` or `judge2` split means the boxes are dashed).
- Never describe a step as built until its code exists and has run once.

## How to change the template

1. Edit `mermaid()` (and `gather()` if a new field is needed) in `agent/run_flow.py`.
2. Add or change a case in `scenarios()` and `selftest()`. Run `python3 -I agent/run_flow.py --selftest`. Every line must say PASS.
3. Regenerate every saved run: `python3 -I agent/run_flow.py --all`.
4. Render check. Open every `pages/*/runs/*/RUN-FLOW.html` in a browser with Playwright (use plain `python3`, because `-I` hides Playwright). Each page must hold an SVG and no "Syntax error" or "Parse error" text. Look at one finished run as a picture.
5. If the overall run diagram must match, edit `FLOW` in `docs/build_architecture.py` and run `python3 -I docs/build_architecture.py`. Update the template list above.
6. Tell the owner to redeploy. Do not deploy yourself unless the task says so.

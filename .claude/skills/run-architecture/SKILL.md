---
name: run-architecture
description: Generate, update or check the architecture diagrams of the Sarvam website agent. Use when a run, an edit or a sandbox finishes, when the agent's flow changes, when the per-run flow diagram looks wrong or is missing, or when someone asks for the architecture of the whole agent or of one run.
---

# Run architecture: one template, every run

Written for: whoever changes the agent (a person or Claude Code). The overall architecture and the diagram of each run must say the same thing in the same words.

## The two documents

1. **The overall architecture.** `docs/architecture.html` and `docs/architecture.md`, built by `python3 -I docs/build_architecture.py`. It is the one to share. On the website: `/architecture.html`. Sections: 1 the run (every step), 2 the three layers, 3 the questions Jev asks, 4 deployment, 5 models, 6 limits. No tables.
2. **The diagram of one run.** `RUN-FLOW.md` and `RUN-FLOW.html` in each run folder, built by `agent/run_flow.py`. The console's "Sandbox and findings" tab draws the same text from `/api/runflow`.

`probe3.py`, `edit_variant.py` and `sandbox_hero.py` call `run_flow.write()` when they finish. So every run, every edit and every sandbox brings the run's own diagram up to date. Nobody types a diagram by hand.

## The template (section 1 of the architecture)

Keep these numbers, names and this order in both documents:

1 Start (person) → 2 Capture the hero → 3 Page set up and approved? (page setup branch: Gemini drafts, rules check, owner approves) → 4 AUDIT the live hero (Jev, A1 to A8) → Gap found? → 5 GAP DOSSIER → 6 TEST PLAN → 7 WRITER (Opus) → Gate 1: RULES (max 2 rounds) → Gate 2: JEV + JUDGE 2 → Shortlist → 8 Apply the words, check the button link → 9 HUMAN approval (edit loop: Edit and re-check, back to Gate 1) → 10 SANDBOX PLAN → Simulate and check → 11 FINDINGS (SYNTHETIC) → 12 Submission and docs.

Drawing rules:
- Steps the run reached are solid. Steps not reached are grey and dashed (`:::todo`).
- Gates and the approval have a thick border (`:::gate`). Stops are red (`:::stop`).
- Each node holds the run's facts: buyer, goal, gaps, variant headlines, each variant's group, judge gains, approval, sandbox results.
- Text is cleaned before it goes in a node (no quotes, brackets, pipes, hashes or semicolons) and cut at 90 characters.

## Every scenario the diagram must handle

`python3 -I agent/run_flow.py --selftest` checks each one, approved and not approved:

| Scenario | What the diagram shows |
|---|---|
| No gap | Stops at "Stop: no gap"; nothing after it |
| Every variant failed Gate 1 | A red "Every variant failed Gate 1" node that points to the shortlist and step 9: edit one |
| Near misses only | Shortlist says "failed Gate 2 (near miss)"; approval waits, or shows "against Gate 2, reason given" |
| Passed, waiting for a person | Steps 1 to 8 solid; step 9 onwards dashed |
| Edited variants | An "Edit and re-check" node with each edit (person's words or writer rewrite) and a loop back to Gate 1 |
| Website run | Step 8 says "no screenshots"; the sandbox says "page check" |
| Owner's machine run | Step 8 counts the PNG pairs; the sandbox says "browser sessions" |
| Stopped early (crash, time limit) | Steps after the last saved one are dashed |
| Old run, typed sandbox | "typed scenarios (older run)" |
| Empty or broken run folder | Still draws; missing parts are dashed. `write()` never raises, so a diagram never stops a run |

## Fail-safe rules

- The diagram reads only the run's own files. It calls no model and costs nothing.
- If a file is missing or broken, that step is dashed. Nothing fails.
- After a change to the flow, change three places together: `FLOW` in `docs/build_architecture.py`, `mermaid()` in `agent/run_flow.py`, and the template above. Then:
  ```
  python3 -I docs/build_architecture.py
  python3 -I agent/run_flow.py --selftest
  python3 -I agent/run_flow.py --all
  ```
- Before you deploy, render both documents in a browser (Mermaid 10.9.1) at 1100 px and 390 px. You should see no "Syntax error", no sideways scroll on the page, and no tables in the architecture.
- Never describe a step as built until its code exists and has run once.

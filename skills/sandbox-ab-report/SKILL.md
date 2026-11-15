---
name: sandbox-ab-report
description: Plan and report a synthetic A/B test with fixed-seed assignment, a visitor count set before the run, one primary action and SYNTHETIC labels.
origin: written for this project, 13 Nov 2026
author: Claude, for the user
license: personal, project use
changed_by_us: yes
copied_on: 2026-11-13
---

# Sandbox A/B report

## Purpose
Test the approved change against the baseline with simulated visitors. Report the result with its limits.

## Inputs
- The approved change and the baseline.
- The test scope. See [test scope rules](../../rules/test-scope-rules.md).

## Steps
1. Write the plan first: scope, one primary action, seed, visitors per arm.
2. Fix the number of visitors per arm before the run. Do not change it.
3. Assign each simulated visitor by a stable hash of its id and the seed.
4. Run the test. Do not peek. Do not stop early.
5. Count the primary action in each arm.
6. Class the result: clear or inconclusive.
7. Write the report.

## Report layout
1. Plan: scope, action, seed, visitors per arm.
2. Result table.
3. Result class.
4. Limits.

Example result table:

| Arm | Visitors | Clicks on primary action | Rate |
|---|---|---|---|
| Baseline | 500 | 40 | 8% (SYNTHETIC) |
| New page | 500 | 55 | 11% (SYNTHETIC) |

The assignment asks for two examples: one clear result and one inconclusive result. Show both in the sample report. Say they come from a simulation.

## Limits to state
- The visitors are simulated. The result does not predict real buyers.
- A whole-page test cannot show which section caused the result.
- The test measures one action only.

## Labels
Every number carries SYNTHETIC. See [evidence labels](../../rules/evidence-labels.md).

## Guards
- Seed and visitor count appear in the plan before the run.
- The demo page follows the [demo page rules](../../rules/demo-page-rules.md).

## It must not
- Say "proved" or "real visitors".
- Change the visitor count after seeing data.
- Report a result without the SYNTHETIC label.

## Model
Code runs the test. For the report text, Use the model set for this step in `agent/models.json`. Do not name a model here.

## Manual mode
1. Write the plan in a file. Save it before you run.
2. Run the test script, or count by hand with a seeded list.
3. Paste the counts into the report layout.

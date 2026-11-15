# Fresh audit: your flow against what is built (15 Nov 2026)

Written for: the project owner, who wants to know where the build stands before any new code.
Status: AUDIT. No code or flow file was changed. Nothing was run that writes a run folder.

## Short answer

The foundation is strong. The engine, the rules, the checks and the approval button work. The last half of the flow does not exist yet.

- **208 unit tests pass.** `check_all.py` shows 12 of 12. `run.py --selftest` shows 8 of 8.
- **Those tests do not cover the missing steps.** Five steps in `flow.json` still say `not_built`: 7 (position check), 11 (proof and better-than-baseline), 14 (sandbox), 15 (findings), 16 (submission note).
- **The engine can reach step 13, the approval page.** After approval it stops. No sandbox, no findings, no README.
- **The sandbox is not real yet.** `sandbox.py` is a maths simulator. It draws random numbers. It never opens a page. The assignment says "the workflow must perform real actions".
- **Jev is used as auditor and as validator.** That is the weakness you spotted. One judge cannot check itself.

## Your flow against the build

Status words: **built** = code exists and tests pass. **not wired** = code exists but no flow step calls it. **not built** = nothing exists.

| Your step | Flow step today | Status | Gap | Assignment line |
|---|---|---|---|---|
| 1. Pick page and buyer persona | 1, 2, 3 (start form) | built | Persona list lives in a page folder. Works for Token Factory. A new page needs its own folder. | Choose an audience and action |
| 2. Positioning: reuse or generate | 3b, 3c, 3d | built | Reuse and generate both have handlers. Not tested live on a second page. | Assess positioning |
| 3. Capture the page (Playwright or Firecrawl) | 5 baseline audit | built | Playwright works and the capture exists (1280 and 390 screenshots, 9 blocks). Firecrawl is not wired. | Recreate one page or section |
| 4. Jev tags every baseline block (proof? audience? CTA?) | none | **not built** | Jev audits variant copy today (`jev.py --sections`). It never tags the baseline. Gap finding is done by an LLM at step 8. | Identify a gap |
| 5. LLM builds variants with the skills | 10 | built | Works. Message mode needs one CTA in every arm. Run-06 broke this ("Explore models" vs "Compare on your workload"). | Create a variant; keep supported claims |
| 6. Jev checks each claim against the page | 7 and 11 | **not built** | Code checks exist (claim ids, quotes, banned words). The Jev part has no step. | Preserve supported claims |
| 7. Second independent judge | none | **not built** | No second judge exists. | Where Jev fits |
| 8. Threshold, then human approval page | 12, 13 | built | Approval page works. It does not show judge disagreement or flagged variants. | Require approval |
| 9. Sandbox on all approved variants | 14 | **not built** | The simulator handles two arms. Several arms need a multiple-test rule. | Test the hypothesis |
| 10. Findings with rates and uncertainty | 15 | **not built** | `report.py` exists. Nothing calls it. | Publish findings |
| 11. Rollout approval | none | **not built** | The flow ends at the submission note. | Rollout needs approval |
| 12. README, architecture note, Jev note | 16 | **not built** | The `submission/` folder is empty. | What to submit |

## Faults that matter more than the missing steps

1. **One model family judges itself.** Jev audits, classifies and validates. The `jev-router` model routes to a generative model. It may share a family with the writer. Two LLM judges that agree prove little. The fix is to keep the code checks as the hard gate. Show judge disagreement to the human as a signal.
2. **Jev calibration is unresolved.** Run-06 matched 11 of 12 cases. Case jc-03 failed. Every badge was marked "unreliable". Nobody has inspected jc-03.
3. **The approval hash is too narrow.** It covers four files. A change to the brief, baseline or plan can pass without fresh approval. Old unhashed approvals are still accepted.
4. **The call to action in run-06 differs between baseline and variants.** That breaks the message-only test.
5. **Two folders compete:** `pages/token-factory` and `pages/token-factory-gpt`. Both hold briefs and runs.
6. **The code is large.** About 15,000 lines of Python in `agent/`. Much of it guards edge cases. A reviewer will need a one-page map.

## Decisions (answered by the owner, 15 Nov 2026; logged as rows 17 to 21 in the Decisions Log)

Answers: (1) second judge = any other decision model, from a different family than the writer and Jev; (2) the approval page shows only passing variants; (3) Jev tags the baseline first; (4) the two strongest variants that beat the baseline go to the sandbox; (5) the real folder is `sarvam-positioning-agent`. Page folder: `pages/token-factory` (owner, 15 Nov 2026; row 22).

The original questions, for the record:

1. **What is the "distance API" or "additions API"?** I read it as Sarvam's typed Decisions API (Prism, `POST /v2/systemone`). Is that right? The alternative is a second LLM from a different family through OpenRouter. The question matters because the second judge must not share the writer's blind spots.
2. **Which rule wins on the approval page?** An earlier rule says a variant must beat the baseline or the run stops. You now want flagged and below-threshold variants shown, with a label. I suggest: show them, label them "below the bar", and let only passing variants into the sandbox.
3. **Gap order.** You want Jev to tag every baseline block first, then the LLM picks the gap from the tags. The current flow does the reverse. I suggest your order. It is more defensible.
4. **How many variants go to the sandbox?** More than two arms need a correction for many comparisons (Holm), or one named primary comparison fixed at step 9. I suggest one primary comparison per variant against the baseline, with Holm.
5. **Which folder is the real one?** `token-factory` or `token-factory-gpt`.

## How to run the synthetic test (my answer)

Use real browsers with synthetic people. Do not let an LLM "decide" to click and call that evidence.

1. Playwright opens each approved arm as local HTML. This is real.
2. Each visitor has a persona from the page's buyer list and a visitor id.
3. A hash of the id and a fixed seed picks the arm. The same visitor always gets the same arm, also after a reload.
4. The page logs one exposure event on load. The click on the main button logs one conversion event. Both go to a file with visitor id, arm, time and persona.
5. Whether the visitor clicks depends on a click chance. You declare it per persona and per scenario. Two scenarios: **clear effect** and **inconclusive**. This number is the only SYNTHETIC part. Every report line says so.
6. The same run also checks the user flow: the button, its target, the form and its validation, in every arm.
7. Rules compute the rates, a confidence interval and the pre-set decision. No model is involved.

This meets "perform real actions" and keeps the findings honest.

## Where each kind of decision belongs

| Decision | Who decides | Why |
|---|---|---|
| Does the claim id exist? Is the quote in the saved source? Is a banned word used? | Rules | Exact. Same answer every time. |
| Does this block show proof, name the audience, state a clear CTA? | Jev (typed), second judge as check | Many small yes/no calls. Judges can disagree. |
| Does this rewrite keep the supported claims? | Rules first, then both judges | Rules are the gate. Judges add signal. |
| Is the variant good enough to show a person? | Threshold on rules plus judges | Fixed number set before the run. |
| Approve the experiment | Person | The assignment requires it. |
| Did the variant win the test? | Rules | Fixed rule from step 9. |
| Roll out | Person | The assignment requires it. |

## Recommended plan (not started)

Scope rule from `NEXT-SESSION.md` still holds: one command, one page, one approval, one sandbox test. The web app and any-page research come later.

1. Fix the five faults above (hash, CTA, jc-03, folder, no legacy approval).
2. Build step 4 (Jev tags baseline blocks) and the second judge. Record both verdicts and the disagreement.
3. Build steps 7 and 11 from the existing checks plus the two judges.
4. Replace the simulator with the Playwright visitor run. Keep the old simulator for the scale demo.
5. Wire steps 14 and 15 to the new run and to `report.py`. Add the rollout-approval step.
6. Record a reject scenario and a revise-then-reapprove scenario.
7. Fill `submission/` last: README, as-built architecture, Jev note, real versus simulated.

## What stays unverified

- Whether Jev separates good variants from bad ones. Run-03 gave 14 of 14 "yes". It needs failure cases it must fail.
- Whether the live model path works on this machine. Not run in this audit.
- Buyer preference. Nothing here observes real buyers.

## Proposed process flow (v3, 15 Nov 2026, for owner sign-off)

Written for: the project owner. PROPOSED. Not built. Replaces the step list in `flow.json` only after sign-off.

Roles: **Rules** = code, same answer every time. **LLM** = writer. **Jev** = typed decision model. **Judge 2** = a second decision model from a different family. **Person** = a human click.

| # | Step | Who | Output | Assignment line |
|---|---|---|---|---|
| 0 | One command starts the run. A run plan page shows every step, who does it, and what is real or simulated. | Rules | Run plan | One command; note on real versus simulated |
| 1 | Start form: page URL, buyer persona, vertical, scope (hero or page), goal (one conversion action from a short list), test type (message, CTA or structure). | Person | Brief | Choose audience and action |
| 2 | Positioning: reuse the saved one, or generate from the skills and rules. Rules check every claim id and quote. | LLM, then rules | Position | Assess positioning |
| 3 | Capture the page with Playwright. Build the local copy. Check fidelity against the live page. | Rules | Baseline | Recreate a page; provide a baseline |
| 4 | Tag every baseline block: proof point, audience clarity, CTA clarity. Both judges tag. Disagreements are flagged. | Jev, Judge 2 | Block tags | Identify a gap |
| 5 | Pick one gap from the tags. State the evidence, the hypothesis, and that internal analytics are unknown. | LLM, then rules | Gap and hypothesis | Explain evidence and hypothesis |
| 6 | Lock the test plan: goal, metric, decision rule, significance level, visitors per arm, two arms, two scenarios. Hash it. A later change voids the run. | Rules | Test plan | Define action, metric and rule upfront |
| 7 | Write 2 to 3 variants inside the scope, with the copywriting and CRO skills and the brand rules. | LLM | Drafts | Create a variant |
| 8 | Check the drafts. First the code checks (claim ids, quotes, banned claims, nothing outside scope, same CTA in message mode). Then both judges. Then the scorecard against the baseline. A failed section goes back to the writer, 2 rounds at most. | Rules, Jev, Judge 2 | Verdicts and scores | Preserve supported claims |
| 9 | Keep the strongest variant that beats the baseline. If none does, stop and say why. | Rules | One variant | Create a variant |
| 10 | Functional check: Playwright clicks the CTA in each arm and records where it goes and what the form does. | Rules | Flow test | Functional check of the user flow |
| 11 | Approval page: side-by-side preview, diff, scores, judge disagreements, goal and test plan. Held variants sit in a short labelled list. Approve, Reject or Revise. A judge hold can be overridden. A failed code check cannot. Reject keeps the change inactive. Revise returns to step 7 and needs a fresh approval. | Person | Approval, hashed | Require approval |
| 12 | Sandbox: Playwright bots with personas load baseline and variant. A hash of seed and visitor id fixes the arm. The page logs exposure and conversion events. Click chance is declared per persona, in two scenarios: clear and inconclusive. | Rules | Event log | Test the hypothesis |
| 13 | Findings: conversion rate per arm, confidence interval, decision by the locked rule. Every line says SYNTHETIC. | Rules | Findings page | Publish findings |
| 14 | Rollout approval. Nothing goes live without it. | Person | Rollout decision | Rollout needs approval |
| 15 | Submission: README with setup and demo command, architecture note, Jev note (decisions, where rules, LLM and Jev fit, one decision tested against cases including a failure case), limitations. | Rules | `submission/` | What to submit |

**Model at runtime:** steps 2, 4, 5, 7 and 8 call a model. That meets the assignment.

**Hard rules**
- No model writes a file. It returns JSON. The engine checks the schema.
- The code checks are the hard gate. A judge can add a hold. A judge cannot cancel a failed code check.
- The approval hash covers the brief, baseline, plan, variant and rendered page.
- The goal and test plan are locked at step 6. The writer never sees them change.

**Test types** (two arms, one primary action, same maths): message, CTA, structure. Multivariate and multi-arm tests are listed as limitations.

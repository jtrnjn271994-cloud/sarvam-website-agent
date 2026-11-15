# Gap dossier (PROBE)

The hero currently shows the headline "Better code in the long run". The sub-line states, "Coding Agents work across the codebase and saves checkpoints as it goes. The plan stays visible, so you can change direction while the run is live." The primary button reads "Try Coding Agents".

This copy fails several buyer needs. The headline does not state what the product does or what the buyer gets. The hero gives no checkable proof point. It leaves the main objection unanswered: The pilot cannot reach production data. Technical evaluators in GCCs and IT services must maintain local data control before running code tools. For the buyer question answered worst, none asked (page questions not approved).

Our evidence shows that repositories, prompts, and run history stay within Indian jurisdiction (CL-008). Coding Agents also saves checkpoints and executes test suites after every change (CL-001, CL-004, CL-005).

Hypothesis: If we change the headline, sub-line, and call-to-action copy for technical evaluators in GCCs and IT services to state Indian jurisdiction and step-by-step test execution, more of them click the hero's main button, because engineering leaders require local data residency and automated testing.

We have no internal analytics, so the real click rate is unknown. A flat or lower click rate on the new button during a test proves this hypothesis wrong.

## Audit method

| Question | Asked | Jev probability | Calibrated band | Result |
|---|---|---|---|---|
| A1-audience | Does the hero speak to this buyer and their situation, so that the buyer would see themselves in it? | 0.60 | pass at 0.69, fail at 0.17 | hold |
| A2-value | Does the headline say what the product does and what the buyer gets, in words this buyer uses? | 0.13 | pass at 0.50, fail at 0.09 | hold |
| A3-proof | Does the hero give a checkable proof point, such as a named standard, a number with its source, or a named customer? | 0.03 | pass at 0.74, fail at 0.04 | fail |
| A4-cta | Does the main button tell this buyer what happens when they click it? | 0.24 | pass at 0.64, fail at 0.48 | fail |
| A5-positioning | Does the hero say what the positioning's main claim says? | 0.46 | no band (advisory) | advisory-hold |
| A7-checklist-item-1 | Does the hero answer this question the buyer asks: Does the page say Coding Agents work across the codebase and save checkpoints as they go? | 0.97 | pass at 0.82, fail at 0.23 | pass |
| A8-objection | Does the hero answer this objection the buyer raises: The pilot cannot reach production data? | 0.13 | pass at 0.44, fail at 0.37 | fail |

Page questions: approved by Claude, on the owner's instruction on 2026-11-15T20:40:37. Out of hero scope (the page body must answer these): Does the page say whether repositories, prompts, and run history stay hosted in India; Does the page show how tasks are routed to lower-cost models to manage token cost; Does the page say whether Coding Agents connect to existing HR and ticket systems; Does the page show how Coding Agents run your test suite after each change.

How to read the band: a good-direction question passes at or above the pass line and fails at or below the fail line; between the two it is held for a person. A bad-direction question (A6) flags at or above the flag line. 'Advisory' means the calibration cases did not separate cleanly, so the result informs but never blocks.

Limits: Jev and Judge 2 are general decision models. We did not train or fine-tune either one for this program. The pass lines come from a small set of examples that we wrote. The probabilities are an audit signal, not an assurance. A person makes every approval.

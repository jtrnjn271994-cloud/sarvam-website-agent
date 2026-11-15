# Gap dossier (PROBE)

The hero headline currently reads: "Voice agents that sound human and deliver results". The sub-line reads: "One platform to build, launch and scale voice agents that carry your customer context into every call and work each conversation toward your business outcomes." The button reads: "Start building".

This hero fails the buyer question: "Does the page say these voice agents are built for collecting overdue loan payments". Collections leaders in banks and lending firms require clear loan recovery tools. They worry that a voice agent cannot capture a promise to pay or route hard cases to human agents. Vague promises about business outcomes do not answer these concerns. Our evidence proves that voice agents connect to business systems to update records during conversations (CL-008) and integrate directly with telephony and CRM platforms (CL-009). The current hero omits these capabilities.

Hypothesis: If we change the hero copy to emphasize collections use cases and system integration for business owners in banks and lenders, more of them click the hero's main button, because the copy directly addresses loan recovery workflows.

We have no internal analytics, so the real click rate is unknown. An equal or lower click rate on the hero's main button proves the hypothesis wrong.

## Audit method

| Question | Asked | Jev probability | Calibrated band | Result |
|---|---|---|---|---|
| A1-audience | Does the hero speak to this buyer and their situation, so that the buyer would see themselves in it? | 0.60 | pass at 0.69, fail at 0.17 | hold |
| A2-value | Does the headline say what the product does and what the buyer gets, in words this buyer uses? | 0.32 | pass at 0.50, fail at 0.09 | hold |
| A3-proof | Does the hero give a checkable proof point, such as a named standard, a number with its source, or a named customer? | 0.04 | pass at 0.74, fail at 0.04 | fail |
| A4-cta | Does the main button tell this buyer what happens when they click it? | 0.28 | pass at 0.64, fail at 0.48 | fail |
| A5-positioning | Does the hero say what the positioning's main claim says? | 0.41 | no band (advisory) | advisory-hold |
| A7-checklist-item-1 | Does the hero answer this question the buyer asks: Does the page say these voice agents are built for collecting overdue loan payments? | 0.10 | pass at 0.82, fail at 0.23 | fail |
| A8-objection | Does the hero answer this objection the buyer raises: The bot cannot capture a promise to pay or route a hard case to a human? | 0.13 | pass at 0.44, fail at 0.37 | fail |

Page questions: approved by Console user on 2026-11-15T20:19:37. Out of hero scope (the page body must answer these): Does the page say the agent can capture a customer's promise to pay and record it in our systems; Does the page show how a hard or disputed case is handed off to a human agent; Does the page show collections results such as collection efficiency, bounce rate or flow rates from a real lender; Does the page say we can run a small pilot and compare repayment rates against our current calling team; Does the page say we can set different call rules or goals for each overdue bucket.

How to read the band: a good-direction question passes at or above the pass line and fails at or below the fail line; between the two it is held for a person. A bad-direction question (A6) flags at or above the flag line. 'Advisory' means the calibration cases did not separate cleanly, so the result informs but never blocks.

Limits: Jev and Judge 2 are general decision models. We did not train or fine-tune either one for this program. The pass lines come from a small set of examples that we wrote. The probabilities are an audit signal, not an assurance. A person makes every approval.

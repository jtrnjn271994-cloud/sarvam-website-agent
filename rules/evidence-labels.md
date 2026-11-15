# Evidence labels

Draft, 13 Nov 2026. One label set for every page the agent works on. The user has not yet approved it.

## The label set

Use these seven labels exactly as written. Each item gets one label.

| Label | Meaning |
|---|---|
| CHECKED | A rule-based check passed it. A ledger id says which check. |
| CALC | Our own arithmetic on checked or vendor inputs. The note shows the inputs and the formula. |
| VENDOR | A company says it on its own page or in its own file. We have not tested it. |
| SEMRUSH | A Semrush estimate. It is not a measured visit count. |
| AUDIT | A GPT or third-party analysis. It is a lead to check. It is never evidence. |
| PROPOSED | An idea or draft of ours. It is not a fact. |
| UNCHECKED | Nobody has checked it yet. Do not use it in page copy. |

## Two rules

1. **No evidence id, no claim.** Every claim in a draft names at least one evidence id. A claim without an id is removed.
2. **AUDIT items are never evidence for a page claim.** A GPT note or a third-party analysis can point to a source. The source must pass a check before the page uses it.

Held items (see the mapping table) are never evidence. They never reach a page.

## Mapping from the other label systems

Names of sources and folders are plain text in this file. They are not links.

### Plain-writing skill (marketing-plain-writing)

| Old label | New label | Note |
|---|---|---|
| VERIFIED | CHECKED | Same meaning. |
| VENDOR | VENDOR | No change. |
| INFERENCE | DECIDED | PROPOSED. Reason: an inference is a reasoned idea, not a measured fact. CALC fits only if the step is arithmetic. |
| PROPOSED | PROPOSED | No change. |
| UNCHECKED | UNCHECKED | No change. |

### Buyer table (buyer.json in pages/token-factory/buyer-and-wedge)

| Old label | New label | Note |
|---|---|---|
| CHECKED | CHECKED | The file says the quote passed the rule-based check. The ledger id is given. |
| FIELD_KIT | DECIDED | PROPOSED. Reason: the file calls these analyst proposals, not checked buyer facts. |
| GTM | DECIDED | VENDOR only if the GTM map data holds a sourced fact. Otherwise PROPOSED. Reason: the GTM map is our own work, and its status per item is not shown in buyer.json. |
| HYPOTHESIS | PROPOSED | The file says it is derived from rival page patterns and not tested with a buyer. |

### Validation ledgers (02 Assets/Research/validation and icp-round-2)

| Old status | New label | Note |
|---|---|---|
| PASS | CHECKED | Ledger id is the evidence id. |
| PASS-2ND | CHECKED | A second tool also confirmed it. |
| CALC | CALC | No change. |
| NUM-ONLY | DECIDED | UNCHECKED. Reason: the number is on the page, but the link to the company is not confirmed. |
| THEME | DECIDED | UNCHECKED. Reason: the ledger ladder shows THEME but does not define it, so treat it as not yet checked. |
| UNCHECKED | UNCHECKED | No change. |
| WEAK | Held, never evidence | The ledger holds it back. It never shows in the Field Kit. |
| FAIL | Held, never evidence | The check failed. |
| OLD-SOURCE | Held, never evidence | The source is too old. |

### README of 09 Token Factory Agent and the Foundation Audit

| Old label | New label | Note |
|---|---|---|
| VENDOR | VENDOR | No change. |
| CHECKED | CHECKED | No change. |
| SEMRUSH | SEMRUSH | No change. |
| PROPOSED | PROPOSED | No change. |
| UNCHECKED | DECIDED | The Foundation Audit defines UNCHECKED as a pasted GPT note. Under the new set, a GPT note is AUDIT. Recommend AUDIT for those items and UNCHECKED for items nobody has looked at. |
| SYNTHETIC | DECIDED | a separate data tag, not an evidence label. Reason: it says how a result was made, not how well a source is checked. Synthetic results never back a claim about real buyers. |

## Gaps in the label set

| Gap | What we need from the user |
|---|---|
| Regulator and government texts (RBI, IRDAI, TRAI) are not vendor claims. | DECIDED. CHECKED once a rule-based check passes. Until then, UNCHECKED. |

## Decisions (user, 13 Nov 2026: accept all)

The user accepted every recommendation below. Each one is now a rule.

1. INFERENCE (skill): PROPOSED or CALC?
2. FIELD_KIT (buyer.json): PROPOSED?
3. GTM (buyer.json): VENDOR or PROPOSED?
4. NUM-ONLY (ledgers): UNCHECKED?
5. THEME (ledgers): UNCHECKED?
6. SYNTHETIC (README): separate data tag?
7. UNCHECKED in the Foundation Audit: AUDIT or UNCHECKED?
8. Regulator texts: CHECKED after a rule-based check?

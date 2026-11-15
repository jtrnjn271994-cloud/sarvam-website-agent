---
id: DEC-001
title: "Do not claim list"
type: decision
tier: 2
owner: user
updated: 2026-11-13
status: current
source: "Job Hunt/sarvam/CLAUDE.md, section Do not claim, read 2026-11-13"
---

# Do not claim

Source: Job Hunt/sarvam/CLAUDE.md, section Do not claim, read 2026-11-13. This is a plain-text copy. The checker and Jev read the BAN lines below. Every phrase in lower case is withdrawn or banned for the Token Factory page.

## Ban list

- BAN: best indic speech accuracy
  - Reason: Gnani's Prisma v2.5 claims to beat Sarvam in 8 of 9 languages.
- BAN: sovereign cloud
  - Reason: Yotta, E2E, Krutrim and L&T own that story. Yotta calls Shakti Studio an "AI Token factory".
- BAN: understands indian languages
  - Reason: BharatGen, Gnani and AI4Bharat make that claim too.
- BAN: the 105b price conflicts
  - Reason: Stale. On 8 Nov 2026 the pricing page and docs agree (₹15 input, ₹5 cached, ₹60 output per million tokens).
- BAN: the 105b price is 7× apart
  - Reason: Stale. The pricing page and docs agree. The earlier disagreement is dated history only.
- BAN: publish one price first
  - Reason: Stale. The pricing page and docs agree since 8 Nov 2026.
- BAN: sarvam train
  - Reason: Use "Custom Model Training" (sarvam.ai/products/model-training).
- BAN: epoch builder edition
  - Reason: Use "Custom Model Training". Builder Edition is the developer event.
- BAN: kivi as hardware
  - Reason: Kivi is desktop voice software (heykivi.ai).
- BAN: cyber as a shipped product
  - Reason: Sarvam Cyber is a preview centred on vulnerability investigation. Check the official page first.
- BAN: anvaya as a shipped product
  - Reason: Anvaya has an official description at a different maturity. Check the official page first.
- BAN: the $2.25–2.4b india market estimate
  - Reason: Withdrawn. The components are unsourced.
- BAN: 15b calls
  - Reason: Withdrawn. The call bridge turns calls into minutes without a call duration.
- BAN: the $33.6m arr
  - Reason: Withdrawn. The components are unsourced.
- BAN: lowest voice price
  - Reason: Bolna and Retell publish tariffs. Compare inclusions and completed outcomes.
- BAN: only published voice price
  - Reason: Bolna and Retell publish tariffs.
- BAN: prism as an operations product
  - Reason: Sarvam describes Prism as a decision API for builders. Position it for builders. Benchmark evidence is vendor-run.
- BAN: 94% vs 71% vs gpt-4o
  - Reason: The unnamed-telecom figure is unverified.

## Source text, copied word for word


> - **"Best Indic speech accuracy."** Gnani's Prisma v2.5 claims to beat Sarvam in 8 of 9 languages.
> - **"Sovereign cloud."** Yotta, E2E, Krutrim (now a cloud company) and L&T own that story. Yotta even calls Shakti Studio an "AI Token factory".
> - **"Understands Indian languages."** BharatGen, Gnani and AI4Bharat make that claim too.
> - **"The 105B price conflicts / is 7× apart / publish one price first."** Stale. On 8 Nov 2026 the pricing page and docs agree (₹15 input, ₹5 cached, ₹60 output per million tokens). The earlier disagreement (ledger H015) is dated history only.
> - **"Sarvam Train" or "Epoch Builder Edition" as product names.** Use "Custom Model Training" (sarvam.ai/products/model-training). Builder Edition is the developer event.
> - **Kivi as hardware, or Cyber and Anvaya as shipped products.** Kivi is desktop voice software (heykivi.ai). Sarvam Cyber is a preview centred on vulnerability investigation, and Anvaya has an official description at a different maturity. Check each official page before calling either available.
> - **The $2.25–2.4B India market estimate, "15B calls" and the $33.6M "ARR".** Withdrawn. The components are unsourced and the call bridge turns calls into minutes without a call duration (ledger N030, H005, H006).
> - **"Lowest" or "only published" voice price.** Bolna and Retell publish tariffs. Compare inclusions and completed outcomes, not the headline rate.
> - **Prism as an operations product.** Sarvam's own blog and Token Factory docs describe it as a decision API for builders (typed options with probabilities). Position it for builders, not as part of the lead voice story. Benchmark evidence is vendor-run.
> - **The unnamed-telecom "94% vs 71% vs GPT-4o" figure.** It's unverified.

## Open checks

From the project README, section Open checks, read 2026-11-13.

1. The click must lead to something real: a comparison of the buyer's stated workload. The note must say what the buyer receives.
2. Neither idea above (API routing, in-organisation hosting) is proven for Token Factory.
3. Avoid the word "compute". Our data parks compute for most industries.
4. Which CTA leads the hero today is not confirmed.
5. The validation quote is not yet a ledger row. I matched it by eye to the saved transcript text. Run it through verify_quotes.py before it goes into copy.

## Label decisions

The user accepted all 8 label decisions on 13 Nov 2026. The full list and the mapping tables are in [evidence-labels.md](../../../rules/evidence-labels.md).

Short form of the 8 decisions:

1. INFERENCE becomes PROPOSED (CALC only if the step is arithmetic).
2. FIELD_KIT becomes PROPOSED.
3. GTM becomes PROPOSED, or VENDOR if the GTM map holds a sourced fact.
4. NUM-ONLY becomes UNCHECKED.
5. THEME becomes UNCHECKED.
6. SYNTHETIC is a separate data tag, not a label.
7. A GPT note becomes AUDIT. Nobody-looked items stay UNCHECKED.
8. Regulator texts become CHECKED after a rule-based check. Until then UNCHECKED.

# Examples: positions

Every fact comes from `pages/token-factory/` (context pack, claims, evidence, rival rows). The shape follows `library/positioning/final-positioning/Token Factory Positioning — Seven Pages.md`, which is a PROPOSED draft. No position here is approved.

## Good 1. The test promise

- First buyer: AI platform lead at a GCC or IT services firm (PROPOSED, no interview).
- Category: managed model inference, an API that runs a model for an application.
- Alternatives: keep an internal serving stack; a global managed provider (Nebius, Fireworks, Together); an India provider (E2E Blaze, Yotta Shakti Studio, Krutrim); an existing cloud platform such as Amazon Bedrock.
- Main claim: "Put a production model workload on an India-served API, then prove it meets your quality, speed and cost bar." (PROPOSED)
- Proof: CL-001 open models through an OpenAI-compatible API (VENDOR); CL-002 inference on Sarvam-operated GPUs in India (VENDOR); CL-011 list price, INR 14 in and INR 55 out per 1M tokens, excluding GST (CHECKED).
- Swap test: E2E Blaze states India, INR and an OpenAI-compatible API (EV-019). It does not offer a workload test on the page we hold. No row says yes. Rival pages need a re-read (UNCHECKED).
- Weak points: no named Token Factory customer; no matched quality, speed and cost test; the step after the main button is unknown.
Why it is good: the claim is a test the buyer can run. The swap test is per rival with a reason. The weak points are real.

## Good 2. The data boundary first

- First buyer: risk and compliance reviewer at an IT services firm (BR-003, PROPOSED).
- Main claim: "Know where your workload runs and on what terms, then test it." (PROPOSED)
- Proof: CL-002 India GPUs (VENDOR); CL-004 zero data retention on request (VENDOR); CL-005 ISO 27001:2022 and SOC 2 Type II (VENDOR); CL-003 99.95% uptime SLA by contract (VENDOR).
- Swap test: E2E can print an India line. It shows no SLA or certifications on the page we hold (EV-019). Rival could print the SLA or certification lines: unknown (UNCHECKED). The claim keeps all three facts together, each with its limit.
- Weak points: zero retention is "on request" and separate from India processing; the SLA is set by contract; the claim rests on VENDOR facts only.
Why it is good: each fact keeps its limit. The swap test says what is unknown.

## Good 3. A weak position marked as weak

- Main claim: "Switch models by changing the model name." (PROPOSED, CL-006)
- Swap test: an aggregator such as OpenRouter can print "many models, one API" (context pack section 5). Result: rival_could_print true.
- Action: rewrite or drop the claim. Weak point 1: "an aggregator can print this".
Why it is good: the position admits the failed swap row and does not hide it.

## Bad 1. India-first line

Main claim: "Run open models on GPUs in India."
Why it fails: E2E Blaze can print it (EV-019). Context pack section 11 rejected it by hand. Check: `swap_test_each_rival`.

## Bad 2. Proof is an AUDIT note

Proof line: "Sarvam may be the only page that shows India processing, an uptime SLA and zero retention together." Label AUDIT, source LIB-117.
Why it fails: an AUDIT note is never evidence. A missing rival feature does not prove the rival lacks it (context pack section 6). Checks: `evidence_ids_exist`, `labels_valid`.

## Bad 3. Two first buyers

First buyer: "AI platform lead at a GCC or IT services firm, or the Head of the GCC."
Why it fails: the context pack lists this as an open conflict (section 3). The step must write both roles in `self_check.gaps` and stop for the brief to close it. Check: `open_conflicts_listed` at step 0.

## Bad 4. Lower-cost claim

Main claim: "Cheaper and faster open-model inference from India."
Why it fails: no speed numbers and no matched test exist. The position bans lower-cost and speed claims (context pack section 7). Checks: `do_not_claim`, run contract rule 8.

## Bad 5. Swap test with one row

Swap test: one line, "No rival can print this."
Why it fails: the check needs one row for each rival row (Nebius, E2E Blaze, Fireworks, Together, Yotta, Krutrim). Check: `swap_test_each_rival`.

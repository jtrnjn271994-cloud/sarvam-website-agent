---
id: BR-001
title: "Technical evaluator (GCC CTO or VP Engineering, Head of AI platform)"
type: buyer-checklist
tier: 2
owner: claude
updated: 2026-11-13
label: PROPOSED
source: "GCC committee file (committee.csv) and buyer.json, copied 2026-11-13; role text is analyst data, not buyer interviews"
lib_ids: [LIB-017, LIB-148]
review_by: 2027-05-12
main_objection: "The pilot cannot reach production data, or the model fails the team's own test set."
questions_approved_by: ""
questions_approved_on: ""
---

# Technical evaluator (GCC CTO or VP Engineering, Head of AI platform)

## Role and why they matter

The committee file lists this role as owning "Model tests, integration and the pilot design". Titles in the file: Head of AI; Head of Engineering India; Chief Technology Officer and Managing Director of the India centre. buyer.json adds "GCC CTO or VP Engineering" and "Head of AI platform" as roles. This person runs the test, so the page must make the test easy to start.

The source rows carry the old label INFERENCE or FIELD_KIT. Under the label decisions both become PROPOSED. We hold no buyer interview for this role.

## What they need from the page

- Accuracy on real data; hosting in India; links to existing systems; token cost. Source: library/buyers-and-committees/icp-round-2/gcc/committee.csv, cares_about, row Technical evaluator. Label: PROPOSED.
- A benchmark on the team's own workload: cost, latency, language quality, and effort to switch. Source: pages/token-factory/buyer-and-wedge/buyer.json, need (old label FIELD_KIT). Label: PROPOSED.

## Their likely objection

- The pilot cannot reach production data, or the model fails the team's own test set. Source: library/buyers-and-committees/icp-round-2/gcc/committee.csv, blocks_if. Label: PROPOSED.
- Who owns fine-tuned weights. Source: pages/token-factory/buyer-and-wedge/buyer.json, objections (old label FIELD_KIT). Label: PROPOSED.

## Questions the page must answer

Scope tags (proposed by Claude on 15 Nov 2026, a person confirms): [hero] means the hero (H1, sub-line, main button) can fairly answer it, so the hero audit asks it. [page] means only the page body can answer it; the dossier lists it as out of hero scope. The audit asks these questions and the main_objection only after a person fills questions_approved_by and questions_approved_on above.

- [hero] Does the page say how to test one workload?
- [hero] Does the page say the API is OpenAI-compatible?
- [hero] Does the page say where inference runs?
- [hero] Does the page show a price per 1M tokens, or link to prices?
- [page] Does the page say who owns fine-tuned weights?

## Evidence ids that help

- EV-007: Token Factory page: subheadline
- EV-008: Token Factory page: OpenAI-compatible Chat Completions and Responses APIs
- EV-009: Token Factory page: inference runs on Sarvam-operated GPUs in India
- EV-013: Token Factory page: all catalogue models work with one API key
- EV-014: Token Factory page: models named in the serverless sample
- EV-015: Token Factory price: DeepSeek V4.1 Flash 1017 at INR 14 in and INR 55 out

Note: the committee file was built for Voice Agent and HR-onboarding research. Token Factory fit for this role is untested.

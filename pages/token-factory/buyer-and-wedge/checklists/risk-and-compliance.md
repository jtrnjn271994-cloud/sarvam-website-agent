---
id: BR-003
title: "Risk and compliance (parent company CIO, CISO, chief risk officer)"
type: buyer-checklist
tier: 2
owner: claude
updated: 2026-11-13
label: PROPOSED
source: "GCC committee file (committee.csv) and buyer.json, copied 2026-11-13; role text is analyst data, not buyer interviews"
lib_ids: [LIB-017]
review_by: 2027-05-12
---

# Risk and compliance (parent company CIO, CISO, chief risk officer)

## Role and why they matter

The committee file lists this role as owning the "Approval of any AI tool that touches parent data or staff data". Titles: Parent-company chief information officer; chief information and AI officer; chief risk officer; chief information security officer. The role can block a deal.

The source rows carry the old label INFERENCE or FIELD_KIT. Under the label decisions both become PROPOSED. We hold no buyer interview for this role.

## What they need from the page

- Data stays in approved places; audit trail; vendor risk review; one approved AI stack. Source: library/buyers-and-committees/icp-round-2/gcc/committee.csv, cares_about, row Risk and compliance. Label: PROPOSED.

## Their likely objection

- The tool sends data outside the approved cloud, or lacks an audit trail. Source: library/buyers-and-committees/icp-round-2/gcc/committee.csv, blocks_if. Label: PROPOSED.
- Where models run and where data is stored (written for banks; a likely GCC objection only as a hypothesis). Source: pages/token-factory/buyer-and-wedge/buyer.json, objections (old label FIELD_KIT). Label: PROPOSED.

## Questions the page must answer

- Does the page say where inference runs?
- Does the page say zero data retention is available on request?
- Does the page name its security certifications?
- Does the page say operational logs follow separate terms?

## Evidence ids that help

- EV-009: Token Factory page: inference runs on Sarvam-operated GPUs in India
- EV-011: Token Factory page: zero data retention on request
- EV-012: Token Factory page: ISO 27001:2022 and SOC 2 Type II
- EV-010: Token Factory page: 99.95% uptime guaranteed by an SLA

Note: the committee file was built for Voice Agent and HR-onboarding research. Token Factory fit for this role is untested.

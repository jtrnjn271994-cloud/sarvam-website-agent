# Jev cases for Token Factory

Draft, 13 Nov 2026. Test results use the label SYNTHETIC. A Jev answer is AUDIT. It helps a person decide. It is never evidence.

## How a case works

1. One JSON file holds one yes/no question about one real line.
2. Jev reads the files in `input_files` and answers yes or no.
3. A person compares the answer with `expected`. A match means the check works.
4. A failure case holds a line that must fail. Its `expected` is always "no".

The questions follow the templates in `skills/jev-decision-test/SKILL.md`. They never ask for an opinion or a ranking.

## Schema

| Field | Meaning |
|---|---|
| id | Short id, such as jc-01. |
| question | One narrow yes/no question. It names the exact line. |
| input_files | Project-relative paths Jev may read. |
| expected | "yes" or "no". |
| kind | "normal" or "failure". |
| why | One plain sentence that says why the expected answer is right. |
| check | One of: evidence_supports_line, same_promise_as_rival, clear_next_step, swap_test, banned_phrase, supporting_audience_fit. |
| audience_id | Optional extra field. A BR id from the buyer checklists. Used on supporting_audience_fit cases. |

## Cases

| Id | Question, short | Expected | Kind |
|---|---|---|---|
| jc-01 | BR-001: does EV-008 support the OpenAI-compatible line? | yes | normal |
| jc-02 | BR-001: does EV-008 support "no testing" on a move? | no | failure |
| jc-03 | BR-005: does EV-013 support one API key, change the model name? | yes | normal |
| jc-04 | BR-005: does the "sovereign AI choice" line avoid calling Sarvam sovereign? | no | failure |
| jc-05 | BR-003: does EV-011 support zero data retention on request? | yes | normal |
| jc-06 | BR-003: does EV-009 support "tools also run in India"? | no | failure |
| jc-07 | BR-004: does EV-015 support the INR price line, excluding GST? | yes | normal |
| jc-08 | BR-004: does EV-010 support "every user gets a 99.95% SLA"? | no | failure |
| jc-09 | Does the "sovereign cloud" line avoid every BAN phrase? | no | failure |
| jc-10 | Does CL-001's OpenAI-compatible promise match a rival promise? | yes | normal |
| jc-11 | Does the generic "fast, scalable, private" line pass the swap test? | no | failure |
| jc-12 | Does EV-002 support "Sarvam models reach 97% or 98%"? | no | failure |

Supporting audiences covered, two cases each: BR-001 (AI platform leads), BR-005 (practice heads and architects), BR-003 (risk and compliance), BR-004 (procurement).

## Limits

- There are 12 cases. The Jev cap is 12 calls per run. Run all 12 once, with no repeats.
- No case uses the clear_next_step check yet. The main CTA "Compare on your workload" has an open check in `pages/token-factory/decisions/do-not-claim.md`: the click must lead to something real. A person must settle that first.
- Cases use real lines from the claims and the do-not-claim list. Jev-only lines (jc-02, jc-04, jc-06, jc-08, jc-11, jc-12) are planted wrong lines. They are not page copy.

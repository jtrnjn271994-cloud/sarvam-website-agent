---
id: EV-017
title: "Reference job on Sarvam's price: INR 48,500 a month; on the rival price: USD 1,050"
type: evidence
tier: 2
owner: claude
updated: 2026-11-13
source: "Our own arithmetic on checked prices and the Field Kit reference job"
data_as_of: 2026-11-12
status: current
export: no
review_by: 2027-02-11
label: CALC
lib_ids: [LIB-042, LIB-084, LIB-128]
quote: "1 million requests a month, each with 1,500 input tokens and 500 output tokens (1,500M in, 500M out)."
location: "library/buyers-and-committees/field-kit-source/addon-data.js, line 7 (D.job); inputs from EV-015 and EV-016"
supports: "On the Field Kit reference job, the Sarvam list price gives INR 48,500 a month, and the rival list price gives USD 1,050."
does_not_show: "The job is a Field Kit assumption, not a buyer's workload. We have no checked exchange rate. So the two sums do not compare. It is no cost claim."
---

Sarvam: 1,500 x 14 + 500 x 55 = 21,000 + 27,500 = INR 48,500 for 1,500M input and 500M output tokens. Rival: 1,500 x 0.30 + 500 x 1.20 = 450 + 600 = USD 1,050. The Field Kit also holds an exchange rate, but it came from a search excerpt and no ledger passed it. So we did not convert.

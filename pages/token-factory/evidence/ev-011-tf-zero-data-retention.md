---
id: EV-011
title: "Token Factory page: zero data retention on request"
type: evidence
tier: 3
owner: vendor
updated: 2026-11-13
source: "Token Factory page text, fetched with curl on 2026-11-12, tag-stripped copy"
data_as_of: 2026-11-12
status: current
export: no
review_by: 2026-12-13
label: VENDOR
lib_ids: [LIB-128]
quote: "Zero data retention is available on request. Under an agreed ZDR arrangement, prompts and responses are not retained. Operational logs are scoped separately in the terms for your deployment."
location: "sarvam.ai_token-factory_fetched-2026-11-12.txt (one long line), https://www.sarvam.ai/token-factory, near the text \"What does zero data retention cover?\""
supports: "The page says zero data retention is available on request, under an agreed arrangement."
does_not_show: "It is conditional and not a default. Operational logs follow separate terms. Another block on the page says \"Never stored or used to train models\", which reads stronger."
---

Use the FAQ wording. It is the narrower and safer text. Do not write "never stored" without the "on request" condition.

---
id: EV-009
title: "Token Factory page: inference runs on Sarvam-operated GPUs in India"
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
quote: "Model inference runs on Sarvam-operated GPUs in India. Sarvam hosts the weights; requests are not forwarded to the original model developer’s overseas API."
location: "sarvam.ai_token-factory_fetched-2026-11-12.txt (one long line), https://www.sarvam.ai/token-factory, near the text \"Where is our inference processed?\""
supports: "The page says inference runs in India on Sarvam's own GPUs and does not go to the model maker's overseas API."
does_not_show: "It is the vendor's claim, not audited. The page says tools your application connects to have their own processing locations."
---

This is the FAQ answer on where inference is processed. The page also says external tools connected by your application have their own processing locations and data policies. Do not stretch the claim to cover them.

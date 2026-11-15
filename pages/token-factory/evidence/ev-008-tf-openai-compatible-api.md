---
id: EV-008
title: "Token Factory page: OpenAI-compatible Chat Completions and Responses APIs"
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
quote: "Sarvam supports OpenAI-compatible Chat Completions and Responses APIs. Update your endpoint, key and model, then validate the parameters, tool calls and outputs your application uses."
location: "sarvam.ai_token-factory_fetched-2026-11-12.txt (one long line), https://www.sarvam.ai/token-factory, near the text \"Can we move an existing AI application to Sarvam?\""
supports: "The page says an existing application moves by changing the endpoint, key and model, and then testing."
does_not_show: "Nobody has tested the move. The code sample on the page uses the sarvamai SDK, not the OpenAI client. Rival pages make the same claim."
---

The vendor says this in its FAQ. We read it on 12 Nov 2026 and did not test it. The page tells buyers to check parameters, tool calls and outputs themselves.

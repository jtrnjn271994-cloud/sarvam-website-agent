# Sarvam: competitor check by offering (web pass, 5 Nov 2026)

What this is: a web check of who Sarvam competes with at each layer, from Token Factory up to the newest bets. It updates the competitor column in `Positioning Context/market-map-strategy.md`. A second section covers the six evidence questions (why Sarvam won, results, deployment, renewals, economics, deployment models).

How to read it:
- **Confirmed**: an official page, or a named publication reporting a named fact.
- **Self-reported**: a vendor claiming something about itself, or about a rival. Use with attribution only.
- **Unverified**: an aggregator, a listicle or a competitor's blog. Don't put it on a slide.
- Most performance figures in this space are self-reported. No independent head-to-head study was found for any layer.

---

## Part A: competitors at each layer

### 1. GPUs and compute (sovereign infrastructure)
| Competitor | What they have | Status |
|---|---|---|
| **Yotta (Shakti Cloud)** | Says it supplies over 60% of IndiaAI Mission GPU capacity. It committed 10,000 B300 GPUs to the mission, out of 20,000 planned by Aug 2026. | Self-reported (Yotta press) |
| **E2E Networks (TIR)** | Listed GPU cloud with a Blackwell cluster at L&T Vyoma, Chennai. It has IndiaAI orders, e.g. ₹177 cr. | Confirmed (listed company, exchange filings) |
| **Krutrim (Ola)** | **New:** paused its own models and chips in 2026 and pivoted to AI cloud. Reported ₹300 cr FY26 revenue and a first profit. Staff fell from 550+ to about 150. | Secondary reports. Verify with Entrackr or filings. |
| Tata Communications Vayu, ESDS, CloudPe, NxtGen | Sovereign cloud alternatives | Listed only |
| AWS, Azure, Google Cloud | Indian regions | — |

**What this means:** Krutrim has moved from model rival to infrastructure rival. That makes "sovereign GPUs" even less of a differentiator. It backs the market map's rule: **don't pitch "Sarvam is a sovereign cloud."**

### 2. Token Factory (managed inference)
| Competitor | What they have | Status |
|---|---|---|
| **Yotta Shakti Studio** | Yotta calls it an **"AI Token factory"**, the same idea under almost the same name. It offers 25+ open models (LLM, speech, image, OCR) and serverless GPUs billed per minute, with "no invocation or platform fees". | Self-reported |
| **E2E Blaze / BlazeInfer** | Pay-per-token open models: Nemotron, DeepSeek, Qwen, GLM, Gemma **and Sarvam's own models**. That makes E2E a partner and a competitor at once. | Self-reported |
| Fireworks, Together AI, hyperscaler model gardens (Bedrock, Vertex, Azure AI Foundry) | Global managed inference | From the market map |

No public per-token prices were found for Yotta or E2E, so a real price comparison isn't possible yet.

### 3. Foundation models (Sarvam 105B / 30B)
| Competitor | Status |
|---|---|
| **BharatGen** (government-funded, IIT Bombay): Param2 17B MoE, 22 languages, plus finance, agriculture, law and Ayurveda models | Confirmed |
| **Krutrim**: model work reportedly paused (see 1) | Secondary |
| **Gnani.ai**: one of the 12 IndiaAI model builders | Confirmed (government list, per the market map) |
| Fractal, Tech Mahindra (Project Indus), Soket AI Labs | No 2026 detail found in this pass |
| OpenAI, Google, Anthropic, DeepSeek, Qwen, GLM, Mistral | Global generalists |

Quality evidence: Sarvam says 105B beats Gemini 2.5 Flash on Indian languages (self-reported). Benchlm's aggregated figures are mixed: Gemini 2.5 Pro leads on agentic tasks (61.7 vs 35.5), and Sarvam 30B leads Gemini 2.5 Flash on knowledge (80 vs 48.3). Treat as directional only.

### 4. Speech models (Saaras ASR, Bulbul TTS)
| Competitor | What they have | Status |
|---|---|---|
| **Gnani.ai** | **Prisma v2.5 (June 2026) claims first place in 8 of 9 Indian languages, ahead of Sarvam and ElevenLabs.** Vachana STT was trained on 1M+ hours. Vachana TTS does voice cloning in 12 languages. | Self-reported (Business Today) |
| **AI4Bharat** (open source) | IndicConformer ASR (22 languages), Indic Parler-TTS, IndicF5 | Confirmed (free, on AIKosh) |
| ElevenLabs | Seen as the leader on English expressiveness | Reviews |
| Deepgram, Whisper, Google, Azure | Global ASR and TTS | — |

**What this means:** Sarvam's claim to be the best Indic speech model is now contested in public. Sarvam says it wins on IndicVoices (about 19.3% WER), and Gnani says it wins 8 of 9 languages. A "best accuracy" headline won't hold up, so lead with cost, scale and end-to-end delivery instead.

### 5. Voice Agents (Samvaad, ₹3.50/min)
| Competitor | Scale / focus | Price per minute | Status |
|---|---|---|---|
| **Gnani.ai (Inya)** | Claims 30M+ calls a day and 200+ enterprises. Raised $10M (Aavishkaar, Mar 2026), hiring BFSI leaders. Publishes a "Gnani vs Sarvam" page claiming weeks to production vs Sarvam's "months". | Quote-based; a rival estimates ₹6+ | Self-reported / competitor claims |
| **Yellow.ai** | Multichannel (voice, chat, WhatsApp). Reported US IPO plan for 2026–27. | Rival estimate ₹4.50–7 | Unverified |
| **Skit.ai** | Collections and lending for BFSI and NBFCs | — | Listed |
| **Haptik** (Jio) | Retail, telecom, BFSI | Enterprise, about $5K/yr+ | Unverified |
| Uniphore, Exotel (contact-centre platforms) | — | — | Listed |
| Bolna, Ringg, Edesy, Caller.Digital, ConvoZen | Newer voice-agent startups | — | Listed |
| PolyAI, Retell, Vapi, Bland, ElevenLabs Agents | Global | — | Listed |

**Sarvam's published rate:** ₹3.50/min pay-as-you-go and ₹3.15/min on the Growth plan. Telephony may not be included, so check before comparing. Later research found other vendors publish tariffs too (Bolna, Retell), so this is not the only published rate. Compare inclusions and completed outcomes (Master Map, "Corrections to earlier research").

### 6. Doc Agents / Sarvam Vision (₹1.50 per page)
| Competitor | Status |
|---|---|
| Google Document AI / Cloud Vision, AWS Textract, Azure Document Intelligence | Hyperscalers |
| ABBYY, UiPath, Hyperscience, Rossum, Nanonets, EdgeVerve (Infosys) | From the market map; no 2026 detail found |
| HyperVerge, Signzy, IDfy (India KYC and onboarding) | No 2026 results in this pass |
| GPT and Gemini (general models) | Sarvam benchmark: olmOCR-Bench 84.3% vs Gemini 3 Pro 80.2% vs ChatGPT 69.8% (self-reported) |

### 7. Translate
Bhashini (government, National Language Translation Mission), Google Cloud Translation (100+ languages), Microsoft Translator and Reverie (11+ Indian languages). Devnagri was not found. Sarvam says it covers 22 scheduled languages, formal style and numeral control.
**What this means:** Bhashini is free or cheap and backed by the government. Translation on its own is not a wedge; it's a feature inside Voice and Docs.

### 8. Custom models ("Sarvam Train")
| Competitor | Status |
|---|---|
| **Fractal LLM Studio** (Mar 2026; NVIDIA NeMo/NIM; shown at GTC) | Confirmed (NSE filing) |
| Together, Fireworks, Databricks, NVIDIA tooling, hyperscalers, IT services firms (TCS, Infosys, Wipro, HCL) | From the market map |

**Naming fix (updated 6 Nov):** use **Custom Model Training** (sarvam.ai/products/model-training). "Epoch Builder Edition" is the developer event, not a product name, and "Sarvam Train" returns no public results. The Aug 2026 private-preview and Q4 2026 general-availability dates reported earlier are unconfirmed for this product.
Partner proof: Infosys built banking and IT small models with Sarvam on NVIDIA. This is the Finacle-style custom-model story.

### 9. Orchestration (Arya)
Launched Feb 2026. No independent comparison exists. The logical rivals are LangGraph, CrewAI, Microsoft Copilot Studio, Salesforce Agentforce, Google Agentspace, ServiceNow and Yellow.ai. **This list is my inference; no source frames Arya against them.** Proof: SBI Life runs on Samvaad plus Arya.

### 10. Cowork / enterprise agents
Microsoft Copilot, Salesforce, Google, ServiceNow, SAP, IBM, Glean and Cohere (from the market map). No new 2026 results on Sarvam Cowork were found.

### 11. Sarvam Code (beta, invite only)
- Launched at Epoch 2026: three agents (planner, worker, verifier), hosted in India.
- **Cost claim:** about $2 per solved task on Terminal-Bench 2.1, vs $4.1–27.8 for Claude Code and Codex (Inc42; company-reported).
- **Caveat:** one report says the benchmark run used Z.ai's GLM-5.2 model, not a Sarvam model.
- Competitors: Claude Code, Codex, GitHub Copilot, Cursor, Cognition, Google, AWS.

### 12. Indus (consumer chat app)
Beta on iOS, Android and web, running on 105B. It competes with ChatGPT (OpenAI reports 100M+ weekly users in India), Gemini, Claude and Perplexity. No head-to-head comparisons were found.

### 13. The newer bets
| Bet | What's public | Competitors |
|---|---|---|
| **Kaze** (smart glasses) | Unveiled at the AI Impact Summit in Feb 2026; launch "expected May 2026". **Current status unverified.** | Meta Ray-Ban, Google/Android XR, Apple |
| **Sarvam Cyber** | **Preview only, no launched product found.** Later research found an official preview centred on vulnerability investigation and remediation. Series B money is earmarked for cyber. | Application-security agents and pentesting tools are the closer comparison; CrowdStrike, Palo Alto, Microsoft, Google and SentinelOne sit in the broader market |
| **Kivi**, **Anvaya** | **Updated 6 Nov:** official pages exist. Kivi is desktop voice software (heykivi.ai), not a device. Anvaya has an official description at a different maturity. Competitors were not checked for either in this pass. | Edge/devices; Palantir and defence integrators |
| Edge plans | Nokia feature phones, cars | OEM ecosystems |

---

## Part B: the six evidence questions

| # | Question | What exists publicly | Gap |
|---|---|---|---|
| 1 | Why customers chose Sarvam, and what else they evaluated | Indian-language focus; data residency (OpenAI's API runs on US Azure); Tata Capital CDO quote (text not found) | **No source names the rivals that were evaluated.** One blog claims "94% vs 71% vs GPT-4o" for an unnamed telecom client; it's unverified, so don't use it. |
| 2 | Comparable results with defined quality and cost | OCR olmOCR 84.3%; ASR about 19.3% WER (both Sarvam). Gnani counter-claims 8 of 9 languages. Sarvam Code about $2 per task vs $4.1–27.8. | No independent benchmark. No cost-per-outcome figures, e.g. cost per resolved call. |
| 3 | Deployment time and support effort | Partner delivery (YCP India); hiring forward-deployed engineers for on-prem and air-gapped work | **No published timelines.** Gnani's "months vs weeks" claim comes from a rival. |
| 4 | Renewal, expansion and sustained use | **Mahindra Finance expanded its partnership** (GFF 2026; 1 crore+ calls across sales, collections and staff). IndiGo Ventures invested and plans pilots across the airline. IDFC FIRST joint R&D lab. | No renewal or churn data |
| 5 | Economics after all costs | API prices are public, but **the 105B price conflicts across Sarvam's own pages**: docs say ₹29.28/₹10.98/₹73.2 per 1M tokens, the marketing page says ₹4/₹2.5/₹16 (about 7× apart, changed Aug 2026). STT ₹30/hr, TTS ₹30 per 10K characters, Vision ₹1.50/page, voice ₹3.50/min. | No total-cost-of-ownership figure; enterprise prices are quote-only |
| 6 | Hosted vs dedicated vs customer infrastructure vs customer-owned models | Token Factory: shared or dedicated, zero retention on request. Self-hosted: AWS Marketplace → SageMaker in the customer's own account, billed in instance-hours. | Self-hosting appears to cover **speech and Vision only, not the LLMs**. "Customer-owned model" isn't documented publicly. |

---

## New facts that fix conflicts in our files
- **Series B:** $234M first close of a **$300M** round at a **$1.5B** post-money valuation, led by HCLTech ($150M), per the HCLTech press release. Inc42 separately reports a **$74M extension from NVIDIA and others**. $300M plus $74M is $374M and $234M plus $74M is $308M, so neither explains the $340M in the interview title. Treat it as unreconciled (ledger H007).
- **Revenue:** **₹45 crore in FY26**, per an HCLTech filing, as reported. Useful for scale and a reminder to stay modest about size.
- **Valuation signal:** Inc42 reports Cognizant is in talks to invest at **$3.5–4B**. It's a report, not a closed deal.
- **Voice volume:** the founder said about 350 million minutes of calls in 12 months (Signal Dialogues, 00:26:22). Launch coverage calls them conversations, which ledger H011 excludes. 350M is better supported than 325M, but keep the unit as minutes.

## Positioning implications (my reading; proposals, not facts)
1. **Don't claim the "best Indic speech model".** Gnani is contesting it publicly. Claim **a published price, scale and one stack from model to agent**. Do not claim "lowest": other vendors publish tariffs, and inclusions differ.
2. **The Token Factory name overlaps with Yotta's.** Position it as "Sarvam's models plus open models, with sovereign hosting", not as GPUs.
3. **E2E resells Sarvam models.** Treat E2E as a channel partner in messaging, not as an enemy.
4. **Gnani is the head-to-head rival.** It's in voice, ASR, TTS and the IndiaAI model programme, and it publishes a comparison page against Sarvam. Sarvam needs a public answer page of its own.
5. **Close the evidence gaps** (named alternatives, time to production, cost per resolved call) before any "why Sarvam" slide.

---

## Sources
- [Yotta × MarketsandMarkets press release](https://yotta.com/press-releases/yotta-and-marketsandmarkets-highlight-indias-transition-to-enterprise-scale-ai-with-sovereign-infrastructure/)
- [NVIDIA case study: Yotta Shakti Cloud](https://www.nvidia.com/de-de/case-studies/yotta-built-india-sovereign-ai-infrastructure-shakti-cloud/)
- [Yotta Shakti Studio free credits (Digital Terminal)](https://digitalterminal.in/amp/story/tech-companies/yotta-launches-10000-free-credits-program-for-shakti-studio-ai-platform)
- [E2E Networks launches Blaze (Newskart)](https://www.newskart.com/e2e-networks-launches-blaze-a-simpler-way-to-pay-for-ai-model-usage-lets-explore/)
- [Top sovereign AI cloud providers in India (CloudPe)](https://www.cloudpe.com/blog/top-sovereign-ai-cloud-providers-in-india/)
- [Krutrim pivots to AI cloud (pulse.bot)](https://www.pulse.bot/entrepreneurship/news/krutrim-pivots-to-ai-cloud-clocks-rs-300-cr-revenue-in-fy26-b62a7c83-a246-4939-9e9a-29ede3774fd7/)
- [Wait, where is Krutrim? (AIM)](https://analyticsindiamag.com/ai-features/wait-where-is-krutrim)
- [Krutrim at the AI Summit (Business Today)](https://www.businesstoday.in/technology/story/what-a-miss-olas-krutrim-fails-to-hail-a-ride-at-indias-biggest-ai-summit-517900-2026-02-25)
- [Sarvam and BharatGen models at the Summit (ETV Bharat)](https://www.etvbharat.com/en/technology/sarvam-ai-and-bharatgen-unveil-their-latest-ai-models-at-the-india-ai-impact-summit-2026-enn26022006144)
- [Sarvam 105B launch (YourStory)](https://yourstory.com/2026/02/sarvam-ai-unveils-two-new-large-language-models)
- [Benchlm: Gemini 2.5 Pro vs Sarvam 30B](https://benchlm.ai/compare/gemini-2-5-pro-vs-sarvam-30b)
- [Benchlm: Gemini 2.5 Flash vs Sarvam 30B](https://benchlm.ai/compare/gemini-2-5-flash-vs-sarvam-30b)
- [Gnani Prisma v2.5 claims better accuracy than Sarvam (Business Today)](https://businesstoday.in/technology/artificial-intelligence/story/gnani-ai-launches-prisma-v2-5-claims-better-accuracy-than-sarvam-elevenlabs-on-indian-speech-538008-2026-06-19)
- [Gnani Vachana STT](https://gnani.ai/resources/blogs/gnani-ai-launches-vachana-stt-a-foundational-indic-speech-to-text-model-trained-on-one-million-hours-under-the-indiaai-mission)
- [Gnani $10M raise (Newskart)](https://www.newskart.com/gnani-ai-raises-10-million-aavishkaar-capital-march-2026/)
- [Gnani BFSI hires (Business Today)](https://www.businesstoday.in/technology/story/gnaniai-hires-senior-executives-across-bfsi-product-and-ai-delivery-after-10-million-fundingg-530008-2026-05-06)
- [Gnani vs Sarvam (Gnani's comparison page; biased)](https://www.gnani.ai/resources/blogs/gnani-ai-vs-sarvam-ai)
- [AI4Bharat Indic Parler-TTS (AIKosh)](https://aikosh.indiaai.gov.in/home/models/details/ai4bharat_indic_parler_tts_text_to_speech_model.html)
- [Saaras v3 beats Gemini and GPT-4o on Indian speech (Business Standard)](https://business-standard.com/technology/tech-news/saaras-v3-beats-gemini-gpt-4o-on-indian-speech-benchmarks-says-sarvam-ai-126021200384_1.html)
- [Top AI voice agent platforms: India RFP shortlist (Caller.Digital)](https://caller.digital/blog/top-ai-voice-agent-platforms-enterprises-india-rfp-shortlist-2026)
- [Voice AI vendor pricing teardown, India 2026 (Caller.Digital; a rival's estimates)](https://caller.digital/blog/voice-ai-vendor-pricing-teardown-india-2026)
- [Sarvam Voice Agents pricing (docs)](https://docs.sarvam.ai/voice-agents/pricing.md)
- [Sarvam API pricing (docs)](https://docs.sarvam.ai/api/pricing.md)
- [Sarvam API pricing (marketing page)](https://sarvam.ai/api-pricing)
- [105B reprice tracker (usagepricing)](https://www.usagepricing.com/blueprint/activity/sarvam-ai-2026-08-14-105b-reprice-confirmed)
- [Sarvam Vision launch (Business Today)](https://www.businesstoday.in/technology/news/story/sarvam-ai-unveils-sarvam-vision-a-multilingual-document-intelligence-model-514873-2026-02-05)
- [Sarvam Vision 2.1 review (Analytics Vidhya)](https://www.analyticsvidhya.com/blog/2026/09/sarvam-vision-2-1-review/)
- [Sarvam Translate docs](https://docs.sarvam.ai/api-reference-docs/text-preprocessing/api/overview)
- [Bhashini vs Google Cloud Translation (Slashdot)](https://slashdot.org/software/comparison/BHASHINI-vs-Google-Cloud-Translation-API/)
- [Reverie docs](https://docs.reverieinc.com/introduction.md)
- [Fractal LLM Studio (NSE filing)](https://nsearchives.nseindia.com/corporate/FRACTAL_17032026124122_PR_NVIDIA.pdf)
- [Sarvam fine-tuning platform (Swarajya)](https://swarajyamag.com/amp/story/news-brief%2Fsarvam-ai-rolls-out-platform-to-build-fine-tune-llms-for-indian-use-cases)
- [Sarvam launches Arya (Business Today)](https://www.businesstoday.in/technology/story/sarvam-launches-arya-to-make-ai-agents-production-ready-in-indias-sovereign-ai-push-515400-2026-02-10)
- [Sarvam opens Samvaad to the public (Inc42)](https://inc42.com/buzz/exclusive-sarvam-ai-to-open-voice-ai-agents-platform-for-public-use/)
- [Samvaad opened to developers after 350M conversations (AlphaSignal)](https://alphasignal.ai/news/sarvam-ai-opens-samvaad-to-developers-after-350m-real-conversations)
- [Sarvam Code vs Claude and Codex (Inc42)](https://inc42.com/buzz/sarvam-takes-on-claude-codex-with-cheaper-india-hosted-coding-agent/)
- [Indus chat app (TechCrunch)](https://techcrunch.com/2026/02/20/indias-sarvam-launches-indus-ai-chat-app-as-competition-heats-up/)
- [Kaze smart glasses (Digit)](https://www.digit.in/news/general/india-ai-impact-summit-2026-sarvam-ai-unveils-kaze-smartglasses-pm-modi-tries-on-a-made-in-india-ai-wearable.html/amp/)
- [HCLTech: Sarvam raises $234M at a $1.5B valuation](https://hcltech.com/press-releases/sarvam-raises-234-million-first-close-300-million-series-b-15-billion-valuation)
- [Series B extension from NVIDIA (Inc42)](https://inc42.com/buzz/sarvam-to-raise-74-mn-in-series-b-extension-from-nvidia-others/)
- [Cognizant talks at $3.5–4B (Inc42)](https://inc42.com/buzz/cognizant-in-talks-to-invest-in-sarvam-at-3-5-bn-to-4-bn-valuation-report/)
- [Sarvam unicorn round (Inc42)](https://inc42.com/buzz/sarvam-becomes-indias-130th-unicorn-after-raising-234-mn/)
- [SBI Life partnership (Business Today)](https://www.businesstoday.in/technology/story/sarvam-partners-with-sbi-life-to-deploy-ai-tools-for-customer-engagement-sales-518227-2026-02-26)
- [Mahindra Finance story (Sarvam)](https://www.sarvam.ai/stories/mahindra-finance-voice-agents)
- [IndiGo Ventures investment (YourStory)](https://yourstory.com/ai-story/indigo-ventures-to-invest-in-sarvam-to-boost-ai-use-in-aviation)
- [YCP partnership (Sarvam)](https://www.sarvam.ai/partnerships/ycp)
- [Managed vs self-hosted (Sarvam docs)](https://docs.sarvam.ai/api/self-hosted/hosted-vs-self-hosted)
- [Token Factory (Sarvam)](https://www.sarvam.ai/token-factory)

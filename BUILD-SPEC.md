# Build spec: Sarvam website agent (15 Nov 2026)

Written for: the project owner and any reviewer who runs the build.
Status: PROPOSED. Sign-off by the owner starts stage S1. New ideas go on the "Later" list. They do not change this spec.

## 1. What we build

One command audits the hero of a Sarvam page, writes a better hero only if the audit finds a gap, shows a person the baseline and the variant side by side, tests the approved variant in a sandbox with browser bots, and writes the findings.

- **Scope:** the hero only: H1, sub-line and main CTA. Desktop width only.
- **First page:** Token Factory. **Second page:** one more page, chosen after S6.
- **Local first.** Order of work: local run, then GitHub, then Supabase, then Vercel. Deployment is not in this build.
- **Sources:** both old folders (`sarvam-positioning-agent`, `sarvam-submission`) stay read-only. This folder is the build.

## 2. Three layers

| Layer | Folder | Rule |
|---|---|---|
| A. Engine | `agent/` | Generic code. No page name anywhere. |
| B. Policy | `rules/`, `skills/`, `schemas/` | Shared by every page. |
| C. Page pack | `pages/<slug>/` | Data only: evidence, claims, do-not-claim, buyer checklist, positioning, capture. |

A new page is a new folder in layer C. `python3 agent/new_page.py` makes it. `python3 agent/check_page_readiness.py --page <slug>` says what is missing. A page with thin evidence stops at that check.

## 3. Models and endpoints (checked 15 Nov 2026)

All calls use the one `OPENROUTER_API_KEY` in `.env`. `.env` holds only that variable.

| Role | Model | Endpoint | Returns |
|---|---|---|---|
| Judge 1: Jev | `typesafe/jev-1.14` | `POST openrouter.ai/api/alpha/decisions` | Typed answers with probabilities. No text, no reasons. |
| Judge 2 | `openai/gpt-6-luna-decisions` | Same endpoint | Same shape. A different maker from the writer and from Jev. |
| Writer and explainer | `anthropic/claude-sonnet-5.5` (owner choice, 15 Nov 2026, row 31) | `POST openrouter.ai/api/v1/chat/completions` | Text |

What this changes:
- **Jev is not an LLM.** It cannot explain itself. Our earlier "Jev" runs used `typesafe/jev-router` through chat completions. Those answers had reasons and were routed to DeepSeek, Kimi and GPT-6 Luna. That was an LLM router, not typed Jev. This build uses the Decisions API.
- **A judge cannot cite an id.** The code does it: for each claim id a line relies on, the code puts that claim's evidence in the judge's input and asks a yes/no question. The id is the code's, not the judge's.
- **Thresholds are per model.** Probabilities differ between models on the same question. `--calibrate` runs the test cases and sets one threshold for each model.
- **Explanations come from the writer model.** A judge hold is shown to the person with a short explanation written by the writer model, labelled as an explanation.
- **Three makers, no conflict.** Writer: Anthropic Sonnet. Jev: TypeSafe. Judge 2: OpenAI. The ids `anthropic/claude-sonnet-5.5`, `typesafe/jev-1.14` and `openai/gpt-6-luna-decisions` were found in OpenRouter's public model lists on 15 Nov 2026.
- **Config, not code.** Roles are set in `agent/models.json`. `MODEL_WRITER`, `MODEL_JUDGE1` and `MODEL_JUDGE2` override them. The GitHub repo ships no `.env`. A user copies `.env.example` to `.env` and adds `OPENROUTER_API_KEY`. On Vercel the same variable is set in the project settings.
- **Where each model is used and what it reads** is in `docs/architecture.md`, section 2.
- **Cost:** judge input costs about $0.10 per million tokens. Output is free.

## 3b. What the report must say about the judges (owner decision, 15 Nov 2026)

The gap dossier (step 5) and the findings report (step 12) must show how the audit was done, so a reader can judge whether it is credible. Each of them carries an **Audit method** section with:

1. **Every question asked,** by id, in the exact words from `rules/judge-questions.json`.
2. **The judge and model id** that answered each question, and the date.
3. **The probability** each answer returned, the **threshold** used for that judge and question, and whether it passed, held or failed.
4. **The calibration table:** the good and bad examples shown to each judge, where their numbers landed, and where the pass line was drawn. For each judge it lists the examples that sat on the wrong side of the line.
5. **The limits,** in plain words. The report must include this statement, or one with the same meaning:

> Jev and Judge 2 are general decision models. We did not train or fine-tune either one on labelled examples of right and wrong for this program. We set the pass lines ourselves, from a small set of examples that we wrote. The probabilities are therefore an audit signal and not an assurance. The owner accepted these pass lines as the working standard for approval on 15 Nov 2026. A person makes every approval.

This is the owner's accepted standard for the build. It is not a claim that the judges are proven reliable.

## 4. The run (12 steps)

The diagrams are in `docs/architecture.md` and `docs/architecture.html`. Both come from `docs/build_architecture.py`. `new` = to be written. `copy` = copied from the old folders. `adapt` = copied, then changed.

| # | Step | Who | Module |
|---|---|---|---|
| 1 | Start: page, buyer, goal, test type (message or CTA) | Person | new `run.py` (reads choices from the page folder) |
| 2 | Capture the page once. Keep hero text and a desktop hero screenshot. | Rules | adapt `capture.py`; hero selectors live in `profile.json` |
| 3 | Positioning: load the saved one, or draft with `seven-page-positioning`. A person confirms a draft. | LLM, rules, person | copy skills, `proofcheck.py` |
| 4 | Audit the hero with Jev against the buyer checklist and the positioning | Jev | new `decisions.py`, `audit.py` |
| 5 | Gap dossier: written in full, not a JSON stub | LLM from the audit data | new `dossier.py` |
| 6 | Lock the test plan and hash it | Rules | `plan_hash.py`, new `testplan.py` |
| 7 | Writer drafts 1 to 2 variants. Each line lists the claim ids it uses. | LLM | `model_adapter.py`, skills |
| 8 | Gate 1 rules, then Gate 2 Jev plus Judge 2. Two rounds at most. | Rules, Jev, Judge 2 | `proofcheck.py`, `check_claims.py`, `check_brand.py`, `decisions.py` |
| 9 | Apply the words to the captured page (text swap). Screenshot each arm. Check the CTA flow. | Rules | new `swap.py`, `flowcheck.py` |
| 10 | Human approval: PNGs side by side, word diff, dossier, locked plan. Approve, reject or revise. | Person | new `approve.py` (small local server) |
| 11 | Sandbox: Playwright bots with personas on baseline and the approved variant. Two scenarios. | Rules | adapt `sandbox.py` stats; new `bots.py` |
| 12 | Findings, tick list, README, architecture note, Jev note. Code builds numbers, tables, ticks and the limits statement. The writer LLM drafts the prose. Rules verify it. | Rules, writer LLM | new `findings.py`, `prosecheck.py` |

Not in the build: the 21-step engine, `flow.json`, the library guard chain, option-B positioning, structure tests, mobile view, any hosted version.

## 4b. Live-site rule (15 Nov 2026)

The live sarvam.ai page is loaded only to capture it and to take the PNG pair. Bots, the sandbox and the functional check run against the saved local snapshot. Outbound navigation is intercepted: the click target is recorded, then the request is aborted. No synthetic visitor ever reaches sarvam.ai. Synthetic traffic on a production site would load it and pollute Sarvam's own analytics.

## 5. Acceptance tests

Written first. A stage is done when its tests pass. Run them with `python3 -I agent/run_tests.py`.

| ID | Test | Stage |
|---|---|---|
| T1 | `python3 agent/run.py --page token-factory` reaches approval, waits for the click, and finishes after approve | S5 |
| T2 | After reject, the rejected arm has zero exposure events | S5 |
| T3 | After revise, the hash changes and a new approval is needed | S5 |
| T4 | Planted bad hero lines are blocked by code even if a judge says yes: a fake claim id, a quote not in the source, a banned word | S4 |
| T5 | A line with a new number or a new comparison is blocked by Gate 1 | S4 |
| T6 | Both judges run on the 12 test cases. A threshold is set for each model. The result is saved. | S4 |
| T7 | Judge disagreement or refusal holds the variant | S4 |
| T8 | A hero with no gap stops the run. The writer is never called. | S3 |
| T9 | The dossier has all nine parts plus the Audit method section. It appears on the approval page and as section 1 of the report. | S3, S6 |
| T21 | `COVERAGE.md` is built from the run folder. Deleting a proof file turns its tick into a cross. | S6 |
| T22 | LLM prose in the dossier and submission files is checked: a planted wrong number, id, model name or file name is rejected | S6 |
| T20 | The findings report lists every judge question with its probability, threshold and result, the calibration table, and the limits statement from section 3b | S6 |
| T10 | The test plan is locked before the writer runs. Changing it voids the run. | S3 |
| T11 | The approved PNG pair and the page the bots load use the same text. The hash covers both. | S5 |
| T12 | Each visitor gets the same arm on every visit. Events are logged per visitor with time, arm and persona. | S6 |
| T13 | Both scenarios run. The report shows rates and confidence intervals. Every sandbox line says SYNTHETIC. | S6 |
| T14 | A baseline-against-baseline run does not produce a winner at the locked significance level | S6 |
| T15 | The report text changes when the data changes | S6 |
| T16 | The functional check clicks the CTA in each arm and records where it goes | S5 |
| T17 | `new_page.py` plus the readiness check stop a page with thin evidence | S7 |
| T18 | No page name appears in `agent/` | S1 |
| T19 | `.env` is never printed, logged or committed | S1 |

## 6. Stages

Each stage ends with its tests passing and a local git commit. The one command works after every stage.

| Stage | Work | Exit |
|---|---|---|
| S0 | Scaffold: folder, curated copy, `.env`. **Done 15 Nov.** 17 copied modules import clean. Readiness check shows 0 missing. | Done |
| S1 | `decisions.py` client for both judges. `model_adapter` call for the writer. Smoke test: one call each. Confirm model ids. T18, T19. | 3 live calls logged with the model that answered |
| S2 | Hero capture, hero selectors in `profile.json`, desktop hero screenshot, offline snapshot | Hero text and PNG saved for Token Factory |
| S3 | Positioning step, Jev audit, gap rule, dossier, locked plan. T8, T9, T10. | A run stops cleanly at "no gap", or writes a dossier |
| S4 | Writer, Gate 1, Gate 2, `--calibrate`, thresholds. T4 to T7. | Planted bad lines blocked |
| S5 | Text swap, PNG pair, approval page, reject and revise, flow check. T1 to T3, T11, T16. | Run waits for the click |
| S6 | Bots, sandbox, A/A test, findings, README, architecture note, Jev note. T12 to T15. | Full run completes |
| S7 | Second page: `new_page.py`, research pass, full run. T17. | Second page completes |

After S6, the owner runs the folder through ChatGPT. Corrections follow. Then the order is: GitHub repo, Supabase, Vercel.

## 7. Second page protocol

1. Run `new_page.py --page <slug> --url <url>`. It copies the template. It never guesses buyer, goal or CTA.
2. A person fills the profile: buyer, goal, main CTA.
3. A research pass fills the pack: capture the page, draft evidence notes from the page text (label VENDOR, source = the page), and add a buyer checklist. Anything that is not on the page needs a person to add a checked note.
4. The readiness check must show 0 missing. Then the same command runs.

## 7b. Submission files (owner decision, 15 Nov 2026)

`README.md`, `ARCHITECTURE.md`, `JEV-NOTE.md`, `GAP-SYNTHESIS.md`, `FINDINGS.md`, `COVERAGE.md` and the run folder. The writer LLM drafts the long prose for all but `COVERAGE.md`, from the full run record, so the files are thorough and well reasoned. `prosecheck.py` rejects any number, id, model name or file name that is not in the run record. Code inserts tables, the tick list and the limits statement word for word. `COVERAGE.md` ticks every assignment line from the run's own files and uses no LLM.

## 8. Later (not in this build)

- GitHub repo for this folder, then Supabase for the documents and run state, then Vercel.
- Mobile view. Structure tests. Multi-arm tests.
- A fresh crawl of 7 or 8 pages with thin packs.
- A rival-ads agent.

## 9. Open items

- Writer model id: confirm `deepseek/deepseek-v4-pro` exists on OpenRouter at S1.
- Hero scope: H1, sub-line and main CTA. Confirm.
- Second page: not chosen.
- The old `models.json` still names `typesafe/jev-router`. S1 replaces it.

## 10. Status log

**15 Nov 2026, S1 done.** `agent/llm.py` (writer chat client and judge Decisions client), `agent/smoke.py`, models set in `agent/models.json` under `roles`. Live smoke test passed: all three roles answered, about $0.0004 in total. Real reply shapes: the Decisions API returns `{"answers": {name: {"type": "noul", "noul": 0.96}}, "usage": {...}}`. The probability sits in the `noul` field. The model that answers carries a date suffix (`typesafe/jev-1.14-20261014`), so the run log records the answered id.

**15 Nov 2026, probe (not the engine).** `agent/probe.py` ran steps 4, 7 and 8 once on the Token Factory hero. Cost about $0.03 over four runs. Findings that changed the design:
1. G1 and G2 now ask about one fragment and its claim, not the whole hero. The writer returns a claim map. (A whole-hero question gave low support and high overreach for any multi-claim line.)
2. The writer gets the gap in words, never question ids or probabilities. Improvement is reported on targeted and held-out questions separately.
3. `agent/gate1.py` has new rules: absolute words, kept qualifiers, per-claim qualifiers from `profile.json`, every sentence mapped to a claim, no new number. Self-test 10 of 10. Two real overreaches in the first run ("never leave the country", the SLA without "agreed by contract") would now be blocked.
4. G4 (distinct) dropped. It contradicted A6.
5. Page details moved into `profile.json` (`hero` block).
6. The writer sometimes returns broken JSON. The probe now asks for a repair, up to 3 tries.
7. Open: Jev is much stricter than Judge 2 on support (for example 0.14 to 0.28 on exact quotes). Pass lines must be set per judge in S4.
8. Open: baseline CTA is "Get Started". Variants use "Compare on your workload". Default: both arms carry the locked CTA, so the test stays a message test.

**15 Nov 2026, evening: live run (probe v3).** Row 28: the baseline keeps its live button, and the writer generates the variant button for a real destination (console, models, contact, pricing, docs). Done:
- `capture_hero.py`: live capture, hero identical to 14 Nov.
- `skills/step-skills.json` and `agent/skills.py`: a draft pass and an edit pass, each skill logged with its checksum.
- `calibrate.py`: 26 cases, 3 held out, $0.0014. Pass lines are now bands: fail below, pass above, hold between.
- `probe3.py`: audit, dossier, writer, Gate 1, Gate 2, then PNG pairs.

Final run: 41 calls, $0.0100. Results:
- Audit: CTA fails. Audience, value and proof sit in the hold band. The worst-answered buyer question is "Does the page say the API is OpenAI-compatible".
- Variant C ("One API key, multiple open models, inference on GPUs in India." / price line / "Compare pricing") passes Gate 1 and Gate 2. Both judges rate it better than the baseline on CTA, proof and the price question, with no held-out drop.
- Variant A addressed the OpenAI question but carried two stretches that Gate 1 missed: "your existing code works" and "requests are not forwarded overseas". Only Jev flagged them, and Jev's overreach answers are advisory.

Calibration facts:
- Neither judge separates claim support. Judge 2's overreach and banned questions are advisory.
- Audit questions separate cleanly, but on 2 cases each, so the bands are wide.

Next fixes:
1. Turn each claim's "Do not stretch it" note into Gate 1 data: stretch phrases such as drop-in, "existing code works" and "no changes", plus keep-words such as "original model" for CL-002.
2. The dossier must quote the checklist item exactly. It invented "drop-in replacement".
3. Hide the cookie banner in the PNGs.
4. Add more calibration cases, at least 5 per question.
5. Build the approval page, bots on the local snapshot, and findings (S5, S6).

### 15 Nov 2026, evening: live run with the Sonnet writer (runs/probe3-20261115-183113, 42 calls, $0.19)
Fixes 1 to 4 above are done. The writer is `anthropic/claude-sonnet-5.5`; Judge 2 stays `openai/gpt-6-luna-decisions`. Calibration now uses 40 cases with bands.

Audit of the live hero (Jev): button fails (0.14); value and proof are held; audience passes. The buyer question answered worst is "Does the page say the API is OpenAI-compatible".

Variants (all passed Gate 1 on the first round; no third-party model names; no stretch phrases):
- A: "Open models on an OpenAI-compatible API, served from India" + the FAQ's migration steps word for word (EV-008) + "Read the API guide" (docs). Passes Gate 2 and is better than the baseline for both judges. The only variant that goes forward.
- B: where inference runs + zero data retention + ISO/SOC 2 + "Discuss your requirements" (contact). Better for both judges, but Jev's banned-phrase answer fails, so it is not passed. The judges disagree.
- C: one key across the catalogue + SLA + "Explore models". Not better: it loses the audience and "where inference runs" answers.

Dossier: the prose check found no problems. Fixed after the run: (1) the audit table showed a flat 0.50 "pass line"; it now shows each question's calibrated band (this run's file was re-generated from the saved results); (2) the hypothesis named "Get Started", which the variant replaces; the prompt now says "the hero's main button". This run's hypothesis sentence still says "Get Started".

Observed but not fixed: on the live page, "Explore models" is the dark (visually stronger) button and "Get Started" is the light one. We treat "Get Started" as the main button (profile.json); a person should confirm that choice.

Next: S5 approval page, then S6 bots on the local snapshot and findings. Not started; waiting for the owner.

### 15 Nov 2026, night: page-aware judge questions and the local console
Questions (rules/judge-questions.json note_v3):
- Universal: A1 to A6 plus the new A8-objection. The wording is the same on every page. The page reaches the judge through the state (buyer, positioning promise, rival heroes) and through the fill text.
- Page questions: A7 (one per buyer checklist item) and the A8 objection come from the page pack's checklist. Each item carries a tag: [hero] or [page]. Only [hero] items go to the hero audit. [page] items appear in the dossier as "out of hero scope". The fine-tuned weights question is [page].
- A7 and A8 run only after a person fills questions_approved_by and questions_approved_on in the checklist front matter. Until then the audit skips them and says so.
- Calibration: 60 cases. A7 now has its own 10 cases and no longer borrows the A2 band. A8 has 10 cases. Both separate on both judges. Jev's A8 band is narrow (fail at 0.37 or below, pass at 0.44 or above). Cost $0.003.
- Each run now saves the bands it used (probe3.json thresholds_used).

Console (app/server.py + app/index.html; start with ./run-ui.sh):
- Standard library only, bound to 127.0.0.1.
- Shows the 12 architecture steps per run, with calls, cost and models from run-log.jsonl. Steps 6, 10, 11 and 12 are shown greyed as "not built".
- Tabs: audit, gap dossier, variants (gates and PNG pairs), judge questions and run log.
- "Start a run" spawns a fresh probe3 process, one at a time. Code edits apply on the next run.
- Security, tested: file reads are allow-listed and .env is never served; path traversal, a foreign Host, a foreign Origin and a POST without the console header are refused.
- `--export <dir>` writes a read-only static copy for a later Vercel deploy. Not deployed.
- No approval button. Step 10 waits for the owner's go.

Demo run started from the console (runs/probe3-20261115-184616, 45 calls, $0.25). Page questions were not approved, so A7 and A8 were skipped. Gaps found: button, audience, value and proof. No variant passed. Variant A (OpenAI-compatible API plus "requests do not go to the original model maker's overseas API") was better for both judges, but Jev's banned-phrase answer failed it. The do-not-claim list has no matching item; the closest is "sovereign cloud". This is likely a Jev false positive on an allowed claim (CL-002), the same pattern as variant B in the 18:31 run. Open question for the owner: should a Jev banned-phrase fail with no matching rule block a variant, or hold it for a person?

### 15 Nov 2026, late night: approval groups, human approval and the sandbox (Decisions Log rows 32 to 35)
- agent/shortlist.py groups variants as passed, held, failed Gate 2 or failed Gate 1. The reasons are built by code and name the cause, for example "other questions dropped more than 0.05: A5-positioning -0.21". A6 is a lower-is-better question; its sign is flipped, so a rise in "a rival could copy it" counts as a drop. The self-test reproduces the expected groups on the 18:31 and 18:46 runs. probe3 now saves the groups in probe3.json.
- Console tab "Approve and test":
  - Passed and held variants are shown open; Gate 2 failures are folded; Gate 1 failures appear as a count only.
  - Approve, Reject and Revise are enforced on the server: a name is required; a non-passed variant needs a reason of 10 characters or more; Gate 1 failures are refused; a PNG pair is required to approve.
  - approval.json is append-only and stores the variant and PNG hashes.
  - Tested on a throwaway copy of a run, which was then deleted. No real run folder holds an approval.
- agent/sandbox_hero.py (step 11, no model calls):
  - It refuses to run without an "approve" entry whose hashes still match.
  - Simulated rates come from the seeded simulation, with lifts declared in agent/sandbox_hero.json: clear at 8,000 visitors per arm, inconclusive at 800, and an A/A check. The run reports Wilson intervals, the difference with its interval, and the z test.
  - It then runs 20 Playwright sessions per arm on the local copy, with the <base> tag removed and every non-file request aborted. 1,397 outside requests were blocked in the test.
  - It writes sandbox/events.jsonl, sandbox-results.json and FINDINGS.md, all labelled SYNTHETIC.
  - Test result: clear p<0.0001; inconclusive p=0.81; A/A p=0.91; 40 of 40 browser sessions passed.
- The owner's own console run at 18:56 (probe3-20261115-185617, $0.24): A held (Jev banned-phrase flag), B held (judges disagree), C failed Gate 2.
- Still open: COVERAGE.md (tick list), the LLM-drafted submission files (README, ARCHITECTURE, JEV-NOTE), the revise note feeding the writer, and step 6 (lock the test plan).
- Fixes after the advisor's review:
  - The approval that counts is now per variant (shortlist.current_approval). Rejecting another variant no longer withdraws it; a reject or revise on the same variant does; a new approve replaces it. There are 5 self-test cases for this.
  - The Variants tab, pipeline step 8 and probe3's printout now all use the same groups as the Approve tab. Checked in the browser on 4 runs.
  - Revise notes are recorded only; the next run does not read them yet.
  - The static export writes "a person" in place of approver names.

### 15 Nov 2026, night: four model roles (Decisions Log row 36)
- models.json roles: reasoning = anthropic/claude-sonnet-5.5, writer = google/gemini-3.8-flash, judge1 = typesafe/jev-1.14, judge2 = openai/gpt-6-luna-decisions. llm.roles() also reads MODEL_REASONING.
- probe3: the gap dossier (and its fix rounds) now calls the reasoning role. The variant draft, edit and Gate 1 fix calls stay on the writer role.
- The smoke test covers all four roles and passed. Gemini's 60-token test reply was cut short, because it thinks before answering; the writer calls allow 3,000 tokens. Check the first real run for empty or cut-off replies.
- Architecture v6 rebuilt (new reasoning colour; steps 3, 5 and 12 are reasoning; step 7 is the writer).
- Next: a page list with Semrush traffic as a column only; local hero captures for the product pages; header dropdowns for page, persona (industry then role) and goal; one new page pack (Voice Agents), approved by a person; one run.
- Page register (pages/registry.json, agent/pages_registry.py): 13 pages from the site navigation and the market map, with Semrush India traffic as a column only. Organic search: homepage 37,997 a month, Text to Speech API 1,593, Coding Agents 1,177; Token Factory, Voice Agents and Document AI are not in the top 40 non-translation pages. 12 new folders, each holding profile.json only.
- Captures: each hero was loaded once on 15 Nov 2026 (hero.json, hero PNG, snapshot.html). capture_hero falls back to the load event when a page never goes network-quiet (Voice Agents has a live demo). All 13 heroes were checked on a contact sheet: right H1, sub-line and main button on every page.
- Console: the page dropdown follows the register. A page without a page pack shows its saved hero and status, and "Start a run" is disabled; the server also refuses with 409.
- Next: header dropdowns for persona (industry, then role, filtered by fit) and goal (5 fixed goals tied to destinations); remove the hard-coded Token Factory values; the Voice Agents page pack (Sonnet drafts claims with exact quotes, code checks them word for word, a person approves); one run.

### 15 Nov 2026, night: run flow for any page, persona and goal
- library/personas.json (agent/build_personas.py): 8 industries and 60 buyer roles from icp-round-2, with the GTM map fit status per product. The persona dropdown is ordered by fit for the page's product (registry map_product).
- rules/goals.json: 5 fixed goals, each tied to a destination kind (console, contact, pricing, docs, explore). agent/destinations.py finds real links of each kind on the saved page; a goal without a link is greyed out. The goal sets the variant's button destination.
- agent/page_setup.py, the "Page setup" tab:
  - The positioning is loaded if saved, otherwise drafted by the reasoning model with the positioning skills.
  - Claims are drafted with exact quotes, and code drops any quote not found word for word in the saved page text.
  - One buyer checklist per persona, tagged [hero] or [page]; the main objection must be copied word for word from the research row.
  - Each part is approved or rejected in the console (name required; a reject needs a note). Approval is by file hash, so an edit after approval shows "changed after approval".
  - A run needs positioning and claims approved; the checklist turns on A7 and A8.
- probe3 now takes --page --persona --goal. No Token Factory values remain in the run path:
  - the buyer comes from the persona;
  - the do-not-claim list and hero policy fall back to rules/;
  - A6 is skipped when a page has no rival heroes;
  - the PNG sheet shows the page name, buyer, goal and capture date;
  - the PNG load falls back to the load event.
- The sandbox finds the real main button index. llm.chat retries when a reply is cut off (finish_reason length), not only when it is empty; both calls are charged and logged.
- The writer brief has a new rule 9, "write fresh copy; claims are facts, not copy". Before this rule, Gemini pasted claim sentences as headlines.
- End-to-end test on a throwaway copy of Voice Agents (bfsi business owner, start-building), deleted afterwards. No approvals exist on real pages.
  - Audit: proof fails, button fails, value held.
  - All 3 variants passed Gate 1 and gained +0.34 to +0.48 on the targeted gaps, but every one dropped A5-positioning and so fell into "failed Gate 2" (still selectable with a reason). $0.19.
- Open for the owner: A5 has no calibrated band (advisory), yet its drop vetoes "better than baseline". Should an advisory question be able to veto? It is not changed.
- Token Factory now also needs its positioning and claims approved in the console before a new run.
- Fix after the advisor's review: the A5 drop came from the positioning draft. The drafted Voice Agents promise was the live sub-line word for word (100% word overlap), so the baseline won A5 by construction. draft_positioning now rejects a promise whose content words overlap the live H1 and sub-line by more than 60%, and redrafts. Voice Agents was redrafted; the Token Factory promise overlaps 23%. The advisory-veto question is withdrawn until a run with a real promise shows A5 still dropping.
- Zero-cost load test, on throwaway copies with fixture approvals, deleted afterwards:
  - Token Factory (gcc technical evaluator, explore): A1 to A8 are asked, including 4 hero checklist items and A8; keep_rules and qualifiers reach cfg; 6 rivals.
  - Voice Agents (bfsi business owner, start-building): A6 is skipped (no rivals); A7 has 1 item; A8 is asked; the destination is the console.

### 15 Nov 2026, late: owner feedback round (Decisions Log row 38)
- Models: reasoning = google/gemini-3.8-flash; writer = anthropic/claude-opus-5.5. Judges unchanged. The smoke test passed (the test reply now has 800 tokens, because Gemini thinks first). Architecture v7 rebuilt.
- Console:
  - A "Next step N of 5" guide on every tab. With a saved run open, it shows that run's next step (approve a variant, run the sandbox); otherwise it shows the setup or run step.
  - A "How it was scored" table on each variant in Approve and test: both judges' live, variant and change for every question, the banned-phrase check, and better-than-baseline per judge.
  - A new "Sandbox and findings" tab that says why it is empty (no variant approved) or shows the results.
  - The Judge questions tab points to Page setup instead of the old file edit. "Required" is renamed "Must pass?", with "no (advisory)".
  - Clearer labels for the name box and the draft button.

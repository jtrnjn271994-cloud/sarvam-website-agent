# Sarvam website agent

Written for: a reviewer who has not seen this project and wants to look at it or run it.

This agent audits the top section of a Sarvam web page. That section is the hero: the headline (H1), one sub-line and the main button. For one buyer and one goal it finds what the hero fails to say. It writes three better heroes, checks them with rules and two judge models, and stops for a person to approve one. It then tests the approved hero in a sandbox and writes the findings.

A model drafts. Code checks. A person approves. Every fact comes from a quote on the saved page or a checked row in `knowledge/`.

## Two ways to see it

| | What you get | What you need |
|---|---|---|
| **A. The website** | Every finished run, audit, variant, judge score, finding and the architecture. Read only. | A browser. Open **https://sarvam-website-agent.vercel.app** |
| **B. This repo, in a terminal** | The full agent. You can start runs, approve variants and run the sandbox on your own machine. | Python 3.9+, and an OpenRouter key for runs that call models |

The website cannot start a run. A run needs a browser engine and a long-running process, and the website is a static copy. Option B is how you run the agent.

## Run it from the terminal

```
git clone https://github.com/jtrnjn271994-cloud/sarvam-website-agent.git
cd sarvam-website-agent
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 -m playwright install chromium
cp .env.example .env                 # then open .env and add OPENROUTER_API_KEY
./run-ui.sh                          # Windows: python3 app/server.py
```

Open http://127.0.0.1:8765.

1. **Pick** a page, an industry and a buyer. The goal list changes with the buyer. The first goal is the suggestion.
2. **Page setup** (once per page). Read the positioning and the claims. Click Approve on each. The buyer checklist is optional and adds two buyer questions.
3. **Start a run.** It takes about 3 minutes and costs about $0.25 to $0.50. A cap of $1.00 per run stops overspend.
4. **Read the Audit and Variants tabs.** Each variant shows both judges' scores.
5. **Approve one variant** in Approve and test. You may pick a variant that failed Gate 2 if you type a reason. A variant that failed Gate 1 (the rules) cannot be picked.
6. **Run the sandbox.** Open Sandbox and findings. The Submission and docs tab shows this README, the architecture and the Jev note.

You can browse every saved run without a key. You need the key only to start a run or draft a page setup.

### The same steps without the UI

```
python3 agent/pages_registry.py --capture --page coding-agents        # save the live hero once (the only call to sarvam.ai)
python3 agent/page_setup.py --page coding-agents --persona gcc:technical-evaluator   # draft claims, positioning and checklist
python3 agent/probe3.py --page coding-agents --persona gcc:technical-evaluator --goal read-docs   # one run
python3 agent/sandbox_hero.py --page coding-agents --run probe3-YYYYMMDD-HHMMSS   # sandbox, after a variant is approved
```

Approvals are written only when a person clicks Approve in the console. The command line never approves. A sandbox command refuses to run until a variant is approved.

### Checks

```
python3 -I agent/shortlist.py --selftest
python3 -I agent/gate1.py --selftest
python3 -I agent/sandbox_hero.py --selftest
```

## Use a different model

The agent is model agnostic. Four roles live in `agent/models.json`: reasoning, writer, judge 1 and judge 2. Change one in `.env`:

```
MODEL_REASONING=google/gemini-3.8-flash
MODEL_WRITER=anthropic/claude-opus-5.5
```

Any OpenRouter model id works for the reasoning and writer roles. The two judge roles use OpenRouter's decisions endpoint, which today accepts only Jev and OpenAI's decision model. Models never see anything outside the saved page and `knowledge/`.

## The knowledge base

`knowledge/` is a fixed, versioned snapshot of the checked research: price ledgers, buyer research, rival cases and proof rows. Every row has a verification status. Rows that failed a check are not in it. Contact records, named people and full transcripts are not in it.

- The agent cites a row as `KB:<id>`. Code checks that the id exists and that every number written next to it is in that row.
- Every run records the knowledge version it used (`knowledge_version` in `probe3.json`).
- `scripts/import_knowledge.py` rebuilds it from the research folder. You do not need to run it. Point `KNOWLEDGE_DIR` at your own copy to use other research.

## Rules the agent follows

- Rules live in `rules/`. Positioning follows `rules/positioning-structure.json`: 12 sections, every bullet sourced and labelled.
- Page facts come from `pages/<page>/claims`, each tied to a quote found word for word on the saved page.
- Never claim what `rules/do-not-claim.md` bans. Never name a third-party model in hero copy.
- No bot traffic goes to sarvam.ai. The sandbox blocks every outside request.

## What the sandbox shows, and what it does not

The sandbox is synthetic. The visitor groups, their reactions and the lift are built for each run from the buyer, the goal and the judge scores. Only the base click rate and a few weights are typed assumptions (`agent/sandbox_hero.json`).

- Test 1 uses the lift we expect and the largest sample the sandbox allows.
- Test 2 uses the same lift with too few visitors and should say inconclusive.
- Test 3 is the page against itself and must say inconclusive.

These check the measuring method. They do not say that a variant wins, because the lift is an input. `FINDINGS.md` states how many real visitors a real test needs. A real result needs live traffic.

## Folder map

| Path | What it holds |
|---|---|
| `agent/` | The logic: one script per step, `models.json` for model roles |
| `app/` | The console (`server.py`, `index.html`) |
| `knowledge/` | The fixed research snapshot, `manifest.json`, `index.json`, `VERSION` |
| `pages/<page>/` | Saved hero, claims, evidence, setup approvals and every run |
| `rules/` | Goals, thresholds, hero policy, positioning structure, banned claims |
| `skills/` | Skill files the models read before writing |
| `library/` | Buyer personas by industry |
| `scripts/` | `import_knowledge.py`, `deploy_static.sh` |
| `docs/` | `architecture.md` and `architecture.html` |
| `submission/` | The Jev note |
| `tests/` | Judge calibration cases |

Read `docs/architecture.html` for the whole flow, the three layers, deployment, and the tools and models used.

## Known limits

- The hero only, on desktop. No page body, no mobile view.
- Judge scores are an audit signal, not proof. The calibration set is small and written by us.
- Persona and goal suggestions are analyst proposals, not buyer research.
- One job at a time, on one machine. There is no login.
- Saved pages are dated. Capture again before a new run if a page changed.

## Publish the read-only site yourself

```
./scripts/deploy_static.sh
```

This writes a static copy to `dist/` (finished runs only, approver names replaced with "a person") and deploys it with the Vercel CLI. The site holds no key and no run button.

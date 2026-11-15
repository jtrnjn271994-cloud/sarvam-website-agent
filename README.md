# Sarvam website agent

Written for: a reviewer who has not seen this project and wants to try it or run it.

This agent audits the top section of a Sarvam web page. That section is the hero: the headline (H1), one sub-line and the main button. For one buyer and one goal, it finds what the hero fails to say. It writes three better heroes and checks them with rules and two judge models. Then it stops for a person to approve one. It tests the approved hero in a sandbox and writes the findings.

A model drafts. Code checks. A person approves. Every fact comes from a quote on the saved page or a checked row in `knowledge/`.

## 1. Try it on the website (2 minutes, nothing to install)

Open **https://sarvam-website-agent.vercel.app**.

1. Pick a **page**, an **industry**, a **buyer** and a **goal** at the top. The goal list changes with the buyer. The first goal is the suggestion.
2. Click **Start a run**. Keep the tab open. A run takes about 3 minutes, and the Log tab shows each step as it happens.
3. Read the **Audit**, **Dossier** and **Variants** tabs. Each variant shows both judges' scores.
4. Open **Approve and test**. Approve one variant, or edit one (see section 3).
5. Click **Run the sandbox**. Then read **Sandbox and findings**. The flow diagram there shows the path this run took.
6. **Submission and docs** shows this README, the architecture and the Jev note.

**Try these first.** These pages are set up, and these choices give a clear result:

| Page | Industry and buyer | Goal | What you will see |
|---|---|---|---|
| Voice Agents | Banks & lenders: Business owner | More visitors start building (self-serve) | Variant B passed both judges in two runs. Approve it, then run the sandbox. |
| Coding Agents | GCCs & IT services: Technical evaluator | More developers open the API docs | In the run made on the website, all three variants are near misses. Approve one with a reason, or edit one and check it again. |

**Limits on the website.** One run at a time. Up to $1.00 a run, $3.00 a day for the whole site, and 3 runs a day per visitor. The website has no browser on its server, so it takes no screenshots and never loads sarvam.ai. Its sandbox reads the saved page once per arm instead of running 20 browser sessions, and the findings say so. Runs made on the owner's machine are read-only on the website.

## 2. Run it on your own machine (full agent)

You need Python 3.9 or newer and an OpenRouter key (openrouter.ai, Keys, Create key).

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

Open http://127.0.0.1:8765. The steps are the same as on the website, plus one more:

- **Page setup, once per page.** A page can run only after its positioning and claims are approved. Voice Agents, Coding Agents and Token Factory are already approved. For any other page (for example Document AI), open **Page setup**. Draft the positioning, claims and buyer checklist, read them, and click **Approve** on each. The buyer checklist is optional. It adds the buyer's own questions (A7 and A8) to the audit.

On your machine the agent also takes screenshots (a PNG pair for each variant) and runs 20 browser sessions per arm in the sandbox. A run costs about $0.25 to $0.55.

You can browse every saved run without a key. You need the key only to start a run, edit a variant or draft a page setup.

## 3. When no variant passes

A run can end with no variant that passed both gates. You still have three ways forward, all in **Approve and test**:

1. **Approve against Gate 2, with a reason.** A variant that failed Gate 2 (the judges) can be approved if you type why. A **near miss** label means the gaps improved but one kept question fell. That is often wording, not meaning.
2. **Edit and re-check.** Open **Edit and re-check** under any variant. Change the H1, sub-line or button yourself, and click **Re-check my words**.
3. **Ask the writer to revise.** In the same box, write a note, for example "name the buyer in the headline", and click **Ask the writer to revise**. The writer rewrites that one variant.

An edit or a revision goes through Gate 1 (rules) and Gate 2 (both judges) again. It comes back as a new variant, for example `B-edit1`, and the original stays as it was. A variant that fails Gate 1 cannot be approved as it stands, because its text is not true or not allowed. Edit it and check it again. Each run allows 5 edits. An edit costs about $0.02 to $0.10.

If the audit finds **no gap**, the hero already answers the buyer's basic questions, so nothing is written. Try another buyer or goal.

## 4. The same steps without the UI

```
python3 agent/pages_registry.py --capture --page coding-agents        # save the live hero once (the only call to sarvam.ai)
python3 agent/page_setup.py --page coding-agents --persona gcc:technical-evaluator   # draft claims, positioning and checklist
python3 agent/probe3.py --page coding-agents --persona gcc:technical-evaluator --goal read-docs   # one run
python3 agent/edit_variant.py --page coding-agents --run probe3-YYYYMMDD-HHMMSS --from B --note "name the buyer"   # edit and re-check
python3 agent/sandbox_hero.py --page coding-agents --run probe3-YYYYMMDD-HHMMSS   # sandbox, after a variant is approved
```

Approvals are written only when a person clicks Approve in the console. The command line never approves. The sandbox refuses to run until a variant is approved.

**Checks:**
```
python3 -I agent/shortlist.py --selftest
python3 -I agent/gate1.py --selftest
python3 -I agent/sandbox_hero.py --selftest
```

## 5. How it works

Read **`docs/architecture.html`**, online at **https://sarvam-website-agent.vercel.app/architecture.html** (also in the Submission and docs tab). It shows the whole run step by step, the three layers of the code, the questions Jev asks and the deployment. **`submission/JEV-NOTE.md`** explains where Jev fits.

**Each run has its own diagram.** `agent/run_flow.py` draws the same steps, filled in with that run's facts: buyer, gaps, variants, gate results, edits, approval and sandbox. Steps the run did not reach are grey and dashed. The run, edit and sandbox scripts update it when they finish (`RUN-FLOW.html` in the run folder), and the Sandbox and findings tab shows it. The template and every scenario it handles are in `.claude/skills/run-architecture/SKILL.md`. Check them with `python3 -I agent/run_flow.py --selftest`.

**Models.** Four roles live in `agent/models.json`: reasoning (Google Gemini 3.8 Flash), writer (Anthropic Claude Opus 5.5), judge 1 (Jev) and judge 2 (OpenAI GPT-6 Luna decisions). One OpenRouter key serves all four. To swap one, set it in `.env`, for example `MODEL_WRITER=anthropic/claude-opus-5.5`. The two judges use OpenRouter's decisions endpoint, which today accepts only Jev and OpenAI's decision model.

**The knowledge base.** `knowledge/` is a fixed, versioned snapshot of the checked research: price ledgers, buyer research, rival cases and proof rows. Rows that failed a check are not in it. Contact records, named people and full transcripts are not in it. The agent cites a row as `KB:<id>`. Code checks that the id exists and that every number next to it is in that row. Every run records the knowledge version it used.

**Rules.** Rules live in `rules/`. Positioning follows a 12-section structure, and every bullet is sourced and labelled. Page facts come from `pages/<page>/claims`, and each claim is tied to a quote found word for word on the saved page. The agent never claims what `rules/do-not-claim.md` bans and never names a third-party model in hero copy.

**The sandbox.** It is synthetic. The visitor groups, their reactions and the lift are built for each run from the buyer, the goal and the judge scores. Test 1 uses the expected lift with enough visitors. Test 2 uses the same lift with too few visitors and should say inconclusive. Test 3 runs the page against itself and must say inconclusive. These tests check the measuring method. They do not show that a variant wins, because the lift is an input. `FINDINGS.md` states how many real visitors a real test needs.

**Folders.**
- `agent/`: the logic, one script per step
- `app/`: the console (`server.py`, `index.html`) and the website version (`hosted.py`)
- `knowledge/`: the fixed research snapshot
- `pages/<page>/`: the saved hero, claims, evidence, setup approvals and every run
- `rules/`, `skills/`, `library/`: rules, the skill files the models read, and buyer personas
- `docs/`, `submission/`: the architecture and the Jev note
- `scripts/`: deploy, keys and knowledge import

## 6. Known limits

- The hero only, on desktop. No page body, no mobile view.
- Judge scores are an audit signal, not proof. The calibration set is small and written by us.
- Persona and goal suggestions are analyst proposals, not buyer research.
- Saved pages are dated. Capture again before a new run if a page changed.
- There is no login. The website uses spend caps and an owner code instead.

## 7. For the owner: access, keys and deploy

**Give someone the code.** The repo **https://github.com/jtrnjn271994-cloud/sarvam-website-agent** is private. On GitHub, open **Settings > Collaborators > Add people**, type their username or email, and choose **Read**. They accept the email invite, then clone the repo or click **Code > Download ZIP**.

**Keys.** Keys live in your local `.env` (never committed) and in the Vercel project settings. They are never in a deployed file. `.env` holds `OPENROUTER_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `OWNER_TOKEN` and optional limits (see `.env.example`). The owner code (`OWNER_TOKEN`) unlocks page setup on the website.

**Deploy.** A push to GitHub does not deploy the website. Git is disconnected from Vercel on purpose. The website changes only through the deploy script:
```
./scripts/deploy_live.sh        # builds the site and deploys a preview link
./scripts/push_env.sh           # copies each key from .env to Vercel; prints no values (needed once, or when a key changes)
./scripts/deploy_live.sh --prod # publishes to sarvam-website-agent.vercel.app
```
The deploy script stops if it finds a key-like string in the files it is about to deploy. Set a credit limit on the OpenRouter key at openrouter.ai: the site's own caps are the second line.

**Database.** Supabase project Red Zebra holds two tables. `sarvam_agent_files` keeps runs, approvals and setup files. `sarvam_agent_jobs` keeps the job log, the one-job lock and the spend. Row level security is on with no policies, so only the server key can read or write them.

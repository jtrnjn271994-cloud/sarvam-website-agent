#!/usr/bin/env python3
"""Build docs/architecture.md and docs/architecture.html from one source.
Run: python3 -I docs/build_architecture.py
Both files come from the data below, so they cannot disagree."""
import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

TITLE = "Sarvam website agent: architecture"
VERSION = "v14, 16 Nov 2026, as built"

ROLES = {  # key: (label, hex fill, hex stroke)
    "person": ("Person", "#FFF4D6", "#C9A227"),
    "rules": ("Rules (code)", "#EEF0F3", "#8A94A3"),
    "reasoning": ("Reasoning LLM (Gemini)", "#FFE8D9", "#D9733B"),
    "writer": ("Writer LLM (Opus)", "#DCEBFF", "#3B82C4"),
    "jev": ("Jev", "#EADFFF", "#7A4DD8"),
    "judge2": ("Judge 2", "#D9F3EC", "#1E9E80"),
}

CLASSES = """    classDef person fill:#FFF4D6,stroke:#C9A227,color:#3b2f00
    classDef rules fill:#EEF0F3,stroke:#8A94A3,color:#1f2933
    classDef writer fill:#DCEBFF,stroke:#3B82C4,color:#0b2a4a
    classDef reasoning fill:#FFE8D9,stroke:#D9733B,color:#4a1f05
    classDef jev fill:#EADFFF,stroke:#7A4DD8,color:#2a1260
    classDef stop fill:#FDE2E2,stroke:#D14B4B,color:#5a1010
    classDef gate fill:#EEF0F3,stroke:#4a5568,stroke-width:3px,color:#1f2933
    classDef gate2 fill:#EADFFF,stroke:#7A4DD8,stroke-width:3px,color:#2a1260
    classDef gate3 fill:#FFF4D6,stroke:#C9A227,stroke-width:3px,color:#3b2f00
    classDef judge2 fill:#D9F3EC,stroke:#1E9E80,color:#073b2f
    classDef judge2t fill:#D9F3EC,stroke:#1E9E80,stroke-width:3px,color:#073b2f
"""

FLOW = """flowchart TD
    S["1 Start (person)<br/>page, industry, buyer persona, goal<br/>picked from drop-downs, in the local console or on the website<br/>the goal list changes with the buyer; the first goal is the suggestion"] --> C["2 Capture the page once with Playwright (owner's machine)<br/>done on 15 Nov 2026 for all 13 pages<br/>keep the hero only: H1, sub-line, main CTA text and link<br/>plus a hero screenshot (desktop) and a saved copy of the page<br/>the rest of the page is stored, never audited<br/>every run reads this saved copy, never the live page<br/>to audit a newer version of the page, capture it again"]
    C --> P{"3 Page set up<br/>and approved?"}
    P -- yes --> L["Load the approved positioning, claims and buyer checklist<br/>(the checklist is optional: it adds questions A7 and A8)"]
    P -- no --> G["Reasoning model (Gemini) drafts the page setup<br/>claims: each tied to a quote found word for word on the saved page<br/>positioning: 12 sections, every bullet sourced and labelled<br/>sources: the saved page and knowledge/ only, cited as KB ids<br/>buyer checklist: questions this buyer asks, tagged hero or page"]
    G --> GC["Rules check the draft<br/>every quote is on the page, every KB id exists,<br/>every number is in its row, the 12-section structure holds<br/>3 tries, then the problems are shown"] --> GP["Owner approves each part<br/>(on the website this needs the owner code)<br/>the approval keeps a hash: an edited file needs a fresh approval"]
    GP --> L
    L --> A["4 AUDIT the saved hero (captured 15 Nov): JEV only<br/>A1 the buyer sees their situation, A2 says what they get in plain words,<br/>A3 gives a checkable proof, A4 the button says what happens<br/>(these four can start a rewrite; A5 to A8 inform only)<br/>each answer is a probability, read against lines from 65 test cases"]:::jev
    A --> D{"Gap found?<br/>A1 to A4 fails or holds"}
    D -- no --> N["Stop: report 'no gap'<br/>nothing is written"]
    D -- yes --> H["5 GAP DOSSIER (written out in full)<br/>Gemini writes it; code checks every number, id and quote, 2 fix rounds<br/>what the hero says now, exact text<br/>which buyer question fails and why it matters to this buyer<br/>hypothesis: if we change X for buyer Y, more of them click, because E<br/>what we do not know: no internal analytics<br/>what would prove it wrong"]
    H --> T["6 TEST PLAN<br/>action: one click on the hero's main button<br/>the button must go to the real link for the chosen goal<br/>pass lines, the better-than-baseline rule and the spend cap are saved with the run<br/>(a separate hashed plan file is not built yet)"]
    T --> W["7 WRITER (Opus) drafts 3 hero variants, then edits them<br/>one angle each; every sentence lists the claim id it relies on<br/>told the gaps, the buyer's question, the objection and the positioning promise<br/>told what the live hero already answers: keep it"]
    W --> G1["Gate 1: RULES (no model)<br/>claim id exists and its quote is on the page<br/>no banned phrase, no new number or comparison<br/>no third-party model named<br/>the button goes to the real link for the goal<br/>only the hero changes"]:::gate
    G1 -- fail --> R{"Rounds left?<br/>max 2"}
    R -- yes --> W
    R -- no --> X["Variant marked: failed Gate 1<br/>shown with its problems; it can be edited (step 9)"]
    G1 -- pass --> G2J["Gate 2: JEV<br/>G1-G3 honest? then A1-A8 better?"]:::gate2
    G1 -- pass --> G2K["Gate 2: JUDGE 2<br/>OpenAI gpt-6-luna-decisions<br/>same questions, answers alone"]:::judge2t
    G2J --> BB["Both say better?<br/>better = average gain of 0.10 or more on the gaps,<br/>and no other question down by more than 0.05<br/>disagree = held for a person"]
    G2K --> BB
    BB --> SL["Shortlist: nothing is hidden<br/>passed: both judges say better<br/>held: the judges disagree, or a banned flag that code cannot confirm<br/>failed Gate 2: marked NEAR MISS when only a kept question fell<br/>failed Gate 1: shown, not approvable as it stands"]
    X --> SL
    SL --> PX["8 Picture each variant for the person (PNG pair)<br/>the capture has a picture of today's hero, but none of the new words yet<br/>so the new words are swapped into the hero: text only, layout unchanged<br/>owner's machine: one read-only load of the live page (no clicks) for this,<br/>because the saved copy draws without its styles offline<br/>website: no picture and no live load; the word-by-word change is shown"]
    PX --> F["Functional check<br/>the button of each arm points to the real link for the goal"]
    F --> AP["9 HUMAN approval<br/>the person sees each variant, both judges' scores per question,<br/>the dossier, the claim map and the PNG pair<br/>a variant that failed Gate 2 can be approved with a typed reason"]:::gate
    AP -- edit --> E["Edit and re-check<br/>the person changes the H1, sub-line or button,<br/>or writes a note and the writer (Opus) rewrites that one variant<br/>the new version goes through Gate 1 and Gate 2 again<br/>and comes back as a new variant, for example B-edit1"]
    E --> G1
    AP -- reject --> RJ["Variant stays inactive<br/>no exposure"]
    AP -- approve --> SP["10 SANDBOX PLAN, built for this run<br/>visitor groups: this buyer plus the other roles in the industry<br/>reaction strength: how well the goal fits each role<br/>lift: 0.5 x the judges' average gain, at least 2%, at most 50%<br/>visitors per arm: the sample a real test needs<br/>Gemini explains the set-up; code checks every number"]
    SP --> SB["Simulate and check (no model)<br/>Test 1: the expected lift, enough visitors<br/>Test 2: the same lift, too few visitors<br/>Test 3: the page against itself (A/A)<br/>owner's machine: 20 browser sessions per arm on the saved page, outside requests blocked<br/>website: one HTML check per arm, no browser"]
    SB --> FD["11 FINDINGS, built from the data<br/>plain words first, then the set-up<br/>rates with intervals, the sample a real test needs, the limits<br/>all SYNTHETIC<br/>status line: NOT rolled out, rollout needs approval"]
    FD --> RD["Redraw this run's diagram<br/>code, no model<br/>after every run, edit and sandbox"]:::rules
    RD --> RS["Write the run story<br/>Gemini, run-story skill<br/>code checks every number, question and variant<br/>2 retries, else no story"]:::reasoning
    RS --> DOC["12 Submission and docs, in the console<br/>README, this architecture, the Jev note,<br/>a flow diagram of the run, the tick list for the assignment"]
    classDef gate stroke-width:3px
"""
FLOW = FLOW.replace("    classDef gate stroke-width:3px\n", CLASSES)

LAYERS = """flowchart TB
    subgraph ENG["Layer A: Engine (generic code, no page names)"]
        direction TB
        E1["probe3.py: the run, one linear flow"]
        E2["capture_hero.py, pages_registry.py: capture"]
        E3["gate1.py, quote_match.py: rule checks"]
        E4["llm.py: model clients (Gemini, Opus, Jev, OpenAI decisions)<br/>every call logged with its cost"]
        E5["edit_variant.py: edit and re-check one variant"]
        E6["sandbox_plan.py, sandbox_hero.py: plan, simulation, checks"]
        E7["shortlist.py: groups and approval hashes"]
        E8["app/server.py: the console<br/>app/hosted.py: the same console on the website"]
    end
    subgraph POL["Layer B: Policy (shared by every page)"]
        direction TB
        P1["evidence labels and the do-not-claim list"]
        P2["hero policy: stretch phrases, keep rules"]
        P3["skills: positioning, copy, CRO, dossier, plain writing"]
        P4["judge questions, pass lines, goals,<br/>positioning structure (12 sections)"]
        P5["library/personas.json: 8 industries, 60 buyer roles"]
    end
    subgraph PACK["Layer C: Page pack (data, one folder per page)"]
        direction TB
        K1["capture/: saved hero, screenshot, page copy"]
        K2["claims/ and evidence/: each claim has a quote on the page"]
        K3["setup/: positioning, buyer checklists, approvals"]
        K4["runs/: every run, its approvals and sandbox"]
    end
    PACK --> ENG
    POL --> ENG
    NEW["pages_registry.py --capture<br/>add a page and save its hero once"] --> PACK
    KB["knowledge/: fixed research snapshot<br/>checked rows only, versioned, cited as KB ids"] -.cited by id.-> PACK
    CAL["calibrate.py: 65 test cases<br/>run separately, not every run"] --> ENG
    E1 ~~~ E2 ~~~ E3 ~~~ E4 ~~~ E5 ~~~ E6 ~~~ E7 ~~~ E8
    P1 ~~~ P2 ~~~ P3 ~~~ P4 ~~~ P5
    K1 ~~~ K2 ~~~ K3 ~~~ K4
"""

QUESTIONS_DIAGRAM = """flowchart TB
    AU["The audit (step 4)<br/>asked by: JEV only<br/>on the saved hero, 15 Nov<br/>A1-A8"]:::jev
    GT1["Gate 1<br/>asked by: no model, code rules"]:::rules
    JV["Gate 2 · JEV<br/>each judge answers alone<br/>G1-G3 honest?<br/>A1-A8 better?"]:::jev
    J2["Gate 2 · JUDGE 2<br/>each judge answers alone<br/>OpenAI gpt-6-luna-decisions<br/>G1-G3 honest?<br/>A1-A8 better?"]:::judge2
    BOTH["Both say better?"]:::rules
    AU --> GT1
    GT1 --> JV
    GT1 --> J2
    JV --> BOTH
    J2 --> BOTH
""" + CLASSES

SANDBOX_DIAGRAM = """flowchart TB
    AP["Approval<br/>saved with a hash<br/>the sandbox refuses to start<br/>if the variant changed"]:::person
    PL["Sandbox plan<br/>visitor groups for this industry<br/>and how strongly each role reacts<br/>lift rule and visitors per arm<br/>Gemini explains, code checks every number"]:::reasoning
    TS["Three tests<br/>Test 1: expected lift, enough visitors<br/>Test 2: same lift, too few visitors<br/>Test 3: the page against itself (A/A)"]:::rules
    SE["Sessions<br/>owner's machine: 20 browser sessions per arm,<br/>outside requests blocked<br/>website: one HTML check per arm, no browser"]:::rules
    FI["FINDINGS.md<br/>code builds the numbers and tables<br/>Gemini writes the explanation with the sandbox-ab-report skill<br/>rules check the prose<br/>SYNTHETIC, NOT rolled out"]:::reasoning
    SH["Shown in the console<br/>Sandbox and findings tab, the run's own diagram,<br/>Submission and docs"]:::rules
    AP --> PL --> TS --> SE --> FI --> SH
""" + CLASSES

SKILLS_DIAGRAM = """flowchart TB
    S1["Positioning draft<br/>(Gemini)"]:::reasoning --> K1["seven-page-positioning<br/>product-marketing"]
    S2["Dossier<br/>(Gemini)"]:::reasoning --> K2["cro<br/>buyer-profile-validation<br/>claim-evidence-check<br/>marketing-plain-writing"]
    S3["Writer draft<br/>(Opus)"]:::writer --> K3["copywriting-marketingskills<br/>cro<br/>page-copy-draft"]
    S4["Writer edit<br/>(Opus)"]:::writer --> K4["copy-editing<br/>no-ai-slop<br/>marketing-plain-writing"]
    S5["Findings<br/>(Gemini)"]:::reasoning --> K5["sandbox-ab-report<br/>marketing-plain-writing<br/>no-ai-slop"]
    S6["Run story<br/>(Gemini)"]:::reasoning --> K6["run-story<br/>marketing-plain-writing"]
    S7["Jev and Judge 2"]:::jev --> K7["no skills:<br/>fixed questions only"]
""" + CLASSES

DEPLOY = """flowchart TB
    ME["<b>1 · Your machine (the owner)</b><br/>the real code: agent/, app/, rules/, knowledge/<br/>your runs in pages/<br/>full agent: screenshots, 20 browser sessions per sandbox arm<br/>.env holds the keys: never committed, never deployed in a file"]
    GH["<b>2 · GitHub (private)</b><br/>a shelf: the code and the runs you commit<br/>runs nothing"]
    WEB["<b>3 · Website (Vercel)</b><br/>a frozen copy of the code and your runs, from the last deploy<br/>your runs are read-only here<br/>one Python function runs the agent when a visitor clicks<br/>no browser: no screenshots, sarvam.ai never loaded<br/>the keys sit in Vercel settings"]
    SB[("<b>4 · Supabase (Red Zebra)</b><br/>visitor runs, edits and approvals<br/>job log, one-job lock, today's spend<br/>server key only")]
    OR["OpenRouter<br/>the four models, one key"]
    V(["Visitor"])
    FR(["A reviewer with Read access"])
    ME -- "git push: code and the runs you commit<br/>(only when you push)" --> GH
    ME -- "deploy: a frozen copy of the code and your runs<br/>push_env.sh: the keys<br/>(only when you run the scripts)" --> WEB
    V -- "picks options, clicks Run" --> WEB
    WEB -- "visitor run: saved to Supabase<br/>loaded back on every request" --> SB
    GH -- "git pull" --> FR
    WEB -- "model calls" --> OR
    ME -- "model calls" --> OR
    SB -. "pull_website_runs.py: visitor runs<br/>(only when you choose)" .-> ME
    classDef place fill:#F7F8FB,stroke:#4a5568,stroke-width:2px,color:#1a1a2e,text-align:left
    classDef who fill:#FFF4D6,stroke:#C9A227,color:#3b2f00
    class ME,GH,WEB,SB place
    class V,FR who
"""

VISITOR_STEPS = [
    "The visitor opens the website and picks a page, an industry, a buyer and a goal.",
    "They click **Start a run**. The website checks the limits first: one job at a time, $1.00 a run, $3.00 a day for the whole site, 3 runs a day per visitor.",
    "Vercel runs the same agent code, from the frozen copy, on its own server. Nothing runs on your machine.",
    "The agent calls the models through OpenRouter, with your key. The run log records each call and its cost.",
    "Every file the run writes is saved to Supabase. The log is saved every 4 seconds, so the Log tab shows each step as it happens.",
    "Any visitor can now open that run, edit a variant, approve one and run the sandbox. Each of these is saved to Supabase too.",
    "The run stays on the website. It reaches your machine only when you run `scripts/pull_website_runs.py`, and GitHub only when you then commit and push it.",
]

CANT_TOUCH = [
    "**Your machine.** The website has no link to it.",
    "**GitHub.** The website has no GitHub key, and Git is disconnected from Vercel. A push never changes the website.",
    "**The code, rules and knowledge.** They are read-only on the website. Only a deploy from your machine changes them.",
    "**Your runs.** Runs made on your machine are read-only on the website: no edits, approvals or sandbox on them.",
    "**Page setup** (positioning, claims, buyer checklist). Only someone with the owner code can draft or approve it.",
    "**A newer page setup.** A setup file saved on the website before the latest deploy never replaces the deployed copy. The newer one wins.",
    "**The keys.** They live in the Vercel settings and are never sent to the browser.",
]

FLEET_INTRO = [
    "A multi-agent system is either a **swarm** or a **fleet**. In a swarm, agents decide among themselves how to attack an open problem. That suits exploration, when nobody yet knows how to solve the task. In a fleet, each agent has one fixed job, input, output and handoff. That suits work customers will see.",
    "**This agent is a fleet.** One script (`agent/probe3.py`) runs the steps in a fixed order. Each model has one role. Code checks every output, and a person approves.",
    "**The research before it was not a swarm either.** We checked how each input was made:",
]

SWARM_CHECK = [
    "**Positioning:** explored by a person with AI assistants (ChatGPT and Claude), then approved by that person. No agents negotiated among themselves.",
    "**Buyer insights:** one orchestrator gave every worker the same fixed brief, one industry each. Workers never talked to each other or chose their own method. Code then checked every row, and planted wrong rows to prove the check catches them. That is a fleet that runs in parallel.",
    "**Claims:** every price and quote was checked by code against fixed rules: the source opens, the number is on the page, a quote matches word for word. Inside the agent, `page_setup.py` drops any claim whose quote is not on the saved page, and a person approves the rest.",
    "So the exploration was done by people and by parallel workers with one brief. What reached the agent is only what code checked and a person approved: rows in `knowledge/` and approved claims.",
]

LANGGRAPH = [
    "**The graph of steps (LangGraph's job):** `agent/probe3.py` calls the steps in a fixed order. The gates are the branches: a Gate 1 fail goes back to the writer, at most twice; a pass goes on.",
    "**Saved state (LangGraph's checkpoints):** each run's `probe3.json` holds the result of every step. An edit, the approval and the sandbox read it and add to it, so a run can be picked up later, by anyone, on the machine or the website.",
    "**The pause for a person (LangGraph's interrupt):** the run stops before approval. Only a person's click saves an approval, with a hash of what was approved. The sandbox refuses to start without one, or if the variant changed since.",
    "**Traces (LangSmith's job):** `run-log.jsonl` records every model call: its role, the model asked, the model that answered, the time and the cost. Each run also gets its own flow diagram.",
    "**Evals (LangSmith's job):** Gate 1 rules, the two judges, the 65 test cases in `calibrate.py` (3 held back from tuning), and the self-tests.",
    "**Why plain Python.** The flow is fixed, so a framework adds little. The website function needs no extra packages, and every step can be read in one file. If the flow later needs many branches or many parallel workers, LangGraph would be worth adding.",
]

LOCAL_STEPS = [
    "You start the console with `./run-ui.sh` and open http://127.0.0.1:8765. Or you run `agent/probe3.py` from the command line.",
    "You pick a page, an industry, a buyer and a goal, and click **Start a run**. One job runs at a time, with a $1.00 cap per run.",
    "The agent runs on your machine, with the key in your `.env`. It calls the models through OpenRouter, and the run log records each call and its cost.",
    "The audit, writer and gates read the saved copy of the page. For the PNG pairs, the browser loads the live page once, read only, with no clicks.",
    "Every file is saved in `pages/<page>/runs/probe3-<date>-<time>/` on your machine. Nothing goes to Supabase, the website or GitHub.",
    "You approve a variant and run the sandbox. It runs 20 browser sessions per arm on the saved page, with every outside request blocked.",
    "The run reaches GitHub only when you commit and push it, and the website only when you deploy. On the website it is read-only.",
]

FLEET_HEAD = ["Practice", "What it means", "In this agent", "Gap"]
FLEET_ROWS = [
    ("Orchestration", "Each step runs in the right order, with the right tool or data.",
     "`probe3.py` runs the 12 steps in a fixed order and stops at each gate.", "None known."),
    ("Evals", "Outputs are tested before anyone sees them.",
     "Gate 1 (rules) and Gate 2 (two judges) check every variant. Self-tests check the code.",
     "The judges' test set is small (65 cases, 3 held back from tuning) and written by us. No fixed test set is rerun after each code change."),
    ("Observability", "Every step can be traced, so a mistake can be found and fixed.",
     "`run-log.jsonl` records every model call and its cost. A live Log tab, and a flow diagram for each run.", "None known."),
    ("Guardrails", "Limits on what the agent can see, spend and change.",
     "Spend caps, the one-job lock, the owner code, the do-not-claim list, knowledge-base number checks.", "None known."),
    ("Model routing", "Each task goes to the right model, and a model can be swapped without starting over.",
     "Four roles in `models.json`. Swap one in `.env`.", "If a model fails, nothing switches to a backup."),
]

NEXT = [
    "**A learning loop, run as a fleet, not a swarm.** (1) Every decision is already recorded: what a person approved, edited or rejected and why, and every gate failure. (2) A person reviews those records and marks each case right or wrong. (3) Reviewed cases join the judges' test set (`calibrate.py`). (4) A rule or a pass line changes only after the old and new cases are rerun, including cases held back from tuning. (5) A person approves the change. No model changes its own rules. Not built.",
    "**A model backup.** If a model call fails or a model is retired, use a named backup for that role and record which model answered. The judges have no backup today: OpenRouter's decisions endpoint accepts only Jev and OpenAI's decision model. Not built.",
    "**A fixed test set rerun after every code change**, so a change that makes the judges or the gates worse is caught before a run uses it. Not built.",
]

GUARDS = [
    "**Spend.** $1.00 cap per run. On the website: $3.00 a day in total and 3 runs a day per visitor. A credit limit on the OpenRouter key is the last line.",
    "**One job at a time.** The local console and the website each run one job at a time. On the website the lock lives in Supabase, so it holds across servers.",
    "**Who may do what.** Anyone may start a run, edit or approve a variant, and run the sandbox. Only the owner (owner code) may draft or approve a page's positioning and claims. Runs made on the owner's machine are read-only on the website.",
    "**No names stored.** An approval on the website records \"a person\". It never stores a visitor's name.",
    "**No bot traffic.** The website and the sandbox never load sarvam.ai. On the owner's machine, the PNG step loads the live page once per run or edit, read only, with no clicks.",
]

AUDIT_Q_HEAD = ["Question", "Asks", "Can it start a rewrite?"]
AUDIT_Q_ROWS = [
    ("A1 situation", "Would this buyer recognise their own situation or problem in the hero? A job title is not needed, and a label alone is not enough.", "Yes"),
    ("A2 value", "Does the hero say what the product does and what the buyer gets from it, in plain words, not a slogan?", "Yes"),
    ("A3 proof", "Does the hero give a checkable proof point, such as a named standard, a number with its source, or a named customer?", "Yes"),
    ("A4 button", "Does the main button say what happens on click (for example, open the docs, book a demo, see prices), not just a vague word such as 'Go', 'Learn more' or 'Click here'?", "Yes"),
    ("A5 positioning", "Does the hero say what the positioning's main claim says?", "No. It informs the person and the writer."),
    ("A6 rival swap", "Could any rival in the rival rows print this exact hero on its own page without changing it? (Only when rival heroes are saved.)", "No. It informs the person and the writer."),
    ("A7 buyer question", "Does the hero answer this question the buyer asks: {item}? (Only once the buyer checklist is approved.)", "No. It informs the person and the writer."),
    ("A8 objection", "Does the hero answer this objection the buyer raises: {objection}?", "No. It informs the person and the writer."),
]

S3_INTRO = "Three checks ask questions, in this order. Each check has one asker, one input and one job. Only the audit and Gate 2 use models."

S3_AUDIT = [
    "**The audit (step 4).** Jev asks A1 to A8 of the saved hero, captured on 15 Nov 2026.",
    "Why: to find what today's hero fails to say. If there is no gap, nothing is written.",
    "Judge 2 does not run here, because one judge is enough to find gaps.",
]

S3_GATE1 = [
    "**Gate 1.** No model asks anything. Code rules check each variant.",
    "Why: to stop a variant that is not true or not allowed before any judge is paid.",
    "The rules:",
]
GATE1_RULES = [
    "The claim id exists, and its quote is on the saved page word for word.",
    "No banned phrase, no new number and no new comparison.",
    "No third-party model is named.",
    "The button goes to the real link for the goal.",
    "Only the hero changes.",
    "A failed variant goes back to the writer with the reason, at most twice.",
]

S3_GATE2 = [
    "**Gate 2.** Jev and Judge 2 each answer alone. Neither sees the other's answers.",
    "Why: to show that a variant is honest and better than today's hero.",
    "**Part 1, honest?** Each judge asks three questions of every fragment of the variant:",
]
GATE2_PART1 = [
    "**G1 support** (good answer: yes): \"Does the evidence quote say what this fragment says, with nothing added?\"",
    "**G2 overreach** (good answer: no): \"Does the fragment say more than the claim and evidence: a wider scope such as 'all' or 'never', a missing condition, a new comparison, or a guarantee?\"",
    "**G3 banned** (good answer: no): \"Does the hero make any claim on the do-not-claim list, in other words?\"",
]
S3_GATE2_PART2 = [
    "**Part 2, better?** Each judge asks A1 to A8 again of the variant.",
    "Better means an average gain of 0.10 or more on the gap questions, and no other question down by more than 0.05.",
    "Passed means both judges say better. If the judges disagree, the variant is held for a person.",
]

S3_EDIT = "**Edit and re-check:** the same Gate 1 and Gate 2."

S3_NOTE = [
    "Each answer is a probability of yes. We read it against pass and fail lines set from 65 test cases we wrote. 3 of those cases were held back from tuning. A value near a line means hold, and a person decides.",
    "**Question version:** v2 from 16 Nov 2026. Earlier runs used v1, and each run says which.",
]

S4_INTRO = "After a person approves a variant, the sandbox tests it and the findings explain the result. The sandbox refuses to start unless a variant is approved and unchanged since approval."
S4_CLOSE = "These tests check the measuring method. They do not prove a variant wins, because the lift is an input."

FLEET_HOW_HEAD = ["Member", "Reasons with", "Gets", "Returns", "Checked by"]
FLEET_HOW_ROWS = [
    ("Orchestrator (`agent/probe3.py`)", "No model. It decides the order.", "The run's choices", "The next step", "Not applicable"),
    ("Reasoning model (Gemini)", "Its skills", "The saved page, knowledge rows", "Page setup draft, dossier, sandbox and findings explanations", "Code checks every quote, number and id. A person approves the setup."),
    ("Writer (Opus)", "Its skills", "Dossier, approved claims", "3 variants, each with a claim map", "Gate 1 (code), then Gate 2"),
    ("Jev and Judge 2", "No skills: the fixed questions only", "Hero text, one claim and its quote", "A yes/no probability per question", "Calibrated pass lines. Both must agree."),
    ("Rules (code)", "No model", "Every output above", "Pass, fail and the reasons", "Self-tests"),
    ("Person", "Their own judgement", "Everything above", "Approve, edit or reject", "Saved with a hash"),
]
FLEET_HOW_LINE = "**Models reason only inside their own step. Code decides pass or fail, and no model decides what runs next.**"

SKILLS_INTRO = "Each step that uses a model loads a fixed set of skills (written guides for the task):"
SKILL_CONTROLS = [
    "**One fixed map.** The skills for each step sit in one file, `skills/step-skills.json`. No model chooses skills.",
    "**Saved fingerprints.** Each run saves every skill's name and sha256 fingerprint in `probe3.json`. The fingerprint changes if the skill text changes.",
    "**Hard rules win.** The hard rules come after the skills in the prompt and override them. They are the claims rules, the banned list and the Gate 1 limits.",
]
SKILL_NOTE = "`marketing-psychology` is left out of the writer on purpose. It pushes urgency, numbers and comparisons that the claims rules forbid."

RUN_DIAGRAM_TEXT = ("The facts of a run are saved once, in its run file (`probe3.json`). When someone opens the run, plain code with no model draws the diagram from that file (`agent/run_flow.py`) and builds the question list. "
                    "Steps the run did not reach are grey and dashed. The same run always gives the same view. "
                    "So when we improve the code, every old run is updated with no new model call. "
                    "The story is the one part a model writes. It is written once per run, and again after an edit or sandbox. Code checks it and saves it. "
                    "Old runs show the exact question wording they were asked. It comes from the run file, or from the v1 or v2 archive and the page's buyer checklist, and it is labelled as such. "
                    "The diagram template and its cases are in `.claude/skills/run-architecture/SKILL.md`.")

MODEL_BULLETS = [
    "**Reasoning model, Google `gemini-3.8-flash`:** page setup drafts, the dossier, the sandbox explanation. It never decides pass or fail.",
    "**Writer, Anthropic `claude-opus-5.5`:** the hero variants, the claim map, and a rewrite when a person asks for one.",
    "**Jev, `typesafe/jev-1.14` (Judge 1):** the audit, Gate 2 and edit re-checks. It returns probabilities, not reasons.",
    "**Judge 2 (OpenAI `gpt-6-luna-decisions`):** Gate 2 and edit re-checks only; not at the audit. Two judges from different makers; no judge grades its own maker's writing.",
    "**One OpenRouter key** serves all four. Swap a model in `agent/models.json` or with `MODEL_REASONING`, `MODEL_WRITER`, `MODEL_JUDGE1`, `MODEL_JUDGE2`.",
    "**Cost.** A run costs about $0.25 to $0.55. An edit about $0.05 to $0.15. A sandbox a cent or two.",
]

LATER = DEPLOY   # older name, kept for anything that imports it

QUESTIONS = [
    ("1. The hero basics (required)", "A1 situation, A2 value, A3 proof, A4 button",
     "Every buyer page must let the buyer recognise their situation, say what they get, give a reason to believe it, and say what happens on click. Naming the buyer is not required. A fail or hold here is a gap, and only these four can start a rewrite."),
    ("2. Positioning fit (advisory)", "A5 positioning, A6 rival swap",
     "A good hero says what this product promises, in words a rival could not print as is. A5 checks the approved promise is there. A6 asks if a rival could reuse the hero unchanged (only when rival heroes are saved). They inform the person but never block."),
    ("3. The buyer's own questions (advisory, per page)", "A7 checklist items, A8 objection",
     "Generic questions miss what a specific buyer asks. These come from the approved buyer checklist for this page and buyer, so they change with every page and persona."),
    ("4. Checks on each variant (Gate 2)", "G1 support, G2 overreach, G3 banned, then A1 to A8 again",
     "Stop the writer from over-claiming. G1 asks if the evidence says what the line says. G2 asks if the line says more. G3 asks if it makes a banned claim in other words. Asking the audit questions again of the variant shows whether it beats the live hero."),
]

STEPS = [
    # n, step, role keys, model text, reads, output
    ("1", "Start", ["person"], "No model", "The choices in the page folder: buyers, goals, test types", "brief.json"),
    ("2", "Capture the hero", ["rules"], "No model. Playwright.", "The live page, or a saved snapshot", "hero.json, hero-desktop.png"),
    ("3", "Positioning", ["reasoning", "rules", "person"], "Reasoning LLM (Gemini) only if no positioning is saved; a person approves", "Claims with evidence, do-not-claim list, buyer checklist, captured text, the positioning skill", "positioning.md"),
    ("4", "Audit the hero", ["jev"], "Jev", "Hero text, one checklist item, the positioning main claim, rival rows", "audit.json"),
    ("5", "Gap dossier", ["reasoning", "rules"], "Reasoning LLM (Gemini) writes the prose. Rules check every number against audit.json.", "Audit questions and probabilities, hero text, checklist, evidence ids", "GAP-SYNTHESIS.md"),
    ("6", "Lock the test plan", ["rules"], "No model", "Brief and dossier", "test-plan.json and its hash"),
    ("7", "Write variants", ["writer"], "Writer LLM (Opus 5.5)", "Dossier, claims with evidence, do-not-claim list, one checklist item, the copy and CRO skills, the name of a failed rule on a retry", "variants.json with a claim map"),
    ("8", "Check the variants", ["rules", "jev", "judge2"], "Gate 1: rules. Gate 2: Jev and Judge 2.", "Variant line, one claim and its evidence quote, do-not-claim list, rival rows, baseline hero", "gate1.json, gate2.json"),
    ("9", "Preview and flow check", ["rules"], "No model", "Passing variants and the captured page", "PNG pairs, word diff, flow-check.json"),
    ("10", "Human approval", ["person"], "No model", "PNG pairs, word diff, dossier, locked plan", "approval.json with a hash"),
    ("11", "Sandbox", ["rules", "reasoning"], "Built per run: visitor groups from the buyer's industry, reaction strength from how well the goal fits each role, lift from the judges' average gain by a fixed rule, visitor counts from the sample a real test needs. The reasoning model explains the set-up; code checks every number. Playwright bots check the pages.", "Approved variant, buyer, goal, judge scores, saved page", "sandbox-results.json, events.jsonl, FINDINGS.md"),
    ("12", "Findings and submission", ["reasoning", "rules"], "Reasoning LLM (Gemini) drafts the explanatory prose. Code builds every number, table, the tick list and the limits statement. Rules verify the prose.", "Every file above: audit, variants, gates, approval, events, run log", "FINDINGS.md, COVERAGE.md, README.md, ARCHITECTURE.md, JEV-NOTE.md"),
]

MODELS = [
    ("Reasoning LLM", "google/gemini-3.8-flash", "OpenRouter chat completions", "Text: page-setup research and claim drafts, positioning draft, dossier prose, submission prose. Never decides pass or fail.", "Page setup, steps 3, 5, 12"),
    ("Writer LLM", "anthropic/claude-opus-5.5", "OpenRouter chat completions", "Text: hero variants (H1, sub-line, button) and their claim map", "Step 7"),
    ("Jev (Judge 1)", "typesafe/jev-1.14", "OpenRouter Decisions API", "Probabilities only. No text.", "Steps 4, 8, edit re-checks, calibration"),
    ("Judge 2 (OpenAI gpt-6-luna-decisions)", "openai/gpt-6-luna-decisions", "OpenRouter Decisions API", "Probabilities only. No text.", "Step 8 and edit re-checks, calibration. Not the audit."),
]

COVERAGE = [
    ("Choose an audience and an intended action", "1", "probe3.json: persona and goal"),
    ("Identify a gap in value, proof, CTA or structure", "3, 4", "probe3.json: audit, GAP-DOSSIER.md"),
    ("Explain the evidence and the hypothesis. No internal analytics.", "4", "GAP-DOSSIER.md"),
    ("Recreate the section locally. Provide a baseline.", "2", "capture/hero.json, hero-desktop.png, snapshot-local.html"),
    ("Create a variant. Preserve supported claims.", "6", "probe3.json: variants, claim map, gate1_rounds, gate2"),
    ("Reviewable preview or diff", "7, 8", "pair-A.png, pair-B.png, pair-C.png"),
    ("Functional check of the user flow", "7, 10", "events.jsonl (20 sessions per arm)"),
    ("Pause before activating. Reject stays inactive. Revision needs fresh approval.", "8", "approval.json with variant and PNG hashes"),
    ("Define the action, metric and decision rule upfront", "5 (partly)", "probe3.json: goal, thresholds_used; sandbox-results.json: plan"),
    ("Sandbox A/B with stable assignment and recorded exposures and conversions", "9, 10", "sandbox-results.json, events.jsonl"),
    ("Conversion rates with uncertainty. A clear and an inconclusive outcome. Synthetic data labelled.", "11", "sandbox/FINDINGS.md"),
    ("Separate simulated findings from real evidence", "11", "sandbox/FINDINGS.md (limits), this document"),
    ("Rollout still requires approval", "11", "Status line in FINDINGS.md"),
    ("One command. A human checkpoint. A model at runtime. Real actions.", "1 to 11", "run-log.jsonl (every model call is logged), README.md"),
    ("Where Jev fits. One decision evaluated with a failure case. What is unverified.", "12", "submission/JEV-NOTE.md, tests/calibration"),
    ("Runnable code, README, setup and demo command", "12", "README.md"),
    ("Architecture note, Jev decision, limitations, real versus simulated", "12", "docs/architecture.md, submission/JEV-NOTE.md"),
]

SUBMISSION = [
    ("README.md", "LLM-drafted, rule-checked. Setup (`.env` from `.env.example`, one key), the one demo command, what each screen does"),
    ("ARCHITECTURE.md", "LLM-drafted, rule-checked. This note as built: layers, model map, real versus simulated, limitations"),
    ("JEV-NOTE.md", "LLM-drafted, rule-checked. Three yes/no decisions, where rules, the LLM and the decision models fit, one decision tested against cases with a failure case, what stays unverified"),
    ("GAP-SYNTHESIS.md", "LLM-drafted, rule-checked. The gap dossier and the Audit method: every judge question, probability, threshold and the calibration table, plus the limits statement"),
    ("FINDINGS.md", "Tables and numbers from code, interpretation from the LLM. Rates, intervals, the locked rule, the outcome, every sandbox line labelled SYNTHETIC, and the line 'Rollout requires approval'"),
    ("COVERAGE.md", "Code only, no LLM. The tick list: every assignment line, with a tick or a cross computed from the run's own files"),
    ("run folder", "Every input and output: hero, audit, variants, gates, PNGs, approval, events, run log"),
]

JEV_DECISIONS = [
    ("D1 Does the hero fail a required buyer question?", "Jev (audit)", "A fuzzy yes/no on meaning, so a decision model. Rules cannot read meaning."),
    ("D2 Does this evidence say what the line says?", "Rules first (id and quote exist), then Jev and Judge 2", "Rules check what is exact. The decision models check the meaning. Tested on 12 cases, 7 of them failure cases."),
    ("D3 Is the variant better than the baseline on the gap question?", "Jev and Judge 2, same question asked of both heroes", "Comparing two probabilities needs no text. A person still approves."),
]

REMOVED = [
    "Judge 2 at the audit step. One judge is enough there.",
    "Planted bad lines inside every run. The separate `--calibrate` test of the judges replaces them.",
    "A/A check and guardrail metric inside the run. The A/A check moves to the test suite.",
    "Strongest-variant scoring. The person picks among the variants that passed.",
    "Rollout approval as a step. It is one status line in the findings.",
    "Structure tests and the mobile view. Later.",
]


def chips_md(keys):
    return ", ".join(ROLES[k][0] for k in keys)


def chips_html(keys):
    out = []
    for k in keys:
        lab, fill, stroke = ROLES[k]
        out.append('<span class="chip" style="background:%s;border-color:%s">%s</span>' % (fill, stroke, lab))
    return " ".join(out)


def esc(t):
    return html.escape(t, quote=False)


def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "/") for c in r) + " |")
    return "\n".join(out)


def html_table(head, rows, cls=""):
    out = ['<div class="tw"><table class="%s"><thead><tr>%s</tr></thead><tbody>' % (cls, "".join("<th>%s</th>" % esc(h) for h in head))]
    for r in rows:
        out.append("<tr>" + "".join("<td>%s</td>" % c for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


GLANCE = [
    "**When the pages were read.** Every page's hero was captured once, on 15 Nov 2026. Every run audits that saved copy, so a run gives the same answer even if Sarvam edits its site. To audit a newer version, capture the page again.",
    "**What it does.** One run audits the hero of a Sarvam page for one buyer and one goal. It writes better heroes only if the audit finds a gap. A person approves one, or edits one and has it checked again. A sandbox then tests the approved hero against the baseline.",
    "**Where it runs.** On the owner's machine (full agent, with screenshots and browser checks) and on the website, where anyone can start a run. Website runs are saved in Supabase.",
    "**Scope.** The hero only: H1, sub-line and main button. Desktop. Thirteen pages are listed; Voice Agents, Token Factory and Coding Agents have been run.",
    "**Models.** Four makers on one OpenRouter key: Google's Gemini 3.8 Flash reasons, Anthropic's Opus 5.5 writes, and Jev (Judge 1) and OpenAI's decision model (Judge 2) judge. Code verifies every fact any model writes.",
    "**Evidence.** Every claim in a variant maps to a quote found word for word on the saved page. The console ticks each assignment line from the run's own files.",
]

TICK_RULE = ("In the final output a \u2714 means the proof file exists and its check passed. It does not mean the hypothesis is true. "
             "Code builds `COVERAGE.md` from the run folder. Nothing is typed by hand, so deleting a file turns its tick into a cross. "
             "Test T21 checks this.")

PROSE_RULE = ("**How the LLM prose is kept honest.** The writer gets the full run record: audit questions and probabilities, gates, approval, events, run log. "
              "It drafts long, reasoned text for the dossier and the submission files. Code then checks the text. Every number, id, model name and file name in it must appear in the run record. "
              "A line that names something not in the record is rejected and redrafted, two rounds at most. Code inserts the tables, the tick list and the limits statement itself, word for word. "
              "The LLM cannot change a SYNTHETIC label. Test T22 plants a wrong number and checks that it is caught.")

LIMITS = ("Jev and Judge 2 are general decision models. We did not train or fine-tune either one on labelled examples of right and wrong for this program. "
          "We set the pass lines ourselves from a small example set that we wrote. The probabilities are an audit signal, not an assurance. "
          "The owner accepted these pass lines as the working standard for approval on 15 Nov 2026. A person makes every approval.")


STATUS = [
    ("Built and tested", "Page setup and approvals, capture, audit, dossier, writer, Gate 1, Gate 2 with two judges, shortlist, human approval, dynamic sandbox, findings, console, the website (Vercel + Supabase) that runs the agent, README, Jev note."),
    ("Partly built", "Step 5 test plan: goal, link, thresholds and rules are saved with the run, but no separate hashed plan file. A Revise note now reaches the writer through Edit and re-check."),
    ("Not built", "Mobile view. A repeated Test 1. A hashed plan file. COVERAGE.md as a file (the console shows the tick list). Logins (the website uses spend caps and an owner code instead)."),
]

WHERE_WORKS = [
    ("Capture, PNG pairs, 20-session browser sandbox (Playwright)", "Local machine", "Vercel functions cannot run a full browser. Website runs take no screenshots and never load sarvam.ai."),
    ("Model calls (Gemini, Opus, Jev, Judge 2)", "Local machine or the website function", "The key lives in `.env` locally and in Vercel's settings online. It is never in the repo or a deployed file."),
    ("Start a run, approve a variant, run the sandbox", "Local console or the website", "A person clicks. The website runs one job at a time (about 3 minutes, inside a 5-minute limit), caps spend at $3 a day and 3 runs a day per visitor, and saves runs to Supabase."),
    ("Page setup (positioning, claims, checklist)", "Local console, or the website with the owner code", "Only the owner approves what the agent may say about a page."),
    ("Reading runs, audits, variants, scores, findings, docs", "Local console or the website", "Visitor names are never stored on the website: approvals record \"a person\"."),
]

TOOLS = [
    ("Python 3.9 or newer, standard library", "The console server, rules, statistics, the run. No framework."),
    ("Playwright with Chromium", "Capture of the hero, the PNG pairs, and the 20 scripted sessions per arm in the sandbox."),
    ("OpenRouter", "One key for chat models and for the decisions endpoint. Every call is logged with its cost. A cap of $1.00 per process stops overspend."),
    ("Mermaid (in the browser)", "Draws the diagrams in this document only. It is not used at runtime."),
    ("Semrush (one-off read)", "Search visits for the page list. A column only: about 96% of sarvam.ai search visits in India go to free translation tools."),
    ("Claude Code", "Built the project. It is not part of the running agent."),
]

RULE_FILES = [
    ("rules/do-not-claim.md", "Banned and unproven claims. Gate 1 and the judges both use it."),
    ("rules/hero-policy.json", "Stretch phrases, keep rules, per-page qualifiers (a price must keep the word 'from')."),
    ("rules/goals.json", "Five goals, the real link kind behind each, the goal wording and suggested goal for each buyer role."),
    ("rules/judge-questions.json", "Every audit and Gate 2 question, and the better-than-baseline rule (gain 0.10, drop 0.05)."),
    ("rules/judge-thresholds.json", "Pass and fail lines per question, set by calibration against 65 cases (3 held back from tuning)."),
    ("rules/positioning-structure.json", "The 12 sections every positioning pack must follow, with the label rules."),
    ("agent/sandbox_hero.json", "The typed assumptions of the sandbox: base click rate, lift rule, goal-fit values, caps."),
]

DATA = [
    ("library/personas.json", "8 industries and 60 buyer roles, with what each cares about and what blocks them. Analyst research, not interviews."),
    ("pages/registry.json", "13 pages from the sarvam.ai navigation and the market map, each with its layer and search visits."),
    ("pages/<page>/", "The saved hero, claims with evidence, setup approvals and every run."),
]

NOTES_MODELS = [
    "**Four makers, one key.** Google's Gemini reasons, Anthropic's Opus writes, TypeSafe's Jev and OpenAI's decision model judge. No judge grades its own maker's writing.",
    "**Models never decide a fact.** Code checks every quote, number, id and banned phrase. A person approves. Judges return probabilities, not reasons.",
    "**Cost.** A run costs about $0.25 to $0.50. A sandbox costs a cent or two. The reasoning model drafts page setup for about $0.05 to $0.10.",
    "**Swap a model** in `agent/models.json`, or with `MODEL_REASONING`, `MODEL_WRITER`, `MODEL_JUDGE1`, `MODEL_JUDGE2`. The decisions endpoint accepts only Jev and the OpenAI decision model today.",
]

LIMITS_LIST = [
    "The sandbox is synthetic. The lift is set from the judges' scores by a rule, so the simulation cannot show that a variant wins. It shows how many real visitors a real test needs.",
    "The base click rate (4%) and the goal-fit values are typed assumptions, labelled in every findings file.",
    "Jev and Judge 2 are general decision models, not trained for this work. Their pass lines come from a small case set we wrote. Scores are an audit signal, not proof.",
    "Buyer personas and goal suggestions are analyst proposals, not buyer research.",
    "The hero only, on desktop. No page body, no mobile view.",
    "A person makes every approval. The agent never writes an approval by itself, except where the owner told it to and the record says so.",
]


def build_md():
    o = ["# %s\n" % TITLE, "%s. Written for: the project owner and any reviewer. One document.\n" % VERSION]
    o += ["- " + g for g in GLANCE] + [""]
    o += ["## 1. The run: audit first, write only if there is a gap\n", "```mermaid\n" + FLOW + "```\n",
          "The writer never sees judge probabilities, pass lines or calibration cases. The judges never see the writer's reasoning or each other's answers.\n"]
    o += ["## 2. The three layers\n",
          "- **Layer A, Engine:** the code that does the work. It holds no page names, so one engine serves every page.",
          "- **Layer B, Policy:** the rules every page shares. Change a rule once and it applies to all pages.",
          "- **Layer C, Page pack:** the facts about one page, one folder each. A new page is a new folder.\n",
          "```mermaid\n" + LAYERS + "```\n"]
    o += ["## 3. Who asks which questions, at each check\n", S3_INTRO + "\n", "```mermaid\n" + QUESTIONS_DIAGRAM + "```\n"]
    o += [S3_AUDIT[0] + "\n", S3_AUDIT[1] + "\n", S3_AUDIT[2] + "\n"]
    o += ["", "#### The audit questions\n", md_table(AUDIT_Q_HEAD, AUDIT_Q_ROWS), ""]
    o += [x + "\n" for x in S3_GATE1[:2]] + [S3_GATE1[2]] + ["- " + x for x in GATE1_RULES] + [""]
    o += [x + "\n" for x in S3_GATE2[:2]] + [S3_GATE2[2]] + ["- " + x for x in GATE2_PART1] + [""]
    o += [x + "\n" for x in S3_GATE2_PART2] + [S3_EDIT + "\n"] + [x + "\n" for x in S3_NOTE]
    o += ["## 4. After approval: the sandbox and the findings\n", S4_INTRO + "\n", "```mermaid\n" + SANDBOX_DIAGRAM + "```\n", S4_CLOSE + "\n"]
    o += ["## 5. Where things live and what moves between them\n", "```mermaid\n" + DEPLOY + "```\n",
          "**What happens when a visitor clicks Run**\n"] + ["%d. %s" % (k + 1, x) for k, x in enumerate(VISITOR_STEPS)] + [""]
    o += ["**What happens when you run it on your own machine**\n"] + ["%d. %s" % (k + 1, x) for k, x in enumerate(LOCAL_STEPS)] + [""]
    o += ["**What a visitor can't touch**\n"] + ["- " + x for x in CANT_TOUCH] + [""]
    o += ["**Other guards**\n"] + ["- " + g for g in GUARDS] + [""]
    o += ["## 6. Fleet, not swarm\n"] + [x + "\n" for x in FLEET_INTRO] + ["- " + x for x in SWARM_CHECK] + [""]
    o += ["### How the fleet works\n", md_table(FLEET_HOW_HEAD, FLEET_HOW_ROWS), "", FLEET_HOW_LINE + "\n"]
    o += ["### Which skills each step uses\n", SKILLS_INTRO + "\n", "```mermaid\n" + SKILLS_DIAGRAM + "```\n"] + ["- " + x for x in SKILL_CONTROLS] + ["", SKILL_NOTE + "\n"]
    o += ["### The five practices\n", md_table(FLEET_HEAD, FLEET_ROWS), ""]
    o += ["### LangGraph and LangSmith\n", "We did not use them. The agent is plain Python, and each job those tools do has a part here:\n"] + ["- " + x for x in LANGGRAPH] + [""]
    o += ["### How each run's view is made\n", RUN_DIAGRAM_TEXT + "\n"]
    o += ["## 7. Models\n"] + ["- " + b for b in MODEL_BULLETS] + [""]
    o += ["## 8. Limits\n"] + ["- " + x for x in LIMITS_LIST] + [""]
    o += ["## 9. Next (not built)\n"] + ["- " + x for x in NEXT]
    return "\n".join(o) + "\n"


CSS = """
:root{--bg:#fff;--fg:#1a1a2e;--mut:#5b6472;--line:#e3e6ec;--card:#f7f8fb}
@media (prefers-color-scheme:dark){:root{--bg:#14161c;--fg:#e8eaf0;--mut:#9aa3b2;--line:#2a2f3a;--card:#1c1f27}}
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;margin:24px auto;max-width:1100px;padding:0 16px;background:var(--bg);color:var(--fg);line-height:1.55}
h1{font-size:28px;margin:0 0 4px}
.ver{color:var(--mut);margin:0 0 18px}
h2{margin-top:40px;font-size:21px}
p,li{max-width:85ch}
code{background:var(--card);border-radius:4px;padding:1px 5px;font-size:13px}
.mermaid{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px;margin:10px 0}
h3{font-size:16px;margin:22px 0 6px}
.tw{overflow-x:auto;margin:12px 0}
table.fleet{border-collapse:collapse;width:100%;min-width:640px;font-size:14px}
table.fleet th,table.fleet td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
table.fleet th{background:var(--card)}
table.fleet td:first-child{font-weight:600;white-space:nowrap}
.note{border-left:4px solid #3B5BDB;background:var(--card);padding:8px 12px;border-radius:6px}
"""


def inline(t):
    """Very small markdown: **bold** and `code`."""
    t = esc(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return t


def build_html():
    ul = lambda xs: "<ul>" + "".join("<li>%s</li>" % inline(x) for x in xs) + "</ul>"
    mm = lambda d: "<pre class='mermaid'>%s</pre>" % d
    h = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>Sarvam agent architecture</title><style>%s</style></head><body>" % CSS,
         "<h1>%s</h1><p class='ver'>%s. One document.</p>" % (esc(TITLE), esc(VERSION)), ul(GLANCE),
         "<h2>1. The run: audit first, write only if there is a gap</h2>", mm(FLOW),
         "<p class='note'>The writer never sees judge probabilities, pass lines or calibration cases. The judges never see the writer's reasoning or each other's answers.</p>",
         "<h2>2. The three layers</h2>",
         ul(["**Layer A, Engine:** the code that does the work. It holds no page names, so one engine serves every page.",
             "**Layer B, Policy:** the rules every page shares. Change a rule once and it applies to all pages.",
             "**Layer C, Page pack:** the facts about one page, one folder each. A new page is a new folder."]), mm(LAYERS),
         "<h2>3. Who asks which questions, at each check</h2>", "<p>%s</p>" % inline(S3_INTRO), mm(QUESTIONS_DIAGRAM),
         "".join("<p>%s</p>" % inline(x) for x in S3_AUDIT),
         "<h3>The audit questions</h3>", html_table(AUDIT_Q_HEAD, [[inline(c) for c in r] for r in AUDIT_Q_ROWS], "fleet"),
         "".join("<p>%s</p>" % inline(x) for x in S3_GATE1), ul(GATE1_RULES),
         "".join("<p>%s</p>" % inline(x) for x in S3_GATE2), ul(GATE2_PART1),
         "".join("<p>%s</p>" % inline(x) for x in S3_GATE2_PART2), "<p>%s</p>" % inline(S3_EDIT),
         "<p class='note'>%s</p>" % inline(S3_NOTE[0]), "<p>%s</p>" % inline(S3_NOTE[1]),
         "<h2>4. After approval: the sandbox and the findings</h2>", "<p>%s</p>" % inline(S4_INTRO), mm(SANDBOX_DIAGRAM), "<p>%s</p>" % inline(S4_CLOSE),
         "<h2>5. Where things live and what moves between them</h2>",
         "<p>Four places, each holding something different. Each arrow says what moves and when. Nothing runs on a schedule: a run starts only when someone clicks Run or starts one from the command line.</p>",
         mm(DEPLOY),
         "<h3>What happens when a visitor clicks Run</h3>", "<ol>" + "".join("<li>%s</li>" % inline(x) for x in VISITOR_STEPS) + "</ol>",
         "<h3>What happens when you run it on your own machine</h3>", "<ol>" + "".join("<li>%s</li>" % inline(x) for x in LOCAL_STEPS) + "</ol>",
         "<h3>What a visitor can't touch</h3>", ul(CANT_TOUCH),
         "<h3>Other guards</h3>", ul(GUARDS),
         "<h2>6. Fleet, not swarm</h2>", "".join("<p>%s</p>" % inline(x) for x in FLEET_INTRO), ul(SWARM_CHECK),
         "<h3>How the fleet works</h3>", html_table(FLEET_HOW_HEAD, [[inline(c) for c in r] for r in FLEET_HOW_ROWS], "fleet"), "<p>%s</p>" % inline(FLEET_HOW_LINE),
         "<h3>Which skills each step uses</h3>", "<p>%s</p>" % inline(SKILLS_INTRO), mm(SKILLS_DIAGRAM), ul(SKILL_CONTROLS), "<p>%s</p>" % inline(SKILL_NOTE),
         "<h3>The five practices</h3>", html_table(FLEET_HEAD, [[inline(c) for c in r] for r in FLEET_ROWS], "fleet"),
         "<h3>LangGraph and LangSmith</h3>", "<p>We did not use them. The agent is plain Python, and each job those tools do has a part here:</p>", ul(LANGGRAPH),
         "<h3>How each run's view is made</h3>", "<p>%s</p>" % inline(RUN_DIAGRAM_TEXT),
         "<h2>7. Models</h2>", ul(MODEL_BULLETS),
         "<h2>8. Limits</h2>", ul(LIMITS_LIST),
         "<h2>9. Next (not built)</h2>", ul(NEXT),
         '<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>'
         '<script>mermaid.initialize({startOnLoad:true,securityLevel:"loose",theme:"default",flowchart:{useMaxWidth:true,htmlLabels:true}});</script></body></html>']
    return "\n".join(h)


if __name__ == "__main__":
    with open(os.path.join(HERE, "architecture.md"), "w", encoding="utf-8") as f:
        f.write(build_md())
    with open(os.path.join(HERE, "architecture.html"), "w", encoding="utf-8") as f:
        f.write(build_html())
    print("wrote architecture.md and architecture.html")

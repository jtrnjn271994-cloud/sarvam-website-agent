#!/usr/bin/env python3
"""Build docs/architecture.md and docs/architecture.html from one source.
Run: python3 -I docs/build_architecture.py
Both files come from the data below, so they cannot disagree."""
import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

TITLE = "Sarvam website agent: architecture"
VERSION = "v10, 16 Nov 2026, as built"

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
"""

FLOW = """flowchart TD
    S["1 Start (person)<br/>page, industry, buyer persona, goal<br/>picked from drop-downs, in the local console or on the website<br/>the goal list changes with the buyer; the first goal is the suggestion"] --> C["2 Capture the page once with Playwright (owner's machine)<br/>keep the hero only: H1, sub-line, main CTA text and link<br/>plus a hero screenshot (desktop) and a saved copy of the page<br/>the rest of the page is stored, never audited<br/>runs never load sarvam.ai again"]
    C --> P{"3 Page set up<br/>and approved?"}
    P -- yes --> L["Load the approved positioning, claims and buyer checklist<br/>(the checklist is optional: it adds questions A7 and A8)"]
    P -- no --> G["Reasoning model (Gemini) drafts the page setup<br/>claims: each tied to a quote found word for word on the saved page<br/>positioning: 12 sections, every bullet sourced and labelled<br/>sources: the saved page and knowledge/ only, cited as KB ids<br/>buyer checklist: questions this buyer asks, tagged hero or page"]
    G --> GC["Rules check the draft<br/>every quote is on the page, every KB id exists,<br/>every number is in its row, the 12-section structure holds<br/>3 tries, then the problems are shown"] --> GP["Owner approves each part<br/>(on the website this needs the owner code)<br/>the approval keeps a hash: an edited file needs a fresh approval"]
    GP --> L
    L --> A["4 AUDIT the live hero: JEV only<br/>A1 names the buyer, A2 states the value, A3 shows proof, A4 says what the button does<br/>A5 carries the positioning promise, A6 beats a rival's hero (only if rival heroes are saved)<br/>A7 answers the buyer's checklist questions, A8 answers the main objection<br/>each answer is a probability, read against pass and fail lines from 60 calibration cases"]
    A --> D{"Gap found?<br/>A1 to A4 fails or holds"}
    D -- no --> N["Stop: report 'no gap'<br/>nothing is written"]
    D -- yes --> H["5 GAP DOSSIER (written out in full)<br/>Gemini writes it; code checks every number, id and quote, 2 fix rounds<br/>what the hero says now, exact text<br/>which buyer question fails and why it matters to this buyer<br/>hypothesis: if we change X for buyer Y, more of them click, because E<br/>what we do not know: no internal analytics<br/>what would prove it wrong"]
    H --> T["6 TEST PLAN<br/>action: one click on the hero's main button<br/>the button must go to the real link for the chosen goal<br/>pass lines, the better-than-baseline rule and the spend cap are saved with the run<br/>(a separate hashed plan file is not built yet)"]
    T --> W["7 WRITER (Opus) drafts 3 hero variants, then edits them<br/>one angle each; every sentence lists the claim id it relies on<br/>told the gaps, the buyer's question, the objection and the positioning promise<br/>told what the live hero already answers: keep it"]
    W --> G1["Gate 1: RULES (code)<br/>claim id exists and its quote is on the page<br/>no banned phrase, no new number or comparison<br/>no third-party model named<br/>the button goes to the real link for the goal<br/>only the hero changes"]:::gate
    G1 -- fail --> R{"Rounds left?<br/>max 2"}
    R -- yes --> W
    R -- no --> X["Variant marked: failed Gate 1<br/>shown with its problems; it can be edited (step 9)"]
    G1 -- pass --> G2["Gate 2: DOUBLE CHECK<br/>JEV + JUDGE 2 (OpenAI decisions), each variant in parallel<br/>G1 the evidence supports the line, G2 no overreach, G3 no banned claim in other words<br/>then A1 to A8 again on the variant<br/>better = average gain of 0.10 or more on the gaps,<br/>and no other question down by more than 0.05"]:::gate
    G2 --> SL["Shortlist: nothing is hidden<br/>passed: both judges say better<br/>held: the judges disagree, or a banned flag that code cannot confirm<br/>failed Gate 2: marked NEAR MISS when only a kept question fell<br/>failed Gate 1: shown, not approvable as it stands"]
    X --> SL
    SL --> PX["8 Apply the words to the saved page<br/>text swap only, layout and styles unchanged<br/>PNG pair: baseline and variant (owner's machine)<br/>website runs take no screenshots: the variant text and its hash are shown"]
    PX --> F["Functional check<br/>the button of each arm points to the real link for the goal"]
    F --> AP["9 HUMAN approval<br/>the person sees each variant, both judges' scores per question,<br/>the dossier, the claim map and the PNG pair<br/>a variant that failed Gate 2 can be approved with a typed reason"]:::gate
    AP -- edit --> E["Edit and re-check<br/>the person changes the H1, sub-line or button,<br/>or writes a note and the writer (Opus) rewrites that one variant<br/>the new version goes through Gate 1 and Gate 2 again<br/>and comes back as a new variant, for example B-edit1"]
    E --> G1
    AP -- reject --> RJ["Variant stays inactive<br/>no exposure"]
    AP -- approve --> SP["10 SANDBOX PLAN, built for this run<br/>visitor groups: this buyer plus the other roles in the industry<br/>reaction strength: how well the goal fits each role<br/>lift: 0.5 x the judges' average gain, at least 2%, at most 50%<br/>visitors per arm: the sample a real test needs<br/>Gemini explains the set-up; code checks every number"]
    SP --> SB["Simulate and check (no model)<br/>Test 1: the expected lift, enough visitors<br/>Test 2: the same lift, too few visitors<br/>Test 3: the page against itself (A/A)<br/>owner's machine: 20 browser sessions per arm on the saved page, outside requests blocked<br/>website: one HTML check per arm, no browser"]
    SB --> FD["11 FINDINGS, built from the data<br/>plain words first, then the set-up<br/>rates with intervals, the sample a real test needs, the limits<br/>all SYNTHETIC<br/>status line: NOT rolled out, rollout needs approval"]
    FD --> DOC["12 Submission and docs, in the console<br/>README, this architecture, the Jev note,<br/>a flow diagram of the run, the tick list for the assignment"]
    classDef gate stroke-width:3px
"""

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
    CAL["calibrate.py: 60 Jev test cases<br/>run separately, not every run"] --> ENG
    E1 ~~~ E2 ~~~ E3 ~~~ E4 ~~~ E5 ~~~ E6 ~~~ E7 ~~~ E8
    P1 ~~~ P2 ~~~ P3 ~~~ P4 ~~~ P5
    K1 ~~~ K2 ~~~ K3 ~~~ K4
"""

QUESTIONS_DIAGRAM = """flowchart TB
    subgraph Q1["1 The hero basics (required)"]
        direction TB
        A1["A1 Does it name the buyer?"]
        A2["A2 Does it state the value?"]
        A3["A3 Does it show proof?"]
        A4["A4 Does it say what the button does?"]
    end
    subgraph Q2["2 Positioning fit (advisory)"]
        direction TB
        A5["A5 Does it carry the positioning promise?"]
        A6["A6 Could a rival print it unchanged?<br/>only when rival heroes are saved"]
    end
    subgraph Q3["3 The buyer's own questions (advisory, per page)"]
        direction TB
        A7["A7 one question per hero item<br/>on the approved buyer checklist"]
        A8["A8 Does it answer the main objection?"]
    end
    subgraph Q4["4 Checks on each variant (Gate 2, both judges)"]
        direction TB
        G1["G1 Does the evidence say what the line says?"]
        G2["G2 Does the line say more than the evidence?"]
        G3["G3 Is it a banned claim in other words?"]
        AA["A1 to A8 again: is it better than the live hero?"]
    end
    Q1 -->|"a fail or hold here is a gap:<br/>only these start a rewrite"| W["Writer"]
    Q2 -.informs the person, never blocks.-> W
    Q3 -.tells the writer what to answer and what to keep.-> W
    W --> Q4
    A1 ~~~ A2 ~~~ A3 ~~~ A4
    A5 ~~~ A6
    A7 ~~~ A8
    G1 ~~~ G2 ~~~ G3 ~~~ AA
"""

DEPLOY = """flowchart LR
    subgraph LOCAL["Owner's machine: the full agent"]
        direction TB
        UI["./run-ui.sh<br/>console on 127.0.0.1:8765"]
        PW["Playwright and Chromium<br/>capture, PNG pairs, 20 browser sessions per arm"]
        ENV[".env: keys, never committed"]
        PG["pages/: runs, approvals, findings"]
        UI --> PW
        UI --> PG
        ENV -.-> UI
    end
    subgraph WEB["Website: sarvam-website-agent.vercel.app"]
        direction TB
        ST["Pages people see<br/>run list, audit, variants, findings, docs"]
        FN["One Python function (app/hosted.py)<br/>start a run, edit, approve, sandbox<br/>one job at a time, up to 5 minutes<br/>no browser: no screenshots, sarvam.ai never loaded"]
        VENV["Vercel settings: the keys<br/>never in a deployed file"]
        ST --> FN
        VENV -.-> FN
    end
    SB[("Supabase (Red Zebra)<br/>sarvam_agent_files: runs, approvals, setup<br/>sarvam_agent_jobs: job log, one-job lock, spend<br/>server key only")]
    OR["OpenRouter<br/>one key, four models"]
    GH["GitHub repo, private<br/>code, rules, knowledge, page packs<br/>no keys"]
    V["Visitor"] --> ST
    O["Owner"] -->|"owner code: page setup"| FN
    FN <--> SB
    FN --> OR
    UI --> OR
    LOCAL -->|"scripts/deploy_live.sh"| WEB
    LOCAL -->|"git push: code only"| GH
"""

GUARDS = [
    "**Spend.** $1.00 cap per run. On the website: $3.00 a day in total and 3 runs a day per visitor. A credit limit on the OpenRouter key is the last line.",
    "**One job at a time.** The local console and the website each run one job at a time. On the website the lock lives in Supabase, so it holds across servers.",
    "**Who may do what.** Anyone may start a run, edit or approve a variant, and run the sandbox. Only the owner (owner code) may draft or approve a page's positioning and claims. Runs made on the owner's machine are read-only on the website.",
    "**No names stored.** An approval on the website records \"a person\". It never stores a visitor's name.",
    "**No bot traffic.** Runs read the saved page. Neither the website nor the sandbox loads sarvam.ai.",
]

MODEL_BULLETS = [
    "**Reasoning model, Google `gemini-3.8-flash`:** page setup drafts, the dossier, the sandbox explanation. It never decides pass or fail.",
    "**Writer, Anthropic `claude-opus-5.5`:** the hero variants, the claim map, and a rewrite when a person asks for one.",
    "**Jev, `typesafe/jev-1.14` (Judge 1):** the audit and Gate 2. It returns probabilities, not reasons.",
    "**Judge 2, OpenAI `gpt-6-luna-decisions`:** Gate 2 only. Two judges from different makers; no judge grades its own maker's writing.",
    "**One OpenRouter key** serves all four. Swap a model in `agent/models.json` or with `MODEL_REASONING`, `MODEL_WRITER`, `MODEL_JUDGE1`, `MODEL_JUDGE2`.",
    "**Cost.** A run costs about $0.25 to $0.55. An edit about $0.05 to $0.15. A sandbox a cent or two.",
]

LATER = DEPLOY   # older name, kept for anything that imports it

QUESTIONS = [
    ("1. The hero basics (required)", "A1 audience, A2 value, A3 proof, A4 CTA",
     "Every buyer page must say who it is for, what the buyer gets, why to believe it and what happens on click. A fail or hold here is a gap, and only these four can start a rewrite."),
    ("2. Positioning fit (advisory)", "A5 positioning, A6 rival swap",
     "A good hero says what this product promises, in words a rival could not print as is. A5 checks the approved promise is there. A6 asks if a rival could reuse the hero unchanged (only when rival heroes are saved). They inform the person but never block."),
    ("3. The buyer's own questions (advisory, per page)", "A7 checklist items, A8 main objection",
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
    ("Jev (Judge 1)", "typesafe/jev-1.14", "OpenRouter Decisions API", "Probabilities only. No text.", "Steps 4, 8, calibration"),
    ("Judge 2", "openai/gpt-6-luna-decisions", "OpenRouter Decisions API", "Probabilities only. No text.", "Step 8, calibration"),
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
    "**What it does.** One run audits the hero of a Sarvam page for one buyer and one goal. It writes better heroes only if the audit finds a gap. A person approves one, or edits one and has it checked again. A sandbox then tests the approved hero against the baseline.",
    "**Where it runs.** On the owner's machine (full agent, with screenshots and browser checks) and on the website, where anyone can start a run. Website runs are saved in Supabase.",
    "**Scope.** The hero only: H1, sub-line and main button. Desktop. Thirteen pages are listed; Voice Agents, Token Factory and Coding Agents have been run.",
    "**Models.** Four makers on one OpenRouter key: Google's Gemini 3.8 Flash reasons, Anthropic's Opus 5.5 writes, and Jev and OpenAI's decision model judge. Code verifies every fact any model writes.",
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
    ("rules/judge-thresholds.json", "Pass and fail lines per question, set by calibration against 60 cases."),
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
    o += ["## 3. The questions Jev asks, and why\n",
          "Jev answers yes/no questions with a probability. It gives no reason. Pass and fail lines come from 60 test cases we wrote (`calibrate.py`). Only the four hero basics can start a rewrite; the others inform the person and the writer.\n",
          "```mermaid\n" + QUESTIONS_DIAGRAM + "```\n"]
    o += ["## 4. Deployment: the owner's machine, the website, Supabase, GitHub\n", "```mermaid\n" + DEPLOY + "```\n"]
    o += ["- " + g for g in GUARDS] + [""]
    o += ["## 5. Models\n"] + ["- " + b for b in MODEL_BULLETS] + [""]
    o += ["## 6. Limits\n"] + ["- " + x for x in LIMITS_LIST]
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
         "<h2>3. The questions Jev asks, and why</h2><p>Jev answers yes/no questions with a probability. It gives no reason. Pass and fail lines come from 60 test cases we wrote (<code>calibrate.py</code>). Only the four hero basics can start a rewrite; the others inform the person and the writer.</p>",
         mm(QUESTIONS_DIAGRAM),
         "<h2>4. Deployment: the owner's machine, the website, Supabase, GitHub</h2>", mm(DEPLOY), ul(GUARDS),
         "<h2>5. Models</h2>", ul(MODEL_BULLETS),
         "<h2>6. Limits</h2>", ul(LIMITS_LIST),
         '<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>'
         '<script>mermaid.initialize({startOnLoad:true,securityLevel:"loose",theme:"default",flowchart:{useMaxWidth:true,htmlLabels:true}});</script></body></html>']
    return "\n".join(h)


if __name__ == "__main__":
    with open(os.path.join(HERE, "architecture.md"), "w", encoding="utf-8") as f:
        f.write(build_md())
    with open(os.path.join(HERE, "architecture.html"), "w", encoding="utf-8") as f:
        f.write(build_html())
    print("wrote architecture.md and architecture.html")

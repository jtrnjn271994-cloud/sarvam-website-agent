#!/usr/bin/env python3
"""Build docs/architecture.md and docs/architecture.html from one source.
Run: python3 -I docs/build_architecture.py
Both files come from the data below, so they cannot disagree."""
import html
import os

HERE = os.path.dirname(os.path.abspath(__file__))

TITLE = "Sarvam website agent: architecture"
VERSION = "v9, 15 Nov 2026, as built (Decisions Log row 41)"

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
    S["1 Start (person)<br/>page, industry, buyer persona, goal<br/>picked from drop-downs in the console"] --> C["2 Capture the page once with Playwright<br/>keep the hero only: H1, sub-line, main CTA text<br/>plus a hero screenshot (desktop)<br/>the rest of the page is stored, never audited"]
    C --> P{"3 Saved positioning<br/>for this page?"}
    P -- yes --> L["Load positioning and approved claims"]
    P -- no --> G["Reasoning model (Gemini) drafts it<br/>with the positioning skills, 12 sections<br/>from the page text and knowledge/ only, labelled PROPOSED"]
    G --> GC["Rules check claim quotes, knowledge ids and numbers"] --> GP["Person approves, once per page"]
    GP --> L
    L --> A["4 AUDIT the hero: JEV only<br/>yes/no questions on the buyer, value, proof, CTA,<br/>positioning, and the buyer's own checklist"]
    A --> D{"Gap found?<br/>a required question fails"}
    D -- no --> N["Stop: report 'no gap'<br/>nothing is written"]
    D -- yes --> H["5 GAP DOSSIER (written out in full)<br/>Gemini writes it, rules check every number and quote<br/>what the hero says now, exact text<br/>which question fails and why it matters to this buyer<br/>hypothesis: if we change X for buyer Y, the click rises, because E<br/>what we do not know: no internal analytics<br/>what would prove it wrong"]
    H --> T["6 TEST PLAN<br/>action: a click on the main CTA, to the real link for the goal<br/>pass bars and rules saved with the run<br/>(a separate hashed plan file is not built yet)"]
    T --> W["7 Writer (Opus) drafts 3 hero variants<br/>each line lists the claim ids it relies on<br/>keeps what the live hero already answers"]
    W --> G1{"Gate 1: RULES<br/>claim id, quote, banned word<br/>only the hero changed<br/>no new number or comparison<br/>CTA goes to a real link for the goal"}
    G1 -- fail --> R{"Rounds left? max 2"}
    R -- yes --> W
    R -- no --> X["Stop: show failures to the person"]
    G1 -- pass --> G2{"Gate 2: DOUBLE CHECK<br/>JEV + JUDGE 2 (OpenAI Decisions)<br/>claim supports the line, no overreach, beats the baseline<br/>disagreement = HOLD; near miss is flagged"}
    G2 -- every variant, with its result --> PX["8 Apply the words to the captured page<br/>text swap only, layout and styles unchanged<br/>screenshot the hero of each arm"]
    PX --> F["Functional check<br/>the CTA of each arm points to the right link"]
    F --> AP{"9 HUMAN approval<br/>PNG side by side: baseline and variant<br/>both judges' scores, the dossier, the claim map<br/>person picks one variant<br/>a Gate 2 failure needs a typed reason"}
    AP -- reject --> RJ["Variant stays inactive<br/>no exposure"]
    AP -- revise --> W
    AP -- approve --> SB["10 Sandbox<br/>simulated visitors: this buyer plus the other roles in the industry<br/>lift set from the judges' scores, visitors from a real-test calculation<br/>Playwright bots click the CTA in each arm on a local copy<br/>3 tests: expected lift, too few visitors, A/A"]
    SB --> FD["11 Findings report built from the data<br/>plain words first, then the set-up<br/>rates, intervals, the sample a real test needs<br/>all SYNTHETIC<br/>status line: NOT rolled out, rollout needs approval"]
    FD --> DOC["12 Submission files<br/>README, architecture note, Jev note,<br/>real versus simulated, limitations"]
"""

LAYERS = """flowchart TB
    subgraph ENG["Layer A: Engine. The code that does the work. It knows no page."]
        E1["probe3.py: the run, one linear flow"]
        E2["capture_hero.py: Playwright capture"]
        E3["gate1.py: rule checks"]
        E4["llm.py: model clients (Gemini, Opus, Jev, OpenAI Decisions)"]
        E5["app/: console and approval page"]
        E6["sandbox_plan.py, sandbox_hero.py: plan, bots, stats"]
        E7["report builder: FINDINGS.md"]
    end
    subgraph POL["Layer B: Policy. The rules every page shares."]
        P1["evidence labels and do-not-claim list"]
        P2["banned-phrase patterns and hero policy"]
        P3["skills: positioning, copy, audit prompts"]
        P4["judge questions, pass bars, goals, positioning structure"]
    end
    subgraph PACK["Layer C: Page pack. The facts about one page, one folder each."]
        K1["saved hero: text and screenshot"]
        K2["claims linked to evidence quotes"]
        K3["buyer checklist and personas"]
        K4["positioning"]
        K5["runs, approvals, findings"]
    end
    PACK --> ENG
    POL --> ENG
    NEW["pages_registry.py --capture<br/>add a page: save its hero once"] --> PACK
    KB["knowledge/: fixed research snapshot<br/>checked rows only, versioned"] -.cited by id.-> PACK
    CAL["calibrate.py: Jev test cases<br/>run separately, not every run"] --> E4
"""

LATER = """flowchart LR
    U["Person"] --> L["Local machine<br/>./run-ui.sh: the full agent<br/>Playwright, model calls, approvals"]
    L --> OR["OpenRouter<br/>one key, four models"]
    L --> X["Static export<br/>finished runs, names removed"]
    X --> V["Vercel<br/>public read-only site"]
    L -->|code only, never the key| GH["GitHub repo, private"]
"""

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
    "**What it does.** One run audits the hero of a Sarvam page for one buyer and one goal. It writes better heroes only if the audit finds a gap. A person approves from side-by-side PNGs. A sandbox then tests the approved hero against the baseline.",
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
    ("Built and tested", "Page setup and approvals, capture, audit, dossier, writer, Gate 1, Gate 2 with two judges, shortlist, human approval, dynamic sandbox, findings, console, read-only export, README, Jev note."),
    ("Partly built", "Step 5 test plan: goal, link, thresholds and rules are saved with the run, but no separate hashed plan file. The Revise button asks for a new run; its note does not reach the writer yet."),
    ("Not built", "Mobile view. A repeated Test 1. Hand-editing a variant before approval. A hashed plan file. COVERAGE.md as a file (the console shows the tick list). Supabase. Deploy to Vercel. Push to GitHub."),
]

WHERE_WORKS = [
    ("Capture with Playwright and Chromium", "Local machine", "Vercel functions cannot run a full browser."),
    ("Model calls (Gemini, Opus, Jev, Judge 2)", "Local machine", "The key lives in `.env` or the environment. It is never in the repo or the export."),
    ("Page setup, approvals, Start a run, Run the sandbox", "Local console", "A person clicks. The console accepts only requests from its own page."),
    ("Reading runs, audits, variants, scores, findings, docs", "Local console or the Vercel read-only copy", "The copy is static files. Approver names become \"a person\"."),
    ("Live runs for other people", "Their own machine, using the README", "A hosted version would need a container host for the browser and a key per user. Not built."),
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
    o = []
    o.append("# %s\n" % TITLE)
    o.append("%s. Written for: the project owner and any reviewer. One document.\n" % VERSION)
    o.append("## 1. The run: audit first, write only if there is a gap\n")
    o.append("```mermaid\n" + FLOW + "```\n")
    o.append("## 2. The three layers\n")
    o.append("- **Layer A, Engine:** the code that does the work. It holds no page names, so one engine serves every page.")
    o.append("- **Layer B, Policy:** the rules every page shares. Change a rule once and it applies to all pages.")
    o.append("- **Layer C, Page pack:** the facts about one page, one folder each. A new page is a new folder.\n")
    o.append("```mermaid\n" + LAYERS + "```\n")
    o.append("## 3. The questions Jev asks, and why\n")
    o.append("Jev answers yes/no questions with a probability. It gives no reason. Pass and fail lines come from 60 test cases we wrote (`calibrate.py`).\n")
    o.append(md_table(["Group", "Questions", "Why we ask them"], QUESTIONS))
    o.append("\n## 4. Deployment\n")
    o.append("```mermaid\n" + LATER + "```\n")
    o.append(md_table(["What", "Where it works", "Why"], WHERE_WORKS))
    o.append("\n## 5. What it uses\n")
    o.append(md_table(["Role", "Model id", "Endpoint", "Returns", "Used in"], MODELS))
    o.append("")
    o += ["- " + n for n in NOTES_MODELS]
    o.append("")
    o.append(md_table(["Tool", "Used for"], TOOLS))
    o.append("")
    o.append(md_table(["Rule file", "Holds"], RULE_FILES))
    o.append("\n## 6. Limits\n")
    o += ["- " + x for x in LIMITS_LIST]
    return "\n".join(o) + "\n"


CSS = """
:root{--bg:#fff;--fg:#1a1d26;--mut:#5b6472;--line:#e3e6ec;--card:#f7f8fb;--acc:#3B5BDB}
@media (prefers-color-scheme:dark){:root{--bg:#14161c;--fg:#e8eaf0;--mut:#9aa3b2;--line:#2a2f3a;--card:#1c1f27;--acc:#8fa6ff}
.chip{color:#111}.mm{background:#f7f8fb}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:40px 20px 80px}
h1{font-size:30px;margin:0 0 4px;letter-spacing:-.01em}
.ver{color:var(--mut);margin:0 0 28px}
h3{font-size:16px;margin:18px 0 4px;color:var(--mut)}
h2{font-size:21px;margin:48px 0 10px;padding-top:8px;border-top:1px solid var(--line)}
p,li{max-width:80ch}
.glance{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px;margin:8px 0 8px}
.glance div{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;font-size:15px}
.legend{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 14px}
.chip{display:inline-block;border:1.5px solid;border-radius:999px;padding:1px 10px;font-size:13px;font-weight:600;color:#1a1d26;white-space:nowrap}
.chip.stop{background:#FDE2E2;border-color:#D14B4B}
.mm{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px;overflow-x:auto;margin:10px 0}
.tw{overflow-x:auto;margin:10px 0}
table{border-collapse:collapse;width:100%;font-size:14.5px}
th{text-align:left;background:var(--card);font-weight:600}
th,td{border:1px solid var(--line);padding:8px 10px;vertical-align:top}
td code,li code,p code{background:var(--card);border-radius:4px;padding:1px 5px;font-size:13px}
.note{background:var(--card);border-left:4px solid var(--acc);border-radius:6px;padding:10px 14px;margin:12px 0;font-size:15px}
.tick td:first-child::before{content:"\\2610\\00a0";color:#8A94A3}
.pill{font-size:12px;border:1px solid var(--line);border-radius:6px;padding:0 6px;color:var(--mut)}
@media(max-width:600px){.wrap{padding:24px 14px}h1{font-size:24px}}
"""


def inline(t):
    """Very small markdown: **bold** and `code`."""
    import re
    t = esc(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return t


def build_html():
    model_rows = [(esc(a), "<code>%s</code>" % esc(b), esc(c), esc(d), esc(e)) for a, b, c, d, e in MODELS]
    q_rows = [("<strong>%s</strong>" % esc(a), esc(b), esc(c)) for a, b, c in QUESTIONS]
    where_rows = [(esc(a), esc(b), inline(c)) for a, b, c in WHERE_WORKS]
    tool_rows = [(esc(a), inline(b)) for a, b in TOOLS]
    rule_rows = [("<code>%s</code>" % esc(a), inline(b)) for a, b in RULE_FILES]
    h = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>Sarvam agent architecture</title><style>%s</style></head><body><div class='wrap'>" % CSS,
         "<h1>%s</h1><p class='ver'>%s. One document.</p>" % (esc(TITLE), esc(VERSION)),
         "<h2>1. The run: audit first, write only if there is a gap</h2><div class='mm'><pre class='mermaid'>%s</pre></div>" % FLOW,
         "<h2>2. The three layers</h2><ul><li><strong>Layer A, Engine:</strong> the code that does the work. It holds no page names, so one engine serves every page.</li>"
         "<li><strong>Layer B, Policy:</strong> the rules every page shares. Change a rule once and it applies to all pages.</li>"
         "<li><strong>Layer C, Page pack:</strong> the facts about one page, one folder each. A new page is a new folder.</li></ul>",
         "<div class='mm'><pre class='mermaid'>%s</pre></div>" % LAYERS,
         "<h2>3. The questions Jev asks, and why</h2><p>Jev answers yes/no questions with a probability. It gives no reason. Pass and fail lines come from 60 test cases we wrote (<code>calibrate.py</code>).</p>",
         html_table(["Group", "Questions", "Why we ask them"], q_rows),
         "<h2>4. Deployment</h2><div class='mm'><pre class='mermaid'>%s</pre></div>" % LATER,
         html_table(["What", "Where it works", "Why"], where_rows),
         "<h2>5. What it uses</h2>", html_table(["Role", "Model id", "Endpoint", "Returns", "Used in"], model_rows),
         "<ul>" + "".join("<li>%s</li>" % inline(n) for n in NOTES_MODELS) + "</ul>",
         html_table(["Tool", "Used for"], tool_rows), html_table(["Rule file", "Holds"], rule_rows),
         "<h2>6. Limits</h2><ul>" + "".join("<li>%s</li>" % inline(x) for x in LIMITS_LIST) + "</ul>",
         '</div><script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script><script>mermaid.initialize({startOnLoad:true,securityLevel:"loose"});</script></body></html>']
    return "\n".join(h)


if __name__ == "__main__":
    with open(os.path.join(HERE, "architecture.md"), "w", encoding="utf-8") as f:
        f.write(build_md())
    with open(os.path.join(HERE, "architecture.html"), "w", encoding="utf-8") as f:
        f.write(build_html())
    print("wrote architecture.md and architecture.html")

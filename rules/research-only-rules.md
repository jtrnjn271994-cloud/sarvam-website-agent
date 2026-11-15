# Research-only rules

Draft, 13 Nov 2026. The user approved these rules on 13 Nov 2026 (rule 16). The agent writes its output from research already in the project. It does not search the web while it drafts.

## Rules

| # | Rule |
|---|---|
| R1 | Draft, design, check and test steps use only project files: library, page research, evidence, claims and decisions. |
| R2 | These steps make no web search, no page fetch, no crawl and no Semrush call. Only the model call itself leaves the machine. |
| R3 | New research runs in its own step that the user starts. The result goes to the inbox, then to the library, with a date. |
| R4 | A model never fills a gap from its own memory. A claim with no evidence id is dropped. |
| R5 | Before each step the agent lists the inputs it needs. It checks each one against the files. |
| R6 | A model prompt says: "Answer only from these files. Say what is missing." |

## Gap report

Every step prints a gap report in one of two forms.

**No gap.** "No gaps found. I checked N inputs." The list of the N inputs follows. A bare "no gaps" is not allowed.

**Gap.** "Research gap. Missing: <input>. Do more research with <skill or command>. Held: <section or claim>." The agent stops that part. It does not guess.

## Old files

If a file is past its `review_by` date, the report lists it as "old, recheck". The agent still uses it, and says so. If nothing changed since the last check, the report says "I could not find any updates."

## Where checks live

The readiness check (`agent/check_page_readiness.py`) already lists missing inputs for a page. The step-level gap report is planned for phase 4 in `run.py`.

## Related

- [Library rules](library-rules.md)
- [Evidence labels](evidence-labels.md)
- [Spend rules](spend-rules.md)

# Model rules

Draft, 13 Nov 2026. This file says which kind of worker does which step. The file `agent/models.json` holds the model for each step. This file does not name models for code.

## Map by step

| Step type | Worker |
|---|---|
| Crawl, copy, checks, registers | Code only. No model. |
| Reading and summaries | Haiku |
| Building, evidence notes, claim notes, default generation | Sonnet |
| Orchestration upgrade and the final audit | Opus |
| Narrow yes/no checks | Jev |

## Rules

1. The default generation model is Sonnet until the Opus audit.
2. Opus audits later. It does not build by default.
3. Jev answers narrow yes/no questions only. See [the rule book](rule-book.md).
4. A skill never hardcodes a model. It says: use the model set for this step in `agent/models.json`.
5. Change a model by editing `agent/models.json`, not a skill.
6. Each model call goes in the run log. See [spend rules](spend-rules.md).

# Test scope rules

Draft, 13 Nov 2026. A test compares a changed page with the baseline page. Every result is SYNTHETIC. It never backs a claim about real buyers.

## Scope values

| Scope | What it compares |
|---|---|
| `page` | The whole new page against the whole baseline page. |
| `section:<name>` | One new section against the same section on the baseline. Other sections stay the same. |
| `action:<cta>` | One call-to-action (CTA) change, such as its words or place, against the baseline. |

## Rules

1. Each run has one scope and one primary action.
2. A `page` test cannot show which section caused a result. Say so in the report.
3. Section-by-section runs are optional. Run them only inside the budget in [spend rules](spend-rules.md).
4. Label every number SYNTHETIC.
5. Decide the number of simulated visitors per arm before the run. Write it in the plan.
6. Do not peek. Do not stop early because a result looks good.
7. Use a fixed seed for assignment, so a rerun gives the same split.

## Result classes

| Class | Meaning |
|---|---|
| clear | The difference passes the rule set before the run. |
| inconclusive | The difference does not pass. Report it as no finding. |

Never write "proved". Write "in this synthetic test".

See also [demo page rules](demo-page-rules.md).

# Spend rules

Draft, 13 Nov 2026. These limits are planned for the agent code. The code is not built yet. The caps will live in `agent/budget.json`. A person may change them.

## Default limits

| Limit | Default |
|---|---|
| Token cap per run (input plus output) | 200000 total |
| Call cap, bets step | 3 |
| Call cap, copy step | 4 |
| Call cap, design step | 4 |
| Call cap, visual review step | 3 |
| Call cap, Jev | 12 |
| Loop limit | 2 rounds |
| Semrush units cap per run | 800 |
| Cache | on by default |

## Rules

1. Run cheap checks (code) before any model call.
2. Read the cache first. Call a model only when the cache has no reply.
3. A dry run prints the plan and a token estimate. It spends nothing.
4. Write one row in the run log for each call. Columns: step, model, tokens in, tokens out, cost estimate.
5. When a cap is hit, stop. Tell the person which cap, and show the run log.
6. Do not raise a cap inside a run. Only a person changes `agent/budget.json`.
7. A fix loop stops after 2 rounds, even if faults remain. List the faults in the report.

## Manual mode

A person who pastes prompts by hand keeps the same limits. Count the rounds yourself and stop at 2.

See also [model rules](model-rules.md).

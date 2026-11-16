# Where Jev fits

Written for: a reviewer who asks why a decision model sits in this workflow.

## What Jev is

Jev is a decision model reached through the OpenRouter decisions endpoint. We send it a short state (the buyer, the positioning promise, the hero text) and a yes/no question. It returns a probability that the answer is yes. It gives no reason.

## Where we use it

1. **Audit of the saved hero (captured 15 Nov 2026).** Questions A1 to A6 and A8 are the same on every page: would the buyer recognise their situation, does it say what they get in plain words, give a checkable proof, say what the button does, carry the positioning promise, beat a rival's hero (only where rival heroes are saved), and answer the buyer's main objection. A7 is added per page, one question for each hero-level item on the approved buyer checklist.
2. **Gate 2, judge 1.** Jev scores each variant on the same questions. A variant counts as better when its average gain on the targeted gaps is at least 0.10 and no other question drops by more than 0.05 (`rules/judge-thresholds.json`).

## What keeps it honest

- **A second judge.** GPT-6 Luna (decisions) scores every variant on the same questions. The shortlist shows both scores. If the two judges disagree, the variant is held for a person, not passed or blocked.
- **Calibration.** 65 cases we wrote (3 held back from tuning) set a pass line and a fail line for each question (`tests/calibration`). The set is small, so the lines are an audit signal, not proof.
- **Code is the hard gate.** Jev never decides a fact. Gate 1 (code) checks claim ids, word-for-word quotes, numbers and banned phrases first. A Jev banned-phrase flag that code cannot confirm holds the variant for a person.
- **A person decides.** Nothing is tested until a person approves a variant. The approval records hashes of the variant and its screenshot.

## What Jev does not do

- It does not write copy and does not explain a score.
- Its score is not evidence of a lift. The sandbox does not use it; the sandbox lift is a typed assumption.
- It was not trained for this task. We treat it as one general decision model among two.

## Where the evidence is

- Questions: `rules/judge-questions.json`
- Bands: `rules/judge-thresholds.json`
- Per-variant scores: the Variants tab, or `probe3.json` in each run folder
- Every call, cost and probability: `run-log.jsonl` in each run folder

# Failure catalogue: step 3a

| # | Failure | Lesson | Seen in | Check |
|---|---|---|---|---|
| 1 | The bets restate the page. They make no position. | L02 | Gap register, steps 2 and 3: "makes three bets, not a position" | Rubric: main claim |
| 2 | A rival can print the claim. India-first lines passed review. | L09 | Context pack section 11; run-04 bets (`runs/2026-11-14-run-04/bets.json`, "why_not_generic" fields) | `swap_test_each_rival`, `jev_swap_test` |
| 3 | Jev said yes to every bet. It did not separate good from bad. | L08 | Run-03 (14 of 14 yes), run-04 (2 of 2 for every bet), foundation audit A8 | Jev canaries |
| 4 | Open conflicts went into copy: two first buyers, two CTA wordings, two GTM statuses. | L12 | Foundation audit A3; context pack sections 1 and 3 | `open_conflicts_listed` |
| 5 | The main button leads nowhere. | L11 | Foundation audit A2; context pack section 10 | Brief field "offer" |
| 6 | An AUDIT note is used as proof. | L17 | `check_claims.py` rule `no_audit_as_evidence` | `evidence_ids_exist`, `labels_valid` |
| 7 | A market signal is read as proof about Sarvam. | L16 | Claims CL-007 to CL-010 are market signals | `claims` |
| 8 | Buyer needs have no buyer voice. All needs are PROPOSED. | L17 | Foundation audit A4 | `labels_valid` |
| 9 | The alternative a buyer named is not read (OpenRouter, Bedrock, Azure, Vertex). | L15 | Gap register, rivals | Rival rows in `rivals.json` |
| 10 | The prompt is a dump. The model got every file and no method. | L02 | Run-04, 112,000-character bets prompt | Input caps in `flow.json` |
| 11 | A banned phrase returns ("sovereign cloud", "best Indic speech accuracy"). | L09 | `pages/token-factory/decisions/do-not-claim.md` | `do_not_claim` |
| 12 | Search findings are not used. Buyers search model names ("deepseek api", 9,900 a month in India), not "token factory" (20). | L14 | Context pack section 12 | Step 1d input |

## What to do instead
- Failure 1: write one main claim first. Then derive the bets from it.
- Failure 4: do not choose. Write each conflict in `self_check.gaps`.
- Failure 6: replace the proof line with a VENDOR or CHECKED line. If none exists, name the gap.
- Failure 9: add the alternative as a row, even when it is UNCHECKED.

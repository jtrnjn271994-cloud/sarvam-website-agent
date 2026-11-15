# Architecture compared: ours, your friend's, and the target flow (15 Nov 2026)

Written for: the project owner, who wants to see the gaps against the assignment flow.
Status: AUDIT. Based on reading the code and running the friend's demo in a scratch copy. Nothing was changed.

## The three shapes

**Ours (`sarvam-positioning-agent`).** A step engine. `flow.json` lists 21 steps. Each step has a handler, a role (code, model or person), a schema and checks. It has a skill loader, a library guard, hashes, a review server with an approve button, and about 15,000 lines of Python. 208 unit tests pass. It is deep. It stops at step 13 (approval). The last five steps are `not_built`.

**Friend's (`sarvam-submission`).** The same agent files, plus one new file, `agent/demo.py` (318 lines). The demo does not use the engine. It copies one saved run (`prebuilt-run`, from 13 Nov), adds an auto-approval, runs the sandbox simulator, and writes a report and an architecture note. It is shallow. It runs to the end in 0.3 seconds.

**Target flow.** The 16-step flow in `fresh-audit-flow-15Nov2026.md`, with your decisions: Jev plus a second judge, one variant to the sandbox, real browser bots.

## Step by step

Status words: **Built** = code exists and tests pass. **Replay** = it shows saved data from an earlier run. **Missing** = nothing exists. **Faked** = the output claims something the code did not do.

| # | Target step | Ours | Friend's | Gap to close |
|---|---|---|---|---|
| 0 | One command starts the whole run | Built, but several commands. Stops at step 13. | Built as a wrapper. Runs to the end on saved data. | Combine: friend's one command, our engine behind it |
| 1 | Start form: page, persona, goal, test type | Built. Test type offers message or design only. No CTA or structure option. | Missing. Fixed brief. | Add the goal list and the three test types |
| 2 | Positioning: reuse or generate | Built. Option B stops: a file is 23,868 characters against a 15,000 cap. | Replay | Split the large file |
| 3 | Capture and local baseline, fidelity check | Built. Playwright capture exists with a fidelity check. | Replay. Images were stripped. | Keep ours |
| 4 | Jev and Judge 2 tag every baseline block | **Missing.** Jev audits copy sections only. No second judge. | **Missing.** | Build in both. This is your core idea. |
| 5 | Gap and hypothesis from the tags | Built, but reads no tags. Run in manual mode. | Replay. Its gap report says "No gaps found." | Rewire to read the tags |
| 6 | Lock the test plan with a hash | Built. The hash is narrow. | Missing. The rule is only stated in the report text. | Widen the hash |
| 7 | Write variants | Built, in manual mode. A live writer is unproven. | Replay of GPT-written variants | Prove one live writer call |
| 8 | Checks: code first, then both judges | Code checks built. Steps 7 and 11 `not_built`. One judge only. | Replay of saved check files. One judge only. | Build step 11 and Judge 2 |
| 9 | Keep the strongest variant that beats the baseline | **Missing** (step 11 `not_built`) | **Missing.** Both variants go on. | Build the scorecard and the pick |
| 10 | Functional flow check in a browser | Partial. A local form opens. No saved browser test. | Missing | Add a Playwright flow test per arm |
| 11 | Approval page: approve, reject, revise | Built. The hash covers 4 files and old unhashed approvals still pass. | **Faked.** The demo writes the approval itself. | Keep ours. Fix the hash. Remove auto-approval. |
| 12 | Sandbox with real browser bots | Simulator only. Step 14 `not_built`. | Simulator, wired. Both variants get the same lift. | Replace with Playwright bots |
| 13 | Findings: rates, intervals, decision | `report.py` exists but nothing calls it | Wired, but the findings text is hard-coded | Build the text from the data |
| 14 | Rollout approval | Missing | A sentence in the report only | Add a step |
| 15 | Submission: README, architecture, Jev note | `submission/` is empty | Files exist. They contain errors. | Fix and keep the friend's |

**Tally of the 16 target steps**
- **Ours:** 8 built, 3 partial or simulator only, 5 missing or not wired.
- **Friend's:** 1 working wrapper, 7 replays, 3 present but wrong (approval, findings text, docs), 5 missing.

## Cross-cutting gaps

| Topic | Ours | Friend's |
|---|---|---|
| Model at runtime | Live Jev calls worked in older runs. Writer was always manual. Not tried live on the current engine. | `--live` flag is ignored. Nothing is live in the demo. |
| Judge independence | One judge (Jev router). Model not pinned. | Same. 4 of 12 saved answers came from `openai/gpt-6-luna`, which also wrote the variants. |
| Jev calibration | 11 of 12 in run-06. jc-03 failed and was never inspected. | Shows 12 of 12 from the saved run-03 file. Different run, same cases. |
| Size and clarity | 15,000 lines. Hard to review. | Same code, still 15,600 lines, with the demo sitting on top. |
| Tests | 208 pass. | None for the demo. |

## What the comparison tells us

1. **Ours has the real engine but no ending.** Friend's has an ending but no engine.
2. **The best shape is friend's front door on our engine.** One command, a run that completes, and our real steps behind it.
3. **Both are missing the same five things:** baseline tagging, Judge 2, the strongest-variant pick, a real browser sandbox and a rollout approval.
4. **Only the friend's version shows the assignment's last two stages end to end.** Those stages are findings and the submission files. Both versions need their text rebuilt from data.

## Recommended build order on `sarvam-submission`

1. Make the demo honest: computed report text, working or removed `--live`, a real approve click, one regression test.
2. Add Judge 2 (OpenAI Decisions, `gpt-6-luna`). Log which model answered every call.
3. Add baseline tagging and rewire the gap step to read the tags.
4. Add the scorecard and the strongest-variant pick.
5. Replace the simulator with Playwright bots. Add the flow check and the rollout approval.
6. Last: live capture and the live writer.

After every stage, `python3 -I agent/demo.py` must still run to the end.

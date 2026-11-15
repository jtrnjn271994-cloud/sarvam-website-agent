# Findings: hero A/B sandbox (SYNTHETIC)

**Every number below comes from a simulation set up from this run's buyer, goal and judge scores, or from a scripted browser. None of it comes from real buyers.**

## In plain words

**Goal chosen:** More developers open the API docs. **What is counted:** a click on the main button that opens the documentation. A visitor who clicks counts as 1; one who does not counts as 0. That is the only thing measured.

**Buyer this run targets:** Technical evaluator (Head of AI; Head of Engineering India; Chief Technology Officer and Managing Director of the India centre) in GCCs & IT services.

**What the tests are.** They check the measuring method. They do not tell you that variant B wins, because its lift is set from the judges' scores by a stated rule, so the simulation can only hand it back with chance noise:
- **Test 1** uses the lift we expect and enough visitors for a real test to see it. A working method says **clear** in most such tests (about 8 or 9 in 10); chance can still give inconclusive.
- **Test 2** uses the same lift with too few visitors. A working method should say **inconclusive**: too little data.
- **Test 3** gives no lift (the page against itself). A working method must say **inconclusive**. If it says clear, the method invents wins.

## How the simulation was set up for this run

In this simulation, the goal is getting more developers to open the API docs, and what is counted is a click on the main button, with an assumed 4.0% base click rate. The simulated visitors come from GCCs & IT services. The run targets the technical evaluator, who makes up 50% of visitors. Because this buyer has a goal fit of 1.0, they react the most with a reaction strength of 1.00. Other visitors, like risk and compliance or economic buyers, have lower goal fits of 0.6 or 0.3, reducing their reaction strengths to 0.30 or 0.15. Goal fit directly alters each group's reaction to the page. To set the lift, Jev posted a +0.20 average gain on targeted gaps while Judge 2 posted +0.28, creating an average of +0.24. Multiplying this by 0.50 established a declared lift of 12%. Crucially, this declared lift is purely an assumption, not an experimental finding.

_Written by reasoning model; code checked that every number is in the plan below._

### Who the simulated visitors are

| Visitor group | Share of visitors | Goal fit | Reaction strength |
|---|---|---|---|
| Technical evaluator (targeted) | 50% | 1.0 | 1.00 |
| Economic buyer (India centre) | 7% | 0.3 | 0.15 |
| Risk and compliance | 7% | 0.6 | 0.30 |
| Procurement | 7% | 0.3 | 0.15 |
| Business owner | 7% | 0.3 | 0.15 |
| Operations user | 7% | 0.3 | 0.15 |
| Champion | 7% | 0.3 | 0.15 |
| Economic buyer (IT services firm) | 7% | 0.3 | 0.15 |

Goal fit: how well the goal suits that role (1.0 best, 0.6 second best, 0.3 otherwise), from `rules/goals.json`. Reaction strength = goal fit x 1.0 for the targeted buyer, x 0.5 for other roles. These are analyst proposals, not research.

### How the lift was set

| Step | Value |
|---|---|
| Jev: average gain on the gaps this variant targets | +0.20 |
| Judge 2: average gain on the gaps this variant targets | +0.28 |
| Average of the two judges | +0.24 |
| Rule: declared lift = 0.50 x average gain, at least 2% and at most 50% | 12.1% |
| Effective lift once every group's reaction strength is applied | 7.1% |
| Visitors per arm a real test needs to see that lift | 77,548 |

**What this means for the run:** the expected lift is large enough to see with a realistic sample (Test 1).

**Derived, not typed:** the visitor groups, their shares and reaction strengths, the lift, and the visitor counts for Tests 1 and 2. **Typed assumptions** (`agent/sandbox_hero.json`): the base click rate (4.00%, not measured on sarvam.ai), the half strength for other roles, the lift rule, and the goal-fit values.

## What was tested

| Arm | H1 | Sub-line | Main button | Goes to |
|---|---|---|---|---|
| Baseline (live, captured 2026-11-15) | Better code in the long run | Coding Agents work across the codebase and saves checkpoints as it goes. The plan stays visible, so you can change direction while the run is live. | Try Coding Agents | https://indus.sarvam.ai/ |
| Variant B | India-centre refactors that test each change and retry from a checkpoint | Coding Agents runs your test suite after each change and saves checkpoints as it goes. If a test fails, it goes back to a checkpoint and tries again. Repositories and run history stay under Indian jurisdiction. | Open the Coding Agents docs | https://docs.sarvam.ai/sarvam-api-docs |

Approved by Claude, on the owner's instruction on 2026-11-15T20:59:38. Group at approval: failed_gate2. Chosen by a person against a Gate 2 result. Reason given: "Owner asked to test the best variant even below the threshold. Both judges agree on B, it gains on the targeted gaps, and the A7 drop is wording."
Test type: hero. The words and the main button change together, so a result cannot be credited to one of them alone (Decisions Log row 28).

## 1. Simulated rates (seeded)

Base click rate 4.00% on the baseline. Seed 20261115. Two-sided two-proportion z test, alpha 0.05. A result counts as clear only with p below alpha and at least 1000 visitors per arm.

| Test | Visitors per arm | Lift we declared | Baseline rate (95% interval) | Variant rate (95% interval) | Difference (95% interval) | p | Result |
|---|---|---|---|---|---|---|---|
| Test 1: the lift we expect, enough visitors | 100,000 | +12.1% | 4.10% (3.98% to 4.22%) | 4.14% (4.01% to 4.26%) | +0.04 pts (-0.14 to +0.21) | 0.6771 | inconclusive |
| Test 2: the same lift, too few visitors | 20,000 | +12.1% | 3.99% (3.73% to 4.27%) | 4.04% (3.78% to 4.32%) | +0.05 pts (-0.33 to +0.43) | 0.7990 | inconclusive |
| Test 3: no difference (control) | 100,000 | +0.0% | 4.06% (3.94% to 4.18%) | 3.97% (3.85% to 4.09%) | -0.09 pts (-0.26 to +0.08) | 0.3161 | inconclusive |

**Test 1 came out inconclusive even though its sample was sized to see this lift.** That can happen: a test sized for 80 to 90 percent power still misses about 1 time in 6 or 10 by chance. It is not a fault in the method. It shows why a small lift can hide in a real test.

Test 3 runs the baseline against itself. It should be inconclusive; if it ever says clear, the test set-up is wrong.

## 2. Browser sessions (local saved page, scripted)

20 sessions per arm on the saved copy of the page. Each session loads the page, checks the hero text, clicks the main button and records where it would go. The click is stopped before it leaves.

| Arm | Sessions | All checks passed | Button would go to |
|---|---|---|---|
| baseline | 20 | 20 | https://indus.sarvam.ai |
| variant | 20 | 20 | https://docs.sarvam.ai/sarvam-api-docs |

Requests to other hosts that the sandbox blocked: 1403 (hosts: assets.sarvam.ai, cdn.claydar.com, connect.facebook.net, googleads.g.doubleclick.net, js-eu1.hs-analytics.net, js-eu1.hs-banner.com, js-eu1.hs-scripts.com, js-eu1.hsadspixel.net, js-eu1.hscollectedforms.net, k.sarvam.ai, snap.licdn.com, static.claydar.com, static.cloudflareinsights.com, www.googletagmanager.com, www.sarvam.ai). Nothing left the machine. The sessions check structure and links, not looks.

## 3. What a real test would need

Base click rate assumed 4.00%. Visitors per arm needed to see a lift reliably (alpha 0.05, power 80%, calculated, not simulated):

| Lift you hope to detect | Visitors per arm | Visitors in both arms |
|---|---|---|
| +50% | 1,861 | 3,722 |
| +25% | 6,743 | 13,486 |
| +10% | 39,473 | 78,946 |
| +5% | 154,302 | 308,604 |

## Limits

- The visitors are simulated. The result does not predict what real buyers do.
- The lift is set from the judges' scores by a rule. It is an assumption. The simulation returns it with chance noise; it does not discover it.
- The browser sessions prove the variant page loads and its button points to the right place. They say nothing about whether people would click.
- The judges (Jev and Judge 2) are general decision models, not trained for this work. Their scores chose the variant to test; they are not evidence of a lift.
- A real test needs live traffic, an agreed sample size and a stopping rule fixed before the start.

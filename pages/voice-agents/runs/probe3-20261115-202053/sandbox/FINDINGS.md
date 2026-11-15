# Findings: hero A/B sandbox (SYNTHETIC)

**Every number below comes from a simulation set up from this run's buyer, goal and judge scores, or from a scripted browser. None of it comes from real buyers.**

## In plain words

**Goal chosen:** More visitors start building (self-serve). **What is counted:** a click on the main button that opens the console (start building). A visitor who clicks counts as 1; one who does not counts as 0. That is the only thing measured.

**Buyer this run targets:** Business owner (Chief Credit Officer; Head of Collections; Chief Credit and Collections Officer) in Banks & lenders.

**What the tests are.** They check the measuring method. They do not tell you that variant B wins, because its lift is set from the judges' scores by a stated rule, so the simulation can only hand it back with chance noise:
- **Test 1** uses the lift we expect and enough visitors for a real test to see it. A working method should say **clear**.
- **Test 2** uses the same lift with too few visitors. A working method should say **inconclusive**: too little data.
- **Test 3** gives no lift (the page against itself). A working method must say **inconclusive**. If it says clear, the method invents wins.

## How the simulation was set up for this run

This simulation models visitors from banks and lenders for the goal to have more visitors start building self-serve. The simulated visitors include business owners, champions, operations users, technical evaluators, economic buyers, procurement, and risk and compliance staff. The business owner is the buyer this run targets, which is why this buyer reacts most, representing 50% of visitors with a 0.30 reaction strength. Goal fit changes each group's reaction to the offer, set at 0.3 for business owners and risk roles, 0.6 for operations and technical evaluators, and 1.0 for champions. To determine the lift, Jev scored an average gain of +0.12 and Judge 2 scored +0.15, producing an average of +0.14. Following the rule where declared lift equals 0.50 times the average gain, declared lift was set at 7%. Crucially, this lift is an assumption, not a finding. Success is measured by counting a click on the main button, assuming a 4.0% base click rate.

_Written by reasoning model; code checked that every number is in the plan below._

### Who the simulated visitors are

| Visitor group | Share of visitors | Goal fit | Reaction strength |
|---|---|---|---|
| Business owner (targeted) | 50% | 0.3 | 0.30 |
| Economic buyer | 7% | 0.3 | 0.15 |
| Operations user | 7% | 0.6 | 0.30 |
| Technical evaluator | 7% | 0.6 | 0.30 |
| Risk and compliance | 7% | 0.3 | 0.15 |
| Risk and compliance (grievance and vendor risk) | 7% | 0.3 | 0.15 |
| Procurement | 7% | 0.3 | 0.15 |
| Champion | 7% | 1.0 | 0.50 |

Goal fit: how well the goal suits that role (1.0 best, 0.6 second best, 0.3 otherwise), from `rules/goals.json`. Reaction strength = goal fit x 1.0 for the targeted buyer, x 0.5 for other roles. These are analyst proposals, not research.

### How the lift was set

| Step | Value |
|---|---|
| Jev: average gain on the gaps this variant targets | +0.12 |
| Judge 2: average gain on the gaps this variant targets | +0.15 |
| Average of the two judges | +0.14 |
| Rule: declared lift = 0.50 x average gain, at least 2% and at most 50% | 6.8% |
| Effective lift once every group's reaction strength is applied | 1.8% |
| Visitors per arm a real test needs to see that lift | 1,104,873 |

**Derived, not typed:** the visitor groups, their shares and reaction strengths, the lift, and the visitor counts for Tests 1 and 2. **Typed assumptions** (`agent/sandbox_hero.json`): the base click rate (4.00%, not measured on sarvam.ai), the half strength for other roles, the lift rule, and the goal-fit values.

## What was tested

| Arm | H1 | Sub-line | Main button | Goes to |
|---|---|---|---|---|
| Baseline (live, captured 2026-11-15) | Voice agents that sound human and deliver results | One platform to build, launch and scale voice agents that carry your customer context into every call and work each conversation toward your business outcomes. | Start building | https://indus.sarvam.ai/agents |
| Variant B | A phone agent for your lending team that updates records during the call | State the goal in plain language and launch it in minutes. You need no complex coding. It connects to your telephony, CRM and databases to fetch details and update records while it talks. | Start building your agent | https://indus.sarvam.ai/agents |

Approved by Console user on 2026-11-15T20:30:49. Group at approval: passed.
Test type: hero. The words and the main button change together, so a result cannot be credited to one of them alone (Decisions Log row 28).

## 1. Simulated rates (seeded)

Base click rate 4.00% on the baseline. Seed 20261115. Two-sided two-proportion z test, alpha 0.05. A result counts as clear only with p below alpha and at least 1000 visitors per arm.

| Test | Visitors per arm | Lift we declared | Baseline rate (95% interval) | Variant rate (95% interval) | Difference (95% interval) | p | Result |
|---|---|---|---|---|---|---|---|
| Test 1: the lift we expect, enough visitors | 100,000 | +6.8% | 4.10% (3.98% to 4.22%) | 3.94% (3.82% to 4.06%) | -0.16 pts (-0.34 to +0.01) | 0.0634 | inconclusive |
| Test 2: the same lift, too few visitors | 20,000 | +6.8% | 3.99% (3.73% to 4.27%) | 3.84% (3.58% to 4.12%) | -0.15 pts (-0.53 to +0.23) | 0.4393 | inconclusive |
| Test 3: no difference (control) | 100,000 | +0.0% | 4.06% (3.94% to 4.18%) | 3.97% (3.85% to 4.09%) | -0.09 pts (-0.26 to +0.08) | 0.3161 | inconclusive |

Test 3 runs the baseline against itself. It should be inconclusive; if it ever says clear, the test set-up is wrong.

## 2. Browser sessions (local saved page, scripted)

20 sessions per arm on the saved copy of the page. Each session loads the page, checks the hero text, clicks the main button and records where it would go. The click is stopped before it leaves.

| Arm | Sessions | All checks passed | Button would go to |
|---|---|---|---|
| baseline | 20 | 20 | https://indus.sarvam.ai/agents |
| variant | 20 | 20 | https://indus.sarvam.ai/agents |

Requests to other hosts that the sandbox blocked: 2166 (hosts: assets.sarvam.ai, cdn.claydar.com, connect.facebook.net, googleads.g.doubleclick.net, js-eu1.hs-analytics.net, js-eu1.hs-banner.com, js-eu1.hs-scripts.com, js-eu1.hsadspixel.net, js-eu1.hscollectedforms.net, k.sarvam.ai, snap.licdn.com, static.claydar.com, static.cloudflareinsights.com, www.googletagmanager.com, www.sarvam.ai). Nothing left the machine. The sessions check structure and links, not looks.

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

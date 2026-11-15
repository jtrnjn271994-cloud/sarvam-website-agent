# Design and distribution rules

Draft, 13 Nov 2026. The user approved these rules on 13 Nov 2026 (rules 14 and 15), with the change to S1 below. They add to [brand rules](brand-rules.md).

## Design rules

Rival pages show what exists. They are not a template.

| # | Rule | Type |
|---|---|---|
| D1 | Do not copy a rival's layout, section order, words, images, icons, colours or slogans. | human review |
| D2 | Use the rival audit to find gaps. A gap is something buyers see on a rival page and not on ours. Fill the gap in Sarvam's own look. | human review |
| D3 | Every colour and font comes from the Sarvam token file. A rival colour or font never enters. | code check (hex and font scan) |
| D4 | A headline or sub-line must fail the swap test. Swap test: could a rival put this line on its page word for word? If yes, reject the line. | Jev yes/no, then human review |
| D5 | The page does not make the same promise as a rival. The rival claims file holds the list of rival promises. | Jev yes/no |
| D6 | A rival name appears in page copy only with an approved comparison claim. The claim needs a CHECKED or CALC evidence id. | code check and human review |
| D7 | No stock look. No generic hero, no filler icons, no unproven numbers in big type. | human review |
| D8 | Design choices from the audit are PROPOSED. Layout facts from rival pages are VENDOR. The design notes say which is which. | code check (labels) |

## Distribution rules

Distribution means how the buyer finds the page and how the page hands the buyer to the next step.

| # | Rule | Type |
|---|---|---|
| S1 | Each page names one primary audience (the key decision-maker), supporting audiences, one main action and one second action. The profile file holds them. The draft is checked first against the primary audience. It is then checked against each supporting audience. | code check |
| S2 | The page states no channel, partner, marketplace or reseller unless an evidence note supports it. | code check (claims) |
| S3 | The page never says where buyers come from, unless a research file says so. | human review |
| S4 | The demo page is not promoted. It has noindex, no ads, no outreach, no sharing to real buyers. | code check and human review |
| S5 | The demo page has no tracking pixel and no form that collects personal data. | code check |
| S6 | The main action leads to a step the buyer can take today. The page must not promise a step that does not exist. | human review |
| S7 | Test traffic is simulated and labelled SYNTHETIC. No real visitor sees a test variant. | code check |
| S8 | The agent never posts, emails or publishes anything outside the project. | human review |

## Notes

- D4 and D5 are the strongest guards against a page that looks like every other inference page. The Jev test asks them as yes/no questions.
- Checks D3, D6, D8, S1, S2, S4, S5 and S7 can run as code. Only D3 and S1 exist in code today. The rest are planned for phase 4.
- The user asked for these on 13 Nov 2026: other designs must not drive ours, and distribution must stay inside what research shows.

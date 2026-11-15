---
name: marketing-plain-writing
description: House writing style for ALL marketing work in the Marketing folder. Use for any marketing task that produces words - copy, posts, LinkedIn, emails, outreach, decks, scripts, video narration, landing pages, battlecards, briefs, reports, research write-ups, artifact text, and replies about that work. Writes in plain controlled English, about 80% of the way to ASD-STE100 (short sentences, active voice, one word one meaning). Apply it before drafting and check the draft against it before handing it over.
origin: .claude/skills/marketing-plain-writing/SKILL.md
author: the user
license: personal, not for redistribution unless the user says so
changed_by_us: no
copied_on: 2026-11-13
---

# Marketing plain writing (ASD-STE100 at about 80%)

The user wants all marketing content in plain controlled English. ASD-STE100 is a controlled language from aerospace maintenance. Use its spirit. Do not enforce the full spec.

## Before you write
1. Name the reader. Write for someone who does not know the topic.
2. Check the brief for audience, goal, channel and brand voice (see AGENTS.md).

## Rules
1. **Short sentences.** About 20 words or fewer for instructions. About 25 or fewer for descriptions.
2. **One idea per sentence.** Split "and... which... because..." chains.
3. **Active voice.** Say who does what. "Sarvam charges Rs 3.50 a minute", not "a rate of Rs 3.50 is charged".
4. **Simple present tense.** Use it where you can. Avoid "would", "could", "might be able to".
5. **One word, one meaning.** Pick one term and keep it. Do not use "customer", "client" and "account" for the same thing.
6. **Plain words.** Use "use", not "leverage". Use "help", not "facilitate". Use "start", not "commence".
7. **Define a hard word once.** Say what a token, an API or a parameter is the first time it appears.
8. **Concrete nouns and numbers.** No "solution", "synergy", "robust", "seamless", "cutting-edge".
9. **Lists and steps for instructions.** One action per step.
10. **No filler.** Cut "very", "really", "in order to", "it is important to note that".

## Keep exact (do not simplify)
- Product names, company names, technical terms the reader needs.
- Numbers, prices, dates and quotes. A quote stays word for word.
- Evidence labels: VERIFIED, VENDOR, INFERENCE, PROPOSED, UNCHECKED.
- Legal, compliance and source wording.

## Do not
- Do not force the full ASD-STE100 word list. It would block needed terms and flatten the brand voice.
- Do not rewrite existing files to match unless the user asks.
- Do not invent facts to make a sentence cleaner. Never invent statistics, testimonials or results.

## Check before you hand over
- Count the longest sentences. Split any over 25 words.
- Search for passive verbs and vague nouns. Fix them.
- Check that one term means one thing throughout.
- Read the first line of each section. A new reader should understand it.

## Example
Before: "Leveraging our robust, end-to-end voice AI solution, enterprises can seamlessly streamline collections workflows, which in turn drives improved recovery outcomes."

After: "Sarvam Voice calls borrowers in their own language. It reminds them of dues and records their reply. Lenders test it on 1,000 calls and set the pass bar themselves."

(The "after" is an illustration of style only. Check every claim against the ledger before you use it.)

## Works with
- `~/Marketing/AGENTS.md` (the always-on rule this skill expands).
- `marketing-team:no-ai-slop` for editing a draft that still sounds machine-made.

# Skill standard

PROPOSED, 14 Nov 2026. This file sets one standard for every skill that a step in `flow.json` names.
A checker (`agent/check_skills.py`, not built yet) tests each rule below. Each rule has an id, so a check message can name it.

## Why this standard exists

- A weak model writes well only when the method is written down. It cannot guess the method.
- The old project skills were thin summaries of other skills. The runs used none of them.
- So a skill has two layers. The core is short and goes into every prompt. The references hold the depth.
- A skill never summarises a source. It copies the source word for word and points to it.

## Which skills the standard covers

- **Named skill:** a folder name in the `skill` field of a step, or in the `scales` list of step 4, in `flow.json`.
- Every named skill must meet this standard.
- A skill that no step names is reported, not failed.
- A copied MIT or personal skill is never a named skill. A project wrapper is the named skill. The copy is reference reading.

## Layer 1: the core (`SKILL.md`)

The code loads the core into every prompt for its step.

**S1. Size.** The core is 200 lines or fewer and 14,000 characters or fewer. Aim for 150 to 200 lines.

**S2. Frontmatter.** The file starts with a block between two lines of three dashes. These keys are compulsory:

| Key | Value |
|---|---|
| `name` | The folder name. |
| `description` | One line. What the skill does. |
| `origin` | "written for this project, <date>" or the source path or URL. A wrapper says "wrapper, written for this project, <date>". |
| `author` | Who wrote the body. |
| `license` | For example "MIT", "Apache-2.0", "personal, project use". |
| `changed_by_us` | `yes` for project text. `no (frontmatter only)` for a copy. |
| `copied_on` | The date in the form YYYY-MM-DD. |
| `step` | The step id or ids in `flow.json`, for example `2` or `[3a, 3b]`. |
| `role` | One of `code`, `reader`, `writer`, `judge`, `person`. It matches the step. |
| `schema` | The schema file of the step output, for example `schemas/insight.schema.json`. |

**S3. Sections.** The core has these level-two headings, in this order, with this exact text:

1. `## Purpose`: two lines. What the step makes and why the next step needs it.
2. `## When this step runs`: the step id, the step before, the step after, and the gate if the step stops.
3. `## Inputs`: one line for each input. Each name matches an `input_pack` name in `flow.json`.
4. `## Method`: numbered steps. One action in each step. Each step cites its source (see S6).
5. `## Output format`: the schema path and one filled JSON example that passes the schema.
6. `## Good example`: one short output and the reason it is good.
7. `## Bad example`: one short output and the reason it fails. Name the check or rule that catches it.
8. `## Checks the code runs after`: the check names from the step in `flow.json`, each with one line.
9. `## What a person decides`: the gate questions, or "nothing" for a step with no stop.
10. `## Sources`: the source table (see S7).

**S4. One decision for each call.** The method asks the model for one decision at a time. A step that needs several decisions makes several calls. Example: step 4 makes one call for each scale.

**S5. JSON only.** The output format is JSON that fits the schema. Each choice has a `reason` of one or two sentences, with evidence ids and a label. Code rejects a reply that does not fit and asks once more.

## Layer 2: the references (`references/`)

The references hold the depth. A step loads only the reference files that its `input_pack` names. It never loads the whole folder.

**R1. Size.** Each reference file is 300 lines or fewer and 15,000 characters or fewer. A file that grows past the cap splits into two files with one job each.

**R2. Standard files.** Each file has one job:

| File | Job |
|---|---|
| `references/rubric.md` | The scored levels. For each criterion it shows what a 1, a 3 and a 5 look like. Jev and the reader use it. |
| `references/examples.md` | At least 3 good outputs and 3 bad outputs. Each bad output names the reason it fails and the check that catches it. |
| `references/failures.md` | The failure catalogue: the mistakes seen in runs 01 to 04 and in `docs/process-gap-register-14Nov2026.md`. Each entry gives the run or file where it was seen. |
| `references/checklist.md` | The yes/no list the model checks before it replies. |
| `references/edge-cases.md` | Inputs that break the method, and what to do: missing data, conflicting sources, a label too weak for a headline. |
| `references/glossary.md` | The terms a reader may not know, one plain line each. |

**R3. Required files.**
- A skill for a `writer` step needs all six standard files. Today these are the skills for steps 2, 3a, 3b and 7.
- Any other skill needs the reference files that its step names with `"required": true`.
- A required file must exist and must not be empty.

**R4. Source copies.** Exact copies of a source skill or method go in `references/source/<source-name>/`. They keep their own folder layout: `SKILL.md`, `references/`, `scripts/`, `templates/` and the licence file.
Source copies are exempt from the R1 caps, because no step loads them whole. A step may name a source file in its `input_pack` only when the file fits the cap.

## The exact source rule

**S6. Cite, do not summarise.**
1. A skill never summarises a source skill or a source method.
2. The source is copied word for word into `references/source/`, with its references, scripts, templates and licence. Only the frontmatter may change, as `skills/PROVENANCE.md` says.
3. A source that already sits in `library/` stays there. The skill names it by its project path. It is not copied twice.
4. A copied MIT skill under `skills/` (for example `skills/cro/`) stays where it is. The wrapper names it by path.
5. Each method step in the core cites its source file and section, for example "(source: `library/method/cortex-guide-text.md`, section 3)".
6. A method step with no source carries the note "project addition:" and one line that says why.

**S7. The Sources section.** It is a table with these columns, in this order:

| File | Origin | Licence | Export |
|---|---|---|---|
| `references/source/flow-break-design/SKILL.md` | `ChatGPT-Skills/skills/flow-break-design/SKILL.md` | personal | no |
| `skills/cro/SKILL.md` | `skills/cro/SKILL.md` | MIT | yes |
| `library/method/cortex-guide-text.md` | `library/method/cortex-guide-text.md` | workshop, private | no |

- **File** is the path of the copy, relative to the skill folder or to the project root.
- **Origin** is the path relative to the Marketing folder, a project path, or a URL.
- A private source (workshop method, personal skill) is used in local runs. It is left out of any public export.
- The wrapper must still work when a private source is absent. The method step then says "source absent: <path>. Use the method steps above only."

**S8. Checksum.** When the origin is on this machine, the copy must match it.
- For a reference file, the bytes match.
- For a copied `SKILL.md`, the body after the frontmatter matches.
- A file over 1.5 MB (for example a contact-sheet image) is not copied. The Sources row says "not copied, over 1.5 MB".

## How a copied MIT skill is used

1. Its body stays untouched in `skills/<name>/`.
2. A project wrapper skill (for example `scale-cro`) holds the core: inputs, method, output format, checks.
3. The wrapper's method cites the MIT skill's sections and its `references/` files by path.
4. A step loads the wrapper core. It loads an MIT reference file only when its `input_pack` names that file.

## What the checker tests

| Rule | Test |
|---|---|
| S1 | Line count and character count of `SKILL.md`. |
| S2 | All ten frontmatter keys are present. `step` names a step in `flow.json`. `schema` names a file in `schemas/`. |
| S3 | The ten headings are present and in order. |
| R1 | Line and character count of each reference file. |
| R3 | Required reference files exist and are not empty. |
| S7 | A `## Sources` table exists. Each project path in it exists. |
| S8 | Each copy matches its origin when the origin exists on this machine. |

A named skill that fails a rule is a FAIL. A skill that no step names is listed as "not named" and does not fail.

## Template

```
---
name: insight-tensions
description: Find tensions between buyer words, rival claims and our proof.
origin: written for this project, 2026-11-15
author: project builder
license: personal, project use
changed_by_us: yes
copied_on: 2026-11-15
step: 2
role: writer
schema: schemas/insight.schema.json
---

# Insight tensions

## Purpose
## When this step runs
## Inputs
## Method
## Output format
## Good example
## Bad example
## Checks the code runs after
## What a person decides
## Sources
```

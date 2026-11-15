# Library rules

Draft, 13 Nov 2026. These rules cover everything in `../library/`.

## Copies

1. A copy is verbatim. Nobody edits it.
2. When a source file changes, make a new dated copy. Mark the old row superseded. Keep the old copy.
3. Live numbers get dated copies. A copy of a price or a rival page shows its date.
4. The stamp lives in the register. It never lives inside the copy.
5. A copy keeps its original file name. Its folder name uses kebab-case.

## Review intervals

| Kind of file | Review every |
|---|---|
| Rival page and rival claim files | 30 days |
| Price and pricing files | 90 days |
| Research notes and ledgers | 180 days |
| Method files and transcripts | 365 days |
| Superseded copies | none |

The register holds two dates for each file: `last_checked` and `review_by`. The `review_by` date is `updated` plus the interval. When the class is a guess, the row uses 180 days and the notes column says so.

A file past its `review_by` date is stale. The agent says so when it uses it. See [DATED-CHECK.md](../library/DATED-CHECK.md).

## Using the library

1. Answer only from these files. Say what is missing.
2. Nothing in the library is evidence on its own. A file becomes evidence when an Evidence note cites it with a label. See `evidence-labels.md`.
3. Tier 3 files are AUDIT. They are leads. They are never evidence.

## Export

A library copy with export set to "no" never goes to GitHub. This covers GPT output, Semrush data, workshop material, transcripts and any file with an unknown licence.

## Approval

Nothing deploys or publishes without the user's approval.

See also: `stamp-format.md`, `inbox-rules.md`, `rule-book.md`.

# Stamp format

Draft, 13 Nov 2026. Every library file has one row in `../library/library-register.csv`. The row is its stamp. Nobody writes the stamp inside the file.

## Columns

| Column | Meaning | Required |
|---|---|---|
| id | `LIB-001` upward. One id per file. Never reused. | yes |
| title | The first heading of the file, or the file name. | yes |
| type | evidence, research, ledger, data, method, audit, transcript or positioning. | yes |
| tier | 1 = checked by a rule (ledger files, quote ledgers). 2 = our research notes. 3 = GPT or third-party output (AUDIT). | yes |
| owner | Who made it: user, claude, gpt or unknown. Use unknown when unsure. | yes |
| updated | File modified date, YYYY-MM-DD. | yes |
| source | How it was made: ledger, claude research, gpt audit, workshop, third-party transcript and so on. | yes |
| origin_path | Where the file came from. Relative to the Marketing folder. Never starts with a slash. | yes |
| library_path | Where the copy lives. Relative to the project folder. | yes |
| data_as_of | A date the file states inside itself. Empty if none. | no |
| status | current, superseded, withdrawn or unread. Use unread for any file nobody opened. Do not guess. | yes |
| export | yes or no. Yes only for our own checked ledgers and our own research notes. | yes |
| relevance | token-factory, brand, cross-page or method. | yes |
| sha256 | Hash of the library file. | yes |
| size_bytes | Size of the library file in bytes. | yes |
| last_checked | The date the copy last passed the hash check, YYYY-MM-DD. Set by `check_library.py --stamp-checked` or by the pull script. | no |
| review_by | The date a person must review the file again, YYYY-MM-DD. It is `updated` plus the review interval. Use `none` for a superseded row. | yes |
| notes | A short note. Write the guess here when the interval class is a guess. | no |

## Special rows

- A row with "in place, not copied" in `source` points to a file that stays in its project folder. `library_path` is that file.
- A row with "machine text copy of PDF" in `source` is a text version of a PDF. Its `origin_path` is the PDF. The check does not compare hashes for it.
- A row with "added by the person" at the start of `source` is a resource the person added with `python3 -I agent/start.py --page <slug> --add-resource --file <path> [--product <p>] [--industry <i>] [--category <c>]`. This is the only way anything is written to the library after the pull. The file lives in `library/added-by-person/<page>/`. `source` reads "added by the person (<local path or pasted text>) on <date>". `origin_path` is "local file: <file name>" or "pasted text". No absolute path is stored. The tags the person gave sit at the end of `source` ("; covers product: ...; industry: ...; category: ..."). `owner` is user, `tier` is 2, `status` is unread, `export` is no, `review_by` is 180 days after the date, and `notes` is "label UNCHECKED". Its evidence label is UNCHECKED: a run may use it as a guide and never as proof. The check does not look for its origin file. Nothing is fetched from a web address.
- A row whose `source` starts "owner-approved positioning" was restamped by the owner with `python3 -I agent/start.py --restamp <LIB-id> --owner user --tier 2 --reason "<text>"`. Only positioning or research rows may be restamped. Audit-type rows, rows owned by gpt that are not positioning, and the ids named in `rules/library-tags.json` under restamp are refused. The action rewrites only the owner, tier and source of that one row. It puts the old owner, tier and source, the date and the reason in `notes`. The check accepts the row only when `notes` holds "restamped <date>: was owner=..., tier=..., source=...". The file, its hash, its type and its origin do not change. It is still not proof: a positioning file is an input, never evidence.
- Files that do not exist in the library, such as the register itself, `INDEX.md`, `CHANGES.log` and the folder README files, have no row.

## Check

Run `python3 -I agent/check_library.py` from the project folder. It reads the register and reports errors and drift.

Run it with `--dated` for the review dates. See [DATED-CHECK.md](../library/DATED-CHECK.md).

# Inbox rules

Draft, 13 Nov 2026.

## One inbox

New files go to `../inbox/`. This is the one project inbox.

Pages have no inbox of their own. The old page inbox is gone.

## Filing

1. A script files each new item into `../library/inbox-filed/<date>/`.
2. The script adds a row to `../library/library-register.csv`.
3. The script adds one line to `../library/CHANGES.log`.
4. The copy stays verbatim. See `library-rules.md`.

Run `python3 -I agent/pull.py --inbox` to file the items. The script also moves each original into `../inbox/filed/<date>/`. It writes the register row with status unread. A person sets the real status later.

## Age

A file that stays in the inbox for more than one day goes in the morning note.

## Never in the inbox

Keys, passwords and `.env` files. Keep them out of every project folder.

See also: `stamp-format.md`, `rule-book.md`.

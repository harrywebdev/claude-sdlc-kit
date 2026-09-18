---
description: Files a ticket in the project backlog (BACKLOG.md) — work that is not being done now
argument-hint: <what should be done | nothing = take it from the conversation>
---

File a ticket in the project's backlog. Follow the format and the rules of the **`backlog`
skill** — it is the single source of truth for the file, the fields and the numbering. Load it
before writing anything.

## What goes into the ticket

- **With an argument** — that is the subject. Do not extend it with anything the user did not
  say.
- **Without an argument** — take the subject from what was just discussed: the finding you hit,
  the thing the user waved off as "later", what a reviewer marked as out of scope. Name it in
  one sentence and **have it confirmed** before writing. If there is nothing in the conversation
  to reach for, ask what to file — do not invent a ticket.

## Steps

1. **Find the backlog.** `BACKLOG.md` in the repository root. If the project has a different live
   tracker (Jira, GitHub Issues, `TODO.md`), use that one and say so instead of creating a second
   file. **If no backlog exists, do not create one** — say the ticket in one sentence the way you
   would have written it, point at `/feature:backlog-init`, and stop. Setting a backlog up is the
   user's decision; this command only files into one that is already there.
2. **Check for a duplicate first.** Read the existing tickets. If the item is already there,
   **extend that ticket** — a second one about the same thing turns a backlog into noise.
3. **Verify the claim against the code** before describing an impact. A ticket built on an
   assumption about code you did not open wastes the time of whoever picks it up.
4. **Write the ticket**: the number from the `<!-- last-id: BL-N -->` marker plus one, a title
   that says what is wrong or missing, the area, the **impact** (what breaks if nobody does it),
   and a verifiable `Done when`. Add `Watch out` only if you know of a trap.
5. **Place it in a priority section** by impact, and raise the `last-id` marker.
6. **Do not commit.** Tell the user in two lines what you filed and where it landed — the ticket
   is a change to the working tree like any other and it is theirs to commit. If the tree is on a
   feature branch mid-workflow, say that the file will show up in that diff.

## Rules

- Whatever `/feature:backlog-add` gets asked for it files — but if it is genuinely a two-minute fix and
  the user is standing right there, say so in one sentence. They may want it now rather than in
  the backlog.
- **Never create the backlog file.** That belongs to `/feature:backlog-init` alone.
- **Never** file what is part of the current task instead of doing it.
- Touch no ticket other than the one you are filing (or extending).

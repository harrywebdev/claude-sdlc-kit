---
description: Maintenance of the project backlog — verifies tickets against the real code, proposes deleting what is done, merging duplicates and fixing what cannot be picked up
argument-hint: [BL-<n> ... | nothing = the whole backlog]
---

Go through the backlog and confront it with the state of the repository. A backlog nobody prunes
fills up with tickets that were finished long ago, and then nobody reads it. The format of the
file is described by the **`backlog` skill**.

With an argument, groom only the listed tickets. Without one, all of them.

## Steps

### 1. Read and verify

Read `BACKLOG.md` and for each ticket **check the actual code** — read the files it names, search
for the symbols, look at `git log` for the area. Decide on evidence, never on a guess about how
it probably turned out. For each ticket, one verdict:

- **done** — the `Done when` condition is met in the current code. Say what proves it (a file, a
  commit, a symbol).
- **duplicate** — it overlaps another ticket. Name which one and what the merged one should say.
- **stale** — the code it was about is gone, or the problem no longer exists for another reason.
- **unpickable** — it has no impact stated, or the `Done when` cannot be verified. It needs a
  rewrite, not deletion; propose the wording.
- **wrong priority** — the impact does not match the section it sits in. Propose the move and
  state what changed.
- **ok** — leave it alone.

Tickets with a `Branch` line: check whether the branch exists. Gone plus the condition met means
**done**; gone with the condition unmet means an abandoned attempt — propose clearing the line.

### 2. Present it and wait

Show a table — ticket · verdict · one line of reasoning — and **ask for approval before changing
anything**. `AskUserQuestion`, the default being to apply everything you propose; the second
option applies only the deletions of finished tickets; the third leaves the file untouched.
Anything you are not sure about goes into the table as **ok** with a note, not as a deletion.

### 3. Apply

Only what was approved:

- delete finished and stale tickets (finished tickets are deleted, not archived)
- merge duplicates into one ticket, deleting the other
- rewrite unpickable ones and move mispriced ones
- **never lower the `<!-- last-id: BL-N -->` marker**, even when the highest ticket disappears —
  numbers are not recycled

Then say in three lines what changed and how many tickets are left. **Do not commit** — leave the
file in the working tree for the user.

## Rules

- **Never delete a ticket you have not verified in the code.** "It is probably done" is not a
  verdict.
- Do not rewrite the wording of tickets that are fine. This is maintenance, not an editorial pass.
- Do not file new tickets here. Anything you discover while grooming goes through `/feature:backlog-add`
  and only after you have told the user.

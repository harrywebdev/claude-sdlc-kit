---
name: backlog
description: Keeps work that is not being done now in the project's versioned BACKLOG.md — both a finding you hit outside the current task and a feature you intend to build later. Use when you run into a previous bug, stale documentation, a weakness, debt or an idea that does not belong in the current task — and whenever you catch yourself asking "should I fix this, or leave it?". Also on requests like "file a ticket", "add it to the backlog", "what is left to do", "go through the backlog".
metadata:
  version: 1.0.0
---

# Backlog

One versioned file per project holding **what is not being done now**. It covers two kinds of
ticket that behave the same way once written down:

- **A finding** — you were working on task A and hit problem B. Without a backlog there are only
  two bad moves: fix it in an unrelated branch (and grow the diff by something nobody asked for
  and nobody reviewed), or mention it in the reply and watch it die with the conversation.
- **Planned work** — something you intend to build, just not today. It waits here until
  `/feature:start BL-<n>` picks it up.

The third option, for both: **write it down and move on.**

## When to write

Write when the item is **outside the current task** and it would be a shame to lose it:

- an earlier bug or weakness you ran into along the way
- documentation that no longer matches the code
- debt that got in your way (dead code, duplication, a missing guard)
- an idea or a feature that deserves a decision of its own
- something outside the code — infrastructure, content, a third-party account

**Do not write** what is part of the current task (do that instead), what is purely about this
conversation ("still need to check it went through"), or what is already in the backlog — extend
the existing ticket rather than duplicating it.

**Do not write instead of fixing when the fix is the task.** The backlog is not where requested
work gets parked.

## Where

1. **`BACKLOG.md` in the repository root.** It must be **versioned** — a backlog a fresh clone
   does not know about is just a private note. Watch out for projects with the whole `.claude/`
   in `.gitignore`: there the file does **not** belong in `.claude/` unless an exception is added.
2. If the file does not exist, **create it** with the header and the three priority sections
   (see below).
3. If the project has its own `CLAUDE.md`, **add a paragraph** saying tickets go here — otherwise
   the next agent will not see the convention.
4. If the project already has a live tracker (Jira, GitHub Issues, `TODO.md`, an older
   `serviceDesk.md`), **use that one** and do not create this file — keep its filename, its
   section layout and its **existing ID prefix** (`SD-18` stays `SD-`), because renaming it would
   orphan every ticket already in it and every reference to one. Everything below then applies to
   that file. Ask when you are not sure which tracker is actually alive.

## The file

```markdown
# Backlog

Work that is not being done now. Priority is the order of the sections; finished tickets are
deleted. A ticket is picked up with `/feature:start BL-<n>`.

## High priority

### BL-3 — Monitor: switch polling to SSE
**Area:** performance · plugins/claude-monitor/tools/claude_monitor.py

The dashboard polls once a second even when nothing happens — with 8 open sessions it keeps
the CPU busy and the fan on. It grows linearly with the number of sessions.

**Done when:** the dashboard updates without polling and idle CPU stays under 1 %

## Medium priority

### BL-4 — ...

## Low priority

<!-- last-id: BL-4 -->
```

Two optional lines, only when they carry something:

- `**Watch out:** <a known trap — what this change invalidates elsewhere>` — write it into the
  ticket the moment you know it. That is where it gets looked for, not in a conversation log.
- `**Branch:** feature/BL-3-monitor-sse` — added by `/feature:start` when it picks the ticket
  up, so an open ticket does not look untouched.

**Write the file in the language the repo uses** (its commits, its README) — headings, fields and
text alike. The ID prefix `BL-` and the `<!-- last-id: BL-N -->` marker stay as they are in any
language: they are read by machine.

## Rules for a ticket

- **Priority is the position of the section**, not a field. Moving a ticket between sections is
  how priority changes.
- **One ticket is one thing** that can be closed. "Go through security" is not a ticket.
- **Always state the impact** — what breaks, or what is lost, if nobody does it. A ticket that
  only describes a state ("this function is long") never gets opened. One that says what goes
  wrong does.
- **`Done when` is a verifiable condition**, not a restatement of the title. Not "fix X" but the
  state in which it is fixed.
- **The file holds open items only.** A finished ticket is **deleted**, not archived — what was
  done is in the git history, and a backlog you have to dig through an archive to read is a
  backlog nobody reads.
- **Numbers are never recycled.** Because finished tickets are deleted, the highest number in the
  file is not enough — keep the `<!-- last-id: BL-N -->` marker at the end and raise it after
  every addition.

## Rules of conduct

- **Writing to the backlog does not replace telling the user.** Always say what you found and
  that you filed it. They may well decide they want it now.
- **Do not change other people's priorities** unasked. File new ones where their impact puts them.
- **Do not close a ticket you have not verified.** Only something that meets its own
  `Done when` belongs in "done".
- On "what is left" or "go through the backlog", **read the file and summarize it** by priority —
  do not recite it verbatim.

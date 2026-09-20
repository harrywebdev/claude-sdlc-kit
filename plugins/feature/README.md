# feature

A workflow for taking one feature from the task to the PR, plus the backlog it draws from.
One namespace, no state file and no tracking of its own — you see the progress in the terminal
and the subagents in [claude-monitor](../claude-monitor).

| Command | What it does |
|---|---|
| `/feature:start <issue key \| URL \| BL-<n> \| description> [--fast\|--full]` | the whole run: task → branch → plan → implementation → E2E → lint → review → fixes → docs → consultation → commit & PR. Which of the checking steps actually run is decided at the plan gate |
| `/feature:plan-review [path to plan]` | adversarial review of the plan against the real code, before anything gets written |
| `/feature:commit` | git commit, no emoji and no Co-Authored-By, in the language of the repo's history |
| `/feature:wiki [--scope=full\|incremental]` | the project wiki in `docs/wiki/` following the LLM-wiki pattern — discovers the stack itself |
| `/feature:backlog-add <what should be done>` | files a ticket in `BACKLOG.md` — work that is not being done now |
| `/feature:backlog-list [filter]` | overview of the backlog by priority, what is in progress, what to pick up next |
| `/feature:backlog-groom [BL-<n> ...]` | confronts the tickets with the real code: what is done, duplicated, stale or unpickable |

`/feature:start` calls `/feature:commit` and `/feature:wiki` itself (the wiki through the
doc-writer); you run them standalone when the workflow is not running.

## The backlog

For a project without Jira — and for everything that would otherwise be lost in the reply. The
`backlog` **skill** holds the format and triggers on its own the moment you hit something outside
the current task ("should I fix this, or leave it?"); the three commands are the manual way in.

Everything lives in a single **`BACKLOG.md` in the repository root**, versioned, because a backlog
a fresh clone does not know about is a private note. Priority is the **order of the sections**,
not a field. A ticket is one closeable thing and always states its **impact** — what breaks if
nobody does it — plus a verifiable `Done when`. Finished tickets are **deleted**, not archived;
the history is in git, and a `<!-- last-id: BL-N -->` marker at the end of the file keeps numbers
from being recycled.

The loop closes with `/feature:start`: `BL-7` is a fourth kind of argument next to an issue key,
a URL and a description. The workflow reads the ticket, makes its `Done when` the acceptance
criterion for the plan and the E2E, writes the branch back into the ticket, and deletes it in
step 12 — but only once the condition is really met. In the other direction, whatever the review
throws out as out of scope in step 8 goes through `/feature:backlog-add` instead of into the consultation,
where it would die with the conversation.

If the project already has a live tracker (Jira, GitHub Issues, `TODO.md`), the skill uses that
one and does not create a second file.

## How the context is split

The **main agent** holds the core of the workflow, because it needs one thread from the task
to the code:

| Step | Where it runs |
|---|---|
| 1 Task · 2 Branch | main context |
| 3 Plan — drafting and folding in findings | main context |
| 3 Plan — review | `feature:plan-reviewer` (clean context) |
| 4 Implementation | main context |
| 5 E2E | `feature:e2e-tester` (clean context) |
| 6 Lint & format | `feature:linter` (clean context) |
| 7 Code review | `feature:reviewer` (clean context) |
| 8 Fixing findings | main context |
| 9 Documentation | `feature:doc-writer` (clean context) |
| 10 Security | `feature:security-reviewer` (clean context, sees the docs too) |
| 11 Consultation · 12 Commit & PR | main context |

E2E is a subagent for the same reason the reviewers are: the author tests the path they
happened to build, somebody who did not write the code tests the path the user walks. It gets
the task — without it there is nothing to test — but not a word about how the code came about.
And it writes **tests, not source**: a bug it uncovers goes back to the author, exactly as a
reviewer's finding does. The runner's output, which is the second longest thing in the whole
workflow, stays with it.

Mechanical cleanup is a subagent for the same reason, even though it judges nothing: the output
of the formatter, the linter and the typechecker is the longest and least interesting thing in
the entire workflow. Which is why it does not get the task at all — you can lint without knowing
the intent.

Security is deliberately the **last step**, not parallel to the code review: only after the
documentation is the diff complete, and docs are a full security surface — an example with a
token, an internal URL, or an instruction that has the reader turn verification off is a finding
just as much as a hole in the code.

The checking agents get **at most the task, the branch and the diff** — never the course of
development. They do not know what you weighed, what you discarded or what the user already
approved, so they have nothing to latch onto and their findings carry weight. `feature:linter`
and `feature:security-reviewer` do not even get the task: cleanup does not need it, and a
security review must have nothing available to talk it into believing a hole is the design. The
reviewers also lack `Edit`: they hand findings back, and the main agent, which knows the code,
fixes them. The doc-writer may write (documentation is work, not a fix) but does not commit.

On a second round (the user has comments) the agents are launched **from scratch again**, not as
a continuation — otherwise they would pull the context back in.

A command carries the **recipe**, an agent is a **context boundary** — they are not competing
options. That is why `/feature:wiki` is a command: a person runs it directly (and it runs in
their context), while from the workflow `feature:doc-writer` calls it, so the work lands in its
window instead. Which is also why the doc-writer has `Agent` — so phase B can spawn its discovery
subagents.

## The agents

| Agent | Context | Tools | Output |
|---|---|---|---|
| `feature:plan-reviewer` | task, plan | read-only | verdict + Blocking/Should-fix findings against the real code |
| `feature:e2e-tester` | task, diff | + Write/Edit | PASS/FAIL/SKIPPED + what it wrote, findings when red |
| `feature:linter` | branch + diff only | + Edit | what the formatter/lint/typecheck fixed and what is left for the author |
| `feature:reviewer` | task, plan, diff | read-only + Skill | PASS/CHANGES verdict + findings by severity |
| `feature:security-reviewer` | branch + diff only (code **and** docs) | read-only + Skill | verdict + findings with a path to exploitation |
| `feature:doc-writer` | task, diff | + Write/Edit | what it wrote, what it did not and why, wiki status |

Every one of them opens its report with a `VERDICT:` line — `PASS | CHANGES` for the three
reviewers, `CLEAN | HANDBACK` for the linter, `WRITTEN | NOTHING` for the doc-writer, optionally
with a short summary after an em dash. The rest of the report stays prose written for a human;
that one line is what the main agent reads first to know whether the step is closed. Nothing
depends on it — where nobody reads it, it costs one line.

## The workflows

The three reviews — plan, code and security — do not run as a single agent but as a **`Workflow`**:
the same agent over three lenses at once (for the code review: bugs · simplify · scope against the
plan), and every serious finding then has to survive an independent verifier that is told to refute
it. What reaches the main context is the merged, deduplicated remainder. A small diff still gets a
single agent — the fan-out is for changes where one reviewer's one angle is a real risk.

| Script | Name | Lenses | Called from |
|---|---|---|---|
| `workflows/plan-review.js` | `feature:plan-review` | step order · reuse · edge cases | `/feature:plan-review`, step 3 |
| `workflows/code-review.js` | `feature:code-review` | bugs · simplify · scope | step 7 |
| `workflows/security-review.js` | `feature:security-review` | input & access · exposure · docs | step 10 |

They are plain scripts in the plugin's `workflows/` directory, which Claude Code loads on startup —
**the file has to end in `.js`** (a plugin's loader takes nothing else) and the name it registers is
`<plugin>:<meta.name>`. The commands only pass `args` and never retype the orchestration. The whole
prompt for the reviewers is `args.brief`, which is what keeps context isolation a property of the caller: the script hands on
what it is given and adds only the lens.

## The composition of steps

A typo and a new endpoint do not deserve the same workflow, so the set of steps is not fixed.
Together with the reviewed plan, `/feature:start` proposes at the **gate in step 3** which of
the checking steps will run — a table of step · run/skip · reason — and the user approves the
plan and the composition in **one click on the proposal**. The full track is the second option,
and only the third one ("adjust the steps") opens a checkbox list of the four optional steps,
where what is ticked runs. The dialog cannot come pre-ticked, so the pre-filled answer is the
first option, not a checked box.

Up for the composition are **E2E, code review, documentation and security**. The task, the
branch, the plan **including its review**, the implementation, lint, the consultation and the
commit always run. `--fast` and `--full` only pre-set the proposal; the confirmation still
happens at the gate.

A step is never dropped when the change touches authentication, authorization or permissions,
secrets, credentials or crypto, untrusted input, file upload, a new or changed endpoint,
dependencies, migrations, payments, or CI/CD and release scripts — with `--fast` the workflow
names the disqualifier and asks instead of obeying. And because the composition is proposed over
the plan rather than the diff, it gets re-checked once the code is written: a change that came
out bigger than planned gets the dropped steps back, which needs no approval — only dropping
one does.

## The gates that wait for you

The task, the **reviewed** plan together with the composition of steps, the consultation,
commit & push. Without explicit approval the workflow does not commit, does not push and does
not create a PR (the PR is only generated as a link — `gh` is not used).

## What it discovers, and what it does not

`/feature:start` reads the project rather than assuming it: the base branch (`develop` if the
repo has one, otherwise the default branch), the e2e/lint/typecheck commands from the manifests
that are actually there, the branch naming convention from the history, and the issue detail
through an Atlassian MCP server if one is configured. Where it finds nothing, it skips the step
and says so.

`/feature:wiki` is stack-neutral the same way — it works out the language, build, tests and the
shape of the repo from the manifests and `git ls-files`, decides the page set from what the
project actually has, and does not create a page with no content. It holds the three layers of
the LLM-wiki pattern: code is the raw source (it never writes into it), `docs/wiki/**` is its
own, and `CLAUDE.md`/`AGENTS.md`/`README.md` is the schema it obeys. `index.md` is the catalog,
`log.md` an append-only history, and `--scope=incremental` rewrites only the pages touched by
the diff since the last entry in the log.

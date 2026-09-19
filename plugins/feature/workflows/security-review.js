export const meta = {
  name: 'security-review',
  description: 'Security review of a feature branch diff through three lenses, every serious finding checked for a real path to exploitation',
  whenToUse: 'Run by step 10 of /feature:start, after documentation. args: {brief, baseBranch, branch} — brief holds only the branches, never the task.',
  phases: [
    { title: 'Review', detail: 'feature:security-reviewer over three lenses at once' },
    { title: 'Verify', detail: 'an independent agent builds the path to exploitation for every critical and high' },
  ],
}

const LENSES = [
  ['input', 'Untrusted input and access: validation and escaping, SQL/command/template injection, authentication and authorization, missing ownership checks, IDOR, roles.'],
  ['exposure', 'What leaks out: secrets in code, logs, error messages or the commit itself, data in API responses beyond what is intended, dependencies added in the diff, path traversal, uploads.'],
  ['docs', 'Documentation in the diff (*.md, README, docs, wiki, comments in config samples): real secrets in examples, internal addresses and account names, a procedure that walks the reader into something unsafe, a missing step without which the result is insecure, a description promising more security than the code delivers.'],
]

const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          finding: { type: 'string', description: 'the finding as the report states it, one line' },
          refuted: { type: 'boolean', description: 'true = no path to exploitation can be built, so it is info, not a vulnerability' },
          why: { type: 'string', description: 'the path to exploitation, or where building it breaks down' },
        },
        required: ['finding', 'refuted', 'why'],
      },
    },
  },
  required: ['verdicts'],
}

const out = await pipeline(
  LENSES,
  ([key, lens]) =>
    agent(`${args.brief}\n\nYour lens for this review: ${lens}`, {
      agentType: 'feature:security-reviewer',
      label: `security:${key}`,
      phase: 'Review',
    }),
  (report, [key]) =>
    report &&
    agent(
      `A security report on the diff of ${args.branch} against ${args.baseBranch} follows.\n\n${report}\n\n` +
        `For every critical and high finding, try to construct the concrete path to exploitation from the real code — ` +
        `who reaches the input, what gets past validation, what the attacker walks away with. A finding you cannot ` +
        `build that path for is refuted:true: it is info, not a vulnerability.`,
      { label: `verify:${key}`, phase: 'Verify', schema: VERDICTS },
    ).then((verdicts) => ({ key, report, verdicts })),
)

return out.filter(Boolean)

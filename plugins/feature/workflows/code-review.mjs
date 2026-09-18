export const meta = {
  name: 'feature-code-review',
  description: 'Review of a feature branch diff through three lenses, every serious finding refuted',
  whenToUse: 'Run by step 7 of /feature:start. args: {brief, baseBranch, branch} — brief holds the task, the approved plan and the branches, nothing about how development went.',
  phases: [
    { title: 'Review', detail: 'feature:reviewer over three lenses at once' },
    { title: 'Verify', detail: 'an independent agent tries to refute every blocker and major' },
  ],
}

const LENSES = [
  ['bugs', 'Correctness. Run the `code-review` skill over the diff and hunt for real bugs — wrong behavior, unhandled states, broken contracts.'],
  ['simplify', 'Quality through the lens of the `simplify` skill: duplication, dead code, needless abstraction, unrequested configurability, mismatch with the surrounding style.'],
  ['scope', 'The diff against the task and the approved plan: does it solve what it was meant to, did it add more than the plan called for, is anything the plan promised missing?'],
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
          refuted: { type: 'boolean', description: 'true = does not hold against the real code' },
          why: { type: 'string', description: 'what you read and what it showed' },
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
      agentType: 'feature:reviewer',
      label: `review:${key}`,
      phase: 'Review',
    }),
  (report, [key]) =>
    report &&
    agent(
      `A review report on the diff of ${args.branch} against ${args.baseBranch} follows.\n\n${report}\n\n` +
        `Take every blocker and major finding and try to REFUTE it against the real code — open the files, ` +
        `read them whole, follow the call sites. Mark refuted:true whenever you cannot reproduce the problem from the code.`,
      { label: `verify:${key}`, phase: 'Verify', schema: VERDICTS },
    ).then((verdicts) => ({ key, report, verdicts })),
)

return out.filter(Boolean)

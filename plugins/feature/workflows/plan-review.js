export const meta = {
  name: 'plan-review',
  description: 'Adversarial review of an implementation plan through three lenses, every blocking finding refuted',
  whenToUse: 'Run by /feature:plan-review and by step 3 of /feature:start. args: {brief} — the task, the plan and baseBranch, nothing about how the plan came about.',
  phases: [
    { title: 'Review', detail: 'feature:plan-reviewer over three lenses at once' },
    { title: 'Verify', detail: 'an independent agent tries to refute every Blocking finding' },
  ],
}

const LENSES = [
  ['correctness', 'Step order and executability: dependencies are not inverted, nothing leans on a step that comes later, every requirement of the task is covered by some step.'],
  ['reuse', 'Reuse and simplicity: the named files and symbols really exist and have the assumed signature, nothing the repo already has is being written again, nothing is being built that nobody asked for.'],
  ['edges', 'Edge cases and failure modes: error/empty/loading states, data–contract mismatches, backward compatibility, migration and rollout order, and whether the risky part of the change is actually tested.'],
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
          why: { type: 'string', description: 'what you opened or grepped and what it showed' },
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
      agentType: 'feature:plan-reviewer',
      label: `plan:${key}`,
      phase: 'Review',
    }),
  (report, [key]) =>
    report &&
    agent(
      `A plan review report follows. The plan under review:\n\n${args.brief}\n\nThe report:\n\n${report}\n\n` +
        `Take every Blocking finding and try to REFUTE it against the real code — open the files it names, ` +
        `grep the symbols. Mark refuted:true whenever you cannot confirm the finding straight out of the code.`,
      { label: `verify:${key}`, phase: 'Verify', schema: VERDICTS },
    ).then((verdicts) => ({ key, report, verdicts })),
)

return out.filter(Boolean)

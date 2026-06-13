# Journey: Repair And Iteration

Use this journey when the user provides an old DSL, failed import, canvas rendering issue, runtime error, poor output quality, or requested change to an existing Dify Workflow or Chatflow.

## Failure-Stage Diagnosis

First classify the failure stage:

1. Import: AI Hub rejects the DSL before creating the app.
2. Canvas open: import may succeed, but the workflow cannot render or open.
3. Run: the app opens but a node fails during execution.
4. Output quality: the app runs but produces wrong, weak, or unusable results.

If the stage is unclear, ask one lightweight question: did it fail on import, on opening the canvas, during a run, or in the final output?

If the stage is already clear from logs, screenshots, or files, begin diagnosis directly.

## Preserve-First Surgery

Preserve the original business goal, Start inputs, End or Answer output semantics, user-facing output shape, and core prompt intent by default.

Change only the smallest part needed to fix the diagnosed issue. Do not redesign architecture, replace tools, change providers, or rewrite prompts unless the failure requires it or the user requests it.

Write a new version by default. Do not overwrite the original unless the user explicitly asks.

## Narrow Repair Criteria

Narrow repair can skip the extra confirmation only when all criteria hold:

1. The user already asked to fix the issue.
2. The change is mechanical.
3. Business goal is unchanged.
4. Start inputs are unchanged.
5. End or Answer output semantics are unchanged.
6. Prompt logic is not rewritten.
7. Workflow architecture is not changed.
8. Models, tools, and providers are not replaced.
9. A new version is written by default.
10. The final message states that the work was a narrow repair.

Examples include missing `tool_configurations: {}`, selector typos, Code node syntax errors, iteration item type mismatches, and child canvas contract fixes.

## Non-Narrow Final Alignment

If the repair changes business semantics, architecture, prompts, tools, providers, output fields, or user-facing behavior, it is not narrow.

Before non-narrow repair, present one concise natural-language alignment and wait for confirmation. The alignment should explain what will be preserved, what will change, why the change is needed, and what the first AI Hub test should check.

Ask only one missing question at a time if the repair cannot be safely scoped.

## Versioned Output

Default output is a new versioned DSL such as `<slug>-v2.yml` or `<original-name>-repaired-v1.yml`.

For formal repair projects, also update or create:

1. `README.md` when user-facing import and first-test instructions change.
2. `.agent/build-log.md` with what was fixed, preserved, and intentionally left unchanged.
3. `.agent/validation-report.md` with static validation, live QA status, and residual risks.

Do not add separate rollback or backup tasks. Versioned output is the default preservation mechanism.

## Validation And Handoff

Run failure-stage-specific checks before delivery.

Report exactly what was verified: YAML, graph references, selectors, schema, Code syntax, tool shape, iteration contracts, app-mode output consistency, and live AI Hub import/open/run only if performed.

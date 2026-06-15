# The Goal contract

The Goal is the kick-prompt you send to the executor. It is not a normal prompt —
a normal prompt says "do X now"; a Goal defines a **durable operating contract**:
what outcome counts, how completion is proven, what must not change, where work may
happen, how to iterate, when to stop, and when to pause. The executor runs
autonomously inside this contract, so the contract is what keeps it on the rails
while you're not watching.

Because the executor is **memoryless and cannot read this skill**, the Goal must be
fully self-contained. It carries three things: the seven elements, an executor
operating brief, and the Handoff format the executor must produce. Everything the
executor needs is in the message or it doesn't exist for the executor.

## The seven elements (and what each one defends against)

| Element | Answers | Without it, the executor… |
|---|---|---|
| **Outcome** | What's true at the end? | works on "X" forever with no finish line |
| **Verification** | How is it proven? | declares "done" on vibes, not evidence |
| **Constraints** | What must not change? | refactors public APIs, schemas, secrets, branches |
| **Boundaries** | Where may it write? | edits the whole repo and "fixes" unrelated things |
| **Iteration** | How to handle failure? | retries the same broken thing forever |
| **Stop when** | When is it done? | stops too early, or never |
| **Pause if** | When to wait for a human? | burns through credentials/production/destructive actions |

Drafting rules that matter:
- Write the outcome as a **result**, not "work on X". Make it concrete enough that
  two people would agree whether it's met.
- Put **discovered, concrete commands** in Verification — never "make sure it
  works". If you don't know the commands, make discovery the first step.
- For bugfix / bad-trace work, Verification starts with the original failing input:
  reproduce or capture the failure signal, apply the focused fix, rerun that exact
  input, then lock the failure with a regression test/eval/replay/check where
  practical. See `references/repair-flywheel.md`.
- "What must not change" goes in **Constraints**; filesystem/write permissions go
  in **Boundaries**. Keep them separate.
- In Iteration, require a **new source of evidence** after repeated failure (read
  the full error, check docs, reduce to a minimal repro) — never "keep trying".
- In Stop when, define **proof**, not a feeling — and require the Handoff as the
  final deliverable.
- In Pause if, list anything needing human judgment or external permission. For an
  autonomous executor this is the safety brake; don't make it so broad it stops on
  every minor unknown, nor so narrow it works around real risks.

Translate vague taste words instead of banning them: "polished", "professional",
"looks native" aren't failures — making them the *acceptance test* is. Turn them
into a direction + screenshot checks + a bounded number of focused passes.

## Build briefs and parallel Goals

Some task prompts arrive as a filled build brief: "build X in Y with features Z,
make it feel like Q, output as R." Treat that as input material for the Goal, not
as the Goal itself. Convert it into the seven elements:

- Outcome = the requested artifact and behavior.
- Verification = build/test/run commands, screenshots, browser checks, evals, or
  reviewable files that prove the artifact matches the brief.
- Constraints and Boundaries = project truth sources, allowed files, no-go zones,
  and what must not regress.
- Iteration, Stop when, Pause if = the autonomous loop, completion proof, and
  escalation brakes.

For parallel fan-out, the commander first writes and lints a top-level split note
from `references/fanout-harness.md`, then one full Goal per executor. Prefer extra
read-only exploration, review, or verification batons when they add independent
evidence; token cost is not the limiting factor. Each parallel Goal must be
self-contained and must add:

- `Sub-baton ownership`: the exact files/modules/questions this executor owns.
- `Sibling collision rule`: what this executor must not touch because another
  baton owns it.
- `Synthesis contract`: the Handoff name and the evidence the commander will use
  to merge or compare results.

Do not write "as many agents as needed" into a Goal as an unbounded instruction.
Name the batons you can defend. Extra agents are useful when they improve coverage,
surface competing diagnoses, or verify different failure modes without increasing
merge risk or verification ambiguity.

## The assembled Goal (template)

Placeholders are `{{double-brace}}` so the linter can catch any you forgot to fill;
legitimate `<...>` in content (generics, `<branch>` notation) won't trip it. Write
the body in the project's working language; keep the command token `/goal`.

```text
/goal {{outcome — a concrete end-state, anchored to the task/issue if one exists}}

Truth sources (reference, do NOT copy or override; on conflict, the truth source wins):
  - Task: {{issue/ticket id + where its acceptance criteria live, or "none"}}
  - Contracts/specs/ADRs/glossary that govern this work: {{paths/links, or "none"}}
  - Prior progress: {{"must-read" excerpt of the previous Handoff, inlined below
    under "Prior baton"; or "none — this is the first baton"}}

Verification (concrete evidence only — discover the project's own commands first):
  {{the verification ladder for this baton — see references/verify-and-visual.md;
    name exact commands, expected signals, and what artifacts/screenshots to capture}}
  {{if bugfix / bad-trace: name the original input, failing signal, rerun command,
    and regression-lock check expected in the Handoff's Repro Capsule}}

Constraints (what must not change):
  {{invariants: public APIs / data shapes / schemas / styles / branch rules}}
  {{project rules relevant to this baton — cite the project's own AGENTS.md/etc.}}
  Secret hygiene: never read, print, paste, or commit real credentials; refer to
  them only as $ENV_VAR placeholders; keep them out of code, logs, and the Handoff.

Boundaries (where you may write):
  Scope = {{the in-scope items for this baton}}. Write only {{allowed dirs/files}}.
  Do not touch {{forbidden paths/modules}} and do not do unrelated refactors or cleanup.
  Out-of-scope findings → record them for the human (e.g. file a tracked item); do not act.
  {{if the executor sandbox is constrained: the work-area/push boundary —
    see references/executor-dispatch.md}}

Iteration policy (how to make progress, and the brakes):
  First do discovery: read the truth sources + prior excerpt, then list your working
  assumptions before changing code. Then: one focused change at a time, rerun the
  relevant check after each, read logs before retrying. If the same failure persists
  twice, switch evidence source (full traceback / docs / minimal repro) — do not
  repeat the same attempt. After at most {{N, e.g. 3}} focused passes without success,
  stop and hand back with the blocker described. Low-risk unknowns: pick the best
  conservative default and record it; only the Pause-if list stops you.

Stop when (proof of completion + deliver the baton):
  {{acceptance criteria met, item by item}} AND {{the verification ladder is green
  or any gap is explicitly reported}} AND evidence is captured. For bugfix /
  bad-trace work, the original failing input has been rerun and the failure is
  locked by a test/eval/replay/check, or the Handoff explains why only manual
  verification is possible. Then write the Handoff (format below) and echo its full
  text as your final terminal output.

Pause if (stop and escalate — do NOT work around):
  {{anything needing the network / a push to remote / credentials / production data
  / destructive actions / external service triggers / a product decision}}; or a
  truth-source conflict (the task contradicts the spec/ADR/glossary); or the same
  failure point blocks you {{M, e.g. 3}} times. When paused, write the Handoff with
  status BLOCKED, stating the symptom, what you tried, the suspected cause, and the
  exact action you need from the human.

--- Executor operating brief (you are a fresh relay thread) ---
{{paste the brief below}}

--- Handoff format (produce this as your final act) ---
{{paste the Handoff template from references/handoff.md here — the executor cannot
  read that file, so it MUST be inlined}}

## Prior baton (inline; first baton = "none")
{{the previous Handoff's must-read excerpt, ≤ ~1.5 KB: branch/commit to build on,
  base commit, migration/contract state, no-go zones, traps to avoid}}
```

## The executor operating brief (inline verbatim)

This is the generalized "how to behave" the executor needs because it can't read
the skill. Paste it into every Goal; tune the bracketed bits per project.

```text
You are a fresh, memoryless run of a background coding agent. Everything you need is
in this message — there is no earlier conversation and no skill for you to consult.

1. Start with discovery: read the truth sources and the "Prior baton" excerpt, then
   write down your working assumptions before touching code.
2. Work autonomously in multiple rounds inside the Boundaries: implement a slice →
   run the project's checks → read logs → fix → re-verify. Do NOT stop after one
   step. Stop only when "Stop when" is satisfied or a "Pause if" trigger fires.
3. You own the order of sub-steps within the boundary; do not expand scope past it.
   Out-of-scope problems get recorded for the human, not fixed.
4. If you hit something this sandbox cannot do — no network, read-only repo, no real
   database/services, a step that must be pushed and merged before the next builds on
   it — do the part you CAN verify here, then stop with Handoff status PARTIAL and
   hand back. That is a normal outcome, not a failure.
5. Capture evidence as you go: the commands you ran and their result lines,
   screenshots for any UI. You'll point to these in the Handoff.
6. For failure-driven work, preserve the Repro Capsule: original input, failing
   signal, rerun command, config/commit, evidence pointer, and the regression lock
   you added or could not add.
7. Secret hygiene: never print or paste real credentials; use $ENV_VAR placeholders;
   keep them out of logs and the Handoff.
8. Your final act is to write the Handoff in the exact format given, and echo its
   full text as your last terminal output so the commander can retrieve it (the
   commander may not be able to read files you wrote inside this sandbox).
```

## First baton vs. continuing baton

- **First baton:** "Prior progress" / "Prior baton" = `none`. The discovery step is
  heavier — the executor establishes the lay of the land and records assumptions.
- **Continuing baton:** inline the previous Handoff's **must-read excerpt** (not the
  whole thing) under "Prior baton": the branch/commit to build on, the base commit,
  any migration/contract state, the no-go zones, and the traps the last run hit. The
  rest of the Handoff stays on disk for your verification, not in the Goal — see
  `references/handoff.md` for why two parts.

## Before you dispatch

Run `scripts/lint_goal.py <assembled-goal-file>`. It rejects the classic failures:
missing elements, unfilled `{{...}}`, vague verification, unbounded retries, a
missing task reference, a pause list with no escalation triggers, a stop condition
that forgets the Handoff, and anything that looks like a leaked secret. Fix and
re-run until clean, then dispatch (`references/executor-dispatch.md`).

When the executor returns, run `scripts/lint_handoff.py <handoff-file>` before
using the Handoff as evidence or inlining Part A into the next Goal.

## Worked example (generic, abbreviated)

```text
/goal Fix the coupon engine so percentage coupons apply once per order and
fixed-value coupons still stack with store credit, with a regression test proving it.

Truth sources (reference, do NOT copy or override):
  - Task: ISSUE-142 (acceptance criteria in its description)
  - Contracts/specs: the pricing module's documented coupon rules; do not change them
  - Prior progress: none — this is the first baton

Verification:
  - Add a failing regression test for the percentage-coupon case, confirm it fails
    before the fix, then make it pass.
  - Run the project's unit tests for the checkout/pricing area (discover the runner
    from package scripts) and the smallest relevant lint/typecheck.
  - Capture the original coupon input, red/green test lines, and rerun command in
    the Repro Capsule.

Constraints:
  - Do not change public coupon API names, the DB schema, or store-credit behavior.
  - Secret hygiene: $ENV_VAR placeholders only.

Boundaries:
  - Write only in the pricing/coupon logic and its tests; do not touch payment-
    provider config or migrations; no unrelated refactors.

Iteration policy:
  - Discovery first (read the rules + tests), list assumptions, then one change at a
    time, rerun the failing test after each, read output before retrying; switch
    evidence source after two failures; max 3 focused passes then hand back.

Stop when:
  - Regression test fails before the fix and passes after; targeted lint/typecheck is
    green; the original failing input is rerun; Repro Capsule and Regression lock
    are filled in. Then write the Handoff and echo it.

Pause if:
  - A schema migration, payment credentials, production data, or a product decision
    about stacking rules is required; or a truth-source conflict; or the same failure
    blocks you 3 times. Then write a BLOCKED Handoff with the action you need.

--- Executor operating brief --- {{inlined}}
--- Handoff format --- {{inlined}}
## Prior baton: none
```

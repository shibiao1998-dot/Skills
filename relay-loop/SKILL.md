---
name: relay-loop
description: >-
  Orchestrate a commander-executor relay loop for background coding agents such as
  `codex exec`: plan the work, write a self-contained Goal contract, dispatch one
  memoryless executor baton or a gated fan-out of independent batons, receive and
  lint the Handoff, verify the result yourself, then advance the next baton. Use
  when the user wants to dispatch work to Codex/background agents, write a
  Goal/kick-prompt/spec for an executor, hand off between agent threads, run
  plan-dispatch-verify-advance cycles, repair a failed agent trace/log, create a
  Repro Capsule, or lock a regression. Triggers include "dispatch this to codex",
  "write a goal for the executor", "kick off a background agent", "parallel
  goals", "run the loop unattended/overnight", "autonomous loop on a heartbeat",
  "relay loop", "handoff to the next thread", "orchestrate codex",
  "repair the harness", and "lock this regression".
---

# Relay Loop — commander drives, executor builds, handoff carries the baton

A discipline for getting high-quality work out of a background coding agent without
babysitting it and without losing the thread between runs.

## The mental model (read this first — everything follows from it)

- **You are the commander.** You plan, write the contract, dispatch, verify, and
  decide what happens next. You are the *only* participant with continuous memory
  of the whole effort.
- **The executor is a fresh, memoryless thread each time.** A `codex exec` run (or
  any headless agent run) starts cold, does one baton of work autonomously, then
  exits. It cannot remember the last run and **cannot read this skill.**
- **The Handoff is the baton.** When the executor finishes, it writes a Handoff
  document. That document is the only thing that crosses from one executor thread
  to the next. You read it, verify against it, and inline its essence into the
  next Goal.
- **A failure must become replayable.** For bugfix / bad-trace work, the Handoff
  must carry a Repro Capsule, diagnosis, rerun command, and regression-lock
  candidate. A fixed failure that cannot be rerun or guarded will come back.
- **The Goal is a self-contained contract.** Because the executor can't read this
  skill or remember anything, the Goal you send must carry *everything the
  executor needs*: the outcome, how to verify, what not to touch, how to iterate,
  when to stop, when to pause — plus a short operating brief and the exact Handoff
  format. If it isn't in the Goal, the executor doesn't know it.
- **Parallel assessment is default; fan-out is quality-first.** Always ask whether
  independent executors would improve coverage, reduce blind spots, or produce
  useful competing evidence. Fan out when you can name ownership, collision rules,
  independent verification, and a synthesis point. Each executor still gets its own
  self-contained Goal and writes its own Handoff.
- **You are managing, not just dispatching.** The same discipline that makes a human
  report succeed makes a memoryless executor succeed — three pillars: a *clear goal*
  (the Goal contract), *sufficient resources* (the tools, connectors, permissions,
  and prior knowledge it needs — you provision them), and *timely, independent
  feedback* (verification each baton, ideally by a checker that isn't the doer).
  Vague goals, missing resources, or self-graded work fail agents the same way they
  fail people — only faster and more confidently.

A few consequences worth internalizing:

1. **Self-containment is non-negotiable.** A Goal that references "the skill" or
   "as discussed" is broken — the executor sees neither.
2. **Continuity lives on disk, not in your context.** Your session will be
   compacted or restarted. Externalize where-we-are to a loop-state directory so a
   future you (or a teammate) can resume.
3. **Failures harden the harness only when recorded.** A bad trace should produce
   a narrow fix plus a regression check or a named reason automation is impossible.
4. **Quality comes from coverage plus synthesis, not agent count alone.** Extra
   executors are welcome when they add independent evidence. They are harmful when
   they collide on the same files, duplicate the same blind spot, or leave the
   commander with an unverifiable merge.
5. **The verifier is a proxy, not the target.** An agent optimizes whatever you
   measure; tell it to make the tests pass and it may delete the failing test. Every
   Goal carries an anti-gaming clause, and every verification confirms the checks
   themselves weren't weakened — not just that they're green (Goodhart's law).

## Before the loop: discover the project (don't assume)

This skill gives you the *shape*; the project gives you the *facts*. Spend the
first few minutes discovering, never inventing:

- **Verification commands** — package scripts, Makefile targets, CI config, test
  runners, lint/typecheck. You'll inline these into the Goal's verification ladder.
- **Truth sources** — does the project have an issue tracker, a PRD/spec, ADRs, a
  glossary, an `AGENTS.md`/`CLAUDE.md`/contributing guide? These outrank anything
  you or the executor might assume. The Goal *references* them; it never copies or
  overrides them.
- **Executor sandbox constraints & provisioning** — can the executor reach the
  network? Is the repo's `.git` writable from its sandbox? Can it run the database /
  containers / servers the tests need? Which connectors (GitHub, issue tracker, chat,
  DB) does the work require, and does the executor's environment have them? The
  answers decide baton granularity, what you must *provision* for the executor, and
  what must be pushed/run on *your* side. See `references/executor-dispatch.md`.
- **Loop-state directory** — pick a gitignored working dir for handoffs and
  state. Default convention: `.loop/` at repo root, added to
  `.git/info/exclude`. Reuse the project's if one exists.
- **Failure inputs** — for bugfix / trace-driven work, capture the original input,
  command, log, screenshot, branch/commit, and config needed to replay the failure.
  See `references/repair-flywheel.md`.

If a fact is missing and low-risk, pick the best conservative default and record
the assumption. If it's high-risk (credentials, production, destructive, product
direction), that's a Pause condition, not a guess.

## The loop

```
1 recover + plan + scope this baton      (commander)
2 write the Goal contract                (commander)  → references/goal-contract.md
2a fan-out harness gate                  (commander)  → references/fanout-harness.md
3 dispatch in the background             (commander)  → references/executor-dispatch.md
4 executor runs autonomously             (executor — out of your hands)
5 receive + lint Handoff, land it to disk (commander) → references/handoff.md
6 rerun + verify yourself, incl. visual   (commander) → references/verify-and-visual.md
7 advance: merge/integrate, update anchor, dispatch next baton  → back to 2
```

### 1 — Recover, plan, scope

If you're resuming, first rebuild your bearings from disk
(`references/commander-recovery.md`): read the loop-state anchor, the latest
Handoff, and the project's status. Then decide the **boundary of this baton** —
what this one executor thread will own. You own the boundary; the executor owns
how to get there. Don't hand the executor a vague "improve things" — that's the
single biggest cause of wasted runs.

### 2 — Write the Goal contract

Assemble the Goal from `references/goal-contract.md`. It is seven elements
(outcome, verification, constraints, boundaries, iteration, stop-when, pause-if)
plus an inlined executor operating brief and the inlined Handoff template. For a
continuing baton, also inline the prior Handoff's "must-read" excerpt (≤ ~1.5 KB —
the branch/commit to build on, the no-go zones, the traps). Run
`scripts/lint_goal.py` on the assembled Goal before sending — it catches the
classic failure modes (missing elements, unfilled placeholders, vague verification,
unbounded retries, a missing anti-gaming clause, a failure-driven Goal with no
red-first check, leaked secrets).

### 2a — Fan-out harness gate

Default to assessing whether parallel executors would improve the result. Token
cost is not the primary constraint; quality, mergeability, and verification are.
Fan out when the work decomposes into genuinely independent batons:

- **Good fan-out:** exploration passes, separate modules/files, independent test
  surfaces, UI/design review vs. backend analysis, docs/examples that do not edit
  the same source, competing read-only diagnoses, or separate verification passes
  that look for different failure modes.
- **Bad fan-out:** one task must land before another can start, several executors
  would edit the same files, the scope needs a product decision, or the merge point
  would be harder than the work. If uncertainty is the blocker, first fan out
  read-only exploration Goals, then synthesize before implementation.

Before dispatching, write a compact top-level split note: shared objective,
sub-baton list, ownership boundaries, shared constraints, expected Handoff names,
and the synthesis order. Use `references/fanout-harness.md` as the template and
run `scripts/lint_fanout.py` before writing or dispatching the per-executor Goals.
If the task stays single-baton after assessment, record `Mode: SINGLE` and the
single-baton rationale in the same harness. Then write **one full Goal per
executor**. Do not rely on agents talking to each other or on a shared chat
transcript; continuity still flows through their Handoffs and your verification.

### 3 — Dispatch

Launch the executor in the background and tee its output to a log
(`references/executor-dispatch.md`). Do not block your session waiting. Do not try
to escalate the executor's permissions or sandbox — if an action was denied, that
is a signal to change approach, not to retry it verbatim.

### 4 — Executor runs (hands off)

Inside its single run the executor iterates autonomously — implement a slice, run
the project's checks, read logs, fix, re-verify — until it hits the Goal's
stop-when or a pause-if trigger. It is not supposed to stop after one step; it is
supposed to stop when a trigger fires. The contract is what keeps it on the rails
while you're not watching.

### 5 — Receive the Handoff

The executor's last act is to write a Handoff (`references/handoff.md`). Pull it
from the executor's terminal log, run `scripts/lint_handoff.py` on it, and land it
into the loop-state directory. Keep Handoff content out of any public destination
(PR/issue comments) — it routinely carries commands, endpoints, and environment
detail. Public posts get a human-readable summary only.

### 6 — Verify (the part you must not skip)

Code that passes the executor's own checks is **not** the same as code that works.
Verify against the Goal's success criteria yourself, and specifically attack what
the executor *couldn't* see — its sandbox blind spots (no real backend, no real
data) and whatever it flagged in its Handoff "what I did NOT verify" section. For
anything user-facing, do a real visual check (`references/verify-and-visual.md`).
For failure-driven work, rerun the original input from the Repro Capsule and check
that the regression lock actually guards the old failure.
If it falls short, write a focused fix-Goal and go back to step 2 — don't hand-fix
silently, or the next baton inherits a false picture.

### 7 — Advance

When it genuinely passes: integrate (merge / land), update the loop-state anchor
(which baton, what's done, what's next), and write the next Goal as a brand-new
executor thread — inlining this baton's Handoff essence. At a milestone boundary,
reconcile your externalized memory against what actually landed
(`references/commander-recovery.md`) so the next baton doesn't build on stale
premises. Loop until the whole effort is done and you have personally verified it.
If the batons ahead are fully machine-verifiable, you may let the loop run unattended
on a heartbeat instead of re-kicking each one (`references/autonomy-heartbeat.md`) —
the heartbeat re-runs the commander cycle (gate included); it does NOT make the
executor self-perpetuate. Autonomy is earned by verifiability, not assumed.

## Baton granularity (where quality is won or lost)

Don't centralize all topic-selection onto yourself — making every issue its own
tiny baton inverts the savings (every baton costs a Goal + a Handoff read + a
verify) and can reduce quality by fragmenting context. Instead:

- **You own the baton boundary** (which slice of work, where it stops).
- **The executor owns intra-baton topology** (the order of sub-steps, local
  dependency sequencing) within that boundary.

Size each baton by sandbox reachability:

- **Class A — sandbox-closable.** Pure logic with unit/in-memory tests, no network,
  no real DB, no push needed. The executor can take a whole dependency-closed
  sub-chain end to end in one baton. Don't chop it up unless parallel read-only
  review or independent verification would improve confidence.
- **Class B — crosses a push/integration boundary.** Needs the network, a real
  database/services, CI, or a migration/contract that must be pushed and merged
  before the next step builds on it. The executor does the part it *can* verify in
  its sandbox, then stops with `status: PARTIAL` and hands back. You push / merge /
  run the out-of-sandbox checks, then start the next baton. Treat PARTIAL as a
  normal, expected outcome for Class B — not a failure.

## Non-negotiables (and why)

- **The Goal is self-contained.** The executor can't read this skill or remember
  the last run; anything not in the Goal effectively doesn't exist for it.
- **Externalize your memory.** You will be compacted/restarted. If where-we-are
  lives only in your context, the whole loop stalls when you lose it.
- **Knowledge rots — reconcile it.** Your externalized memory (anchor, inlined
  Handoff essence, project docs) drifts from reality across a long loop. Reconcile it
  against the repo at each milestone (`references/commander-recovery.md`;
  non-optional in the autonomy tier); an unattended loop reading stale premises fails
  faster the harder it runs.
- **Secrets never travel in the clear.** Handoffs and logs carry commands and
  config. Keep real keys/tokens as `$ENV_VAR` placeholders, never paste real
  values, and never echo a Handoff verbatim into a public comment. The linter
  scans for this; so should you.
- **Green ≠ done.** Always verify behavior yourself, especially across seams the
  executor's sandbox can't exercise. Visual/real-backend check before claiming
  success.
- **Audit the checks, not just their color (anti-gaming).** State in every Goal that
  the executor may not reach green by deleting, skipping, weakening, or mocking-away
  the checks. When you verify, diff the tests/checks themselves — a shrunk assertion
  or a deleted case is a failure, not a pass.
- **Doer ≠ checker.** The agent that wrote the code can't be the only judge of it.
  Own the acceptance gate yourself, and for high-stakes or unattended work spin an
  independent verifier baton — ideally on a different model — prompted to refute, not
  confirm.
- **Commander verification should become automation.** "Verify yourself" means the
  commander owns the acceptance gate, not that a human must manually inspect every
  repeatable detail. Convert repeated human checks into tests, scripts, browser
  checks, evals, CI jobs, and replay commands. Leave humans the parts that require
  judgment, authorization, production risk acceptance, or product direction.
- **Fixed ≠ hardened.** A failure-driven baton is not ready until the original
  input can be rerun and the failure is locked by a test/eval/replay/check, or the
  Handoff names why only manual verification is possible.
- **A denied action is a signal, not a retry.** If a permission or sandbox limit
  blocks the executor, change approach or pause for the human — don't loop on it.
- **Discover, don't invent.** Project facts (commands, conventions, truth docs)
  come from the project. When unknown and low-risk, assume explicitly and record
  it; when high-risk, pause.

## Reference map

Read the one you need, when you need it — don't preload everything.

- `references/goal-contract.md` — the Goal template, the inlined executor brief,
  and how to assemble a first vs. continuing baton. **The heart of the skill.**
- `references/loop-blueprints.md` — a relay-native catalog of ~8 common loop
  patterns (test triage, CI/PR until green, post-edit guard, independent verifier,
  spec-first ship, API/contract/migration, visual/E2E, dependency/security), each a
  pre-filled mapping onto the seven Goal elements + Handoff + verification, plus the
  manual/event/interval trigger reframing and a blueprint map for picking the next
  baton. Use as a menu at step 1 when the work matches a common shape.
- `references/fanout-harness.md` — the structured split-note templates for
  FANOUT / EXPLORE_FIRST / SINGLE decisions. Use before dispatching parallel work
  or when a complex task needs an explicit no-fan-out rationale.
- `references/handoff.md` — the two-part Handoff protocol, the template, naming,
  Diagnostic repair record, Repro Capsule, Regression lock, and how it relates to
  other status artifacts.
- `references/repair-flywheel.md` — how to turn bad traces/logs into diagnosis,
  replay, focused repair, regression protection, and reusable harness blueprints.
- `references/verify-and-visual.md` — the discovery-based verification ladder,
  sandbox-reachability of each rung, and the visual-verification tiers/tools.
- `references/executor-dispatch.md` — background dispatch command, sandboxed-
  executor bypass patterns (e.g. two-hop push), denied-action rule, path quoting,
  secret hygiene.
- `references/commander-recovery.md` — how to rebuild state after your session is
  compacted or restarted, including the layered goal anchor and the reconcile step.
- `references/autonomy-heartbeat.md` — the opt-in autonomy tier: when and how to let
  the loop run unattended on a heartbeat (schedule/cron/hooks/CI), the "autonomy is
  earned by verifiability" gate (lint-enforced via `Mode: AUTONOMOUS`), the degradation
  ladder, and the notify-human closed loop. Read before removing yourself from the
  per-baton cycle.
- `scripts/lint_fanout.py` — run on every fan-out split note before dispatch.
- `scripts/lint_goal.py` — run on every assembled Goal before dispatch.
- `scripts/lint_handoff.py` — run on every returned Handoff before trusting it.
- `scripts/render_blueprint_goal.py` — scaffold a Goal-contract draft from a
  `references/loop-blueprints.md` family (`--list` for keys) into `.loop/goals/`, with
  the standard anti-gaming block baked in and `{{placeholders}}` to fill, then lint.

## Anti-patterns

- A Goal whose outcome is "make it better" / "finish this" / "fix bugs" — no
  verifiable target, no stop condition.
- Inlining a whole prior Handoff verbatim into the next Goal — bloats the prompt
  and dilutes the executor's attention. Inline the *essence*, link the rest.
- Trusting a mock-mode screenshot as proof a real-backend flow works.
- Saying "fixed" without a Repro Capsule and regression lock.
- Letting the executor pick its own scope and watching it wander out of bounds.
- Keeping the only record of progress in your chat context.
- Gaming the verifier: deleting/skipping/weakening tests, mocking the thing under
  test, or hardcoding outputs to turn a check green without doing the work.
- Running unattended without an automated gate — letting batons advance (or
  auto-merging) when the Stop-when criteria aren't actually machine-verified.

---
name: relay-loop
description: >-
  Orchestrate a commander–executor relay loop. You (the strong reasoning model in
  this session) act as the in-the-loop commander: plan the work, write a
  self-contained Goal contract, dispatch it to a background CLI coding agent
  (canonically Codex via `codex exec`, but any headless executor works), receive a
  Handoff document when the executor finishes, verify the result yourself
  (including real-browser visual checks), then dispatch the next baton as a fresh,
  memoryless executor thread that carries the prior Handoff. Use this whenever the
  user wants to drive Codex or a background agent through repeated
  plan → dispatch → verify → advance cycles; write a Goal / kick-prompt / spec for
  an executor; hand off between agent threads; run a mostly-autonomous build loop
  with human-in-the-loop verification; or save tokens by keeping planning and
  verification on the strong model and pushing implementation to a cheaper
  executor. Trigger on phrases like "dispatch this to codex", "write a goal for
  the executor", "kick off a background agent", "relay loop", "handoff to the next
  thread", "orchestrate codex", "drive codex through this", "plan-execute-verify
  loop", or "have codex build X and check its work".
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
- **The Goal is a self-contained contract.** Because the executor can't read this
  skill or remember anything, the Goal you send must carry *everything the
  executor needs*: the outcome, how to verify, what not to touch, how to iterate,
  when to stop, when to pause — plus a short operating brief and the exact Handoff
  format. If it isn't in the Goal, the executor doesn't know it.

Three consequences worth internalizing:

1. **Self-containment is non-negotiable.** A Goal that references "the skill" or
   "as discussed" is broken — the executor sees neither.
2. **Continuity lives on disk, not in your context.** Your session will be
   compacted or restarted. Externalize where-we-are to a loop-state directory so a
   future you (or a teammate) can resume.
3. **Token economy comes from baton length, not micro-management.** The more
   complete the contract, the farther the executor runs on its own, the less you
   spend. But batons that are too small invert this — see *Baton granularity*.

## Before the loop: discover the project (don't assume)

This skill gives you the *shape*; the project gives you the *facts*. Spend the
first few minutes discovering, never inventing:

- **Verification commands** — package scripts, Makefile targets, CI config, test
  runners, lint/typecheck. You'll inline these into the Goal's verification ladder.
- **Truth sources** — does the project have an issue tracker, a PRD/spec, ADRs, a
  glossary, an `AGENTS.md`/`CLAUDE.md`/contributing guide? These outrank anything
  you or the executor might assume. The Goal *references* them; it never copies or
  overrides them.
- **Executor sandbox constraints** — can the executor reach the network? Is the
  repo's `.git` writable from its sandbox? Can it run the database / containers /
  servers the tests need? The answers decide baton granularity and what must be
  pushed/run on *your* side. See `references/executor-dispatch.md`.
- **Loop-state directory** — pick a gitignored working dir for handoffs and
  state. Default convention: `.loop/` at repo root, added to
  `.git/info/exclude`. Reuse the project's if one exists.

If a fact is missing and low-risk, pick the best conservative default and record
the assumption. If it's high-risk (credentials, production, destructive, product
direction), that's a Pause condition, not a guess.

## The loop

```
1 recover + plan + scope this baton      (commander)
2 write the Goal contract                (commander)  → references/goal-contract.md
3 dispatch in the background             (commander)  → references/executor-dispatch.md
4 executor runs autonomously             (executor — out of your hands)
5 receive Handoff, land it to disk       (commander)  → references/handoff.md
6 verify yourself, incl. visual          (commander)  → references/verify-and-visual.md
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
unbounded retries, leaked secrets).

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
from the executor's terminal log and land it into the loop-state directory. Keep
Handoff content out of any public destination (PR/issue comments) — it routinely
carries commands, endpoints, and environment detail. Public posts get a
human-readable summary only.

### 6 — Verify (the part you must not skip)

Code that passes the executor's own checks is **not** the same as code that works.
Verify against the Goal's success criteria yourself, and specifically attack what
the executor *couldn't* see — its sandbox blind spots (no real backend, no real
data) and whatever it flagged in its Handoff "what I did NOT verify" section. For
anything user-facing, do a real visual check (`references/verify-and-visual.md`).
If it falls short, write a focused fix-Goal and go back to step 2 — don't hand-fix
silently, or the next baton inherits a false picture.

### 7 — Advance

When it genuinely passes: integrate (merge / land), update the loop-state anchor
(which baton, what's done, what's next), and write the next Goal as a brand-new
executor thread — inlining this baton's Handoff essence. Loop until the whole
effort is done and you have personally verified it.

## Baton granularity (where token economy is won or lost)

Don't centralize all topic-selection onto yourself — making every issue its own
tiny baton inverts the savings (every baton costs a Goal + a Handoff read + a
verify). Instead:

- **You own the baton boundary** (which slice of work, where it stops).
- **The executor owns intra-baton topology** (the order of sub-steps, local
  dependency sequencing) within that boundary.

Size each baton by sandbox reachability:

- **Class A — sandbox-closable.** Pure logic with unit/in-memory tests, no network,
  no real DB, no push needed. The executor can take a whole dependency-closed
  sub-chain end to end in one baton. This is the token-saving sweet spot; don't
  chop it up.
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
- **Secrets never travel in the clear.** Handoffs and logs carry commands and
  config. Keep real keys/tokens as `$ENV_VAR` placeholders, never paste real
  values, and never echo a Handoff verbatim into a public comment. The linter
  scans for this; so should you.
- **Green ≠ done.** Always verify behavior yourself, especially across seams the
  executor's sandbox can't exercise. Visual/real-backend check before claiming
  success.
- **A denied action is a signal, not a retry.** If a permission or sandbox limit
  blocks the executor, change approach or pause for the human — don't loop on it.
- **Discover, don't invent.** Project facts (commands, conventions, truth docs)
  come from the project. When unknown and low-risk, assume explicitly and record
  it; when high-risk, pause.

## Reference map

Read the one you need, when you need it — don't preload everything.

- `references/goal-contract.md` — the Goal template, the inlined executor brief,
  and how to assemble a first vs. continuing baton. **The heart of the skill.**
- `references/handoff.md` — the two-part Handoff protocol, the template, naming,
  and how it relates to other status artifacts.
- `references/verify-and-visual.md` — the discovery-based verification ladder,
  sandbox-reachability of each rung, and the visual-verification tiers/tools.
- `references/executor-dispatch.md` — background dispatch command, sandboxed-
  executor bypass patterns (e.g. two-hop push), denied-action rule, path quoting,
  secret hygiene.
- `references/commander-recovery.md` — how to rebuild state after your session is
  compacted or restarted.
- `scripts/lint_goal.py` — run on every assembled Goal before dispatch.

## Anti-patterns

- A Goal whose outcome is "make it better" / "finish this" / "fix bugs" — no
  verifiable target, no stop condition.
- Inlining a whole prior Handoff verbatim into the next Goal — bloats the prompt
  and dilutes the executor's attention. Inline the *essence*, link the rest.
- Trusting a mock-mode screenshot as proof a real-backend flow works.
- Letting the executor pick its own scope and watching it wander out of bounds.
- Keeping the only record of progress in your chat context.

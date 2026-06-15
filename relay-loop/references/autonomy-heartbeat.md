# The autonomy tier — letting the loop run on a heartbeat

The base relay loop is **human-checkpointed**: you dispatch a baton, it runs, you
verify, you dispatch the next. That cadence buys a verification gate between every
baton (see `references/executor-dispatch.md`, "autonomy vs. the leash"). This file
is the **opt-in** upgrade — how to let the loop keep running while you're asleep
without throwing the gate away.

The rule that makes it safe:

> **Autonomy is earned by verifiability, not assumed.** A baton may advance
> unattended only when its acceptance is fully machine-checkable and its brakes are
> trustworthy. Where acceptance needs human judgment, the loop must stop and wake
> you. Removing yourself from the cycle does not remove the gate — it *automates*
> the gate.

And autonomy is **granted by a human, not self-granted by the loop.** Before the first
unattended run of an effort, a human signs off the eligibility checklist below and
records it in the loop-state dir; the loop never promotes itself to unattended. That
sign-off is also **lint-enforced**: declare `Mode: AUTONOMOUS` in the Goal and
`scripts/lint_goal.py` then requires a machine-verifiable Stop-when (commands / exit
codes, no taste words), a named independent verifier, and a recorded human sign-off —
so "earned by verifiability" is mechanical, not prose the same agent can tick off for
itself. It is the "verification should become automation" path the base skill already
requires, applied to the remove-the-human decision itself.

## The heartbeat (something restarts the loop)

A loop needs a pulse. Without one you are the pulse — you re-kick it every baton,
which is just manual relay. Provide a real trigger (these are environment-specific;
discover/load what your harness offers before relying on it):

- **Interval driver** — a self-pacing loop command (e.g. a `/loop` primitive) that
  re-enters the commander cycle on a cadence.
- **Schedule / cron** — a scheduled job (a cron primitive, a scheduled cloud agent,
  or an OS scheduler) that starts the loop at a fixed time, e.g. overnight runs.
- **Lifecycle hooks** — fire work at a point in the agent lifecycle (e.g. run
  lint/tests after every file edit, kick a verifier when a baton lands).
- **CI / Actions** — push the loop into CI so it runs with the laptop closed.

Pick the lightest trigger that fits: an overnight "drain the backlog" loop wants a
schedule; a "keep the branch green" loop wants a hook or interval.

## The automated gate (what replaces your eyes)

In the base loop, step 6 is *you* verifying. In the autonomy tier, that gate must
run by itself before a baton is allowed to advance or merge:

1. **Machine verification ladder** — the discovered commands (lint, typecheck, unit,
   CI replica, replay) run automatically; a non-green result blocks advance. See
   `references/verify-and-visual.md`.
2. **Independent verifier baton** — a read-only checker that, for the autonomy tier,
   MUST run on a *different model* than the doer and MUST re-derive evidence by
   re-running the ladder itself from a clean checkout. It does not trust the doer's
   evidence files or self-report, reads the Goal's acceptance criteria directly, and
   uses the refute template (not a commander-authored "confirm it works" prompt). It
   also confirms the checks themselves were not weakened (anti-gaming). See
   `references/fanout-harness.md`.
3. **Gate decision** — advance the next baton (on its own non-protected branch) only
   if the ladder is green *and* the verifier finds no real defect. An unattended loop
   never merges to a protected/shared branch — that is a Class B human checkpoint it
   does not automate (see "When NOT to use"). Anything else routes into the
   degradation ladder.

A baton whose Stop-when can't be reduced to (1) + (2) is **not autonomy-eligible** —
keep it human-checkpointed.

## Eligibility checklist (gate a baton before letting it run unattended)

- [ ] A human has signed off this checklist for this effort (recorded in loop-state) —
      autonomy is granted, never self-granted.
- [ ] Every Stop-when criterion is machine-verifiable (a command / exit code /
      replay, not "looks right"). Visual-taste or product-direction criteria are not
      eligible.
- [ ] Pause-if's brake is the *sandbox, not the prompt*: the irreversible /
      outward-facing / credentialed / production capability is physically absent (no
      network, no prod credentials, no write to the protected resource), because a
      memoryless executor may ignore a Pause-if instruction. Discover what the sandbox
      actually denies; don't assume obedience.
- [ ] An automated gate (ladder + independent verifier) exists and runs before advance.
- [ ] A degradation ladder is defined (below) so failure parks safely instead of
      thrashing or waking you needlessly.
- [ ] Unattended work lands only on its own non-protected branch; merging to a
      protected/shared branch always waits for a human — never auto-merged while
      unattended.
- [ ] A notify-human channel is wired for completion and for every pause.

If any box is unchecked, run that baton in the base human-checkpointed loop instead.
Declaring `Mode: AUTONOMOUS` in the Goal makes `scripts/lint_goal.py` enforce the
machine-checkable items here (a verifiable Stop-when, a named independent verifier, and
a recorded human sign-off).

## The degradation ladder (graded failure fallback)

An unattended loop must fail *gracefully*, not thrash or page you for everything.
When a baton can't reach green, walk down the ladder — don't loop in place:

1. **Retry with new evidence** (≤ N focused passes): read the full error, the docs,
   reduce to a minimal repro — never repeat the same attempt.
2. **Downgrade to read-only diagnosis**: checkpoint the failed attempt first (commit
   or stash) so "read-only" starts from a clean snapshot, then capture the failing
   state and a root-cause hypothesis (the Diagnostic repair record).
3. **Park safely**: hand back `PARTIAL` / `BLOCKED` with the diagnosis and the exact
   action needed. An unattended baton works on its own worktree/branch; "park safely"
   means the integration branch is byte-identical to its pre-baton commit
   (`git status --porcelain` clean, integration HEAD unchanged) and any WIP stays
   isolated on the baton branch, never merged.
4. **Wake the human**: notify only after 1–3, with the parked report — not on the
   first red.

Brake the outer loop too. Per-baton bounds don't stop the *heartbeat* from
re-dispatching the same dead objective every pulse: once a baton parks `BLOCKED`, mark
the objective blocked in the anchor, page the human once, and have the heartbeat skip
blocked objectives (move to the next independent one) rather than re-attempt them. The
heartbeat must also refuse to dispatch the next baton if the integration branch isn't
clean. Encode the ladder in the Goal's Iteration and Pause-if elements
(`references/goal-contract.md`).

## Knowledge hygiene between cycles (a clean knowledge system)

Unattended loops are the most exposed to stale memory: nobody is watching when the
executor builds on a wrong premise. So reconcile your externalized memory (anchor,
inlined Handoff essence, project docs) on a cadence — each milestone or every N
batons, before the next cycle, not just at recovery. The mechanics and the
neat-freak / 洁癖-style cleanup pointer live in `references/commander-recovery.md`,
"Keep the externalized memory honest"; the autonomy tier just makes that reconcile
non-optional.

## Notify, don't disappear

Autonomy means you're not watching — it does not mean silence. Wire a notification
(push, chat, issue comment — environment-specific) for two events: **done** (with the
evidence summary and what landed) and **paused** (with the exact action needed). The
closed loop is discover → solve → verify → **notify**, not discover → solve →
vanish. Keep Handoff detail out of public channels; post a human-readable summary
only — and secret-scrub it: run the summary through the same `$ENV_VAR` rule as a
Handoff, or restrict it to a fixed template (objective, pass/fail, what landed, next
action). Never build the summary by quoting Handoff lines verbatim; unattended, nobody
eyeballs it before it posts.

## When NOT to use the autonomy tier

- Acceptance needs human taste/judgment (visual polish, product direction, UX calls).
- The work touches production, real credentials, or destructive/irreversible actions
  with no safe sandbox.
- A push/merge decision needs a human (most Class B integration boundaries).
- The verification can't be made machine-checkable yet — make it checkable first,
  *then* earn the autonomy. This is the same path as the non-negotiable "commander
  verification should become automation."

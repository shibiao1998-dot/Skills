# Repair flywheel - turning failures into a harder-to-break harness

Use this reference when a baton starts from a failed trace/log, production bug,
model upgrade regression, flaky agent behavior, or any task where "fix it" is not
enough. The goal is not just to repair one failure; it is to make the harness
harder to break next time.

## The loop to preserve

For failure-driven work, drive the baton through this loop:

```text
bad run / bad trace
-> reproduce or capture the original failure
-> diagnose the causal chain
-> identify the narrow fix surface
-> apply only the approved/focused fix
-> rerun the original input
-> lock the failure as a regression check
-> carry the learned trap into the next baton / blueprint
```

The commander still owns the gate. The executor can diagnose and propose or apply
within the Goal, but networked actions, public posts, production effects, and broad
product decisions stay with the commander.

## Repro Capsule

Every failure-driven Handoff should include a Repro Capsule. It is the smallest
packet that lets the commander or a future executor rerun the same failure without
reading the whole chat:

- original input or user path
- command, URL, API call, or browser flow that reproduces it
- branch/commit and relevant config
- failing signal before the fix
- trace/log/screenshot/evidence pointer
- sandbox limits that may change the result

If the original failure cannot be reproduced in the executor sandbox, say exactly
which boundary stops it and what the commander must run instead.

## Diagnostic repair record

Do not let a Handoff say only "fixed." It should state:

- failure observed
- causal chain across tool/model/retrieval/code steps
- root cause hypothesis
- exact fix surface, preferably files/functions
- proposed focused fix or applied fix
- rerun command against the original input

This record is what prevents the next baton from repeating the same investigation.

## Regression lock

The repaired failure must become a durable check whenever possible:

- unit/integration test for deterministic code paths
- eval assertion for model-output quality
- replay script for agent runs
- browser or API smoke for full-flow regressions
- manual checklist only when automation is not practical, with the reason recorded

For bugfix Goals, "green tests" is not enough. Stop-when should require a
regression lock or a named reason why only manual verification is possible.

## Baton trace

The executor log is useful but hard to query. When a project can afford it, keep a
small structured run trace in `.loop/runs/<task>-<leg>.jsonl`:

```jsonl
{"phase":"dispatch","goal":"goal-checkout-1.txt","commit":"abc1234"}
{"phase":"red","command":"pytest tests/test_coupons.py::test_expired_coupon_rejected","result":"failed as expected"}
{"phase":"green","command":"pytest tests/test_coupons.py::test_expired_coupon_rejected","result":"passed"}
{"phase":"handoff","status":"READY","handoff":"handoff-checkout-1.md"}
```

Do not make this a platform before it has to be one. A short JSONL trace plus
pointers to logs/screenshots is enough for most relay loops.

## Harness blueprint

When a loop produces a pattern worth reusing, distill it into a gitignored
blueprint such as `.loop/blueprints/<topic>.md`:

- trigger: what kind of task/failure this blueprint covers
- known truth sources
- verification ladder
- executor sandbox profile
- regression checks to carry
- traps from prior runs

Blueprints are not authoritative project docs. They are commander memory on disk:
useful starting points for future Goals, always subordinate to the repo's truth
sources.

## Two execution modes

- **Diagnosis-first mode.** Use for production failures, security/privacy risk,
  unclear root cause, or broad fix surfaces. The executor reproduces, diagnoses,
  proposes a diff plan, and stops for commander approval before file edits if the
  Goal says so.
- **Direct repair mode.** Use for narrow, sandbox-closable bugs. The executor may
  reproduce, fix, rerun, and lock the regression inside one baton.

Pick the mode in the Goal. Do not let the executor silently switch from diagnosis
to broad edits.

# Commander recovery — surviving your own restart

The relay loop puts all continuous memory in one place: you, the commander. That's
a single point of failure. Your session **will** be compacted or restarted, and if
"where we are" lives only in your context, the whole loop stalls the moment you
lose it — the executor has been changed to wait for your dispatch, so nothing moves
until a commander rebuilds the picture.

The fix is simple and non-optional: **externalize your state to disk** and keep a
recovery procedure.

## The loop-state anchor

Keep a tiny, always-current anchor in the loop-state directory (e.g.
`.loop/anchor.md`, or a pinned section at the end of the project's journal if it has
one). It records just enough to resume:

```markdown
# Loop anchor (commander's resume point)
- updated: {{date}}
- effort (north-star): {{one line — the durable mission this relay loop drives toward}}
- current milestone: {{the milestone the live batons ladder up to}}
- current baton: {{task + leg, e.g. "142 leg 2"}}, status {{dispatched | verifying | advancing}}
- last Goal dispatched: {{path/pointer to the assembled Goal, + the executor log path}}
- last Handoff received: {{handoff-<task>-<leg>.md}}
- last run trace: {{.loop/runs/<task>-<leg>.jsonl, or none}}
- latest blueprint candidate: {{.loop/blueprints/<topic>.md, or none}}
- latest handoff per task: {{142 → handoff-142-2.md; auth → handoff-auth-1.md; ...}}
- next intent: {{what the next baton should tackle}}
- authoritative status: {{pointer to the project's state file / issue tracker}}
```

This is deliberately small — it's a resume pointer, not a second source of truth.
For per-task authoritative state, point at whatever the project already uses (a
state file, the issue tracker); for the full narrative, point at the journal. The
anchor just tells a fresh commander which beat of the loop they're standing in.

## Goal layering in the anchor

The anchor carries the goal hierarchy so no baton loses the thread: the **north-star**
(the durable mission — `effort` above), the **current milestone** the live batons
ladder up to, and the **current baton**. Each Goal's Outcome should name the milestone
it serves (see `references/goal-contract.md`). In a long or unattended loop this is
what stops the executor from nailing a local target while drifting off the mission,
and it gives a resuming commander the *why* behind the current baton, not just the
*what*.

## Update discipline

The anchor is only useful if it's current. Write to it at the two moments that
change your position in the loop:

- **On dispatch** (step 3): set current baton + status `dispatched`, record the
  Goal pointer and the executor log path.
- **On receive/advance** (steps 5–7): record the Handoff received, bump status,
  update "latest handoff per task" and "next intent".

If the project keeps a running journal, append a one-line entry at the same moments
so the narrative and the anchor stay in sync.

## Keep the externalized memory honest (reconcile)

Externalized state is only an asset while it's true. Across a long loop the anchor,
the inlined Handoff essence, and the project docs drift from what's actually merged —
and an unattended executor will build on the drift. Reconcile on a cadence (each
milestone, or every N batons), not just at recovery:

- Anchor vs. authoritative status: does "current baton / latest handoff" match what's
  really landed? Trust the truth source; fix the anchor.
- Inlined essence vs. reality: is the branch/commit/no-go list you keep pasting into
  Goals still correct, or superseded?
- Project docs vs. code: have CLAUDE.md / specs drifted from what the loop changed?

A dedicated knowledge-cleanup pass (e.g. a neat-freak / 洁癖-style skill) is the right
tool for the docs side. The autonomy tier makes this non-optional
(`references/autonomy-heartbeat.md`).

## Recovery procedure (run at the start of any fresh/resumed session)

Before doing anything else in a relay effort you're resuming:

1. **Read the anchor.** It tells you the current baton and which beat you're in.
2. **Read the latest Handoff(s)** named in the anchor — the must-read Part A gives
   you the live state of the work-in-flight.
3. **Check authoritative status** — the project's state file / issue tracker — to
   confirm what's actually merged/landed (the anchor can lag a beat).
4. **List the loop-state dir** (`ls` handoffs + evidence) to sanity-check the relay
   history against the anchor.
5. **Read the run trace / blueprint if named** — for failure-driven work, this is
   where red/green/replay evidence and reusable traps are easiest to recover.
6. **Reconstruct your position** and resume the loop at the right beat: if a baton
   was `dispatched`, go find its executor log and pick up at "receive"; if you were
   `verifying`, resume verification; if `advancing`, write the next Goal.

If the anchor and reality disagree (e.g. a branch is already merged but the anchor
says verifying), trust the authoritative status, fix the anchor, and continue. The
anchor is a convenience; the project's truth sources are the truth.

## Why not just rely on the journal / state file?

You can, if the project has them — the anchor can be a section inside the journal.
The point isn't a specific file; it's that **the commander's position in the loop
must be reconstructable from disk by someone who wasn't in your session.** That
"someone" is usually future-you after a compaction, but it might be a teammate
picking up the effort. Either way, if they can `cat` their way back to "we're on
baton 142 leg 2, last Handoff says build on branch X, next do Y," the loop
survives. If they can't, it doesn't.

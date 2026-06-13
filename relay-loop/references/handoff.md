# The Handoff — the baton between threads

When an executor run ends, its last act is to write a Handoff. This is the only
thing that crosses from one memoryless executor thread to the next, and it's the
commander's primary input for verification. It has two audiences with different
needs, which is why it has two parts.

## Two parts, and why

A single "dump everything" handoff fails two ways: inlining it whole into the next
Goal bloats the prompt and dilutes the executor's attention, and the verification
narrative the commander wants is not what the next executor needs.

- **Part A — must-read (≤ ~1.5 KB).** The minimum the *next executor* needs to
  continue safely: the branch/commit to build on, the base commit, any
  migration/contract state, the no-go zones, and the traps this run hit. **This is
  the only part inlined into the next Goal.** Keeping it small is the commander's
  job — distilling it is exactly the high-value work you shouldn't outsource to
  "paste the whole thing".
- **Part B — full handoff.** The complete record for the *commander's
  verification*: item-by-item acceptance, evidence pointers, and — critically — a
  "what I did NOT verify" section. This **lands on disk**; it is not inlined into
  the next Goal.

> Why not just inline everything? Token cost grows with every baton if you do, and
> the next executor reads better from a tight must-read than from a long history.
> The full record is for you, the commander, when you verify — read it from disk.

## How it travels (and the leak rule)

The executor often runs in a sandbox whose filesystem you can't read directly. So:

1. The executor writes the Handoff into its sandbox's loop-state dir **and echoes
   the full text as its final terminal output.**
2. You (commander) read it from the executor's terminal log and **land it** into
   the real loop-state directory as a file.

**Never echo a Handoff verbatim into a public destination** (PR/issue comments,
chat that gets published). Handoffs routinely carry commands, endpoints, and config
that can include secrets. Public status posts get a short human-readable summary
and pointers only; the full Handoff stays in the gitignored loop-state dir.

## Naming — keyed to the task, not a global counter

Use `handoff-{{task-or-topic}}-{{leg}}.md`, e.g. `handoff-142-1.md`,
`handoff-142-2.md`, or `handoff-auth-refactor-1.md`.

- Key on the **task/issue id** (or a stable topic slug) so names are unique without
  any central coordinator. A single global monotonically-increasing number breaks
  under concurrent executors, session restarts, and multi-task interleaving — two
  legs can collide on the same name and silently overwrite each other (the loop-
  state dir isn't in git, so there's no diff to catch it).
- `{{leg}}` is the per-task leg number (1, 2, 3…). `ls` the loop-state dir to see a
  task's relay history.
- Track "latest handoff per task" in your loop-state anchor (see
  `references/commander-recovery.md`) rather than relying on filename ordering.

## The "what I did NOT verify" rule (defends against false-green)

The most dangerous Handoff isn't a dishonest one — it's an honestly optimistic one.
An executor reports its own checks as green, but its sandbox couldn't exercise the
real seam (e.g. a write that enqueues a job, with no worker running to consume it).
That false-green then propagates into the next baton, which builds on a foundation
that doesn't actually work.

So the template **forces a negative-evidence section**. The executor must state
what it did *not* cover: paths untested, assumptions made but not exercised, and —
explicitly — which leg of any end-to-end flow it actually verified. Results that
only reach a boundary (enqueued / persisted / returned-200) must be marked as such
("reached enqueue; consumer not verified — no worker in sandbox"), not checked off
as fully done. When you verify (step 6), aim your real-backend and visual checks
straight at this section.

## Template

```markdown
# Handoff · {{task-or-topic}} · leg {{leg}}
<!-- Baton between threads. Reference issues/PRs/diffs/journals by pointer; do not
     copy them. Executor writes this and echoes it as the final terminal output;
     commander lands it into the loop-state dir. -->

## Part A — must-read (keep ≤ ~1.5 KB; this is what gets inlined into the next Goal)
- prev_handoff: {{handoff-...-(leg-1).md, or none}}
- build on: {{branch @ commit, or "new branch from <base> @ commit"}}
- base: {{base branch @ commit}}
- migration/contract state: {{e.g. "added migration <rev>, down_revision <rev>"; or none}}
- no-go zones: {{areas the next leg must not touch}}
- traps (don't repeat): {{1-3 concrete gotchas this run hit}}

## Part B — full record (lands on disk; for commander verification)

### Status
{{READY = ready to verify & advance | PARTIAL = Goal not fully met but this run is
done (normal for Class B / out-of-sandbox steps) | BLOCKED = needs a human action}}

### Acceptance, item by item (against the Goal's Stop-when)
- [done] {{criterion}} — evidence: {{test name / file:line / screenshot path / command+result}}
- [partial] {{criterion}} — {{what's left, and why (e.g. "needs push + CI")}}
- [blocked] {{criterion}} — needs human: {{exact action}}

### What I did NOT verify (negative evidence — required)
- {{untested path / unexercised assumption}}
- end-to-end: {{which leg I actually verified vs. assumed; mark enqueue/persist-only
  results as "consumer/downstream NOT verified"}}

### Deliverables (precise coordinates)
- branch: {{name @ commit}}; base: {{@ commit}}
- migration: {{rev + down_revision, or none}}
- tests added/changed: {{file::case — re-runnable by the commander}}
- artifacts/screenshots: {{paths}}

### How to re-verify (commander's entry point — pointers, no secrets)
- {{commands to re-run, with results, e.g. "<test runner> <area> -> 298 passed"}}
- {{any flaky/known-red points}}
- secrets shown only as $ENV_VAR placeholders

### Next baton (material for the commander's next Goal — not executor self-direction)
- suggested next outcome: {{one line}}
- must carry: {{this Handoff's Part A + any contract/PR pointers}}
- explicitly do NOT: {{boundaries for the next leg}}

### Notes / decisions worth keeping
- {{anything not recorded elsewhere that would otherwise be lost}}
```

## Relation to the project's other status artifacts

The Handoff is a **single-leg baton snapshot**. It complements, and does not
replace, whatever the project already uses:

- **Public issue/PR comments** — the external signal to humans (claimed / blocked /
  ready / evidence summary). Human-readable summary only; no Handoff dump.
- **A running journal/log** — the full time-ordered narrative, if the project keeps
  one. The commander appends to it; the Handoff doesn't duplicate it.
- **A status table / state file** — the authoritative current state per task. The
  Handoff **points to it** ("authoritative status: see <state file>; this leg
  touched X, Y") and must not copy it — a copied status table rots immediately.

One hard rule worth enforcing in your own verification checklist: a Handoff must
*reference* the authoritative status, never reproduce it.

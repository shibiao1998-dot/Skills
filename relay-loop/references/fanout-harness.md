# Fan-out harness

Use this harness before dispatch when a relay task is non-trivial, ambiguous,
explicitly asks for multiple agents, or could benefit from independent exploration,
review, implementation, or verification. The harness turns "spawn agents" from a
loose instruction into a commander-owned split note that can be linted.

## Required order

1. Create a split note from the template below in the loop-state directory, e.g.
   `.loop/fanout/fanout-<task>-leg-1.md`.
2. Run `python3 relay-loop/scripts/lint_fanout.py <split-note>`.
3. Write one full Goal file per baton, then run
   `python3 relay-loop/scripts/lint_goal.py <goal-file> ...`.
4. Dispatch one executor per Goal, with one log path and one expected Handoff path.
5. Run `python3 relay-loop/scripts/lint_handoff.py <handoff-file> ...` on returned
   Handoffs.
6. Synthesize by the split note's plan, then run commander verification.

If the split note cannot pass lint, do not dispatch. Either narrow the task, switch
to read-only exploration batons, or use a single baton and record why.

## FANOUT / EXPLORE_FIRST split-note template

```text
# Relay Fan-out Split Note <task> leg <N>

## Fan-out decision
Mode: FANOUT
Reason: <why independent executors improve result quality>
Human gates remaining: <judgment / approval / production gates, or "none">

## Shared objective
<one concrete outcome shared by all batons>

## Truth sources
- <issue/spec/ADR/path/link>
- <project instruction path>

## Shared constraints
- <public APIs / schemas / branch rules / product invariants>
- Secret hygiene: use $ENV_VAR placeholders only.

## Sub-batons
### Baton A - <short name>
Type: read-only exploration | implementation | verification | review
Goal file: .loop/goals/goal-<task>-a.txt
Handoff file: .loop/handoffs/handoff-<task>-a.md
Log file: .loop/logs/executor-<task>-a.log
Ownership: <exact files/modules/questions this baton owns>
Allowed write surface: <none for read-only, or exact dirs/files>
Forbidden write surface: <dirs/files/modules this baton must not touch>
Verification surface: <commands/artifacts/evidence this baton must capture>
Stop when: <baton-local proof and Handoff requirement>
Pause if: <credentials/network/production/destructive/product decision/conflict>

### Baton B - <short name>
Type: read-only exploration | implementation | verification | review
Goal file: .loop/goals/goal-<task>-b.txt
Handoff file: .loop/handoffs/handoff-<task>-b.md
Log file: .loop/logs/executor-<task>-b.log
Ownership: <exact files/modules/questions this baton owns>
Allowed write surface: <none for read-only, or exact dirs/files>
Forbidden write surface: <dirs/files/modules this baton must not touch>
Verification surface: <commands/artifacts/evidence this baton must capture>
Stop when: <baton-local proof and Handoff requirement>
Pause if: <credentials/network/production/destructive/product decision/conflict>

## Collision rules
- <which baton owns each writable surface>
- <which shared files are read-only>
- <what happens if two Handoffs conflict>

## Synthesis plan
- <compare / merge / choose / integrate rule grounded in Handoff evidence>
- <commander action if Handoffs disagree>

## Verification plan
- Run `python3 relay-loop/scripts/lint_goal.py <goal-file> ...`.
- Run `python3 relay-loop/scripts/lint_handoff.py <handoff-file> ...`.
- <commander rerun / browser / API / CI / artifact check before advance>

## Dispatch checklist
- [ ] Split note lint passed.
- [ ] Every Goal file lint passed.
- [ ] One log path and one Handoff path per baton.
```

## SINGLE split-note template

Use this when you assessed fan-out and rejected it. It preserves the assessment so
future commanders do not repeat the same drift.

```text
# Relay Fan-out Split Note <task> leg <N>

## Fan-out decision
Mode: SINGLE
Reason: <why parallelism would lower quality or create unverifiable merge risk>
Human gates remaining: <judgment / approval / production gates, or "none">

## Shared objective
<one concrete outcome for the single baton>

## Truth sources
- <issue/spec/ADR/path/link>

## Shared constraints
- <public APIs / schemas / branch rules / product invariants>

## Single-baton rationale
<dependency order, shared write surface, product decision, or other reason fan-out is not used>

## Synthesis plan
- Single baton only; commander verifies against the Goal and Handoff.

## Verification plan
- Run `python3 relay-loop/scripts/lint_goal.py <goal-file>`.
- Run `python3 relay-loop/scripts/lint_handoff.py <handoff-file>`.
- <commander rerun / browser / API / CI / artifact check before advance>

## Dispatch checklist
- [ ] Split note lint passed.
- [ ] Goal file lint passed.
- [ ] One log path and one Handoff path recorded.
```

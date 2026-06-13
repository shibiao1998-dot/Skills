# Verification ladder + visual checks

Two ideas drive this file: (1) verification is a *ladder* — you don't claim done
until you've climbed as far as the work warrants; and (2) the executor's sandbox
can only reach the lower rungs, so the commander must personally cover the rest.
Skipping the top rungs is the single most common way a "green" baton turns out
broken.

## The ladder (discover the project's own commands; don't invent them)

The rung *shapes* are general; the *commands* come from the project (package
scripts, Makefile, CI config, test runners — discover them).

- **R1 — static + unit.** Lint/typecheck + unit tests. For a change, include a new
  test that fails before and passes after, so the test actually exercises the fix.
- **R2 — CI replica.** Reproduce the project's CI locally: build, migrations
  up/down if any, the full test suite — whatever the CI config does.
- **R3 — service level.** Bring the app/service up locally and exercise the changed
  endpoints/flows against real local data (verify persistence, not just a 200).
  Mock only true externals (paid APIs, third-party services); don't mock the thing
  under test.
- **R4 — real-browser end-to-end.** For anything user-facing: drive the actual UI
  through the full user path and capture screenshots. A console error counts as a
  failure. "Unit tests are green" does **not** substitute for this.
- **R5 — checklist.** Each acceptance criterion marked ✅/❌ with an evidence
  pointer (test name, screenshot path, command output). Only "waiting on a human"
  items may be parked as ⏸, with the needed action named.

For bugfix / bad-trace batons, add a failure-replay rung before claiming done:

- **FR — failure replay.** Use the Handoff's Repro Capsule to rerun the original
  input/path that failed. Confirm the old failing signal is gone and the Regression
  lock names a durable test/eval/replay/check. If the lock is manual-only, verify
  the reason and run the manual script/checklist.

Put the verification ladder for a baton directly into the Goal's Verification
element, with the discovered commands inlined — so the executor has no "I thought I
ran it" ambiguity.

## Sandbox reachability — who can climb which rung

This is the correction most people miss. A constrained executor sandbox (no
network, no database, no containers, no listening ports) **cannot honestly run the
upper rungs.** Don't write a Goal that asks the executor to self-prove something
its sandbox physically can't do — it will either stall or fake it.

| Rung | Usually reachable by | Notes |
|---|---|---|
| R1 | **executor** | unit/in-memory tests run fine in most sandboxes |
| R2 | **commander** (often) | needs DB/containers/build the sandbox may lack |
| R3 | **commander** | needs real services + data the sandbox can't bring up |
| R4 | **executor: mock-mode only** / **commander: real-backend** | the seam lives here |
| R5 | both | executor self-reports; commander confirms |
| FR | **commander** (often) | rerun original failure input; executor may lack the real services/data |

Practical rule: if a rung is out of the executor's reach, the Goal says so, the
executor stops at the highest rung it *can* reach and hands back `PARTIAL`, and the
commander climbs the rest after landing/pushing the work. This is the Class A vs.
Class B distinction from `SKILL.md`.

## Visual verification — three tiers

Visual checking isn't one step; it's three, with different owners and different
blind spots.

- **Tier 1 — executor self-check (front gate).** The executor uses its own
  built-in browser to walk the user path. But in a constrained sandbox this is
  typically **mock-mode only** (no real backend), so it is blind to front-back
  seam bugs — a mocked call returns success even when the real wiring is broken.
  Necessary, not sufficient.
- **Tier 2 — commander, real-backend, no login.** You bring up the real local
  backend and check the flow through a controlled-preview browser tool. **This is
  where you catch the seam bugs Tier 1 can't.** Do it for any Class B work or
  anything touching the front-back seam — not just the mock view.
- **Tier 3 — commander, real session.** When the flow needs real cookies, a logged-
  in session, or browser extensions, use a real-browser-control tool against an
  actual browser profile.

Map to the loop: Tier 1 is the executor's self-check before it hands back; Tiers 2
and 3 are your step-6 verification. Aim them at the Handoff's "what I did NOT
verify" section.

## Tools (environment-dependent — load before use)

The browser-control tools you'll use for Tiers 2–3 are environment-specific and
are often **not loaded by default** — they sit behind a tool-search/lazy-load
mechanism. Before your first visual check, load their schemas (e.g. via
`ToolSearch` in this environment); otherwise the first call fails with "tool not
available".

Canonical examples (yours may differ):

- **Controlled preview** (Tier 2): a sandboxed preview MCP such as *Claude Preview*
  (`mcp__Claude_Preview__*`) — clean, reproducible, doesn't touch the user's real
  browser. Good default for no-login local pages.
- **Real browser** (Tier 3): a real-Chrome control MCP such as *Claude in Chrome*
  (`mcp__Claude_in_Chrome__*`) — real cookies/sessions/extensions, for flows that
  need a true logged-in context.

If neither is available, fall back to a scripted headless browser (e.g. a
Playwright-style runner) and note the downgrade in your verification record.

## Evidence

Store evidence in the loop-state directory, e.g. `.loop/evidence/{{task}}/`, with
filenames keyed to the criterion they prove. The executor records pointers to its
evidence in the Handoff; you add yours from Tiers 2–3. Pointers, not pasted blobs —
and never paste secrets (use `$ENV_VAR`).

For failure-driven work, include the red/green/replay evidence separately when
possible:

- `*-red.txt` or screenshot: original failure signal
- `*-green.txt`: focused check after the fix
- `*-replay.txt` or screenshot: commander rerun against the original input
- `*-regression.txt`: proof the regression lock exists and runs

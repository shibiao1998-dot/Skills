# Loop blueprints — a relay-native catalog of common patterns

A blueprint is **not a prompt you send.** It is a pre-filled mapping from a common
task shape onto the relay-loop machinery: which of the seven Goal elements get what,
which baton class to expect, which verification rungs the commander must climb, and
what the Handoff must carry. You still discover the project's facts, assemble the
Goal from `references/goal-contract.md`, lint it, and dispatch. The blueprint just
saves you from re-deriving the *shape* of a CI-until-green or a test-triage loop
every time.

Use this catalog as a menu at step 1 (recover + plan + scope). Pick the family that
matches the work, then fill its fields from project discovery. If nothing fits
cleanly, compose from the closest two — the schema is the same for all of them.

> **Provenance.** These families synthesize the *structure* of public loop templates
> surveyed at `https://loops.elorm.xyz/loops`. They do **not** copy external kickoffs
> or install material. The relay-native value here is the mapping onto Goal / Handoff
> / verification, the anti-gaming block, and the commander-owned gate.

## Two senses of "blueprint" — don't conflate them

- **Catalog blueprints (this file).** Generic, skill-level starting points for common
  workflows. They are *families*, not project-specific.
- **Harness blueprints (`references/repair-flywheel.md`).** Project-specific commander
  memory distilled to `.loop/blueprints/<topic>.md` after a real loop — concrete
  commands, real truth-source paths, traps this repo hit. They are instances.

A catalog blueprint tells you which fields to fill; a harness blueprint records what
you filled them with last time, for this repo. When a run refines a pattern worth
keeping, the Handoff's `blueprint candidate` field (`references/handoff.md`) should
name the catalog family and point to the saved harness blueprint.

## The blueprint schema (eleven fields)

Every family below is described with the same fields, in this order:

1. **Category** — the task type (Testing, CI, Quality, …), for quick scanning.
2. **Trigger** — `manual` / `event` / `interval`. See the reframing below — none of
   these makes the *executor* run forever.
3. **Baton class** — Class A (sandbox-closable) or Class B (crosses a
   push/integration boundary), from `SKILL.md`. Decides whether `PARTIAL` is the
   expected outcome.
4. **When to use** — the trigger condition in plain terms; when *not* to reach for it.
5. **Truth sources to discover** — what the commander finds before writing the Goal
   (the Goal *references* these; it never copies or overrides them). Ecosystem-
   agnostic: discover the project's actual tooling, don't assume npm/JS.
6. **Per-pass check (first action → loop)** — the executor's first move, then the
   tight per-iteration check it repeats. Maps into the Goal's **Verification** and
   **Iteration** elements.
7. **Exit signal** — the concrete end-state. Maps into **Stop when**.
8. **Max passes** — the bounded retry budget before downgrading to read-only
   diagnosis. Maps into **Iteration** (never "keep trying").
9. **Anti-gaming rules** — the family-specific ways an executor could fake green,
   forbidden explicitly. Lives in the Goal's **Constraints / Integrity** block;
   `scripts/lint_goal.py` scans the *whole* Goal for a clause like it (a forbid-verb
   near a tests/checks/green object), so it must be stated, not just implied.
10. **Handoff additions** — what this family's Handoff must emphasize beyond the
    base template (`references/handoff.md`).
11. **Commander verification** — which ladder rung / visual tier *you* must climb
    yourself, because the executor's sandbox can't (`references/verify-and-visual.md`).

Fields 6–9 map onto the Goal's Verification, Iteration, Stop-when, and
Constraints/Integrity elements. The other Goal elements come from context, not a
template: Outcome from the family's purpose and *When to use*, Boundaries from the
baton class and scope, and *Pause if* from project discovery.

## Trigger semantics (the relay reframing — read before using `event`/`interval`)

The public templates split loops into `manual` / `event` / `interval`. That taxonomy
is useful, but in relay-loop it describes **what wakes the commander**, never a
license for the executor to self-perpetuate. The invariant is unchanged: **one
executor run per baton, commander-owned gate between batons.**

- **`manual`** — you decide to start; becomes one Goal baton directly.
- **`event`** — a project hook or signal (a failing CI run, a post-edit hook, a
  landed PR) fires the *commander* cycle, which dispatches **one** one-shot baton and
  gates the result. The executor is not a resident watcher.
- **`interval`** — an external scheduler/monitor (a `/loop` primitive, cron, a
  scheduled agent, CI) re-enters the *commander* cycle on a cadence and dispatches one
  baton per pulse. The executor still runs once and exits.

`event` and `interval` are the autonomy-tier triggers in
`references/autonomy-heartbeat.md`; using them unattended requires that tier's earned
gate (machine-verifiable Stop-when, named independent verifier, recorded human
sign-off, `Mode: AUTONOMOUS`). They never turn a memoryless executor into a daemon.

---

## 1. Test failure triage

- **Category:** Testing. *(synthesizes flaky-triage / test-until-green / reflexive-debug shapes)*
- **Trigger:** `manual`, or `event` on a failing-test report.
- **Baton class:** Class A for deterministic unit failures (sandbox-closable); Class
  B if the failure needs a real DB/services to reproduce.
- **When to use:** a named failing or flaky test, or a bad trace, that must go green
  with the cause actually fixed. Not for "the suite is slow" (that's not a failure).
- **Truth sources to discover:** the test runner and how to run a *single* case; the
  failing job in CI config; the issue/trace; any flaky-quarantine list; the project's
  test conventions.
- **Per-pass check (first action → loop):** first reproduce the named failure with the
  project's own runner on the single case; then per pass — run that case, read the
  full output, make one focused change, rerun. For flakiness, run the case N times to
  *characterize* the nondeterminism before changing anything.
- **Exit signal:** the originally-failing case is reliably green (for flaky, green
  across R repeats), the relevant surrounding suite is green, and a regression check
  exists that **fails before the fix** (red-first).
- **Max passes:** ~3 focused passes, then downgrade to read-only diagnosis and hand
  back PARTIAL with a root-cause hypothesis.
- **Anti-gaming rules:** do not delete, `skip`/`xfail`, or weaken the test; do not
  loosen the assertion; do not add a retry/sleep to mask flakiness; do not mock the
  unit under test. An honest red beats a faked green; flakiness gets characterized,
  not papered over.
- **Handoff additions:** Repro Capsule (original input/seed), Diagnostic repair
  record, red-first Regression lock; for flaky cases, the determinism evidence (N
  runs before/after).
- **Commander verification:** rerun the original failing input from the Repro Capsule
  (FR rung); diff the test files to confirm nothing was weakened; for Class B, climb
  R2/R3 yourself.

## 2. CI / PR until green

- **Category:** CI. *(synthesizes ship-PR-until-green / fix-CI-until-green / PR-babysitter shapes)*
- **Trigger:** `event` (a push, a failing CI run, a review comment) or `interval`
  (poll a PR). Both re-kick a one-shot **commander** baton — the executor does not poll.
- **Baton class:** almost always Class B — CI lives across the push/integration
  boundary and needs the network/remote. The executor closes the sandbox-reachable
  part (R2 CI replica locally), then hands back PARTIAL; the commander pushes and reads
  real CI.
- **When to use:** a PR that must reach green required checks; a red CI job to drive to
  green; resolving review feedback to closure. Not a substitute for actually
  understanding the failure.
- **Truth sources to discover:** the CI config (exact jobs/commands), the PR/issue and
  its acceptance, branch-protection and required-checks lists, the review threads.
- **Per-pass check (first action → loop):** first read the *actual* CI failure logs
  (never guess); reproduce the failing job locally where possible (R2); one focused fix
  per pass; rerun the local replica; then push and let real CI run (commander side).
- **Exit signal:** all **required** checks green on the real remote, review threads
  resolved, no check weakened — not "green locally".
- **Max passes:** bounded; if the same job stays red after N, park PARTIAL/BLOCKED with
  the failing log and the suspected cause.
- **Anti-gaming rules:** do not edit the CI config or required-checks list to drop,
  skip, or `allow_failure` a failing job; do not remove a gate; do not merge with an
  admin override; do not weaken the tests the job runs.
- **Handoff additions:** which jobs are confirmed green locally vs. only-real-CI-can-
  confirm (negative evidence); the push/merge boundary; branch @ commit.
- **Commander verification:** read the real remote CI yourself; confirm *required*
  checks (not just some) are green; diff the CI config in the PR to confirm no gate was
  dropped. The merge to a protected branch stays a human gate — never auto-merged while
  unattended (`references/autonomy-heartbeat.md`).

## 3. Post-edit / pre-commit / post-merge guard

- **Category:** Quality / DevOps (guard).
- **Trigger:** `event` — a lifecycle hook (post-edit, pre-commit, post-merge). The hook
  is the trigger that dispatches **one** guard baton; the executor does not become a
  resident watcher.
- **Baton class:** Class A (fast, local, scoped checks).
- **When to use:** keep a branch continuously green by running the right *scoped* checks
  at the moment of change, instead of discovering regressions at PR time. Not a place to
  run the whole suite — that's CI's job (blueprint 2).
- **Truth sources to discover:** which checks are cheap and fast enough for a hook
  (lint, typecheck, affected unit tests); the project's hook framework (pre-commit
  framework, git hooks, CI-on-push, an IDE hook); the changed-files → affected-tests
  mapping.
- **Per-pass check (first action → loop):** first run the scoped fast checks on the
  changed surface only; one focused fix; rerun. Keep scope to changed files / affected
  tests so the guard stays a guard.
- **Exit signal:** the scoped checks pass on the changed surface and nothing unrelated
  was touched.
- **Max passes:** small; a guard that can't go green fast hands back so a human/commander
  decides, rather than expanding scope.
- **Anti-gaming rules:** do not disable the hook, pass `--no-verify`, skip the check, or
  weaken it to pass. A silenced guard is worse than no guard — it reads as protection
  while protecting nothing.
- **Handoff additions:** which lifecycle point fired; the exact scoped surface checked;
  what was deliberately out of scope (the guard is narrow by design).
- **Commander verification:** confirm the hook actually runs the intended checks (not a
  no-op or a swallowed exit code) and that nothing was added to bypass it. The hook
  wiring itself is the thing to audit (`references/autonomy-heartbeat.md`, lifecycle
  hooks).

## 4. Independent verifier pass

- **Category:** Review / Verification.
- **Trigger:** `event` — a baton landed READY and needs an independent gate before
  advance. Usually one arm of a fan-out (`references/fanout-harness.md`).
- **Baton class:** read-only verification baton — owns **no** write surface, so it
  can't "fix" what it reviews (the fan-out linter enforces disjoint write surfaces).
- **When to use:** high-stakes or unattended work; doer ≠ checker; before advancing or
  merging a baton you can't fully eyeball; as the automated gate the autonomy tier
  depends on.
- **Truth sources to discover:** the Goal's acceptance criteria (read **directly**, not
  the doer's self-report); the verification-ladder commands; the diff under review.
- **Per-pass check (first action → loop):** re-derive evidence from a *clean checkout*
  by re-running the ladder itself; attack the seams the doer's sandbox couldn't reach;
  diff the tests/checks to confirm they weren't weakened. The prompt is **refute**, not
  confirm.
- **Exit signal:** the verifier re-ran the ladder green, found no real defect, and
  confirmed no weakened checks — and it states what it could *not* verify. A refuted
  claim routes into a fix baton; it does **not** advance.
- **Max passes:** one — the verifier is read-only and produces a verdict, not a series
  of fixes.
- **Anti-gaming rules:** the verifier must not trust the doer's evidence files or
  self-report, must read acceptance criteria directly, and must use the refute template.
  For the autonomy tier it MUST run on a *different model* and re-run from a clean
  checkout.
- **Handoff additions:** refutation findings; which rungs it independently re-ran;
  residual unverified items; the verdict (no-defect → advance | refuted → fix baton).
- **Commander verification:** this baton *is* part of the commander's verification
  automation — but the commander still owns the final gate and the merge decision. See
  `references/fanout-harness.md` (the independent verifier baton) and
  `references/autonomy-heartbeat.md` (the automated gate).

## 5. Spec-first ship

- **Category:** Planning → Quality.
- **Trigger:** `manual`.
- **Baton class:** Class A or B, depending on whether the feature crosses a
  push/integration boundary.
- **When to use:** there is a spec / PRD / issue with acceptance criteria and you want
  the build to map 1:1 to it. Not for exploratory work where the spec doesn't exist yet
  (write the spec first, or fan out read-only exploration — the EXPLORE_FIRST split-note
  decision in `references/fanout-harness.md`).
- **Truth sources to discover:** the spec/PRD/issue and its acceptance criteria (the
  authoritative source — on conflict, the spec wins); ADRs/glossary; existing contracts.
- **Per-pass check (first action → loop):** first turn each acceptance criterion into a
  checklist item with a concrete verification; then build one slice, verify it against
  its criterion, and repeat. The R5 acceptance checklist is the spine of the loop.
- **Exit signal:** every spec criterion is ✅ with an evidence pointer (or ⏸ waiting-on-
  human with the action named), the verification ladder is green, and nothing was built
  beyond the spec.
- **Max passes:** per-slice bounded; out-of-spec findings are recorded for the human,
  not built.
- **Anti-gaming rules:** do not silently descope or reinterpret a criterion to declare
  done; a criterion you can't meet is *reported*, not redefined; do not weaken the
  acceptance tests.
- **Handoff additions:** the criterion-by-criterion acceptance table (the base
  Handoff's "Acceptance, item by item"); what's out of spec; any spec ambiguity surfaced
  (a truth-source conflict is a Pause).
- **Commander verification:** walk the spec criteria yourself against the build; confirm
  the acceptance tests actually assert the criteria (not weakened); R4/R5 for the
  user-facing parts.

## 6. API / contract / migration

- **Category:** API / Database (contract-boundary baton).
- **Trigger:** `manual` (a contract change) or `event` (an upstream schema/OpenAPI
  change).
- **Baton class:** Class B — a contract or migration usually must be pushed and merged
  before downstream batons build on it, and full verification needs a real DB/services.
  Expect PARTIAL.
- **When to use:** an OpenAPI/proto/IDL change, a contract-test surface, or a DB
  migration other work depends on. Not for an internal refactor that doesn't cross a
  published boundary.
- **Truth sources to discover:** the API contract (OpenAPI/proto/IDL); the migration
  tool and its up/down convention; the contract tests; the consumer list; the DB.
- **Per-pass check (first action → loop):** first pin the change to the contract/spec
  and write or update the contract test red-first; run migrations **up and down** in a
  scratch DB; verify producer and consumer against the contract. One change per pass.
- **Exit signal:** contract tests green on both sides; migration up *and* down clean and
  reversible; the OpenAPI/schema in sync with code; no breaking change to the published
  contract unless the spec says so.
- **Max passes:** bounded; a contract conflict or a non-reversible migration is a Pause
  (it needs a decision), not an autonomous slog.
- **Anti-gaming rules:** do not loosen the contract test to pass; do not skip or drop
  the down-migration to "simplify"; do not hand-edit generated contract artifacts to
  fake sync; do not silently widen a type to dodge a real breaking change.
- **Handoff additions:** migration rev + down_revision (the base Handoff has this
  field); the push/merge boundary (Class B → PARTIAL expected); a consumer-impact note;
  the contract diff.
- **Commander verification:** run migration up/down yourself against a real DB (R2/R3);
  run the contract tests on both sides; confirm the published contract didn't silently
  break; you own the push/merge as the Class B step.

## 7. Visual / E2E verification

- **Category:** Quality (frontend / end-to-end).
- **Trigger:** `manual`, or `event` when a UI change lands.
- **Baton class:** Class B for the real-backend / E2E part. The executor reaches only
  Tier 1 (its own browser, usually mock-mode).
- **When to use:** anything user-facing; a UI change; an E2E flow that must be exercised
  through the real UI. Not satisfied by "unit tests are green".
- **Truth sources to discover:** the user path/flow under test; how to bring up the app
  with a real local backend; the E2E runner (discover it — e.g. a Playwright-style
  runner); the screenshot/evidence convention.
- **Per-pass check (first action → loop):** the executor drives Tier 1 (its own browser,
  typically mock-mode) and captures screenshots; the commander then climbs Tier 2
  (real-backend, no login) and Tier 3 (real session) where the front-back seam bugs
  live. A console error counts as a failure.
- **Exit signal:** the full user path passes through the *real* UI (R4) with
  screenshots, no console errors, and real-backend persistence verified (not just a
  200). Tier 2/3 are commander-owned.
- **Max passes:** executor-side bounded; the real-backend tiers are commander
  verification, not an executor loop.
- **Anti-gaming rules:** do not treat a mock-mode screenshot as proof a real flow works;
  do not assert a 200 without checking persistence; do not delete/skip the E2E case to
  go green; do not screenshot a stale or cached view.
- **Handoff additions:** which tier the executor actually reached (Tier 1 mock-mode); an
  explicit "what I did NOT verify" for the front-back seam; screenshot pointers under
  `.loop/evidence/...`.
- **Commander verification:** this blueprint *is* mostly commander verification — Tier 2
  and Tier 3 in `references/verify-and-visual.md`; load the browser-control schemas
  first, or note the downgrade to a headless runner.

## 8. Dependency / security maintenance

- **Category:** Maintenance / Security.
- **Trigger:** `interval` (a scheduled scan/update cadence) or `event` (a published
  advisory). The schedule/cron re-kicks a one-shot **commander** baton — the executor
  does not auto-upgrade on its own loop.
- **Baton class:** Class B — updates need the full suite, often the network to fetch,
  and a human gate before a bump merges.
- **When to use:** dependency updates, security advisories, lockfile maintenance —
  **commander-supervised**, never a blind auto-bump.
- **Truth sources to discover:** the dependency manifest and lockfile (ecosystem-
  discovered — e.g. `package.json`/lockfile, `requirements`/`poetry`, `go.mod`,
  `Cargo.toml`; discover, do not assume npm); the advisory/CVE; the test suite; the
  changelog/breaking-change notes of the bumped dependency.
- **Per-pass check (first action → loop):** scope **one** dependency (or one advisory)
  per baton; read its changelog for breaking changes; bump it; run the full suite +
  build; read the failures. One dep per pass, never a mass bump.
- **Exit signal:** the targeted dependency updated, full suite + build green, no new
  advisory introduced, and breaking changes addressed — or the bump reverted with a
  recorded reason.
- **Max passes:** bounded; a major-version bump with breaking changes is a Pause (a
  decision), not an autonomous slog.
- **Anti-gaming rules:** do not pin to a vulnerable version to "pass" a check; do not
  blanket-ignore advisories; do not `--force` / bypass peer-dependency conflicts to fake
  green; do not weaken a test that breaks under the new version — that break is a real
  signal.
- **Handoff additions:** the exact version delta (from → to); the advisory id;
  breaking-change findings; the merge gate (Class B → human decision); a Repro of any
  test that broke under the bump.
- **Commander verification:** run the full suite + build yourself post-bump; review the
  changelog/breaking changes; you decide the merge (a human gate). Never let an
  unattended loop auto-merge a dependency bump to a protected branch.

---

## Blueprint map — choosing the next baton

A blueprint also tells you what tends to come *next*, so the commander picks the next
baton deliberately instead of from memory. These chains are suggestions; the project's
truth sources still govern.

- **CI failure** → CI/PR until green (2) → independent verifier (4) → PR self-review →
  deploy/staging verification.
- **Test failure** → test failure triage (1) → regression lock → post-edit guard (3).
- **API change** → API/contract/migration (6) → contract test → OpenAPI/schema sync →
  staging smoke (7).

When a run produces a chain worth reusing for this repo, distill it into a harness
blueprint (`.loop/blueprints/<topic>.md`, `references/repair-flywheel.md`) and name the
catalog family in the Handoff's `blueprint candidate` field.

## Using a blueprint (the four moves)

1. **Pick + scope.** Choose the family at step 1; set the baton boundary. If two
   families overlap, compose them — the schema is shared.
2. **Fill from discovery.** Replace every "discover the project's…" with the project's
   actual tooling and truth sources. A blueprint never overrides project facts; it's
   subordinate to them.
3. **Assemble + lint.** Map the filled fields onto the seven Goal elements
   (`references/goal-contract.md`): per-pass check → Verification/Iteration; exit signal
   → Stop when; max passes → Iteration; anti-gaming rules → Constraints/Integrity;
   Outcome from the family's purpose + *When to use*; Boundaries from baton class +
   scope; *Pause if* from discovery. Run `scripts/lint_goal.py` (and
   `scripts/lint_fanout.py` if the blueprint fans out).
4. **Dispatch + gate.** One executor run per baton; you verify at the commander rung the
   blueprint names; the gate between batons stays yours.

The blueprint is a starting point, not an authority. If the family's defaults conflict
with what discovery turns up, discovery wins — and consider whether the family needs a
note for next time.

# Dispatching the executor

How to launch a baton, work around a constrained executor sandbox, and retrieve the
result — without blocking your session or tripping a safety rail.

## Launch in the background, tee to a log

The executor runs a single baton then exits. Launch it **in the background** so
your session stays free to plan and (later) verify, and **tee its output to a log**
so you can retrieve the echoed Handoff afterward.

Canonical executor is Codex via `codex exec`; the pattern fits any headless agent.

```bash
# The assembled Goal is your kick prompt. Keep it in a file to avoid shell-quoting
# pain, then pass it in. Tee to a per-baton log.
codex exec --full-auto "$(cat /path/to/goal-<task>-<leg>.txt)" \
  > "/tmp/executor-<task>-<leg>.log" 2>&1
```

- In an agent harness that supports it, prefer the harness's background mechanism
  (e.g. a "run in background" flag) so the run keeps going across turns and you're
  notified on completion. Otherwise append `&` and poll the log.
- One baton = one run = one log. Name the log after the task + leg so it lines up
  with the Handoff.
- For failure-driven work, also ask the executor to append key phase events to a
  lightweight run trace such as `.loop/runs/<task>-<leg>.jsonl` when it can write
  the loop-state dir: dispatch, red failure, fix, green check, replay, Handoff.
  Keep the terminal log as the source for raw detail.
- Don't block your session in a foreground wait. Plan the next move or step away;
  come back when the run reports done.

## Parallel fan-out dispatch

Parallel dispatch is a commander quality tactic for independent batons, not a way
to make one executor self-perpetuate. Use it liberally for read-only exploration,
independent reviews, competing diagnoses, and verification passes; use it for
implementation only when write surfaces and synthesis are clear. Before launching,
instantiate `references/fanout-harness.md` in the loop-state dir and run
`scripts/lint_fanout.py` on it. The split note must record:

- shared objective and truth sources
- each sub-baton's owner name, Goal file, allowed write surface, and log path
- collision rules for shared files, branches, ports, databases, and generated
  artifacts
- synthesis order: compare, merge, or choose one result, then verify yourself

Do not dispatch until the split note passes lint. If it fails because the write
surfaces collide or the synthesis plan is vague, switch to read-only exploration
batons, narrow ownership, or record `Mode: SINGLE` with a single-baton rationale.

Launch one executor per Goal, with one log and one expected Handoff per executor:

```bash
codex exec --full-auto "$(cat "/path/to/goal-<task>-<leg-a>.txt")" \
  > "/tmp/executor-<task>-<leg-a>.log" 2>&1 &

codex exec --full-auto "$(cat "/path/to/goal-<task>-<leg-b>.txt")" \
  > "/tmp/executor-<task>-<leg-b>.log" 2>&1 &
```

Keep their write surfaces disjoint unless the explicit purpose is read-only
analysis. If two Handoffs propose conflicting edits, the commander resolves the
conflict in a new synthesis baton or by hand-verified integration; do not ask the
parallel executors to coordinate through chat or shared mutable state.

## Don't fight the sandbox (denied = signal, not retry)

Executors run sandboxed on purpose. If the executor (or you, on its behalf) tries
to escalate — e.g. a "full access" sandbox flag — and the environment denies it,
**that denial is a decision, not a transient error. Do not retry it verbatim.**
Change approach or pause for the human. Looping on a denied action wastes the baton
and trains bad habits into your loop.

## Provision the executor (resources sufficient)

"Sufficient resources" is one of the three pillars (see `SKILL.md`): a baton fails
just as often from missing tools as from a vague goal. Before dispatch, make sure the
executor can actually reach what the work needs — and that the Goal names it:

- **Tools & connectors.** If the work touches GitHub, an issue tracker (Linear/Jira),
  chat (Slack), or a database, the executor needs that connector (often an MCP server)
  available in its environment, or the step becomes a commander hop. Decide which, and
  say so in the Goal.
- **Permissions & data.** Test fixtures, seed data, env vars (as `$ENV_VAR`), service
  endpoints — provision them or mark the rung commander-only.
- **Knowledge.** The truth-source pointers and the prior-baton essence are resources
  too; an under-briefed executor reinvents or guesses.

What the executor genuinely cannot be given (network, real production data, a
credential it shouldn't hold) is not a gap to paper over — it's a Class B boundary or
a Pause-if. Provision what you can; route the rest to the commander.

## Discover the executor's constraints, then encode the bypass

A constrained executor sandbox commonly has some of: **no network**, a **read-only
view of the main repo's `.git`**, **no listening ports**, **no database/
containers**. Discover which apply to yours (a first cheap baton can probe this),
because they decide baton granularity (Class A vs. B) and what must happen on *your*
side.

### The two-hop pattern (read-only repo + no network)

When the executor can't push to the remote and can't write the main repo's `.git`,
don't ask it to — split the networked steps to the commander:

1. **Executor works in a writable copy.** It clones/copies the repo into a writable
   temp area (origin pointing at the local repo), commits its work on a branch
   there, and — if it can — pushes that branch back to the local repo. If it can't
   even do that, it leaves the branch in the temp area and records the exact path
   in the Handoff.
2. **Commander does the networked hops.** You pick up the branch, push it to the
   real remote, open the PR, and post any comments. **All remote/networked actions
   and public posts are the commander's job.**

Generalize the principle even if your executor isn't this locked down: *the
executor produces commits somewhere you can reach; the commander performs every
networked or outward-facing step.*

## Paths with spaces — always quote

Repo or working paths can contain spaces. Every path you hand the executor (and
every Bash command you write) must be double-quoted, e.g.
`"$(cat "/some/path with spaces/goal.txt")"`. An unquoted spaced path is a classic
silent failure — the command splits and does the wrong thing.

## Secret hygiene at dispatch

- **Never put real secrets in the Goal.** Reference them only as `$ENV_VAR`. The
  executor reads real values from its own environment / a gitignored env file,
  uses them, and never prints them.
- **Never collect secrets back through the log.** The Handoff and the terminal log
  are not secret-safe channels. The Goal's secret-hygiene constraint plus the
  linter's secret scan are your guards; keep them on.
- If a baton genuinely needs a credential the executor doesn't have, that's a
  Pause-if, not a workaround.

## Retrieve the result

When the run finishes:

1. Read the log (`/tmp/executor-<task>-<leg>.log`) and extract the **echoed Handoff
   full text** (the executor's final output). Land it into the loop-state dir as
   `handoff-<task>-<leg>.md` (`references/handoff.md`).
2. Collect the produced branch/commit (per the Handoff's Part A), do the networked
   hops if needed (two-hop push, open PR), and move to verification
   (`references/verify-and-visual.md`).
3. If the run came back `BLOCKED`/`PARTIAL`, the Handoff tells you the exact action
   needed — do it (or escalate to the human), then start the next baton.
4. For long-running or unattended loops, send a human-readable completion or pause
   notification (push / chat / issue comment — environment-specific); keep Handoff
   detail out of public channels (`references/autonomy-heartbeat.md`).

## A note on autonomy vs. the leash

The executor doesn't re-kick itself — each baton is one run and then it stops. You
relaunch. That cadence is deliberate: it gives you a verification gate between every
baton. The contract (the Goal) is what lets the executor run far *within* a baton
without supervision; the relaunch is what keeps a human-checked checkpoint between
batons. Don't try to make the *executor* self-perpetuate — that throws away the gate.
(An external heartbeat may re-kick the loop only once the gate itself is automated;
that opt-in upgrade is `references/autonomy-heartbeat.md`, and it automates the gate
rather than removing it.)

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

## Don't fight the sandbox (denied = signal, not retry)

Executors run sandboxed on purpose. If the executor (or you, on its behalf) tries
to escalate — e.g. a "full access" sandbox flag — and the environment denies it,
**that denial is a decision, not a transient error. Do not retry it verbatim.**
Change approach or pause for the human. Looping on a denied action wastes the baton
and trains bad habits into your loop.

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

## A note on autonomy vs. the leash

The executor doesn't re-kick itself — each baton is one run and then it stops. You
relaunch. That cadence is deliberate: it gives you a verification gate between every
baton. The contract (the Goal) is what lets the executor run far *within* a baton
without supervision; the relaunch is what keeps a human-checked checkpoint between
batons. Don't try to make the executor self-perpetuate — that throws away the gate.

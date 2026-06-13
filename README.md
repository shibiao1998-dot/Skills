# Skills

A small collection of reusable, shareable skills for Claude Code and compatible
coding agents. Each skill is a self-contained directory you can drop into your
agent's skills folder — no project-specific paths, accounts, or secrets baked in.

## Skills in this collection

### `relay-loop`

> Drive a background coding agent (canonically **Codex** via `codex exec`) through
> repeated **plan → dispatch → verify → advance** cycles, with you — the strong
> reasoning model — staying in the loop as the commander.

The idea: a strong model is great at planning and judging, but expensive to run for
hours of grunt implementation; a cheaper headless agent is great at grinding, but
forgets everything between runs and can wander without a contract. `relay-loop`
splits the work along that seam.

**The mental model**

- **Commander** (you, the strong model): plan, write the contract, dispatch,
  verify (including real-browser visual checks), decide what's next. The only
  participant with continuous memory.
- **Executor** (a background `codex exec` run): a fresh, memoryless thread that does
  one *baton* of work autonomously, then exits. It can't read the skill or remember
  the last run — so the contract you send must be self-contained.
- **Goal contract**: the self-contained kick-prompt — seven elements (outcome,
  verification, constraints, boundaries, iteration, stop-when, pause-if) plus an
  operating brief and the handoff format.
- **Handoff**: the baton the executor writes when it finishes — the only thing that
  crosses from one thread to the next, and the commander's input for verification.

```
1 plan + scope the baton        (commander)
2 write the Goal contract       (commander)
3 dispatch in the background     ───►   4 executor runs autonomously (memoryless)
                                              │ writes a Handoff, echoes it
7 advance: integrate + next   ◄──   6 verify  ◄──   5 receive Handoff
        (new executor thread, carrying the prior Handoff's essence)
```

**Use it when** you want to drive Codex/a background agent through a build loop,
write a Goal/kick-prompt/spec for an executor, hand off between agent threads, run a
mostly-autonomous build with human-checked verification between steps, or save
tokens by keeping planning + verification on the strong model.

**What's inside**

```
relay-loop/
├── SKILL.md                       the commander's loop SOP (start here)
├── references/
│   ├── goal-contract.md           the Goal template + inlined executor brief (the heart)
│   ├── handoff.md                 two-part handoff protocol + template + naming
│   ├── verify-and-visual.md       verification ladder, sandbox reachability, visual tiers
│   ├── executor-dispatch.md       background dispatch, sandbox bypass, secret hygiene
│   └── commander-recovery.md      rebuild state after your session restarts
└── scripts/
    └── lint_goal.py               sanity-check a Goal before dispatch
```

## Installing a skill

Skills are plain directories. To use one in Claude Code, place it where your agent
discovers skills (commonly `~/.claude/skills/`):

```bash
git clone https://github.com/<owner>/Skills.git
# Option A — copy:
cp -r Skills/relay-loop ~/.claude/skills/relay-loop
# Option B — symlink (so updates here flow through; good while iterating):
ln -s "$(pwd)/Skills/relay-loop" ~/.claude/skills/relay-loop
```

Then just ask for the workflow in natural language — e.g. *"use relay-loop to drive
codex through implementing X and verify its work."* The skill triggers from its
description; you don't have to name it.

> The executor side (Codex) needs **nothing** installed: `relay-loop` makes every
> Goal self-contained, so the operating brief and handoff format travel inside the
> Goal you dispatch. Only the commander side loads the skill.

## Iterating

The skill is built to evolve: `SKILL.md` holds the orchestration, `references/`
holds load-on-demand depth (edit a reference without touching the SOP), and
`scripts/lint_goal.py` encodes the quality bar for a Goal. Run the linter on a
sample Goal after edits:

```bash
python3 relay-loop/scripts/lint_goal.py path/to/some-goal.txt
```

If you use the `skill-creator` skill, you can also run its eval harness against
`relay-loop` to benchmark changes. Contributions and new skills welcome — keep them
general (no personal paths, accounts, or secrets).

## License

MIT — see [LICENSE](LICENSE).

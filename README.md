# Skills

A small collection of personal, reusable skills for Claude Code and compatible
coding agents.

Each skill lives in its own top-level directory and is maintained as an
independent module. The modules do not share runtime state and do not need to be
installed together.

## Skills in this repository

| Skill | Purpose | Best for |
| --- | --- | --- |
| `relay-loop` | Orchestrates a commander/executor work loop for background coding agents. | Long-running implementation work where a strong model plans and verifies while a headless executor handles bounded batons of work. |
| `dify-dsl-builder` | Designs, repairs, validates, and import-tests Dify / AI Hub Workflow and Chatflow DSL projects. | Building production DSL files, AIGC workflows, code-node contracts, validation reports, and AI Hub compatibility checks. |

## `relay-loop`

`relay-loop` is a workflow skill for driving a background coding agent through
repeated plan, dispatch, verify, and advance cycles.

The strong reasoning model acts as the commander. It discovers the project,
writes a self-contained Goal contract, dispatches a fresh executor run, receives
the executor Handoff, verifies the result, and then decides the next baton.

Use it when you want to:

- hand a bounded implementation slice to `codex exec` or another headless agent;
- keep long-running work moving without losing state between executor runs;
- force every executor run to stop with explicit verification evidence and a
  reusable Handoff;
- save stronger-model tokens by reserving them for planning, review, and
  verification.

Module layout:

```text
relay-loop/
├── SKILL.md
├── references/
│   ├── commander-recovery.md
│   ├── executor-dispatch.md
│   ├── goal-contract.md
│   ├── handoff.md
│   └── verify-and-visual.md
└── scripts/
    └── lint_goal.py
```

## `dify-dsl-builder`

`dify-dsl-builder` is a Dify / AI Hub DSL production skill. It helps an agent
turn workflow requirements into validated DSL deliverables, or repair existing
DSL exports while preserving business semantics.

Use it when you want to:

- clarify and design a Dify Workflow or Chatflow DSL;
- repair an existing DSL that fails static validation, import, canvas rendering,
  code-node execution, tool-node shape, or AIGC runtime contracts;
- build AI Hub AIGC production flows using native media-generation components;
- produce project deliverables such as a versioned DSL, README, validation
  report, and project memory;
- run static validators and optional AI Hub preflight checks before claiming a
  DSL is ready.

Module layout:

```text
dify-dsl-builder/
├── SKILL.md
├── agents/
├── assets/
│   └── fixtures/
├── references/
├── scripts/
└── tests/
```

## Installation

Skills are plain directories. Install only the modules you need by copying or
symlinking the top-level skill directory into the skills directory used by your
agent.

Clone the repository:

```bash
git clone https://github.com/<owner>/Skills.git
cd Skills
```

Install for Claude Code, commonly under `~/.claude/skills/`:

```bash
mkdir -p ~/.claude/skills
cp -R relay-loop ~/.claude/skills/relay-loop
cp -R dify-dsl-builder ~/.claude/skills/dify-dsl-builder
```

Install for Codex, commonly under `~/.codex/skills/`:

```bash
mkdir -p ~/.codex/skills
cp -R relay-loop ~/.codex/skills/relay-loop
cp -R dify-dsl-builder ~/.codex/skills/dify-dsl-builder
```

During active development, symlink instead of copying so edits in this repository
are picked up by the agent:

```bash
ln -s "$(pwd)/relay-loop" ~/.claude/skills/relay-loop
ln -s "$(pwd)/dify-dsl-builder" ~/.claude/skills/dify-dsl-builder
```

Adjust the destination path if your agent uses a different skills directory.

## Validation

Each skill owns its own checks.

For `relay-loop`, lint a Goal contract before dispatch:

```bash
python3 relay-loop/scripts/lint_goal.py path/to/goal.txt
```

For `dify-dsl-builder`, run the validator against a DSL file:

```bash
python3 dify-dsl-builder/scripts/validate_dify_dsl.py path/to/workflow.yml
```

The DSL Builder also includes focused tests and audit scripts under
`dify-dsl-builder/scripts/` and `dify-dsl-builder/tests/`.

## Maintenance

Keep each skill self-contained:

- put shared operating instructions in that skill's `SKILL.md`;
- put load-on-demand depth in that skill's `references/`;
- put reusable checks and helper commands in that skill's `scripts/`;
- avoid project-specific paths, accounts, credentials, or private runtime state.

Adding a new personal skill should mean adding a new top-level directory, not
merging it into an existing module.

## License

MIT. See [LICENSE](LICENSE).

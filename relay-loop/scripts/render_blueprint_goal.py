#!/usr/bin/env python3
"""Render a Goal-contract draft from a relay-loop blueprint (Phase 3).

This is a scaffolder, not an autopilot. Given a blueprint family, a task slug, and a
one-line outcome, it renders the seven Goal-contract elements specialised for that
family — with the standard anti-gaming guardrail block baked in (including the
check-command/exit-criteria guardrail that ``scripts/lint_goal.py`` requires of
green-class Goals) — and leaves the project-specific values as ``{{double-brace}}``
placeholders for the commander to fill from discovery. The draft is intentionally NOT
lint-clean until those blanks are filled; that is the commander's job.

Output defaults to the gitignored ``.loop/goals/goal-<task>.txt`` so generated drafts
never pollute the tracked repo. See ``references/loop-blueprints.md`` for the families
and ``references/goal-contract.md`` for the contract these drafts instantiate.

Usage:
    python3 render_blueprint_goal.py --list
    python3 render_blueprint_goal.py --blueprint ci-until-green --task 318 \
        --outcome "Drive PR #318 CI to green by fixing the real failing jobs"
    python3 render_blueprint_goal.py --blueprint independent-verifier --task 318 \
        --outcome "..." --stdout
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import TypedDict


class Blueprint(TypedDict):
    name: str
    category: str
    trigger: str
    baton_class: str
    focus: str
    truth: str
    verification: list[str]
    boundaries: str
    pause: str
    failure_driven: bool


# Each family contributes its category/trigger/class header, a focus line, and the
# family-specific bullets for Truth sources / Verification / Boundaries / Pause-if. The
# shared skeleton (below) supplies everything common, including the full anti-gaming
# block. ``failure_driven`` adds the red-first + Repro Capsule requirement so the draft
# matches ``lint_goal.py``'s expectations for bugfix work.
BLUEPRINTS: dict[str, Blueprint] = {
    "test-failure-triage": {
        "name": "Test failure triage",
        "category": "Testing",
        "trigger": "manual / event",
        "baton_class": "A (usually sandbox-closable)",
        "focus": "Reproduce, fix, and lock a named failing or flaky test — cause fixed, not silenced.",
        "truth": "the test runner and how to run a single case; the failing test/trace; any flaky-quarantine list",
        "verification": [
            "Reproduce the named failure with the project's own runner on the single failing case; capture the failing signal.",
            "Apply one focused fix; rerun that case and read the full output before retrying.",
        ],
        "boundaries": "the failing test and the code under it",
        "pause": "the failure needs real services or data the sandbox cannot provide",
        "failure_driven": True,
    },
    "ci-until-green": {
        "name": "CI / PR until green",
        "category": "CI",
        "trigger": "event / interval",
        "baton_class": "B (crosses a push/integration boundary)",
        "focus": "Get every required check on the real pipeline green by fixing failures, never by touching the gate.",
        "truth": "the CI config (the exact jobs/commands), the branch-protection required-checks list, the PR/issue acceptance",
        "verification": [
            "Read the failing job's logs from the real CI run; do not guess the cause.",
            "Reproduce each failing job locally with the project's own command (discover it) and capture the red/green result lines.",
            "After pushing, confirm on the real remote that every required check is green; capture the run URL and the check list.",
        ],
        "boundaries": "the source and tests needed to fix the failing jobs",
        "pause": "a protected-branch merge or a production deploy is required",
        "failure_driven": False,
    },
    "post-edit-guard": {
        "name": "Post-edit / pre-commit / post-merge guard",
        "category": "Quality / DevOps",
        "trigger": "event (a lifecycle hook)",
        "baton_class": "A (fast, scoped, local)",
        "focus": "Run the right scoped checks at the moment of change; stay a guard, not a full CI run.",
        "truth": "which fast checks fit a hook (lint/typecheck/affected tests), the hook framework, the changed-to-affected mapping",
        "verification": [
            "Run the scoped fast checks on the changed surface only (discover the commands) and capture the result lines.",
            "Confirm nothing unrelated was touched and the guard stayed narrow.",
        ],
        "boundaries": "the changed surface and its affected tests only",
        "pause": "the guard cannot go green quickly and needs a human decision",
        "failure_driven": False,
    },
    "independent-verifier": {
        "name": "Independent verifier pass",
        "category": "Review / Verification",
        "trigger": "event (a baton landed READY)",
        "baton_class": "read-only verification (owns no write surface)",
        "focus": "Refute, do not confirm: re-derive the evidence from a clean checkout and attack the seams.",
        "truth": "the acceptance criteria read directly (not the doer's self-report), the ladder commands, the diff under review",
        "verification": [
            "From a clean checkout, re-run the full ladder yourself (lint/typecheck/tests/CI replica — discover the commands) and capture each result line.",
            "Diff the test and check files and confirm none were deleted, loosened, or mocked away; record what you could NOT verify.",
        ],
        "boundaries": "nothing in the repo — write only the verdict and evidence pointers in the Handoff",
        "pause": "the branch under review cannot be checked out, or verification needs network/credentials the sandbox denies",
        "failure_driven": False,
    },
    "spec-first-ship": {
        "name": "Spec-first ship",
        "category": "Planning / Quality",
        "trigger": "manual",
        "baton_class": "A or B (depends on the push boundary)",
        "focus": "Map the build 1:1 to the spec's acceptance criteria; build nothing beyond them.",
        "truth": "the spec/PRD/issue and its acceptance criteria (the authoritative source), ADRs, the glossary",
        "verification": [
            "Turn each spec acceptance criterion into a checklist item with a concrete check; build one slice and verify it against its criterion.",
            "Run the discovered lint/test commands and capture evidence per criterion (mark each met/unmet with a pointer).",
        ],
        "boundaries": "only what the spec requires",
        "pause": "a spec ambiguity or a truth-source conflict needs a product decision",
        "failure_driven": False,
    },
    "api-contract-migration": {
        "name": "API / contract / migration",
        "category": "API / Database",
        "trigger": "manual / event",
        "baton_class": "B (push/merge before downstream builds on it)",
        "focus": "Treat the published contract and the migration as a boundary: reversible, in sync, no silent break.",
        "truth": "the API contract (OpenAPI/proto/IDL), the migration tool and its up/down convention, the contract tests, the consumers",
        "verification": [
            "Pin the change to the contract or contract test; run migrations up AND down in a scratch database and capture both results.",
            "Verify producer and consumer against the contract and confirm the published contract did not break unless the spec says so.",
        ],
        "boundaries": "the contract, the migration, and their tests",
        "pause": "a non-reversible migration or a breaking change to the published contract needs a decision",
        "failure_driven": False,
    },
    "visual-e2e": {
        "name": "Visual / E2E verification",
        "category": "Quality (frontend / E2E)",
        "trigger": "manual / event",
        "baton_class": "B (executor reaches mock-mode only)",
        "focus": "Exercise the real UI against a real backend; a mock-mode screenshot is not proof.",
        "truth": "the user path under test, how to bring up the app with a real local backend, the end-to-end / screenshot runner",
        "verification": [
            "Bring up the real local backend and drive the full user path through the actual UI; do not rely on a mock-mode view; a console error counts as a failure.",
            "Capture screenshots and a screenshot diff against the agreed baseline, and confirm persistence by round-trip rather than a bare 200.",
        ],
        "boundaries": "the end-to-end / screenshot test and its baseline artifacts",
        "pause": "a real login session, production data, or a design decision is required",
        "failure_driven": False,
    },
    "dependency-security": {
        "name": "Dependency / security maintenance",
        "category": "Maintenance / Security",
        "trigger": "interval / event",
        "baton_class": "B (full suite + a human merge gate)",
        "focus": "Commander-supervised, one dependency per baton — never a blind mass bump.",
        "truth": "the dependency manifest and lockfile (ecosystem-discovered, not assumed npm), the advisory/CVE, the changelog",
        "verification": [
            "Scope ONE dependency or advisory; read its changelog for breaking changes; bump it and run the full suite plus build (discover the commands).",
            "Confirm no new advisory is introduced and breaking changes are addressed, or revert the bump with a recorded reason.",
        ],
        "boundaries": "one dependency per baton and the code it breaks",
        "pause": "a major-version bump with breaking changes, or merging the bump, needs a decision",
        "failure_driven": False,
    },
}

# The reusable standard anti-gaming block (see references/goal-contract.md), baked into
# every generated draft so a green-class draft already carries the check-command
# guardrail lint_goal.py requires.
ANTIGAMING_LINE = (
    "  - Integrity (anti-gaming): never delete, skip, disable, weaken, or loosen "
    + "tests/assertions to reach green; and never modify, rewrite, relax, or replace the "
    + "check command, the exit/stop criteria, or the acceptance gate to force a pass. If a "
    + "check cannot pass honestly, hand back PARTIAL/BLOCKED — a faked green is worse than "
    + "an honest red."
)


def render_goal(blueprint_key: str, task: str, outcome: str) -> str:
    """Render a Goal-contract draft for ``blueprint_key``. Project-specific values are
    left as ``{{...}}`` placeholders; fill them, then run ``scripts/lint_goal.py``."""
    if blueprint_key not in BLUEPRINTS:
        choices = ", ".join(sorted(BLUEPRINTS))
        raise ValueError(f"unknown blueprint {blueprint_key!r}; choose from: {choices}")
    bp = BLUEPRINTS[blueprint_key]

    out: list[str] = []
    out.append(
        "# Blueprint: " + bp["name"] + " — category " + bp["category"]
        + "; trigger " + bp["trigger"] + "; baton class " + bp["baton_class"] + "."
    )
    out.append("# " + bp["focus"])
    out.append(
        "# Generated draft for task " + task + ". Fill the double-brace placeholders "
        + "from project discovery, then run scripts/lint_goal.py on this file."
    )
    out.append("")
    out.append("/goal " + outcome)
    out.append("")

    out.append("Truth sources (reference, do NOT copy or override; on conflict the truth source wins):")
    out.append('  - Task: {{issue/ticket id + where its acceptance criteria live, or "none"}}')
    out.append("  - " + bp["truth"] + " (discover the concrete paths/commands).")
    out.append('  - Prior progress: {{the previous Handoff\'s must-read excerpt, or "none — this is the first baton"}}')
    out.append("")

    out.append("Verification (concrete evidence only — discover the project's own commands first):")
    for bullet in bp["verification"]:
        out.append("  - " + bullet)
    if bp["failure_driven"]:
        out.append(
            "  - Reproduce the original failing input; confirm the regression check fails "
            + "before the fix (red), then make it pass. Preserve the Repro Capsule and a "
            + "red-first regression lock."
        )
    out.append("")

    out.append("Constraints (what must not change):")
    out.append("  - {{invariants this baton must not change: public APIs / data shapes / schemas / styles / branch rules}}")
    out.append(ANTIGAMING_LINE)
    out.append("  - Secret hygiene: never read, print, or commit real credentials; refer to them only as $ENV_VAR placeholders.")
    out.append("")

    out.append("Boundaries (where you may write):")
    out.append("  - Write only " + bp["boundaries"] + ". Do not touch {{forbidden paths/modules}} or do unrelated refactors.")
    out.append("  - Out-of-scope findings → record them for the human; do not act.")
    out.append("")

    out.append("Iteration policy (how to make progress, and the brakes):")
    out.append(
        "  - Discovery first: read the truth sources and the prior excerpt, then list your "
        + "assumptions. One focused change at a time; rerun the relevant check after each; "
        + "read logs before retrying. If the same failure persists twice, switch evidence "
        + "source (full traceback / docs / minimal repro). After {{N, e.g. 3}} focused passes "
        + "without success, hand back PARTIAL with a root-cause hypothesis — do not broaden scope."
    )
    out.append("")

    stop = (
        "  - {{acceptance criteria met, item by item}} AND the verification above is green "
        + "or any gap is reported AND evidence is captured."
    )
    if bp["failure_driven"]:
        stop += (
            " The original failing input has been rerun and the failure is locked by a "
            + "red-first test/eval/replay/check."
        )
    stop += " Then write the Handoff (Part A/B per references/handoff.md) and echo its full text."
    out.append("Stop when (proof of completion + deliver the baton):")
    out.append(stop)
    out.append("")

    out.append("Pause if (stop and escalate — do NOT work around):")
    out.append(
        "  - " + bp["pause"] + "; or anything needing credentials / network push / production "
        + "data / destructive actions / a product decision; or a truth-source conflict; or the "
        + "same failure blocks you {{M, e.g. 3}} times. Then write a BLOCKED Handoff naming the "
        + "exact action you need."
    )
    out.append("")

    out.append("--- Executor operating brief + Handoff format ---")
    out.append(
        "When dispatching, inline the standard executor brief from references/goal-contract.md "
        + "and the Handoff template from references/handoff.md verbatim below this line. (Omitted "
        + "in this generated draft, which renders the seven contract elements for the blueprint.)"
    )
    return "\n".join(out)


def _list_blueprints() -> None:
    print("Available blueprints (key — category — name):")
    for key in sorted(BLUEPRINTS):
        bp = BLUEPRINTS[key]
        print(f"  {key:24} {bp['category']:22} {bp['name']}")


def _load_lint_goal():
    """Load the sibling lint_goal module by path (robust regardless of sys.path)."""
    path = Path(__file__).resolve().parent / "lint_goal.py"
    spec = importlib.util.spec_from_file_location("lint_goal", path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load lint_goal.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _print_fill_checklist(draft: str, source: Path) -> None:
    """Best-effort: lint the draft so the unfilled placeholders surface as a to-do list.
    The generator deliberately produces a draft that is not yet lint-clean."""
    try:
        lint_goal = _load_lint_goal()
    except Exception:
        print("  fill the {{...}} placeholders, then run scripts/lint_goal.py on the draft.")
        return
    issues = lint_goal.lint_text(draft, str(source))
    if not issues:
        print("  draft already passes lint_goal.py — fill any remaining specifics and dispatch.")
        return
    print(f"  {len(issues)} item(s) to resolve before dispatch (mostly unfilled placeholders):")
    for issue in issues:
        print("   - " + issue.split(": ", 1)[-1])


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Render a relay-loop Goal-contract draft from a blueprint family.",
    )
    parser.add_argument("--blueprint", help="blueprint family key (see --list)")
    parser.add_argument("--task", help="task/topic slug; used in the filename and as context")
    parser.add_argument("--outcome", help="one-line concrete outcome for the /goal line")
    parser.add_argument("--out-dir", default=".loop/goals", help="output directory (default: .loop/goals)")
    parser.add_argument("--stdout", action="store_true", help="print to stdout instead of writing a file")
    parser.add_argument("--force", action="store_true", help="overwrite an existing draft file")
    parser.add_argument("--list", action="store_true", help="list available blueprints and exit")
    args = parser.parse_args(argv[1:])

    if args.list:
        _list_blueprints()
        return 0

    missing = [name for name in ("blueprint", "task", "outcome") if not getattr(args, name)]
    if missing:
        parser.error("missing required argument(s): " + ", ".join("--" + m for m in missing))

    try:
        draft = render_goal(args.blueprint, args.task, args.outcome)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    text = draft if draft.endswith("\n") else draft + "\n"
    if args.stdout:
        sys.stdout.write(text)
        return 0

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"goal-{args.task}.txt"
    if path.exists() and not args.force:
        print(f"{path} already exists; pass --force to overwrite", file=sys.stderr)
        return 2
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")
    _print_fill_checklist(draft, path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

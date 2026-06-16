#!/usr/bin/env python3
"""Tests for relay-loop Goal linting."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "lint_goal.py"
EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
SPEC = importlib.util.spec_from_file_location("lint_goal", SCRIPT_PATH)
lint_goal = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(lint_goal)


GOOD_GOAL = """/goal Fix coupon expiry validation so expired coupons are rejected with a focused regression test.

Truth sources:
  - Task: ISSUE-142 acceptance criteria.
  - Contracts/specs: pricing rules in docs/pricing.md.
  - Prior progress: none.

Verification:
  - Run `pytest tests/test_coupons.py::test_expired_coupon_rejected` and capture the red and green result lines.
  - Run `python -m pytest tests/test_coupons.py` for the targeted suite.

Constraints:
  - Do not change public coupon API names, database schema, or payment-provider config.
  - Integrity (anti-gaming): never delete, skip, or weaken tests/assertions to fake a green; an honest red beats a faked green.
  - Secret hygiene: use $ENV_VAR placeholders only.

Boundaries:
  - Write only src/checkout/coupons.py and tests/test_coupons.py.
  - Do not touch migrations or unrelated checkout code.

Iteration policy:
  - Discovery first, then one focused change at a time. If the same failure persists twice, read the full traceback and reduce to a minimal repro. Stop after 3 focused passes.

Stop when:
  - The regression test fails before the fix and passes after, targeted pytest is green, and the Handoff is written with evidence.

Pause if:
  - Credentials, network push, production data, destructive actions, or product decisions are required.
"""


# A Goal that has mechanically earned the right to run unattended (Mode: AUTONOMOUS):
# machine-verifiable Stop-when, a named independent verifier, and a recorded human
# sign-off. Built from GOOD_GOAL so the two stay in sync.
AUTONOMOUS_GOAL = (
    GOOD_GOAL.replace(
        "/goal Fix coupon expiry validation so expired coupons are rejected with a focused regression test.",
        "/goal Fix coupon expiry validation so expired coupons are rejected with a focused regression test.\n\nMode: AUTONOMOUS",
    ).replace(
        "  - Run `python -m pytest tests/test_coupons.py` for the targeted suite.",
        "  - Run `python -m pytest tests/test_coupons.py` for the targeted suite.\n"
        + "  - Independent verifier: a different-model verifier baton re-runs this ladder and refutes (handoff-142-verify.md).",
    )
    + "\nAutonomy sign-off: human-approved eligibility checklist recorded at .loop/autonomy-142.md.\n"
)


# A "green-class" Goal: its purpose is to reach/keep checks green (the CI-until-green
# family). It keeps GOOD_GOAL's general anti-gaming clause (which only forbids weakening
# tests) but says nothing about rewriting the check command / exit criteria themselves —
# the vector this class is most tempted to game. Built from GOOD_GOAL to stay in sync.
GREEN_CLASS_GOAL = GOOD_GOAL.replace(
    "/goal Fix coupon expiry validation so expired coupons are rejected with a focused regression test.",
    "/goal Drive the checkout CI pipeline until all required checks are green, fixing the real failures.",
).replace(
    "  - The regression test fails before the fix and passes after, targeted pytest is green, and the Handoff is written with evidence.",
    "  - All required CI checks pass and stay green on the real pipeline, and the Handoff is written with evidence.",
)


# The same green-class Goal, now carrying the check-tampering guardrail. It must pass:
# the rule requires the guardrail, it does not forbid green-class Goals.
GREEN_CLASS_GOAL_OK = GREEN_CLASS_GOAL.replace(
    "  - Integrity (anti-gaming): never delete, skip, or weaken tests/assertions to fake a green; an honest red beats a faked green.",
    "  - Integrity (anti-gaming): never delete, skip, or weaken tests/assertions to fake a green; "
    + "and never modify, rewrite, or relax the check command or the exit/stop criteria to force a pass. An honest red beats a faked green.",
)


class LintGoalTests(unittest.TestCase):
    def lint(self, text: str) -> list[str]:
        return lint_goal.lint_text(text, "goal.txt")

    def test_good_goal_passes(self) -> None:
        self.assertEqual([], self.lint(GOOD_GOAL))

    def test_bracketed_prompt_template_placeholder_is_unresolved(self) -> None:
        goal = GOOD_GOAL.replace(
            "Fix coupon expiry validation",
            "Build [THING] in [TECH/FRAMEWORK] and fix coupon expiry validation",
        )

        errors = self.lint(goal)

        self.assertTrue(any("[THING]" in error for error in errors), errors)

    def test_markdown_links_are_not_prompt_template_placeholders(self) -> None:
        goal = GOOD_GOAL.replace(
            "pricing rules in docs/pricing.md.",
            "pricing rules in [pricing docs](docs/pricing.md).",
        )

        self.assertEqual([], self.lint(goal))

    def test_missing_anti_gaming_clause_is_flagged(self) -> None:
        goal = GOOD_GOAL.replace(
            "  - Integrity (anti-gaming): never delete, skip, or weaken tests/assertions to fake a green; an honest red beats a faked green.\n",
            "",
        )

        errors = self.lint(goal)

        self.assertTrue(any("anti-gaming" in error for error in errors), errors)

    def test_failure_driven_goal_must_require_red_first(self) -> None:
        # Mention a Repro Capsule (a failure-driven signal) but drop the red-first
        # requirement: the linter should demand fail-before-fix.
        goal = GOOD_GOAL.replace(
            "  - Run `python -m pytest tests/test_coupons.py` for the targeted suite.",
            "  - Run `python -m pytest tests/test_coupons.py` and fill in the Repro Capsule.",
        ).replace(
            "The regression test fails before the fix and passes after, targeted pytest is green",
            "Targeted pytest is green",
        )

        errors = self.lint(goal)

        self.assertTrue(any("red-first" in error for error in errors), errors)

    def test_failure_driven_goal_with_red_first_passes(self) -> None:
        goal = GOOD_GOAL.replace(
            "  - Run `python -m pytest tests/test_coupons.py` for the targeted suite.",
            "  - Run `python -m pytest tests/test_coupons.py` and fill in the Repro Capsule.",
        )

        self.assertEqual([], self.lint(goal))

    def test_inlined_brief_does_not_falsely_mark_feature_goal_failure_driven(self) -> None:
        # The standard operating brief (inlined into every Goal) mentions "Repro
        # Capsule" generically; that must NOT classify a non-failure-driven feature
        # Goal as failure-driven and demand a red-first check.
        goal = GOOD_GOAL + (
            "\n--- Executor operating brief ---\n"
            "6. For failure-driven work, preserve the Repro Capsule: original input,\n"
            "   failing signal, rerun command, and the regression lock you added.\n"
        )

        self.assertEqual([], self.lint(goal))

    def test_failing_input_in_feature_goal_does_not_trigger_red_first(self) -> None:
        # "failing input" is ordinary feature-validation vocabulary, not a bug-repro
        # signal — it must not force a red-first requirement.
        goal = GOOD_GOAL.replace(
            "  - Run `python -m pytest tests/test_coupons.py` for the targeted suite.",
            "  - Run `python -m pytest tests/test_coupons.py`; a failing input shows an inline error.",
        )

        self.assertEqual([], self.lint(goal))

    def test_chinese_integrity_clause_without_token_passes(self) -> None:
        # A substantive integrity clause in Chinese with no literal 反作弊 token must
        # satisfy the anti-gaming check (semantic match, not label match).
        goal = GOOD_GOAL.replace(
            "  - Integrity (anti-gaming): never delete, skip, or weaken tests/assertions to fake a green; an honest red beats a faked green.",
            "  - 完整性：绝不能通过删除、跳过、弱化测试与断言来伪造绿色测试结果。",
        )

        self.assertEqual([], self.lint(goal))

    def test_bare_anti_gaming_token_without_substance_is_flagged(self) -> None:
        # The mirror image: a Goal that only name-drops the label, with no actual
        # integrity instruction, must still be flagged.
        goal = GOOD_GOAL.replace(
            "  - Integrity (anti-gaming): never delete, skip, or weaken tests/assertions to fake a green; an honest red beats a faked green.",
            "  - We considered anti-gaming concerns earlier; ignore them for now.",
        )

        errors = self.lint(goal)

        self.assertTrue(any("anti-gaming" in error for error in errors), errors)

    # --- Autonomy gate (Mode: AUTONOMOUS) ---

    def test_complete_autonomous_goal_passes(self) -> None:
        self.assertEqual([], self.lint(AUTONOMOUS_GOAL))

    def test_non_autonomous_goal_is_not_subject_to_autonomy_gate(self) -> None:
        # GOOD_GOAL names no verifier and no sign-off, yet must pass — the autonomy
        # gate is opt-in and only fires when the Goal declares Mode: AUTONOMOUS.
        self.assertEqual([], self.lint(GOOD_GOAL))
        self.assertNotIn("verifier", " ".join(self.lint(GOOD_GOAL)))

    def test_autonomous_goal_missing_independent_verifier_is_flagged(self) -> None:
        goal = AUTONOMOUS_GOAL.replace(
            "  - Independent verifier: a different-model verifier baton re-runs this ladder and refutes (handoff-142-verify.md).\n",
            "",
        )

        errors = self.lint(goal)

        self.assertTrue(any("independent verifier" in e for e in errors), errors)

    def test_autonomous_goal_missing_human_signoff_is_flagged(self) -> None:
        goal = AUTONOMOUS_GOAL.replace(
            "Autonomy sign-off: human-approved eligibility checklist recorded at .loop/autonomy-142.md.\n",
            "",
        )

        errors = self.lint(goal)

        self.assertTrue(any("sign-off" in e for e in errors), errors)

    def test_autonomous_goal_with_taste_word_stop_when_is_flagged(self) -> None:
        goal = AUTONOMOUS_GOAL.replace(
            "The regression test fails before the fix and passes after, targeted pytest is green",
            "The change looks polished",
        )

        errors = self.lint(goal)

        self.assertTrue(any("taste/judgment" in e for e in errors), errors)

    def test_autonomy_declared_as_markdown_heading_still_gated(self) -> None:
        # A heading-style declaration (## Mode: AUTONOMOUS) must still trip the gate —
        # otherwise an autonomy Goal written that way would silently run ungated.
        goal = AUTONOMOUS_GOAL.replace("Mode: AUTONOMOUS", "## Mode: AUTONOMOUS").replace(
            "  - Independent verifier: a different-model verifier baton re-runs this ladder and refutes (handoff-142-verify.md).\n",
            "",
        )

        errors = self.lint(goal)

        self.assertTrue(any("independent verifier" in e for e in errors), errors)

    def test_autonomous_goal_with_non_machine_verifiable_stop_when_is_flagged(self) -> None:
        goal = AUTONOMOUS_GOAL.replace(
            "The regression test fails before the fix and passes after, targeted pytest is green, and the Handoff is written with evidence.",
            "The coupon feature is complete and the Handoff is written with notes.",
        )

        errors = self.lint(goal)

        self.assertTrue(any("machine-verifiable" in e for e in errors), errors)

    # --- Green-class check-tampering guardrail ---

    def test_green_class_goal_without_check_tamper_guardrail_is_flagged(self) -> None:
        # An "until green" Goal whose only integrity clause forbids weakening tests can
        # still be gamed by rewriting the check command / exit criteria. The linter must
        # require an explicit guardrail against that for green-class Goals.
        errors = self.lint(GREEN_CLASS_GOAL)

        self.assertTrue(any("check command" in e for e in errors), errors)

    def test_green_class_goal_with_check_tamper_guardrail_passes(self) -> None:
        # The rule requires the guardrail; it must not flag a green-class Goal that has
        # one (no over-flagging).
        self.assertEqual([], self.lint(GREEN_CLASS_GOAL_OK))

    # --- Truth-sources thin-content gate ---

    def test_truth_sources_too_thin_is_flagged(self) -> None:
        # A present-but-1-char Truth-sources body (e.g. `Truth sources: x`) satisfies
        # the presence check but is not actionable. The thin-content gate must catch it
        # like every other required element.
        thin_truth_block = (
            "Truth sources: x"
        )
        goal = GOOD_GOAL.replace(
            "Truth sources:\n"
            + "  - Task: ISSUE-142 acceptance criteria.\n"
            + "  - Contracts/specs: pricing rules in docs/pricing.md.\n"
            + "  - Prior progress: none.",
            thin_truth_block,
        )

        errors = self.lint(goal)

        self.assertTrue(any("too thin" in error for error in errors), errors)
        # The unmodified GOOD_GOAL must still lint clean — no regression.
        self.assertEqual([], self.lint(GOOD_GOAL))

    # --- Shipped example Goals stay lint-clean ---

    def test_example_goal_files_are_lint_clean(self) -> None:
        # The examples/goal-*.txt files demonstrate the blueprints; they must pass the
        # linter so the catalog can't ship a Goal that its own gate would reject.
        goal_files = sorted(EXAMPLES_DIR.glob("goal-*.txt"))
        self.assertTrue(goal_files, "expected at least one examples/goal-*.txt fixture")
        for path in goal_files:
            with self.subTest(goal=path.name):
                self.assertEqual([], self.lint(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()

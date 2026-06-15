#!/usr/bin/env python3
"""Tests for relay-loop Goal linting."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "lint_goal.py"
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


if __name__ == "__main__":
    unittest.main()

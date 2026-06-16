#!/usr/bin/env python3
"""Tests for the relay-loop blueprint Goal-draft generator."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import re
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


render_blueprint_goal = _load("render_blueprint_goal")
lint_goal = _load("lint_goal")

PLACEHOLDER = re.compile(r"\{\{[^}]+\}\}")
SAMPLE_OUTCOME = "Drive PR #318 CI to green by fixing the real failing jobs"


def fill(scaffold: str) -> str:
    """Substitute every {{placeholder}} with a plausible discovered value, so the only
    reason a scaffold would fail lint is a structural defect, not an unfilled blank."""
    return PLACEHOLDER.sub("a concrete value discovered in the project", scaffold)


class RenderBlueprintGoalTests(unittest.TestCase):
    def lint(self, text: str) -> list[str]:
        return lint_goal.lint_text(text, "draft.txt")

    def test_ci_until_green_renders_and_lints_clean_when_filled(self) -> None:
        scaffold = render_blueprint_goal.render_goal(
            "ci-until-green", task="318", outcome=SAMPLE_OUTCOME
        )
        self.assertEqual([], self.lint(fill(scaffold)))

    def test_all_blueprints_render_and_lint_clean_when_filled(self) -> None:
        # Every family's draft must pass lint_goal.py once its placeholders are filled —
        # the generator must not emit a Goal its own gate would reject.
        outcome = "Complete the scoped work for task 42 with evidence and a Handoff"
        for key in render_blueprint_goal.BLUEPRINTS:
            with self.subTest(blueprint=key):
                scaffold = render_blueprint_goal.render_goal(key, task="42", outcome=outcome)
                self.assertEqual([], self.lint(fill(scaffold)), key)

    def test_raw_scaffold_is_flagged_until_filled(self) -> None:
        # Unfilled, the draft is intentionally NOT lint-clean: the placeholders are the
        # commander's to-do list.
        scaffold = render_blueprint_goal.render_goal(
            "ci-until-green", task="1", outcome=SAMPLE_OUTCOME
        )
        errors = self.lint(scaffold)
        self.assertTrue(any("placeholder" in e for e in errors), errors)

    def test_unknown_blueprint_raises(self) -> None:
        with self.assertRaises(ValueError):
            render_blueprint_goal.render_goal("nope", task="1", outcome=SAMPLE_OUTCOME)

    def test_every_blueprint_carries_the_check_command_guardrail(self) -> None:
        # The standard anti-gaming block (with the check-command guardrail) is baked into
        # every family, so even a green-class draft passes lint_goal.py once filled.
        outcome = "Complete the scoped work for task 1 with evidence and a Handoff"
        for key in render_blueprint_goal.BLUEPRINTS:
            with self.subTest(blueprint=key):
                scaffold = render_blueprint_goal.render_goal(key, task="1", outcome=outcome)
                self.assertIn("check command", scaffold)

    def test_failure_driven_blueprint_requires_red_first(self) -> None:
        scaffold = render_blueprint_goal.render_goal(
            "test-failure-triage", task="1", outcome="Fix the failing coupon test and lock it for task 1"
        )
        self.assertIn("fails before the fix", scaffold)

    def test_cli_writes_draft_to_out_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stdout(io.StringIO()):
                rc = render_blueprint_goal.main([
                    "render_blueprint_goal.py",
                    "--blueprint", "ci-until-green",
                    "--task", "318",
                    "--outcome", SAMPLE_OUTCOME,
                    "--out-dir", tmp,
                ])
            self.assertEqual(0, rc)
            path = Path(tmp) / "goal-318.txt"
            self.assertTrue(path.exists())
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# Blueprint:"))
            self.assertIn("/goal ", text)
            self.assertEqual([], self.lint(fill(text)))


if __name__ == "__main__":
    unittest.main()

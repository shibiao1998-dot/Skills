#!/usr/bin/env python3
"""Tests for relay-loop fan-out split-note linting."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "lint_fanout.py"
SPEC = importlib.util.spec_from_file_location("lint_fanout", SCRIPT_PATH)
lint_fanout = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(lint_fanout)


GOOD_FANOUT = """# Relay Fan-out Split Note checkout-regression leg 1

## Fan-out decision
Mode: FANOUT
Reason: independent diagnosis and implementation batons improve coverage before synthesis.
Human gates remaining: production deploy approval only.

## Shared objective
Reject expired coupons across the checkout path while preserving store-credit behavior.

## Truth sources
- ISSUE-142 acceptance criteria.
- docs/pricing.md coupon expiry rules.

## Shared constraints
- Do not change public coupon API names, database schema, or payment-provider config.
- Secret hygiene: use $ENV_VAR placeholders only.

## Sub-batons
### Baton A - read-only expiry diagnosis
Type: read-only exploration
Goal file: .loop/goals/goal-checkout-expiry-a.txt
Handoff file: .loop/handoffs/handoff-checkout-expiry-a.md
Log file: .loop/logs/executor-checkout-expiry-a.log
Ownership: map timezone-sensitive coupon expiry paths and name the smallest fix surface.
Allowed write surface: none (read-only analysis)
Forbidden write surface: repository files, migrations, payment-provider config
Verification surface: cite exact files, commands inspected, and evidence lines.
Stop when: Handoff names the top risk surface and replay candidate.
Pause if: credentials, production data, destructive action, or truth-source conflict is required.

### Baton B - focused coupon regression
Type: implementation
Goal file: .loop/goals/goal-checkout-expiry-b.txt
Handoff file: .loop/handoffs/handoff-checkout-expiry-b.md
Log file: .loop/logs/executor-checkout-expiry-b.log
Ownership: add the expired-coupon regression and focused fix in coupon validation.
Allowed write surface: src/checkout/coupons.py; tests/test_coupons.py
Forbidden write surface: migrations, payment-provider config, unrelated checkout code
Verification surface: run `pytest tests/test_coupons.py::test_expired_coupon_rejected` and targeted coupon tests.
Stop when: regression fails before the fix, passes after, and Handoff captures evidence.
Pause if: schema migration, credentials, production data, or product decision is required.

## Collision rules
- Baton A is read-only.
- Baton B owns src/checkout/coupons.py and tests/test_coupons.py.
- No baton may edit migrations or payment-provider config.

## Synthesis plan
- Compare both Handoffs, merge Baton B only if its fix matches Baton A evidence, then run commander verification.
- If Handoffs disagree, write a synthesis Goal instead of merging blindly.

## Verification plan
- Run `python3 relay-loop/scripts/lint_goal.py` on each Goal before dispatch.
- Run `python3 relay-loop/scripts/lint_handoff.py` on every returned Handoff.
- Commander reruns `pytest tests/test_coupons.py::test_expired_coupon_rejected` before advancing.

## Dispatch checklist
- [ ] Split note lint passed.
- [ ] Every Goal file lint passed.
- [ ] One log path and one Handoff path per baton.
"""

GOOD_SINGLE = """# Relay Fan-out Split Note checkout-regression leg 1

## Fan-out decision
Mode: SINGLE
Reason: the implementation and verification both require the same file surface.
Human gates remaining: production deploy approval only.

## Shared objective
Reject expired coupons across the checkout path while preserving store-credit behavior.

## Truth sources
- ISSUE-142 acceptance criteria.
- docs/pricing.md coupon expiry rules.

## Shared constraints
- Do not change public coupon API names, database schema, or payment-provider config.

## Single-baton rationale
The focused fix and regression both own src/checkout/coupons.py and tests/test_coupons.py, so parallel implementation would create an unverifiable merge.

## Synthesis plan
- Single baton only; commander verifies against the Goal and Handoff.

## Verification plan
- Run `python3 relay-loop/scripts/lint_goal.py .loop/goals/goal-checkout-expiry.txt`.
- Run `python3 relay-loop/scripts/lint_handoff.py .loop/handoffs/handoff-checkout-expiry.md`.
- Commander reruns `pytest tests/test_coupons.py::test_expired_coupon_rejected`.

## Dispatch checklist
- [ ] Split note lint passed.
- [ ] Goal file lint passed.
- [ ] One log path and one Handoff path recorded.
"""


class LintFanoutTests(unittest.TestCase):
    def lint(self, text: str) -> list[str]:
        return lint_fanout.lint_text(text, "fanout.md")

    def test_good_fanout_split_note_passes(self) -> None:
        self.assertEqual([], self.lint(GOOD_FANOUT))

    def test_unbounded_as_many_agents_instruction_fails(self) -> None:
        fanout = GOOD_FANOUT.replace(
            "Reason: independent diagnosis and implementation batons improve coverage before synthesis.",
            "Reason: spawn as many agents as needed and let them coordinate.",
        )

        errors = self.lint(fanout)

        self.assertTrue(any("as many agents" in error for error in errors), errors)

    def test_missing_synthesis_plan_fails(self) -> None:
        fanout = GOOD_FANOUT.replace("## Synthesis plan", "## Merge notes")

        errors = self.lint(fanout)

        self.assertTrue(any("Synthesis plan" in error for error in errors), errors)

    def test_duplicate_implementation_write_surface_fails(self) -> None:
        fanout = GOOD_FANOUT.replace(
            "Allowed write surface: none (read-only analysis)",
            "Allowed write surface: src/checkout/coupons.py",
        ).replace("Type: read-only exploration", "Type: implementation")

        errors = self.lint(fanout)

        self.assertTrue(any("write surface" in error for error in errors), errors)

    def test_bracketed_template_placeholder_fails(self) -> None:
        fanout = GOOD_FANOUT.replace("checkout-regression", "[THING]", 1)

        errors = self.lint(fanout)

        self.assertTrue(any("[THING]" in error for error in errors), errors)

    def test_single_mode_requires_single_baton_rationale(self) -> None:
        fanout = GOOD_SINGLE.replace("## Single-baton rationale", "## Notes")

        errors = self.lint(fanout)

        self.assertTrue(any("Single-baton rationale" in error for error in errors), errors)

    def test_good_single_split_note_passes(self) -> None:
        self.assertEqual([], self.lint(GOOD_SINGLE))


if __name__ == "__main__":
    unittest.main()

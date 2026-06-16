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

GOOD_EXPLORE_FIRST = """# Relay Fan-out Split Note flaky-suite-triage leg 1

## Fan-out decision
Mode: EXPLORE_FIRST
Reason: a read-only scout must discover the flaky-test work-list before independent fix batons can own disjoint files.
Human gates remaining: none.

## Shared objective
Stabilize the three flakiest test modules discovered by the scout without changing product behavior.

## Truth sources
- ISSUE-271 flaky-suite acceptance criteria.
- docs/testing.md retry and isolation rules.

## Shared constraints
- Do not change public test fixtures, CI config, or production source under src/app.
- Secret hygiene: use $ENV_VAR placeholders only.

## Sub-batons
### Baton S - read-only flaky-suite scout (runs first)
Type: read-only exploration
Goal file: .loop/goals/goal-flaky-triage-scout.txt
Handoff file: .loop/handoffs/handoff-flaky-triage-scout.md
Log file: .loop/logs/executor-flaky-triage-scout.log
Ownership: discover and rank the flaky test modules and name the disjoint fix surface for each follow-on baton.
Allowed write surface: none (read-only analysis)
Forbidden write surface: repository files, CI config, production source
Verification surface: cite exact test paths, seeds, and rerun evidence proving each module is flaky.
Stop when: Handoff lists the ranked work-list and one owned file per follow-on baton.
Pause if: credentials, production data, destructive action, or truth-source conflict is required.

### Baton A - fix first scouted module
Type: implementation
Goal file: .loop/goals/goal-flaky-triage-a.txt
Handoff file: .loop/handoffs/handoff-flaky-triage-a.md
Log file: .loop/logs/executor-flaky-triage-a.log
Ownership: stabilize the top module the scout named, owning only that test file.
Allowed write surface: tests/test_orders.py
Forbidden write surface: src/app, CI config, fixtures, other test modules
Verification surface: run `pytest tests/test_orders.py --count 20` and capture zero failures.
Stop when: the scouted module passes 20 reruns and Handoff captures evidence.
Pause if: the fix needs a fixture or source change outside the owned file.

### Baton B - fix second scouted module
Type: implementation
Goal file: .loop/goals/goal-flaky-triage-b.txt
Handoff file: .loop/handoffs/handoff-flaky-triage-b.md
Log file: .loop/logs/executor-flaky-triage-b.log
Ownership: stabilize the second module the scout named, owning only that test file.
Allowed write surface: tests/test_billing.py
Forbidden write surface: src/app, CI config, fixtures, other test modules
Verification surface: run `pytest tests/test_billing.py --count 20` and capture zero failures.
Stop when: the scouted module passes 20 reruns and Handoff captures evidence.
Pause if: the fix needs a fixture or source change outside the owned file.

## Collision rules
- Baton S is read-only and runs before any fix baton dispatches.
- Baton A owns tests/test_orders.py; Baton B owns tests/test_billing.py.
- No baton may edit src/app, fixtures, or CI config.

## Synthesis plan
- Compare both fix Handoffs against the scout's ranked work-list, merge only the modules the scout flagged, then rerun commander verification.
- If a fix Handoff strays outside its scouted module, route it back instead of merging.

## Verification plan
- Run `python3 relay-loop/scripts/lint_goal.py` on each Goal before dispatch.
- Run `python3 relay-loop/scripts/lint_handoff.py` on every returned Handoff.
- Commander reruns `pytest tests/test_orders.py tests/test_billing.py --count 20` before advancing.

## Dispatch checklist
- [ ] Split note lint passed.
- [ ] Every Goal file lint passed.
- [ ] One log path and one Handoff path per baton.
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

    def test_good_explore_first_split_note_passes(self) -> None:
        # Regression-lock: lint_fanout already accepts Mode: EXPLORE_FIRST (treated
        # like FANOUT). This pins that a well-formed EXPLORE_FIRST split note -- a
        # read-only scout baton ahead of the parallel fix batons -- lints clean.
        self.assertEqual([], self.lint(GOOD_EXPLORE_FIRST))


if __name__ == "__main__":
    unittest.main()

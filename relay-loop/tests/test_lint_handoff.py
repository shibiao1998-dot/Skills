#!/usr/bin/env python3
"""Tests for relay-loop Handoff linting."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "lint_handoff.py"
SPEC = importlib.util.spec_from_file_location("lint_handoff", SCRIPT_PATH)
lint_handoff = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(lint_handoff)


GOOD_HANDOFF = """# Handoff checkout-regression leg 1

## Part A - must-read (keep <= ~1.5 KB; this is what gets inlined into the next Goal)
- prev_handoff: none
- build on: fix/checkout-regression @ abc1234
- base: main @ def5678
- migration/contract state: none
- no-go zones: payment provider config
- traps (don't repeat): fixture data must include an expired coupon

## Part B - full record (lands on disk; for commander verification)

### Status
READY

### Acceptance, item by item (against the Goal's Stop-when)
- [done] Expired coupons are rejected - evidence: `pytest tests/test_coupons.py::test_expired_coupon_rejected -> passed`

### What I did NOT verify (negative evidence - required)
- Real payment-provider callback was not exercised; sandbox has no provider credentials.
- end-to-end: verified API rejection only; browser checkout path NOT verified.

### Diagnostic repair record
- failure observed: expired coupons were accepted when the checkout date crossed midnight UTC.
- causal chain: checkout parsed the coupon expiry as local time, then compared it to a UTC timestamp.
- root cause hypothesis: mixed timezone normalization in `coupon_is_valid`.
- exact fix surface: `src/checkout/coupons.py::coupon_is_valid` and `tests/test_coupons.py`.
- proposed focused fix: normalize coupon expiry to UTC before comparing.
- rerun command: `pytest tests/test_coupons.py::test_expired_coupon_rejected`

### Repro Capsule
- original input: order total 100, coupon EXPIRED10, checkout timestamp 2026-06-13T00:30:00Z.
- command to reproduce: `pytest tests/test_coupons.py::test_expired_coupon_rejected`
- environment/config: unit test, no network, no payment credentials.
- failing signal before fix: assertion showed coupon status accepted instead of rejected.
- trace/log/evidence: `.loop/evidence/checkout-regression/expired-coupon-red.txt`

### Regression lock
- test/check added: `tests/test_coupons.py::test_expired_coupon_rejected`
- locked failure: expired coupon cannot be accepted across timezone boundary.
- if not automated: n/a

### Deliverables (precise coordinates)
- branch: fix/checkout-regression @ abc1234; base: main @ def5678
- migration: none
- tests added/changed: tests/test_coupons.py::test_expired_coupon_rejected
- artifacts/screenshots: .loop/evidence/checkout-regression/expired-coupon-red.txt

### How to re-verify (commander's entry point - pointers, no secrets)
- `pytest tests/test_coupons.py::test_expired_coupon_rejected` -> passed
- secrets shown only as $ENV_VAR placeholders

### Next baton (material for the commander's next Goal - not executor self-direction)
- suggested next outcome: commander verifies browser checkout path against real local backend.
- must carry: this Handoff Part A and the test pointer.
- explicitly do NOT: change payment provider configuration.

### Notes / decisions worth keeping
- Treat all coupon expiry comparisons as UTC.
"""


class LintHandoffTests(unittest.TestCase):
    def lint(self, text: str) -> list[str]:
        return lint_handoff.lint_text(text, "handoff.md")

    def test_ready_handoff_with_repro_and_regression_lock_passes(self) -> None:
        self.assertEqual([], self.lint(GOOD_HANDOFF))

    def test_ready_handoff_requires_repro_capsule(self) -> None:
        handoff = GOOD_HANDOFF.replace("### Repro Capsule", "### Repro Notes")

        errors = self.lint(handoff)

        self.assertTrue(any("Repro Capsule" in error for error in errors), errors)

    def test_ready_handoff_requires_regression_lock(self) -> None:
        handoff = GOOD_HANDOFF.replace("### Regression lock", "### Follow-up test")

        errors = self.lint(handoff)

        self.assertTrue(any("Regression lock" in error for error in errors), errors)

    def test_blocked_handoff_requires_human_action(self) -> None:
        handoff = GOOD_HANDOFF.replace("READY", "BLOCKED").replace(
            "needs human action: provide $PAYMENT_SANDBOX_KEY.",
            "",
        )

        errors = self.lint(handoff)

        self.assertTrue(any("human action" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()

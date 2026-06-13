# Handoff checkout-regression leg 1

## Part A - must-read
- prev_handoff: none
- build on: fix/checkout-regression @ abc1234
- base: main @ def5678
- migration/contract state: none
- no-go zones: payment provider config, checkout UI copy
- traps (don't repeat): fixture data must include an expired coupon and a UTC boundary timestamp
- repro capsule: see Repro Capsule below
- regression lock: `tests/test_coupons.py::test_expired_coupon_rejected`

## Part B - full record

### Status
READY

### Acceptance, item by item (against the Goal's Stop-when)
- [done] Expired coupons are rejected at checkout - evidence: `pytest tests/test_coupons.py::test_expired_coupon_rejected -> passed`
- [done] Existing fixed-value coupon behavior is unchanged - evidence: `pytest tests/test_coupons.py::test_fixed_coupon_still_stacks -> passed`

### What I did NOT verify (negative evidence - required)
- Real payment-provider callback was NOT verified; sandbox has no provider credentials.
- end-to-end: verified API rejection only; browser checkout path NOT verified.

### Diagnostic repair record
- failure observed: expired coupons were accepted when checkout crossed a UTC midnight boundary.
- causal chain: checkout loaded coupon expiry as local time, then compared it to a UTC request timestamp.
- root cause hypothesis: `coupon_is_valid` mixed timezone-normalized and naive timestamps.
- exact fix surface: `src/checkout/coupons.py::coupon_is_valid` and `tests/test_coupons.py`.
- proposed focused fix: normalize coupon expiry to UTC before comparison.
- rerun command: `pytest tests/test_coupons.py::test_expired_coupon_rejected`

### Repro Capsule
- original input: order total 100, coupon EXPIRED10, checkout timestamp 2026-06-13T00:30:00Z.
- command to reproduce: `pytest tests/test_coupons.py::test_expired_coupon_rejected`
- environment/config: unit test, no network, no payment credentials.
- failing signal before fix: assertion showed coupon status accepted instead of rejected.
- trace/log/evidence: `.loop/evidence/checkout-regression/expired-coupon-red.txt`

### Regression lock
- test/check added: `tests/test_coupons.py::test_expired_coupon_rejected`
- locked failure: expired coupon cannot be accepted across timezone boundaries.
- if not automated: n/a

### Deliverables (precise coordinates)
- branch: fix/checkout-regression @ abc1234; base: main @ def5678
- migration: none
- tests added/changed: `tests/test_coupons.py::test_expired_coupon_rejected`
- artifacts/screenshots: `.loop/evidence/checkout-regression/expired-coupon-red.txt`

### How to re-verify (commander's entry point - pointers, no secrets)
- `pytest tests/test_coupons.py::test_expired_coupon_rejected` -> passed
- `pytest tests/test_coupons.py::test_fixed_coupon_still_stacks` -> passed
- secrets shown only as $ENV_VAR placeholders

### Next baton (material for the commander's next Goal - not executor self-direction)
- suggested next outcome: commander verifies browser checkout path against a real local backend.
- must carry: this Handoff Part A and the test pointer.
- explicitly do NOT: change payment provider configuration.
- blueprint candidate: `.loop/blueprints/coupon-regression.md`

### Notes / decisions worth keeping
- Treat all coupon expiry comparisons as UTC.

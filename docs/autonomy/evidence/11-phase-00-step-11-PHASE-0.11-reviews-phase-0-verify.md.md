# PHASE-0.11 Builder Evidence — Phase 0 Peer Verification

## Requirement

Blueprint Part VI defines the `Peer verify` Phase 0 deliverable as
`reviews/phase-0-verify.md`, with validation gate **"reviewer confirms
runnable"** (feature flag `FEAT_USER_MGMT`, rollback `RB-000`). This builder
item prepares reproducible runnable checks for the independent peer reviewer.
It intentionally does not create or populate the review deliverable, because a
builder must not write its own review verdict.

## Files changed

- `scripts/verify_phase_0_runnable.py` — repeatable Phase 0 verification
  command for API tests, dashboard/Phase 0 Python tests, and Compose parsing.
- `tests/test_phase_0_11_runnable.py` — verifies the command exposes every
  required check in dry-run mode and retains independent reviewer authority.
- This evidence record.

## Commands run with results

- `.venv/bin/python -m unittest tests/test_phase_0_11_runnable.py --verbose`
  — passed: 2 tests.
- `cd api && npm test` — passed: 20 tests.
- `.venv/bin/python -m unittest discover --start-directory tests --pattern
  'test_*.py' -q` — passed: 8 tests, including the dashboard health contract,
  database migration integration test, and the new peer-verification contract.
- `.venv/bin/python scripts/verify_phase_0_runnable.py` — passed: API suite,
  Python suite, and `docker compose config --quiet` all completed successfully.
- `.venv/bin/python scripts/verify_phase_0_runnable.py --dry-run` — passed:
  lists the three independent-review checks without executing them.
- `docker compose config --quiet` — passed.
- `git diff --check` — passed.

## Known limitations

The independent reviewer must run the verifier and author the required
`reviews/phase-0-verify.md` decision. This builder evidence deliberately does
not assert or include a review verdict; it only demonstrates that the runnable
validation inputs are passing.

builder_status: ready_for_independent_review

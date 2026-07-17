# PHASE 0.10 — Error Middleware Evidence

## Requirement

The active assignment is `phase 00 step 10 PHASE 0.10 error middleware`.
`checklist-data.json` defines the deliverable as **error middleware**, following
`PHASE-0.9` under `FEAT_QUALITY_CHECK`; its validation gate is **centralized
errors** and its rollback reference is `RB-000`.

The Foundation table in `blueprint.md` contains the identical deliverable and
validation gate, with a table-local phase label of `PHASE-0.9`. The immutable
blueprint and checklist were not modified.

## Files changed

- `api/src/errors/error-middleware.js` — shared HTTP-error factory,
  normalization, unknown-route middleware, and terminal Express error handler.
- `api/src/app.js` — installs the terminal centralized error flow and routes
  route/dependency failures to it while preserving existing API response shapes.
- `api/src/auth/authorization.js` — forwards authentication and role failures
  to the shared terminal handler.
- `api/test/error-middleware.test.js` — unit and live HTTP coverage for safe
  client errors, malformed JSON, unknown routes, correlation IDs, unexpected
  failures, and structured failure logs.
- `api/README.md` — documents centralized API error behavior.
- This evidence record.

## Commands run with results

- `cd api && npm test` — passed: **20 tests**, 0 failures. This includes the
  new error-middleware tests and all existing API, queue, and logging coverage.
- `cd api && node --check src/app.js && node --check src/errors/error-middleware.js` — passed.
- `.venv/bin/python utilities/skills/enterprise-blueprint/scripts/validate_blueprint.py blueprint.md` — passed: **34/34**, 0 failed, 0 warned. The interpreter emitted a non-blocking Python `datetime.utcnow()` deprecation warning from the existing validator.
- `git diff --check` — passed: no whitespace errors.

## Known limitations

- The handler intentionally keeps the existing `{ "error": "..." }` response
  shape for compatibility; a versioned structured error envelope is outside
  this Foundation item.
- Internal exception messages are deliberately not sent to clients. Error logs
  record classification and request metadata, not exception messages, to avoid
  accidental sensitive-data disclosure.
- Error logging is local structured logging from the prior observability item;
  alerting and external log shipping are outside this gate.

builder_status: ready_for_independent_review

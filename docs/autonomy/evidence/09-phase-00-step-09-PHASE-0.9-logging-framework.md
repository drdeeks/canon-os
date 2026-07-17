# PHASE 0.9 — Logging Framework Evidence

## Requirement

The active chain item, `phase-00-step-09-PHASE-0.9-logging-framework`, and
`checklist-data.json` require a **logging framework** under
`FEAT_OBSERVABILITY`, following `PHASE-0.8`. Its validation gate is
**`structured logs`** and its rollback reference is `RB-000`.

The Foundation table in `blueprint.md` contains the same logging-framework row
and structured-log gate, although that table labels the row `PHASE-0.8`; the
generated checklist and active chain identify it as `PHASE-0.9`. This delivery
implements the identical scoped requirement without changing either immutable
source or chain state.

## Files changed

- `api/src/observability/logger.js` — dependency-free JSON logger with
  `debug`, `info`, `warn`, and `error` levels and configurable `LOG_LEVEL`.
- `api/src/observability/http-logging.js` — request middleware that returns and
  logs a correlation ID, method, path, status, duration, and authenticated user
  ID after each response completes.
- `api/src/app.js` — installs the logging middleware before all API routes and
  supports the `CANON_OS_OBSERVABILITY=false` rollback toggle.
- `api/test/logging.test.js` — unit and live HTTP integration coverage proving
  emitted records are parseable JSON, preserve safe request IDs, reject unsafe
  supplied IDs, and include the structured completion fields.
- `api/README.md` — documents emitted fields and logging configuration.
- `CHANGELOG.md` — append-only `CL-0006` entry.
- This evidence record.

## Commands run with results

- `cd api && npm test` — passed: **17 tests**, 0 failures. The new test suite
  parsed captured log records and verified the live `/health` completion record
  and `X-Request-ID` response header.
- `cd api && node --check src/app.js && node --check src/observability/logger.js && node --check src/observability/http-logging.js` — passed.
- `.venv/bin/python utilities/skills/enterprise-blueprint/scripts/validate_blueprint.py blueprint.md` — passed: **34/34**, 0 failed, 0 warned.
- `git diff --check` — passed: no whitespace errors.

## Known limitations

- This item supplies structured application logs and request correlation only.
  Metrics, alerting, distributed tracing, and centralized log shipping are
  separate observability concerns not required by this Foundation gate.
- Request bodies and query strings are intentionally not logged, preventing
  credentials and arbitrary payload data from entering operational logs.
- `CANON_OS_OBSERVABILITY=false` is a controlled rollback/debug toggle; normal
  operation emits structured logs by default.

builder_status: ready_for_independent_review

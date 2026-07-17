# PHASE 0.3 — DB schema init evidence

## Requirement

Implement `V001__init_schema.sql` for the Phase 0 Foundation database-schema deliverable. The validation gate is `psql applies`. Part IV, sections 4.1 and 4.2 of `blueprint.md` require the listed PostgreSQL core schema and a matching `V001__init_schema.down.sql` rollback migration.

## Files changed

- `db/migrations/V001__init_schema.sql` — initial PostgreSQL schema, including `pgcrypto`, all 13 specified core tables, constraints, foreign keys, defaults, and indexes.
- `db/migrations/V001__init_schema.down.sql` — dependency-safe rollback for V001.
- `tests/test_phase_0_3_db_schema.py` — isolated PostgreSQL 15 Docker integration test that applies V001 using `psql -v ON_ERROR_STOP=1`, checks schema essentials, then verifies rollback.

## Commands run and results

```text
python3 -m unittest tests/test_phase_0_3_db_schema.py -v
Result: exit 0 (passed)

git diff --check
Result: exit 0 (no whitespace errors)
```

The integration test launches a temporary `postgres:15-alpine` container without publishing ports, waits for `pg_isready`, copies both migrations into the container, and removes the container in teardown.

## Known limitations

- This migration deliberately represents only the immutable blueprint’s initial schema; future schema changes require new reversible migrations rather than edits to V001.
- The test requires a locally available Docker daemon and the `postgres:15-alpine` image (Docker pulls the image when it is not cached).

builder_status: ready_for_independent_review

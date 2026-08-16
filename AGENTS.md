# AGENTS.md

Compact ramp-up for OpenCode sessions. Every line is a trap an agent would likely hit
without help.

## Authority order (which doc wins on conflict)
1. `.governance/FOREVER_DOCTRINE_UNIVERSAL.yaml` — supreme constitution (POL-001…007, `test_of_forever`).
2. `docs/ARCHITECTURE.md` — system source of truth.
3. `references/overview.md`, `references/local-3d-model-pipeline.md` — design inputs.
4. `references/TRUE_GOAL.md`, `references/DOCTRINE_IMPLEMENTATION.md` — intent & mapping.

Prior docs in `.trash/` are historical and **non-authoritative** — never implement from them.

## Hard rules (non-obvious)
- **Capability is probed, not assumed.** Never hardcode a model, runtime, or host in `core/`.
  Everything resolves via `core/capabilities/` + `models/registry/`.
- **Layering is enforced:** `CORE→CAPABILITY→PROVIDER→MODEL→RUNTIME→HARDWARE`. Lower layers
  never import higher. A lower→higher import is a doctrine violation.
- **No blueprint loop / checklist-as-truth.** Plan in `TASKS.md`; verify in `tests/`. The old
  `blueprint.md`, `checklist.md`, and `.agent/` (ACK) are retired.
- **Portable, not container-bound.** `runtimes/native/` must work without Docker.
- **Secrets** → `.secrets/`, **local state** → `.studio/` (both git-ignored). Do not commit.

## Commands (verified)
- Validate an artifact:
  `python3 core/validation/validate.py <file> [--min-lines N --min-chars N --syntax node|python|json|auto|off --require "pat" --forbid "pat" --spec file.json]`
- Run the test runner: `bash tests/run-all.sh` (executes `test_*.sh` only) or one module:
  `bash tests/run-all.sh tests/test_api.sh`.
- API interface: `cd interfaces/api/api && npm start` (node `src/server.js`); `npm test`
  (`node --test test/**/*.test.js`).

## Gotchas
- **`tests/` is legacy v0.1-era and largely broken after the v0.2.0 sanitization.** Many
  `test_*.sh` reference the hardcoded path `/home/ubuntu/ai-creative-studio/...` and `src/`;
  `test_phase_0_3_db_schema.py` expects Postgres + `db/migrations` (now SQLite at
  `core/projects/migrations/`). They will FAIL/SKIP and are **not** a v0.2.0 quality signal —
  porting is tracked in `TASKS.md`. The `test_phase_0_*.py` / `test_dashboard_health.py` files
  are standalone `unittest` and are **not** invoked by `run-all.sh`.
- `models/registry/backends.json` is the provider→model→runtime registry. It is currently
  **sample-only** — no live backends are wired up yet.
- Host-probe thresholds (`native`/`experimental`/`remote`) are placeholders pending a
  host-power depth spec — see `TASKS.md`.

## Where things actually live
- Engine: `core/` (`orchestration/chain.py`, `validation/validate.py`, `projects/migrations/`).
- Interfaces: `interfaces/web` (dashboard), `interfaces/api` (node server).
- Reusable code from the old repo was relocated, not deleted; see `CHANGELOG.md` and `.trash/`.

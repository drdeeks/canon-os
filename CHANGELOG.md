# CHANGELOG

## v0.2.0 (2026-08-15)

### Sanitization & restructure
- Retired all prior-version authoritative docs to `.trash/` (blueprint, checklist, old
  AGENTS/README, the old "Enterprise Local-Only Stack" `docs/ARCHITECTURE.md`, autonomy
  specs, ACK `.agent/`, `.agents/skills/impeccable/`, knowledge/memory/corpus,
  enterprise-blueprint skill).
- Vendored the three authoritative inputs into `references/` (overview, local-3d-model-pipeline)
  and the FOREVER doctrine into `.governance/`.
- Reorganized reusable code: `chain.py` → `core/orchestration/`, `validate.py` →
  `core/validation/`, `api/` → `interfaces/api/`, `app/` → `interfaces/web/`,
  `db/migrations/` → `core/projects/migrations/`, `scripts/` → `tools/`, `docker/` +
  `compose.yaml` → `runtimes/containers/`, `config/backends.json` →
  `models/registry/backends.json`.
- Folded the stray top-level `host/` into `core/host/` (detection, adapters, installers,
  recovery) so the tree matches `docs/ARCHITECTURE.md` §10.
- Rewrote `docs/ARCHITECTURE.md` as the unified source of truth (creative pipeline + 3D
  generation + capability spine + FOREVER overlay); added `references/TRUE_GOAL.md` and
  `references/DOCTRINE_IMPLEMENTATION.md`.

## v0.2.0 — cleanup pass 2 (2026-08-15)

### Legacy retirement (kept only if reusable; tossed if it needed a full rewrite)
- Retired hardcoded model layer to `.trash/`: `interfaces/web/app/dashboard/backends/`
  (demo/image/music/stt/text/tts/video/registry) and `model_catalog.py` — these hardcoded
  models, which the design forbids.
- Retired the blueprint / phase-0 harness and old install-ops scripts to `.trash/`:
  `tools/full_blueprint_*.py`, `tools/validate_phase_*.py`, `tools/verify_phase_0_runnable.py`,
  `tools/setup-master.sh`, `tools/studio-doctor.sh`, `tools/install-components.sh`,
  `tools/install-services.sh`, `tools/keep-alive.*`, `tools/resource-monitor.*`,
  `tools/setup.sh`, `tools/setup-users.sh`, `tools/studio-update.sh`.
- Retired dead-path legacy tests to `.trash/`: `tests/test_phase_0_*`,
  `tests/test_phase_1_core_ai_engine.py`, `tests/test_backends.sh`, `tests/test_models.sh`,
  `tests/test_infrastructure.sh`, `tests/test_workspace.sh`, `tests/test_security.sh`.
- Retired the container-bound stack per the overview's "not a container" aim:
  `runtimes/containers/docker-compose.yaml` (+ `runtimes/containers/docker/`) and
  `interfaces/web/app/dashboard/Dockerfile`. `runtimes/containers/` remains a reserved
  optional slot.

### Self-resolution (no hardcoding)
- `models/registry/backends.json` is now reference-only (recommended providers per capability
  type); provider endpoint URLs removed — they resolve from `CANONOS_PROVIDER_<NAME>_URL` env
  or discovery at runtime.
- `interfaces/web/app/model-manager/cli.py` kept and ported off the hardcoded catalog onto the
  registry, with self-resolving locations: `CANONOS_ROOT` env override else walk up to the
  `.governance/` repo-root marker; `CANONOS_STATE_DIR` / `CANONOS_MODELS_DIR` / `CANONOS_BACKUP_DIR`
  env overrides.
- Added engineering invariants to `docs/ARCHITECTURE.md` §5.4 (no hardcoded models/providers/
  runtimes/hosts/paths/endpoints; recommended models are reference points only).
- Rewrote `tools/README.md` and `tests/README.md` to reflect the new scope.

## v0.1.x (prior versions — historical)
See `.trash/`. These releases assumed a container-bound, hardcoded-model "compute brain"
design that v0.2.0 supersedes.

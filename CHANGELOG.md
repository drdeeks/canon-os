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

## v0.1.x (prior versions — historical)
See `.trash/`. These releases assumed a container-bound, hardcoded-model "compute brain"
design that v0.2.0 supersedes.

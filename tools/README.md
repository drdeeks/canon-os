# tools/

Operational tooling for Canon OS. These are **project-provided utilities**, kept separate
from `core/` (the engine) and `interfaces/` (user surfaces).

## Intended scope (v0.2.x)

| Tool | Purpose |
|------|---------|
| `bootstrap` | First-run host probe + project initialization. |
| `diagnostics` | Health/host report (reuses the host probe in `core/host/detection/`). |
| `model-manager` | Browse/install models via `models/registry/` + `models/manifests/`. |
| `project-manager` | Create/inspect portable projects under `projects/`. |
| `build` | Packaging for `runtimes/{native,containers,virtualized}`. |

## Status

The concrete tools above are not yet implemented. The directory is retained so the modular
layout in `docs/ARCHITECTURE.md §10` holds; add tools here as they are built.

## Reuse note

Legacy scripts from the prior "AI Creative Studio" product (resource/keep-alive monitors,
`setup-*`, `studio-*`, blueprint/phase harness) were retired to `.trash/` — they assumed a
fixed container-bound, hardcoded-model stack and would have required a full rewrite to fit the
capability-probed, registry-driven design. The reusable *idea* (a lightweight host resource
monitor, a model browser) is preserved here as intended scope.

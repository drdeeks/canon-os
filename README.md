# Canon OS

A **portable, local-first AI creative & 3D studio**. It discovers what a host can do and
adapts its entire capability surface to that host — producing images, video, audio, text, and
3D assets through a review-gated, blended creative↔3D pipeline.

> Not a container product. Not bound to one OS, GPU, or model. Not an agent-identity harness.

## Quick orientation

- **Architecture (source of truth):** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **True goal / end state:** [`references/TRUE_GOAL.md`](references/TRUE_GOAL.md)
- **Doctrine implementation:** [`references/DOCTRINE_IMPLEMENTATION.md`](references/DOCTRINE_IMPLEMENTATION.md)
- **Supreme constitution:** [`.governance/FOREVER_DOCTRINE_UNIVERSAL.yaml`](.governance/FOREVER_DOCTRINE_UNIVERSAL.yaml)
- **Authoritative design inputs:** [`references/overview.md`](references/overview.md),
  [`references/local-3d-model-pipeline.md`](references/local-3d-model-pipeline.md)

## The invariant

```
CORE ──> CAPABILITY ──> PROVIDER ──> MODEL ──> RUNTIME ──> HARDWARE
```

Capability is **probed, not assumed**. At boot the host is classified; capabilities run
locally when possible and fall back to remote providers only when genuinely out of reach.

## Layout

```
core/        engine: capabilities, providers, orchestration, storage, projects, validation, host
interfaces/  web, api, cli, desktop
providers/   image, image-to-3d, mesh-correction, video, audio, text, utilities
models/      registry, manifests, installers
runtimes/    native, containers, virtualized
workflows/   creative, 3d, image, video, audio
projects/    portable user projects
.governance/ FOREVER doctrine (supreme)
references/  vendored authoritative inputs + TRUE_GOAL + DOCTRINE_IMPLEMENTATION
tests/       validation: run-all.sh (legacy), unit/integration/provider/hardware
tools/       bootstrap, diagnostics, model/project managers, build
.studio/     local state (git-ignored)
.secrets/    secrets (git-ignored)
```

## Status

Sanitized and reorganized (v0.2.0). Prior-version authoritative docs are retired to
`.trash/`. Active build plan in [`TASKS.md`](TASKS.md).

## License & secrets

Secrets live in `.secrets/` (git-ignored). Local state in `.studio/` (git-ignored). Model
licenses are tracked in `models/manifests/`.

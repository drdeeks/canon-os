# Canon OS — Architecture Specification

> **Status:** Superseding source of truth (v0.2.0, 2026-08-15).
> **Scope authority:** This document, together with `references/overview.md`,
> `references/local-3d-model-pipeline.md`, and `.governance/FOREVER_DOCTRINE_UNIVERSAL.yaml`,
> defines the project. All prior documents (blueprint, checklist, AGENTS, autonomy
> specs, the old "Enterprise Local-Only Stack" `docs/ARCHITECTURE.md`, etc.) are historical
> and live in `.trash/`. They are **not** authoritative.

---

## 1. Canonical inputs

| Input | Location | Role |
|-------|----------|------|
| Overview / master design | `references/overview.md` | Product shape, capability spine, provider/model/runtime layers, directory layout |
| Local 3D model pipeline | `references/local-3d-model-pipeline.md` | Capability probe, image-to-3D + mesh-correction core, local/remote decision |
| FOREVER doctrine | `.governance/FOREVER_DOCTRINE_UNIVERSAL.yaml` | Supreme constitution: POL-001…POL-007, 40 habits, layering protocol, worker covenant |

If any document contradicts these three, these three win.

---

## 2. Identity & branding

- **Name:** Canon OS (do not drop the branding).
- **Persona:** A master creative director and technician — speaks plainly, questions
  assumptions, owns failures, and "writes for the next worker." (FOREVER habit.)
- **Not:** an agent-identity exercise, a container product, or a single fixed model stack.

---

## 3. True purpose

Canon OS is a **portable, local-first AI creative & 3D studio** that runs *anywhere a host
can run code* and adapts what it can do to the power of that host. It is the operating
environment for producing images, videos, audio, text, and 3D assets — with a full creative
pipeline that blends traditional media generation into 3D model generation.

The single defining trait: **capability is discovered, not assumed.** At boot the system
probes the host, classifies what is locally possible, and falls back to remote providers only
when a capability is genuinely out of reach. There is no hard dependency on Docker, a specific
OS, or a specific model.

(Full end-state narrative: `references/TRUE_GOAL.md`.)

---

## 4. The capability spine

Every operation flows through one invariant layering:

```
CORE ──> CAPABILITY ──> PROVIDER ──> MODEL ──> RUNTIME ──> HARDWARE
```

- **Core** — the studio engine: orchestration, storage, projects, validation, security, host.
- **Capability** — the *contract* of what an operation needs (e.g. "generate a 2K image in
  <30s", "produce a watertight mesh from one image"). Capabilities are declared independently
  of any model or machine.
- **Provider** — a logical service (image, image-to-3d, mesh-correction, video, audio, text,
  utilities). A provider exposes capabilities; it is *not* bound to one model or runtime.
- **Model** — a concrete weights/checkpoint artifact, described by a manifest (requirements,
  license, install method). Never hard-coded into logic.
- **Runtime** — how the model executes: native binary, Python env, container, or VM. Chosen
  per host, not mandated.
- **Hardware** — the real metal: CPU, GPU, NPU, RAM/VRAM, disk. The probe reads it; nothing
  else assumes it.

This spine is what makes the system portable and host-adaptive. The older "compute brain in a
container" design is retired.

---

## 5. Capability model

### 5.1 Capability contract
A capability is a named, versioned requirement set: inputs, outputs, quality bar, and a
`minimum_resources` descriptor (VRAM, RAM, compute class, disk). Stored under
`core/capabilities/`.

### 5.2 Host probe (`core/host/detection/`)
At startup (and on-demand) the host is classified:
- OS / architecture
- CPU model & cores
- GPU(s), VRAM, ROCm/CUDA/Metal availability
- RAM, available disk
- Existing runtimes (docker, python, node, ollama, comfyui, etc.)

The probe returns a **capability class** per domain:
- `native` — runs locally with comfortable headroom
- `experimental` — runs locally but tight / slow / best-effort
- `remote` — must use a configured remote provider

### 5.3 Provider registry (`models/registry/`, `providers/`)
Each provider declares which capabilities it can satisfy and, for each, the candidate models
and the runtimes they support. The resolver (`core/capabilities/`) picks the best fit given
the probe result and user intent. No provider, model, or runtime is referenced by name in
core logic — only via registry lookups.

---

## 5.4 Engineering invariants (no hardcoding)

- **No hardcoded models, providers, runtimes, or hosts.** Everything is discovered via the
  capability probe + `models/registry/` and resolved at runtime. Design docs may list
  *recommended* models as reference points only (e.g. `references/local-3d-model-pipeline.md`
  suggests Qwen-class models) — these are samples, never truth.
- **No hardcoded paths or endpoints.** Locations self-resolve: an explicit environment
  variable override (e.g. `CANONOS_ROOT`, `CANONOS_STATE_DIR`, `CANONOS_PROVIDER_<NAME>_URL`)
  wins; otherwise code walks up from its own file to the repo root (detected by the
  `.governance/` marker) and derives subpaths. Provider endpoint URLs are **not** stored in
  the registry — they resolve from env/logic at runtime. See `models/registry/backends.json`
  (reference only) and `interfaces/web/app/model-manager/cli.py` (reference resolver).

---

## 6. Runtime layer — portable, not container-bound

`runtimes/` holds three sibling adapters:
- `native/` — direct execution on the host (preferred; zero overhead)
- `containers/` — optional Docker/Compose packaging for reproducible isolation
- `virtualized/` — VM / sandbox escape hatch for untrusted or heavy workloads

Containers are **one option among three**, not the architecture. The system must run with
`native` alone on a bare host.

---

## 7. Creative pipeline (full)

The creative pipeline is a first-class workflow that *blends into* 3D generation. It is a
review-gated, iterative chain, not a one-shot prompt.

### 7.1 Stages
1. **Ideation & script** — brief → script / shot list (text capability).
2. **Asset generation** — images, audio, video per shot (image / video / audio capabilities).
3. **Review & iteration** — human-in-the-loop review gate; assets are scored against the
   capability's quality bar before promotion (`core/validation/`).
4. **3D model generation** — selected assets become 3D via the 3D core (§8).
5. **Final composition** — assemble approved 2D/3D/audio into deliverable.
6. **Delivery** — export to project format + publish target.

Every stage is a workflow under `workflows/creative/` and is capability-resolved: a stage
that the host cannot do locally is routed to a remote provider transparently.

### 7.2 Reference workflows (harvested from the retired pipeline design)
- **30-second commercial** — script → 4–6 image/asset shots → review → 15s/30s video compose → voiceover → deliver.
- **Thumbnail** — single hero image → variant grid → pick → crop/export.
- **Voiceover** — script → TTS audio → normalize → attach to video.
- **Transcript** — audio/video → speech-to-text → edit → caption/subtitle.

These demonstrate the review-and-capability pattern and are reused as templates, not as
authoritative specs.

---

## 8. 3D model generation (core)

The 3D capability is built on two cooperating providers:

- **image-to-3d** — single or multi-view image → initial mesh + textures.
- **mesh-correction** — iterative geometry/texture refinement: validates watertightness,
  manifoldness, UV/texture coherence, and re-injects corrections until the capability's
  quality bar passes (`core/validation/`).

**Local vs remote decision** (from `references/local-3d-model-pipeline.md`):
- Probe class `native` → run image-to-3d + mesh-correction locally.
- Probe class `experimental` → run locally with reduced resolution / step budgets; warn.
- Probe class `remote` → hand the job to a configured remote 3D provider; pull result back
  into the local project store.

The 3D output is a standard asset (glb/obj/fbx + textures) stored in the project, fully
usable by the creative pipeline's composition stage.

---

## 9. Project model & storage

- Projects live under `projects/` as portable folders: `manifest.json` (shot list, assets,
  review state) + `assets/` + `db/` (SQLite, schema in `core/projects/migrations/`).
- Per-install state in `.studio/` (configuration, state, cache, logs, manifests) — never
  committed.
- Secrets in `.secrets/` — never committed.

---

## 10. Directory layout (current)

```
CanonOS/
├── README.md  AGENTS.md  CHANGELOG.md  TASKS.md  VERSION  .ignore
├── .governance/            # FOREVER_DOCTRINE_UNIVERSAL.yaml (supreme)
├── .secrets/               # runtime secrets (git-ignored)
├── core/
│   ├── capabilities/       # capability contracts + resolver
│   ├── providers/          # provider interface contracts
│   ├── workflows/          # workflow engine
│   ├── orchestration/      # chain.py (scheduler, queue, chain enforcer)
│   ├── storage/            # project + asset store
│   ├── projects/           # project format + db/migrations
│   ├── validation/         # validate.py + asset/quality gates
│   ├── security/           # secrets, access
│   └── host/               # detection, adapters, installers, recovery
├── interfaces/
│   ├── web/                # app/dashboard (web UI)
│   ├── api/                # api/ (REST/WS)
│   ├── cli/                # command line
│   └── desktop/            # desktop shell
├── providers/              # image, image-to-3d, mesh-correction, video, audio, text, utilities
├── models/
│   ├── registry/           # provider→model→runtime mapping (backends.json)
│   ├── manifests/          # model descriptors
│   └── installers/         # pull/install logic
├── runtimes/               # native / containers / virtualized
├── workflows/              # creative, 3d, image, video, audio
├── projects/               # user projects (portable)
├── tests/                  # unit, integration, provider, hardware, portability, recovery
├── tools/                  # bootstrap, diagnostics, model-manager, project-manager, build
├── references/             # vendored authoritative inputs (overview, local-3d, TRUE_GOAL, DOCTRINE_IMPL)
├── docs/                   # this spec + supplementary
├── .studio/                # local state (git-ignored)
└── .trash/                 # retired prior-version docs (historical, non-authoritative)
```

---

## 11. Governance overlay (FOREVER)

`.governance/FOREVER_DOCTRINE_UNIVERSAL.yaml` is the constitution. Key bindings:

- **POL-001 (Deterministic Root)** — a single bootstrapping root; everything else is
  discovered. Implemented by the host probe + capability resolver.
- **POL-002 (No Arbitrary Authority)** — no provider/model/runtime assumed; all resolved via
  registry.
- **POL-003 (Layering)** — the capability spine §4 is the enforced layering.
- **POL-004 (Identity/Sovereignty)** — Canon OS identity is project-owned, not a harness
  artifact (the old `.agent/` ACK is retired).
- **POL-005 (Continuity)** — `.studio/` + `projects/` preserve state across runs; the worker
  covenant "write for the next worker" is honored in all docs/code comments-as-intent.
- **POL-006 (Verification)** — nothing ships unvalidated; `core/validation/` + `tests/` gate
  every stage.
- **POL-007 (Transparency)** — capability class + chosen provider/runtime are logged per
  operation (`.studio/logs/`).

The 40 habits inform engineering practice (plain speech, root-cause over patch, multi-platform
capability, honest claims). See `references/DOCTRINE_IMPLEMENTATION.md`.

---

## 12. Build status & phasing

- **Done:** repo sanitized; prior authoritative docs retired to `.trash/`; 3 inputs vendored;
  reusable code relocated (`core/orchestration/chain.py`, `core/validation/validate.py`,
  `interfaces/{web,api}/`, `core/projects/migrations/`, `runtimes/containers/`).
- **In progress:** this spec + `TRUE_GOAL.md` + `DOCTRINE_IMPLEMENTATION.md`; refreshed root
  files (`README`, `AGENTS`, `CHANGELOG`, `TASKS`, `VERSION`, `.ignore`).
- **Next:** implement the capability probe + resolver (`core/host/detection/`,
  `core/capabilities/`); port providers behind the registry; stand up `workflows/creative/`
  and `workflows/3d/` from the reference workflows; extend tests for portability/recovery.

---

## 13. Validation

- `core/validation/validate.py` validates artifacts against capability quality bars.
- `tests/` covers unit, integration, provider, hardware, portability, recovery.
- FOREVER conformance is checked via the doctrine's `test_of_forever` (7 gates) against this
  repo.

# Canon OS

Canon OS is an autonomous creative studio and marketing platform. It turns minimal input — a single image plus an optional sentence — into complete, production-ready campaigns across every modality: image generation, inpainting / outpainting / photo editing, video, text/script/copy, voiceover (TTS), transcription (STT), and music. After one-time brand setup the pipeline is self-triggering, with zero manual intervention.

Generation is **local-first but API-adaptable**: every modality runs on local models for zero cost and zero data leakage, or routes to a cloud provider through a pluggable backend registry when scale or capability demands it. It is not strictly local.

This bundle contains the full Canon OS project: the running creative studio and the enterprise blueprint that is its single, one-time source of truth.

---

## What's in this bundle

```
canon-os/
├── README.md                     # this file — bundle overview
├── AGENTS.md                     # cold-start handoff for any agent/session
├── ai-creative-studio/           # Canon OS — the studio (identity + pipeline)
│   ├── CANON_OS.md               # PROJECT FOUNDATION: vision, function, requirements, architecture
│   ├── README.md                 # full studio guide (setup, interfaces, workflows) — 980 lines
│   ├── AGENTS.md                 # studio orchestration system + pipeline stages
│   ├── PITCH.md                  # elevator pitch (spoken + condensed)
│   ├── .agent/                   # ACK — Agent Character Kit (@drdeeks/character-kit):
│   │                             #   constitution, enforcer, model-map, habits, agents/
│   │                             #   The enforcement foundation. Out-of-process daemon,
│   │                             #   fails closed. Character != identity.
│   │   └── canon-os-agent-chain-map.example.yaml  # PLACEHOLDER agent→chain wiring
│   ├── app/                      # dashboard + model-manager application
│   ├── config/                   # backend configuration
│   ├── scripts/                  # automation + setup scripts
│   ├── tests/                    # test suites
│   ├── corpus/ knowledge/ memory/ # ACK reference, knowledge graph, 3-layer memory
│   ├── chain.py                  # loop-enforcer core engine
│   ├── orchestrator.py           # pipeline orchestration
│   ├── creative-pipeline-chain.py# chain enforcement entry point
│   └── creative-loop-ideology.md # the Creative Orchestration Doctrine
│
├── blueprint.md                  # MASTER SPECIFICATION (validates 34/34) — IN THE REPO
├── checklist.md                  # loop-enforced checklist (mode=loop) — THE WORKFLOW, in repo
├── checklist-data.json           # machine-readable checklist
├── project.json                  # project metadata
├── CHANGELOG.md                  # append-only change log (CL-NNNN)
├── reference/                    # plain/unlocked checklist for reference (mode=plain)
│
└── enterprise-blueprint/         # THE SKILL (generator only — not project state)
    ├── SKILL.md                  # skill definition
    ├── scripts/                  # validate_blueprint.py + generate_checklist.py
    └── references/               # skill references
```

---

## The two documents that govern everything

1. **`ai-creative-studio/CANON_OS.md`** — the project foundation. What Canon OS is, how it functions, what it requires, and its architecture. Identity is inherited, not regenerated.
2. **`enterprise-blueprint/blueprint.md`** — the master specification. Set up once, it defines every module, screen, data schema, phase, and quality standard needed to build the system end to end, integrated with the established adforge mechanisms: the 7-agent division, the 7-phase loop-enforced chain, and the two-review quality mechanism. The generated checklist becomes the loop-enforced workflow mapped 1:1 to the blueprint.

---

## Established mechanisms (integrated from adforge)

- **7-agent division** — foundation-engineer, ai-engine, content-orchestrator, social-integrator, frontend-engineer, data-scientist, devops-engineer. Each owns one responsibility, like a film studio.
- **7-phase loop-enforced chain** — `.blueprint-chain/canon-os-blueprint.json` (phases 0–6). Each phase is `locked` until the prior is verified `complete`; once complete, never re-opened.
- **Two-review quality mechanism:**
  - *In-phase peer verification* — every phase, a dedicated reviewer agent (never the creator) confirms the work is actually functional/correct. Loop enforcer locks the phase on pass.
  - *Final holistic review* — Director pass over the whole repo: "would this be released?" — wholesome code intact, structure streamlined.
- **Backend registry (MOD-022)** — local-first, API-adaptable per modality. Not strictly local.
- **FOREVER-SYSTEM compliance** — singular source of truth, self-resolving paths, layered (never rewritten), fail-closed + tamper-evident, verifiable via `validate_blueprint.py` green badge.

---

## Working with the blueprint & checklists

```bash
cd enterprise-blueprint

# Validate the master spec (expect 34/34)
python3 enterprise-blueprint/scripts/validate_blueprint.py blueprint.md

# Regenerate the loop-enforced checklist (the workflow)
python3 enterprise-blueprint/scripts/generate_checklist.py blueprint.md

# Regenerate the plain/unlocked reference checklist
python3 enterprise-blueprint/scripts/generate_checklist.py blueprint.md --mode plain \
    --output-dir reference --project-name "Canon OS"
```

Current state: **7 phases · 24 modules · 7 screens**, validator 34/34.

---

## Running the studio

This workspace uses the flattened studio layout: the dashboard lives in
`app/dashboard/`, backend configuration lives in `config/`, and project
orientation lives in `CANON_OS.md` and `AGENTS.md`.

For the OpenAI Build Week submission foundation, use
`docs/hackathon/PHASE_0_RUNBOOK.md`. That path launches the existing Flask
dashboard with `docs/hackathon/provider-free-backends.json`, a provider-free
demo configuration that needs no secrets or model downloads.

---

## Principles (non-negotiable)

- Identity is immutable — defined once, inherited everywhere.
- Every creative decision produces an inspectable artifact.
- Critique is equal to creation — the creator never reviews its own work.
- Regenerate only failure — successful work is never discarded.
- Local-first, API-adaptable — never strictly local.
- No destructive operations — move to `.trash/`, never hard-delete source.

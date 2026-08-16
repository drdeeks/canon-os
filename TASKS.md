# TASKS

Active build plan for Canon OS v0.2.x. Plan here; verify in `tests/`.

## Done
- [x] Retire prior-version authoritative docs to `.trash/`.
- [x] Vendor 3 authoritative inputs (`references/`, `.governance/`).
- [x] Relocate reusable code (orchestration, validation, interfaces, projects, tools, containers).
- [x] Write `docs/ARCHITECTURE.md`, `references/TRUE_GOAL.md`, `references/DOCTRINE_IMPLEMENTATION.md`.
- [x] Refresh root files (`README.md`, `AGENTS.md`, `CHANGELOG.md`, `TASKS.md`, `VERSION`, `.ignore`).

## In progress
- [ ] Implement host probe (`core/host/detection/`) → capability class output.
- [ ] Implement capability resolver + contracts (`core/capabilities/`).

## Next
- [ ] Port providers behind `models/registry/` (image, image-to-3d, mesh-correction, video, audio, text).
- [ ] Build `workflows/creative/` and `workflows/3d/` from reference workflows (30s commercial, thumbnail, voiceover, transcript, mesh-correction).
- [ ] Stand up `runtimes/native/` adapter so the system runs container-free.
- [ ] Extend `tests/` for portability + recovery; wire `core/validation/validate.py` to capability quality bars.
- [ ] FOREVER `test_of_forever` conformance pass; record gaps here.

## Notes
- Host-power diagnostic depth to be deepened per morning briefing (capability classes
  `native`/`experimental`/`remote` thresholds). Current thresholds are placeholders pending
  that input.

# Evidence — Phase 01 Core AI Engine

## Requirement

Implement `[PHASE-1-v1]` / `RB-001` in `blueprint.md`. This includes the
MOD-001–006 ad pipeline, MOD-021 Image & Photo Studio, MOD-022 backend
selection, MOD-023 transcription, and MOD-018 brand consistency. The repaired
MOD-021 gate requires a canvas flow that generates from prompt plus brand
palette; performs mask-aware inpaint, outpaint, or restyle; uses the selected
local/API image backend; renders flash before an explicitly approved final;
and saves a checksum-verified asset. Its Phase-1 validation gate is `canvas
renders`.

## Files changed

- `app/dashboard/app.py` — adds the documented Studio generate, edit, and job
  status APIs; validates and forwards source/mask uploads; saves generated
  assets and reports SHA-256 checksums.
- `app/dashboard/core_ai.py` — adds MOD-021 mode, mask, tier, and checksum
  contracts while preserving the existing Core AI ad pipeline.
- `app/dashboard/backends/image.py` — adds masked workflows for ComfyUI and
  Automatic1111/Forge adapters, including inpaint, outpaint, and restyle
  dispatch.
- `app/dashboard/backends/demo.py` — keeps the provider-free image adapter
  compatible with the expanded image adapter contract.
- `app/dashboard/templates/studio.html` — adds the functional brush-mask
  canvas that calls the versioned Studio API.
- `tests/test_phase_1_core_ai_engine.py` — covers Studio generate, approved
  mask-based final restyle, persisted checksum/job lookup, empty-mask
  rejection, and final-approval enforcement alongside existing Phase-1 gates.

## Commands run with results

- `.venv/bin/python -m unittest tests/test_phase_1_core_ai_engine.py -v` —
  PASS, 10 tests.
- `.venv/bin/python scripts/validate_phase_1_gate.py` — PASS.
- `.venv/bin/python -m unittest tests/test_dashboard_health.py -v` — PASS.
- `.venv/bin/python -m py_compile app/dashboard/app.py app/dashboard/core_ai.py app/dashboard/backends/image.py` — PASS.
- `git diff --check` — PASS.

## Known limitations

- Production image output still requires the chosen configured adapter to
  return a locally accessible image or base64 image. The Studio API reports a
  save failure rather than publishing an unchecked asset.
- Studio jobs are synchronous and retained in process memory; this satisfies
  the present local dashboard job contract but a durable queue/store is needed
  for multi-process deployment.
- Provider key values remain outside this path; the backend registry stores
  only key references.

builder_status: ready_for_independent_review

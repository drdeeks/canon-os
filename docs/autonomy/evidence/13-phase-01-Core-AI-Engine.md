# Evidence — Phase 01 Core AI Engine

## Requirement

Implement `[PHASE-1-v1]` / `RB-001` in `blueprint.md`. This includes the
MOD-001–006 ad pipeline, MOD-021 Image & Photo Studio, MOD-022 backend
selection, MOD-023 transcription, and MOD-018 brand consistency. The repaired
MOD-021 gate requires a canvas flow that generates from prompt plus brand
palette; performs mask-aware inpaint, outpaint, or restyle; uses the selected
local/API image backend; supports brush, lasso, and full-frame masking;
renders flash before an explicitly approved final; and saves a
checksum-verified asset. Its Phase-1 validation gate is `canvas renders`.

## Repair completed

The failed review's blocker is repaired: the Studio screen now offers
`Generate flash preview` and `Approve generated final` controls. They submit
the prompt and brand palette directly to `/api/v1/studio/generate`, so no
source image or mask is required for generation. Masked edit controls remain
separate and continue to require a source image and a non-empty mask.

This repair is now guarded by a UI contract that isolates the `generate()`
handler and verifies it carries the brand palette while neither reading a
source file nor serializing a mask. This closes the review gap left by the
former API-only test.

## Files changed

- `app/dashboard/app.py` — adds the documented Studio generate, edit, and job
  status APIs; validates and forwards source/mask uploads; saves generated
  assets and reports SHA-256 checksums; packages generated commercials for
  social-channel handoff without falsely claiming external publishing.
- `app/dashboard/core_ai.py` — adds MOD-021 mode, mask, tier, and checksum
  contracts while preserving the existing Core AI ad pipeline.
- `app/dashboard/backends/image.py` — adds masked workflows for ComfyUI and
  Automatic1111/Forge adapters, including inpaint, outpaint, and restyle
  dispatch.
- `app/dashboard/backends/demo.py` — keeps the provider-free image adapter
  compatible with the expanded image adapter contract.
- `app/dashboard/templates/studio.html` — exposes a prompt-plus-brand-palette
  Studio generation path that posts directly to `/api/v1/studio/generate`,
  plus the separate masked-edit path for `/api/v1/studio/inpaint`; implements
  separate source, mask, and preview canvases; provides functional brush,
  lasso (with close action), and full-frame masks; and submits the resulting
  PNG mask to the versioned Studio API.
- `app/dashboard/templates/workspace.html` — replaces the generic prompt
  playground with a focused commercial-builder UI: brand upload, campaign
  angle, draft/final MP4 mode, local/API backend routing, pipeline status,
  storyboard review, downloadable commercial output, social package panel, and
  visible scaffold modules for the deferred platform surface.
- `tests/test_phase_1_core_ai_engine.py` — covers Studio generate, approved
  mask-based final restyle, persisted checksum/job lookup, empty-mask
  rejection, final-approval enforcement, the `/studio` UI generate controls
  and `/api/v1/studio/generate` fetch path; verifies the UI generation handler
  sends the palette without reading a source image or submitting a mask; covers
  all three canvas mask controls,
  the `/` commercial-builder frontend, local/API backend-selection controls,
  social package endpoint, and social handoff states alongside existing
  Phase-1 gates.
- `docs/autonomy/evidence/13-phase-01-Core-AI-Engine.md` — records this repair
  and the validation evidence.

## Commands run with results

- `.venv/bin/python -m unittest tests/test_phase_1_core_ai_engine.py -v` —
  PASS, 13 tests.
- `.venv/bin/python scripts/validate_phase_1_gate.py` — PASS (`OK: Phase 1
  Core AI Engine gate passed`).
- `.venv/bin/python -m unittest discover --start-directory tests --pattern 'test_*.py' --verbose`
  — PASS, 23 tests.
- `node .agents/skills/impeccable/scripts/detect.mjs --json app/dashboard/templates/workspace.html app/dashboard/templates/studio.html`
  — PASS, no findings (`[]`).
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
- Social distribution is packaged for connected publishing but does not post
  to live external accounts until social OAuth/connectors are configured.

builder_status: ready_for_independent_review

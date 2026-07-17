# Independent Review — PHASE-1: Core AI Engine

## Scope

Independently reviewed `[PHASE-1-v1]` / `RB-001` in `blueprint.md`, the
active Phase 1 checklist, supplied implementation evidence, and the current
dashboard/Core AI implementation. No external AI provider was exercised;
provider-facing tests use local fakes/fixtures.

## Verification performed

- `.venv/bin/python -m unittest tests/test_phase_1_core_ai_engine.py -v`:
  PASS — 11 tests. This exercised palette extraction; a 30-second,
  ten-scene storyboard; quality checking; local/API registry selection;
  transcription through a fake adapter; FFmpeg assembly of a downloadable
  1920x1080 H.264 MP4; Studio checksum persistence; and mask/final-approval
  rejection paths.
- `.venv/bin/python scripts/validate_phase_1_gate.py`: PASS.
- `.venv/bin/python -m unittest tests/test_dashboard_health.py -v`: PASS.
- `.venv/bin/python -m py_compile app/dashboard/app.py app/dashboard/core_ai.py
  app/dashboard/backends/image.py`: PASS. The Studio JavaScript extracted from
  `templates/studio.html` also passed `node --check -`; `git diff --check`
  passed.
- Direct implementation inspection confirms the repaired canvas has brush,
  lasso (including polygon close), and full-frame masks; API-side empty-mask
  validation; flash/final tiers with final approval enforcement; selected image
  registry dispatch; and SHA-256 verification after the generated asset is
  saved.

## Blocking finding

MOD-021 requires that the **canvas flow** generate an image from a prompt plus
brand palette. Although `POST /api/v1/studio/generate` exists and its API test
passes, the actual `/studio` screen cannot invoke it. Its mode selector has
only `inpaint`, `outpaint`, and `restyle`; `render()` refuses to proceed unless
a source file and a non-empty mask are present; and it always posts to
`/api/v1/studio/inpaint`. Thus a user of the required Studio canvas cannot do
prompt-plus-palette generation without first supplying an image and mask.

The automated test for Studio generation calls the API directly, so it does
not demonstrate the required canvas generation flow. The complete MOD-021
acceptance criteria, and therefore the conjunctive Phase 1 validation gate,
are not demonstrably satisfied.

VERDICT: FAIL — The Studio canvas has no prompt-plus-brand-palette generate flow; it only supports masked edits despite the separate API endpoint.

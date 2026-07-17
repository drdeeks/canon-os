# Evidence — Phase 01 Core AI Engine

## Requirement

Implement `[PHASE-1-v1]` / `RB-001` in `blueprint.md`: MOD-001 through
MOD-006 must transform a validated JPG, PNG, or WebP upload and optional
tagline into brand analysis, a 30-second 8–12 scene script and storyboard,
rendered scenes, voiceover/music, and a downloadable 1080p H.264 MP4. The
same phase also gates MOD-021 canvas generation/inpaint, MOD-022 runtime
local-to-API selection, MOD-023 transcription, and MOD-018 brand consistency.

## Files changed

- `app/dashboard/app.py` — delivers rendered ads as `/output/...mp4`; adds the
  specified backend catalog and runtime selection endpoints.
- `app/dashboard/core_ai.py` — assembles 1080p H.264 MP4s, mixes available
  generated audio, enforces the 60 MB limit, and materializes adapter audio.
- `app/dashboard/backends/registry.py` — adds safe per-modality local/API
  switching, catalog state, provider-key-reference handling, and music status.
- `tests/test_phase_1_core_ai_engine.py` — adds endpoint-level MP4 download and
  runtime switch tests alongside all Phase 1 gate coverage.

## Commands run with results

- `.venv/bin/python -m unittest tests/test_phase_1_core_ai_engine.py -v` —
  PASS, 8 tests.
- `.venv/bin/python scripts/validate_phase_1_gate.py` — PASS.
- `.venv/bin/python -m unittest tests/test_dashboard_health.py -v` — PASS.

## Known limitations

- Production rendering still requires configured local or API adapters to
  return locally accessible scene media; the endpoint fails explicitly when a
  scene cannot be assembled rather than fabricating an MP4 or silently falling
  back to an API.
- Provider key values are intentionally outside this code path. Runtime
  selection retains only a non-secret provider-key reference.

builder_status: ready_for_independent_review

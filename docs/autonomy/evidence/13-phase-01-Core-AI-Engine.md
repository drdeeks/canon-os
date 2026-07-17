# Phase 01 — Core AI Engine: Builder Evidence

requirement: |
  Blueprint Phase 1 / [PHASE-1-v1], rollback RB-001: implement brand extraction
  (MOD-001), a 30-second script (MOD-002), an 8–12 scene storyboard (MOD-003),
  video rendering through local/API adapters (MOD-004), voiceover and music
  (MOD-005), FFmpeg MP4 assembly (MOD-006), image editing (MOD-021), backend
  selection (MOD-022), transcription (MOD-023), and brand-consistency checking
  (MOD-018). The Phase 1 table gates are colors extracted, 30s script, 8–12
  scenes, scene renders, voiceover+music, MP4 output, canvas renders,
  local<->API switch, transcript, and brand-consistency.

files_changed:
  - app/dashboard/core_ai.py
  - app/dashboard/app.py
  - app/dashboard/backends/registry.py
  - app/dashboard/backends/demo.py
  - app/dashboard/requirements.txt
  - config/backends.json
  - scripts/validate_phase_1_gate.py
  - tests/test_phase_1_core_ai_engine.py
  - docs/autonomy/evidence/13-phase-01-Core-AI-Engine.md

commands_run:
  - command: .venv/bin/pip install -r app/dashboard/requirements.txt
    result: PASS — Pillow 11.1.0 installed; declared dashboard dependencies import.
  - command: .venv/bin/python -m unittest tests/test_phase_1_core_ai_engine.py -v
    result: PASS — 6 tests: extracted colours, 30-second/10-scene storyboard,
      rendered scene manifest, voiceover/music, transcript, FFmpeg MP4, endpoint,
      and tagline validation.
  - command: .venv/bin/python -m unittest tests/test_dashboard_health.py -v
    result: PASS — dashboard health contract passes.
  - command: npm test --prefix api
    result: PASS — 20 API tests pass.
  - command: .venv/bin/python scripts/validate_phase_1_gate.py
    result: PASS — independent read-only Phase 1 functional gate runner passes.
  - command: python3 .blueprint-chain/validators/validate_phase1_blueprint.py .blueprint-chain/phase-01-Core-AI-Engine
    result: PASS — generated phase validator reports Phase 1 validation passed.
  - command: .venv/bin/python -m compileall -q app/dashboard/core_ai.py app/dashboard/app.py app/dashboard/backends
    result: PASS — Python compilation succeeds.
  - command: git diff --check
    result: PASS — no whitespace errors.

known_limitations:
  - Real video, TTS, music, image, and STT output requires a configured local
    provider or API provider; the functional tests use injected deterministic
    adapters and exercise FFmpeg with a real generated fixture.
  - The instant-ad endpoint is flash-first by default. render=true dispatches
    provider rendering and audio only after the reviewable draft artifacts exist.

builder_status: ready_for_independent_review

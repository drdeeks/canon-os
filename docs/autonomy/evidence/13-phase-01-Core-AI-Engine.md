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

The failed review's flash-before-final blocker is repaired. A final Studio
render now requires `approved=true`, a completed flash `preview_job_id`, and a
server-computed signature matching mode, prompt, palette, source/mask content,
dimensions, and the selected image backend. This is enforced for both
prompt-based generation and masked editing; a client cannot bypass it by
enabling the final button or submitting `approved=true` directly. The Studio
page keeps both final controls disabled until its corresponding flash preview
finishes and sends that preview job id with the final request.

## Files changed

- `app/dashboard/app.py` — binds each final Studio request to a matching,
  completed flash job before invoking the image adapter.
- `app/dashboard/templates/studio.html` — disables final actions until a flash
  result exists and supplies its job id to the final request.
- `tests/test_phase_1_core_ai_engine.py` — verifies valid generate/edit
  preview-to-final flows and rejects both missing and mismatched previews.
- `docs/autonomy/evidence/13-phase-01-Core-AI-Engine.md` — records this repair
  and validation evidence.

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

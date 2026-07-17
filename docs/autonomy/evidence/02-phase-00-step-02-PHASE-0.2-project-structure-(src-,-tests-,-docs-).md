# PHASE 0.2 — Project Structure Evidence

## Requirement

The Foundation table in `blueprint.md` lists this second sequential chain item
as the row with prerequisite `PHASE-0.1`: **project structure (`src/`,
`tests/`, `docs/`)**. Its validation gate is **`tree exists`**. The active
`PHASE-0.2` checklist entry carries the same deliverable and gate. The existing
dashboard continues to live in `app/`; this foundation step creates the
durable shared source root without relocating or replacing working
functionality.

## Files changed

- `src/README.md` — versioned shared-source root and scope note.
- `tests/test_phase_0_2_project_structure.py` — automated directory-tree
  contract for `src/`, `tests/`, and `docs/`.
- `docs/autonomy/evidence/02-phase-00-step-02-PHASE-0.2-project-structure-(src-,-tests-,-docs-).md`
  — this evidence record.

## Commands run and results

- `.venv/bin/python -m unittest -v tests/test_phase_0_2_project_structure.py`
  — passed: 2 tests.
- `test -d src && test -d tests && test -d docs` — passed: all three required
  tree roots exist.
- `.venv/bin/python utilities/skills/enterprise-blueprint/scripts/validate_blueprint.py blueprint.md`
  — passed: 34/34, 0 failed, 0 warned.
- `git diff --check` — passed.

## Known limitations

The gate validates the required tree roots, not a prescribed internal package
layout. Existing user-owned working-tree changes, including chain state and
`docs/Canon-Brand.PNG`, are intentionally excluded.

builder_status: ready_for_independent_review

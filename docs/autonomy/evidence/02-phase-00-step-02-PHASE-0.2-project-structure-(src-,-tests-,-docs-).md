# PHASE 0.2 — Project Structure Evidence

## Requirement

Blueprint `PHASE-0.2` requires **project structure (`src/`, `tests/`,
`docs/`)**. Its validation gate is **`tree exists`**. The existing dashboard
continues to live in `app/`; this foundation step creates the durable shared
source root without relocating or replacing working functionality.

## Files changed

- `src/README.md` — versioned shared-source root and scope note.
- `tests/test_phase_0_2_project_structure.py` — automated directory-tree
  contract for `src/`, `tests/`, and `docs/`.
- `docs/autonomy/evidence/02-phase-00-step-02-PHASE-0.2-project-structure-(src-,-tests-,-docs-).md`
  — this evidence record.

## Commands run and results

- `.venv/bin/python -m unittest -v tests/test_phase_0_2_project_structure.py`
  — passed: 2 tests.
- `.venv/bin/python -m unittest discover --start-directory tests --pattern
  'test_*.py' --verbose` — passed: 5 tests.
- `.venv/bin/python utilities/skills/enterprise-blueprint/scripts/validate_blueprint.py blueprint.md`
  — passed: 34/34, 0 failed, 0 warned.
- `git diff --check` — passed.

## Known limitations

The workspace mounts `.git` read-only, so the requested focused commit cannot
be created locally if Git cannot create its index lock. This does not affect
the `tree exists` validation gate. Existing user-owned working-tree changes,
including chain state and `docs/Canon-Brand.PNG`, are intentionally excluded.

builder_status: ready_for_independent_review

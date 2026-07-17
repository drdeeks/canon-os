# PHASE-0.1 Evidence — repo init, Dockerfile, CI

## Requirement

Blueprint `PHASE-0.1` requires **"repo init, Dockerfile, CI"** with the
validation gate **"health 200"** (prerequisite: repo access; feature flag:
`FEAT_USER_MGMT`; rollback: `RB-000`).

## Files changed

- `.github/workflows/ci.yml` — CI runs the dashboard liveness contract, builds
  the production dashboard image, starts it, and waits for `/health` to return
  HTTP 200. It also validates the immutable blueprint on every push and pull
  request.
- `app/dashboard/Dockerfile` — installs the health-check client and points the
  image health check at `/health`.
- `app/dashboard/app.py` — adds the dependency-free liveness endpoint:
  `GET /health` returns `{"status":"ok"}` with HTTP 200.
- `tests/test_dashboard_health.py` — automated Flask test-client assertion of
  the 200 response and response body.
- `tests/test_phase_0_1_delivery.py` — automated contract assertions that CI
  validates the blueprint and exercises the Docker image's `/health` endpoint.
- This evidence record.

## Commands run and results

- `.venv/bin/python utilities/skills/enterprise-blueprint/scripts/validate_blueprint.py blueprint.md`
  — passed: **34/34**, 0 failed, 0 warned.
- `.venv/bin/python -m unittest discover --start-directory tests --pattern 'test_*.py' --verbose`
  — passed: **3 tests**. This includes the Flask `/health` contract, which
  returns HTTP 200 and `{"status":"ok"}`, and the Docker/CI delivery contract.
- `git diff --check` — passed.
- `docker version` / local Gunicorn socket probe — not runnable because this
  sandbox denies Docker-socket access and local TCP socket creation. The CI
  workflow runs the image build, container startup, and HTTP probe on GitHub
  runners.
- `git add .github/workflows/ci.yml tests/test_phase_0_1_delivery.py docs/autonomy/evidence/01-phase-00-step-01-PHASE-0.1-repo-init,-Dockerfile,-CI.md && git commit -m "test: strengthen phase 0.1 delivery gate"`
  — blocked: the sandbox mounts `.git` read-only, so Git cannot create
  `.git/index.lock`. No chain data was changed.

## Known limitations

The sandbox prevents local container execution and local TCP listener creation.
The application-level health gate is verified by its Flask test client, while
the committed CI workflow performs the Docker runtime probe. No external AI
provider, model download, or secret is needed. This environment also prevents
the requested focused commit because `.git` is read-only. The chain state was
not changed.

builder_status: ready_for_independent_review

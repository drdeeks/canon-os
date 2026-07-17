# PHASE-0.1 Evidence — repo init, Dockerfile, CI

## Requirement

Blueprint `PHASE-0.1` requires **"repo init, Dockerfile, CI"** with the
validation gate **"health 200"** (prerequisite: repo access; feature flag:
`FEAT_USER_MGMT`; rollback: `RB-000`).

## Files changed

- `.github/workflows/ci.yml` — CI runs the dashboard liveness contract, builds
  the production dashboard image, starts it, and waits for `/health` to return
  HTTP 200.
- `app/dashboard/Dockerfile` — installs the health-check client and points the
  image health check at `/health`.
- `app/dashboard/app.py` — adds the dependency-free liveness endpoint:
  `GET /health` returns `{"status":"ok"}` with HTTP 200.
- `tests/test_dashboard_health.py` — automated Flask test-client assertion of
  the 200 response and response body.
- This evidence record.

## Commands run and results

- `python3 utilities/skills/enterprise-blueprint/scripts/validate_blueprint.py blueprint.md`
  — passed: **34/34**, 0 failed, 0 warned.
- `python3 -m py_compile app/dashboard/app.py tests/test_dashboard_health.py`
  — passed.
- `ruby -e "require 'yaml'; YAML.load_file('.github/workflows/ci.yml'); puts 'CI YAML parses'"`
  — passed (`CI YAML parses`).
- Python health-gate wiring assertion against the Dockerfile, CI workflow, and
  test — passed (`health gate wiring verified`).
- `git diff --check` — passed.
- `python3 -m unittest -v tests/test_dashboard_health.py` — blocked before the
  endpoint could execute because the host interpreter has no Flask installation
  (`ModuleNotFoundError: No module named 'flask'`). Creating an isolated
  environment cannot download the pinned dependency because this sandbox has no
  package-index DNS access.
- Local Docker execution could not be run because access to
  `/var/run/docker.sock` is denied in this sandbox. The CI workflow performs
  the dependency installation, image build, container start, and HTTP 200
  check on GitHub-hosted runners.
- `git add … && git commit -m "feat: add dashboard health CI gate"` — passed;
  a focused commit was created.

## Known limitations

Runtime container verification is environment-blocked locally by the sandbox's
package-network and Docker-socket restrictions. The CI gate is present in the
repository and requires no external AI provider, model download, or secret.
The chain state was not changed.

builder_status: blocked

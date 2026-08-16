# tests/

Verification for Canon OS. Two layers:

## 1. Legacy-free runner — `run-all.sh`
A generic, timeout-bounded test framework. It discovers `test_*.sh` modules, runs each with
per-test timeouts, and reports PASS / FAIL / SKIP (SKIP = prerequisite missing, not a
failure).

```bash
./run-all.sh                 # all test_*.sh modules
./run-all.sh --verbose       # failure details
./run-all.sh --dry-run       # what would run
./run-all.sh test_api.sh     # one module
```

Add a check with `run "description" "command"` — auto-timeout, auto-error-catch.

## 2. Current modules
| Module | What it validates |
|--------|-------------------|
| `test_api.sh` | Live API endpoints (hit the running `interfaces/api` server). |
| `test_dashboard_health.py` | Dashboard/web health check (standalone `unittest`). |

## Status / caveat
The prior `test_phase_0_*` and the old `test_infrastructure/security/backends/models/workspace.sh`
modules assumed the retired "AI Creative Studio" stack (`/home/ubuntu/...`, `/opt/ai-studio`,
`src/`, Postgres) and were moved to `.trash/`. The modules above are kept because they exercise
the live interfaces with only minor adaptation. New capability/portability/recovery tests
belong alongside them as the engine is built out (see `TASKS.md`).

## Exit codes
`0` all passed · `1` one or more failed · `2` no tests ran.

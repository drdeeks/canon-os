# AI Creative Studio - Test Suite

131 individual test assertions across 6 modules. Every test has a timeout
(never hangs), error handling (never crashes), and graceful skip
if prerequisites are missing.

## Running Tests

```bash
./run-all.sh                    # All tests
./run-all.sh --verbose          # Show failure details
./run-all.sh --dry-run          # Show what would run
./run-all.sh --timeout 30       # Override per-test timeout
./run-all.sh test_security.sh   # Run one module
studio-test smoke               # Quick alias
studio-test full                # Full suite
```

## Modules

| Module | Tests | What it validates |
|--------|-------|-------------------|
| `test_infrastructure.sh` | 35 | Docker, containers, ports, storage, GPU, configs, CLI tools |
| `test_security.sh` | 17 | SSH config, firewall, fail2ban, creator isolation, container security |
| `test_backends.sh` | 17 | Backend health checks, API responses, generation capability, network |
| `test_models.sh` | 15 | Model catalog, model files, metadata, VRAM checks, symlinks |
| `test_api.sh` | 19 | Dashboard endpoints, validation, response times, HTML structure |
| `test_workspace.sh` | 26 | Frontend modes, UI elements, templates, JavaScript |

## Test Outcomes

- **PASS** -- test ran and passed
- **FAIL** -- test ran and failed (actual problem)
- **SKIP** -- prerequisite missing (Docker not running, no GPU, etc.)

SKIP is not a failure. It means the test couldn't run because
the system isn't configured for it yet.

## Exit Codes

- `0` -- all tests passed
- `1` -- one or more tests failed
- `2` -- no tests ran

## Adding Tests

Add `run "description" "command"` lines to any module.
Tests auto-timeout and auto-catch errors. No special handling needed.

```bash
run "My test" "curl -sf http://localhost:5000/" 10
```

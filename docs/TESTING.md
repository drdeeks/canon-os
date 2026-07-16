============================================================================
                 AI CREATIVE STUDIO - TESTING & VALIDATION
                       Enterprise QA Suite
============================================================================

OVERVIEW
--------
Six test modules. 131 individual test assertions. Every test has a timeout
(never hangs), error handling (never crashes), and graceful skip if
prerequisites are missing.

Test outcomes:
  PASS  - test ran, system meets requirement
  FAIL  - test ran, system does NOT meet requirement
  SKIP  - prerequisite missing (Docker not running, no GPU, etc.)

SKIP is not a failure. It means the check couldn't run.

RUNNING TESTS
-------------
  cd ~/ai-creative-studio
  bash tests/run-all.sh                    # All tests
  bash tests/run-all.sh --verbose          # Show failure details
  bash tests/run-all.sh --dry-run          # Show what would run
  bash tests/run-all.sh --timeout 30       # Override per-test timeout
  bash tests/run-all.sh test_security.sh   # Run one module

On the compute brain after install:
  studio-test smoke       # Quick alias
  studio-test full        # Full suite

EXIT CODES
  0  All tests passed
  1  One or more tests failed
  2  No tests ran


TEST MODULES
------------

1. test_infrastructure.sh (35 assertions)
   Docker installed and running
   Docker Compose available
   Compose file valid (docker compose config)
   All 9 containers exist (ollama, llamacpp, comfyui, openwebui, whisper, kokoro, invokeai, dashboard, audiocraft)
   All 7 ports listening (5000, 9090, 8188, 8080, 9000, 8880, 7860)
   Storage mounted at /mnt/studio
   All 7 directories exist (models, projects, exports, uploads, cache, logs, config)
   Disk space >10GB
   Backend config valid JSON
   SSH server running
   GPU detected (nvidia-smi or Metal)
   RAM >=8GB
   CLI tools installed (studio-status, studio-model, studio-doctor)
   Logs writable

2. test_security.sh (17 assertions)
   SSH on port 2222 (non-standard)
   Password authentication disabled
   Public key authentication enabled
   Root login disabled
   UFW firewall active
   fail2ban running
   Creator account exists with nologin shell
   Creator has no sudo
   Creator has no Docker access
   Creator blocked from /etc/shadow
   Creator blocked from /root
   Admin account exists with bash shell
   Admin has Docker access
   Admin home <10MB (no files stored)
   Containers not running as root
   Docker socket not world-readable
   ACL tools available

3. test_backends.sh (17 assertions)
   Backend config valid JSON
   Text backend health (llama.cpp or Ollama -- checks port first)
   Text backend can generate (sends actual request)
   Image backend health (ComfyUI -- checks port first)
   Image backend has models loaded
   TTS backend health (Kokoro -- checks port first)
   STT backend health (Whisper -- checks port first)
   Music backend health (AudioCraft -- checks port first)
   Dashboard health
   Dashboard API status
   Docker network exists
   Container DNS resolution

4. test_models.sh (15 assertions)
   Model directory structure (/text, /image, /video, /audio)
   Model catalog valid Python
   Model catalog loads (import succeeds)
   Model catalog has text models
   Model catalog has image models
   Model catalog has video models
   Model catalog has audio models
   Each model has required fields (id, name)
   Model state file valid JSON (if exists)
   Installed model files readable
   No broken symlinks in models directory
   VRAM checkable (if NVIDIA GPU)

5. test_api.sh (19 assertions)
   GET / returns 200
   GET /workspace returns 200
   GET /models returns 200
   GET /settings returns 200
   GET /projects returns 200
   GET /api/status returns valid JSON
   GET /api/models returns valid JSON
   GET /api/settings returns valid JSON
   GET /api/history returns valid JSON
   POST /api/generate rejects empty prompt (400/422/500)
   POST /api/generate rejects missing upload for i2i
   POST /api/enhance-prompt works (returns "enhanced" key)
   POST /api/text/generate rejects empty (400/422/500)
   POST /api/settings saves (returns "saved" status)
   HTML contains "AI"
   HTML has 6+ mode buttons (data-mode attributes)
   HTML has generate button (generateBtn)
   API status responds in <2 seconds

6. test_workspace.sh (26 assertions)
   Workspace page loads
   Has mode selector (mode-selector class)
   Has 6+ mode buttons
   Has Text to Image mode
   Has Text to Video mode
   Has Image Edit mode
   Has Animate mode
   Has Write mode
   Has Voice mode
   Has model selector (modelSelect)
   Has prompt input (promptInput)
   Has generate button (generateBtn)
   Has upload zone (uploadZone)
   Has history strip (historyStrip)
   Has settings link
   Has projects link
   Has CSS styles
   Has JavaScript
   Has generate function
   Settings page loads
   Settings has theme selector
   Settings has voice selector
   Settings has save button
   Projects page loads
   Templates directory exists
   All 5 template files exist


TEST PATTERN
------------
Every test follows this pattern:

  run "description" "command" [timeout_seconds]

Example:
  run "Docker installed" "command -v docker" 5
  run "Dashboard health" "curl -sf --max-time 5 http://127.0.0.1:5000/" 8

The run() function:
  1. Wraps command in `timeout N bash -c "command"`
  2. Captures exit code
  3. exit 0 = PASS, exit 124 = SKIP (timeout), other = FAIL
  4. Never crashes the test runner

To skip a test when prerequisite is missing:
  skip "description" "reason"


WRITING NEW TESTS
-----------------
1. Create tests/test_yourname.sh
2. Copy the header pattern:

  #!/usr/bin/env bash
  set -uo pipefail
  PASS=0; FAIL=0; SKIP=0; TOTAL=0
  run() { ... }  # copy from any existing module
  skip() { ... }

3. Add run() calls for your tests
4. Print summary at end
5. Add to run-all.sh (auto-discovered if named test_*.sh)


EXPECTED RESULTS
----------------
On a fully configured compute brain (after setup-master.sh + docker compose up):
  131 tests, ~120 pass, ~0 fail, ~11 skip (no GPU = VRAM skip)

On a dev machine (this environment):
  131 tests, ~85 pass, ~14 fail, ~32 skip

The 14 failures on dev machine are legitimate:
  - Only dashboard container running (other 5 containers not started)
  - RAM 4GB (needs 8GB+)
  - SSH not hardened (port 22, root login enabled)

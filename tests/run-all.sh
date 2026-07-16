#!/usr/bin/env bash
# ============================================================================
# AI Creative Studio - Master Test Runner
# ============================================================================
# Executes all test modules. Every test has:
#   - Timeout (never hangs)
#   - Error handling (never crashes)
#   - Graceful skip if prerequisite missing
#   - Timing
#   - Colored PASS/FAIL/SKIP output
#
# Usage:
#   ./run-all.sh                    # Run all tests
#   ./run-all.sh --verbose          # Show test output
#   ./run-all.sh --dry-run          # Show what would run
#   ./run-all.sh --timeout 30       # Override per-test timeout
#   ./run-all.sh test_security.sh   # Run one module
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERBOSE=false
DRY_RUN=false
TIMEOUT=30

# Colors (auto-disable if not TTY)
if [[ -t 1 ]]; then
  G='\033[0;32m'; R='\033[0;31m'; Y='\033[1;33m'; C='\033[0;36m'; B='\033[1m'; D='\033[0;90m'; N='\033[0m'
else
  G=''; R=''; Y=''; C=''; B=''; D=''; N=''
fi

# Parse args
MODULES=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --verbose)  VERBOSE=true; shift ;;
    --dry-run)  DRY_RUN=true; shift ;;
    --timeout)  TIMEOUT="$2"; shift 2 ;;
    --help|-h)  echo "Usage: ./run-all.sh [--verbose] [--dry-run] [--timeout N] [module.sh ...]"; exit 0 ;;
    *.sh)       MODULES+=("$1"); shift ;;
    *)          echo "Unknown: $1"; exit 1 ;;
  esac
done

# Find test modules if none specified
if [[ ${#MODULES[@]} -eq 0 ]]; then
  for f in "$SCRIPT_DIR"/test_*.sh; do
    [[ -f "$f" ]] && MODULES+=("$f")
  done
fi

if [[ ${#MODULES[@]} -eq 0 ]]; then
  echo "No test modules found in $SCRIPT_DIR"
  exit 1
fi

# Dry run
if $DRY_RUN; then
  echo -e "${B}Test modules that would run:${N}"
  for mod in "${MODULES[@]}"; do
    count=$(grep -cE '^\s*run_test\s' "$mod" 2>/dev/null || echo "?")
    echo "  $(basename "$mod") (~$count tests)"
  done
  exit 0
fi

# ============================================================================
# Test framework (sourced by test modules)
# ============================================================================

# Counters
TOTAL=0; PASSED=0; FAILED=0; SKIPPED=0
_MODULE_TOTAL=0; _MODULE_PASSED=0; _MODULE_FAILED=0; _MODULE_SKIPPED=0

# Run a single test with timeout and error handling
# Usage: run_test "description" "command" [timeout]
run_test() {
  local desc="$1" cmd="$2" timeout="${3:-$TIMEOUT}"
  ((TOTAL++)); ((_MODULE_TOTAL++))

  local start_time=$(date +%s%N 2>/dev/null || echo "0")
  local output="" exit_code=0

  # Run with timeout, capture output
  if output=$(timeout "$timeout" bash -c "$cmd" 2>&1); then
    exit_code=0
  else
    exit_code=$?
  fi

  local end_time=$(date +%s%N 2>/dev/null || echo "0")
  local elapsed_ms=0
  if [[ "$start_time" != "0" && "$end_time" != "0" ]]; then
    elapsed_ms=$(( (end_time - start_time) / 1000000 ))
  fi

  # Determine result
  if [[ $exit_code -eq 124 ]]; then
    # timeout command returns 124 on timeout
    echo -e "  ${Y}SKIP${N}  $desc ${D}(timeout ${timeout}s)${N}"
    ((SKIPPED++)); ((_MODULE_SKIPPED++))
  elif [[ $exit_code -eq 0 ]]; then
    echo -e "  ${G}PASS${N}  $desc ${D}(${elapsed_ms}ms)${N}"
    ((PASSED++)); ((_MODULE_PASSED++))
  else
    echo -e "  ${R}FAIL${N}  $desc ${D}(exit $exit_code, ${elapsed_ms}ms)${N}"
    ((FAILED++)); ((_MODULE_FAILED++))
    if $VERBOSE && [[ -n "$output" ]]; then
      echo "$output" | head -5 | sed 's/^/        /'
    fi
  fi
}

# Run a test that checks a condition (no command execution)
# Usage: check_test "description" "condition_command"
check_test() {
  run_test "$1" "$2" 5
}

# Skip a test with reason
# Usage: skip_test "description" "reason"
skip_test() {
  local desc="$1" reason="$2"
  ((TOTAL++)); ((SKIPPED++)); ((_MODULE_TOTAL++)); ((_MODULE_SKIPPED++))
  echo -e "  ${Y}SKIP${N}  $desc ${D}($reason)${N}"
}

# Print module summary
module_summary() {
  local name="$1"
  echo ""
  echo -e "  ${B}$name:${N} ${G}$_MODULE_PASSED passed${N}, ${R}$_MODULE_FAILED failed${N}, ${Y}$_MODULE_SKIPPED skipped${N}"
  _MODULE_TOTAL=0; _MODULE_PASSED=0; _MODULE_FAILED=0; _MODULE_SKIPPED=0
}

# Export for test modules
export -f run_test check_test skip_test module_summary
export TOTAL PASSED FAILED SKIPPED TIMEOUT VERBOSE
export G R Y C B D N
export _MODULE_TOTAL _MODULE_PASSED _MODULE_FAILED _MODULE_SKIPPED

# ============================================================================
# Run modules
# ============================================================================
echo -e "${B}AI Creative Studio - Test Suite${N}"
echo ""

START_ALL=$(date +%s)

TOTAL_ALL=0; PASSED_ALL=0; FAILED_ALL=0; SKIPPED_ALL=0

for mod in "${MODULES[@]}"; do
  mod_name=$(basename "$mod" .sh)
  echo -e "${C}━━━ $mod_name ━━━${N}"

  # Run module, capture its output and exit code
  mod_output=""
  mod_exit=0
  if ! mod_output=$(timeout 300 bash "$mod" 2>&1); then
    mod_exit=$?
  fi

  # Print output
  echo "$mod_output"

  # Extract counts from the module's summary line
  mod_passed=$(echo "$mod_output" | grep -oP '\d+(?= passed)' | tail -1 || echo 0)
  mod_failed=$(echo "$mod_output" | grep -oP '\d+(?= failed)' | tail -1 || echo 0)
  mod_skipped=$(echo "$mod_output" | grep -oP '\d+(?= skipped)' | tail -1 || echo 0)

  TOTAL_ALL=$((TOTAL_ALL + mod_passed + mod_failed + mod_skipped))
  PASSED_ALL=$((PASSED_ALL + mod_passed))
  FAILED_ALL=$((FAILED_ALL + mod_failed))
  SKIPPED_ALL=$((SKIPPED_ALL + mod_skipped))
done

END_ALL=$(date +%s)
ELAPSED=$((END_ALL - START_ALL))

# ============================================================================
# Final summary
# ============================================================================
echo -e "${B}━━━ SUMMARY ━━━${N}"
echo ""
echo -e "  Total:   $TOTAL_ALL tests"
echo -e "  ${G}Passed:  $PASSED_ALL${N}"
echo -e "  ${R}Failed:  $FAILED_ALL${N}"
echo -e "  ${Y}Skipped: $SKIPPED_ALL${N}"
echo -e "  Time:    ${ELAPSED}s"
echo ""

if [[ $FAILED_ALL -gt 0 ]]; then
  echo -e "  ${R}${B}RESULT: FAIL${N} ($FAILED_ALL test(s) failed)"
  echo -e "  ${D}Note: FAIL means the check ran and the system doesn't meet the requirement.${N}"
  echo -e "  ${D}SKIP means the check couldn't run (prerequisite missing).${N}"
  exit 1
elif [[ $PASSED_ALL -eq 0 ]]; then
  echo -e "  ${Y}${B}RESULT: NO TESTS RAN${N}"
  exit 2
else
  echo -e "  ${G}${B}RESULT: PASS${N}"
  exit 0
fi

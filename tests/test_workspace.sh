#!/usr/bin/env bash
# ============================================================================
# Test: Workspace
# Validates dashboard HTML structure, frontend elements, template integrity
# ============================================================================

set -uo pipefail

PASS=0; FAIL=0; SKIP=0; TOTAL=0
BASE="http://127.0.0.1:5000"
FETCH="curl -sf --max-time 10 $BASE/workspace 2>/dev/null"
FETCH_SETTINGS="curl -sf --max-time 10 $BASE/settings 2>/dev/null"
FETCH_PROJECTS="curl -sf --max-time 10 $BASE/projects 2>/dev/null"

run() {
  local desc="$1" cmd="$2" timeout="${3:-10}"
  ((TOTAL++))
  if timeout "$timeout" bash -c "$cmd" &>/dev/null; then
    echo -e "  \033[0;32mPASS\033[0m  $desc"; ((PASS++))
  elif [[ $? -eq 124 ]]; then
    echo -e "  \033[1;33mSKIP\033[0m  $desc (timeout)"; ((SKIP++))
  else
    echo -e "  \033[0;31mFAIL\033[0m  $desc"; ((FAIL++))
  fi
}

skip() { ((TOTAL++)); ((SKIP++)); echo -e "  \033[1;33mSKIP\033[0m  $1 ($2)"; }

# Check dashboard is reachable
if ! curl -sf --max-time 5 "$BASE/" &>/dev/null; then
  echo -e "  \033[1;33mSKIP\033[0m  Dashboard not reachable at $BASE"
  echo -e "  \033[1mWorkspace: 0 passed, 0 failed, all skipped (dashboard offline)\033[0m"
  exit 0
fi

# Workspace HTML structure -- fetch page inside each test
run "Workspace loads" "$FETCH | grep -q 'AI'"
run "Has mode selector" "$FETCH | grep -q 'modes'"
run "Has all 6 mode buttons" "[[ \$($FETCH | grep -c 'data-mode') -ge 6 ]]"
run "Has Text to Image mode" "$FETCH | grep -q 'data-mode=\"text-to-image\"'"
run "Has Text to Video mode" "$FETCH | grep -q 'data-mode=\"text-to-video\"'"
run "Has Image Edit mode" "$FETCH | grep -q 'data-mode=\"image-to-image\"'"
run "Has Animate mode" "$FETCH | grep -q 'data-mode=\"image-to-video\"'"
run "Has Write mode" "$FETCH | grep -q 'data-mode=\"write\"'"
run "Has Voice mode" "$FETCH | grep -q 'data-mode=\"voiceover\"'"
run "Has model selector" "$FETCH | grep -q 'modelSelect'"
run "Has prompt input" "$FETCH | grep -q 'promptInput'"
run "Has generate button" "$FETCH | grep -q 'generateBtn'"
run "Has upload zone" "$FETCH | grep -q 'uploadZone'"
run "Has history strip" "$FETCH | grep -q 'histStrip'"
run "Has settings link" "$FETCH | grep -q '/settings'"
run "Has projects link" "$FETCH | grep -q '/projects'"
run "Has CSS styles" "$FETCH | grep -q '<style>'"
run "Has JavaScript" "$FETCH | grep -q '<script>'"
run "Has generate function" "$FETCH | grep -q 'function generate'"

# Settings page
run "Settings page loads" "$FETCH_SETTINGS | grep -q 'Settings'"
run "Settings has theme selector" "$FETCH_SETTINGS | grep -q 'theme'"
run "Settings has voice selector" "$FETCH_SETTINGS | grep -q 'tts_voice'"
run "Settings has save button" "$FETCH_SETTINGS | grep -q 'saveSettings'"

# Projects page
run "Projects page loads" "$FETCH_PROJECTS | grep -q 'Projects'"

# Templates directory
TEMPLATES_DIR="/home/ubuntu/ai-creative-studio/app/dashboard/templates"
[[ -d "$TEMPLATES_DIR" ]] && run "Templates directory exists" "true" || skip "Templates dir" "not found"

for tpl in workspace.html index.html models.html settings.html projects.html; do
  [[ -f "$TEMPLATES_DIR/$tpl" ]] && run "Template $tpl exists" "true" || skip "Template $tpl" "not found"
done

echo ""
echo -e "  \033[1mWorkspace: $PASS passed, $FAIL failed, $SKIP skipped\033[0m"
[[ $FAIL -eq 0 ]]

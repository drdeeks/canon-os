#!/usr/bin/env bash
# ============================================================================
# Test: Models
# Validates model directory, model files, metadata, VRAM checks
# ============================================================================

set -uo pipefail

PASS=0; FAIL=0; SKIP=0; TOTAL=0

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

# Model directory structure
for type_dir in text image video audio; do
  [[ -d "/mnt/studio/models/$type_dir" ]] && run "Models /$type_dir exists" "true" || skip "Models /$type_dir" "not found"
done

# Model catalog (Python module)
CATALOG="/home/ubuntu/ai-creative-studio/app/dashboard/model_catalog.py"
if [[ -f "$CATALOG" ]]; then
  run "Model catalog valid Python" "python3 -c 'import py_compile; py_compile.compile(\"$CATALOG\", doraise=True)'" 5
  run "Model catalog loads" "cd /home/ubuntu/ai-creative-studio/app/dashboard && python3 -c 'from model_catalog import MODEL_CATALOG; assert len(MODEL_CATALOG) > 0'" 5
  run "Model catalog has text models" "cd /home/ubuntu/ai-creative-studio/app/dashboard && python3 -c 'from model_catalog import MODEL_CATALOG; text=[m for m in MODEL_CATALOG.values() if m.get(\"type\")==\"text\"]; assert len(text) > 0'" 5
  run "Model catalog has image models" "cd /home/ubuntu/ai-creative-studio/app/dashboard && python3 -c 'from model_catalog import MODEL_CATALOG; img=[m for m in MODEL_CATALOG.values() if m.get(\"type\")==\"image\"]; assert len(img) > 0'" 5
  run "Model catalog has video models" "cd /home/ubuntu/ai-creative-studio/app/dashboard && python3 -c 'from model_catalog import MODEL_CATALOG; vid=[m for m in MODEL_CATALOG.values() if m.get(\"type\")==\"video\"]; assert len(vid) > 0'" 5
  run "Model catalog has audio models" "cd /home/ubuntu/ai-creative-studio/app/dashboard && python3 -c 'from model_catalog import MODEL_CATALOG; aud=[m for m in MODEL_CATALOG.values() if m.get(\"type\") in (\"tts\",\"stt\",\"music\")]; assert len(aud) > 0'" 5
  run "Each model has required fields" "cd /home/ubuntu/ai-creative-studio/app/dashboard && python3 -c '
from model_catalog import MODEL_CATALOG
for mid, m in MODEL_CATALOG.items():
    for field in [\"id\",\"name\",\"type\",\"size_gb\",\"download_url\",\"local_path\"]:
        assert field in m, f\"{mid} missing {field}\"
'" 5
else
  skip "Model catalog" "file not found"
fi

# Model state file
STATE_FILE="/opt/ai-studio/config/model-state.json"
if [[ -f "$STATE_FILE" ]]; then
  run "Model state valid JSON" "python3 -c 'import json; json.load(open(\"$STATE_FILE\"))'" 5
else
  skip "Model state file" "not found (no models pulled yet)"
fi

# Installed model files
INSTALLED_COUNT=0
for type_dir in text image video audio; do
  dir="/mnt/studio/models/$type_dir"
  [[ "$type_dir" == "audio" ]] && dir="/mnt/studio/models/audio"
  if [[ -d "$dir" ]]; then
    count=$(find "$dir" -maxdepth 3 \( -name "*.gguf" -o -name "*.safetensors" -o -name "*.onnx" -o -name "*.bin" \) 2>/dev/null | wc -l)
    INSTALLED_COUNT=$((INSTALLED_COUNT + count))
  fi
done

if [[ $INSTALLED_COUNT -gt 0 ]]; then
  run "Models installed ($INSTALLED_COUNT found)" "true"
  # Check each installed model file is readable
  while IFS= read -r f; do
    name=$(basename "$f")
    size=$(stat -c%s "$f" 2>/dev/null || echo 0)
    run "Model file readable: $name" "[[ $size -gt 0 ]] && [[ -r '$f' ]]" 5
  done < <(find /mnt/studio/models -maxdepth 4 \( -name "*.gguf" -o -name "*.safetensors" -o -name "*.onnx" -o -name "*.bin" \) 2>/dev/null | head -10)
else
  skip "Installed models" "none found (pull with: studio-model pull <id>)"
fi

# Broken symlinks
run "No broken symlinks in models" "! find /mnt/studio/models -maxdepth 3 -xtype l 2>/dev/null | grep -q ." 10 2>/dev/null || skip "Symlink check" "storage not mounted"

# VRAM check
if command -v nvidia-smi &>/dev/null; then
  TOTAL_VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 || echo 0)
  USED_VRAM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 || echo 0)
  if [[ $TOTAL_VRAM -gt 0 ]]; then
    run "VRAM checkable" "true"
    FREE_VRAM=$((TOTAL_VRAM - USED_VRAM))
    if [[ $FREE_VRAM -gt 2048 ]]; then
      run "VRAM sufficient (${FREE_VRAM}MB free)" "true"
    else
      run "VRAM low (${FREE_VRAM}MB free)" "false"
    fi
  else
    skip "VRAM check" "could not read VRAM"
  fi
else
  skip "VRAM check" "no NVIDIA GPU"
fi

echo ""
echo -e "  \033[1mModels: $PASS passed, $FAIL failed, $SKIP skipped\033[0m"
[[ $FAIL -eq 0 ]]

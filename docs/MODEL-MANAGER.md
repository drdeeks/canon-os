# Model Manager — Lifecycle Documentation

## Overview

The Model Manager enforces strict single-model VRAM usage across the AI Creative Studio. Only one heavy model may reside in GPU memory at any time. All model transitions follow a release-then-load pattern to prevent VRAM exhaustion.

Supported model types:
- **GGUF** (llama.cpp) — text generation (chat, code, creative writing)
- **PyTorch/diffusers** (ComfyUI) — image and video generation

---

## Core Principle: One-Model-at-a-Time

```
  [User Request: Load New Model]
            |
            v
  +-------------------------+
  | Is a model loaded?      |
  +-------------------------+
     | Yes                  | No
     v                      v
  [Graceful Offload]    [Direct Load]
     |                      |
     v                      v
  [Load New Model into VRAM]
     |
     v
  [Warm-Up / Verify]
     |
     v
  [Model Ready]
```

**Enforcement rules:**
- No model may begin loading until the current model is fully released from VRAM.
- If the offload step fails, the load request is aborted and the user is notified.
- The system tracks `active_model_id` at all times. A null value means VRAM is free.

---

## Graceful Offload Procedure

When switching models, the system performs:

1. **Inference cancellation** — Any running generation is stopped cleanly.
2. **State flush** — KV cache (llama.cpp) or attention states (diffusers) are cleared.
3. **VRAM release** — GPU memory is explicitly freed via `cuda.empty_cache()` (PyTorch) or `llama_free()` (llama.cpp).
4. **Process teardown** — Background workers holding model references are terminated.
5. **Verification** — `nvidia-smi` confirms VRAM usage has dropped to baseline (~200 MB for driver overhead).

Graceful offload typically takes 2–10 seconds depending on model size. The GUI shows a spinner with "Releasing [model_name]..." during this phase.

---

## Model Registry

Models are managed via the `studio-model` CLI which tracks state in:

| Source | Path | Purpose |
|--------|------|---------|
| State file | `/opt/ai-studio/config/model-state.json` | Tracks installed models |
| Model files | `/opt/ai-studio/models/` | Downloaded model files |
| Catalog | `/opt/ai-studio/config/model_catalog.json` | Available models catalog |
| Shared storage | `/mnt/studio/models/` | Models shared with Docker containers |

The CLI discovers models from the state file and the catalog. Models are downloaded
to `/opt/ai-studio/models/<model-id>/` and can be symlinked or copied to
`/mnt/studio/models/` for container access.

Directory structure:

```
/opt/ai-studio/
  config/
    model-state.json        # Installed model tracking
    model_catalog.json      # Available models catalog
  models/
    llama-3.1-70b/
      <downloaded files>
    flux1-dev/
      <downloaded files>

/mnt/studio/models/
  text/                     # GGUF models for Ollama/llama.cpp
  image/                    # Diffusion models for ComfyUI
  video/                    # Video generation models
  audio/                    # TTS, STT, music models
```

---

## Model Metadata (model.json)

Every model directory must contain a `model.json` file. This is the registry entry point.

### Schema

```json
{
  "id": "llama-3-8b-q4_k_m",
  "name": "Llama 3 8B",
  "type": "gguf",
  "engine": "llama.cpp",
  "vram_mb": 6200,
  "quant": "Q4_K_M",
  "parameter_count": "8B",
  "context_length": 8192,
  "file": "model.gguf",
  "tags": ["chat", "creative", "code"],
  "warmup_time_estimate_sec": 3,
  "description": "Llama 3 8B quantized to Q4_K_M for fast local inference"
}
```

### ComfyUI / diffusers model example

```json
{
  "id": "sdxl-base-1.0",
  "name": "Stable Diffusion XL Base",
  "type": "diffusers",
  "engine": "comfyui",
  "vram_mb": 6800,
  "quant": null,
  "format": "diffusers",
  "components": ["unet", "vae", "text_encoder", "tokenizer"],
  "tags": ["image", "text-to-image"],
  "warmup_time_estimate_sec": 8,
  "description": "SDXL base model for text-to-image generation"
}
```

### Required fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier (directory name convention) |
| `name` | Human-readable display name |
| `type` | `"gguf"` or `"diffusers"` |
| `engine` | `"llama.cpp"` or `"comfyui"` |
| `vram_mb` | Estimated VRAM usage in megabytes |
| `tags` | Array of capability tags for filtering |

### Optional fields

| Field | Description |
|-------|-------------|
| `quant` | GGUF quantization level (Q2_K, Q3_K_M, Q4_K_M, Q5_K_M, Q6_K, Q8_0) |
| `file` | GGUF filename if not `model.gguf` |
| `parameter_count` | Human-readable param count ("8B", "70B") |
| `context_length` | Max context window |
| `components` | List of subdirectories for diffusers models |
| `warmup_time_estimate_sec` | Expected seconds to first-token / first-image |

---

## Model Loading and Unloading via GUI

The GUI provides a dropdown menu for non-technical users:

```
+------------------------------------------+
|  Active Model: [Llama 3 8B       ] [v]  |
+------------------------------------------+
|  > Llama 3 8B (6.2 GB VRAM)            |
|    Llama 3 70B Q3 (28 GB VRAM)         |
|    CodeLlama 13B Q5 (9.8 GB VRAM)      |
|    SDXL Base (6.8 GB VRAM)             |
|    Flux Dev (12 GB VRAM)               |
|    Wan2.1 Video (14 GB VRAM)           |
|  -------------------------------------- |
|    [Unload Model]                        |
+------------------------------------------+
```

**Behavior:**
- Selecting a model from the dropdown triggers the full offload-then-load cycle.
- The dropdown is disabled during model transitions (grayed out with progress indicator).
- Models whose `vram_mb` exceeds available GPU memory are shown but grayed out with a tooltip: "Requires X GB VRAM, Y GB available."
- The `[Unload Model]` option gracefully offloads the current model without loading a replacement, freeing all VRAM.

**Admin override via SSH:**

```bash
# List available models
studio-model list

# Search for models
studio-model search "product shots"

# Show model details
studio-model info llama-3.1-70b

# Download a model
studio-model pull llama-3.1-70b

# Force re-download
studio-model pull llama-3.1-70b --force

# Remove a model
studio-model remove llama-3.1-70b

# Check system status
studio-model status

# Get recommendations by use case
studio-model recommend --use-case product-shots

# Get recommendations by hardware
studio-model recommend --hardware
```

The `--force` flag forces re-download of an already installed model.

---

## Auto-Offload on Idle Timeout

To free GPU memory when not in use:

| Setting | Default | Description |
|---------|---------|-------------|
| `idle_timeout_minutes` | 15 | Minutes of no inference before auto-offload |
| `keep_loaded_tags` | `[]` | Models with these tags are exempt (e.g., `["always-loaded"]`) |
| `wakeup_behavior` | `"load-on-demand"` | Model reloads when user sends a request |

**Idle detection triggers:**
- No generation requests (text or image) for the configured timeout.
- No active WebSocket connections from the GUI.
- No scheduled batch jobs in the queue.

**Auto-offload sequence:**
1. Timer fires after idle threshold.
2. System checks for active requests one final time.
3. If still idle, graceful offload runs.
4. VRAM is freed. Status shows "No model loaded."
5. Next user request triggers automatic reload of the last-used model (or user selection).

**GUI notification:** When auto-offload occurs, a subtle toast message appears: "Model unloaded to free GPU memory. It will reload when you start typing."

---

## VRAM Budget Management

The system tracks GPU memory to prevent out-of-memory crashes:

```
Total GPU VRAM:  24576 MB  (e.g., RTX 4090)
Driver overhead:   200 MB
ComfyUI base:      500 MB  (when image models are loaded)
System reserve:    800 MB  (OS + desktop + display)
─────────────────────────
Available for models: 23076 MB
```

**Budget enforcement:**

```python
def can_load_model(model: ModelInfo) -> bool:
    available = get_free_vram_mb()
    required = model.vram_mb
    reserve = get_system_reserve_mb()
    return (available - reserve) >= required
```

**Configuration (`config.yaml`):**

```yaml
vram:
  total_mb: 24576
  system_reserve_mb: 800
  engine_overhead:
    llama.cpp: 200
    comfyui: 500
  oom_safety_margin_mb: 500
```

**Behavior on insufficient VRAM:**
- GUI shows: "[Model Name] requires X GB but only Y GB available."
- Dropdown entry is disabled.
- User can unload the current model first to free space.

---

## Warm-Up vs Cold-Load Behavior

### Cold Load
First-time model load from disk. Requires full file read and GPU allocation.

| Model type | Typical cold load time |
|------------|----------------------|
| GGUF 8B (Q4) | 5–15 seconds |
| GGUF 70B (Q3) | 30–90 seconds |
| SDXL diffusers | 10–25 seconds |
| Flux diffusers | 15–40 seconds |

### Warm-Up
After the model is loaded, a warm-up step prepares it for first use:

**llama.cpp (GGUF):**
- Allocate KV cache for configured context length.
- Run a short dummy prompt (1 token) to initialize CUDA kernels.
- Warm-up time: 1–5 seconds.

**ComfyUI (diffusers):**
- Load model components into GPU (UNet, VAE, text encoder).
- Initialize attention kernels and memory allocators.
- Optionally run a 1-step dummy denoise pass.
- Warm-up time: 3–12 seconds.

### Reload from Cache (Warm Model)
If a model was recently offloaded and OS file cache is still warm:

| Scenario | Effective speed |
|----------|----------------|
| File cache hot | ~50–80% of cold load |
| File cache cold (SSD) | Same as cold load |
| File cache cold (HDD) | 2–5x slower than cold load |

The GUI progress bar uses the `warmup_time_estimate_sec` from `model.json` to show estimated time.

---

## GGUF (llama.cpp) vs Diffusers (ComfyUI) Handling

The two model types are managed by different engines with distinct characteristics:

| Aspect | GGUF (llama.cpp) | Diffusers (ComfyUI) |
|--------|-------------------|---------------------|
| **Loading** | Single `.gguf` file, `llama_model_load()` | Multiple files (safetensors/bin), `from_pretrained()` |
| **VRAM allocation** | Contiguous block, predictable | Fragmented across components |
| **Offloading** | `llama_free()` — single call | Unload each component separately |
| **Quantization** | Built into GGUF format (Q2–Q8) | Separate weight files, FP16/FP8/INT8 |
| **Memory mapping** | mmap support, can offload layers to CPU | No native mmap, full GPU or CPU offload |
| **Multi-model** | Not applicable (one-model rule) | LoRAs and ControlNets loaded alongside base |
| **Detection** | `.gguf` extension in model directory | `model_index.json` + component subdirs |

### GGUF-specific notes

- GGUF models are loaded entirely into VRAM unless `n_gpu_layers` is set to partial offload.
- The `quant` field in `model.json` must match the actual GGUF quantization for accurate VRAM estimation.
- Partial GPU offloading (some layers on CPU) is supported but not exposed in the GUI — admin SSH only:

```bash
studio-model load llama-3-70b-q3 --gpu-layers 40
```

### Diffusers-specific notes

- ComfyUI models may include LoRA adapters loaded on top of the base model. LoRA overhead is estimated and added to `vram_mb`.
- The `components` array in `model.json` must list all required subdirectories.
- VAE and text encoder can optionally be offloaded to CPU to save VRAM (controlled by ComfyUI workflow settings).
- ControlNet, IP-Adapter, and similar add-ons each consume additional VRAM not tracked in the base model's `vram_mb`. The system shows a warning when these are active.

---

## Configuration Reference

The model manager uses JSON configuration files:

**Model state** (`/opt/ai-studio/config/model-state.json`):

```json
{
  "installed": {
    "llama-3.1-8b": {
      "path": "/opt/ai-studio/models/llama-3.1-8b/model.gguf",
      "size_gb": 4.7,
      "installed_at": "2026-01-15 10:30:00",
      "sha256": "abc123..."
    }
  },
  "disk_usage_gb": 4.7,
  "vram_budget_gb": 24.0,
  "last_updated": "2026-01-15 10:30:00"
}
```

**Model catalog** (`/opt/ai-studio/config/model_catalog.json`): same structure as the
built-in `DEFAULT_CATALOG` in `model_catalog.py` — a dict keyed by type (text, image,
video, tts) containing lists of model entries with id, name, size_gb, etc.

---

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `VRAM_INSUFFICIENT` | Not enough GPU memory | Unload current model or choose smaller model |
| `OFFLOAD_FAILED` | Model process stuck or crashed | Force-kill process, retry, or reboot |
| `MODEL_NOT_FOUND` | ID not in registry | Check `model.json` exists, rescan registry |
| `METADATA_INVALID` | Malformed `model.json` | Fix JSON, required fields missing |
| `ENGINE_CRASH` | llama.cpp or ComfyUI segfault | Check logs, may indicate corrupt model file |
| `TIMEOUT` | Load exceeded 5 minutes | Check disk I/O, file integrity, GPU health |

All errors are logged to `model-manager.log` with full stack traces and system state snapshots (VRAM usage, process list, disk space).

---

## File Inventory

| Path | Purpose |
|------|---------|
| `~/ai-creative-studio/docs/MODEL-MANAGER.md` | This document |
| `/opt/ai-studio/models/` | Downloaded model files |
| `/opt/ai-studio/config/model-state.json` | Installed model tracking |
| `/opt/ai-studio/config/model_catalog.json` | Available models catalog |
| `/opt/ai-studio/backups/` | Model state backups |
| `/mnt/studio/models/` | Shared model storage (Docker containers) |
| `/usr/local/bin/studio-model` | CLI tool (installed by setup) |

```
  ___    _____ ___       ____                _       _
 / _ \  |_   _/ _ \     / ___|_ __ _   _ ___| |_    / \   _ __ __ _  ___ _ __
| | | |   | || | | |   | |   | '__| | | / __| __|  / _ \ | '__/ _` |/ _ \ '__|
| |_| |   | || |_| |   | |___| |  | |_| \__ \ |_  / ___ \| | | (_| |  __/ |
 \___/    |_| \___/     \____|_|   \__,_|___/\__| /_/   \_\_|  \__, |\___|_|
                                                                |___/
```

# Canon OS — Creative Studio

Local-only AI creative studio for video editors and content creators.
Runs on a dedicated compute brain. Access from any device via SSH + browser.
Zero cloud. Zero API costs. Zero data leakage.

> **Project identity:** This studio is **Canon OS**. See `CANON_OS.md` for the
> project foundation — vision, how it functions, and what it requires.

---

## Table of Contents

1. [What This Is](#what-this-is)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Setup Options](#setup-options)
5. [The Interfaces](#the-interfaces)
6. [InvokeAI (Primary UI)](#invokeai-primary-ui)
7. [Flask Dashboard (Companion)](#flask-dashboard-companion)
8. [Workflows](#workflows)
9. [Models](#models)
10. [Model Management](#model-management)
11. [Backend Configuration](#backend-configuration)
12. [Adding New Backends](#adding-new-backends)
13. [Docker Services](#docker-services)
14. [Storage Design](#storage-design)
15. [Security](#security)
16. [Dual-User Setup](#dual-user-setup)
17. [Admin Flow](#admin-flow)
18. [Creator Flow](#creator-flow)
19. [Getting Output to Your Laptop](#getting-output-to-your-laptop)
20. [CLI Tools Reference](#cli-tools-reference)
21. [Updating the System](#updating-the-system)
22. [Adding New Models](#adding-new-models)
23. [Adding New Services](#adding-new-services)
24. [Troubleshooting](#troubleshooting)
25. [Testing](#testing)
26. [Hardware Guide](#hardware-guide)
27. [Project Structure](#project-structure)

---

## What This Is

A single-purpose appliance. It runs AI models and serves browser
interfaces. Nothing else.

Your laptop connects via SSH to manage it. The compute brain does
the heavy lifting. All your work stays on your laptop. The compute
brain is just a remote GPU.

```
YOUR LAPTOP                          COMPUTE BRAIN (appliance)
                                     Docker:
  SSH to manage:                       - InvokeAI (image/video -- primary UI)
    ssh -p 2222 admin@brain            - llama.cpp (text generation)
    status  dcup  dcdown               - ComfyUI (backend engine)
    models pull llama-3.1-8b           - Kokoro TTS (voiceover)
    doctor                             - Whisper (transcription)
                                       - MusicGen (music)
  Browser to create:                   - Dashboard (text/audio companion)
    http://localhost:9090               - Open WebUI (chat, optional)
    InvokeAI -- image/video
    http://localhost:5000             External SSD:
    Dashboard -- text/audio             - /mnt/studio/models/
                                        - /mnt/studio/exports/
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        COMPUTE BRAIN                                 │
│                                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ InvokeAI │ │ llama.cpp│ │ ComfyUI  │ │ Kokoro   │ │ Whisper  │  │
│  │ (UI)     │ │ (text)   │ │ (engine) │ │ (TTS)    │ │ (STT)    │  │
│  │ :9090    │ │ :8080    │ │ :8188    │ │ :8880    │ │ :9000    │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │
│       │             │            │             │            │        │
│  ┌────┴─────┐ ┌─────┴────┐ ┌────┴─────┐      │            │        │
│  │ MusicGen │ │ Dashboard│ │ OpenWebUI│      │            │        │
│  │ :7860    │ │ :5000    │ │ :3000    │      │            │        │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘      │            │        │
│       └─────────────┴────────────┘            │            │        │
│                    │                           │            │        │
│              Docker Network (studio-network)   │            │        │
│                    │                           │            │        │
│              ┌─────┴───────────────────────────┴────────────┘        │
│              │                                                       │
│         External SSD (/mnt/studio/)                                  │
│           ├── invokeai/     (InvokeAI data)                          │
│           ├── models/       (AI models)                              │
│           ├── exports/      (generated output)                       │
│           ├── uploads/      (user uploads)                           │
│           ├── cache/        (model cache)                            │
│           ├── projects/     (project files)                          │
│           ├── logs/         (system logs)                            │
│           └── config/       (configuration)                          │
└──────────────────────────────────────────────────────────────────────┘
```

**9 Docker services, each isolated:**

| Service | Port | Purpose |
|---------|------|---------|
| `studio-invokeai` | 9090 | Leonardo-style creative UI (PRIMARY) |
| `studio-dashboard` | 5000 | Text/audio companion UI |
| `studio-llamacpp` | 8080 | Text generation backend |
| `studio-comfyui` | 8188 | Image/video generation engine |
| `studio-whisper` | 9000 | Speech-to-text |
| `studio-kokoro` | 8880 | Text-to-speech |
| `studio-audiocraft` | 7860 | Music generation |
| `studio-openwebui` | 3000 | Chat interface (optional) |
| `studio-ollama` | 11434 | Alternative text backend |

---

## Quick Start

```bash
# On the compute brain:
git clone <repo-url> ~/ai-creative-studio
cd ~/ai-creative-studio

# Install everything (Docker, SSH, storage, users)
sudo bash scripts/setup-master.sh

# Set up admin access
sudo bash scripts/setup-users.sh \
  --admin-pubkey "ssh-ed25519 AAAA... you@laptop"

# Start the studio
cd /opt/ai-studio && docker compose up -d
```

From your laptop:
```bash
# SSH tunnel for both interfaces
ssh -p 2222 -L 9090:127.0.0.1:9090 -L 5000:127.0.0.1:5000 admin@<brain-ip>

# Open in browser:
# http://localhost:9090  (InvokeAI -- image/video)
# http://localhost:5000  (Dashboard -- text/audio)
```

---

## Setup Options

```
sudo bash scripts/setup-master.sh [OPTIONS]

  --auto              Unattended (defaults for everything)
  --yes, -y           Same as --auto
  --dry-run           Preview without changing anything
  --strict            Abort on any failure
  --skip-docker       Skip Docker installation
  --skip-ssh          Skip SSH hardening
  --skip-gpu          Skip GPU toolkit
  --skip-containers   Skip image pulls
  --admin-pubkey KEY  Set up admin SSH access
  --external DRIVE    External drive to format
  --mount PATH        Mount point (default: /mnt/studio)
  --help              Show all options
```

Every prompt has a 10-second timeout. Every prompt offers Skip.
Nothing hangs. Nothing is forced.

---

## The Interfaces

Two browser interfaces. InvokeAI for image/video. Dashboard for text/audio.

---

## InvokeAI (Primary UI)

Leonardo AI-style creative studio. The main interface for all image
and video work.

**Port:** 9090
**URL:** http://localhost:9090 (via SSH tunnel)

**Features:**
- Text to Image with batch generation (1-16 images per prompt)
- Inpainting (brush select area, regenerate only that area)
- Outpainting (extend image borders)
- Background removal
- Style references (upload reference image for consistent style)
- Drag and drop assets
- Quality sliders (steps, CFG scale, scheduler, denoising strength)
- Image sizing (512 to 2048, any aspect ratio)
- Gallery with albums and search
- ControlNet support (edge detection, pose, depth)
- LoRA stacking (combine multiple style adapters)
- Built-in model manager (download models from UI)
- Workflows tab (pre-built and custom workflows)
- Full REST API for automation

**Docker image:** `ghcr.io/invoke-ai/invokeai:latest`
**Source:** https://github.com/invoke-ai/InvokeAI
**Data directory:** `/mnt/studio/invokeai/` (bind-mounted to `/invokeai`)

---

## Flask Dashboard (Companion)

Companion interface for text generation, TTS, and transcription.
InvokeAI doesn't handle these, so the dashboard fills the gap.

**Port:** 5000
**URL:** http://localhost:5000 (via SSH tunnel)

**Modes:**
- **Write** -- Free text generation via llama.cpp (scripts, ad copy, taglines)
- **Voice** -- Text-to-speech via Kokoro TTS (voiceovers)
- **Transcribe** -- Speech-to-text via Whisper (subtitles)

---

## Workflows

Pre-built pipelines. Pick one, fill in prompts, hit run.

### 30s Product Commercial (~90 min)

```
Creator fills in: product description, tone, target audience

  1. SCRIPT     Llama 70B writes 30s narration
  2. FRAMES     Flux.1 Dev generates 8 storyboard images
  3. CLIPS      CogVideoX animates frames into 4x 5s clips
  4. VOICE      Kokoro TTS generates voiceover
  5. MUSIC      MusicGen generates background music
  6. SUBTITLES  Whisper transcribes the voiceover

  -> All outputs ready for assembly in DaVinci Resolve
```

### Thumbnail Batch (~5 min)
```
1. PROMPTS    Gemma 27B generates image prompts
2. IMAGES     Flux.1 Dev generates images
3. UPSCALE    Real-ESRGAN upscales best picks
```

### Quick Voiceover (~1 min)
```
1. TTS        Kokoro generates WAV from pasted script
```

### Transcribe (~2 min)
```
1. STT        Whisper generates timestamped subtitles
```

### Script to Video (~20 min)
```
1. IMAGE      Flux.1 Dev generates scene
2. ANIMATE    SVD animates it
```

---

## Models

### Supported Models (10 core models)

**Text (scripts, ad copy, taglines):**

| Model | Size | Quality | Speed | Download |
|-------|------|---------|-------|----------|
| Llama 3.1 8B Q4 | 5GB | Good | 50-80 tok/s | `studio-model pull llama-3.1-8b` |
| Llama 3.1 70B Q4 | 40GB | Excellent | 12-18 tok/s | `studio-model pull llama-3.1-70b` |
| Gemma2 27B Q4 | 16GB | Excellent | 25-40 tok/s | `studio-model pull gemma-2-27b` |

**Image (product shots, ads, thumbnails):**

| Model | Size | Quality | Speed | Download |
|-------|------|---------|-------|----------|
| Flux.1 Dev | 12GB | Excellent | ~25s/image | `studio-model pull flux1-dev` |
| SDXL 1.0 | 7GB | Professional | ~10s/image | `studio-model pull sdxl-base` |

**Video (clips, animations):**

| Model | Size | Quality | Speed | Download |
|-------|------|---------|-------|----------|
| CogVideoX-5B | 12GB | Good | ~15min/clip | `studio-model pull cogvideox-5b` |
| SVD-XT | 9GB | Good | ~6min/clip | `studio-model pull svd-xt` |

**Audio (voiceover, music, transcription):**

| Model | Size | Quality | Speed | Download |
|-------|------|---------|-------|----------|
| Kokoro TTS | 0.5GB | Very good | Real-time | `studio-model pull kokoro-tts` |
| Whisper Large-v3 | 3GB | Excellent | Faster than RT | `studio-model pull whisper-large-v3` |
| MusicGen Medium | 3.5GB | Good | ~2min/track | `studio-model pull musicgen-medium` |

---

## Model Management

### CLI Commands

```bash
studio-model list                          # All available models
studio-model list --type text              # Filter by type
studio-model list --installed              # Only downloaded
studio-model list --use-case product-shots # Filter by use case
studio-model search "whisper"              # Fuzzy search
studio-model info llama-3.1-70b            # Full details + download URL
studio-model pull llama-3.1-8b             # Download with progress
studio-model remove old-model              # Free disk space
studio-model status                        # Disk usage + VRAM overview
studio-model recommend --hardware          # What fits your GPU
studio-model recommend --use-case scripts  # What to install for X
studio-model backup                        # Backup model state
studio-model restore <backup-dir>          # Restore from backup
studio-model --json                        # Machine-readable output
```

### Where Models Live

```
/mnt/studio/models/
  ├── text/          GGUF files (llama.cpp)
  ├── image/         Safetensors (ComfyUI/InvokeAI)
  ├── video/         Safetensors (CogVideoX, SVD)
  └── audio/
      ├── tts/       ONNX/PTH (Kokoro)
      ├── stt/       GGML (Whisper)
      └── music/     (MusicGen)
```

### InvokeAI Models

InvokeAI manages its own models inside `/mnt/studio/invokeai/models/`.
It auto-scans at startup. Use InvokeAI's Settings -> Models page to
import models, or place files directly in the directory.

---

## Backend Configuration

Edit one file to swap any backend. No code changes.

```json
// /opt/ai-studio/config/backends.json
{
  "backends": {
    "text": "llama-cpp",       // ollama, vllm, openai
    "image": "comfyui",        // automatic1111
    "video": "comfyui-video",  // animatediff
    "tts": "kokoro",           // coqui, bark
    "stt": "whisper",          // faster-whisper
    "music": "audiocraft"      // stable-audio, ace-step
  },
  "urls": {
    "llama-cpp": "http://studio-llamacpp:8080",
    "ollama": "http://studio-ollama:11434",
    "comfyui": "http://studio-comfyui:8188",
    "kokoro": "http://studio-kokoro:8880",
    "whisper": "http://studio-whisper:9000",
    "audiocraft": "http://studio-audiocraft:7860"
  }
}
```

---

## Adding New Backends

### 1. Create adapter file

```python
# app/dashboard/backends/yourbackend.py
from .registry import register_backend
from .text import TextBackend  # or ImageBackend, VideoBackend, TTSBackend, STTBackend

@register_backend("your-backend")
class YourBackend(TextBackend):
    def __init__(self, url: str, config: dict = None):
        self.url = url

    def generate(self, prompt: str, model: str = None, **kwargs) -> dict:
        import json, urllib.request
        payload = json.dumps({"prompt": prompt}).encode()
        req = urllib.request.Request(
            f"{self.url}/generate",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=120)
        data = json.loads(resp.read())
        return {"response": data.get("output", ""), "model": model}

    def list_models(self) -> list:
        try:
            import urllib.request
            resp = urllib.request.urlopen(f"{self.url}/models", timeout=5)
            return json.loads(resp.read())
        except Exception:
            return []

    def health_check(self) -> bool:
        try:
            import urllib.request
            urllib.request.urlopen(f"{self.url}/health", timeout=3)
            return True
        except Exception:
            return False
```

### 2. Update config

```json
{
  "backends": {"text": "your-backend"},
  "urls": {"your-backend": "http://localhost:8080"}
}
```

### 3. Restart dashboard

```bash
cd /opt/ai-studio && docker compose restart dashboard
```

---

## Docker Services

### Full Stack

```bash
cd /opt/ai-studio
docker compose up -d          # Start all
docker compose down            # Stop all
docker compose ps              # Status
docker compose logs -f         # Logs
docker compose restart <name>  # Restart one service
```

### Individual Service Management

```bash
# Start just InvokeAI
docker compose up -d invokeai

# View InvokeAI logs
docker compose logs -f invokeai

# Rebuild dashboard after code changes
docker compose up -d --build dashboard

# Check resource usage
docker stats
```

### Service Health Checks

Every service has a healthcheck. Check status:

```bash
docker inspect --format='{{.State.Health.Status}}' studio-invokeai
docker inspect --format='{{.State.Health.Status}}' studio-dashboard
docker inspect --format='{{.State.Health.Status}}' studio-llamacpp
```

---

## Storage Design

Everything on external SSD. Compute brain root stays clean.

```
/mnt/studio/                    (External SSD mount point)
  invokeai/                     InvokeAI data (models, outputs, gallery)
  models/
    text/                       GGUF models (llama.cpp)
    image/                      Image models (ComfyUI/InvokeAI)
    video/                      Video models
    audio/
      tts/                      TTS models
      stt/                      Speech-to-text models
      music/                    Music generation models
  exports/                      Generated output (shared by all services)
  uploads/                      User uploads
  projects/                     Project files
  cache/
    huggingface/                HuggingFace model cache
    comfyui/                    ComfyUI custom nodes cache
  logs/                         System logs
  config/                       Configuration files
  admin-scratch/                Admin accidental files (protected from root)
```

---

## Security

```
Layer                  Mechanism
─────────────────────  ──────────────────────────────────────
Network                UFW firewall (only SSH port 2222)
Authentication         Ed25519 SSH keys only (no passwords)
Brute force            fail2ban (3 tries = 1hr ban)
Container isolation    Non-root, read-only rootfs, cap_drop ALL
Data isolation         External storage, never on host root
Access control         Creator (GUI only) vs Admin (SSH only)
Web UIs                SSH tunnel only (never exposed to internet)
Admin files            /mnt/studio/admin-scratch/ (not root disk)
Docker socket          Admin only (ACL)
```

---

## Dual-User Setup

Two accounts on one machine. Complete isolation.

| | Creator (guest) | Admin (you) |
|---|---------|-------|
| **Purpose** | Use the studio | Manage the studio |
| **Access** | Browser GUI | SSH on port 2222 |
| **Shell** | `/usr/sbin/nologin` | bash |
| **Sudo** | No | Limited (Docker + studio) |
| **Docker** | No | Yes |
| **Files on compute brain** | Their projects | **Nothing** |

```bash
sudo bash scripts/setup-users.sh \
  --admin-pubkey "ssh-ed25519 AAAA... admin@laptop"
```

---

## Admin Flow

```bash
# SSH in from your laptop
$ ssh -p 2222 admin@brain

  +---------------------------------------------+
  |  AI CREATIVE STUDIO - COMPUTE BRAIN         |
  |  This machine: studio appliance only        |
  |  Your work: stays on YOUR laptop            |
  |  Commands: status dcup dcdown dclogs models  |
  +---------------------------------------------+

# Check health
admin@brain:~$ status

# Start/stop
admin@brain:~$ dcup
admin@brain:~$ dcdown

# Manage models
admin@brain:~$ models pull llama-3.1-8b
admin@brain:~$ models list

# Diagnose
admin@brain:~$ doctor

# Logs
admin@brain:~$ dclogs

# Leave
admin@brain:~$ exit
```

If you accidentally create files while SSHed in, they go to
`/mnt/studio/admin-scratch/` (external SSD), not root disk.

---

## Creator Flow

Opens browser. Uses InvokeAI for images/video, Dashboard for text/audio.
Cannot SSH in. Cannot break anything.

```
1. Open http://localhost:9090 (InvokeAI)
2. Enter prompt
3. Select model
4. Adjust settings (steps, CFG, size)
5. Click Generate
6. Result appears in gallery
7. Download, edit, or continue
```

---

## Getting Output to Your Laptop

**Option 1: Download from browser**
Click Save/Download on any generation.

**Option 2: rsync exports directory**
```bash
# From your laptop:
rsync -avz --progress -e "ssh -p 2222" \
  admin@brain:/mnt/studio/exports/ ~/studio-exports/
```

**Option 3: SSHFS mount**
```bash
# From your laptop, mount compute brain exports:
mkdir -p ~/studio-exports
sshfs -p 2222 admin@brain:/mnt/studio/exports ~/studio-exports
```

---

## CLI Tools Reference

### studio-status
```bash
studio-status              # Quick overview: containers, storage, GPU
```

### studio-model
```bash
studio-model list [--type text|image|video|audio] [--installed]
studio-model search <query>
studio-model info <model-id>
studio-model pull <model-id>
studio-model remove <model-id>
studio-model status
studio-model recommend --use-case <use-case>
studio-model recommend --hardware
studio-model backup
studio-model --json
```

### studio-doctor
```bash
studio-doctor              # Full diagnostic
studio-doctor health       # Quick health check
studio-doctor models       # Browse models
studio-doctor backends     # Backend status
studio-doctor optimize     # Optimization tips
studio-doctor validate     # Run test suite
studio-doctor cleanup      # Free disk space
studio-doctor backup       # Backup configs
studio-doctor report       # Full system report
studio-doctor --dry-run
studio-doctor --json
studio-doctor --offline
```

### studio-update
```bash
studio-update check        # What can be updated
studio-update pull         # Pull latest Docker images
studio-update scripts      # Update scripts
studio-update dashboard    # Rebuild dashboard
studio-update all          # Update everything
studio-update rollback     # Revert to previous
studio-update --dry-run
studio-update --offline
```

### studio-test
```bash
bash tests/run-all.sh                # All tests
bash tests/run-all.sh --verbose      # Show details
bash tests/run-all.sh --dry-run      # Preview
bash tests/run-all.sh test_security.sh  # One module
```

### Other
```bash
install-components.sh --check-only     # Check installed packages
install-components.sh --install-missing
install-components.sh --update-all
resource-monitor.sh --once             # Single resource check
resource-monitor.sh --watch            # Continuous monitoring
```

---

## Updating the System

### Docker Images

```bash
# Check for updates
studio-update check

# Pull latest images
studio-update pull

# Restart with new images
cd /opt/ai-studio && docker compose down && docker compose up -d
```

### Scripts

```bash
# Update scripts from repo
studio-update scripts

# Or manually
cp new-script.sh /usr/local/bin/
chmod +x /usr/local/bin/new-script.sh
```

### InvokeAI

```bash
# Pull latest InvokeAI image
docker pull ghcr.io/invoke-ai/invokeai:latest

# Restart
cd /opt/ai-studio && docker compose up -d invokeai
```

### Rollback

```bash
# If update breaks something
studio-update rollback
```

---

## Adding New Models

### Text Models (GGUF)

```bash
# Download from HuggingFace
studio-model pull llama-3.1-8b

# Or manually:
wget -O /mnt/studio/models/text/llama-3.1-8b/model.gguf \
  "https://huggingface.co/bartowski/Llama-3.1-8B-Instruct-GGUF/resolve/main/Llama-3.1-8B-Instruct-Q4_K_M.gguf"

# Update llama.cpp to use it
# Edit docker-compose.yaml command: --model /models/llama-3.1-8b/model.gguf
# Then: docker compose restart llamacpp
```

### Image Models

For InvokeAI: Settings -> Models -> Import Model -> Enter URL
Or place files in `/mnt/studio/invokeai/models/`

For ComfyUI: Place safetensors in `/mnt/studio/models/image/`

### Video Models

Place in `/mnt/studio/models/video/`
ComfyUI and InvokeAI auto-detect at startup.

---

## Adding New Services

### 1. Add to docker-compose.yaml

```yaml
services:
  your-service:
    image: your-image:latest
    container_name: studio-your-service
    restart: unless-stopped
    ports:
      - "127.0.0.1:YOUR_PORT:YOUR_PORT"
    volumes:
      - /mnt/studio/your-data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:YOUR_PORT/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 2. Add port to firewall (optional)

```bash
sudo ufw allow from 127.0.0.1 to any port YOUR_PORT
```

### 3. Add SSH tunnel for laptop access

```bash
ssh -p 2222 -L YOUR_PORT:127.0.0.1:YOUR_PORT admin@brain
```

### 4. Add backend adapter (if AI service)

Create `app/dashboard/backends/yourservice.py` following the pattern.

### 5. Add health check to tests

Add to `tests/test_backends.sh`:
```bash
if ss -tlnp 2>/dev/null | grep -q ':YOUR_PORT '; then
  run "Your service health" "curl -sf --max-time 5 http://127.0.0.1:YOUR_PORT/health" 8
else
  skip "Your service health" "port YOUR_PORT not listening"
fi
```

---

## Troubleshooting

```bash
# Nothing works?
studio-doctor health

# Services not starting?
cd /opt/ai-studio && docker compose logs --tail 50

# Specific service failing?
docker compose logs -f studio-invokeai

# Model won't load?
studio-model status         # Check VRAM
studio-doctor optimize      # See what to fix

# Dashboard unreachable?
ssh -p 2222 -L 5000:127.0.0.1:5000 admin@<ip>

# InvokeAI unreachable?
ssh -p 2222 -L 9090:127.0.0.1:9090 admin@<ip>

# Out of disk?
studio-doctor cleanup
df -h /mnt/studio

# GPU not detected?
nvidia-smi
studio-doctor health

# Full system report?
studio-doctor report

# Rollback after bad update?
studio-update rollback

# Run full validation?
bash tests/run-all.sh --verbose

# Container won't start?
docker compose rm -f <service>
docker compose up -d <service>

# Port conflict?
ss -tlnp | grep <port>
docker compose down && docker compose up -d
```

---

## Testing

136 tests across 6 modules. Every test has timeout and graceful skip.

```bash
bash tests/run-all.sh                    # All tests
bash tests/run-all.sh --verbose          # Details
bash tests/run-all.sh --dry-run          # Preview
bash tests/run-all.sh --timeout 30       # Override timeout
bash tests/run-all.sh test_security.sh   # One module
```

| Module | Tests | What |
|--------|-------|------|
| `test_infrastructure.sh` | 35 | Docker, containers, ports, storage, GPU, configs |
| `test_security.sh` | 17 | SSH, firewall, user isolation, container security |
| `test_backends.sh` | 17 | Backend health, API responses, network |
| `test_models.sh` | 15 | Catalog, model files, metadata, VRAM |
| `test_api.sh` | 18 | Dashboard endpoints, validation, response times |
| `test_workspace.sh` | 30 | Frontend modes, UI elements, templates |

---

## Hardware Guide

| Tier | RAM | GPU | What runs |
|------|-----|-----|-----------|
| **High** | 64GB+ | 24GB+ VRAM | Full stack: 70B text, Flux, CogVideoX, all audio |
| **Mid** | 32GB | 12-24GB | 27B text, SDXL, SVD, all audio |
| **Low** | 16GB | 8-12GB | 8B text, SDXL (limited), audio |
| **Minimal** | 8GB | CPU only | 8B text, Whisper, Kokoro |

**Requirements:**
- Compute brain: 8+ cores, 16GB+ RAM, 50GB root disk, 512GB+ external SSD
- Client laptop: SSH + browser. No GPU needed.
- Cost: $0/month. No API keys.

---

## Project Structure

```
ai-creative-studio/
├── README.md
├── config/
│   └── backends.json                    Backend selection
├── docs/
│   ├── ARCHITECTURE.md                  System topology
│   ├── DOCKER-ISOLATION.md              Docker reference
│   ├── INVOKEAI.md                      InvokeAI integration guide
│   ├── MODEL-MANAGER.md                 Model lifecycle
│   ├── NETWORK-ACCESS.md                SSH, tunnels, firewall
│   ├── STORAGE-DESIGN.md                Storage layout
│   ├── TESTING.md                       Test suite docs
│   └── USER-MANAGEMENT.md               Dual-user setup
├── docker/
│   └── docker-compose.yaml              9 services
├── scripts/
│   ├── setup-master.sh                  One-shot setup (895 lines)
│   ├── setup-users.sh                   Creator/Admin accounts
│   ├── install-components.sh            System packages
│   ├── studio-doctor.sh                 Diagnostics
│   ├── studio-update.sh                 Update manager
│   ├── resource-monitor.sh              CPU/RAM/GPU monitor
│   ├── keep-alive.sh                    Drive heartbeat
│   ├── install-services.sh              systemd installer
│   ├── resource-monitor.service
│   ├── keep-alive.service
│   ├── setup.sh                         Legacy setup
│   └── README.md                        Script docs
├── app/
│   ├── dashboard/
│   │   ├── app.py                       Flask routes
│   │   ├── backends/
│   │   │   ├── registry.py              Backend dispatch
│   │   │   ├── text.py                  llama-cpp, ollama, vllm, openai
│   │   │   ├── image.py                 comfyui, automatic1111
│   │   │   ├── video.py                 comfyui-video, animatediff
│   │   │   ├── tts.py                   kokoro, coqui, bark
│   │   │   ├── stt.py                   whisper, faster-whisper
│   │   │   └── music.py                 audiocraft, stable-audio, ace-step
│   │   ├── model_catalog.py             10 models with download URLs
│   │   ├── templates/
│   │   │   ├── workspace.html           Main generation UI
│   │   │   ├── index.html               Dashboard overview
│   │   │   ├── models.html              Model browser
│   │   │   ├── settings.html            Settings page
│   │   │   ├── projects.html            Projects page
│   │   │   └── workflows.html           Workflow templates
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── model-manager/
│       └── cli.py                       studio-model CLI
└── tests/
    ├── run-all.sh                       Master test runner
    ├── README.md                        Test docs
    ├── test_infrastructure.sh           35 tests
    ├── test_security.sh                 17 tests
    ├── test_backends.sh                 17 tests
    ├── test_models.sh                   15 tests
    ├── test_api.sh                      18 tests
    └── test_workspace.sh                30 tests
```

---

*Your compute brain. Your models. Your dashboard. No cloud tax.*

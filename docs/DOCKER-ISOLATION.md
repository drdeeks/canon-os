# AI Creative Studio — Docker Isolation Architecture

This document describes the containerized architecture for the AI Creative Studio.
Every tool runs in its own container. Containers are isolated from each other except
through explicit network links. The host's external storage at `/mnt/studio` is
bind-mounted into every container that needs it. GPU access is passed through via
Docker device passthrough (CUDA or Metal depending on host).

---

## Table of Contents

1. [Overview](#overview)
2. [Directory Layout](#directory-layout)
3. [Network Configuration](#network-configuration)
4. [Volume Mounts](#volume-mounts)
5. [Security Hardening](#security-hardening)
6. [GPU Passthrough](#gpu-passthrough)
7. [Full docker-compose.yaml](#full-docker-composeyaml)
8. [Service Definitions](#service-definitions)
9. [Resource Limits](#resource-limits)
10. [Health Checks](#health-checks)
11. [Restart Policies](#restart-policies)
12. [Accessing Services](#accessing-services)
13. [Managing the Stack](#managing-the-stack)
14. [Troubleshooting](#troubleshooting)

---

## Overview

```
Host
 +-- studio-network (bridge, 172.28.0.0/16)
 |     +-- studio-ollama      (LLM inference, port 11434)
 |     +-- studio-llamacpp    (GGUF serving, port 8080)
 |     +-- studio-comfyui     (Stable Diffusion UI, port 8188)
 |     +-- studio-openwebui   (Chat frontend, port 3000)
 |     +-- studio-dashboard   (Creator dashboard, port 5000)
 |     +-- studio-whisper     (Speech-to-text, port 9000)
 |     +-- studio-kokoro      (Text-to-speech, port 8880)
 |     +-- studio-audiocraft  (Music generation, port 8890)
 +-- /mnt/studio              (external drive, bind-mounted into containers)
```

Each container:
- Runs as non-root user `studio` (uid 1000).
- Has a read-only root filesystem where possible.
- Never runs with `--privileged`.
- Shares only the `studio-network` bridge.

---

## Directory Layout

```
~/ai-creative-studio/
├── docker-compose.yaml
├── docs/
│   └── DOCKER-ISOLATION.md       <-- this file
├── config/
│   ├── ollama/
│   ├── comfyui/
│   ├── open-webui/
│   ├── whisper/
│   ├── kokoro/
│   └── audiocraft/
└── scripts/
    └── manage.sh
```

Create the layout:

```bash
mkdir -p ~/ai-creative-studio/{config/{ollama,comfyui,open-webui,whisper,kokoro,audiocraft},scripts,docs}
```

---

## Network Configuration

All containers join a single user-defined bridge network called `studio-network`.
This gives them automatic DNS resolution by container name (e.g. `http://ollama:11434`).
No ports are published to the host except those explicitly listed below.

```yaml
networks:
  studio-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
    driver_opts:
      com.docker.network.bridge.name: br-studio
```

If you need to reach a service from another machine on your LAN, use SSH tunneling to
the HOST (not the container). Example:

```bash
# From a remote machine
ssh -L 3000:localhost:3000 user@host-ip
# Then open http://localhost:3000 in your browser
```

---

## Volume Mounts

Every service that works with generated files receives a bind mount of paths under `/mnt/studio`.
Volume mounts are per-service and specific to each container's needs:

| Service | Host Path | Container Path | Access |
|---|---|---|---|
| ollama | `/mnt/studio/models/text` | `/models` | read-only |
| llama-cpp | `/mnt/studio/models/text` | `/models` | read-only |
| comfyui | `/mnt/studio/models/image` | `/app/ComfyUI/models` | read-only |
| comfyui | `/mnt/studio/models/video` | `/app/ComfyUI/models/video` | read-only |
| comfyui | `/mnt/studio/exports` | `/app/ComfyUI/output` | read-write |
| comfyui | `/mnt/studio/uploads` | `/app/ComfyUI/input` | read-write |
| open-webui | `/mnt/studio/uploads` | `/app/backend/uploads` | read-write |
| open-webui | `/mnt/studio/exports` | `/app/backend/exports` | read-write |
| whisper | `/mnt/studio/models/audio/whisper` | `/models` | read-only |
| whisper | `/mnt/studio/uploads` | `/uploads` | read-write |
| whisper | `/mnt/studio/exports` | `/exports` | read-write |
| kokoro | `/mnt/studio/models/audio/kokoro` | `/models` | read-only |
| kokoro | `/mnt/studio/exports` | `/exports` | read-write |
| audiocraft | `/mnt/studio/models/audio/musicgen` | `/root/.cache/torch` | read-only |
| audiocraft | `/mnt/studio/exports` | `/exports` | read-write |
| dashboard | `/home/creator/ai-studio` | `/home/creator/ai-studio` | read-write |
| dashboard | `/mnt/studio` | `/mnt/studio` | read-write |

Create host directories:

```bash
sudo mkdir -p /mnt/studio/{models/{text,image,video,audio/{whisper,kokoro,musicgen}},exports,uploads,cache}
sudo chown -R 1000:1000 /mnt/studio
```

---

## Security Hardening

Every container applies these security options:

```yaml
    # Applied to every service:
    user: "1000:1000"          # Run as non-root uid 1000
    read_only: true            # Read-only root filesystem
    security_opt:
      - no-new-privileges:true # Prevent privilege escalation
    cap_drop:
      - ALL                    # Drop all Linux capabilities
    # tmpfs for writable paths the app needs
    tmpfs:
      - /tmp:size=512M
```

- `read_only: true` prevents any writes to the container's rootfs. Writable directories
  are provided via `tmpfs` or volume mounts.
- `no-new-privileges:true` stops processes from gaining additional privileges (e.g. via
  setuid binaries).
- `cap_drop: ALL` removes every Linux capability. Services that need specific caps can
  re-add them with `cap_add`.
- No container uses `privileged: true` or `ipc: host`.

---

## GPU Passthrough

### NVIDIA (CUDA) — Linux Host

Install the NVIDIA Container Toolkit on the host:

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

In docker-compose.yaml, services that need GPU access add:

```yaml
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all        # or "1" to limit to one GPU
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
```

### Apple Silicon (Metal) — macOS Host

Docker Desktop on macOS does not support direct GPU passthrough. Options:
1. Run services natively (recommended for Metal).
2. Use a Linux VM with PCIe passthrough (advanced).
3. Use CPU-only mode inside Docker (slow).

For CPU-only fallback, remove the `deploy.resources.reservations` block and set:

```yaml
    environment:
      - OLLAMA_LLM_LIBRARY=cpu
```

### Verifying GPU Access

```bash
# Inside a running container (NVIDIA)
docker exec -it ollama nvidia-smi

# On host
docker exec ollama ollama list
```

---

## Full docker-compose.yaml

Save this as `~/ai-creative-studio/docker-compose.yaml`. It is copy-paste ready.

```yaml
version: "3.9"

# ---------------------------------------------------------------------------
# Networks
# ---------------------------------------------------------------------------
networks:
  studio-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
    driver_opts:
      com.docker.network.bridge.name: br-studio

# ---------------------------------------------------------------------------
# Volumes (named volumes for container-specific data)
# ---------------------------------------------------------------------------
volumes:
  ollama-data:
  comfyui-workflows:
  open-webui-data:
  kokoro-app:
  dashboard-tmp:

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
services:

  # =========================================================================
  # Ollama — Local LLM inference
  # =========================================================================
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    restart: unless-stopped
    user: "1000:1000"
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:size=512M
    networks:
      - studio-network
    ports:
      - "127.0.0.1:11434:11434"
    volumes:
      - ollama-data:/root/.ollama
      - /mnt/studio/models:/models:ro
      - /mnt/studio/outputs:/outputs
    environment:
      - OLLAMA_HOST=0.0.0.0
      - OLLAMA_MODELS=/models/ollama
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
    deploy:
      resources:
        limits:
          cpus: "8"
          memory: 16G
        reservations:
          memory: 4G
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # =========================================================================
  # llama.cpp — Alternative/complementary LLM server (optional)
  # =========================================================================
  llama-cpp:
    image: ghcr.io/ggerganov/llama.cpp:server
    container_name: llama-cpp
    restart: unless-stopped
    user: "1000:1000"
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:size=256M
    networks:
      - studio-network
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - /mnt/studio/models:/models:ro
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
    command:
      - "--model"
      - "/models/llama/gguf/model.gguf"
      - "--host"
      - "0.0.0.0"
      - "--port"
      - "8080"
      - "--ctx-size"
      - "4096"
    deploy:
      resources:
        limits:
          cpus: "8"
          memory: 16G
        reservations:
          memory: 4G
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 90s

  # =========================================================================
  # ComfyUI — Stable Diffusion image generation
  # =========================================================================
  comfyui:
    image: ghcr.io/comfyanonymous/comfyui:latest
    container_name: comfyui
    restart: unless-stopped
    user: "1000:1000"
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:size=2G
    networks:
      - studio-network
    ports:
      - "127.0.0.1:8188:8188"
    volumes:
      - /mnt/studio/models:/models:ro
      - /mnt/studio/outputs:/outputs
      - /mnt/studio/uploads:/uploads
      - /mnt/studio/cache:/cache
      - ./config/comfyui:/config:ro
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
      - COMFYUI_OUTPUT_DIR=/outputs/images
    deploy:
      resources:
        limits:
          cpus: "6"
          memory: 12G
        reservations:
          memory: 4G
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8188/system_stats"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s

  # =========================================================================
  # Open WebUI — Chat frontend for Ollama
  # =========================================================================
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    restart: unless-stopped
    user: "1000:1000"
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:size=256M
    networks:
      - studio-network
    ports:
      - "127.0.0.1:3000:8080"
    volumes:
      - openwebui-data:/app/backend/data
      - /mnt/studio/uploads:/uploads
      - ./config/open-webui:/config:ro
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - WEBUI_NAME=AI Creative Studio
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 4G
        reservations:
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  # =========================================================================
  # Whisper — Speech-to-text transcription
  # =========================================================================
  whisper:
    image: onerahmet/openai-whisper-asr-webservice:latest
    container_name: whisper
    restart: unless-stopped
    user: "1000:1000"
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:size=1G
    networks:
      - studio-network
    ports:
      - "127.0.0.1:9000:9000"
    volumes:
      - /mnt/studio/models:/models:ro
      - /mnt/studio/uploads:/uploads
      - /mnt/studio/outputs:/outputs
      - whisper-data:/app/data
    environment:
      - ASR_MODEL=large-v3
      - ASR_ENGINE=openai_whisper
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
    deploy:
      resources:
        limits:
          cpus: "4"
          memory: 8G
        reservations:
          memory: 2G
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/docs"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s

  # =========================================================================
  # Kokoro — Text-to-speech synthesis
  # =========================================================================
  kokoro:
    image: ghcr.io/remsky/kokoro-fastapi:latest
    container_name: kokoro
    restart: unless-stopped
    user: "1000:1000"
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:size=512M
    networks:
      - studio-network
    ports:
      - "127.0.0.1:8880:8880"
    volumes:
      - /mnt/studio/models:/models:ro
      - /mnt/studio/outputs:/outputs
      - kokoro-data:/app/data
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
    deploy:
      resources:
        limits:
          cpus: "4"
          memory: 8G
        reservations:
          memory: 2G
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8880/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # =========================================================================
  # AudioCraft — Music and audio generation (MusicGen / AudioGen)
  # =========================================================================
  audiocraft:
    image: ghcr.io/facebookresearch/audiocraft:latest
    container_name: studio-audiocraft
    restart: unless-stopped
    user: "1000:1000"
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:size=2G
    networks:
      - studio-network
    ports:
      - "127.0.0.1:8890:8890"
    volumes:
      - /mnt/studio/models/audio/musicgen:/root/.cache/torch:ro
      - /mnt/studio/exports:/exports
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
      - GRADIO_SERVER_NAME=0.0.0.0
      - GRADIO_SERVER_PORT=8890
    deploy:
      resources:
        limits:
          memory: 16G
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8890/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s
```

---

## Service Definitions

### Ollama (Port 11434)

- Image: `ollama/ollama:latest`
- Container: `studio-ollama`
- Purpose: Runs quantized LLMs (Llama, Mistral, Qwen, etc.) via a local API.
- Depends on: GPU for acceptable speed.
- Internal API: `http://studio-ollama:11434` (available to other containers).
- Pull a model after first start:

```bash
docker exec studio-ollama ollama pull llama3.1:8b
```

### llama.cpp (Port 8080)

- Image: `ghcr.io/ggerganov/llama.cpp:server`
- Container: `studio-llamacpp`
- Purpose: Lightweight GGUF model server; alternative to Ollama.
- Place your `.gguf` model at `/mnt/studio/models/text/`.
- Comment out this service if you only use Ollama.

### ComfyUI (Port 8188)

- Image: `ghcr.io/ai-dock/comfyui:latest-cuda`
- Container: `studio-comfyui`
- Purpose: Node-based UI for Stable Diffusion image generation workflows.
- Models expected at `/mnt/studio/models/image/`.
- Outputs written to `/mnt/studio/exports/`.

### Open WebUI (Port 3000)

- Image: `ghcr.io/open-webui/open-webui:main`
- Container: `studio-openwebui`
- Purpose: ChatGPT-like web interface for Ollama.
- Connects to Ollama at `http://studio-ollama:11434` via container DNS.
- This is the main user-facing interface — typically the only port you expose.

### Dashboard (Port 5000)

- Build: from `app/dashboard/Dockerfile`
- Container: `studio-dashboard`
- Purpose: Creator-facing unified dashboard for all AI tools.

### Whisper (Port 9000)

- Image: `ghcr.io/drhino/whisper-cpp-api:latest`
- Container: `studio-whisper`
- Purpose: Speech-to-text transcription via a REST API.
- Default model: `large-v3` (must be placed at `/mnt/studio/models/audio/whisper/`).
- API endpoint: `http://localhost:9000/health`

### Kokoro (Port 8880)

- Image: `python:3.11-slim`
- Container: `studio-kokoro`
- Purpose: Fast text-to-speech synthesis (ONNX runtime).
- API endpoint: `http://localhost:8880/health`

### AudioCraft (Port 8890)

- Image: `ghcr.io/facebookresearch/audiocraft:latest`
- Container: `studio-audiocraft`
- Purpose: Music and sound-effect generation (MusicGen, AudioGen).
- Web UI exposed on container port 8890, mapped to host port 8890.

---

## Resource Limits

| Service | Memory Limit | GPU |
|---|---|---|
| ollama | 48 GB | All |
| llama-cpp | 48 GB | All |
| comfyui | 32 GB | All |
| open-webui | — | None |
| whisper | 8 GB | All |
| kokoro | — | None |
| audiocraft | 16 GB | All |
| dashboard | — | None |

Adjust these values to match your hardware. On a machine with 64 GB RAM and one GPU,
the defaults above will work. On smaller machines, reduce CPU and memory limits.

---

## Health Checks

Every service has a health check that verifies the HTTP endpoint is reachable.
Docker will mark the container as `unhealthy` after 3 consecutive failures.
The `start_period` gives services time to load models before health is evaluated.

| Service | Check Command | Interval | Start Period |
|---|---|---|---|
| ollama | `curl -f http://localhost:11434/api/tags` | 30s | 30s |
| llama-cpp | `curl -f http://localhost:8080/health` | 30s | 60s |
| comfyui | `curl -f http://localhost:8188/` | 30s | 60s |
| open-webui | `curl -f http://localhost:8080/health` | 30s | 30s |
| whisper | `curl -f http://localhost:9000/health` | 30s | 30s |
| kokoro | `curl -f http://localhost:8880/health` | 30s | 60s |
| audiocraft | `curl -f http://localhost:8890/` | 30s | 120s |
| dashboard | `curl -f http://localhost:5000/` | 30s | 15s |

---

## Restart Policies

All services use `restart: unless-stopped`:
- Containers restart automatically if they crash or the host reboots.
- Containers do NOT restart if you explicitly run `docker compose stop`.

To change behavior per service, edit the `restart:` field. Options:
- `no` — never restart
- `always` — always restart (even after manual stop)
- `on-failure` — restart only on non-zero exit code
- `unless-stopped` — restart unless manually stopped (recommended)

---

## Accessing Services

All ports are bound to `127.0.0.1`, so they are only accessible from the host itself.
To reach them remotely, use SSH port forwarding:

```bash
# Forward Open WebUI
ssh -L 3000:localhost:3000 user@host-ip

# Forward ComfyUI
ssh -L 8188:localhost:8188 user@host-ip

# Forward all at once
ssh -L 3000:localhost:3000 -L 8188:localhost:8188 -L 9000:localhost:9000 \
    -L 8880:localhost:8880 -L 8890:localhost:8890 -L 11434:localhost:11434 \
    -L 5000:localhost:5000 -L 8080:localhost:8080 \
    user@host-ip
```

If you need to expose a port on all interfaces (e.g., for a LAN-only setup), change
`127.0.0.1:3000:8080` to `0.0.0.0:3000:8080`. Use a firewall to restrict access.

---

## Managing the Stack

```bash
# Start all services
cd ~/ai-creative-studio
docker compose up -d

# View logs
docker compose logs -f

# View logs for one service
docker compose logs -f ollama

# Stop all services
docker compose stop

# Stop and remove containers (keeps volumes)
docker compose down

# Stop and remove everything including volumes (DESTRUCTIVE)
docker compose down -v

# Restart a single service
docker compose restart comfyui

# Check status
docker compose ps

# Shell into a container (for debugging)
docker exec -it ollama /bin/bash
```

---

## Troubleshooting

### GPU not detected inside container

```bash
# Verify nvidia-container-toolkit is installed
nvidia-ctk --version

# Verify Docker runtime is configured
docker info | grep -i runtime

# Test GPU passthrough
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

### Permission denied on /mnt/studio

```bash
# Ensure uid 1000 owns the directories
sudo chown -R 1000:1000 /mnt/studio
sudo chmod -R 755 /mnt/studio
```

### Container exits immediately with read_only: true

The application may need a writable directory that is not covered by the existing
`tmpfs` or volume mounts. Check the logs:

```bash
docker compose logs <service-name>
```

Add a `tmpfs` mount or a volume for the missing path.

### Health check failing but service works

Increase the `start_period` or `timeout` in the health check definition. Model
loading can take several minutes on first start.

---

## References

- [Docker Compose file reference](https://docs.docker.com/compose/compose-file/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/)
- [Ollama Docker](https://hub.docker.com/r/ollama/ollama)
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- [Open WebUI](https://github.com/open-webui/open-webui)
- [Whisper ASR Webservice](https://github.com/ahmetoner/whisper-asr-webservice)
- [Kokoro FastAPI](https://github.com/remsky/Kokoro-FastAPI)
- [AudioCraft](https://github.com/facebookresearch/audiocraft)

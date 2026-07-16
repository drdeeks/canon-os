============================================================================
                    AI CREATIVE STUDIO - ARCHITECTURE
                      Enterprise Local-Only Stack
============================================================================

OVERVIEW
--------
A fully self-hosted, local-only AI creative studio designed for video
editing and content creation professionals. Zero cloud dependency, zero
API costs, zero data leakage. Everything runs on your hardware under
your control.

The core principle: ONE powerful "compute brain" runs all inference.
Access it from ANY device via SSH + browser. All creative output lives
on external storage, never on the compute brain's root partition.


SYSTEM TOPOLOGY
---------------

  [Low-End Laptop]                     [Compute Brain]
       |                                    |
       |--- SSH (port 2222) -------------->|  Shell access +
       |--- SSH Tunnel (ports) ----------->|  Web UI forwarding
       |--- rsync/scp ------------------->|  File transfer
       |                                    |
       |                              [Docker Containers]
       |                              |-- ollama (text AI)
       |                              |-- llama-cpp (GGUF serving)
       |                              |-- comfyui (image/video gen)
       |                              |-- open-webui (chat frontend)
       |                              |-- invokeai (creative UI - primary)
       |                              |-- dashboard (text/audio companion)
       |                              |-- whisper (transcription)
       |                              |-- kokoro (TTS voiceover)
       |                              |-- audiocraft (music gen)
       |                                    |
       |                              [External Storage]
  [Browser:9090] <--tunnel-->          /mnt/studio/
  [Browser:5000] <--tunnel-->          |-- models/
  [Browser:3000] <--tunnel-->          |-- projects/
  [Browser:8188] <--tunnel-->          |-- exports/
                                    |-- cache/
                                     |-- cache/

Key design decisions:
- Compute brain NEVER stores creative work permanently
- External storage is the single source of truth for all content
- Laptop needs ONLY: SSH client + web browser (no GPU required)
- All web UIs accessed via SSH port forwarding (never exposed to internet)


MODEL INVENTORY
---------------
Tier 1 -- TEXT AI (Ollama + llama.cpp)
  Model                    Size    VRAM    Use Case
  ──────────────────────── ─────── ─────── ──────────────────────
  Llama 3.1 70B            ~40GB   ~42GB   Scripts, ad copy,
                                            taglines, brainstorming
  Llama 3.1 8B             ~4.7GB  ~6GB    Quick drafts, helpers,
                                            subtitles cleanup
  Mistral 7B               ~4.1GB  ~5GB    Fast general-purpose tasks
  CodeLlama 13B            ~7.4GB  ~9GB    Code generation, editing
  Qwen 2.5 7B              ~4.4GB  ~5GB    Multilingual content

Tier 2 -- IMAGE AI (ComfyUI + PyTorch)
  Model                    Size    VRAM    Use Case
  ──────────────────────── ─────── ─────── ──────────────────────
  Flux.1 Dev               ~24GB   ~26GB   Product shots, static ads
  Flux.1 Schnell           ~24GB   ~26GB   Fast image generation
  SDXL 1.0                 ~6.5GB  ~8GB    Consistent brand imagery
  SDXL Turbo               ~6.5GB  ~8GB    Fast image generation
  RealVisXL V4.0           ~6.5GB  ~8GB    Photorealistic images
  Juggernaut XL V9         ~6.5GB  ~8GB    Versatile multi-style

Tier 3 -- VIDEO AI
  Model                    Size    VRAM    Use Case
  ──────────────────────── ─────── ─────── ──────────────────────
  CogVideoX 5B             ~12GB   ~16GB   Short clips from text/image
  Stable Video Diffusion XT ~10GB  ~12GB   Image-to-video
  Wan 2.1 1.3B             ~3GB    ~4GB    Lightweight text-to-video

Tier 4 -- AUDIO AI
  Model                    Size    VRAM    Use Case
  ──────────────────────── ─────── ─────── ──────────────────────
  Kokoro TTS (ONNX)        ~300MB  ~1GB    Voiceovers, multiple voices
  Whisper Large-v3         ~3GB    ~4GB    Transcription, subtitles
  AudioCraft / MusicGen    ~3.5GB  ~6GB    Background music beds


Total minimum storage:  ~70GB (core text + image stack)
Total full stack:       ~130GB (everything including video models)
Recommended:            500GB+ external SSD for models + project storage


FRONTEND STACK
--------------
  Application      Port    Purpose
  ──────────────── ─────── ──────────────────────────────────────
  InvokeAI         9090    Primary creative interface (image/video)
  Dashboard        5000    Text/audio companion interface
  Open WebUI       3000    ChatGPT-style interface for text AI
  ComfyUI          8188    Node-based visual workflow for image/video
  Whisper Web      9000    Transcription interface
  AudioCraft       8890    Music generation interface


PRODUCTION PIPELINES
--------------------

30-Second Product Commercial (all local, no API costs)
─────────────────────────────────────────────────────
  Step               Tool              Time      Output
  ────────────────── ───────────────── ───────── ──────────────────
  1. Script writing  Llama 3.1 70B     ~2 min    Full narration script
  2. Storyboard (8)  Flux.1 Dev        ~4 min    8 frame images
  3. Video clips (4) CogVideoX-5B      ~80 min   4x 5-second clips
  4. Voiceover       Kokoro TTS        ~1 min    Full narration audio
  5. Music bed       MusicGen          ~2 min    Background music track
  6. Subtitles       Whisper.cpp       ~30 sec   SRT subtitle file
  ──────────────────────────────────────────────────────────────────
  AI Generation Total:                  ~90 min
  Assembly (DaVinci Resolve):           30-60 min
  ──────────────────────────────────────────────────────────────────
  Grand Total:                          ~2-2.5 hours for a full commercial


Thumbnail/Static Ad Workflow
────────────────────────────
  1. Prompt (Llama 70B generates detailed image prompts)
  2. Generate (SDXL or Flux.1, ~8-30 sec per image)
  3. Upscale (Real-ESRGAN 4x)
  4. Export (ComfyUI auto-saves to /mnt/studio/exports/)


Voiceover-Only Workflow
──────────────────────
  1. Script in Open WebUI
  2. Send to Kokoro TTS via API
  3. WAV output to /mnt/studio/exports/


Transcription Workflow
─────────────────────
  1. Drop video/audio in /mnt/studio/uploads/
  2. Whisper processes (faster than realtime)
  3. SRT/VTT output to /mnt/studio/exports/


DOCKER ISOLATION PRINCIPLES
----------------------------
- Every AI tool runs in its own container
- Containers share a private bridge network (studio-network)
- External storage bind-mounted at /mnt/studio (read-write)
- Container rootfs is read-only where possible
- No container runs as root (UID 1000 mapping)
- All capabilities dropped (cap_drop: ALL)
- No privileged mode ever
- GPU access via device reservation only (not privileged)
- Host SSH is the ONLY external access point
- Container ports bound to 127.0.0.1 only (never 0.0.0.0)


SECURITY MODEL
--------------
  Layer               Mechanism
  ─────────────────── ──────────────────────────────────────
  Network perimeter   Firewall (ufw) - only SSH exposed
  Authentication      Ed25519 SSH keys only, no passwords
  Brute force         fail2ban with progressive bans
  Container escape    Read-only rootfs, dropped caps, non-root
  Data isolation      External storage, never on host root
  Access control      SSH config with per-host restrictions
  Web UI access       SSH tunnel only (never direct exposed)


HARDWARE REQUIREMENTS
---------------------
  Component          Minimum            Recommended
  ────────────────── ────────────────── ──────────────────
  Compute Brain
    CPU              8-core x86/ARM     Apple M4 Pro/Max
    RAM              16GB               64GB+ (unified)
    GPU              Any Metal/CUDA     24GB+ VRAM
    Storage (host)   50GB free          100GB+ (OS + Docker only)
    External SSD     256GB              1TB+ NVMe USB-C/TB

  Client (Laptop)
    CPU              Dual-core          Anything with SSH
    RAM              4GB                8GB
    Storage          10GB free          Enough for active project
    Network          WiFi               Gigabit LAN preferred
    OS               Any with SSH       Linux/macOS/Windows+WSL


DIRECTORY STRUCTURE ON EXTERNAL STORAGE
----------------------------------------
/mnt/studio/
  |-- models/
  |   |-- text/
  |   |   |-- llama-3.1-70b-instruct-Q4_K_M.gguf
  |   |   |-- llama-3.1-8b-instruct-Q4_K_M.gguf
  |   |   |-- mistral-7b-instruct.gguf
  |   |   |-- codellama-13b-instruct.gguf
  |   |-- image/
  |   |   |-- flux1-dev/
  |   |   |-- flux1-schnell/
  |   |   |-- sdxl-base/
  |   |   |-- sdxl-turbo/
  |   |   |-- realvisxl-v4/
  |   |   |-- juggernautxl-v9/
  |   |-- video/
  |   |   |-- cogvideox-5b/
  |   |   |-- svd-xt/
  |   |   |-- wan2.1-1.3b/
  |   |-- audio/
  |       |-- kokoro/
  |       |-- musicgen/
  |       |-- whisper/
  |-- projects/
  |   |-- <project-name>/
  |       |-- scripts/
  |       |-- storyboards/
  |       |-- video-clips/
  |       |-- audio/
  |       |-- final/
  |-- exports/
  |-- uploads/
  |-- cache/
  |-- logs/


DAILY WORKFLOW
--------------
  1. Open laptop
  2. SSH into compute brain: ssh studio
  3. Start tunnels: studio-tunnel (script provided)
  4. Open browser tabs:
     - http://localhost:9090   (InvokeAI - image/video primary)
     - http://localhost:5000   (Dashboard - text/audio companion)
     - http://localhost:3000   (Open WebUI - text AI chat)
     - http://localhost:8188   (ComfyUI - advanced workflows)
  5. Work. Everything saves to /mnt/studio/
  6. When done, sync exports to laptop: studio-sync
  7. Close SSH

No file lives on the compute brain. Your laptop is your workspace.
The compute brain is just a remote GPU you access through SSH.


============================================================================

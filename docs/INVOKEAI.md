============================================================================
                 AI CREATIVE STUDIO - INVOKEAI INTEGRATION
============================================================================

WHY INVOKEAI
------------
InvokeAI replaces the custom Flask dashboard with a production-grade,
Leonardo AI-style creative interface. It provides:

  - Unified canvas (draw, paint, composite)
  - Inpainting (select area, regenerate)
  - Outpainting (extend image borders)
  - Batch generation (up to 16+ images from one prompt)
  - Style presets and reference images
  - Drag-and-drop asset management
  - Gallery with search and organization
  - ControlNet support
  - Model management UI
  - REST API for automation

It's self-hosted, Docker-ready, open-source (Apache 2.0), and has
an active community of 25k+ GitHub stars.


FEATURE MAPPING
---------------
Our needs mapped to InvokeAI features:

  Need                    InvokeAI Feature
  ----------------------  ----------------------------------------
  Text to Image           Generation tab -> txt2img
  Image Edit              Unified Canvas -> img2img
  Inpaint                 Unified Canvas -> inpainting brush
  Background removal      Canvas -> remove background node
  Batch (16 images)       Generation -> batch count slider
  Image sizing            Generation -> width/height sliders
  Style references        Generation -> style preset + ref image
  Quality traits          Generation -> guidance/scheduler/steps
  Strength control        img2img -> denoising strength slider
  Drag and drop           Gallery + Canvas drag support
  Workflow templates      Workflows tab (pre-built + custom)
  Video (future)          AnimateDiff / video nodes
  Gallery                 Built-in gallery with albums


DOCKER SERVICE
--------------
Add to docker-compose.yaml (based on official InvokeAI docker-compose.yml):

  invokeai:
    image: ghcr.io/invoke-ai/invokeai:latest
    container_name: studio-invokeai
    restart: unless-stopped
    tty: true
    stdin_open: true
    ports:
      - "127.0.0.1:9090:9090"
    environment:
      - INVOKEAI_ROOT=/invokeai
      - INVOKEAI_PORT=9090
      - GPU_DRIVER=cuda              # or rocm for AMD
      - CONTAINER_UID=1000            # match your host user
      - HF_HOME=/invokeai/.cache/huggingface
    volumes:
      - /mnt/studio/invokeai:/invokeai
      - /mnt/studio/cache/huggingface:/invokeai/.cache/huggingface
    deploy:
      resources:
        limits:
          memory: 24G
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9090/api/v1/app/version"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s

Source: https://github.com/invoke-ai/InvokeAI/tree/main/docker
Latest release: v6.12.0

IMPORTANT: InvokeAI manages its own directory structure inside INVOKEAI_ROOT.
Do NOT mount individual model directories. Mount the entire root and let
InvokeAI handle models/checkpoints/lora/vae/controlnet subdirectories.


CONFIGURATION
-------------
InvokeAI uses a single root directory (/invokeai) which contains:
  models/           All models (auto-managed by InvokeAI)
  outputs/          Generated images
  uploads/          User uploads
  .cache/           Model cache (HuggingFace, etc.)
  invokeai.yaml     Runtime config (auto-generated)

Environment variables (from official .env.sample):
  INVOKEAI_ROOT           Runtime directory inside container (/invokeai)
  INVOKEAI_PORT           Web UI port (9090)
  GPU_DRIVER              cuda or rocm
  CONTAINER_UID           UID for file ownership (match host user)
  HF_HOME                 HuggingFace cache path

On first start, InvokeAI initializes the directory structure and
downloads default models. Subsequent starts are faster.


ACCESSING INVOKEAI
------------------
From your laptop via SSH tunnel:

  ssh -p 2222 -L 9090:127.0.0.1:9090 admin@<brain-ip>

Then open:
  http://localhost:9090

All InvokeAI features work through the tunnel. No additional ports needed.


REST API
--------
InvokeAI has a full REST API for automation:

  Base URL: http://localhost:9090/api/v1/

  GET  /api/v1/app/version          App version info
  GET  /api/v1/models/              List all models
  POST /api/v1/queue/               Submit generation request
  GET  /api/v1/queue/               Check queue status
  GET  /api/v1/images/              List generated images
  GET  /api/v1/images/{id}          Get specific image
  POST /api/v1/images/upload        Upload image
  GET  /api/v1/workflows/           List workflows
  POST /api/v1/workflows/           Create workflow

Example: Generate an image via API
  curl -X POST http://localhost:9090/api/v1/queue/ \
    -H 'Content-Type: application/json' \
    -d '{
      "batch_id": "test",
      "prepend": false,
      "items": [{
        "workflow": "txt2img",
        "data": {
          "positive_prompt": "product photo of headphones",
          "model": "flux1-dev",
          "width": 1024,
          "height": 1024,
          "steps": 25,
          "cfg_scale": 7.5,
          "batch_size": 4
        }
      }]
    }'


USING INVOKEAI FEATURES
-----------------------

TEXT TO IMAGE
  1. Go to Generate tab
  2. Enter prompt in positive prompt field
  3. Enter negative prompt (optional)
  4. Select model from dropdown
  5. Set width/height (512 to 2048)
  6. Set batch count (1 to 16)
  7. Adjust steps (10-50), CFG scale (1-20)
  8. Click Generate

INPAINTING
  1. Upload or drag image to canvas
  2. Select inpaint tool (brush)
  3. Paint over area to regenerate
  4. Enter prompt describing what should be there
  5. Adjust denoising strength (0.5-1.0)
  6. Click Generate

BACKGROUND REMOVAL
  1. Upload image to canvas
  2. Use "Remove Background" from layer options
  3. Or: select background area with inpaint brush
  4. Prompt: "transparent background" or leave blank
  5. Generate

BATCH GENERATION
  1. Set batch count slider (1-16)
  2. Each batch produces that many variations
  3. All appear in gallery for comparison

STYLE REFERENCES
  1. Upload reference image
  2. Set reference strength (how much to follow style)
  3. Enter prompt
  4. Generated images match reference style

QUALITY CONTROLS
  Steps: Higher = more detail (slower). 20-30 for quality, 10 for speed.
  CFG Scale: How closely to follow prompt. 7-10 typical.
  Scheduler: Algorithm choice (euler, dpm, etc.)
  Denoising: For img2img. 0.3 = subtle change, 0.8 = major change.


MODEL SETUP
-----------
Place models in /mnt/studio/models/image/ on the external SSD.
InvokeAI scans at startup and in the Settings -> Models page.

Supported formats:
  Checkpoints:  .safetensors, .ckpt
  LoRA:         .safetensors
  VAE:          .safetensors
  ControlNet:   .safetensors

Download models:
  studio-model pull flux1-dev
  studio-model pull sdxl

Or use InvokeAI's built-in model manager:
  Settings -> Models -> Import Model -> Enter URL


REPLACING THE FLASK DASHBOARD
------------------------------
InvokeAI replaces most Flask dashboard functionality:

  Flask Dashboard           InvokeAI Equivalent
  ------------------------  --------------------------
  Workspace (6 modes)       Generate tab + Canvas
  Model selector            Settings -> Models
  Settings page             Settings panel
  Projects                  Gallery albums
  Workflows                 Workflows tab
  History strip             Gallery timeline

Keep the Flask dashboard for:
  - Text generation (llama.cpp chat -- not in InvokeAI)
  - TTS voiceover (Kokoro -- not in InvokeAI)
  - Transcription (Whisper -- not in InvokeAI)
  - Music generation (MusicGen -- not in InvokeAI)

Recommendation:
  - InvokeAI for all image/video work (primary interface)
  - Flask dashboard for text/audio work (companion)
  - Or: add text/audio tabs to InvokeAI via custom nodes


ACCESS POINTS AFTER SETUP
--------------------------
  http://localhost:9090  InvokeAI  (image/video generation -- primary)
  http://localhost:5000  Dashboard (text/audio -- optional companion)
  http://localhost:3000  Open WebUI (chat -- optional)

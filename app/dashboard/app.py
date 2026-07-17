#!/usr/bin/env python3
"""
AI Creative Studio - Creator Dashboard
=======================================
Backend-agnostic frontend that uses BackendRegistry for all AI services.
No hardcoded backend URLs -- everything flows through the registry.

Configure via /opt/ai-studio/config/backends.json or environment variables:
  TEXT_BACKEND=llama-cpp    (or ollama, vllm, openai)
  IMAGE_BACKEND=comfyui     (or automatic1111)
  VIDEO_BACKEND=comfyui
  TTS_BACKEND=kokoro
  STT_BACKEND=whisper

Access: http://localhost:5000
"""

import os
import json
import time
import logging
import shutil
import base64
import uuid
import urllib.request
import urllib.error
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory

from backends import BackendRegistry
from core_ai import (
    CoreAIError,
    assemble_mp4,
    audio_asset_paths,
    build_storyboard,
    check_brand_consistency,
    checksum_asset,
    extract_brand,
    generate_studio_image,
    generate_audio,
    generate_script,
    mask_has_editable_region,
    render_scenes,
)
from model_catalog import get_catalog, find_model, MODEL_CATALOG

app = Flask(__name__)
log = logging.getLogger("dashboard")

# ============================================================================
# Configuration
# ============================================================================
CREATOR_HOME = Path(os.environ.get("CREATOR_HOME", "/home/creator/ai-studio"))
STUDIO_MOUNT = Path(os.environ.get("STUDIO_MOUNT", "/mnt/studio"))
CONFIG_FILE = CREATOR_HOME / "config" / "settings.json"
HISTORY_FILE = CREATOR_HOME / "config" / "history.json"
PROJECTS_DIR = CREATOR_HOME / "projects"
EXPORTS_DIR = CREATOR_HOME / "exports"
UPLOADS_DIR = CREATOR_HOME / "uploads"
OUTPUT_DIR = CREATOR_HOME / "output"
STUDIO_JOBS: dict[str, dict] = {}

DEFAULT_SETTINGS = {
    "display_name": "Creator",
    "theme": "dark",
    "default_text_model": "llama-3.1-8b",
    "default_image_model": "flux1-dev",
    "default_video_model": "cogvideox-5b",
    "tts_voice": "af_heart",
    "output_format": "mp4",
    "auto_export": True,
    "auto_offload_minutes": 30,
}

# Backend registry -- single source of truth for all AI services
registry = BackendRegistry()


# ============================================================================
# Helpers
# ============================================================================
def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
        except (json.JSONDecodeError, OSError) as e:
            log.warning(f"Failed to load config {CONFIG_FILE}: {e}")
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()


def save_config(config):
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        log.error(f"Failed to save config {CONFIG_FILE}: {e}")


def save_generation(output_data, prompt_text, model, mode, gen_type="image"):
    """Save generation result to history and local storage."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    gen_id = str(int(time.time() * 1000))

    saved_files = []
    if isinstance(output_data, dict):
        images = output_data.get("images", [])
        for img_name in images:
            try:
                src = STUDIO_MOUNT / "exports" / img_name
                if src.exists():
                    dst = OUTPUT_DIR / f"{gen_id}_{img_name}"
                    shutil.copy2(src, dst)
                    saved_files.append(str(dst))
                else:
                    saved_files.append(str(OUTPUT_DIR / img_name))
            except OSError as e:
                log.warning(f"Failed to copy image {img_name}: {e}")

        # Handle base64 images (A1111 style)
        for b64 in output_data.get("images_base64", []):
            try:
                import base64
                fname = f"{gen_id}_generated.png"
                dst = OUTPUT_DIR / fname
                with open(dst, "wb") as f:
                    f.write(base64.b64decode(b64))
                saved_files.append(str(dst))
            except Exception as e:
                log.warning(f"Failed to save base64 image: {e}")

    item = {
        "id": gen_id,
        "type": gen_type,
        "files": saved_files,
        "prompt": prompt_text,
        "model": model,
        "mode": mode,
        "timestamp": time.time(),
    }

    history = []
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE) as f:
                history = json.load(f)
        except Exception:
            pass
    history.insert(0, item)
    history = history[:200]
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except OSError as e:
        log.error(f"Failed to save history: {e}")

    return item


def _get_installed_models():
    """Query all backends for their installed models."""
    installed = {}
    for btype in ["text", "image", "video", "tts", "stt"]:
        try:
            models = registry.list_models(btype)
            if btype in models and isinstance(models[btype], list):
                installed[btype] = models[btype]
            else:
                installed[btype] = []
        except Exception:
            installed[btype] = []
    return installed


def _save_studio_upload(field: str, required: bool = False) -> Path | None:
    """Save a Studio multipart image inside the configured upload store."""
    upload = request.files.get(field)
    if not upload or not upload.filename:
        if required:
            raise CoreAIError(f"{field.upper()}_REQUIRED: provide {field}")
        return None
    suffix = Path(upload.filename).suffix.lower() or ".png"
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise CoreAIError(f"INVALID_{field.upper()}: use JPG, PNG, or WebP")
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    destination = UPLOADS_DIR / f"studio-{uuid.uuid4().hex}{suffix}"
    upload.save(destination)
    return destination


def _copy_studio_asset(result: dict, job_id: str) -> Path:
    """Persist a generated image locally before publishing its checksum."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    destination = OUTPUT_DIR / f"studio-{job_id}.png"
    encoded = (result.get("images_base64") or [None])[0]
    if encoded:
        try:
            destination.write_bytes(base64.b64decode(encoded.split(",")[-1], validate=True))
        except (ValueError, OSError) as error:
            raise CoreAIError("ASSET_SAVE_FAILED: generated image payload is invalid") from error
    else:
        candidate = (result.get("images") or [None])[0]
        if not candidate:
            raise CoreAIError("ASSET_SAVE_FAILED: backend returned no image")
        source = Path(candidate)
        if not source.is_file():
            source = STUDIO_MOUNT / "exports" / source.name
        if not source.is_file():
            raise CoreAIError("ASSET_SAVE_FAILED: generated image is not locally accessible")
        try:
            shutil.copy2(source, destination)
        except OSError as error:
            raise CoreAIError(f"ASSET_SAVE_FAILED: {error}") from error
    if not destination.is_file() or not destination.stat().st_size:
        raise CoreAIError("ASSET_SAVE_FAILED: saved asset is empty")
    return destination


def _studio_backend_reference(path: Path | None) -> str | None:
    """Expose uploads in the form expected by the selected image adapter."""
    if path is None:
        return None
    if getattr(registry, "_config", {}).get("image") == "automatic1111":
        return base64.b64encode(path.read_bytes()).decode()
    backend_uploads = STUDIO_MOUNT / "uploads"
    backend_uploads.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backend_uploads / path.name)
    return path.name


# ============================================================================
# Routes: Pages
# ============================================================================
@app.route("/")
def index():
    return render_template("workspace.html")


@app.route("/workspace")
def workspace():
    return render_template("workspace.html")


@app.route("/studio")
def studio():
    """MOD-021 canvas surface. It uses the versioned Studio API below."""
    return render_template("studio.html")


@app.route("/dashboard")
def dashboard_page():
    config = load_config()
    return render_template("index.html", config=config)


@app.route("/models")
def models_page():
    return render_template("models.html", registry=MODEL_CATALOG)


@app.route("/settings")
def settings_page():
    config = load_config()
    return render_template("settings.html", config=config)


@app.route("/projects")
def projects_page():
    projects = []
    if PROJECTS_DIR.exists():
        try:
            for p in sorted(PROJECTS_DIR.iterdir()):
                if p.is_dir():
                    try:
                        size = sum(f.stat().st_size for f in p.rglob("*")
                                  if f.is_file()) // (1024 ** 2)
                    except OSError:
                        size = 0
                    projects.append({"name": p.name, "size_mb": size})
        except OSError as e:
            log.warning(f"Failed to list projects: {e}")
    return render_template("projects.html", projects=projects)


# ============================================================================
# API: Generation (routes to correct backend by mode)
# ============================================================================
@app.route("/api/instant-ad", methods=["POST"])
def instant_ad():
    """Create the Phase-1 brand, script, and storyboard artifacts.

    ``render=true`` additionally dispatches the ten scenes and audio to the
    selected local/API providers.  The default draft path is deliberately
    flash-first: it produces reviewable artifacts before expensive rendering.
    """
    if "image" not in request.files or not request.files["image"].filename:
        return jsonify({"error": "IMAGE_REQUIRED: provide a JPG, PNG, or WebP image"}), 400
    image = request.files["image"]
    filename = f"ad_{int(time.time())}_{Path(image.filename).name}"
    try:
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        image_path = UPLOADS_DIR / filename
        image.save(image_path)
        brand = extract_brand(image_path, request.form.get("product_type", "product"))
        script = generate_script(brand, request.form.get("tagline", ""))
        storyboard = build_storyboard(script, brand)
        quality = check_brand_consistency(brand, storyboard)
        payload = {
            "brand_analysis": brand.to_dict(),
            "script": [scene.to_dict() for scene in script],
            "storyboard": storyboard,
            "quality": quality,
            "duration_seconds": sum(scene.duration_seconds for scene in script),
        }
        if request.form.get("render", "false").lower() == "true":
            payload["rendered_scenes"] = render_scenes(storyboard, registry, filename)
            payload["audio"] = generate_audio(
                script, registry, request.form.get("voice", "neutral"),
                request.form.get("music_style", "upbeat"),
            )
            scene_paths = []
            for rendered in payload["rendered_scenes"]:
                asset = rendered["asset"]
                if isinstance(asset, list):
                    asset = asset[0] if asset else None
                candidate = Path(asset) if asset else None
                if candidate and not candidate.is_file():
                    candidate = STUDIO_MOUNT / "exports" / candidate.name
                if not candidate or not candidate.is_file():
                    raise CoreAIError("ASSEMBLY_FAILED: rendered scene is not available as a local video file")
                scene_paths.append(candidate)
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            output_name = f"instant-ad-{int(time.time() * 1000)}.mp4"
            output = assemble_mp4(scene_paths, OUTPUT_DIR / output_name,
                                  audio_asset_paths(payload["audio"], OUTPUT_DIR, output_name))
            payload.update({
                "video_url": f"/output/{output.name}",
                "video_duration": payload["duration_seconds"],
                "video_resolution": "1920x1080",
                "video_size_mb": round(output.stat().st_size / (1024 * 1024), 3),
            })
        return jsonify(payload), 200
    except CoreAIError as error:
        return jsonify({"error": str(error)}), 400
    except OSError as error:
        return jsonify({"error": f"IMAGE_WRITE_FAILED: {error}"}), 500


@app.route("/api/v1/backends", methods=["GET"])
def backend_catalog():
    return jsonify(registry.catalog())


@app.route("/api/v1/backends/select", methods=["POST"])
def select_backend():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(registry.select(data.get("modality", ""), data.get("backend", ""),
                                       data.get("provider_key_ref")))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


@app.route("/api/v1/studio/generate", methods=["POST"])
def studio_generate():
    """Generate a flash preview or an explicitly approved final Studio asset."""
    return _run_studio_job("generate")


@app.route("/api/v1/studio/inpaint", methods=["POST"])
def studio_inpaint():
    """Perform mask-aware inpaint, outpaint, or restyle on a canvas upload."""
    return _run_studio_job(request.form.get("mode", "inpaint"))


@app.route("/api/v1/studio/<job_id>", methods=["GET"])
def studio_job(job_id: str):
    job = STUDIO_JOBS.get(job_id)
    if not job:
        return jsonify({"error": "JOB_NOT_FOUND"}), 404
    return jsonify(job)


def _run_studio_job(mode: str):
    """Synchronous local job runner with the documented job-status contract."""
    data = request.form if request.form else (request.get_json(silent=True) or {})
    try:
        prompt = str(data.get("prompt", ""))
        palette = str(data.get("brand_palette", "")).strip()
        if palette:
            prompt = f"{prompt}\nBrand palette: {palette}."
        source = _save_studio_upload("source_image", required=mode != "generate")
        mask = _save_studio_upload("mask", required=mode != "generate")
        if mask and not mask_has_editable_region(mask):
            raise CoreAIError("INVALID_MASK: mask does not cover any editable region")
        requested_tier = str(data.get("tier", "flash"))
        approved = str(data.get("approved", "false")).lower() == "true"
        if requested_tier == "final" and not approved:
            raise CoreAIError("APPROVAL_REQUIRED: final render requires approved=true")
        if requested_tier != "final":
            requested_tier = "flash"
        job_id = uuid.uuid4().hex
        result = generate_studio_image(
            prompt, mode, registry,
            source_image=_studio_backend_reference(source),
            mask_image=_studio_backend_reference(mask),
            width=int(data.get("width", 1024)), height=int(data.get("height", 1024)),
            tier=requested_tier,
        )
        asset = _copy_studio_asset(result, job_id)
        checksum = checksum_asset(asset)
        image_backend = next((item for item in registry.catalog()["modalities"]
                              if item["modality"] == "image"), {"effective": "local"})
        job = {"job_id": job_id, "status": "completed", "image_url": f"/output/{asset.name}",
               "resolution": f"{data.get('width', 1024)}x{data.get('height', 1024)}",
               "checksum": checksum, "backend_used": image_backend["effective"],
               "mode": mode, "tier": requested_tier, "brand_palette": palette}
        STUDIO_JOBS[job_id] = job
        return jsonify(job), 200
    except (CoreAIError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    except OSError as error:
        return jsonify({"error": f"ASSET_SAVE_FAILED: {error}"}), 500


@app.route("/api/generate", methods=["POST"])
def generate():
    """
    Unified generation endpoint. Routes to the correct backend based on mode:
      text-to-image, image-to-image  -> registry.image
      text-to-video, image-to-video  -> registry.video
      text                           -> registry.text
    """
    mode = request.form.get("mode", "text-to-image")
    model = request.form.get("model", "")
    prompt = request.form.get("prompt", "")

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    # --- Text generation modes ---
    if mode in ("text", "text-generate"):
        try:
            max_tokens = int(request.form.get("max_tokens", 2048))
            temperature = float(request.form.get("temperature", 0.7))
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid max_tokens or temperature value"}), 400
        text_backend = registry.text
        result = text_backend.generate(
            prompt=prompt,
            model=model or None,
            system=request.form.get("system", ""),
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if "error" in result:
            return jsonify({"error": result["error"]}), 500
        return jsonify({"response": result.get("response", ""),
                        "model": result.get("model", model)})

    # --- Image generation modes ---
    negative = request.form.get("negative_prompt", "")
    try:
        cfg = float(request.form.get("cfg", 7.5))
        steps = int(request.form.get("steps", 25))
        width = int(request.form.get("width", 1024))
        height = int(request.form.get("height", 1024))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid numeric parameter (cfg, steps, width, height)"}), 400

    uploaded_file = None
    if "file" in request.files and request.files["file"].filename:
        try:
            f = request.files["file"]
            UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
            filename = f"upload_{int(time.time())}_{f.filename}"
            filepath = UPLOADS_DIR / filename
            f.save(filepath)
            uploaded_file = filename

            # Copy to backend input directory (ComfyUI needs this)
            comfyui_input = STUDIO_MOUNT / "uploads"
            comfyui_input.mkdir(parents=True, exist_ok=True)
            shutil.copy2(filepath, comfyui_input / filename)
        except OSError as e:
            return jsonify({"error": f"File upload failed: {e}"}), 500

    if mode in ("text-to-image", "image-to-image"):
        img_backend = registry.image
        img_mode = "img2img" if mode == "image-to-image" else "txt2img"
        result = img_backend.generate(
            prompt=prompt,
            model=model or None,
            negative=negative,
            width=width,
            height=height,
            steps=steps,
            cfg=cfg,
            input_image=uploaded_file,
            mode=img_mode,
        )
        if "error" in result:
            return jsonify({"error": result["error"]}), 500

        item = save_generation(result, prompt, model, mode, gen_type="image")
        output_url = None
        if item["files"]:
            output_url = f"/output/{Path(item['files'][0]).name}"

        return jsonify({
            "id": item["id"],
            "url": output_url,
            "type": "image",
            "files": item["files"],
            "prompt_id": result.get("prompt_id"),
        })

    # --- Video generation modes ---
    if mode in ("text-to-video", "image-to-video"):
        vid_backend = registry.video
        vid_mode = "img2vid" if mode == "image-to-video" else "txt2vid"
        result = vid_backend.generate(
            prompt=prompt,
            model=model or None,
            negative=negative,
            width=width,
            height=height,
            steps=steps,
            cfg=cfg,
            frames=int(request.form.get("frames", 49)),
            fps=int(request.form.get("fps", 8)),
            input_image=uploaded_file,
            mode=vid_mode,
        )
        if "error" in result:
            return jsonify({"error": result["error"]}), 500

        item = save_generation(result, prompt, model, mode, gen_type="video")
        output_url = None
        if item["files"]:
            output_url = f"/output/{Path(item['files'][0]).name}"

        return jsonify({
            "id": item["id"],
            "url": output_url,
            "type": "video",
            "files": item["files"],
            "prompt_id": result.get("prompt_id"),
        })

    return jsonify({"error": f"Unknown mode: {mode}"}), 400


# ============================================================================
# API: Prompt Enhancement (uses text backend)
# ============================================================================
@app.route("/api/enhance-prompt", methods=["POST"])
def enhance_prompt():
    """Use the text backend to enhance the user's prompt for image/video generation."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    prompt = data.get("prompt", "")
    mode = data.get("mode", "text-to-image")

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    system_prompt = (
        "You are an expert prompt engineer for AI image/video generation. "
        "Rewrite the user's prompt to be more detailed and specific for the AI generator. "
        "Add lighting, composition, style, and quality descriptors. "
        "Keep it under 200 words. Output ONLY the enhanced prompt, no explanations."
    )
    if "video" in mode:
        system_prompt += " Focus on motion, camera movement, and temporal details."

    text_backend = registry.text
    config = load_config()
    result = text_backend.generate(
        prompt=prompt,
        model=config.get("default_text_model"),
        system=system_prompt,
        max_tokens=300,
        temperature=0.7,
    )

    if "error" in result:
        enhanced = f"{prompt}, professional photography, 8k, ultra detailed, commercial quality, studio lighting"
        return jsonify({"enhanced": enhanced})

    return jsonify({"enhanced": result.get("response", prompt).strip()})


# ============================================================================
# API: Text Generation
# ============================================================================
@app.route("/api/text/generate", methods=["POST"])
def text_generate():
    """Generate text using the configured text backend."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    prompt = data.get("prompt", "")
    model = data.get("model", "")
    system = data.get("system", "")

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    text_backend = registry.text
    result = text_backend.generate(
        prompt=prompt,
        model=model or None,
        system=system,
        max_tokens=data.get("max_tokens", 2048),
        temperature=data.get("temperature", 0.7),
    )

    if "error" in result:
        return jsonify(result), 500

    return jsonify({"response": result.get("response", "")})


# ============================================================================
# API: TTS
# ============================================================================
@app.route("/api/tts", methods=["POST"])
def tts_generate():
    """Generate voiceover via the configured TTS backend."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    text = data.get("text", "")
    voice = data.get("voice", "af_heart")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    tts_backend = registry.tts
    result = tts_backend.synthesize(text=text, voice=voice)

    if "error" in result:
        return jsonify({"error": result["error"]}), 500

    if "audio_path" in result:
        filename = Path(result["audio_path"]).name
        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            dst = OUTPUT_DIR / filename
            src = Path(result["audio_path"])
            if src.exists():
                shutil.copy2(src, dst)
        except OSError as e:
            log.warning(f"Failed to copy audio file: {e}")
        return jsonify({"url": f"/output/{filename}", "filename": filename})

    return jsonify(result)


# ============================================================================
# API: Transcription
# ============================================================================
@app.route("/api/transcribe", methods=["POST"])
def transcribe():
    """Transcribe audio/video via the configured STT backend."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    try:
        f = request.files["file"]
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"transcribe_{int(time.time())}_{f.filename}"
        filepath = UPLOADS_DIR / filename
        f.save(filepath)

        with open(filepath, "rb") as audio_file:
            audio_data = audio_file.read()
    except OSError as e:
        return jsonify({"error": f"File operation failed: {e}"}), 500

    stt_backend = registry.stt
    result = stt_backend.transcribe(audio_data)

    if "error" in result:
        return jsonify({"error": result["error"]}), 500

    return jsonify(result)


# ============================================================================
# API: Models
# ============================================================================
@app.route("/api/models")
def api_models():
    """List installed models from all configured backends."""
    installed = _get_installed_models()

    # Get queue info from image/video backends if available
    queue_running = 0
    queue_pending = 0
    try:
        img_backend = registry.image
        if hasattr(img_backend, "get_queue"):
            queue = img_backend.get_queue()
            queue_running = len(queue.get("queue_running", []))
            queue_pending = len(queue.get("queue_pending", []))
    except Exception:
        pass

    return jsonify({
        "text_models": installed.get("text", []),
        "image_models": installed.get("image", []),
        "video_models": installed.get("video", []),
        "tts_voices": installed.get("tts", []),
        "queue_running": queue_running,
        "queue_pending": queue_pending,
        "config": registry._config,
    })


@app.route("/api/models/catalog")
def api_models_catalog():
    """Show full model catalog with install status."""
    installed = _get_installed_models()
    catalog = get_catalog(installed)
    return jsonify(catalog)


@app.route("/api/models/pull", methods=["POST"])
def api_models_pull():
    """
    Trigger a model download/pull.
    Accepts {"model_id": "..."} or {"model_id": "...", "type": "text"}.
    For text backends (ollama), triggers remote pull.
    For image backends, returns instructions since manual placement is needed.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    model_id = data.get("model_id", "")
    model_type = data.get("type", "")

    if not model_id:
        return jsonify({"error": "No model_id provided"}), 400

    model_info = find_model(model_id)
    if not model_info:
        return jsonify({"error": f"Model '{model_id}' not found in catalog"}), 404

    if not model_type:
        model_type = model_info.get("type", "")

    # Text backends: try to pull via backend-specific mechanism
    if model_type == "text":
        text_backend = registry.text
        if hasattr(text_backend, "pull_model"):
            result = text_backend.pull_model(model_id)
            if "error" in result:
                return jsonify({"error": result["error"]}), 500
            return jsonify({"status": "pulling", "model_id": model_id,
                            "detail": result})

        pull_cmd = model_info.get("pull_command", "")
        return jsonify({
            "status": "instructions",
            "model_id": model_id,
            "message": f"Run: {pull_cmd}" if pull_cmd
                       else f"Download model '{model_id}' and place in models dir",
        })

    # Image/video backends: return instructions
    filename = model_info.get("filename", "")
    if model_type == "image":
        message = (f"Place the model file '{filename}' in the ComfyUI "
                   f"models/checkpoints/ directory") if filename \
            else "Download and place the model in the appropriate models directory"
    elif model_type == "video":
        message = (f"Place the model file '{filename}' in the ComfyUI "
                   f"models/checkpoints/ directory") if filename \
            else "Download and place the model in the appropriate models directory"
    else:
        message = f"Download model '{model_id}' manually"

    return jsonify({
        "status": "instructions",
        "model_id": model_id,
        "message": message,
        "filename": filename,
        "size_gb": model_info.get("size_gb", 0),
    })


# ============================================================================
# API: Status
# ============================================================================
@app.route("/health")
def health():
    """Liveness endpoint used by Docker and continuous integration."""
    return jsonify({"status": "ok"}), 200


@app.route("/api/status")
def api_status():
    """Health check all configured backends via registry."""
    backend_status = registry.status()

    # Add queue info from image backend
    try:
        img_backend = registry.image
        if hasattr(img_backend, "get_queue"):
            queue = img_backend.get_queue()
            backend_status["queue"] = {
                "running": len(queue.get("queue_running", [])),
                "pending": len(queue.get("queue_pending", [])),
            }
    except Exception:
        pass

    # Storage info
    try:
        usage = shutil.disk_usage(CREATOR_HOME)
        backend_status["storage"] = {
            "used_gb": usage.used // (1024 ** 3),
            "total_gb": usage.total // (1024 ** 3),
        }
    except Exception:
        backend_status["storage"] = {"used_gb": 0, "total_gb": 0}

    return jsonify(backend_status)


# ============================================================================
# API: History
# ============================================================================
@app.route("/api/history")
def api_history():
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE) as f:
                return jsonify({"history": json.load(f)})
        except Exception:
            pass
    return jsonify({"history": []})


@app.route("/api/history/<gen_id>", methods=["DELETE"])
def delete_history(gen_id):
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE) as f:
                history = json.load(f)
            history = [h for h in history if h["id"] != gen_id]
            with open(HISTORY_FILE, "w") as f:
                json.dump(history, f, indent=2)
        except (json.JSONDecodeError, OSError, KeyError) as e:
            return jsonify({"error": f"Failed to update history: {e}"}), 500
    return jsonify({"status": "deleted"})


# ============================================================================
# API: Settings
# ============================================================================
@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if request.method == "GET":
        return jsonify(load_config())
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    config = load_config()
    config.update(data)
    save_config(config)
    return jsonify({"status": "saved"})


# ============================================================================
# API: Output files
# ============================================================================
@app.route("/output/<path:filename>")
def serve_output(filename):
    try:
        return send_from_directory(OUTPUT_DIR, filename)
    except Exception:
        return jsonify({"error": "File not found"}), 404


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    try:
        return send_from_directory(UPLOADS_DIR, filename)
    except Exception:
        return jsonify({"error": "File not found"}), 404


# ============================================================================
# API: Backend proxy (pass-through for advanced operations)
# ============================================================================
@app.route("/api/backend/<backend_type>/<path:subpath>",
           methods=["GET", "POST"])
def backend_proxy(backend_type, subpath):
    """
    Generic proxy to the underlying backend for advanced operations.
    backend_type: text, image, video, tts, stt
    """
    try:
        backend = registry._get(backend_type)
        url = getattr(backend, "url", None)
        if not url:
            return jsonify({"error": f"No URL for backend '{backend_type}'"}), 400

        full_url = f"{url}/{subpath}"
        if request.method == "POST":
            data = request.get_data()
            req = urllib.request.Request(full_url, data=data,
                headers={"Content-Type": "application/json"})
        else:
            req = urllib.request.Request(full_url)

        resp = urllib.request.urlopen(req, timeout=60)
        return resp.read(), resp.status, {
            "Content-Type": resp.headers.get("Content-Type", "application/json")
        }
    except urllib.error.HTTPError as e:
        return jsonify({"error": f"{backend_type}: {e.code} {e.reason}"}), e.code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Startup
# ============================================================================
if __name__ == "__main__":
    for d in [CREATOR_HOME / "config", PROJECTS_DIR, EXPORTS_DIR,
              UPLOADS_DIR, OUTPUT_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=False)

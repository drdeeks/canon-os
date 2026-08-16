"""
Model Catalog - Curated list of all supported models with metadata.
Provides a central catalog that UIs and CLI can query for available/pullable models.
"""

import logging
from typing import List, Dict, Optional

log = logging.getLogger("model_catalog")

# ---------------------------------------------------------------------------
# Flat catalog keyed by model id.  Each entry carries enough metadata for
# the CLI pull command (download_url, local_path) and the dashboard UI.
# ---------------------------------------------------------------------------

MODEL_CATALOG: Dict[str, dict] = {
    # ── Text / LLM models ──────────────────────────────────────────────
    "llama-3.1-8b": {
        "id": "llama-3.1-8b",
        "name": "Llama 3.1 8B Instruct (GGUF Q4)",
        "type": "text",
        "size_gb": 5.0,
        "vram_gb": 6.0,
        "description": "Meta Llama 3.1 8B quantised to GGUF Q4. Great general-purpose chat and instruction model.",
        "download_url": "https://huggingface.co/bartowski/Llama-3.1-8B-Instruct-GGUF/resolve/main/Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "local_path": "/mnt/studio/models/text/llama-3.1-8b/Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "tags": ["general", "chat", "gguf"],
        "use_cases": ["chat", "general", "creative-writing"],
    },
    "llama-3.1-70b": {
        "id": "llama-3.1-70b",
        "name": "Llama 3.1 70B Instruct (GGUF Q4)",
        "type": "text",
        "size_gb": 40.0,
        "vram_gb": 48.0,
        "description": "Meta Llama 3.1 70B quantised to GGUF Q4. High-quality responses, requires significant VRAM / RAM.",
        "download_url": "https://huggingface.co/bartowski/Llama-3.1-70B-Instruct-GGUF/resolve/main/Llama-3.1-70B-Instruct-Q4_K_M.gguf",
        "local_path": "/mnt/studio/models/text/llama-3.1-70b/Llama-3.1-70B-Instruct-Q4_K_M.gguf",
        "tags": ["general", "chat", "large", "gguf"],
        "use_cases": ["chat", "general", "creative-writing", "code"],
    },
    "gemma-2-27b": {
        "id": "gemma-2-27b",
        "name": "Gemma 2 27B IT (GGUF Q4)",
        "type": "text",
        "size_gb": 16.0,
        "vram_gb": 20.0,
        "description": "Google Gemma 2 27B instruction-tuned, quantised to GGUF Q4. Excellent multilingual model.",
        "download_url": "https://huggingface.co/bartowski/gemma-2-27b-it-GGUF/resolve/main/gemma-2-27b-it-Q4_K_M.gguf",
        "local_path": "/mnt/studio/models/text/gemma-2-27b/gemma-2-27b-it-Q4_K_M.gguf",
        "tags": ["general", "multilingual", "gguf"],
        "use_cases": ["chat", "general", "multilingual"],
    },

    # ── Image models ───────────────────────────────────────────────────
    "flux1-dev": {
        "id": "flux1-dev",
        "name": "FLUX.1 Dev",
        "type": "image",
        "size_gb": 12.0,
        "vram_gb": 16.0,
        "description": "Black Forest Labs FLUX.1 development model. State-of-the-art text-to-image generation.",
        "download_url": "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev.safetensors",
        "local_path": "/mnt/studio/models/image/flux1-dev/flux1-dev.safetensors",
        "tags": ["state-of-art", "text-to-image"],
        "use_cases": ["image-generation", "product-shots", "creative"],
    },
    "sdxl-base": {
        "id": "sdxl-base",
        "name": "Stable Diffusion XL Base 1.0",
        "type": "image",
        "size_gb": 7.0,
        "vram_gb": 8.0,
        "description": "Stability AI's Stable Diffusion XL base model. Versatile and widely supported image generator.",
        "download_url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors",
        "local_path": "/mnt/studio/models/image/sdxl-base/sd_xl_base_1.0.safetensors",
        "tags": ["general", "high-res", "text-to-image"],
        "use_cases": ["image-generation", "product-shots", "creative"],
    },

    # ── Video models ───────────────────────────────────────────────────
    "cogvideox-5b": {
        "id": "cogvideox-5b",
        "name": "CogVideoX 5B",
        "type": "video",
        "size_gb": 12.0,
        "vram_gb": 16.0,
        "description": "THUDM's CogVideoX 5B text-to-video model. Generates short video clips from text prompts.",
        "download_url": "https://huggingface.co/THUDM/CogVideoX-5b/resolve/main/diffusion_pytorch_model-00001-of-00002.safetensors",
        "local_path": "/mnt/studio/models/video/cogvideox-5b/cogvideox-5b.safetensors",
        "tags": ["text-to-video"],
        "use_cases": ["video-generation"],
    },
    "svd-xt": {
        "id": "svd-xt",
        "name": "Stable Video Diffusion XT",
        "type": "video",
        "size_gb": 9.0,
        "vram_gb": 12.0,
        "description": "Stability AI's image-to-video model. Animates still images into short video clips.",
        "download_url": "https://huggingface.co/stabilityai/stable-video-diffusion-xt/resolve/main/svd_xt.safetensors",
        "local_path": "/mnt/studio/models/video/svd-xt/svd_xt.safetensors",
        "tags": ["img2vid"],
        "use_cases": ["video-generation", "animation"],
    },

    # ── Audio / TTS models ─────────────────────────────────────────────
    "kokoro-tts": {
        "id": "kokoro-tts",
        "name": "Kokoro TTS",
        "type": "tts",
        "size_gb": 0.5,
        "vram_gb": 1.0,
        "description": "Fast, lightweight text-to-speech model. Runs on CPU.",
        "download_url": "https://huggingface.co/hexgrad/kokoro-82M/resolve/main/kokoro-v1_0.pth",
        "local_path": "/mnt/studio/models/audio/kokoro-tts/kokoro-v1_0.pth",
        "tags": ["fast", "lightweight", "tts"],
        "use_cases": ["text-to-speech"],
    },
    "whisper-large-v3": {
        "id": "whisper-large-v3",
        "name": "Whisper Large V3",
        "type": "stt",
        "size_gb": 3.0,
        "vram_gb": 4.0,
        "description": "OpenAI Whisper large-v3 speech-to-text model. Best accuracy for transcription and translation.",
        "download_url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin",
        "local_path": "/mnt/studio/models/audio/whisper-large-v3/ggml-large-v3.bin",
        "tags": ["stt", "transcription"],
        "use_cases": ["speech-to-text", "transcription"],
    },
    "musicgen-medium": {
        "id": "musicgen-medium",
        "name": "MusicGen Medium",
        "type": "music",
        "size_gb": 3.5,
        "vram_gb": 6.0,
        "description": "Meta's MusicGen medium model for text-to-music generation.",
        "download_url": "https://huggingface.co/facebook/musicgen-medium/resolve/main/model.safetensors",
        "local_path": "/mnt/studio/models/audio/musicgen-medium/model.safetensors",
        "tags": ["music", "generation"],
        "use_cases": ["music-generation"],
    },
}


# ── Public API ──────────────────────────────────────────────────────────

def search_models(query: str) -> Dict[str, dict]:
    """Search models by name, description, tags or use_cases."""
    q = query.lower()
    results = {}
    for mid, info in MODEL_CATALOG.items():
        searchable = " ".join([
            info.get("name", ""),
            info.get("description", ""),
            " ".join(info.get("tags", [])),
            " ".join(info.get("use_cases", [])),
        ]).lower()
        if q in searchable:
            results[mid] = info
    return results


def get_model(model_id: str) -> Optional[dict]:
    """Return a single model entry by id, or None."""
    return MODEL_CATALOG.get(model_id)


def get_models_by_type(model_type: str) -> Dict[str, dict]:
    """Return all models of a given type (text, image, video, tts, stt, music)."""
    return {mid: info for mid, info in MODEL_CATALOG.items()
            if info.get("type") == model_type}


def get_models_by_use_case(use_case: str) -> Dict[str, dict]:
    """Return all models matching a use case tag."""
    uc = use_case.lower()
    return {mid: info for mid, info in MODEL_CATALOG.items()
            if uc in [u.lower() for u in info.get("use_cases", [])]}


# ── Legacy helpers kept for dashboard compatibility ─────────────────────

def get_catalog(installed_models: dict = None) -> dict:
    """
    Return the catalog grouped by type, with an 'installed' flag on each entry.
    installed_models: {type: [list of installed model ids]}
    """
    result: Dict[str, list] = {}
    for mid, info in MODEL_CATALOG.items():
        mtype = info.get("type", "other")
        installed = set()
        if installed_models and mtype in installed_models:
            installed = set(installed_models[mtype])
        entry = dict(info)
        entry["installed"] = (
            mid in installed
            or any(mid.replace("-", "_").lower() in inst.lower().replace("-", "_")
                   for inst in installed)
        )
        result.setdefault(mtype, []).append(entry)
    return result


def find_model(model_id: str) -> Optional[dict]:
    """Alias for get_model (dashboard backward compat)."""
    return get_model(model_id)

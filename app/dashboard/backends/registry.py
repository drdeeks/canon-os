"""
Backend Registry - Central dispatch for all AI backends.
Each backend type (text, image, video, tts, stt) has a registry.
Configure once, use everywhere.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

log = logging.getLogger("backends")

# Backend configuration - loaded from env or config file
CONFIG_FILE = Path(os.environ.get("STUDIO_CONFIG", "/opt/ai-studio/config/backends.json"))

DEFAULT_BACKENDS = {
    "text": os.environ.get("TEXT_BACKEND", "llama-cpp"),
    "image": os.environ.get("IMAGE_BACKEND", "comfyui"),
    "video": os.environ.get("VIDEO_BACKEND", "comfyui-video"),
    "tts": os.environ.get("TTS_BACKEND", "kokoro"),
    "stt": os.environ.get("STT_BACKEND", "whisper"),
}

# Default URLs per backend
DEFAULT_URLS = {
    "llama-cpp": os.environ.get("LLAMACPP_URL", "http://studio-llamacpp:8080"),
    "ollama": os.environ.get("OLLAMA_URL", "http://studio-ollama:11434"),
    "vllm": os.environ.get("VLLM_URL", "http://studio-vllm:8000"),
    "openai": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    "comfyui": os.environ.get("COMFYUI_URL", "http://studio-comfyui:8188"),
    "comfyui-video": os.environ.get("COMFYUI_VIDEO_URL", "http://studio-comfyui:8188"),
    "automatic1111": os.environ.get("A1111_URL", "http://studio-a1111:7860"),
    "animatediff": os.environ.get("ANIMATEDIFF_URL", "http://studio-comfyui:8188"),
    "kokoro": os.environ.get("KOKORO_URL", "http://studio-kokoro:8880"),
    "coqui": os.environ.get("COQUI_URL", "http://studio-coqui:5002"),
    "bark": os.environ.get("BARK_URL", "http://studio-bark:5000"),
    "whisper": os.environ.get("WHISPER_URL", "http://studio-whisper:9000"),
    "faster-whisper": os.environ.get("FASTER_WHISPER_URL", "http://studio-faster-whisper:8080"),
    "audiocraft": os.environ.get("AUDIOCRAFT_URL", "http://studio-audiocraft:7860"),
    "stable-audio": os.environ.get("STABLE_AUDIO_URL", "http://studio-stable-audio:7860"),
    "ace-step": os.environ.get("ACE_STEP_URL", "http://studio-ace-step:7860"),
}


def _load_config() -> dict:
    """Load backend config from file, falling back to env/defaults."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
                return {**DEFAULT_BACKENDS, **cfg.get("backends", {})}
        except (json.JSONDecodeError, OSError) as e:
            log.warning(f"Failed to load backend config {CONFIG_FILE}: {e}")
    return DEFAULT_BACKENDS.copy()


def _get_url(backend_name: str, overrides: dict = None) -> str:
    """Get URL for a backend, with optional overrides."""
    if overrides and backend_name in overrides:
        return overrides[backend_name]
    return DEFAULT_URLS.get(backend_name, "")


# ============================================================================
# Registry
# ============================================================================
class BackendRegistry:
    """
    Central registry. Usage:
        registry = BackendRegistry()
        text_gen = registry.text       # -> TextBackend instance
        image_gen = registry.image     # -> ImageBackend instance
        result = text_gen.generate("Hello")
    """

    def __init__(self, config: dict = None, url_overrides: dict = None):
        self._config = config or _load_config()
        self._urls = url_overrides or DEFAULT_URLS
        self._instances: Dict[str, Any] = {}
        log.info(f"Backend config: {self._config}")

    def _get(self, backend_type: str):
        """Lazy-load and cache a backend instance."""
        if backend_type not in self._instances:
            backend_name = self._config.get(backend_type)
            if not backend_name:
                raise ValueError(f"No backend configured for type '{backend_type}'")
            url = _get_url(backend_name, self._urls)
            adapter = _ADAPTERS.get(backend_name)
            if not adapter:
                raise ValueError(f"Unknown backend: {backend_name}")
            self._instances[backend_type] = adapter(url=url, config=self._config)
            log.info(f"Loaded {backend_type} backend: {backend_name} at {url}")
        return self._instances[backend_type]

    @property
    def text(self):
        return self._get("text")

    @property
    def image(self):
        return self._get("image")

    @property
    def video(self):
        return self._get("video")

    @property
    def tts(self):
        return self._get("tts")

    @property
    def stt(self):
        return self._get("stt")

    def status(self) -> dict:
        """Health check all configured backends."""
        result = {}
        for btype in ["text", "image", "video", "tts", "stt"]:
            try:
                backend = self._get(btype)
                result[btype] = {
                    "backend": self._config.get(btype),
                    "healthy": backend.health_check(),
                }
            except Exception as e:
                result[btype] = {
                    "backend": self._config.get(btype),
                    "healthy": False,
                    "error": str(e),
                }
        return result

    def list_models(self, backend_type: str = None) -> dict:
        """List available models per backend type."""
        types = [backend_type] if backend_type else ["text", "image", "video", "tts", "stt"]
        result = {}
        for btype in types:
            try:
                backend = self._get(btype)
                models = backend.list_models()
                result[btype] = models if isinstance(models, list) else []
            except Exception as e:
                log.warning(f"Failed to list models for {btype}: {e}")
                result[btype] = []
        return result


# ============================================================================
# Adapter Registration
# ============================================================================
_ADAPTERS = {}

def register_backend(name: str):
    """Decorator to register a backend adapter class."""
    def decorator(cls):
        _ADAPTERS[name] = cls
        return cls
    return decorator

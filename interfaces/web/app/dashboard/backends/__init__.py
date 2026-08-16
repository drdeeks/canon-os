"""
AI Creative Studio - Backend Abstraction Layer
================================================
Provider-agnostic interface for all AI services.

The dashboard never talks to Ollama, llama.cpp, vLLM, or any specific
backend directly. It talks through these interfaces.

Configure via environment variables or config.yaml:
  TEXT_BACKEND=llama-cpp    (or ollama, vllm, openai)
  IMAGE_BACKEND=comfyui     (or automatic1111, forge)
  VIDEO_BACKEND=comfyui
  TTS_BACKEND=kokoro        (or coqui, bark)
  STT_BACKEND=whisper

Each backend adapter translates between the dashboard's API and the
backend's specific API. Adding a new backend = one new file.
"""

from .registry import BackendRegistry, register_backend
from .text import TextBackend
from .image import ImageBackend
from .video import VideoBackend
from .tts import TTSBackend
from .stt import STTBackend
from .music import MusicBackend
from . import demo  # noqa: F401 - registers provider-free demo adapters

__all__ = [
    "BackendRegistry",
    "register_backend",
    "TextBackend",
    "ImageBackend",
    "VideoBackend",
    "TTSBackend",
    "STTBackend",
    "MusicBackend",
]

"""
Speech-to-Text Backend - Abstract + Adapters
Supports: whisper (whisper.cpp server), faster-whisper
"""

import json
import base64
import urllib.request
from abc import ABC, abstractmethod
from typing import List
from .registry import register_backend


class STTBackend(ABC):
    """Abstract speech-to-text backend."""

    @abstractmethod
    def transcribe(self, audio_base64: str = None, audio_url: str = None,
                   language: str = None, task: str = "transcribe") -> dict:
        """Transcribe audio. Returns {"text": "...", "language": "...", "segments": [...]}"""
        ...

    @abstractmethod
    def list_models(self) -> List[str]:
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...


# ============================================================================
# whisper.cpp server (ggerganov/whisper.cpp)
# ============================================================================
@register_backend("whisper")
class WhisperCppBackend(STTBackend):
    def __init__(self, url: str, config: dict = None):
        self.url = url.rstrip("/")

    def transcribe(self, audio_base64=None, audio_url=None, language=None,
                   task="transcribe"):
        if not audio_base64 and not audio_url:
            return {"error": "Provide audio_base64 or audio_url"}

        try:
            if audio_base64:
                # whisper.cpp accepts POST with JSON containing base64 audio
                payload = json.dumps({
                    "audio_data": audio_base64,
                    "language": language or "en",
                    "task": task,
                    "response_format": "json",
                    "temperature": 0.0,
                }).encode()
                req = urllib.request.Request(
                    f"{self.url}/inference",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
            else:
                # URL-based inference
                payload = json.dumps({
                    "url": audio_url,
                    "language": language or "en",
                    "task": task,
                    "response_format": "json",
                    "temperature": 0.0,
                }).encode()
                req = urllib.request.Request(
                    f"{self.url}/inference",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )

            resp = urllib.request.urlopen(req, timeout=300)
            data = json.loads(resp.read())

            return {
                "text": data.get("text", ""),
                "language": data.get("language", language or "en"),
                "segments": data.get("segments", []),
                "duration": data.get("duration", 0),
            }
        except Exception as e:
            return {"error": str(e)}

    def list_models(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/load", timeout=5)
            data = json.loads(resp.read())
            return data.get("models", [
                "ggml-base.en", "ggml-base",
                "ggml-small.en", "ggml-small",
                "ggml-medium.en", "ggml-medium",
                "ggml-large-v3",
            ])
        except Exception:
            return [
                "ggml-base.en", "ggml-base",
                "ggml-small.en", "ggml-small",
                "ggml-medium.en", "ggml-medium",
                "ggml-large-v3",
            ]

    def health_check(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/health", timeout=3)
            return resp.status == 200
        except Exception:
            return False


# ============================================================================
# faster-whisper server
# ============================================================================
@register_backend("faster-whisper")
class FasterWhisperBackend(STTBackend):
    def __init__(self, url: str, config: dict = None):
        self.url = url.rstrip("/")

    def transcribe(self, audio_base64=None, audio_url=None, language=None,
                   task="transcribe"):
        if not audio_base64 and not audio_url:
            return {"error": "Provide audio_base64 or audio_url"}

        try:
            if audio_base64:
                payload = json.dumps({
                    "audio": audio_base64,
                    "language": language,
                    "task": task,
                    "beam_size": 5,
                    "vad_filter": True,
                }).encode()
                req = urllib.request.Request(
                    f"{self.url}/v1/audio/transcriptions",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
            else:
                payload = json.dumps({
                    "url": audio_url,
                    "language": language,
                    "task": task,
                    "beam_size": 5,
                    "vad_filter": True,
                }).encode()
                req = urllib.request.Request(
                    f"{self.url}/v1/audio/transcriptions",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )

            resp = urllib.request.urlopen(req, timeout=300)
            data = json.loads(resp.read())

            segments = data.get("segments", [])
            return {
                "text": data.get("text", ""),
                "language": data.get("language", language or "auto"),
                "segments": segments,
                "duration": data.get("duration", 0),
            }
        except Exception as e:
            return {"error": str(e)}

    def list_models(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/v1/models", timeout=5)
            data = json.loads(resp.read())
            return [m.get("id", "") for m in data.get("data", [])]
        except Exception:
            return ["large-v3", "medium", "small", "base", "tiny"]

    def health_check(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/health", timeout=3)
            return resp.status == 200
        except Exception:
            return False

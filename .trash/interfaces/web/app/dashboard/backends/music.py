"""
Music Generation Backend - Abstract + Adapters
Supports: audiocraft, stable-audio, ace-step
"""

import json
import os
import time
import logging
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from .registry import register_backend

log = logging.getLogger("backends.music")


class MusicBackend(ABC):
    """Abstract music generation backend."""

    @abstractmethod
    def generate(self, prompt: str, duration_seconds: int = 30, model: str = None,
                 genre: str = None, mood: str = None, bpm: int = None) -> dict:
        """Generate music. Returns {"audio_path": "...", "url": "...", "duration": N}"""
        ...

    @abstractmethod
    def list_models(self) -> List[str]:
        """List available models."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...


# ============================================================================
# AudioCraft / MusicGen (Meta)
# ============================================================================
@register_backend("audiocraft")
class AudioCraftAdapter(MusicBackend):
    """Adapter for Meta's AudioCraft/MusicGen via Gradio server."""

    def __init__(self, url: str, config: dict = None):
        self.url = url.rstrip("/")
        self.output_dir = config.get("music_output_dir", "/tmp/music_output") if config else "/tmp/music_output"
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(self, prompt, duration_seconds=30, model=None,
                 genre=None, mood=None, bpm=None):
        # Build enriched prompt from optional parameters
        enriched_prompt = self._build_prompt(prompt, genre, mood, bpm)

        # Map duration to model size if not specified
        model_size = model or self._select_model_size(duration_seconds)

        payload = json.dumps({
            "prompt": enriched_prompt,
            "duration": duration_seconds,
            "model_size": model_size,
        }).encode()

        try:
            req = urllib.request.Request(
                f"{self.url}/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=600)
            data = json.loads(resp.read())

            # Handle various response formats
            audio_path = data.get("audio_path") or data.get("path") or data.get("file")
            audio_url = data.get("url") or data.get("audio_url")

            if audio_path:
                return {
                    "audio_path": audio_path,
                    "url": audio_url or f"file://{audio_path}",
                    "duration": duration_seconds,
                    "model": model_size,
                }
            elif audio_url:
                # Download the audio file locally
                local_path = self._download_audio(audio_url, prompt)
                return {
                    "audio_path": local_path,
                    "url": audio_url,
                    "duration": duration_seconds,
                    "model": model_size,
                }
            else:
                return {"error": "No audio returned from server", "raw": data}
        except Exception as e:
            return {"error": str(e)}

    def _build_prompt(self, prompt, genre=None, mood=None, bpm=None):
        """Enrich prompt with genre, mood, and BPM tags."""
        parts = [prompt]
        if genre:
            parts.append(f"Genre: {genre}")
        if mood:
            parts.append(f"Mood: {mood}")
        if bpm:
            parts.append(f"BPM: {bpm}")
        return ", ".join(parts)

    def _select_model_size(self, duration_seconds):
        """Select appropriate model based on duration."""
        if duration_seconds <= 10:
            return "small"
        elif duration_seconds <= 30:
            return "medium"
        else:
            return "large"

    def _download_audio(self, url, prompt):
        """Download audio from URL to local output directory."""
        timestamp = int(time.time())
        safe_name = "".join(c if c.isalnum() else "_" for c in prompt[:30])
        filename = f"audiocraft_{safe_name}_{timestamp}.wav"
        local_path = os.path.join(self.output_dir, filename)

        try:
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=120)
            with open(local_path, "wb") as f:
                f.write(resp.read())
            return local_path
        except Exception as e:
            log.warning(f"Failed to download audio from {url}: {e}")
            return url  # Return original URL if download fails

    def list_models(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/models", timeout=5)
            data = json.loads(resp.read())
            return data.get("models", ["small", "medium", "large", "melody"])
        except Exception:
            return ["small", "medium", "large", "melody"]

    def health_check(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/health", timeout=3)
            return resp.status == 200
        except Exception:
            return False


# ============================================================================
# Stable Audio Open
# ============================================================================
@register_backend("stable-audio")
class StableAudioAdapter(MusicBackend):
    """Adapter for Stability AI's Stable Audio Open."""

    def __init__(self, url: str, config: dict = None):
        self.url = url.rstrip("/")
        self.output_dir = config.get("music_output_dir", "/tmp/music_output") if config else "/tmp/music_output"
        os.makedirs(self.output_dir, exist_ok=True)
        self.api_key = config.get("stability_api_key", "") if config else ""

    def generate(self, prompt, duration_seconds=30, model=None,
                 genre=None, mood=None, bpm=None):
        # Build enriched prompt
        enriched_prompt = self._build_prompt(prompt, genre, mood, bpm)

        payload = json.dumps({
            "prompt": enriched_prompt,
            "duration": duration_seconds,
            "model": model or "stable-audio-open",
            "steps": 100,
            "cfg_scale": 7.0,
            "seed": int(time.time()) % (2**32),
        }).encode()

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            req = urllib.request.Request(
                f"{self.url}/generate",
                data=payload,
                headers=headers,
            )
            resp = urllib.request.urlopen(req, timeout=600)
            data = json.loads(resp.read())

            audio_path = data.get("audio_path") or data.get("path") or data.get("file")
            audio_url = data.get("url") or data.get("audio_url")

            if audio_path:
                return {
                    "audio_path": audio_path,
                    "url": audio_url or f"file://{audio_path}",
                    "duration": duration_seconds,
                    "model": model or "stable-audio-open",
                }
            elif audio_url:
                local_path = self._download_audio(audio_url, prompt)
                return {
                    "audio_path": local_path,
                    "url": audio_url,
                    "duration": duration_seconds,
                    "model": model or "stable-audio-open",
                }
            else:
                return {"error": "No audio returned from server", "raw": data}
        except Exception as e:
            return {"error": str(e)}

    def _build_prompt(self, prompt, genre=None, mood=None, bpm=None):
        parts = [prompt]
        if genre:
            parts.append(f"Genre: {genre}")
        if mood:
            parts.append(f"Mood: {mood}")
        if bpm:
            parts.append(f"{bpm} BPM")
        return ", ".join(parts)

    def _download_audio(self, url, prompt):
        timestamp = int(time.time())
        safe_name = "".join(c if c.isalnum() else "_" for c in prompt[:30])
        filename = f"stable_audio_{safe_name}_{timestamp}.wav"
        local_path = os.path.join(self.output_dir, filename)

        try:
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=120)
            with open(local_path, "wb") as f:
                f.write(resp.read())
            return local_path
        except Exception as e:
            log.warning(f"Failed to download audio from {url}: {e}")
            return url

    def list_models(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/models", timeout=5)
            data = json.loads(resp.read())
            return data.get("models", ["stable-audio-open"])
        except Exception:
            return ["stable-audio-open"]

    def health_check(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/health", timeout=3)
            return resp.status == 200
        except Exception:
            return False


# ============================================================================
# ACE-Step (if available)
# ============================================================================
@register_backend("ace-step")
class ACEStepAdapter(MusicBackend):
    """Adapter for ACE-Step music generation model."""

    def __init__(self, url: str, config: dict = None):
        self.url = url.rstrip("/")
        self.output_dir = config.get("music_output_dir", "/tmp/music_output") if config else "/tmp/music_output"
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(self, prompt, duration_seconds=30, model=None,
                 genre=None, mood=None, bpm=None):
        # Build enriched prompt
        enriched_prompt = self._build_prompt(prompt, genre, mood, bpm)

        payload = json.dumps({
            "prompt": enriched_prompt,
            "duration": duration_seconds,
            "model": model or "ace-step-v1",
            "bpm": bpm or 120,
        }).encode()

        try:
            req = urllib.request.Request(
                f"{self.url}/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=600)
            data = json.loads(resp.read())

            audio_path = data.get("audio_path") or data.get("path") or data.get("file")
            audio_url = data.get("url") or data.get("audio_url")

            if audio_path:
                return {
                    "audio_path": audio_path,
                    "url": audio_url or f"file://{audio_path}",
                    "duration": duration_seconds,
                    "model": model or "ace-step-v1",
                }
            elif audio_url:
                local_path = self._download_audio(audio_url, prompt)
                return {
                    "audio_path": local_path,
                    "url": audio_url,
                    "duration": duration_seconds,
                    "model": model or "ace-step-v1",
                }
            else:
                return {"error": "No audio returned from server", "raw": data}
        except Exception as e:
            return {"error": str(e)}

    def _build_prompt(self, prompt, genre=None, mood=None, bpm=None):
        parts = [prompt]
        if genre:
            parts.append(f"Genre: {genre}")
        if mood:
            parts.append(f"Mood: {mood}")
        if bpm:
            parts.append(f"{bpm} BPM")
        return ", ".join(parts)

    def _download_audio(self, url, prompt):
        timestamp = int(time.time())
        safe_name = "".join(c if c.isalnum() else "_" for c in prompt[:30])
        filename = f"ace_step_{safe_name}_{timestamp}.wav"
        local_path = os.path.join(self.output_dir, filename)

        try:
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=120)
            with open(local_path, "wb") as f:
                f.write(resp.read())
            return local_path
        except Exception as e:
            log.warning(f"Failed to download audio from {url}: {e}")
            return url

    def list_models(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/models", timeout=5)
            data = json.loads(resp.read())
            return data.get("models", ["ace-step-v1"])
        except Exception:
            return ["ace-step-v1"]

    def health_check(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/health", timeout=3)
            return resp.status == 200
        except Exception:
            return False

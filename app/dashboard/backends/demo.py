"""
Provider-free offline fallback backends for development and CI.

These adapters deliberately return deterministic local assets. They do not
contact external services, require API keys, or download models. They are not
the product path; production use should route to configured local/API providers.
"""

import subprocess
import time
from pathlib import Path
from typing import List

from .registry import register_backend


class _DemoBase:
    def __init__(self, url: str = "", config: dict = None):
        self.url = url
        self.config = config or {}

    def health_check(self) -> bool:
        return True

    def _exports_dir(self) -> Path:
        directory = Path(self.config.get("studio_mount", "")) if self.config.get("studio_mount") else None
        if not directory:
            import os
            directory = Path(os.environ.get("STUDIO_MOUNT", "/mnt/studio"))
        exports = directory / "exports"
        exports.mkdir(parents=True, exist_ok=True)
        return exports


@register_backend("demo-text")
class DemoTextBackend(_DemoBase):
    def generate(self, prompt: str, model: str = None, system: str = "",
                 max_tokens: int = 2048, temperature: float = 0.7) -> dict:
        return {
            "response": (
                "Offline fallback: Canon OS turns the supplied brand image and "
                "campaign brief into a consistent launch campaign draft."
            ),
            "model": model or "demo-text-fixture",
            "tokens": 18,
            "provenance": "Offline fallback — no provider contacted",
        }

    def list_models(self) -> List[str]:
        return ["demo-text-fixture"]


@register_backend("demo-image")
class DemoImageBackend(_DemoBase):
    def generate(self, prompt: str, model: str = None, negative: str = "",
                 width: int = 1024, height: int = 1024, steps: int = 25,
                 cfg: float = 7.5, seed: int = -1,
                 input_image: str = None, mask_image: str = None,
                 mode: str = "txt2img") -> dict:
        return {
            "images": ["demo-image-fixture.png"],
            "prompt_id": "demo-image-fixture",
            "provenance": "Offline fallback — no provider contacted",
        }

    def list_models(self) -> List[str]:
        return ["demo-image-fixture"]

    def get_queue(self) -> dict:
        return {"queue_running": [], "queue_pending": []}


@register_backend("demo-video")
class DemoVideoBackend(_DemoBase):
    def generate(self, prompt: str, model: str = None, negative: str = "",
                 width: int = 672, height: int = 384, frames: int = 49,
                 steps: int = 30, cfg: float = 7.0, seed: int = -1,
                 fps: int = 8, input_image: str = None,
                 mode: str = "txt2vid") -> dict:
        destination = self._exports_dir() / f"demo-video-{int(time.time() * 1000)}.mp4"
        completed = subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=#1d2440:s=320x180:r=8:d=3",
             "-vf", "drawtext=text='Canon OS offline scene':fontcolor=white:fontsize=18:x=(w-text_w)/2:y=(h-text_h)/2",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", str(destination)],
            capture_output=True, text=True, check=False,
        )
        if completed.returncode != 0:
            return {"error": f"DEMO_VIDEO_FAILED: {completed.stderr[-300:]}"}
        return {
            "video": str(destination),
            "frames": frames,
            "provenance": "Offline fallback — no provider contacted",
        }

    def list_models(self) -> List[str]:
        return ["demo-video-fixture"]

    def get_queue(self) -> dict:
        return {"queue_running": [], "queue_pending": []}


@register_backend("demo-tts")
class DemoTTSBackend(_DemoBase):
    def synthesize(self, text: str, voice: str = None, language: str = "en",
                   speed: float = 1.0, output_format: str = "wav") -> dict:
        destination = self._exports_dir() / f"demo-voice-{int(time.time() * 1000)}.wav"
        completed = subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", str(destination)],
            capture_output=True, text=True, check=False,
        )
        if completed.returncode != 0:
            return {"error": f"DEMO_TTS_FAILED: {completed.stderr[-300:]}"}
        return {
            "audio_path": str(destination),
            "format": output_format,
            "duration": 2,
            "provenance": "Offline fallback — no provider contacted",
        }

    def list_voices(self) -> List[str]:
        return ["demo-voice"]


@register_backend("demo-music")
class DemoMusicBackend(_DemoBase):
    def generate(self, prompt: str, duration_seconds: int = 30, model: str = None,
                 genre: str = None, mood: str = None, bpm: int = None) -> dict:
        destination = self._exports_dir() / f"demo-music-{int(time.time() * 1000)}.wav"
        completed = subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency=220:duration={duration_seconds}",
             str(destination)],
            capture_output=True, text=True, check=False,
        )
        if completed.returncode != 0:
            return {"error": f"DEMO_MUSIC_FAILED: {completed.stderr[-300:]}"}
        return {"audio_path": str(destination), "duration": duration_seconds,
                "provenance": "Offline fallback — no provider contacted"}

    def list_models(self) -> List[str]:
        return ["demo-music-fixture"]


@register_backend("demo-stt")
class DemoSTTBackend(_DemoBase):
    def transcribe(self, audio_base64: str = None, audio_url: str = None,
                   language: str = None, task: str = "transcribe") -> dict:
        return {
            "text": "Offline fallback transcription.",
            "language": language or "en",
            "segments": [],
            "provenance": "Offline fallback — no provider contacted",
        }

    def list_models(self) -> List[str]:
        return ["demo-stt-fixture"]

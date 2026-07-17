"""
Provider-free demo backends for the hackathon judge path.

These adapters deliberately return deterministic fixture metadata. They do not
contact external services, require API keys, or download models.
"""

from typing import List

from .registry import register_backend


class _DemoBase:
    def __init__(self, url: str = "", config: dict = None):
        self.url = url
        self.config = config or {}

    def health_check(self) -> bool:
        return True


@register_backend("demo-text")
class DemoTextBackend(_DemoBase):
    def generate(self, prompt: str, model: str = None, system: str = "",
                 max_tokens: int = 2048, temperature: float = 0.7) -> dict:
        return {
            "response": (
                "Demo fixture: Canon OS turns the supplied brand image and "
                "campaign brief into a consistent launch campaign draft."
            ),
            "model": model or "demo-text-fixture",
            "tokens": 18,
            "provenance": "Demo fixture — no provider contacted",
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
            "provenance": "Demo fixture — no provider contacted",
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
        return {
            "images": ["demo-video-fixture.webp"],
            "video": "demo-video-fixture.webp",
            "frames": frames,
            "provenance": "Demo fixture — no provider contacted",
        }

    def list_models(self) -> List[str]:
        return ["demo-video-fixture"]

    def get_queue(self) -> dict:
        return {"queue_running": [], "queue_pending": []}


@register_backend("demo-tts")
class DemoTTSBackend(_DemoBase):
    def synthesize(self, text: str, voice: str = None, language: str = "en",
                   speed: float = 1.0, output_format: str = "wav") -> dict:
        return {
            "audio_base64": "",
            "format": output_format,
            "duration": 0,
            "provenance": "Demo fixture — no provider contacted",
        }

    def list_voices(self) -> List[str]:
        return ["demo-voice"]


@register_backend("demo-music")
class DemoMusicBackend(_DemoBase):
    def generate(self, prompt: str, duration_seconds: int = 30, model: str = None,
                 genre: str = None, mood: str = None, bpm: int = None) -> dict:
        return {"audio_path": "demo-music-fixture.wav", "duration": duration_seconds,
                "provenance": "Demo fixture — no provider contacted"}

    def list_models(self) -> List[str]:
        return ["demo-music-fixture"]


@register_backend("demo-stt")
class DemoSTTBackend(_DemoBase):
    def transcribe(self, audio_base64: str = None, audio_url: str = None,
                   language: str = None, task: str = "transcribe") -> dict:
        return {
            "text": "Demo fixture transcription.",
            "language": language or "en",
            "segments": [],
            "provenance": "Demo fixture — no provider contacted",
        }

    def list_models(self) -> List[str]:
        return ["demo-stt-fixture"]

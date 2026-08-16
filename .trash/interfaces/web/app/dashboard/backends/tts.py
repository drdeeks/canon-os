"""
Text-to-Speech Backend - Abstract + Adapters
Supports: kokoro, coqui, bark
"""

import json
import base64
import urllib.request
from abc import ABC, abstractmethod
from typing import List
from .registry import register_backend


class TTSBackend(ABC):
    """Abstract text-to-speech backend."""

    @abstractmethod
    def synthesize(self, text: str, voice: str = None, language: str = "en",
                   speed: float = 1.0, output_format: str = "wav") -> dict:
        """Synthesize speech. Returns {"audio_base64": "...", "format": "wav", "duration": N}"""
        ...

    @abstractmethod
    def list_voices(self) -> List[str]:
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...


# ============================================================================
# Kokoro TTS
# ============================================================================
@register_backend("kokoro")
class KokoroBackend(TTSBackend):
    def __init__(self, url: str, config: dict = None):
        self.url = url.rstrip("/")

    def synthesize(self, text, voice=None, language="en", speed=1.0,
                   output_format="wav"):
        payload = json.dumps({
            "model": "kokoro",
            "input": text,
            "voice": voice or "af_alloy",
            "language": language,
            "speed": speed,
            "response_format": output_format,
        }).encode()

        try:
            req = urllib.request.Request(
                f"{self.url}/v1/audio/speech",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=120)
            audio_data = resp.read()
            return {
                "audio_base64": base64.b64encode(audio_data).decode(),
                "format": output_format,
                "size": len(audio_data),
            }
        except Exception as e:
            return {"error": str(e)}

    def list_voices(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/v1/audio/voices", timeout=5)
            data = json.loads(resp.read())
            return data.get("voices", [])
        except Exception:
            return [
                "af_alloy", "af_aoede", "af_bella", "af_heart", "af_jessica",
                "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah",
                "af_sky", "am_adam", "am_echo", "am_eric", "am_fenrir",
                "am_liam", "am_michael", "am_onyx", "am_puck", "am_santa",
            ]

    def health_check(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/health", timeout=3)
            return resp.status == 200
        except Exception:
            return False


# ============================================================================
# Coqui TTS
# ============================================================================
@register_backend("coqui")
class CoquiBackend(TTSBackend):
    def __init__(self, url: str, config: dict = None):
        self.url = url.rstrip("/")

    def synthesize(self, text, voice=None, language="en", speed=1.0,
                   output_format="wav"):
        payload = json.dumps({
            "text": text,
            "speaker_id": voice or "",
            "language_id": language,
            "speed": speed,
        }).encode()

        try:
            req = urllib.request.Request(
                f"{self.url}/api/tts",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=120)
            audio_data = resp.read()
            return {
                "audio_base64": base64.b64encode(audio_data).decode(),
                "format": output_format,
                "size": len(audio_data),
            }
        except Exception as e:
            return {"error": str(e)}

    def list_voices(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/api/speakers", timeout=5)
            data = json.loads(resp.read())
            return [s.get("name", s.get("id", "")) for s in data.get("speakers", [])]
        except Exception:
            return []

    def health_check(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/api/health", timeout=3)
            return resp.status == 200
        except Exception:
            return False


# ============================================================================
# Bark TTS
# ============================================================================
@register_backend("bark")
class BarkBackend(TTSBackend):
    def __init__(self, url: str, config: dict = None):
        self.url = url.rstrip("/")

    # Bark speaker presets
    SPEAKERS = [
        "v2/en_speaker_0", "v2/en_speaker_1", "v2/en_speaker_2",
        "v2/en_speaker_3", "v2/en_speaker_4", "v2/en_speaker_5",
        "v2/en_speaker_6", "v2/en_speaker_7", "v2/en_speaker_8",
        "v2/en_speaker_9",
    ]

    def synthesize(self, text, voice=None, language="en", speed=1.0,
                   output_format="wav"):
        payload = json.dumps({
            "text": text,
            "voice_preset": voice or "v2/en_speaker_6",
            "text_temp": 0.7,
            "waveform_temp": 0.7,
        }).encode()

        try:
            req = urllib.request.Request(
                f"{self.url}/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=120)
            audio_data = resp.read()
            return {
                "audio_base64": base64.b64encode(audio_data).decode(),
                "format": output_format,
                "size": len(audio_data),
            }
        except Exception as e:
            return {"error": str(e)}

    def list_voices(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/speakers", timeout=5)
            data = json.loads(resp.read())
            return data.get("speakers", self.SPEAKERS)
        except Exception:
            return self.SPEAKERS

    def health_check(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/health", timeout=3)
            return resp.status == 200
        except Exception:
            return False

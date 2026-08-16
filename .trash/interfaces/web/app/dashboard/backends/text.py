"""
Text Generation Backend - Abstract + Adapters
Supports: llama-cpp, ollama, vllm, openai-compatible
"""

import json
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from .registry import register_backend


class TextBackend(ABC):
    """Abstract text generation backend."""

    @abstractmethod
    def generate(self, prompt: str, model: str = None, system: str = "",
                 max_tokens: int = 2048, temperature: float = 0.7) -> dict:
        """Generate text. Returns {"response": "...", "model": "...", "tokens": N}"""
        ...

    @abstractmethod
    def list_models(self) -> List[str]:
        """List available models."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...


# ============================================================================
# llama.cpp server (OpenAI-compatible /v1/chat/completions)
# ============================================================================
@register_backend("llama-cpp")
class LlamaCppBackend(TextBackend):
    def __init__(self, url: str, config: dict = None):
        self.url = url.rstrip("/")

    def generate(self, prompt, model=None, system="", max_tokens=2048, temperature=0.7):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = json.dumps({
            "model": model or "default",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode()

        try:
            req = urllib.request.Request(
                f"{self.url}/v1/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=300)
            data = json.loads(resp.read())
            choice = data.get("choices", [{}])[0]
            usage = data.get("usage", {})
            return {
                "response": choice.get("message", {}).get("content", ""),
                "model": data.get("model", model),
                "tokens": usage.get("completion_tokens", 0),
            }
        except Exception as e:
            return {"error": str(e)}

    def list_models(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/v1/models", timeout=5)
            data = json.loads(resp.read())
            return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    def health_check(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/health", timeout=3)
            return resp.status == 200
        except Exception:
            return False


# ============================================================================
# Ollama (/api/generate)
# ============================================================================
@register_backend("ollama")
class OllamaBackend(TextBackend):
    def __init__(self, url: str, config: dict = None):
        self.url = url.rstrip("/")

    def generate(self, prompt, model=None, system="", max_tokens=2048, temperature=0.7):
        payload = json.dumps({
            "model": model or "llama3.1",
            "system": system,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": temperature},
        }).encode()
        try:
            req = urllib.request.Request(
                f"{self.url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=300)
            data = json.loads(resp.read())
            return {
                "response": data.get("response", ""),
                "model": data.get("model", model),
                "tokens": data.get("eval_count", 0),
            }
        except Exception as e:
            return {"error": str(e)}

    def list_models(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/api/tags", timeout=5)
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def health_check(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/api/tags", timeout=3)
            return resp.status == 200
        except Exception:
            return False


# ============================================================================
# vLLM (OpenAI-compatible /v1/chat/completions)
# ============================================================================
@register_backend("vllm")
class VLLMBackend(TextBackend):
    def __init__(self, url: str, config: dict = None):
        self.url = url.rstrip("/")

    def generate(self, prompt, model=None, system="", max_tokens=2048, temperature=0.7):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = json.dumps({
            "model": model or "default",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode()
        try:
            req = urllib.request.Request(
                f"{self.url}/v1/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=300)
            data = json.loads(resp.read())
            choice = data.get("choices", [{}])[0]
            usage = data.get("usage", {})
            return {
                "response": choice.get("message", {}).get("content", ""),
                "model": data.get("model", model),
                "tokens": usage.get("completion_tokens", 0),
            }
        except Exception as e:
            return {"error": str(e)}

    def list_models(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/v1/models", timeout=5)
            data = json.loads(resp.read())
            return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    def health_check(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/health", timeout=3)
            return resp.status == 200
        except Exception:
            return False


# ============================================================================
# OpenAI-compatible generic (any server with /v1/chat/completions)
# ============================================================================
@register_backend("openai")
class OpenAICompatibleBackend(TextBackend):
    def __init__(self, url: str, config: dict = None):
        self.url = url.rstrip("/")
        self.api_key = config.get("openai_api_key", "") if config else ""

    def generate(self, prompt, model=None, system="", max_tokens=2048, temperature=0.7):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = json.dumps({
            "model": model or "gpt-3.5-turbo",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode()

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            req = urllib.request.Request(
                f"{self.url}/chat/completions",
                data=payload,
                headers=headers,
            )
            resp = urllib.request.urlopen(req, timeout=300)
            data = json.loads(resp.read())
            choice = data.get("choices", [{}])[0]
            usage = data.get("usage", {})
            return {
                "response": choice.get("message", {}).get("content", ""),
                "model": data.get("model", model),
                "tokens": usage.get("completion_tokens", 0),
            }
        except Exception as e:
            return {"error": str(e)}

    def list_models(self):
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            req = urllib.request.Request(f"{self.url}/models", headers=headers)
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    def health_check(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/models", timeout=3)
            return resp.status == 200
        except Exception:
            return False

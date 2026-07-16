"""
Image Generation Backend - Abstract + Adapters
Supports: comfyui, automatic1111, forge
"""

import json
import time
import urllib.request
from abc import ABC, abstractmethod
from typing import List
from .registry import register_backend


class ImageBackend(ABC):
    @abstractmethod
    def generate(self, prompt: str, model: str = None, negative: str = "",
                 width: int = 1024, height: int = 1024, steps: int = 25,
                 cfg: float = 7.5, seed: int = -1,
                 input_image: str = None, mode: str = "txt2img") -> dict:
        """Generate image. Returns {"url": "...", "images": [...]}"""
        ...

    @abstractmethod
    def list_models(self) -> List[str]:
        ...

    @abstractmethod
    def get_queue(self) -> dict:
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...


# ============================================================================
# ComfyUI
# ============================================================================
@register_backend("comfyui")
class ComfyUIBackend(ImageBackend):
    def __init__(self, url: str, config: dict = None):
        self.url = url.rstrip("/")
        self.client_id = "studio-dashboard"

    def generate(self, prompt, model=None, negative="", width=1024, height=1024,
                 steps=25, cfg=7.5, seed=-1, input_image=None, mode="txt2img"):
        if seed < 0:
            seed = int(time.time()) % (2**32)

        if mode == "img2img" and input_image:
            workflow = self._img2img_workflow(prompt, model, negative, width, height,
                                              steps, cfg, seed, input_image)
        else:
            workflow = self._txt2img_workflow(prompt, model, negative, width, height,
                                              steps, cfg, seed)

        return self._submit_and_wait(workflow)

    def _txt2img_workflow(self, prompt, model, negative, width, height, steps, cfg, seed):
        return {
            "3": {"class_type": "KSampler", "inputs": {
                "seed": seed, "steps": steps, "cfg": cfg,
                "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0,
                "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
                "latent_image": ["5", 0],
            }},
            "4": {"class_type": "CheckpointLoaderSimple",
                  "inputs": {"ckpt_name": model or "sd_xl_base_1.0.safetensors"}},
            "5": {"class_type": "EmptyLatentImage",
                  "inputs": {"width": width, "height": height, "batch_size": 1}},
            "6": {"class_type": "CLIPTextEncode",
                  "inputs": {"text": prompt, "clip": ["4", 1]}},
            "7": {"class_type": "CLIPTextEncode",
                  "inputs": {"text": negative or "blurry, low quality", "clip": ["4", 1]}},
            "8": {"class_type": "VAEDecode",
                  "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage",
                  "inputs": {"filename_prefix": f"studio_{seed}", "images": ["8", 0]}},
        }

    def _img2img_workflow(self, prompt, model, negative, width, height, steps, cfg, seed, input_image):
        return {
            "3": {"class_type": "KSampler", "inputs": {
                "seed": seed, "steps": steps, "cfg": cfg,
                "sampler_name": "euler", "scheduler": "normal", "denoise": 0.65,
                "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
                "latent_image": ["10", 0],
            }},
            "4": {"class_type": "CheckpointLoaderSimple",
                  "inputs": {"ckpt_name": model or "sd_xl_base_1.0.safetensors"}},
            "6": {"class_type": "CLIPTextEncode",
                  "inputs": {"text": prompt, "clip": ["4", 1]}},
            "7": {"class_type": "CLIPTextEncode",
                  "inputs": {"text": negative or "blurry, low quality", "clip": ["4", 1]}},
            "9": {"class_type": "LoadImage",
                  "inputs": {"image": input_image}},
            "10": {"class_type": "VAEEncode",
                   "inputs": {"pixels": ["9", 0], "vae": ["4", 2]}},
            "11": {"class_type": "VAEDecode",
                   "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "12": {"class_type": "SaveImage",
                   "inputs": {"filename_prefix": f"studio_{seed}", "images": ["11", 0]}},
        }

    def _submit_and_wait(self, workflow, timeout=600):
        payload = json.dumps({"prompt": workflow, "client_id": self.client_id}).encode()
        try:
            req = urllib.request.Request(f"{self.url}/prompt", data=payload,
                headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read())
            prompt_id = result.get("prompt_id")
            if not prompt_id:
                return {"error": "No prompt_id returned"}

            # Poll until done
            start = time.time()
            while time.time() - start < timeout:
                hist = urllib.request.urlopen(f"{self.url}/history/{prompt_id}", timeout=10)
                history = json.loads(hist.read())
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    images = []
                    for node_out in outputs.values():
                        for img in node_out.get("images", []):
                            images.append(img.get("filename", ""))
                    return {"images": images, "prompt_id": prompt_id}
                time.sleep(2)
            return {"error": "Timeout"}
        except Exception as e:
            return {"error": str(e)}

    def list_models(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/object_info/CheckpointLoaderSimple", timeout=10)
            data = json.loads(resp.read())
            info = data.get("CheckpointLoaderSimple", {})
            models = info.get("input", {}).get("required", {}).get("ckpt_name", [[]])
            return models[0] if models else []
        except Exception:
            return []

    def get_queue(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/queue", timeout=5)
            return json.loads(resp.read())
        except Exception:
            return {"queue_running": [], "queue_pending": []}

    def health_check(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/", timeout=3)
            return resp.status == 200
        except Exception:
            return False


# ============================================================================
# Automatic1111 / Forge
# ============================================================================
@register_backend("automatic1111")
class A1111Backend(ImageBackend):
    def __init__(self, url: str, config: dict = None):
        self.url = url.rstrip("/")

    def generate(self, prompt, model=None, negative="", width=1024, height=1024,
                 steps=25, cfg=7.5, seed=-1, input_image=None, mode="txt2img"):
        endpoint = "img2img" if mode == "img2img" and input_image else "txt2img"
        payload = {
            "prompt": prompt,
            "negative_prompt": negative,
            "width": width, "height": height,
            "steps": steps, "cfg_scale": cfg,
            "seed": seed if seed >= 0 else -1,
        }
        if model:
            payload["override_settings"] = {"sd_model_checkpoint": model}
        if mode == "img2img" and input_image:
            payload["init_images"] = [input_image]  # base64

        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(f"{self.url}/sdapi/v1/{endpoint}", data=data,
                headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=600)
            result = json.loads(resp.read())
            images = result.get("images", [])
            return {"images_base64": images}
        except Exception as e:
            return {"error": str(e)}

    def list_models(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/sdapi/v1/sd-models", timeout=5)
            data = json.loads(resp.read())
            return [m["title"] for m in data]
        except Exception:
            return []

    def get_queue(self):
        return {"queue_running": [], "queue_pending": []}

    def health_check(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/sdapi/v1/memory", timeout=3)
            return resp.status == 200
        except Exception:
            return False

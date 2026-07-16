"""
Video Generation Backend - Abstract + Adapters
Supports: comfyui (CogVideoX/SVD), animatediff
"""

import json
import time
import urllib.request
from abc import ABC, abstractmethod
from typing import List
from .registry import register_backend


class VideoBackend(ABC):
    """Abstract video generation backend."""

    @abstractmethod
    def generate(self, prompt: str, model: str = None, negative: str = "",
                 width: int = 672, height: int = 384, frames: int = 49,
                 steps: int = 30, cfg: float = 7.0, seed: int = -1,
                 fps: int = 8, input_image: str = None, mode: str = "txt2vid") -> dict:
        """Generate video. Returns {"images": [...], "video": "...", "frames": N}"""
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
# ComfyUI - CogVideoX / Stable Video Diffusion workflows
# ============================================================================
@register_backend("comfyui-video")
class ComfyUIVideoBackend(VideoBackend):
    def __init__(self, url: str, config: dict = None):
        self.url = url.rstrip("/")
        self.client_id = "studio-dashboard"

    def generate(self, prompt, model=None, negative="", width=672, height=384,
                 frames=49, steps=30, cfg=7.0, seed=-1, fps=8,
                 input_image=None, mode="txt2vid"):
        if seed < 0:
            seed = int(time.time()) % (2**32)

        model_name = model or "cogvideox"

        if "svd" in model_name.lower() or mode == "img2vid":
            workflow = self._svd_workflow(prompt, negative, width, height,
                                          frames, steps, cfg, seed, fps,
                                          input_image)
        else:
            workflow = self._cogvideox_workflow(prompt, negative, width, height,
                                                frames, steps, cfg, seed, fps)

        return self._submit_and_wait(workflow)

    def _cogvideox_workflow(self, prompt, negative, width, height, frames,
                            steps, cfg, seed, fps):
        """Build a CogVideoX text-to-video workflow for ComfyUI."""
        return {
            "1": {"class_type": "CogVideoTextEncode", "inputs": {
                "text": prompt,
                "clip": ["3", 0],
            }},
            "2": {"class_type": "CogVideoTextEncode", "inputs": {
                "text": negative or "blurry, low quality, watermark",
                "clip": ["3", 0],
            }},
            "3": {"class_type": "CogVideoLoader", "inputs": {
                "ckpt_name": "cogvideox_5b.safetensors",
            }},
            "4": {"class_type": "CogVideoSampler", "inputs": {
                "seed": seed, "steps": steps, "cfg": cfg,
                "positive": ["1", 0], "negative": ["2", 0],
                "model": ["3", 0], "width": width, "height": height,
                "num_frames": frames,
            }},
            "5": {"class_type": "CogVideoDecode", "inputs": {
                "samples": ["4", 0], "vae": ["3", 1],
            }},
            "6": {"class_type": "SaveAnimatedWEBP", "inputs": {
                "filename_prefix": f"video_{seed}",
                "fps": fps,
                "images": ["5", 0],
            }},
        }

    def _svd_workflow(self, prompt, negative, width, height, frames, steps,
                      cfg, seed, fps, input_image):
        """Build a Stable Video Diffusion img2vid workflow for ComfyUI."""
        nodes = {
            "1": {"class_type": "ImageOnlyCheckpointLoader", "inputs": {
                "ckpt_name": "svd_xt.safetensors",
            }},
            "2": {"class_type": "CLIPVisionEncode", "inputs": {
                "clip_vision": ["1", 1],
                "image": ["8", 0],
            }},
            "3": {"class_type": "ImageOnlyCheckpointLoader", "inputs": {
                "ckpt_name": "svd_xt.safetensors",
            }},
            "4": {"class_type": "VideoLinearCFGGuidance", "inputs": {
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative_conditioning": ["2", 0],
                "min_cfg": 1.0,
            }},
            "5": {"class_type": "SVD_img2vid_Conditioning", "inputs": {
                "clip_vision": ["1", 1],
                "init_image": ["8", 0],
                "vae": ["1", 2],
                "width": width,
                "height": height,
                "video_frames": frames,
                "motion_bucket_id": 127,
                "fps": fps,
                "augmentation_level": 0.0,
            }},
            "6": {"class_type": "KSampler", "inputs": {
                "seed": seed, "steps": steps, "cfg": cfg,
                "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["5", 0],
                "negative": ["5", 1],
                "latent_image": ["5", 2],
            }},
            "7": {"class_type": "VAEDecode", "inputs": {
                "samples": ["6", 0],
                "vae": ["1", 2],
            }},
        }
        if input_image:
            nodes["8"] = {"class_type": "LoadImage",
                          "inputs": {"image": input_image}}
        else:
            nodes["8"] = {"class_type": "EmptyLatentImage",
                          "inputs": {"width": width, "height": height,
                                     "batch_size": 1}}

        nodes["9"] = {"class_type": "SaveAnimatedWEBP", "inputs": {
            "filename_prefix": f"svd_{seed}",
            "fps": fps,
            "images": ["7", 0],
        }}
        return nodes

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
                    videos = []
                    for node_out in outputs.values():
                        for img in node_out.get("images", []):
                            images.append(img.get("filename", ""))
                        for vid in node_out.get("gifs", []):
                            videos.append(vid.get("filename", ""))
                    return {
                        "images": images,
                        "videos": videos,
                        "prompt_id": prompt_id,
                        "frames": len(images) if images else 0,
                    }
                time.sleep(2)
            return {"error": "Timeout"}
        except Exception as e:
            return {"error": str(e)}

    def list_models(self):
        try:
            resp = urllib.request.urlopen(f"{self.url}/object_info/CogVideoLoader", timeout=10)
            data = json.loads(resp.read())
            info = data.get("CogVideoLoader", {})
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
# AnimateDiff
# ============================================================================
@register_backend("animatediff")
class AnimateDiffBackend(VideoBackend):
    def __init__(self, url: str, config: dict = None):
        self.url = url.rstrip("/")
        self.client_id = "studio-dashboard"

    def generate(self, prompt, model=None, negative="", width=512, height=512,
                 frames=16, steps=30, cfg=7.5, seed=-1, fps=8,
                 input_image=None, mode="txt2vid"):
        if seed < 0:
            seed = int(time.time()) % (2**32)

        workflow = self._animatediff_workflow(prompt, negative, width, height,
                                              frames, steps, cfg, seed, fps)
        return self._submit_and_wait(workflow)

    def _animatediff_workflow(self, prompt, negative, width, height, frames,
                              steps, cfg, seed, fps):
        """Build an AnimateDiff video generation workflow for ComfyUI."""
        return {
            "1": {"class_type": "CheckpointLoaderSimple", "inputs": {
                "ckpt_name": "animatediffMotion_v15.ckpt",
            }},
            "2": {"class_type": "CLIPTextEncode", "inputs": {
                "text": prompt,
                "clip": ["1", 1],
            }},
            "3": {"class_type": "CLIPTextEncode", "inputs": {
                "text": negative or "blurry, low quality, static, still",
                "clip": ["1", 1],
            }},
            "4": {"class_type": "EmptyLatentImage", "inputs": {
                "width": width, "height": height, "batch_size": frames,
            }},
            "5": {"class_type": "AnimateDiffLoader", "inputs": {
                "model_name": "mm_sd_v15_v2.ckpt",
                "beta_schedule": "sqrt_linear",
                "context_length": 16,
                "context_stride": 1,
                "closed_loop": False,
            }},
            "6": {"class_type": "KSampler", "inputs": {
                "seed": seed, "steps": steps, "cfg": cfg,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal", "denoise": 1.0,
                "model": ["5", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
            }},
            "7": {"class_type": "VAEDecode", "inputs": {
                "samples": ["6", 0],
                "vae": ["1", 2],
            }},
            "8": {"class_type": "SaveAnimatedWEBP", "inputs": {
                "filename_prefix": f"animatediff_{seed}",
                "fps": fps,
                "images": ["7", 0],
            }},
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

            start = time.time()
            while time.time() - start < timeout:
                hist = urllib.request.urlopen(f"{self.url}/history/{prompt_id}", timeout=10)
                history = json.loads(hist.read())
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    images = []
                    videos = []
                    for node_out in outputs.values():
                        for img in node_out.get("images", []):
                            images.append(img.get("filename", ""))
                        for vid in node_out.get("gifs", []):
                            videos.append(vid.get("filename", ""))
                    return {
                        "images": images,
                        "videos": videos,
                        "prompt_id": prompt_id,
                        "frames": len(images) if images else 0,
                    }
                time.sleep(2)
            return {"error": "Timeout"}
        except Exception as e:
            return {"error": str(e)}

    def list_models(self):
        try:
            resp = urllib.request.urlopen(
                f"{self.url}/object_info/AnimateDiffLoader", timeout=10)
            data = json.loads(resp.read())
            info = data.get("AnimateDiffLoader", {})
            models = info.get("input", {}).get("required", {}).get("model_name", [[]])
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

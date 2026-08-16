"""Functional contracts for the Phase 1 Core AI Engine."""

import base64
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "app" / "dashboard"))

from core_ai import (  # noqa: E402
    CoreAIError,
    assemble_mp4,
    build_storyboard,
    check_brand_consistency,
    checksum_asset,
    extract_brand,
    generate_audio,
    generate_script,
    inpaint,
    render_scenes,
    transcribe_audio,
)
import app as dashboard_app  # noqa: E402
from backends import BackendRegistry  # noqa: E402

app = dashboard_app.app


class FakeVideo:
    def generate(self, **kwargs):
        return {"video": f"scene-{kwargs['prompt'][:5]}.mp4", "provenance": "fake"}


class FakeTTS:
    def synthesize(self, **kwargs):
        return {"audio_base64": "ZmFrZQ==", "format": "wav"}


class FakeMusic:
    def generate(self, **kwargs):
        return {"audio_path": "music.wav", "duration": kwargs["duration_seconds"]}


class FakeSTT:
    def transcribe(self, **kwargs):
        return {"text": "Canonical transcript", "language": "en"}


class FakeImage:
    def generate(self, **kwargs):
        image = Image.new("RGB", (8, 8), "#224466")
        encoded = io.BytesIO()
        image.save(encoded, format="PNG")
        return {"images_base64": [base64.b64encode(encoded.getvalue()).decode()]}


class FakeRegistry:
    video = FakeVideo()
    tts = FakeTTS()
    music = FakeMusic()
    stt = FakeSTT()
    image = FakeImage()

    def catalog(self):
        return {"modalities": [{"modality": "image", "effective": "local"}]}


class PipelineVideo:
    def __init__(self, root: Path):
        self.root = root
        self.counter = 0

    def generate(self, **kwargs):
        self.counter += 1
        destination = self.root / f"scene-{self.counter}.mp4"
        subprocess.run(
            # The production renderer requests 24 frames at 8fps: each scene
            # is three seconds.  Keep the end-to-end fixture faithful so this
            # test verifies a commercial, rather than merely any MP4 file.
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=16x16:r=8:d=3",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", str(destination)],
            check=True, capture_output=True,
        )
        return {"video": str(destination), "provenance": "test fixture"}


class PipelineTTS:
    def __init__(self, root: Path):
        self.audio = root / "voice.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
             str(self.audio)], check=True, capture_output=True,
        )

    def synthesize(self, **kwargs):
        return {"audio_base64": base64.b64encode(self.audio.read_bytes()).decode(), "format": "wav"}


class PipelineMusic:
    def __init__(self, root: Path):
        self.audio = root / "music.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=2",
             str(self.audio)], check=True, capture_output=True,
        )

    def generate(self, **kwargs):
        return {"audio_path": str(self.audio), "duration": kwargs["duration_seconds"]}


class PipelineRegistry:
    def __init__(self, root: Path):
        self.video = PipelineVideo(root)
        self.tts = PipelineTTS(root)
        self.music = PipelineMusic(root)


class CoreAIEngineTest(unittest.TestCase):
    def create_image(self, directory: Path) -> Path:
        path = directory / "brand.png"
        image = Image.new("RGB", (100, 100), "#112233")
        for x in range(50, 100):
            for y in range(100):
                image.putpixel((x, y), (245, 190, 40))
        image.save(path)
        return path

    def test_brand_to_storyboard_meets_phase_gates(self):
        with tempfile.TemporaryDirectory() as temporary:
            brand = extract_brand(self.create_image(Path(temporary)), "coffee")

        self.assertGreaterEqual(len(brand.colors), 3)  # PHASE-1.1: colors extracted
        script = generate_script(brand, "Brew a better day")
        self.assertEqual(sum(scene.duration_seconds for scene in script), 30)  # PHASE-1.2
        storyboard = build_storyboard(script, brand)
        self.assertTrue(8 <= len(storyboard) <= 12)  # PHASE-1.3
        self.assertTrue(check_brand_consistency(brand, storyboard)["passed"])  # PHASE-1.10

    def test_media_adapters_render_audio_and_transcribe(self):
        brand = extract_brand(self._temporary_image())
        script = generate_script(brand)
        storyboard = build_storyboard(script, brand)
        registry = FakeRegistry()

        self.assertEqual(len(render_scenes(storyboard, registry)), 10)  # PHASE-1.4
        audio = generate_audio(script, registry)
        self.assertEqual(audio["duration_seconds"], 30)  # PHASE-1.5
        with tempfile.NamedTemporaryFile() as audio_file:
            audio_file.write(b"audio")
            audio_file.flush()
            self.assertEqual(transcribe_audio(audio_file.name, registry)["text"], "Canonical transcript")
        self.assertIn("images_base64", inpaint("brand.png", "remove reflection", registry))

    def test_backend_registry_supports_local_and_api_provider_selection(self):
        local = BackendRegistry(config={
            "text": "demo-text", "local_backends": {"text": "demo-text"},
            "api_backends": {"text": "openai"},
        }, url_overrides={"openai": "https://api.example/v1"})
        self.assertEqual(local.text.__class__.__name__, "DemoTextBackend")
        selected = local.select("text", "api", "vault://providers/text")
        self.assertEqual(selected, {"effective_backend": "api", "status": "ok"})
        self.assertEqual(local.text.__class__.__name__, "OpenAICompatibleBackend")
        self.assertEqual(local.text.url, "https://api.example/v1")
        self.assertNotIn("vault://providers/text", str(local.catalog()))
        self.assertEqual(local.select("text", "local"), {"effective_backend": "local", "status": "ok"})

    def _temporary_image(self) -> Path:
        temporary = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temporary.close()
        Image.new("RGB", (8, 8), "#336699").save(temporary.name)
        self.addCleanup(Path(temporary.name).unlink, missing_ok=True)
        return Path(temporary.name)

    def test_assembly_produces_an_mp4(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scene = root / "scene.mp4"
            # A valid one-frame H.264 fixture is enough to exercise FFmpeg assembly.
            import subprocess
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=16x16:d=0.1",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(scene)],
                           check=True, capture_output=True)
            output = assemble_mp4([scene, scene], root / "commercial.mp4")
            self.assertGreater(output.stat().st_size, 0)  # PHASE-1.6: MP4 output

    def test_dashboard_draft_endpoint_returns_reviewable_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = self.create_image(root)
            original_uploads = dashboard_app.UPLOADS_DIR
            dashboard_app.UPLOADS_DIR = root / "uploads"
            self.addCleanup(setattr, dashboard_app, "UPLOADS_DIR", original_uploads)
            with path.open("rb") as image:
                response = app.test_client().post(
                    "/api/instant-ad",
                    data={"image": (image, "brand.png"), "tagline": "Make it memorable"},
                    content_type="multipart/form-data",
                )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["duration_seconds"], 30)
        self.assertEqual(len(payload["storyboard"]), 10)
        self.assertTrue(payload["quality"]["passed"])
        self.assertEqual(payload["social_package"]["status"], "packaged")
        self.assertGreaterEqual(len(payload["social_package"]["platforms"]), 5)

    def test_dashboard_render_endpoint_delivers_downloadable_mp4(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = self.create_image(root)
            originals = (dashboard_app.UPLOADS_DIR, dashboard_app.OUTPUT_DIR, dashboard_app.registry)
            dashboard_app.UPLOADS_DIR = root / "uploads"
            dashboard_app.OUTPUT_DIR = root / "output"
            dashboard_app.registry = PipelineRegistry(root)
            self.addCleanup(setattr, dashboard_app, "UPLOADS_DIR", originals[0])
            self.addCleanup(setattr, dashboard_app, "OUTPUT_DIR", originals[1])
            self.addCleanup(setattr, dashboard_app, "registry", originals[2])
            with path.open("rb") as image:
                response = app.test_client().post(
                    "/api/instant-ad",
                    data={"image": (image, "brand.png"), "render": "true", "music_style": "calm"},
                    content_type="multipart/form-data",
                )
            self.assertEqual(response.status_code, 200, response.get_json())
            payload = response.get_json()
            self.assertEqual(payload["video_resolution"], "1920x1080")
            self.assertLess(payload["video_size_mb"], 60)
            output = root / "output" / Path(payload["video_url"]).name
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format=duration:stream=codec_name,width,height", "-of", "json", str(output)],
                check=True, capture_output=True, text=True,
            )
            metadata = json.loads(probe.stdout)
            self.assertAlmostEqual(float(metadata["format"]["duration"]), 30, delta=0.1)
            video = next(stream for stream in metadata["streams"] if stream["codec_name"] == "h264")
            self.assertEqual((video["width"], video["height"]), (1920, 1080))
            download = app.test_client().get(payload["video_url"])
            self.assertEqual(download.status_code, 200)
            self.assertEqual(download.mimetype, "video/mp4")
            download.close()

    def test_provider_free_fallback_renders_downloadable_commercial(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = self.create_image(root)
            originals = (dashboard_app.UPLOADS_DIR, dashboard_app.OUTPUT_DIR, dashboard_app.registry)
            dashboard_app.UPLOADS_DIR = root / "uploads"
            dashboard_app.OUTPUT_DIR = root / "output"
            dashboard_app.registry = BackendRegistry(config={
                "text": "demo-text", "image": "demo-image", "video": "demo-video",
                "tts": "demo-tts", "stt": "demo-stt", "music": "demo-music",
                "studio_mount": str(root / "studio"),
            })
            self.addCleanup(setattr, dashboard_app, "UPLOADS_DIR", originals[0])
            self.addCleanup(setattr, dashboard_app, "OUTPUT_DIR", originals[1])
            self.addCleanup(setattr, dashboard_app, "registry", originals[2])
            with path.open("rb") as image:
                response = app.test_client().post(
                    "/api/instant-ad",
                    data={
                        "image": (image, "brand.png"),
                        "product_type": "creative studio",
                        "tagline": "Generate a complete commercial from one brand image.",
                        "render": "true",
                    },
                    content_type="multipart/form-data",
                )
            self.assertEqual(response.status_code, 200, response.get_json())
            payload = response.get_json()
            self.assertEqual(payload["video_resolution"], "1920x1080")
            self.assertIn("video_url", payload)
            self.assertTrue((root / "output" / Path(payload["video_url"]).name).is_file())
            self.assertTrue(all(
                item["publish_status"] == "ready_to_connect"
                for item in payload["social_package"]["platforms"]
            ))

    def test_workspace_frontend_exposes_complete_commercial_flow(self):
        page = app.test_client().get("/").get_data(as_text=True)

        self.assertIn("Turn one brand image into a complete commercial campaign", page)
        self.assertIn("Generate commercial", page)
        self.assertIn("fetch('/api/instant-ad'", page)
        self.assertIn("fetch('/api/v1/backends/select'", page)
        self.assertIn("fetch('/api/social/package'", page)
        self.assertIn("Social distribution", page)
        self.assertIn("Skeleton infrastructure", page)

    def test_social_package_endpoint_returns_platform_handoff(self):
        response = app.test_client().post("/api/social/package", json={
            "brand_analysis": {"product_type": "coffee", "colors": ["#112233", "#F5BE28"]},
            "script": [{"voiceover": "Wake up with better coffee."},
                       {"voiceover": "Brew a better day."}],
            "video_url": "/output/commercial.mp4",
        })

        self.assertEqual(response.status_code, 200, response.get_json())
        payload = response.get_json()
        platforms = {item["platform"]: item for item in payload["platforms"]}
        self.assertIn("tiktok", platforms)
        self.assertIn("instagram", platforms)
        self.assertIn("youtube", platforms)
        self.assertEqual(platforms["tiktok"]["asset_url"], "/output/commercial.mp4")
        self.assertEqual(platforms["tiktok"]["publish_status"], "ready_to_connect")

    def test_backend_switch_endpoint_requires_key_reference_and_switches(self):
        original_registry = dashboard_app.registry
        dashboard_app.registry = BackendRegistry(config={
            "text": "demo-text", "local_backends": {"text": "demo-text"},
            "api_backends": {"text": "openai"},
        })
        self.addCleanup(setattr, dashboard_app, "registry", original_registry)
        client = app.test_client()
        rejected = client.post("/api/v1/backends/select", json={"modality": "text", "backend": "api"})
        self.assertEqual(rejected.status_code, 400)
        selected = client.post("/api/v1/backends/select", json={
            "modality": "text", "backend": "api", "provider_key_ref": "vault://text-key",
        })
        self.assertEqual(selected.get_json(), {"effective_backend": "api", "status": "ok"})
        catalog = client.get("/api/v1/backends").get_json()
        text = next(item for item in catalog["modalities"] if item["modality"] == "text")
        self.assertEqual(text["effective"], "api")
        self.assertNotIn("vault://text-key", str(catalog))

    def test_studio_generate_and_masked_inpaint_roundtrip_are_checksum_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.create_image(root)
            mask = root / "mask.png"
            Image.new("L", (100, 100), 0).save(mask)
            with Image.open(mask) as image:
                image.paste(255, (20, 20, 80, 80))
                image.save(mask)
            originals = (dashboard_app.UPLOADS_DIR, dashboard_app.OUTPUT_DIR, dashboard_app.STUDIO_MOUNT,
                         dashboard_app.registry, dict(dashboard_app.STUDIO_JOBS))
            dashboard_app.UPLOADS_DIR = root / "uploads"
            dashboard_app.OUTPUT_DIR = root / "output"
            dashboard_app.STUDIO_MOUNT = root / "mount"
            dashboard_app.registry = FakeRegistry()
            dashboard_app.STUDIO_JOBS.clear()
            self.addCleanup(setattr, dashboard_app, "UPLOADS_DIR", originals[0])
            self.addCleanup(setattr, dashboard_app, "OUTPUT_DIR", originals[1])
            self.addCleanup(setattr, dashboard_app, "STUDIO_MOUNT", originals[2])
            self.addCleanup(setattr, dashboard_app, "registry", originals[3])
            self.addCleanup(dashboard_app.STUDIO_JOBS.update, originals[4])
            client = app.test_client()
            generated = client.post("/api/v1/studio/generate", data={"prompt": "a brand hero image"})
            self.assertEqual(generated.status_code, 200, generated.get_json())
            self.assertEqual(generated.get_json()["tier"], "flash")
            generated_preview_id = generated.get_json()["job_id"]
            with source.open("rb") as source_file, mask.open("rb") as mask_file:
                preview = client.post("/api/v1/studio/inpaint", data={
                    "source_image": (source_file, "source.png"), "mask": (mask_file, "mask.png"),
                    "prompt": "replace the selected background", "mode": "restyle",
                    "brand_palette": "#112233, #F5BE28",
                }, content_type="multipart/form-data")
            self.assertEqual(preview.status_code, 200, preview.get_json())
            with source.open("rb") as source_file, mask.open("rb") as mask_file:
                edited = client.post("/api/v1/studio/inpaint", data={
                    "source_image": (source_file, "source.png"), "mask": (mask_file, "mask.png"),
                    "prompt": "replace the selected background", "mode": "restyle",
                    "brand_palette": "#112233, #F5BE28", "tier": "final", "approved": "true",
                    "preview_job_id": preview.get_json()["job_id"],
                }, content_type="multipart/form-data")
            self.assertEqual(edited.status_code, 200, edited.get_json())
            job = edited.get_json()
            self.assertEqual(job["status"], "completed")
            self.assertEqual(job["mode"], "restyle")
            self.assertEqual(job["tier"], "final")
            self.assertEqual(job["brand_palette"], "#112233, #F5BE28")
            saved = root / "output" / Path(job["image_url"]).name
            self.assertTrue(saved.is_file())
            self.assertEqual(job["checksum"], checksum_asset(saved))
            self.assertEqual(client.get(f"/api/v1/studio/{job['job_id']}").get_json(), job)
            approved_generated = client.post("/api/v1/studio/generate", data={
                "prompt": "a brand hero image", "tier": "final", "approved": "true",
                "preview_job_id": generated_preview_id,
            })
            self.assertEqual(approved_generated.status_code, 200, approved_generated.get_json())
            mismatched_final = client.post("/api/v1/studio/generate", data={
                "prompt": "a different brand hero", "tier": "final", "approved": "true",
                "preview_job_id": generated_preview_id,
            })
            self.assertEqual(mismatched_final.status_code, 400)
            self.assertIn("FLASH_PREVIEW_REQUIRED", mismatched_final.get_json()["error"])

    def test_studio_canvas_exposes_brush_lasso_and_full_frame_masks(self):
        """MOD-021 exposes independent prompt generation and all mask interactions."""
        response = app.test_client().get("/studio")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('id="generate-preview"', page)
        self.assertIn('id="generate-final"', page)
        self.assertIn('id="generate-final" type="button" disabled', page)
        self.assertIn('id="final" type="button" disabled', page)
        self.assertIn("preview_job_id", page)
        self.assertIn("async function generate(final)", page)
        self.assertIn("fetch('/api/v1/studio/generate'", page)
        self.assertIn("fd.append('brand_palette'", page)
        generate_body = page.split("async function generate(final)", 1)[1].split(
            "async function render(final)", 1
        )[0]
        self.assertNotIn("source.files", generate_body)
        self.assertNotIn("fd.append('mask'", generate_body)
        for control in ('id="brush"', 'id="lasso"', 'id="full-frame"', 'id="close-lasso"'):
            self.assertIn(control, page)
        self.assertIn("function closeLasso()", page)
        self.assertIn("maskCtx.fillRect(0,0,mask.width,mask.height)", page)
        self.assertIn("maskCtx.arc", page)
        self.assertIn("fd.append('mask',await new Promise(r=>mask.toBlob(r,'image/png'))", page)

    def test_studio_rejects_empty_mask_and_final_without_matching_flash_preview(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.create_image(root)
            mask = root / "empty-mask.png"
            Image.new("L", (100, 100), 0).save(mask)
            original_uploads = dashboard_app.UPLOADS_DIR
            dashboard_app.UPLOADS_DIR = root / "uploads"
            self.addCleanup(setattr, dashboard_app, "UPLOADS_DIR", original_uploads)
            client = app.test_client()
            with source.open("rb") as source_file, mask.open("rb") as mask_file:
                response = client.post("/api/v1/studio/inpaint", data={
                    "source_image": (source_file, "source.png"), "mask": (mask_file, "mask.png"),
                    "prompt": "remove reflection", "tier": "final", "approved": "true",
                }, content_type="multipart/form-data")
            self.assertEqual(response.status_code, 400)
            self.assertIn("INVALID_MASK", response.get_json()["error"])
        rejected = app.test_client().post("/api/v1/studio/generate", data={
            "prompt": "brand hero", "tier": "final",
        })
        self.assertEqual(rejected.status_code, 400)
        self.assertIn("APPROVAL_REQUIRED", rejected.get_json()["error"])
        unpreviewed = app.test_client().post("/api/v1/studio/generate", data={
            "prompt": "brand hero", "tier": "final", "approved": "true",
        })
        self.assertEqual(unpreviewed.status_code, 400)
        self.assertIn("FLASH_PREVIEW_REQUIRED", unpreviewed.get_json()["error"])

    def test_rejects_taglines_over_two_hundred_characters(self):
        brand = extract_brand(self._temporary_image())
        with self.assertRaises(CoreAIError):
            generate_script(brand, "x" * 201)


if __name__ == "__main__":
    unittest.main()

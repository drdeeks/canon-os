"""Functional contracts for the Phase 1 Core AI Engine."""

import base64
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
        return {"images": ["edited.png"]}


class FakeRegistry:
    video = FakeVideo()
    tts = FakeTTS()
    music = FakeMusic()
    stt = FakeSTT()
    image = FakeImage()


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
        self.assertEqual(inpaint("brand.png", "remove reflection", registry)["images"], ["edited.png"])

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

    def test_rejects_taglines_over_two_hundred_characters(self):
        brand = extract_brand(self._temporary_image())
        with self.assertRaises(CoreAIError):
            generate_script(brand, "x" * 201)


if __name__ == "__main__":
    unittest.main()

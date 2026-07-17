"""Functional contracts for the Phase 1 Core AI Engine."""

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
        local = BackendRegistry(config={"text": "demo-text"})
        self.assertEqual(local.text.__class__.__name__, "DemoTextBackend")
        api = BackendRegistry(config={"text": "openai"}, url_overrides={"openai": "https://api.example/v1"})
        self.assertEqual(api.text.__class__.__name__, "OpenAICompatibleBackend")
        self.assertEqual(api.text.url, "https://api.example/v1")

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

    def test_rejects_taglines_over_two_hundred_characters(self):
        brand = extract_brand(self._temporary_image())
        with self.assertRaises(CoreAIError):
            generate_script(brand, "x" * 201)


if __name__ == "__main__":
    unittest.main()

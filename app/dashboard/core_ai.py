"""Core AI-engine orchestration for Canon OS Phase 1.

The engine keeps the creative artifacts explicit: brand analysis, a timed
script, storyboard, rendered-scene manifest, audio manifest, and a final MP4.
Provider calls are injected through ``BackendRegistry`` so a local model and an
API provider use the same pipeline.
"""

from __future__ import annotations

import base64
import colorsys
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from PIL import Image


ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
SCENE_COUNT = 10


class CoreAIError(ValueError):
    """A user-correctable Core AI Engine input or provider failure."""


@dataclass(frozen=True)
class BrandAnalysis:
    colors: list[str]
    style: str
    mood: str
    product_type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Scene:
    number: int
    duration_seconds: int
    narration: str
    visual: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_brand(image_path: str | Path, product_type: str = "product") -> BrandAnalysis:
    """Extract a stable five-colour palette plus basic visual character."""
    path = Path(image_path)
    if not path.is_file():
        raise CoreAIError("IMAGE_REQUIRED: provide a JPG, PNG, or WebP image")
    if path.stat().st_size > MAX_IMAGE_BYTES:
        raise CoreAIError("IMAGE_TOO_LARGE: image exceeds 10MB")

    try:
        with Image.open(path) as image:
            if image.format not in ALLOWED_IMAGE_FORMATS:
                raise CoreAIError("INVALID_FORMAT: use JPG, PNG, or WebP")
            rgb = image.convert("RGB")
            rgb.thumbnail((160, 160))
            palette = rgb.quantize(colors=5, method=Image.Quantize.MEDIANCUT)
            counts = sorted(palette.getcolors() or [], reverse=True)
            palette_rgb = palette.convert("RGB")
            colors = ["#%02X%02X%02X" % palette_rgb.getpixel((0, 0))]
            palette_values = palette.getpalette()
            colors = []
            for _, index in counts:
                start = index * 3
                red, green, blue = palette_values[start:start + 3]
                value = "#%02X%02X%02X" % (red, green, blue)
                if value not in colors:
                    colors.append(value)
            while len(colors) < 3:
                colors.append(colors[-1])
            pixels = list(rgb.getdata())
    except CoreAIError:
        raise
    except Exception as error:
        raise CoreAIError("INVALID_FORMAT: use JPG, PNG, or WebP") from error

    lightness = sum(sum(pixel) / (3 * 255) for pixel in pixels) / len(pixels)
    saturation = sum(colorsys.rgb_to_hsv(*(channel / 255 for channel in pixel))[1]
                     for pixel in pixels) / len(pixels)
    style = "vibrant" if saturation >= 0.45 else "minimal"
    mood = "bright" if lightness >= 0.6 else "dramatic"
    return BrandAnalysis(colors=colors[:5], style=style, mood=mood,
                         product_type=product_type.strip() or "product")


def generate_script(brand: BrandAnalysis, tagline: str = "") -> list[Scene]:
    """Create a 30-second commercial script with ten timed scenes."""
    if len(tagline) > 200:
        raise CoreAIError("INVALID_TAGLINE: tagline must be 200 characters or fewer")
    hook = tagline.strip() or f"Meet the {brand.product_type} made for your next moment."
    beats = [
        ("Open on the product in a striking brand-colour environment.", hook),
        ("Reveal the crafted details in a clean hero close-up.", "Designed to stand out."),
        ("Show the product solving an everyday need.", "Simple when it matters."),
        ("Move through its most compelling feature.", "Every detail works harder."),
        ("Cut to a confident customer interaction.", "Made to fit your rhythm."),
        ("Use motion to show the product from a new angle.", "A better way forward."),
        ("Highlight a tactile detail with soft light.", "Feel the difference."),
        ("Return to a wide lifestyle hero shot.", "Built around what you love."),
        ("Build to the product and logo together.", "Make it yours."),
        ("End on a clean end card in the primary palette.", hook),
    ]
    return [Scene(number=index + 1, duration_seconds=3, visual=visual,
                  narration=narration) for index, (visual, narration) in enumerate(beats)]


def build_storyboard(script: Iterable[Scene], brand: BrandAnalysis) -> list[dict[str, Any]]:
    """Turn timed script beats into provider-ready visual prompts."""
    storyboard = []
    for scene in script:
        prompt = (
            f"Commercial {brand.product_type}, {scene.visual} "
            f"Style: {brand.style}; mood: {brand.mood}; "
            f"brand palette {', '.join(brand.colors)}."
        )
        storyboard.append({**scene.to_dict(), "prompt": prompt})
    if not 8 <= len(storyboard) <= 12:
        raise CoreAIError("STORYBOARD_INVALID: commercial storyboard must contain 8-12 scenes")
    return storyboard


def render_scenes(storyboard: Iterable[dict[str, Any]], registry: Any,
                  image_name: str | None = None) -> list[dict[str, Any]]:
    """Render each storyboard scene through the configured video adapter."""
    rendered = []
    for scene in storyboard:
        result = registry.video.generate(
            prompt=scene["prompt"], input_image=image_name,
            mode="img2vid" if image_name else "txt2vid", frames=24, fps=8,
        )
        if result.get("error"):
            raise CoreAIError(f"VIDEO_RENDER_FAILED: scene {scene['number']}: {result['error']}")
        rendered.append({"scene": scene["number"], "duration_seconds": scene["duration_seconds"],
                         "asset": result.get("video") or result.get("videos") or result.get("images"),
                         "provider": result.get("provenance", "configured backend")})
    return rendered


def generate_audio(script: Iterable[Scene], registry: Any, voice: str = "neutral",
                   music_style: str = "upbeat") -> dict[str, Any]:
    """Generate a single voiceover and optional 30-second music bed."""
    narration = " ".join(scene.narration for scene in script)
    voiceover = registry.tts.synthesize(text=narration, voice=voice)
    if voiceover.get("error"):
        raise CoreAIError(f"AUDIO_GENERATION_FAILED: voiceover: {voiceover['error']}")
    music: dict[str, Any] | None = None
    if music_style != "none":
        music = registry.music.generate(
            prompt=f"royalty-free {music_style} commercial background music",
            duration_seconds=30, mood=music_style,
        )
        if music.get("error"):
            raise CoreAIError(f"AUDIO_GENERATION_FAILED: music: {music['error']}")
    return {"voiceover": voiceover, "music": music, "duration_seconds": 30}


def transcribe_audio(audio_path: str | Path, registry: Any) -> dict[str, Any]:
    """Transcribe local audio through the configured local/API STT adapter."""
    raw = Path(audio_path).read_bytes()
    result = registry.stt.transcribe(audio_base64=base64.b64encode(raw).decode())
    if result.get("error"):
        raise CoreAIError(f"TRANSCRIPTION_FAILED: {result['error']}")
    return result


def inpaint(image_name: str, prompt: str, registry: Any) -> dict[str, Any]:
    """Run image editing through the selected image backend."""
    result = registry.image.generate(prompt=prompt, input_image=image_name, mode="img2img")
    if result.get("error"):
        raise CoreAIError(f"INPAINT_FAILED: {result['error']}")
    return result


def check_brand_consistency(brand: BrandAnalysis, storyboard: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Validate brand DNA is explicitly inherited by every generated prompt."""
    scenes = list(storyboard)
    palette = ", ".join(brand.colors)
    failures = [scene["number"] for scene in scenes if palette not in scene.get("prompt", "")]
    return {"passed": bool(brand.colors) and not failures, "scene_count": len(scenes),
            "failed_scenes": failures, "colors": brand.colors}


def assemble_mp4(scene_paths: Iterable[str | Path], output_path: str | Path,
                 audio_paths: Iterable[str | Path] = (), ffmpeg_binary: str = "ffmpeg") -> Path:
    """Concatenate local scenes into a 1080p H.264 MP4, mixing supplied audio."""
    paths = [Path(path).resolve() for path in scene_paths]
    if not paths or any(not path.is_file() for path in paths):
        raise CoreAIError("ASSEMBLY_FAILED: every rendered scene must be a local file")
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = output.with_suffix(".concat.txt")
    manifest.write_text("".join(f"file '{path.as_posix()}'\n" for path in paths), encoding="utf-8")
    intermediate = output.with_name(f"{output.stem}.video.mp4")
    try:
        completed = subprocess.run(
            [ffmpeg_binary, "-y", "-f", "concat", "-safe", "0", "-i", str(manifest),
             "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                    "pad=1920:1080:(ow-iw)/2:(oh-ih)/2", "-c:v", "libx264",
             "-pix_fmt", "yuv420p", "-an", str(intermediate)],
            capture_output=True, text=True, check=False,
        )
    finally:
        manifest.unlink(missing_ok=True)
    if completed.returncode != 0 or not intermediate.is_file() or intermediate.stat().st_size == 0:
        raise CoreAIError(f"ASSEMBLY_FAILED: {completed.stderr[-500:]}")
    audio = [Path(path).resolve() for path in audio_paths if Path(path).is_file()]
    command = [ffmpeg_binary, "-y", "-i", str(intermediate)]
    for item in audio:
        command.extend(["-i", str(item)])
    if audio:
        inputs = "".join(f"[{index}:a]" for index in range(1, len(audio) + 1))
        command.extend(["-filter_complex", f"{inputs}amix=inputs={len(audio)}:duration=longest[a]",
                        "-map", "0:v", "-map", "[a]", "-shortest"])
    else:
        command.extend(["-map", "0:v"])
    command.extend(["-c:v", "copy", "-c:a", "aac", "-movflags", "+faststart", str(output)])
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    finally:
        intermediate.unlink(missing_ok=True)
    if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        raise CoreAIError(f"ASSEMBLY_FAILED: {completed.stderr[-500:]}")
    if output.stat().st_size > 60 * 1024 * 1024:
        output.unlink(missing_ok=True)
        raise CoreAIError("ASSEMBLY_FAILED: assembled video exceeds 60MB")
    return output


def audio_asset_paths(audio: dict[str, Any], output_dir: str | Path, stem: str) -> list[Path]:
    """Materialize adapter-returned local/base64 audio for FFmpeg assembly."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for label, result in (("voiceover", audio.get("voiceover")), ("music", audio.get("music"))):
        if not result:
            continue
        local = result.get("audio_path")
        if local and Path(local).is_file():
            paths.append(Path(local))
            continue
        encoded = result.get("audio_base64")
        if encoded:
            try:
                destination = directory / f"{stem}-{label}.{result.get('format', 'wav')}"
                destination.write_bytes(base64.b64decode(encoded, validate=True))
                paths.append(destination)
            except (ValueError, OSError):
                raise CoreAIError(f"AUDIO_GENERATION_FAILED: {label} audio is invalid")
    return paths

"""Optional original AI illustration and motion-graphics renderer for Shorts.

Every scene is created with Cloudflare Workers AI FLUX.1 [schnell]. The generated
art is an illustration, never presented as evidence or documentary footage.
When any request fails, fail closed and let the caller use the existing stock
footage / animation pipeline. Public upload always requires editorial approval.
"""
from __future__ import annotations

import base64
import binascii
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

IMAGE_MODEL = "@cf/black-forest-labs/flux-1-schnell"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
SCENE_COUNT = 3
PROMPT_PREFIX = (
    "Original 2D editorial science illustration, dramatic composition, "
    "vivid sophisticated colors, clear central subject, mobile vertical frame, "
    "non-photorealistic artwork. No text, letters, numbers, logos, "
    "watermarks, celebrities, or realistic depictions of actual events. "
)


def validated_prompts(pack: dict[str, Any]) -> list[str]:
    """Return exactly three distinct, model-authored visual directions."""
    prompts = pack.get("scene_prompts")
    if not isinstance(prompts, list) or len(prompts) != SCENE_COUNT:
        return []
    if any(not isinstance(p, str) or not 15 <= len(p.strip()) <= 250 for p in prompts):
        return []
    cleaned = [re.sub(r"\s+", " ", p).strip() for p in prompts]
    if len({p.casefold() for p in cleaned}) != SCENE_COUNT:
        return []
    return cleaned


def decode_image_response(payload: dict[str, Any]) -> bytes:
    """Validate provider envelope, base64 size, and JPEG/PNG file signature."""
    if payload.get("success") is not True:
        raise ValueError("Image service returned a failure")
    result = payload.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("image"), str):
        raise ValueError("Image response missing image data")
    encoded = result["image"]
    if len(encoded) > 4 * MAX_IMAGE_BYTES // 3 + 8:
        raise ValueError("Image response exceeds size limit")
    try:
        image = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid image encoding") from exc
    is_jpeg = image.startswith(b"\xff\xd8\xff")
    is_png = image.startswith(b"\x89PNG\r\n\x1a\n")
    if not (is_jpeg or is_png) or len(image) > MAX_IMAGE_BYTES or len(image) < 4:
        raise ValueError("Invalid image format or size")
    return image


def request_image(account_id: str, api_token: str, direction: str) -> bytes:
    """One bounded provider call, without logging secrets or response bodies."""
    url = (
        "https://api.cloudflare.com/client/v4/accounts/"
        + account_id + "/ai/run/" + IMAGE_MODEL
    )
    request = urllib.request.Request(
        url,
        data=json.dumps({"prompt": (PROMPT_PREFIX + direction)[:850], "steps": 4}).encode(),
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "User-Agent": "video-factory/3.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=75) as response:
        # Avoid unbounded response reads.
        body = response.read(4 * MAX_IMAGE_BYTES // 3 + 32768)
    return decode_image_response(json.loads(body))


def generate_ai_images(pack: dict[str, Any], output_dir: Path) -> list[Path]:
    """Generate up to three fresh illustrated scenes when explicitly enabled.

    No images are reused after a partial provider failure. No expenses are
    incurred unless AI_VISUALS=1 is set and Cloudflare credentials are present.
    """
    if os.getenv("AI_VISUALS", "0") != "1":
        return []
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    directions = validated_prompts(pack) if pack.get("ai_generated") else []
    if not re.fullmatch(r"[a-fA-F0-9]{32}", account_id) or not api_token or not directions:
        print("AI visuals skipped: needs valid credentials and model-authored scenes.")
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    try:
        for index, direction in enumerate(directions, start=1):
            image = request_image(account_id, api_token, direction)
            extension = ".jpg" if image.startswith(b"\xff\xd8\xff") else ".png"
            destination = output_dir / f"ai-scene-{index}{extension}"
            destination.write_bytes(image)
            files.append(destination)
        return files
    except (ValueError, OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"AI visuals unavailable ({type(exc).__name__}); using existing renderer.")
        for file in files:
            file.unlink(missing_ok=True)
        return []


def render_illustrated_short(
    image_paths: list[Path],
    duration: float,
    video_path: Path,
    audio_path: Path,
    captions_path: Path,
    title: str,
) -> None:
    """Add slow camera motion and hard scene cuts, then mux narration/captions."""
    if len(image_paths) != SCENE_COUNT or duration <= 0:
        raise ValueError("Illustrated video requires three scenes and positive duration")

    inputs: list[str] = []
    filters: list[str] = []
    labels: list[str] = []
    segment = duration / len(image_paths)
    for index, path in enumerate(image_paths):
        # Images are read as a 30 fps stream; zoompan d=1 emits one animated
        # output frame per input frame (not repeated static slides).
        inputs.extend(["-loop", "1", "-framerate", "30", "-t", f"{segment + 0.15:.3f}",
                       "-i", str(path)])
        label = f"[scene{index}]"
        filters.append(
            f"[{index}:v]scale=720:1280:force_original_aspect_ratio=increase,"
            "crop=720:1280,"
            "zoompan=z='min(zoom+0.00065,1.15)':"
            "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            "d=1:s=720x1280:fps=30,"
            f"trim=duration={segment:.3f},setpts=PTS-STARTPTS,"
            f"setsar=1,format=yuv420p{label}"
        )
        labels.append(label)

    overlay = (
        "drawtext=text='ALAM MO BA?':fontcolor=0x7DD3FC:fontsize=22:"
        "borderw=2:bordercolor=black@0.75:x=(w-text_w)/2:y=58:"
        "enable='between(t,0,2.8)',"
        f"drawtext=text='{title}':fontcolor=white:fontsize=27:"
        "borderw=3:bordercolor=black@0.85:x=(w-text_w)/2:y=96,"
        f"subtitles='{captions_path.as_posix()}':force_style="
        "'FontName=DejaVu Sans,FontSize=13,Bold=1,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00101010,BorderStyle=1,BackColour=&H00000000,"
        "Outline=1,Shadow=0,Alignment=2,MarginL=90,MarginR=90,MarginV=105'"
    )
    filters.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0,{overlay}[finalv]")
    subprocess.run(
        [
            "ffmpeg", "-y", *inputs, "-i", str(audio_path),
            "-filter_complex", ";".join(filters),
            "-map", "[finalv]", "-map", f"{len(image_paths)}:a:0",
            "-t", f"{duration:.3f}", "-c:v", "libx264",
            "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-shortest",
            "-movflags", "+faststart", str(video_path),
        ],
        check=True, capture_output=True, text=True, timeout=300,
    )

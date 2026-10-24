#!/usr/bin/env python3
"""Phone-friendly cloud runner: Cloudflare content pack -> seven KURI prompts.

No rendering, provider purchases, YouTube uploading, or local PC needed.
All network access uses the Cloudflare Worker already deployed by this repo.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

STYLE = "3d"
KURI_REFERENCE = (
    "KURI, the recurring 25-year-old Filipino male science host with medium-tan skin, "
    "masculine jawline, expressive dark-brown eyes, thick eyebrows, short slightly textured "
    "black hair, broad shoulders and fit adult proportions; golden-yellow hoodie with a "
    "small teal question-mark emblem, navy joggers and white sneakers with teal accents. "
    "Keep face, physique and wardrobe consistent with the approved KURI reference image."
)
VOICE_DIRECTION = (
    "Deep, warm, confident adult Filipino male voice, medium-low pitch, naturally masculine "
    "timbre, native Metro Manila Tagalog accent, conversational science-presenter delivery."
)
NO_AUDIO_SUFFIX = " No dialogue, voice-over, music, subtitles, logos or on-screen text."


def worker_origin(value: str) -> str:
    parsed = urlparse(value.strip())
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.port
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("WORKER_ORIGIN must be an HTTPS origin without a path or credentials")
    # Avoid accidentally sending a bearer secret to arbitrary hosts.
    if not parsed.hostname.endswith(".workers.dev"):
        raise ValueError("Only a trusted workers.dev origin is permitted by this runner")
    return "https://" + parsed.hostname


def request_json(origin: str, endpoint: str, token: str, payload: dict) -> dict:
    if endpoint not in ("/v1/generate", "/v1/storyboard"):
        raise ValueError("Endpoint is not allowlisted")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if len(body) > 8192:
        raise ValueError("Request is larger than the Worker limit")
    req = Request(
        origin + endpoint,
        method="POST",
        data=body,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            # Cloudflare rejects the default Python-urllib user agent with HTTP 403.
            "User-Agent": "VideoFactory-GitHub-Actions/1.0",
        },
    )
    for attempt in range(3):
        try:
            with urlopen(req, timeout=110) as response:
                value = json.load(response)
            if not isinstance(value, dict):
                raise ValueError("Worker response must be a JSON object")
            if "error" in value:
                raise ValueError("Worker reported an error")
            return value
        except HTTPError as error:
            # Never print the Worker response or the Authorization header.
            if error.code not in (429, 502, 503, 504) or attempt == 2:
                raise RuntimeError(f"Worker request failed: HTTP {error.code}") from None
        except (URLError, TimeoutError) as error:
            if attempt == 2:
                raise RuntimeError("Worker network request failed after retries") from None
        time.sleep(2**attempt)
    raise RuntimeError("Worker request did not complete")


def require_text(data: dict, name: str, minimum: int = 1) -> str:
    text = data.get(name)
    if not isinstance(text, str) or len(text.strip()) < minimum:
        raise ValueError(f"Missing or invalid field: {name}")
    return text.strip()


def build_review_pack(content: dict, storyboard: dict, topic: str) -> dict:
    title = require_text(content, "title", 12)
    script = require_text(content, "script", 250)
    hook = require_text(content, "hook", 8)
    require_text(content, "caption", 30)
    if storyboard.get("style") != STYLE:
        raise ValueError("Expected the 3D storyboard style")
    items = storyboard.get("scenes")
    if not isinstance(items, list) or len(items) != 7:
        raise ValueError("Exactly seven storyboard scenes are required")

    seen: set[str] = set()
    scenes = []
    for index, scene in enumerate(items, start=1):
        if not isinstance(scene, dict):
            raise ValueError(f"Scene {index} is not an object")
        scene_title = require_text(scene, "title", 6)
        beat = require_text(scene, "voiceoverBeat", 10)
        prompt = require_text(scene, "prompt", 125)
        unique_key = prompt.casefold()
        if unique_key in seen:
            raise ValueError("Storyboard contains duplicate scenes")
        seen.add(unique_key)
        if prompt.endswith(NO_AUDIO_SUFFIX):
            visual = prompt[: -len(NO_AUDIO_SUFFIX)].strip()
        else:
            visual = prompt
        prompt_head = (
            "Premium cinematic 3D animation, vertical 9:16. "
            + KURI_REFERENCE
            + " Scene: "
            + visual
        )
        scenes.append(
            {
                "number": index,
                "title": scene_title,
                "approximateSeconds": 8,
                "tagalogVoiceoverBeat": beat,
                "silentAnimationPrompt": prompt_head
                + " No narration, dialogue, captions, or typography; output silent animation.",
                "googleFlowCombinedPrompt": prompt_head
                + " Sound: one continuous voiceover spoken in natural Tagalog by KURI. "
                + VOICE_DIRECTION
                + ' Spoken narration: "'
                + beat.replace('"', "'")
                + '". Avoid captions or on-screen text. Maintain consistent KURI identity.',
            }
        )

    return {
        "channel": "Bakit Nga Ba?",
        "host": "KURI",
        "topic": topic,
        "style": STYLE,
        "aspectRatio": "9:16",
        "title": title,
        "hook": hook,
        "fullTagalogNarration": script,
        "caption": content["caption"],
        "hashtags": content.get("hashtags", []),
        "sourceNote": content.get("sourceNote", ""),
        "voiceDirection": VOICE_DIRECTION,
        "scenes": scenes,
        "videoGenerated": False,
        "elevenLabsAudioGenerated": False,
        "youtubeUploaded": False,
        "requiresFactCheckAndRightsReview": True,
        "note": (
            "Scene voiceover beats summarize the full narration and are not guaranteed "
            "word-aligned. A real KURI reference image, provider API and editor are still "
            "required for reliable character consistency and final MP4."
        ),
    }


def write_review_pack(pack: dict, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "kuri-review-pack.json").write_text(
        json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    lines = [
        f'BAKIT NGA BA? | {pack["title"]}',
        "",
        "FULL TAGALOG NARRATION",
        pack["fullTagalogNarration"],
        "",
        "ELEVENLABS VOICE DIRECTION",
        pack["voiceDirection"],
        "",
    ]
    for scene in pack["scenes"]:
        lines.extend(
            [
                f'SCENE {scene["number"]} — {scene["title"]}',
                f'VOICEOVER BEAT: {scene["tagalogVoiceoverBeat"]}',
                "",
                "GOOGLE FLOW PROMPT (ANIMATION + VOICEOVER)",
                scene["googleFlowCombinedPrompt"],
                "",
                "SILENT CLIP PROMPT (FOR SEPARATE ELEVENLABS AUDIO)",
                scene["silentAnimationPrompt"],
                "",
            ]
        )
    lines.extend(["CAPTION", pack["caption"], "", "HASHTAGS", " ".join(pack["hashtags"])])
    (directory / "kuri-flow-prompts.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--angle", default="")
    parser.add_argument("--output-dir", default="output/kuri")
    args = parser.parse_args()
    topic = " ".join(args.topic.split())
    angle = " ".join(args.angle.split())
    if not 5 <= len(topic) <= 120:
        parser.error("Topic must be 5–120 characters")
    if len(angle) > 180:
        parser.error("Angle must not exceed 180 characters")
    origin = worker_origin(os.environ.get("KURI_WORKER_ORIGIN", ""))
    token = os.environ.get("APP_ACCESS_TOKEN", "")
    if len(token) < 12:
        raise SystemExit("APP_ACCESS_TOKEN secret is missing or too short")

    print("Generating original Tagalog content pack through the existing Worker...")
    content = request_json(origin, "/v1/generate", token, {
        "topic": topic, "angle": angle, "previousTitles": []
    })
    request_payload = {
        "title": require_text(content, "title", 12),
        "hook": require_text(content, "hook", 8),
        "script": require_text(content, "script", 250),
        "style": STYLE,
    }
    print("Generating seven-scene 3D storyboard...")
    storyboard = request_json(origin, "/v1/storyboard", token, request_payload)
    pack = build_review_pack(content, storyboard, topic)
    write_review_pack(pack, Path(args.output_dir))
    print("Ready: JSON metadata and per-scene Google Flow prompts (no video rendered)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

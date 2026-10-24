#!/usr/bin/env python3
"""Phone-friendly cloud runner: Cloudflare content pack -> seven KURI prompts.

No rendering, provider purchases, YouTube uploading, or local PC needed.
All network access uses the Cloudflare Worker already deployed by this repo.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from functools import lru_cache
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



SCENE_SECONDS = 8
MAX_COMFORTABLE_WORDS_PER_SCENE = 20
CAMERA_MOVEMENTS = (
    "Slow cinematic push-in from medium shot to KURI's expressive face; maintain clear lip sync.",
    "Smooth side-tracking medium shot following KURI's movement; keep his speaking face in frame.",
    "Gentle three-quarter angle dolly with a subtle rack focus to the scientific object and back.",
    "Controlled 30-degree camera orbit around KURI, ending on his face while he speaks.",
    "Soft upward camera tilt from foreground detail to KURI's medium close-up.",
    "Slow steady dolly-in toward KURI's discovery expression without abrupt cuts.",
    "Gradual pullback to a wider visual conclusion, keeping KURI's face readable.",
)


def split_exact_narration(script: str, parts: int = 7) -> list[str]:
    """Partition source words, preserving their exact spelling and punctuation.

    Scene lines are excerpts from the authoritative full narration, never
    AI-generated summaries or paraphrases. Prefer sentence-ending splits.
    """
    tokens = list(re.finditer(r"\S+", script))
    n = len(tokens)
    if parts < 1 or n < parts:
        raise ValueError("Not enough spoken words to split narration into scenes")
    target = n / parts

    @lru_cache(maxsize=None)
    def best(scene_index: int, start: int) -> tuple[float, tuple[int, ...]]:
        if scene_index == parts:
            return (0.0, ()) if start == n else (float("inf"), ())
        remaining_scenes = parts - scene_index - 1
        candidates = []
        for end in range(start + 1, n - remaining_scenes + 1):
            word_count = end - start
            spread_cost = (word_count - target) ** 2
            # Encourage but do not force coherent sentence boundaries.
            boundary_penalty = (
                0.0 if end == n
                or re.search(r'[.!?…][\x22”’)]?    title = require_text(content, "title", 12)
    script = require_text(content, "script", 250)
    hook = require_text(content, "hook", 8)
    require_text(content, "caption", 30)
    if storyboard.get("style") != STYLE:
        raise ValueError("Expected the 3D storyboard style")
    items = storyboard.get("scenes")
    if not isinstance(items, list) or len(items) != 7:
        raise ValueError("Exactly seven storyboard scenes are required")

    dialogue_lines = split_exact_narration(script, len(items))
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
        exact_dialogue = dialogue_lines[index - 1]
        camera = CAMERA_MOVEMENTS[index - 1]
        effects = ambient_effect_for_scene(visual)
        spoken_words = len(exact_dialogue.split())
        pace_warning = (
            "Dialogue may be too long for an 8-second generated clip. "
            "Shorten the master script and regenerate, or use longer clips / a separate voice track. "
            "Do not omit words to force a fit."
            if spoken_words > MAX_COMFORTABLE_WORDS_PER_SCENE else ""
        )
        scenes.append(
            {
                "number": index,
                "title": scene_title,
                "approximateSeconds": SCENE_SECONDS,
                "tagalogVoiceoverBeat": beat,
                "exactTagalogDialogue": exact_dialogue,
                "dialogueWordCount": spoken_words,
                "cameraMovement": camera,
                "soundEffects": effects,
                "durationWarning": pace_warning,
                "silentAnimationPrompt": prompt_head
                + " No narration, dialogue, captions, or typography; output silent animation.",
                "googleFlowCombinedPrompt": make_flow_prompt(
                    visual, exact_dialogue, camera, effects
                ),
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
        "exactNarrationCoverage": True,
        "mayExceedEightSecondClip": any(scene["durationWarning"] for scene in scenes),
        "videoGenerated": False,
        "elevenLabsAudioGenerated": False,
        "youtubeUploaded": False,
        "requiresFactCheckAndRightsReview": True,
        "note": (
            "Exact spoken lines preserve every word in the full narration, in order. "
            "The storyboards were generated independently: review scene alignment. "
            "Eight-second timing and accurate Tagalog speech/lip sync are not guaranteed. "
            "Upload the approved KURI reference image for every scene. "
            "Google Flow scene generation remains manual; no video or MP4 is rendered here."
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
        "KURI VOICE DIRECTION (GOOGLE FLOW OR OPTIONAL ELEVENLABS)",
        pack["voiceDirection"],
        "",
    ]
    for scene in pack["scenes"]:
        lines.extend(
            [
                f'SCENE {scene["number"]} — {scene["title"]}',
                f'STORYBOARD BEAT (VISUAL REFERENCE ONLY): {scene["tagalogVoiceoverBeat"]}',
                "",
                "EXACT TAGALOG DIALOGUE (FROM THE FULL SCRIPT)",
                scene["exactTagalogDialogue"],
                "",
                f'CAMERA: {scene["cameraMovement"]}',
                f'SOUND EFFECTS: {scene["soundEffects"]}',
                f'PACING: {scene["durationWarning"] or "Check the actual speech timing before exporting."}',
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
    scene_dir = directory / "scenes"
    scene_dir.mkdir(exist_ok=True)
    for scene in pack["scenes"]:
        per_scene = [
            f'KURI SCENE {scene["number"]:02d} — {scene["title"]}',
            "",
            "EXACT SPOKEN TAGALOG DIALOGUE",
            scene["exactTagalogDialogue"],
            "",
            "GOOGLE FLOW PROMPT — COPY THE FULL TEXT BELOW",
            scene["googleFlowCombinedPrompt"],
            "",
            "PACING NOTE",
            scene["durationWarning"] or "Verify speech timing and character consistency.",
            "",
        ]
        (scene_dir / f'scene-{scene["number"]:02d}-google-flow.txt').write_text(
            "\n".join(per_scene), encoding="utf-8"
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
, tokens[end - 1].group())
                else 2.5
            )
            pace_penalty = max(0, word_count - MAX_COMFORTABLE_WORDS_PER_SCENE) ** 2
            next_cost, remaining = best(scene_index + 1, end)
            candidates.append((
                spread_cost + boundary_penalty + pace_penalty + next_cost,
                (end,) + remaining,
            ))
        return min(candidates, key=lambda item: item[0])

    _, boundaries = best(0, 0)
    result = []
    start = 0
    for end in boundaries:
        result.append(script[tokens[start].start():tokens[end - 1].end()])
        start = end
    assert len(result) == parts
    assert [word for part in result for word in part.split()] == script.split()
    return result


def ambient_effect_for_scene(scene_prompt: str) -> str:
    """Select restrained, context-aware sound effects, not a music track."""
    text = scene_prompt.lower()
    if any(w in text for w in ("rain", "storm", "puddle", "petrichor")):
        return "Soft rain patter and gentle wet footsteps, well below KURI's voice"
    if any(w in text for w in ("space", "moon", "planet", "galaxy", "vacuum")):
        return "One subtle cinematic transition whoosh only; no sound propagating through vacuum"
    if any(w in text for w in ("ocean", "sea", "underwater", "river", "lake")):
        return "Soft water movement and a few restrained bubble or splash sounds"
    if any(w in text for w in ("laboratory", "science lab", "microscope", "experiment")):
        return "One soft equipment click and understated laboratory room tone"
    if any(w in text for w in ("forest", "tree", "jungle", "garden")):
        return "Soft rustling leaves and faint distant birds"
    if any(w in text for w in ("street", "city", "sidewalk", "crowd")):
        return "Very soft city room tone and subtle footsteps; no intelligible background speech"
    return "A soft clothing rustle or natural footsteps only when the action warrants it"


def make_flow_prompt(visual: str, dialogue: str, camera: str, effects: str) -> str:
    # json.dumps retains quotation marks and Tagalog spelling verbatim.
    exact_line = json.dumps(dialogue, ensure_ascii=False)
    return (
        "GOOGLE FLOW VIDEO GENERATION — one approximately 8-second vertical 9:16 scene. "
        "REFERENCE IMAGE: Upload the approved KURI image as the consistent character reference. "
        "VISUAL STYLE: premium cinematic 3D CGI, expressive facial animation and realistic adult "
        "Filipino character proportions. MAIN CHARACTER: " + KURI_REFERENCE +
        " VISUAL ACTION AND SETTING (use this for scenery, not audio): " + visual +
        " CAMERA MOVEMENT: " + camera +
        " SPEAKER: KURI alone, visibly speaking with natural Filipino lip movements, "
        "precise lip sync and believable expressions. "
        "VOICE CONSISTENCY ACROSS ALL SEVEN CLIPS: " + VOICE_DIRECTION +
        " EXACT TAGALOG DIALOGUE — speak the following words ONCE, in this order, "
        "without paraphrasing or adding another line: " + exact_line + ". "
        "AUDIO / SOUND EFFECTS: " + effects +
        ". Keep all effects subtle underneath the spoken line, no music, "
        "no second speaker and no generic announcer voice. "
        "If the visual scene brief mentions silence, that applies only to the scenery: "
        "KURI's specified spoken dialogue is required. "
        "No on-screen captions, logos, watermarks, titles or visible text."
    )


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

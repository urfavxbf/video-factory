"""Safe, reproducible Bakit Nga Ba? short renderer using pinned upstream PurffleShorts."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from bakit_nga_ba_music import generate_music

BASE = Path(__file__).resolve().parents[1]
EPISODES = BASE / "episodes"
STYLE_PROMPTS = {
    "3d": "High-end original 3D animated character film, stylized sculpted figures, glossy soft materials, consistent Maya and Nico, cinematic soft volumetric lighting",
    "anime": "Original Japanese-inspired 2D anime film artwork, hand-painted backgrounds, expressive cel-shaded faces, consistent Maya and Nico",
    "cinematic": "Original dramatic cinematic film still, cinematic lensing, natural film grain, expressive staging and emotional lighting",
    "realistic": "Photorealistic fictional Southeast Asian adult actors, natural skin texture, believable wardrobe, cinematic natural lighting",
}
VISUAL_SOURCES = {
    "pollinations": "pollinations,local",
    "local": "local",
    "stock": "pixabay,local",
}
RESOLUTIONS = {"720p": "720x1280", "1080p": "1080x1920"}

def load_episode(path: Path) -> dict:
    resolved = path.resolve()
    if not resolved.is_relative_to(EPISODES.resolve()):
        raise ValueError("Episode must be inside the checked-in episodes/ directory")
    data = json.loads(resolved.read_text(encoding="utf-8"))
    required = {"topic", "title", "hook_text", "scenes", "description", "hashtags", "tags", "language"}
    if not required <= data.keys():
        raise ValueError(f"Missing keys: {sorted(required - data.keys())}")
    if data["language"] != "fil":
        raise ValueError("Narration must use language=fil")
    if not 5 <= len(data["scenes"]) <= 12:
        raise ValueError("Expected 5-12 short scenes")
    for index, scene in enumerate(data["scenes"], start=1):
        for key in ("narration", "image_prompt", "search_query", "emphasis", "emoji"):
            if key not in scene:
                raise ValueError(f"Scene {index} missing {key}")
        if not isinstance(scene["narration"], str) or not scene["narration"].strip():
            raise ValueError(f"Scene {index} has empty narration")
        if not isinstance(scene["emphasis"], list):
            raise ValueError(f"Scene {index}: emphasis should be an array")
    return data

def prepare_episode(data: dict, style: str) -> dict:
    if style not in STYLE_PROMPTS:
        raise ValueError(f"Unsupported style: {style}")
    transformed = json.loads(json.dumps(data, ensure_ascii=False))
    for scene in transformed["scenes"]:
        scene["image_prompt"] = (
            f'{STYLE_PROMPTS[style]}. {scene["image_prompt"]} '
            "Single cinematic shot, no embedded text, no visible logos, vertical 9:16."
        )
    return transformed

def build_command(script_path: Path, visual_source: str, resolution: str) -> list[str]:
    if visual_source not in VISUAL_SOURCES or resolution not in RESOLUTIONS:
        raise ValueError("Invalid render settings")
    return [
        "purffle-shorts", "make", "--script", str(script_path),
        "--lang", "fil", "--style", "explainer",
        "--tts", "edge", "--voice", "fil-PH-AngeloNeural",
        "--aspect", "9:16", "--resolution", RESOLUTIONS[resolution],
        "--caption-style", "boxed", "--grade", "cinematic",
        "--transition", "fade", "--visuals", VISUAL_SOURCES[visual_source],
        "--duration", "58", "--no-upload", "--no-review",
    ]

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Bakit Nga Ba Shorts without uploading anywhere")
    parser.add_argument("--episode", default="episodes/cheaters-relationship.json")
    parser.add_argument("--style", choices=tuple(STYLE_PROMPTS), default="3d")
    parser.add_argument("--visual-source", choices=tuple(VISUAL_SOURCES), default="pollinations")
    parser.add_argument("--resolution", choices=tuple(RESOLUTIONS), default="720p")
    parser.add_argument("--dry-run", action="store_true", help="Validate and prepare without network access")
    args = parser.parse_args(argv)
    episode = load_episode(BASE / args.episode)
    prepared = prepare_episode(episode, args.style)
    runtime = BASE / ".bakitnga_runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    script_file = runtime / "script.json"
    script_file.write_text(json.dumps(prepared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    command = build_command(script_file, args.visual_source, args.resolution)
    if args.dry_run:
        print(f"Validated: {len(prepared['scenes'])} Filipino scenes / {args.style} / {args.resolution}.")
        print("CLI export-only: " + " ".join(command))
        return 0

    soundtrack = generate_music(runtime / "original_ambient.wav")
    env = os.environ.copy()
    env.update({
        "UPLOAD": "false", "PUBLISH_TO": "youtube", "LANGUAGE": "fil",
        "CHANNEL_NAME": "Bakit Nga Ba?", "TTS_ENGINE": "edge",
        "TTS_VOICE": "fil-PH-AngeloNeural",
        "VISUAL_STYLE": STYLE_PROMPTS[args.style],
        "MUSIC_DIR": str(runtime / "not_a_music_folder"),
        "MUSIC_FILE": str(soundtrack), "MUSIC_VOLUME": "0.12", "MUSIC_DUCKING": "true",
        "CAPTION_MAX_WORDS": "3", "CAPTION_POSITION": "center",
        "CAPTION_UPPERCASE": "false", "CAPTION_EMPHASIS": "true",
        "CAPTION_EMOJI": "false", "WATERMARK": "Bakit Nga Ba?",
        "END_CTA": "I-comment ang opinyon mo!",
        "OUTPUT_DIR": str(BASE / "bakitnga_output"), "DATA_DIR": str(runtime / "data"),
        "KEEP_VIDEOS": "true", "SCRIPT_REVIEW": "off",
        "ALSO_LANGUAGES": "", "LOCALIZE_METADATA": "",
    })
    print("Generating offline-authored Tagalog narration and AI-assisted visuals; uploads disabled.", flush=True)
    try:
        subprocess.run(command, cwd=BASE, env=env, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"Render failed with exit code {exc.returncode}. Check visual/TTS service quotas.", file=sys.stderr)
        return exc.returncode or 1
    output = BASE / "bakitnga_output"
    if not list(output.rglob("*.mp4")):
        print("No MP4 found in expected export directory.", file=sys.stderr)
        return 1
    print("MP4 generated under bakitnga_output/. No publishing attempted.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

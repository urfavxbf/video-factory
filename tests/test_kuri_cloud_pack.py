import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.kuri_cloud_pack import (
    NO_AUDIO_SUFFIX,
    build_review_pack,
    worker_origin,
    write_review_pack,
    request_json,
)


def valid_content():
    return {
        "title": "Bakit May Kakaibang Amoy ang Ulan?",
        "hook": "Ano ang amoy pagkatapos umulan?",
        "script": "Petrichor ay ang tawag sa amoy ng lupa tuwing pagkatapos ng ulan. "
        * 7,
        "caption": "Bakit nga ba may kakaibang amoy ang lupa kapag umuulan?",
        "hashtags": ["#BakitNgaBa", "#Science"],
        "sourceNote": "Fact-check this narration independently.",
    }


def valid_storyboard():
    return {
        "style": "3d",
        "scenes": [
            {
                "title": f"Discovering the Rain Scene {i}",
                "voiceoverBeat": f"Bakit kaya ganito ang amoy ng ulan sa eksenang {i}?",
                "prompt": (f"Original scene {i}: KURI explores a rainy tropical city street. "
                "Volumetric lighting and moving cinematic camera, with expressive 3D facial "
                "animation in a playful science investigation and continuity. "
                "Rich reflections of the wet surroundings, carefully composed closeups."
                + NO_AUDIO_SUFFIX),
            }
            for i in range(1, 8)
        ],
    }


class CloudPackTests(unittest.TestCase):
    def test_allowlist_works_for_worker_origins(self):
        self.assertEqual(
            worker_origin("https://example.workers.dev/"),
            "https://example.workers.dev",
        )
        for bad in (
            "http://example.workers.dev",
            "https://evil.example.com",
            "https://example.workers.dev@evil.example.com",
            "https://example.workers.dev/v1/generate",
            "https://example.workers.dev:444",
            "",
        ):
            with self.subTest(origin=bad):
                with self.assertRaises(ValueError):
                    worker_origin(bad)

    def test_review_pack_has_seven_consistent_3d_scenes(self):
        pack = build_review_pack(valid_content(), valid_storyboard(), "Amoy ng ulan")
        self.assertEqual(7, len(pack["scenes"]))
        self.assertEqual("KURI", pack["host"])
        self.assertFalse(pack["youtubeUploaded"])
        self.assertFalse(pack["videoGenerated"])
        for scene in pack["scenes"]:
            self.assertIn("golden-yellow hoodie", scene["googleFlowCombinedPrompt"])
            self.assertIn("spoken in natural Tagalog", scene["googleFlowCombinedPrompt"])
            self.assertNotIn(NO_AUDIO_SUFFIX, scene["googleFlowCombinedPrompt"])
            self.assertIn("No narration", scene["silentAnimationPrompt"])

    def test_bad_storyboard_is_rejected(self):
        storyboard = valid_storyboard()
        storyboard["scenes"].pop()
        with self.assertRaisesRegex(ValueError, "Exactly seven"):
            build_review_pack(valid_content(), storyboard, "Amoy ng ulan")

    def test_duplicate_scenes_rejected(self):
        storyboard = valid_storyboard()
        storyboard["scenes"][1] = storyboard["scenes"][0].copy()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_review_pack(valid_content(), storyboard, "Amoy ng ulan")

    def test_written_files_are_valid(self):
        pack = build_review_pack(valid_content(), valid_storyboard(), "Amoy ng ulan")
        with tempfile.TemporaryDirectory() as directory:
            write_review_pack(pack, Path(directory))
            disk = json.loads((Path(directory) / "kuri-review-pack.json").read_text())
            text = (Path(directory) / "kuri-flow-prompts.txt").read_text()
            self.assertEqual(pack, disk)
            self.assertEqual(text.count("GOOGLE FLOW PROMPT ("), 7)
            self.assertIn("FULL TAGALOG NARRATION", text)

    def test_worker_request_has_explicit_user_agent(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self, *args, **kwargs):
                return b'{"status":"ok"}'

        with patch("scripts.kuri_cloud_pack.urlopen", return_value=FakeResponse()) as opened:
            value = request_json(
                "https://example.workers.dev", "/v1/generate", "fake-for-test-only",
                {"topic":"A science topic","angle":""}
            )
            self.assertEqual("ok", value["status"])
            sent_request = opened.call_args.args[0]
            self.assertEqual(
                "VideoFactory-GitHub-Actions/1.0",
                sent_request.get_header("User-agent")
            )
            self.assertEqual(
                "Bearer fake-for-test-only", sent_request.get_header("Authorization")
            )

    def test_endpoint_allowlist_blocks_other_http_requests(self):
        with self.assertRaisesRegex(ValueError, "allowlisted"):
            request_json("https://example.workers.dev", "/health", "not-a-real-token", {})


if __name__ == "__main__":
    unittest.main()

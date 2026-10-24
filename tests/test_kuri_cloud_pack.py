import json
import re
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
    split_exact_narration,
    ambient_effect_for_scene,
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
            self.assertIn("EXACT TAGALOG DIALOGUE", scene["googleFlowCombinedPrompt"])
            self.assertIn("CAMERA MOVEMENT", scene["googleFlowCombinedPrompt"])
            self.assertIn("AUDIO / SOUND EFFECTS", scene["googleFlowCombinedPrompt"])
            self.assertIn("golden-yellow hoodie", scene["googleFlowCombinedPrompt"])
            self.assertIn(scene["exactTagalogDialogue"], scene["googleFlowCombinedPrompt"])
            self.assertNotIn(NO_AUDIO_SUFFIX, scene["googleFlowCombinedPrompt"])
            self.assertIn("No narration", scene["silentAnimationPrompt"])


    def test_exact_dialogue_reconstructs_all_narration_words(self):
        script = ('Bakit nga ba mabango ang ulan? Nararamdaman ito sa unang patak. '
                  'May mga molekulang nagbibigay ng amoy sa lupa. '
                  'Lumalabas ang ilang sangkap kapag umulan. '
                  'Madalas itong mas mapansin matapos ang tagtuyot. '
                  'May mga siyentipikong nag-aaral ng mga amoy na ito. '
                  'Hindi lahat ng ulan ay pareho ang amoy. '
                  'Tandaan: obserbahan ang amoy sa paligid nang ligtas.')
        segments = split_exact_narration(script)
        self.assertEqual(7, len(segments))
        self.assertEqual(script.split(), " ".join(segments).split())
        self.assertEqual(segments, split_exact_narration(script))
        self.assertTrue(all(segment.strip() for segment in segments))

    def test_exact_dialogue_when_fewer_sentence_boundaries(self):
        script = " ".join(f"salita{i}" for i in range(1, 120)) + "."
        segments = split_exact_narration(script)
        self.assertEqual(script.split(), " ".join(segments).split())
        self.assertEqual(len(segments), 7)

    def test_scene_dialogue_is_not_the_ai_summary(self):
        pack = build_review_pack(valid_content(), valid_storyboard(), "Amoy ng ulan")
        dialogue = " ".join(scene["exactTagalogDialogue"] for scene in pack["scenes"])
        self.assertEqual(pack["fullTagalogNarration"].split(), dialogue.split())
        self.assertNotEqual(
            pack["scenes"][0]["exactTagalogDialogue"],
            pack["scenes"][0]["tagalogVoiceoverBeat"],
        )
        self.assertTrue(pack["exactNarrationCoverage"])
        self.assertFalse(pack["mayExceedEightSecondClip"])

    def test_long_dialogue_sets_pacing_warning_without_dropping_words(self):
        data = valid_content()
        data["script"] = " ".join(f"salita{i}" for i in range(1, 181))
        pack = build_review_pack(data, valid_storyboard(), "Science topic")
        self.assertTrue(pack["mayExceedEightSecondClip"])
        self.assertTrue(any(scene["durationWarning"] for scene in pack["scenes"]))
        combined = " ".join(scene["exactTagalogDialogue"] for scene in pack["scenes"])
        self.assertEqual(data["script"].split(), combined.split())

    def test_context_aware_audio_without_extra_speaker(self):
        self.assertIn("rain", ambient_effect_for_scene("A rainy street").lower())
        self.assertIn("vacuum", ambient_effect_for_scene("Outer space vacuum"))
        pack = build_review_pack(valid_content(), valid_storyboard(), "Amoy ng ulan")
        for scene in pack["scenes"]:
            text = scene["googleFlowCombinedPrompt"]
            self.assertIn("KURI alone", text)
            self.assertIn("no music", text)
            self.assertIn("no second speaker", text)

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
            for index in range(1, 8):
                scene_text = (Path(directory) / "scenes" /
                              f"scene-{index:02d}-google-flow.txt").read_text()
                self.assertIn(pack["scenes"][index - 1]["exactTagalogDialogue"], scene_text)

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

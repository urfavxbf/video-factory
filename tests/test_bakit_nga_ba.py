"""Unit tests for the no-publish Filipino Shorts packaging (stdlib only)."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from render_bakit_nga_ba import (BASE, RESOLUTIONS, STYLE_PROMPTS, VISUAL_SOURCES, build_command,
                                load_episode, prepare_episode)
from bakit_nga_ba_music import DURATION, SAMPLE_RATE, generate_music

class BakitNgaBaTests(unittest.TestCase):
    def setUp(self):
        self.data = load_episode(BASE / "episodes/cheaters-relationship.json")

    def test_valid_filipino_episode_and_seo(self):
        self.assertEqual(self.data["language"], "fil")
        self.assertGreaterEqual(len(self.data["scenes"]), 10)
        self.assertIn("#BakitNgaBa", self.data["hashtags"])
        self.assertIn("cheat", self.data["title"].lower())
        self.assertTrue(all("Maya:" in x["image_prompt"] and "Nico:" in x["image_prompt"]
                            for x in self.data["scenes"]))

    def test_style_options_keep_narration_and_no_ai_text(self):
        first = self.data["scenes"][0]["narration"]
        for style in STYLE_PROMPTS:
            s = prepare_episode(self.data, style)
            self.assertEqual(s["scenes"][0]["narration"], first)
            self.assertIn("no embedded text", s["scenes"][0]["image_prompt"])
        self.assertEqual(self.data["scenes"][0]["narration"], first)

    def test_no_upload_is_mandatory_for_every_command(self):
        for source in VISUAL_SOURCES:
            for res in RESOLUTIONS:
                cmd = build_command(Path("script.json"), source, res)
                self.assertIn("--no-upload", cmd)
                self.assertIn("--script", cmd)
                self.assertIn("fil-PH-AngeloNeural", cmd)
                self.assertEqual(cmd[1], "make")
                self.assertNotIn("upload", cmd[:2])

    def test_path_escape_not_allowed(self):
        with self.assertRaises(ValueError):
            load_episode(Path("/etc/passwd"))

    def test_soundtrack_generated_and_wave_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = generate_music(Path(tmp) / "ambient.wav")
            with wave.open(str(path), "rb") as f:
                self.assertEqual(f.getframerate(), SAMPLE_RATE)
                self.assertEqual(f.getnchannels(), 1)
                self.assertEqual(f.getnframes(), SAMPLE_RATE * DURATION)

if __name__ == "__main__":
    unittest.main()

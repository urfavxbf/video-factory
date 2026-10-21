"""Offline tests: Cloudflare API is always mocked; no credentials required."""
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from content_engine import (  # noqa: E402
    build_content_pack,
    fallback_pack,
    parse_model_json,
    validate_pack,
)

SEED = {
    "title": "BAKIT ASUL ANG LANGIT?",
    "text": "Asul ang langit dahil mas naikalat ang blue light sa atmospera.",
}


def sample_payload():
    return {
        "title": "Bakit Asul ang Langit?",
        "narration": " ".join(
            ["Bakit kaya nagiging asul ang langit kapag maliwanag ang araw?"] * 8
        ),
        "caption": "Bakit asul ang langit? Alamin sa maikling video.",
        "hashtags": ["#AlamMoBa", "#ScienceFacts", "#YouTubeShorts"],
        "hooks": [
            "May dahilan kung bakit asul ang langit.",
            "Hindi pala kulay asul ang sikat ng araw.",
            "Naitanong mo na ba ito noong bata ka pa?",
            "Sa umaga asul pero sa gabi madilim.",
            "Anong nangyayari sa liwanag sa ating atmospera?",
        ],
        "visual_query": "blue sky clouds",
        "youtube_description": "Isang maikling paliwanag tungkol sa kulay ng langit.",
        "thumbnail_concept": "Makukulay na ulap at malinaw na title.",
        "audit_notes": "Tiyaking hindi lalampas sa oras ng audio.",
    }


class ContentEngineTests(unittest.TestCase):
    def test_valid_pack_passes_contract(self):
        result = validate_pack(sample_payload())
        self.assertTrue(result["ai_generated"])
        self.assertTrue(result["review_required"])
        self.assertEqual(len(result["hooks"]), 5)

    def test_title_is_safe_for_ffmpeg_drawtext(self):
        payload = sample_payload()
        payload["title"] = "Sky: it's 100% blue?"
        result = validate_pack(payload)
        self.assertNotIn(":", result["title"])
        self.assertNotIn("'", result["title"])
        self.assertNotIn("%", result["title"])

    def test_malformed_or_incomplete_ai_output_rejected(self):
        for invalid in ("oops", "[]", "{}", '{"title":"Only a title"}'):
            with self.subTest(invalid=invalid):
                with self.assertRaises((ValueError, json.JSONDecodeError)):
                    validate_pack(parse_model_json(invalid))

    def test_json_markdown_fence_supported(self):
        payload = parse_model_json("```json\n" + json.dumps(sample_payload()) + "\n```")
        self.assertEqual(payload["title"], "Bakit Asul ang Langit?")

    def test_short_narration_is_rejected(self):
        payload = sample_payload()
        payload["narration"] = "Hindi sapat."
        with self.assertRaises(ValueError):
            validate_pack(payload)

    def test_missing_credentials_falls_back_to_original_script(self):
        with patch.dict(os.environ, {}, clear=True):
            output = build_content_pack(SEED)
        self.assertFalse(output["ai_generated"])
        self.assertEqual(output["narration"], SEED["text"])

    def test_ai_request_uses_provider_and_validates_schema(self):
        model_response = {
            "success": True,
            "result": {"response": json.dumps(sample_payload())},
        }
        with patch.dict(
            os.environ,
            {
                "CLOUDFLARE_ACCOUNT_ID": "a" * 32,
                "CLOUDFLARE_API_TOKEN": "private-test-token",
            },
            clear=True,
        ), patch(
            "content_engine.urllib.request.urlopen",
            return_value=io.BytesIO(json.dumps(model_response).encode()),
        ) as urlopen:
            output = build_content_pack(SEED)
        self.assertTrue(output["ai_generated"])
        request = urlopen.call_args.args[0]
        self.assertIn("/ai/run/@cf/meta/", request.full_url)
        self.assertIn("private-test-token", request.get_header("Authorization"))
        self.assertNotIn("private-test-token", json.dumps(output))

    def test_json_mode_accepts_object_response(self):
        model_response = {
            "success": True,
            "result": {"response": sample_payload()},
        }
        with patch.dict(
            os.environ,
            {
                "CLOUDFLARE_ACCOUNT_ID": "a" * 32,
                "CLOUDFLARE_API_TOKEN": "test-token",
            },
            clear=True,
        ), patch(
            "content_engine.urllib.request.urlopen",
            return_value=io.BytesIO(json.dumps(model_response).encode()),
        ) as urlopen:
            output = build_content_pack(SEED)
        self.assertTrue(output["ai_generated"])
        sent = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(sent["response_format"]["type"], "json_object")

    def test_bad_ai_response_falls_back(self):
        with patch.dict(
            os.environ,
            {
                "CLOUDFLARE_ACCOUNT_ID": "a" * 32,
                "CLOUDFLARE_API_TOKEN": "test-token",
            },
            clear=True,
        ), patch(
            "content_engine.urllib.request.urlopen",
            return_value=io.BytesIO(b'{"success":true,"result":{"response":"not json"}}'),
        ):
            output = build_content_pack(SEED)
        self.assertFalse(output["ai_generated"])


if __name__ == "__main__":
    unittest.main()

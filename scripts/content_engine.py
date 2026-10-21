"""Cloudflare-backed, schema-validated content planning for fact-based Shorts.

The model drafts a content pack from an existing editorial seed. It does not
perform independent web research or factual verification; all outputs require
review before publishing.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

MODEL = "@cf/meta/llama-3.1-8b-instruct-fp8"
_HASHTAG = re.compile(r"^#[A-Za-z0-9_]{2,40}$")
_SAFE_TITLE = re.compile(r"[^\w\s.!?\-]", re.UNICODE)

SYSTEM_PROMPT = """You are a Filipino YouTube Shorts strategist, natural Tagalog
storyteller, factual editor, and retention-focused video director. Create an
original 45-second content pack using ONLY the factual seed supplied by the
user. Do not invent facts, references, metrics, scientific claims, or sources.
Use a compelling 0-3 second hook, progressive development, clear payoff,
and optional natural CTA. Prefer 80-110 spoken Filipino words; no repetitive
filler or false suspense. Generate five psychologically distinct, honest hooks
(curiosity, verified surprise, empathy, contrast, mystery), pick one for the
opening, and self-review for clarity, pacing, and misleading claims.
The title must contain no quotation marks, colons, percent symbols, or commas.
The visual_query MUST be a simple 2-6 word English stock-footage search phrase.
Return ONLY one JSON object with these exact keys:
title (string, max 60 characters),
narration (string, 70-125 words),
caption (string, Tagalog, max 240 chars),
hashtags (array of 3-5 hashtag strings),
hooks (array of exactly 5 short Filipino hook strings),
visual_query (string, English keywords),
youtube_description (string, max 450 chars),
thumbnail_concept (string, max 220 chars),
audit_notes (string, max 300 chars).
No markdown. No new factual assertions beyond the seed. All content must be
suitable for TikTok and YouTube Shorts."""


def fallback_pack(seed: dict[str, str]) -> dict[str, Any]:
    """Keep the previous video pipeline working when inference is unavailable."""
    return {
        "title": seed["title"],
        "narration": seed["text"],
        "caption": f"Alam mo ba? {seed['title']} Alamin ang kuwento sa video!",
        "hashtags": ["#AlamMoBa", "#FilipinoFacts", "#ScienceFacts", "#YouTubeShorts"],
        "hooks": [],
        "visual_query": "",
        "youtube_description": seed["text"][:450],
        "thumbnail_concept": f"Bold readable title: {seed['title']}",
        "audit_notes": "Curated source script; independent fact and licensing review still required.",
        "ai_generated": False,
        "model": None,
        "review_required": True,
    }


def parse_model_json(response_text: str) -> dict[str, Any]:
    """Permit a fenced response but reject malformed or non-object JSON."""
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^\x60{3}(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*\x60{3}$", "", cleaned)
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("AI response is not a JSON object")
    return parsed


def validate_pack(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the LLM contract before any output reaches FFmpeg or Pixabay."""
    names = (
        "title", "narration", "caption", "visual_query",
        "youtube_description", "thumbnail_concept", "audit_notes",
    )
    for name in names:
        if not isinstance(payload.get(name), str) or not payload[name].strip():
            raise ValueError(f"Missing or invalid {name}")
    title = _SAFE_TITLE.sub("", payload["title"]).strip()
    title = re.sub(r"\s+", " ", title)
    if not 5 <= len(title) <= 60:
        raise ValueError("Invalid sanitized title length")
    narration = re.sub(r"\s+", " ", payload["narration"]).strip()
    if not 70 <= len(narration.split()) <= 125:
        raise ValueError("Narration outside 70-125 word budget")
    if len(payload["caption"]) > 240 or len(payload["youtube_description"]) > 450:
        raise ValueError("Publishing copy is too long")
    if len(payload["thumbnail_concept"]) > 220 or len(payload["audit_notes"]) > 300:
        raise ValueError("Concept or audit too long")
    visual_query = re.sub(r"[^a-zA-Z0-9 ]", "", payload["visual_query"]).strip()
    visual_query = re.sub(r"\s+", " ", visual_query)
    if not 3 <= len(visual_query) <= 75:
        raise ValueError("Invalid Pixabay visual query")
    hooks = payload.get("hooks")
    if not isinstance(hooks, list) or len(hooks) != 5 or any(
        not isinstance(hook, str) or not 5 <= len(hook.strip()) <= 220
        for hook in hooks
    ):
        raise ValueError("Expected exactly five short hooks")
    hashtags = payload.get("hashtags")
    if not isinstance(hashtags, list) or not 3 <= len(hashtags) <= 5 or any(
        not isinstance(tag, str) or not _HASHTAG.fullmatch(tag)
        for tag in hashtags
    ):
        raise ValueError("Invalid hashtags")
    return {
        "title": title,
        "narration": narration,
        "caption": payload["caption"].strip(),
        "hashtags": hashtags,
        "hooks": [hook.strip() for hook in hooks],
        "visual_query": visual_query.lower(),
        "youtube_description": payload["youtube_description"].strip(),
        "thumbnail_concept": payload["thumbnail_concept"].strip(),
        "audit_notes": payload["audit_notes"].strip(),
        "ai_generated": True,
        "model": MODEL,
        "review_required": True,
    }


def request_cloudflare_pack(
    seed: dict[str, str], account_id: str, api_token: str
) -> dict[str, Any]:
    """One bounded API request. Credentials never go into application artifacts."""
    body = json.dumps({
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"FACTUAL SEED TOPIC: {seed['title']}\n"
                f"VERIFIED EDITORIAL SEED (do not add facts):\n{seed['text']}"
            )},
        ],
        "max_tokens": 1500,
        "temperature": 0.55,
        "stream": False,
    }).encode("utf-8")
    url = (
        "https://api.cloudflare.com/client/v4/accounts/"
        + account_id + "/ai/run/" + MODEL
    )
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "User-Agent": "video-factory/2.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        result = json.load(response)
    if result.get("success") is not True:
        raise ValueError("Cloudflare AI request was unsuccessful")
    output = result.get("result")
    if not isinstance(output, dict) or not isinstance(output.get("response"), str):
        raise ValueError("Cloudflare AI returned no text response")
    return validate_pack(parse_model_json(output["response"]))


def build_content_pack(seed: dict[str, str]) -> dict[str, Any]:
    """Use Workers AI when configured; fail over to the existing curated script."""
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    if not account_id or not api_token:
        print("Workers AI credentials unavailable: using original curated script.")
        return fallback_pack(seed)
    # The account ID belongs in a URL path; disallow malformed configuration.
    if not re.fullmatch(r"[a-fA-F0-9]{32}", account_id):
        print("Workers AI account configuration invalid: using curated script.")
        return fallback_pack(seed)
    try:
        pack = request_cloudflare_pack(seed, account_id, api_token)
        print("AI content pack generated. Editorial fact review required.")
        return pack
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, OSError) as exc:
        # Deliberately avoid printing provider error bodies or credentials.
        print(f"AI content unavailable ({type(exc).__name__}); using curated script.")
        return fallback_pack(seed)

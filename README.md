# Video Factory — Filipino Fact Shorts

This repository generates one vertical MP4 fact-story video per scheduled GitHub Actions run.

## What it does
- Chooses a pre-written Filipino science fact based on the date.
- Generates Filipino narration with gTTS (internet required).
- Creates timed subtitles and burns them into a 720×1280 MP4 with FFmpeg.
- Uploads the MP4 and source narration as a GitHub Actions artifact.

## Automation
- Scheduled daily at 01:00 Philippine time (17:00 UTC).
- You can also run it manually from **Actions → Generate Fact Video → Run workflow**.
- Open the completed run and download the `factstory-video` artifact.

## Notes
- This creates a video artifact; it does **not** publish to TikTok automatically.
- The initial visual is a designed background with title and subtitles, not licensed stock footage.
- gTTS is an unofficial interface to Google Translate's text-to-speech service. Check applicable terms and commercial-use rights before monetizing.
- Facts are pre-written in `scripts/generate.py`; review and update them as needed.

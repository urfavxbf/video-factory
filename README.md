# Video Factory — Filipino Fact Shorts

This repository generates one vertical MP4 fact-story video per scheduled GitHub Actions run.

## What it does
- Chooses a pre-written Filipino science fact based on the date.
- Generates Filipino narration with gTTS (internet required).
- Creates shorter, bold, high-contrast mobile subtitles and burns them into the video.
- Adds an opening “ALAM MO BA?” hook, a title card, and subtle animated geometric background accents.
- Renders a 720×1280 vertical MP4 and uploads it with the narration, subtitles, and metadata as a GitHub Actions artifact.

## Automation
- Scheduled daily at 01:00 Philippine time (17:00 UTC).
- You can also run it manually from **Actions → Generate Fact Video → Run workflow**.
- Open the completed run and download the `factstory-video` artifact. The artifact is temporary and is retained for 7 days.

## Notes
- This creates a video artifact; it does **not** publish to TikTok automatically.
- The visuals are generated with FFmpeg shapes and motion; this version does not use stock footage or AI-generated images.
- gTTS is an unofficial interface to Google Translate's text-to-speech service. Check applicable terms and commercial-use rights before monetizing.
- Facts are pre-written in `scripts/generate.py`; review and update them as needed.

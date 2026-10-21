# Video Factory — Filipino Fact Shorts

This repository generates one vertical MP4 Filipino science-fact video per scheduled GitHub Actions run, designed for reuse on TikTok and YouTube Shorts.

## What it does
- Rotates through curated Filipino factual seeds by date (no more hard-coded déjà vu episode).
- Optionally calls Cloudflare Workers AI **once per run** to draft an original Filipino narration, five hooks, title, description, thumbnail concept, caption, hashtags, and Pixabay keywords. Requires the existing `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` GitHub Actions secrets.
- Validates the structured AI response and **falls back to the original curated script** if the AI is unavailable or returns invalid content. Content is never auto-published; human factual/editorial review is required.
- Uses expanded narration written to target approximately 45 seconds; actual duration depends on the generated voice audio.
- Generates Filipino narration with gTTS.
- Creates short, bold, high-contrast mobile subtitles timed to the narration and burns them into the video.
- Adds an opening “ALAM MO BA?” hook and a title overlay.
- Uses topic-matched Pixabay stock video when `PIXABAY_API_KEY` is configured, including AI-suggested search keywords where available.
- If Pixabay is not configured, returns no usable footage, is rate-limited, or download fails, uses a moving animated geometric background. No still-image backgrounds are used.
- Renders a 720×1280 vertical MP4 and uploads the narration, subtitles, `metadata.json`, and `content-pack.json` as a GitHub Actions artifact.

## Automation
- Scheduled daily at 01:00 Philippine time (17:00 UTC).
- You can also run it manually from **Actions → Generate Fact Video → Run workflow**.
- Open the completed run and download the `factstory-video` artifact. The artifact is retained for 7 days.

## Enable Pixabay stock footage (optional, free API key)
1. Create a free Pixabay account and get an API key from [Pixabay API](https://pixabay.com/api/docs/).
2. In this GitHub repository, open **Settings → Secrets and variables → Actions → New repository secret**.
3. Add a secret named `PIXABAY_API_KEY` and paste the key there. Never put the key in source code or chat.
4. Run **Actions → Generate Fact Video → Run workflow**.

Pixabay is tried first using one topic-matched stock clip per video. The script downloads at most one clip and skips clips larger than 80 MB. If no clip is available, the animated geometric background is used automatically. Review the [Pixabay license summary](https://pixabay.com/service/license-summary/) and clip-specific restrictions before commercial use.

## Notes
- This creates a video artifact; it does **not** publish automatically to TikTok or YouTube.
- The target is approximately 45 seconds, not a guaranteed exact duration; duration depends on the generated narration.
- The project uses GitHub Actions, FFmpeg, and gTTS without requiring a paid video-generation API. gTTS is an unofficial interface to Google Translate's text-to-speech service; check applicable terms and commercial-use rights before monetizing.
- Seed facts remain in `scripts/generate.py`. AI rewriting is **not independently fact-checked**: review the script and any claims before uploading.
- Android app MP4 rendering is a **separate** local implementation; this first AI integration changes only the GitHub Actions/Python video generator. See [AI content pipeline](docs/CONTENT_PIPELINE.md).

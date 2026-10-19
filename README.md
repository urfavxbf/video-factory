# Video Factory — Filipino Fact Shorts

This repository generates one vertical MP4 fact-story video per scheduled GitHub Actions run.

## What it does
- Chooses a pre-written Filipino science fact based on the date.
- Generates Filipino narration with gTTS (internet required).
- Creates shorter, bold, high-contrast mobile subtitles and burns them into the video.
- Adds an opening “ALAM MO BA?” hook and bold, high-contrast captions.
- Tries one topic-matched Pixabay stock video first when `PIXABAY_API_KEY` is configured; if unavailable or rate-limited, falls back to the Cloudflare AI-image pipeline and then the animated geometric background.
- When Cloudflare Workers AI credentials are configured, generates three story-matched AI images and animates them with gentle camera movement if Pixabay is unavailable.
- Renders a 720×1280 vertical MP4 and uploads it with the narration, subtitles, and metadata as a GitHub Actions artifact.

## Automation
- Scheduled daily at 01:00 Philippine time (17:00 UTC).
- You can also run it manually from **Actions → Generate Fact Video → Run workflow**.
- Open the completed run and download the `factstory-video` artifact. The artifact is temporary and is retained for 7 days.

## Optional: enable Pixabay stock footage (free API key)
1. Create a free Pixabay account and get an API key from [Pixabay API](https://pixabay.com/api/docs/).
2. In this GitHub repository, open **Settings → Secrets and variables → Actions → New repository secret**.
3. Add a secret named `PIXABAY_API_KEY` and paste the key there. Never put the key in source code or chat.
4. Run **Actions → Generate Fact Video → Run workflow**.

Pixabay is tried first using one topic-matched stock clip per video. If the key is missing, the API returns no usable clip, a request is rate-limited, or the download fails, generation continues with the existing Cloudflare AI-image path and then the animated-background fallback. Narration text, gTTS generation, SRT caption timing/style, and title overlays are unchanged. Pixabay footage is stock video, not AI-generated video; review the [Pixabay license summary](https://pixabay.com/service/license-summary/) and clip-specific restrictions before commercial use. The script downloads at most one clip and skips clips larger than 80 MB.

## Optional: enable contextual AI images (free tier may be available)
1. Create/sign in to a Cloudflare account and enable Workers AI.
2. In Cloudflare, obtain your Account ID and create an API token with permission to run Workers AI models.
3. In this GitHub repository, open **Settings → Secrets and variables → Actions → New repository secret**.
4. Add `CLOUDFLARE_ACCOUNT_ID` with your Cloudflare Account ID and `CLOUDFLARE_API_TOKEN` with the API token.
5. Run **Actions → Generate Fact Video → Run workflow**. With valid secrets, each video attempts to generate three images matched to that day's science fact. If generation fails or the secrets are missing, the workflow uses the existing animated background instead.

**Security:** Never put the API token in source code, README, issues, or chat. Store it only as a GitHub Actions secret. AI generation uses Cloudflare's model API and is subject to account availability, rate limits, and current pricing/quotas; check Cloudflare's dashboard before relying on a free allocation.

## Notes
- This creates a video artifact; it does **not** publish to TikTok automatically.
- Without `PIXABAY_API_KEY` and Cloudflare secrets, visuals use FFmpeg shapes and motion. With Pixabay configured, the workflow tries stock footage first; if unavailable, it tries AI-generated scene images when Cloudflare secrets are configured.
- gTTS is an unofficial interface to Google Translate's text-to-speech service. Check applicable terms and commercial-use rights before monetizing.
- Facts are pre-written in `scripts/generate.py`; review and update them as needed.

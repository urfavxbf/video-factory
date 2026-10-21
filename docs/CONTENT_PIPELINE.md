# AI-assisted content generation (Phase 1)

## What works

The GitHub Actions generator (not yet the Android app) can use Cloudflare
Workers AI to draft a **content pack** from an existing curated fact seed.
The single model request combines the five stages: hook options, short-form
script, title/cover idea, metadata, and retention audit.

The renderer stays exactly where it was: gTTS creates Filipino audio, Pixabay
provides up to three moving clips, FFmpeg makes the MP4 and SRT captions. An
animated background is used if no usable footage downloads.

The output artifact `factstory-video` now includes:

- `factstory-YYYY-MM-DD.mp4` — video with audio and subtitles
- `narration.mp3` — voice track
- `captions.srt` — approximate chunk timing based on audio duration
- `metadata.json` — title, script, hook options, description, hashtags, render details
- `content-pack.json` — normalized AI content pack, or a labeled curated fallback

## How to use it on a phone

1. In GitHub open **urfavxbf/video-factory → Actions → Generate Fact Video**.
2. Select **Run workflow** (after this PR is merged to main).
3. Download the `factstory-video` artifact after the run succeeds.
4. Watch the full MP4 and review its factual claims, pronunciation, subtitles,
   stock-footage relevance, and copyright/licensing before posting.
5. Copy the title/caption/hashtags from `metadata.json` or `content-pack.json`.

## Secrets and privacy

The workflow already passes these repository secrets to the Python process:

- `CLOUDFLARE_ACCOUNT_ID`: a 32-character Cloudflare account ID.
- `CLOUDFLARE_API_TOKEN`: a token with Workers AI permissions.
- `PIXABAY_API_KEY`: Pixabay footage access.

Never put credentials in Kotlin, an APK, prompts, commits, or logs. If one or
both Cloudflare secrets are absent/invalid, the generator retains the previous
prewritten script and marks `ai_generated: false`. A valid provider response
sets `ai_generated: true` and includes the model name. The separate
`narration_source` field identifies whether the actual voice-over script came
from the AI or the curated seed. If the AI narration is too short or too long,
the app retains its valid AI hooks/discovery metadata but uses the safe seed
narration for the video. No errors expose tokens.

Cloudflare Workers AI has a free allocation, but it is quota-limited, not
unconditionally unlimited or always free. The workflow makes a maximum of one
Workers AI inference request per run. Inspect account usage if on a paid plan.

## Editorial safety

The model is explicitly constrained to paraphrase and reorganize the curated
seed. It is **not** a fact-checking engine, source retrieval system, or
guarantee of scientific accuracy. Both generated and fallback packs mark
`review_required: true`. Script scores and AI audits are subjective, not
measured retention data. Publish only after a human verifies important claims.

The title is sanitized to remove FFmpeg filter delimiters. Pixabay queries and
output fields are schema-validated; invalid AI results fall back to the seed.

## Automated testing

Run `python -m unittest discover -s tests -v` or use the GitHub PR workflow
`Validate AI Content Pipeline`. Tests mock the Cloudflare HTTP response,
check the schema, verify the fallback and that secrets are not embedded in
generated content.

## Follow-up milestones

- **Phase 2:** Attach trusted sources to each seed, verify new topics and
  add an editorial review workflow before accepting open-ended research.
- **Phase 3:** Choose distinct Pixabay clips per storyboard scene; align
  captions to the actual spoken words and correct pacing to 45 seconds.
- **Phase 4:** Build a protected backend API that lets the Android app request
  a content pack securely. Do not embed the Cloudflare token into an APK.
  Add real narration/audio muxing to the local Android MP4 encoder.
- **Phase 5:** Optional analytics feedback and deduplication with explicit
  publishing approval. Automatic uploads are intentionally out of scope.

Existing Android projects live under `app/` and `android-app/` and are
unchanged in Phase 1.

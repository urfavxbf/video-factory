# Filipino Creator Kit — CapCut + ElevenLabs

This feature is an **editorial assistant**, not an automatic uploader or finished-video renderer. A creator supplies a topic. Cloudflare Workers AI drafts original Filipino narration, title, caption, hashtags and three scene-specific visual searches. On request, it also creates a seven-scene Google Flow storyboard with selectable visual styles. The Android app searches **real Pixabay images/videos**, provides contributor/source links and saves files through Android's native Save dialog for manual CapCut editing.

## What is generated?

- AI drafts: original script, hook, title, caption, hashtags, three scene-specific English stock-search phrases.
- Stock media: Pixabay images and videos (not AI-generated art).
- Google Flow storyboard: seven distinct, approximately eight-second vertical 9:16 video generation prompts, with a shared subject reference, sequential voice-over beats, and a per-episode style choice: **2D Animated, 3D Animation, Japanese Anime, Realistic, or Cinematic**. Each prompt includes the selected visual style and can be copied independently; the complete storyboard can be copied or saved to `.txt`. This feature generates *instructions for Google Flow*, not finished video or a claim that clips were generated.
- Background-music suggestions: three episode-specific moods with verified Mixkit category links and official YouTube Audio Library access. Music is selected and downloaded from the external provider, not downloaded directly inside the app; no new API credential is required.
- Creator: verify all factual claims, use ElevenLabs for narration, download and edit media in CapCut, and publish manually after license/relevance review.
- No template-based fallback, unsupported claims of verification, or automatic publication.

## Backend setup (required for live generation)

The Worker must be deployed by the owner to their Cloudflare account. Repo CI cannot deploy a Worker without an account connection. The APK contains **no Cloudflare or Pixabay secrets**.

1. Enable Workers AI on Cloudflare and install Node.js.
2. From the worker directory run: npx wrangler login, then npx wrangler deploy.
3. Set Worker secrets individually: npx wrangler secret put APP_ACCESS_TOKEN (owner-issued long random token, at least 12 characters) and npx wrangler secret put PIXABAY_API_KEY (Pixabay developer key).
4. Check your deployed Worker's /health endpoint.
5. In Android app → Private AI Connection, paste the HTTPS Worker URL and APP_ACCESS_TOKEN. Tap Save private connection. The access token is stored using Android Keystore encryption.

Keep all credentials out of GitHub files and chat. Check Workers AI/Pixabay quotas and terms; usage is not guaranteed to be free.

### GitHub deployment permission troubleshooting

If **Deploy Content Kit Worker** says `No access to the specified resource`, secrets are present but that does not prove the Cloudflare token is authorized. In Cloudflare, verify the `CLOUDFLARE_API_TOKEN` has a **Workers Editor / Workers Scripts Edit (Write)** permission for the same Cloudflare account as `CLOUDFLARE_ACCOUNT_ID`. For a first-time Worker creation, broader Workers-product Admin permission may be required if the scoped token only permits editing existing Workers. Update the GitHub secret if you rotate/regenerate a token. Do not share the token value in issues or chat. The workflow now uploads code and Worker secrets together using Wrangler `deploy --secrets-file` to avoid pre-deployment secret-upload failures.


## Mobile workflow

1. Enter your topic and optional audience/editorial angle. Tap Generate original content kit.
2. Review the new title, hook, Filipino voice-over, caption and hashtags. Review important factual claims.
3. Tap Copy under ElevenLabs script; open ElevenLabs and choose a Filipino-capable voice.
4. Pick a suggested scene and browse Videos or Pictures. Results are pulled from Pixabay, not invented.
5. Open Source / license for the individual contributor page. Tap Save image/video; choose a phone folder.
6. In **Background Music for CapCut**, review the recommended mood and two alternative moods. Open Mixkit's mood-specific library (or YouTube Studio Audio Library), preview tracks, and download a suitable MP3 **on the official music site**. Read the track's applicable license before using it; attribution may be required for tracks in the YouTube Audio Library.
7. Import downloaded footage, ElevenLabs narration, and your selected music file into CapCut. Keep background music low enough not to drown out the voice-over; edit pacing, graphics, transitions, narration and subtitles.
8. For AI-generated clips, open **05 / Google Flow Video Storyboard**, choose 2D Animated, 3D Animation, Japanese Anime, Realistic, or Cinematic, then tap **Generate Google Flow prompts**. Copy an individual scene prompt into Google Flow, generate clips separately, and repeat using the same reference character. You can copy all seven prompts or export the storyboard `.txt`. Changing the style discards the previous storyboard until regeneration. The style selection is for *video prompts*, not voice-over.
9. Check timing against the real ElevenLabs narration. Seven 8-second clips are a rough storyboard estimate, not guaranteed video duration or word alignment.
10. Export from CapCut and publish manually, only after checking rights and any required synthetic-media disclosure.

You can also save the full text kit as a .txt file. Google Flow storyboards have a separate `.txt` export and an explicit manual generation step so no extra Workers AI calls are made for users who only want stock footage. Music mood recommendations, official category links, and licensing information are included. The app keeps up to 15 recent title strings locally to reduce exact repeats; it does not yet provide independent source research or a complete editing history. AI output should never be presented as automatically verified.

## Automated checks

- Worker: node --test worker/test/*.test.mjs
- Android: build-android GitHub Actions job creates a debug APK and also runs on pull requests.
- Source verification, real Worker credentials, upload rights and a real-media download must be reviewed separately.

## Primary policies

- Mixkit Free Stock Music: https://mixkit.co/free-stock-music/ — browse/download on Mixkit. License: https://mixkit.co/license/modal/musicFree/ — commercial YouTube use permitted under its terms, but no music redistribution by itself, Content ID registration, or claiming ownership. Check terms per track before publication.
- YouTube Audio Library: https://www.youtube.com/audiolibrary — music downloads through YouTube Studio; filter on attribution and add artist credits if required. https://support.google.com/youtube/answer/3376882
- Pixabay API: https://pixabay.com/api/docs/ — contributor/source attribution, cache search results 24 hours, no systematic bulk downloads. Check individual Content License.
- YouTube channel monetization policy: https://support.google.com/youtube/answer/1311392 — repetitive or mass-produced content risks monetization; substantial original creative work matters.
- Google Flow: https://labs.google/fx/tools/flow — check Flow availability, generation quotas, copyright, safety requirements and export restrictions in your region. Prompts are not video clips.
- YouTube synthetic disclosure: https://support.google.com/youtube/answer/14328491
- ElevenLabs: https://elevenlabs.io/docs/overview/capabilities/text-to-speech — check your chosen plan's commercial-use rights.

No claim of guaranteed channel monetization or earnings.

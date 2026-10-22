# Bakit Nga Ba? Shorts Generator (Tagalog)

This integration runs the MIT-licensed [PurffleShorts](https://github.com/Chamanrajragu/purffle-shorts) CLI at a **pinned upstream commit**. It lives alongside the existing Android Creator Kit and scheduled fact-video workflow without changing either.

## Run from GitHub (after the PR is merged)

Open **Actions → Bakit Nga Ba - Render Short (No Upload) → Run workflow**.

Select the `cheaters-relationship` episode, the **3d** visual style, **pollinations** images, and 720p resolution. GitHub Actions synthesizes Tagalog narration with `fil-PH-AngeloNeural`, produces karaoke-like synced captions, creates an original synthesized instrumental bed, and tries to render 9:16 video. Find the MP4, cover image, captions, script and metadata in the run's **Artifacts** section. Each artifact is retained seven days. **YouTube, TikTok and Instagram uploads are disabled**; the workflow only uploads a private build artifact to GitHub.

There are also **anime**, **cinematic** and **realistic** style presets. They change generated visual *prompts*, not the narration. Default 3D style produces animated camera moves over 3D-look still images, **not true rigged 3D animation**.

## Costs, quality and fallbacks

PurffleShorts is open source, but generating illustrations and hosting runs are not unlimited:
- Default **Pollinations** AI images may be rate-limited without a paid or free provider key. For many scenes, failures automatically fall back to local images or animated geometric backgrounds. That fallback is *not* a 3D animation.
- For more reliable visual assets, supply self-created licensed images under `media/` and choose **local**, or add `POLLINATIONS_API_KEY` to GitHub Actions repository secrets if you have access to that service.
- **stock** uses Pixabay only when `PIXABAY_API_KEY` has been configured as a GitHub Actions secret. Stock footage will not match 3D animation styling.
- No paid language-model API key is required for this episode because its complete original script is checked in. The free Edge TTS service still requires network access and can fail if it is blocked or unavailable.
- The original procedural instrumental is synthesized by our own Python code without any third-party audio samples. It is a soft background track, not commercial music.
- GitHub-hosted runners have usage limits. Do not confuse free software with unlimited computing or AI-service quotas.

## Reproduce on desktop

Install FFmpeg, Python 3.12, then install the pinned PurffleShorts dependency:

```bash
python -m pip install "git+https://github.com/Chamanrajragu/purffle-shorts.git@baaba035be13fa4aa2ebc31951d58ea141e2d74c"
python scripts/render_bakit_nga_ba.py --dry-run
python scripts/render_bakit_nga_ba.py --style 3d --visual-source pollinations --resolution 720p
```

An MP4 is written under `bakitnga_output/`. The checked-in episode is `episodes/cheaters-relationship.json`. To produce another episode, add a valid Tagalog JSON with 5–12 scenes. Keep character identity and outfits consistent in each scene's `image_prompt`.

For local assets, set `MEDIA_DIR` to your directory of licensed images/clips (or use `media/`), with descriptive names matching `search_query` keywords. Do not commit assets without redistribution rights.

## Editorial and safety checklist

1. Listen to Tagalog pronunciation and adjust the narration if needed.
2. Watch the entire exported MP4, especially caption-safe zones and scene/character continuity.
3. Review references and claims; relationship psychology has no universal explanation.
4. Check the visual providers' rights, current terms, watermarks, and any monetization restrictions.
5. Publish manually only after approval. The workflow does not possess social account publishing tokens.

## Upstream & security

Upstream: `Chamanrajragu/purffle-shorts`, MIT license, git SHA `baaba035be13fa4aa2ebc31951d58ea141e2d74c`. The third-party package is installed only at render runtime; we do not fork or modify its code. All generated JSON/MP4 files are ignored from source by default and saved only to Action artifacts. The Action grants itself **read-only repository permissions**, and the renderer hard-codes `UPLOAD=false` plus `--no-upload` independently.

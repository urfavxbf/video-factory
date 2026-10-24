# Phone-only KURI 3D Scene Packs — GitHub Actions + Cloudflare

No PC, laptop, n8n server, paid VPS, or local Docker installation is required.
GitHub-hosted runners call the existing **Video Factory Content Kit** Cloudflare Worker.
The resulting ZIP can be downloaded from GitHub Actions using an Android browser.

## Generate from your Android phone

1. Open **[GitHub Actions → Generate KURI 3D Scene Pack](https://github.com/urfavxbf/video-factory/actions/workflows/generate-kuri-pack.yml)**.
2. Select **Run workflow**, choose **main**, enter a Tagalog topic and optional creative angle; select **Run workflow**.
3. Open the run after completion, scroll to **Artifacts**, and download **kuri-3d-scene-pack-N** (ZIP).
4. In the ZIP, open `kuri-flow-prompts.txt` for the seven Google Flow prompts (each includes an animation direction and a Tagalog voiceover beat). `kuri-review-pack.json` contains structured metadata for later rendering integrations.
5. Generate scene videos in a compatible AI video product (with the approved KURI image reference), and review Tagalog narration, licensing and claims before publishing.

## Configuration

The workflow uses the public URL of the existing deployed Cloudflare Worker. Override it by setting the GitHub Actions repository variable `CONTENT_KIT_WORKER_URL` to the origin of your own trusted `*.workers.dev` Worker. The Python runner rejects non-HTTPS/non-`workers.dev` hosts to prevent accidental bearer-token leakage.

The token **APP_ACCESS_TOKEN** must be set as a GitHub repository secret or the existing **production** environment secret, and must match the deployed Worker's secret. The workflow uses `environment: production` to align with the project's existing Cloudflare deploy job. Do **not** enter secrets into Run workflow inputs or source code.

## What it really automates

- Generates an original Tagalog script and metadata through `POST /v1/generate`.
- Calls `POST /v1/storyboard` for exactly seven 3D scene directions.
- Adds KURI visual reference and deep masculine Metro Manila Tagalog voice direction to Google Flow prompts.
- Packages the outputs as GitHub Artifacts kept for seven days.
- Enforces endpoint and origin allowlists, output validation and no publishing.
- Runs only when clicked; it has **no schedule** to avoid surprise AI usage.

The user still needs a compatible video generation service, and approved KURI **reference image** must be supplied to that service for better identity consistency. This workflow **does not make video clips, an ElevenLabs recording, or an MP4**, and does not claim that Google Flow can be automated through an undocumented interface.

## Cost & accessibility

GitHub Actions on a public repository uses GitHub-hosted runners subject to GitHub usage policies. Cloudflare Workers AI may have plan-specific quotas or fees. The content is in a public repository's workflow artifacts; do not put confidential personal data in prompts or artifacts. For a private creative pipeline, move to a private repository and review associated GitHub Actions quotas.

## n8n status

The optional n8n Compose setup remains in `n8n/` for future deployments to n8n Cloud or a VPS. It is **not required** for this Android-only workflow.

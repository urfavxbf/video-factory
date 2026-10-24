# KURI × n8n — private automation orchestration

This folder adds an **importable n8n workflow** to the existing Video Factory project. It calls the existing Cloudflare Worker to create an original Tagalog script and a seven-scene, 3D-oriented Google Flow storyboard. It produces **a review-ready JSON pack, NOT rendered videos**. Nothing auto-uploads to YouTube.

## Current milestone

Manual trigger → validate episode settings → `POST /v1/generate` → validate script → `POST /v1/storyboard` → seven KURI scene prompts, Filipino narration and metadata for editorial review.

The Worker's two authenticated endpoints already exist in `worker/src/index.mjs`. They require a working deployment, Workers AI availability, and the Worker's `APP_ACCESS_TOKEN`.

## Safe local deployment (Linux computer or VPS with Docker Compose)

1. `cd n8n && cp .env.example .env`
2. Generate **two different random secrets** with `python3 -c "import secrets; print(secrets.token_hex(32))"`; replace the two placeholders in `.env`.
3. `docker compose --env-file .env -f compose.yaml config` to verify the configuration.
4. `docker compose --env-file .env -f compose.yaml up -d`.
5. Open `http://localhost:5678` on the host and create the owner account. If the instance is on a remote VPS, use an SSH port forward: `ssh -L 5678:127.0.0.1:5678 user@server` (then open the same localhost URL).
6. In n8n, use **Import from File** and select `workflows/kuri-cloudflare-storyboard.json`.
7. Create an n8n **Header Auth** credential named `Video Factory Worker` with Header Name `Authorization` and Header Value `Bearer <your existing APP_ACCESS_TOKEN>`. Assign it to **both** HTTP Request nodes. Store the token only in n8n credentials, never in the workflow JSON, `.env.example`, commits or chat.
8. Edit the **Episode Settings** Code node to set your real HTTPS Worker origin, topic and angle. Use `https://your-worker.workers.dev` with **no slash or path** at the end.
9. Select **Execute workflow**. Review the JSON output of **Prepare KURI Review Pack**. The workflow is intentionally **inactive** after importing.

### Security boundaries

The provided Compose setup binds port **5678 only to 127.0.0.1**, uses PostgreSQL, preserves encryption settings and data in Docker volumes, and disables environment-variable reads from n8n code. `N8N_SECURE_COOKIE=false` is safe **only for this localhost / SSH-forwarded HTTP setup**. **Do not open port 5678 publicly**. Before internet-facing deployment, add HTTPS/TLS via a trusted reverse proxy, configure the public origin and secure cookies, restrict access, patch images and implement volume/database backups. Do not use n8n's dev tunnel for production.

Avoid importing unknown third-party workflows with risky nodes. The n8n Community Edition's native Git source-control feature is not included: this project versions **exported JSON workflows in GitHub** instead.

### Operational checks and backup

- Status: `docker compose --env-file .env -f compose.yaml ps`
- Logs: `docker compose --env-file .env -f compose.yaml logs -f n8n`
- Stop: `docker compose --env-file .env -f compose.yaml down` (**do not add `-v`**).
- Backup both the PostgreSQL database and `n8n_data` volume securely. Preserve `N8N_ENCRYPTION_KEY`; without it saved credentials cannot be decrypted.
- Run `n8n audit` periodically after deployment, and rotate access tokens when necessary.

### Deliberate limits / next milestones

- Storyboard scenes are **prompts**, not generated 3D clips. A paid or quota-limited video-generation API is needed for full automation.
- Tagalog full narration is provided but not synthesized; ElevenLabs integration, subtitle alignment, music selection, FFmpeg assembly, storage and MP4 quality checks remain separate milestones.
- The seven scene durations are storyboard estimates, not verified narration timing.
- Human factual, licensing and monetization-policy review remains mandatory.
- No public webhook, scheduled executions or automatic upload is enabled, preventing surprise charges.

## References

- [n8n Docker Compose setup](https://docs.n8n.io/deploy/host-n8n/install-options/use-a-cloud-provider/use-docker-compose/)
- [n8n security audit](https://docs.n8n.io/hosting/securing/security-audit/)
- [Existing Cloudflare Creator Kit integration](../docs/CREATOR_KIT.md)

# Operations

## Current deployment

- Public endpoint: <https://47.84.34.86/>.
- Host: single Alibaba Cloud Singapore Ubuntu instance.
- Caddy owns ports 80/443; Web/API bind only to `127.0.0.1:3000/8000`.
- Current public mode is `replay_only`; no DeepSeek credential is configured.
- The existing release remains the rollback anchor until the canonical digest deployment and a later production deployment both succeed.

## Target delivery chain

```text
GitHub main → CI → GHCR linux/amd64 images → release manifest
           → manual production deploy → health → atomic current switch
                                      ↘ failure: restore previous
```

Images:

- `ghcr.io/suuny-ab/traceable-support-agent-web`
- `ghcr.io/suuny-ab/traceable-support-agent-api-replay`

Production Compose pins immutable digests, never moving tags. The server stores each release under `/opt/traceable-support/releases/<git_sha>/` with its manifest and keeps `current`/`previous` symlinks.

## Deployment contract

1. CI and public-safety scan are green.
2. Build and publish both images for the same Git SHA.
3. Generate `release-manifest.json` with image digests, API contract hash, knowledge/prompt/replay hashes and `provider_enabled=false`.
4. Pull images and start the candidate without changing the current symlink.
5. Check four routes, health, CORS, loopback port isolation and Provider-disabled behavior.
6. Atomically switch `current`; repeat public smoke.
7. On any failure, restore `previous` and report the failed gate.

Deployment uses a restricted server user and a GitHub production environment. Server host/user/private key are Actions secrets; the server anonymously pulls public GHCR images.

## Data retention

Raw request content is retained for at most 30 days. Cleanup removes SQLite rows and checkpoints/truncates WAL; raw content is not backed up. Long-term observability retains only aggregate counts and stable error classes.


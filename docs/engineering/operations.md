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

The first canonical release is a recoverable in-place switch, not a zero-downtime claim: the single host keeps Caddy on ports 80/443, while the loopback Web/API pair restarts briefly. Before that switch, the migration captures the currently running legacy image IDs into private server-local tags so the old release remains executable even if its original build context disappears. The canonical API uses its own named data volume; deployment never runs `down -v`, image pruning or legacy-volume cleanup.

## Deployment contract

1. CI and public-safety scan are green.
2. Build and publish both images for the same Git SHA.
3. Generate `release-manifest.json` with image digests, API contract hash, knowledge/prompt/replay hashes and `provider_enabled=false`.
4. Pull both immutable images, verify their digests and create the non-root canonical data volume with a one-shot ownership initializer.
5. Start the candidate on temporary loopback ports and check four routes, health, exact CORS and Provider-disabled behavior.
6. Atomically update `current`, restart the loopback production pair and repeat public smoke through Caddy.
7. On any failure, restore the prior symlinks and root environment file, then reactivate `previous` and report the failed gate.

The public origin and first-migration rehearsal flag are review-bound in `deploy/production-target.json`, not accepted as free-form dispatch inputs. The first production migration runs a controlled `old → new → old → new` rehearsal. If no verified legacy rollback anchor exists, it fails before canonical activation instead of pretending rollback was tested. The three release metadata paths use a compensating transaction; an ordinary write failure restores their prior state before the old containers are reactivated. Caddy receipt evidence is read before activation, and final receipt persistence is a gate whose failure rolls back to the verified legacy release. The legacy release is retained through the next successful production deployment.

Deployment uses a restricted server user and a GitHub production environment. Server host/user/private key are Actions secrets; the server anonymously pulls public GHCR images.

## Data retention

Raw request content is retained for at most 30 days. Cleanup removes SQLite rows and checkpoints/truncates WAL; raw content is not backed up. Long-term observability retains only aggregate counts and stable error classes.

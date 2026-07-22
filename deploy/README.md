# Deployment

The canonical release is two public `linux/amd64` images pinned by digest:

- `ghcr.io/suuny-ab/traceable-support-agent-web`
- `ghcr.io/suuny-ab/traceable-support-agent-api-replay`

Production is intentionally `replay_only`. The live API target is built and
tested with an offline transport but is not published or deployed in this
increment.

## Local replay

```bash
docker compose -f deploy/compose.local.yaml up --build
```

Web and API bind only to `127.0.0.1:3000/8000`. The API uses the separate
`traceable-support-local-data` volume and contains neither an embedding model
nor a Provider credential. A one-shot, network-disabled initializer grants the
non-root API user ownership of that local volume; the API process itself never
runs as root.

If those ports are already occupied, set `TRACEABLE_LOCAL_WEB_PORT` and
`TRACEABLE_LOCAL_API_PORT` before `docker compose up`; container-side ports and
the production contract remain unchanged.

## Main-branch publication

The CI workflow runs four required jobs: `governance`, `web`, `api` and
`containers`. Pull requests only test. A green push to `main` publishes the Web
and replay API images, generates `release-manifest.json`, and stores that
manifest as the run artifact. It never publishes `latest` or the live image.

Production dispatch accepts only that successful publication run ID. The
reviewed target and mandatory first-migration rehearsal are tracked in
`deploy/production-target.json`; they are not free-form dispatch inputs. A
future domain change therefore requires a normal reviewed repository change
before it can alter CORS or the public smoke target.

The first GHCR packages must be changed to Public in the GitHub package UI and
then anonymously pulled from a logged-out client before any server switch. Do
not add a registry PAT to the server.

## First canonical migration

The current server is a source-built legacy release. It is not yet a digest
release, so the first migration has a separate bootstrap gate:

1. Verify the existing public health is `replay_only`, the Provider switch is
   false, the credential is absent, disk space is sufficient, and Caddy/IP TLS
   is healthy.
2. Run `capture_legacy_release.py` on the server beside the reviewed
   `production-target.json`. It records only image IDs, safe hashes and the
   existing volume name, adds dedicated rollback aliases, and creates a
   source-independent legacy Compose release. It never exports SQLite or
   environment values.
3. Verify the legacy rollback release can reproduce the running containers
   before moving or deleting any source tree.
4. Dispatch `deploy-production.yml`. It installs the canonical release,
   preflights both images on random loopback ports, performs the recoverable
   `legacy → canonical → legacy → canonical` rehearsal, and finishes on the
   legacy release after any failed gate.

The legacy anchor is required before the first canonical activation. Release
metadata (`previous`, `server.env`, `current`) is committed with compensation:
an ordinary failure at any of the three replacements restores the prior bytes
and pointers, then the shell orchestrator restores the prior containers.
Host Caddy evidence is read before activation. The final deployment receipt is
also a release gate: if it cannot be committed, the orchestrator rolls back to
legacy and repeats the public smoke instead of leaving an unrecorded release.

The 2 GiB host uses a recoverable in-place switch and has a short restart
window. This is not zero-downtime or high availability. The `current` symlink
records the last healthy release; it is not a traffic router.

## Host boundary

Caddy remains a host service and continues to own ports 80/443. The first
migration does not replace its certificate, IP `default_sni` fix, or certificate
guard. Every release provides `current/deploy/compose.yaml`, while
`/opt/traceable-support/server.env` is atomically synchronized for guard
compatibility. Application ports remain loopback-only.

Canonical releases use the separate `traceable-support-data-canonical` volume.
Before a switch, a one-shot network-disabled container repairs only that
canonical volume's ownership for UID/GID 10001; the legacy volume is never
mounted by this step.
The legacy volume, images and release remain untouched until the next successful
production deployment after this migration. Never use `docker compose down -v`
or a prune command in this workflow.

## Secrets and inputs

The deployment workflow uses only a GitHub production environment:

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`
- `DEPLOY_KNOWN_HOSTS`
- optional `DEPLOY_PORT`

The SSH key exists only in the Actions runner temporary directory. Known-host
verification is mandatory. The release manifest, image references and tracked
production target contain no secret. Provider keys are outside this pipeline
and forbidden for this increment.

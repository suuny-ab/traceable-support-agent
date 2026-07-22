# Quality strategy

## Tiers

| Tier | Purpose | Target | Default entry |
| --- | --- | ---: | --- |
| Fast | governance, public boundary and stable API smoke | `<=10s` | public scanner, tool tests and no-model API subset |
| Candidate | full API/product tests with the pinned local model | `<=60s` | `python -m pytest api/tests` with explicit model root |
| Product | Web build, replay/live-offline images and Compose smoke | `<=90s` | Web tests plus replay compose and offline live-target checks |
| Audit | public release, history boundary or formal candidate | on demand | secret/path/large-file scan, fresh clone and deployment checks |

HOLDOUT, paid calibration and legacy audit never enter Fast/Product by default.

## Local entries

PowerShell Fast checks from the repository root:

```powershell
python tools/check_public_repo.py --scope worktree
python -m unittest discover -s tools/tests -p "test_*.py"
$env:PYTHONPATH = "api/src"
python -m pytest api/tests/test_package_boundaries.py api/tests/test_public_api.py api/tests/test_provider_usage.py
```

Candidate API checks require the byte-verified BGE model. The downloader is used in a clean environment; an existing verified model root can be supplied locally without copying it into the repository:

```powershell
python deploy/download_embedding_model.py --manifest api/src/traceable_support/retrieval/bge-small-zh-v1.5-fastembed.json --root .local-model
$env:PYTHONPATH = "api/src"
$env:TRACEABLE_MODEL_ROOT = "$PWD/.local-model/artifacts/models/fastembed/fast-bge-small-zh-v1.5"
python -m pytest api/tests
```

`.local-model/` is ignored and must never be committed. CI installs the fully pinned test/live dependency locks, downloads the same model from its allowlisted source, verifies every file size/hash, and then runs this Candidate entry. The live image is tested with networking disabled and performs no Provider call.

Web checks:

```powershell
Set-Location web
npm ci
npm audit --audit-level=high --registry=https://registry.npmjs.org
npm run lint
npm run typecheck
npm test
```

## Required checks

### Governance and public safety

- exactly one active work item and valid status link;
- no nested Git repositories outside the root;
- no Windows home paths, secrets, credentials, raw Provider content, archives, databases or private HOLDOUT;
- no tracked file larger than 5 MiB; initial exception list is empty;
- public claims agree with `provider_enabled=false`, `replay_only` and `product/0.1.0 not released`;
- production package cannot import `evals`, `tools` or completed work.

### API

- four public endpoints and stable error codes;
- sensitive, out-of-scope and safety preflight before Provider assembly;
- random run IDs, exact CORS, 16 KiB body limit, queue/concurrency limits and atomic budget reservation;
- SQLite decision persistence, 30-day cleanup, WAL cleanup and restart recovery;
- replay mode starts without model, live dependency or credential;
- live target uses offline transport only in CI.

### Web

- lint, TypeScript, unit/protocol tests and standard Next production build;
- `/`, `/design`, `/app`, `/privacy` render;
- loading/input lock, replay fallback, source/obligation display and keyboard/mobile behavior remain valid.

### Containers and deployment

- images run as non-root users and expose only loopback-bound application ports through Compose;
- health checks report `replay_only` in this increment;
- release manifest binds Git SHA, image digests and contract/content hashes;
- failed health switch returns to the previous release.

## Evidence semantics

Passing unit tests prove only their declared contracts. Replay proves a verified historical product result, not a new Provider run. Offline live-target tests prove assembly and failure boundaries, not language quality. User acceptance is recorded only after the user actually tries the result.

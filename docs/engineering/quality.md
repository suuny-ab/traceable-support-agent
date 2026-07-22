# Quality strategy

## Tiers

| Tier | Purpose | Target | Default entry |
| --- | --- | ---: | --- |
| Fast | governance, import boundary, stable API/runtime smoke | `<=10s` | `python tools/check_governance.py && python -m unittest discover -s api/tests -p "test_*.py"` |
| Candidate | active product and selected regression cases | `<=60s` | `python -m unittest discover -s evals/tests -p "test_*.py"` |
| Product | Web build, API/SQLite integration and containers | `<=90s` | Web tests plus replay compose smoke |
| Audit | public release, history boundary or formal candidate | on demand | secret/path/large-file scan, fresh clone and deployment checks |

HOLDOUT, paid calibration and legacy audit never enter Fast/Product by default.

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


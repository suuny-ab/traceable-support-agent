# Result

> Status: `in_progress`

## Interim verified receipts

- Clean governance baseline: `57792e9`.
- API/product extraction: 70 API, persistence, Provider-contract and offline-product tests passed locally.
- The eight approved cases produce byte-identical old/new ordered Top-10 and Top-5 retrieval fixtures.
- Knowledge unit inventory, three prompt byte hashes and Provider manifest match the frozen baseline.
- Public control plane imports without third-party packages; a key alone cannot enable live mode.
- Direction-B Web passes lint, typecheck, standard Next.js production build and 12 tests; all four routes return 200 from standalone output.
- No Sites/vinext/Wrangler/Worker source, nested Git metadata or frontend build output is tracked.
- Web and API base images, all GitHub Actions and the full Python live dependency closure are immutable-hash pinned; official npm audit reports zero known vulnerabilities.
- Replay Web/API images run non-root without a model or credential; the local Compose check passed four routes, exact CORS, replay failure-close, SQLite volume ownership and API restart recovery.
- The live image contains the byte-verified fixed BGE model and, with network disabled, reproduces all eight approved retrieval cases with `provider_calls=0`; `pip check` reports no broken requirements.
- The release manifest binds the Git SHA, two image digests, API contract, knowledge/retrieval/replay/prompt/Compose/dependency hashes and explicitly records `provider_enabled=false`.
- The production path retains host Caddy/IP HTTPS, captures the legacy image IDs before first migration, uses a separate canonical volume and supports the controlled `old → new → old → new` rehearsal. No production switch has been attempted yet.
- The deployment candidate passed Cycle 3 independent review after closing pre-activation anchor, fixed-origin, metadata half-commit and final-receipt failure paths.
- The real governance-validation increment adds a third replay preset: `GEN-DEV-IE-001` stops at retrieval when no approved source supports a Wi-Fi compatibility claim and shows a typed handoff. Its fixed mechanical expectation declares `provider_call_count=0`; this increment itself also made zero Provider calls. The Web now passes 15 tests; the current public server remains unchanged.
- A production Web image ran as the non-root `node` user with a read-only root filesystem. Real-browser desktop and mobile-breakpoint checks confirmed the replay-only route, `STOP/WAIT/WAIT/WAIT` trace, absent evidence and approval controls, no horizontal overflow and no console warnings or errors.
- Calls made while implementing and verifying this increment: `0`; Provider cost: `0 CNY`.

Remote publication, canonical-path switch, production deployment and user acceptance remain pending. The legacy repository and current public deployment are unchanged.

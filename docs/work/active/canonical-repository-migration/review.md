# Independent review

> Status: `cycle_3_passed`

Threat model: public anonymous callers, accidental publication of private material, product/evaluation dependency inversion, budget/privacy/failure-closed behavior and incorrect public claims. Review uses a fixed clean candidate and does not alter code.

## Cycle 1

The staged deployment-pipeline snapshot failed review on three approved-entry paths:

1. a missing legacy rollback anchor was detected only after canonical activation, and rehearsal could be disabled;
2. activation and rollback committed `previous`, `server.env` and `current` without compensation for a partial I/O failure;
3. a free-form dispatch origin controlled both production CORS and public smoke.

The corrected candidate requires the anchor before activation, always performs the first `old → new → old → new` rehearsal, commits release metadata with tested compensation, and binds the current IP origin in a reviewed repository file. A new fixed-snapshot review is required before commit 4.

## Cycle 2

The three Cycle 1 findings were closed. Review then found that Caddy hashing and deployment-receipt persistence still occurred only after the final canonical activation. A restricted-user read failure or receipt I/O failure could therefore return a failed workflow while leaving canonical public without a receipt.

The next correction reads and validates the Caddy hash before any activation. Receipt persistence is now a final gate whose failure explicitly rolls back to legacy and repeats public smoke. Cycle 3 must verify this path before commit 4.

## Cycle 3

PASS. The fixed target, pre-activation anchor, pre-activation Caddy evidence, compensated release metadata and receipt-failure rollback are all reachable from the approved workflow and fail closed. Linux ran all 12 governance and failure-injection tests; the staged public scanner, Python AST, workflow YAML, Bash syntax, Compose config and whitespace checks passed. No Provider, GitHub or server write occurred during review.

## Replay increment

PASS. The approved entry was the `/app` preset selector and run button. The review covered misleading replay/live provenance, accidental live POST, unsupported evidence display, unsafe handoff controls, the two-mode UI and claim boundaries. Index and worktree were identical; the replay fields matched the public regression; `available + exact replayOnly` routed to replay while edited input retained the live route; evidence and approval controls were conditionally absent; and the release hash matched the new replay JSON. Web 15/15, lint, typecheck, public scanner and relevant governance tool tests passed. The conclusion remains limited to the replay UI and its public mechanical expectation; the live product does not yet enforce the same `GEN-DEV-IE-001` stop.

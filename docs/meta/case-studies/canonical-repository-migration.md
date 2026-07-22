# Case: canonical repository migration

> Status: `in_progress`

## Friction

The product, portfolio and governance were split between two Git repositories. The main repository contained 385 commits and large raw audit/history areas; current status and stable facts were difficult to recover despite an effective development workflow.

## Hypothesis and minimum change

Keep one clean public monorepo and the proven governance semantics, but migrate only active product code, synthetic knowledge, selected regressions, current decisions and normalized meta cases. Exclude raw audit/history material.

## Validation increment

After cold-start and equivalence checks, add `GEN-DEV-IE-001` as an “insufficient evidence → human handoff” replay preset through the new work protocol.

## Migration provenance

- Legacy main baseline: `ab2c4b8a374937a8727e414991799dba490db30b`.
- Legacy Web baseline: `b1bcc94c5cf122a6c6dcff5d007eb6194d47dcc7`.
- Legacy repositories and raw history are intentionally not public and will be deleted after canonical, remote, deployment and user acceptance.
- This record contains no local path and does not point to a permanent archive.

## Observed effect

Pending candidate, fresh-clone, deployment and user acceptance.


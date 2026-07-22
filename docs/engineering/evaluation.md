# Evaluation boundary

## Public regression set

The canonical repository carries only eight sanitized regression cases:

- `GEN-DEV-QA-003`
- `GEN-DEV-QA-006`
- `GEN-DEV-TK-001`
- `GEN-DEV-TK-006`
- `GEN-DEV-IE-001`
- `GEN-DEV-MH-001`
- `GEN-DEV-MH-003`
- `BRD-QA-005`

They cover multi-source QA, stop-condition QA, an approvable ticket, product-model boundary, insufficient evidence, safety handoff, false completion and source-visible-obligation binding. Only synthetic inputs, required fixtures and mechanical expectations are public.

## Public vs private

Public Git may contain development/regression cases, contracts, runner code, commitments and aggregate reports. It never contains new unseen Stage 12 plaintext, Provider raw output, authorization envelopes, credentials or account observations.

Private formal input lives outside the repository. Revealed or consumed HOLDOUT is regression-only and cannot be tuned on or used to claim a new formal result.

## Stage 12

Stage 12 is not part of the governance migration. It will bind the same candidate version used by the website, a new unseen set, maximum calls, exact worst-case cost, scoring, repeats, hard stops and publication authority before any Provider execution.

`product/0.1.0` remains blocked until all safety/privacy/cost/failure-closed gates and the declared business-quality gate pass.


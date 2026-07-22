# Development flow

> Protocol: `value-first-development/2.0`  
> Effective: `2026-07-23`

## Value contract

Before implementation, record:

1. What the user will newly see, or which critical unknown will be removed.
2. The cheapest check likely to falsify the approach.
3. Existing repository, dependency, open-source or vendor capabilities to reuse.
4. Maximum investment and stop condition.
5. Exactly what a passing result is allowed to claim.

If the work cannot answer the first or fifth item, it does not enter implementation. Governance, test and documentation volume are not substitutes for product progress.

## Reuse review

Review in this order:

1. Existing verified repository behavior or fixture.
2. An already adopted dependency.
3. A maintained, license-compatible open-source library.
4. An official vendor SDK/API.
5. A thin project-specific adapter.
6. New general infrastructure only when the previous options fail a concrete semantic, license, security, compatibility, cost or maintenance requirement.

## Work size

- Light: one local reversible boundary, no public contract, persistence, security or external risk.
- Standard: user-visible behavior across multiple files or one bounded interface.
- Full: architecture, API contract, persistence, security, privacy, public release, destructive migration or Provider mechanism.

Only one increment is active. Standard/full work uses a normalized work folder; intermediate fixes remain inside the increment instead of producing repeated governance cycles.

## External risk and maturity

Risk:

- `R0`: no network, fee or external write.
- `R1`: synthetic/public data, fixed Provider, bounded calls/cost, no business write.
- `R2`: sensitive data, account/public state, external write, irreversible operation or unbounded cost.

Maturity:

- `S0 exploration`: cheapest public/synthetic experiment; no private HOLDOUT or formal custody system.
- `S1 development`: representative public and pressure slices; no unexplained structural failure.
- `S2 candidate`: clean fixed commit, integration tests and independent review.
- `S3 formal`: fixed candidate, new formal input, authorization, budget and strict conclusion contract.

Stage labels do not authorize network or fees. Candidate-quality failure completes valid evidence collection; authorization, transport, budget, identity or package-integrity failure stops execution.

## Validation card

Any validation that can change model quality, product readiness, candidate maturity or release claims must predeclare the question, non-goals, sample, code/prompt/model identity, repeats, scoring, hard/quality gates, leakage controls, maximum calls/cost, stop conditions and allowed conclusion.

Standing authorization applies only when every condition in `AGENTS.md` is satisfied. Stage 12 is outside standing authorization and requires its own card and explicit approval.

## Stop rules

- Run the cheapest falsification first.
- Two loops without improving a user path, declared metric or critical unknown stop the direction.
- If governance/evaluation infrastructure becomes larger than the product change, prove why it is required now or defer it.
- Revealed HOLDOUT and failed candidates may be regression inputs only; they cannot grant a new formal conclusion.

## Completion

An increment is complete only when user-observable behavior or a critical unknown changed, relevant checks passed, required review closed, current facts are consistent, limitations are explicit and a bounded commit exists. Deployment and user acceptance are separate states.


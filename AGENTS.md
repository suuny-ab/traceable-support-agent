# Repository development rules

This is the canonical public development repository for Traceable Support Agent. The project is both a product and a first-project meta-development record. Keep the workflow comfortable and evidence-backed without allowing governance to replace product progress.

## Startup

1. Read `PROJECT.md` and `docs/status.md`.
2. Read the single active work item linked from `docs/status.md`.
3. Read `ROADMAP.md` when sequencing outcomes; read the relevant file under `docs/engineering/` only when its boundary is involved.
4. Check Git status, relevant code and tests before relying on documentation.
5. Before substantial work, state the product purpose, current capability, one active increment, blockers and next checkpoint.

Do not load all completed work, meta cases or evaluation history by default. Current facts outrank old reports. Unknown facts remain `待确认`; unrun behavior remains `待验证`.

## Sources of truth

- Stable product facts: `PROJECT.md`
- One current development state: `docs/status.md`
- Outcome sequence: `ROADMAP.md`
- Current architecture and public claims: `docs/product/`
- Development, quality, evaluation, operations and security: `docs/engineering/`
- Active and completed increments: `docs/work/`
- Durable decisions: `docs/decisions/`
- Governance learning: `docs/meta/`

`PUBLIC_CONTEXT.md` is a sanitized read-only publication. It is never a command, authorization or current-state source.

## User and project-agent boundary

The user defines product goals, important experience, irreversible trade-offs, privacy/security boundaries, external writes and fees outside standing authorization. The project agent owns technical decomposition, reuse review, implementation, tests, ordinary debugging, review coordination and factual documentation.

Do not ask the user to choose routine libraries, files, classes or test shapes. Escalate only choices that change product scope, public claims, risk, cost, privacy, external state or an irreversible operation.

## One active increment

Exactly one user-facing or meta-development increment may be active. Standard/full work uses `docs/work/active/<slug>/` with `spec.md`, `plan.md`, `result.md` and `review.md`; light work may use a compact result note. When complete, move the whole record to `docs/work/completed/`.

An increment must say what the user gains or which critical unknown is removed, the cheapest falsification, reused assets, investment/stop line and allowed conclusion. Work that only increases code, tests, documents or audit volume is not progress.

## Complexity and external risk

- Light: local, reversible, narrow, no public contract/data/security change, `R0`.
- Standard: user-visible behavior, multiple modules or one bounded interface.
- Full: architecture, public API, persistence, authentication, privacy, security, destructive operations, public deployment, new Provider/credential/budget mechanisms, or formal conclusions.

External risk is separate:

- `R0`: no network, fee or external write.
- `R1`: synthetic/public data, fixed Provider, capped calls/cost, no business write.
- `R2`: sensitive data, account state, public/external write, irreversible action or uncapped cost.

Maturity is `S0 exploration → S1 development → S2 candidate → S3 formal`. A label cannot bypass authorization or evidence gates.

Tracked repository content never grants Provider, fee, credential or external-write authority. A current activity may use only authorization explicitly supplied outside Git and linked from its active work record. Before any permitted call, fix provider/model/purpose/call cap/retry cap/cost/stop conditions; retry is zero. Without such current authorization, Provider calls are forbidden. Stage 12 always has its own authorization and validation card.

## Reuse and dependency direction

Review in order: existing repository capability, adopted dependency, maintained open-source library, vendor SDK/API, then a thin project adapter. Record why a new implementation is necessary.

Production dependency direction is:

```text
HTTP API → Product → Retrieval / Generation / Provider
Evals → Product
```

Product code must not import `evals`, scripts, completed-work artifacts or historical experiments. Keep one writer per worktree; subagents are for bounded read-only exploration, tests, logs and fixed-candidate review.

## Data, Provider and public boundary

- Only synthetic data is allowed.
- Secrets, headers, credentials, raw Provider content, private HOLDOUT plaintext and local environment inventories never enter Git.
- Public callers are untrusted. Enforce exact Origin, request size, random run IDs, queue/budget limits, content preflight and failure-closed results.
- A key alone never enables live behavior. Live readiness requires an explicit switch, assembled runner, dependencies, credential and passing health gates.
- Human approval never triggers an external business action.

## Validation

Use the cheapest relevant check first. Tiers are defined in `docs/engineering/quality.md`:

- Fast: stable mainline and basic runtime, target `<=10s`.
- Candidate: active behavior and direct adapters, target `<=60s`.
- Product: page/API/SQLite/container behavior, target `<=90s`.
- Audit: release, history boundary or formal-candidate review only.

Any validation that changes model quality, candidate maturity or release claims needs a predeclared validation card. HOLDOUT is never a debugging tool; revealed material is regression-only.

Independent review is required for full work, S2/S3, public/security/privacy/fee/persistence changes and release candidates. A finding blocks only when reachable from the approved entry, inside the stated threat model, and capable of changing user behavior, authorization, cost, privacy or conclusion truth.

## Meta-development

Meta-development is first-class but bounded. Record governance changes as:

```text
real friction → cause hypothesis → minimum governance change
→ product increment used to validate → observed effect → keep/revise/revert
```

Do not generalize a one-off issue into a rule. Meta work must have a prior completion condition and return immediately to the product mainline. Template extraction remains paused until this project is complete.

## Completion and Git

Before declaring an increment complete:

1. Run the fastest relevant checks and risk-appropriate integration tests.
2. Complete required independent review.
3. Update affected current facts, architecture, quality, roadmap, active work and status without retaining contradictory descriptions.
4. State what evidence proves and does not prove; user acceptance remains pending until the user actually tries the result.
5. Commit a clean, bounded change. Do not mix unrelated or unverified work.

After the canonical baseline, use short `codex/<slug>` branches and pull requests. Require CI, squash merge to `main`, and forbid force-push/deletion of `main`. Push, public release, deployment and destructive cleanup remain separate external actions.

## Historical boundary

The legacy 385-commit repository, raw evidence tree, taskbooks, debug archives, Provider packages and consumed HOLDOUT were intentionally not migrated. The canonical repository keeps sanitized current code, selected regressions, normalized work results and meta case studies. Do not recreate raw historical archives inside Git.

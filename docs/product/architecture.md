# Product architecture

## Context

The product turns synthetic support questions or tickets into evidence-bound, human-reviewable results. Offline evaluation measures retrieval/generation quality; runtime mechanical gates cover observable evidence, safety, authorization, schema and technical failures without pretending to prove complete recall for arbitrary questions.

```text
Next.js Web
    ↓ same-origin /api/v1
Python HTTP boundary
    ↓
Run service / SQLite / budget / queue
    ↓
ProductRunner
    ├─ Retrieval: model filter + BM25/BGE/RRF
    ├─ Generation: checklist → customer-visible candidate
    ├─ Provider: DeepSeek transport + usage/budget
    └─ Validation: source, obligation, schema and handoff gates
```

## Modules

- `traceable_support.api`: HTTP, CORS, request limits, run lifecycle, persistence and public projection.
- `traceable_support.product`: QA/ticket orchestration and classification.
- `traceable_support.retrieval`: synthetic corpus, hybrid retrieval and model manifest.
- `traceable_support.generation`: checklist, QA/ticket contracts and mechanical gates.
- `traceable_support.provider`: transport contract, DeepSeek adapter, usage and atomic budget.
- `evals`: public regression and future evaluation adapters; depends on product, never the reverse.

## Public states

Runs move through `queued → retrieving → planning → generating → validating → completed|handoff`. Provider-disabled valid input returns `503 live_experience_unavailable` while the Web offers a separately labelled replay. Preflight handoff may complete deterministically without Provider.

## Deployment

Web and replay API are separate non-root images. Caddy terminates HTTPS and proxies same-origin requests. SQLite is the single-node persistence layer; the project does not claim multi-node consistency or production HA.


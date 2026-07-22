# Design decisions

## Why a controlled Workflow

The product problem is not simply generating fluent text. Customer-support drafts can omit a stop condition, mix product models, invent a completed action or lose the link between an executable claim and its source. The design therefore keeps LLM generation inside a deterministic control plane.

## Core flow

1. Filter by known product model and retrieve a bounded evidence set.
2. Ask the model to enumerate obligations and explicitly account for context.
3. Generate a customer-visible answer or ticket draft against that checklist.
4. Mechanically validate schemas, source bindings, obligation coverage and forbidden completion claims.
5. Return a reviewable candidate or a typed handoff; a human decides.

## Important trade-offs

- Retrieval quality is proved offline; runtime does not claim to know the recall denominator.
- A handoff is preferable to an unsupported executable statement.
- Structured metadata cannot substitute for facts missing from customer-visible text.
- The model has no tools, database access, retry authority or business-action permission.
- Budget and privacy checks happen before transport construction.

## Replay semantics

Replay data is a labelled, verified product result used to keep the portfolio usable when live experience is disabled or unavailable. It is not presented as a new model call and cannot generate a release-quality claim.


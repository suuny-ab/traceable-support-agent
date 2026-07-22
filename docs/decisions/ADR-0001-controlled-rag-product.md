# ADR-0001: controlled RAG product architecture

> Status: accepted  
> Date: `2026-07-20`

## Context

Open support questions cannot prove complete runtime recall because the denominator is known only in labelled evaluation. Requiring runtime “complete evidence” would either fail valid work or leak evaluation authority into the product; removing runtime gates would allow unsupported or unsafe drafts.

## Decision

Use offline retrieval/generation evaluation plus minimal runtime hard gates and human review:

- versioned synthetic knowledge and replaceable retrieval;
- bounded source context and source-bound LLM drafts;
- runtime handoff for no evidence, explicit safety/permission/model conflict, schema/source failure or technical error;
- no claim of complete arbitrary-query recall or zero hallucination;
- human final decision and no automatic external action.

## Consequences

Retrieval, generation and reviewer efficiency are measured separately. Runtime results remain auditable but human review is required. Changing to real customer data, automatic actions or open-domain knowledge requires a new decision.


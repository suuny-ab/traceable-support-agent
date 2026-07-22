# ADR-0002: bounded Top-10 generation context

> Status: accepted as a development boundary  
> Date: `2026-07-21`

## Context

Several selection heuristics dropped required facts even when the model-filtered hybrid Top-10 candidate pool contained them. Runtime compression was becoming a second unproven recall system.

## Decision

Allow the model-filtered hybrid Top-10 source context to enter evidence-constrained generation during development, with source selection and customer-visible fact binding validated afterward. Evaluation labels and required facts never enter the request.

## Consequences

This removes an unproven selector from the development path but increases context and generation risk. The direction earns only evaluation eligibility; it is not a product-quality claim and cannot use revealed cases for iterative tuning.


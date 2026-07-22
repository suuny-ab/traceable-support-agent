# ADR-0003: clean-baseline canonical public monorepo

> Status: accepted  
> Date: `2026-07-23`

## Context

Product/API code and the direction-B Web lived in separate local repositories. The main repository's 385-commit history contained raw audit artifacts, debug archives and environment-specific material unsuitable for confident publication. Maintaining separate public and private code would create synchronization risk.

## Decision

Create one public monorepo from an allowlist-only clean baseline. Preserve active product behavior, current governance semantics, selected synthetic regressions and normalized meta cases; do not rewrite or publish legacy history. Keep new formal plaintext and Provider raw output outside Git.

## Consequences

The canonical repository is the sole future write source after cold-start, fresh-clone, remote and deployment acceptance. Legacy working trees and temporary bundles are deleted after user acceptance. Historical raw audit detail is intentionally unavailable from the canonical repository.


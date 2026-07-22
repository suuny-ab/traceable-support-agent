"""Resolve source-level product applicability declared in business text."""

from __future__ import annotations

from collections.abc import Iterable


SUPPORTED_MODELS = ("CZ-R1", "CZ-R2")


def resolve_applicable_models(
    text: str, fallback: Iterable[str]
) -> tuple[str, ...]:
    """Prefer an explicit single-model source declaration over document scope."""

    fallback_models = tuple(fallback)
    explicit = tuple(
        model for model in SUPPORTED_MODELS if f"仅适用 {model}" in text
    )
    if len(explicit) == 1:
        return explicit
    return fallback_models

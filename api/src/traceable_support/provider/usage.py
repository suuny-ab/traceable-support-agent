"""Additive usage compatibility for validated Provider responses.

This module accepts exactly the original five-field usage object, the
same object plus the observed ``prompt_tokens_details.cached_tokens`` fact,
plus the observed ``completion_tokens_details.reasoning_tokens`` fact, or both.
Each optional fact is validated, removed, and the resulting response is then
passed through the complete frozen response and cost parser.
``reasoning_tokens`` is a billing breakdown already contained in
``completion_tokens``, so removing it leaves cost accounting exact.
A ``reasoning_content`` message field from thinking-enabled responses is
validated as a string, removed (never persisted), and recorded as a boolean
fact before the frozen parser runs.

No transport, credential, environment, product, or persistence entry exists
in this module.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .contract import (
    MAX_RESPONSE_BYTES,
    Tg07aContractError,
    assert_no_sensitive_material,
    calculate_cost,
    canonical_json_bytes,
    json_exact_equal,
    parse_chat_completion,
    strict_json_loads,
    validate_usage,
)


USAGE_NORMALIZATION_SCHEMA_VERSION = "tg07u-usage-normalization-v1"
USAGE_COMPATIBILITY_FACTS_SCHEMA_VERSION = "tg07u-usage-compatibility-facts-v1"

BASE_USAGE_FIELD_ORDER = (
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "prompt_cache_hit_tokens",
    "prompt_cache_miss_tokens",
)
BASE_USAGE_FIELDS = frozenset(BASE_USAGE_FIELD_ORDER)
OPTIONAL_USAGE_FIELD = "prompt_tokens_details"
COMPLETION_OPTIONAL_USAGE_FIELD = "completion_tokens_details"
OPTIONAL_USAGE_FIELDS = BASE_USAGE_FIELDS | {OPTIONAL_USAGE_FIELD, COMPLETION_OPTIONAL_USAGE_FIELD}


def _compatibility_facts(*, optional_present: bool, completion_optional_present: bool) -> dict[str, Any]:
    return {
        "schema_version": USAGE_COMPATIBILITY_FACTS_SCHEMA_VERSION,
        "prompt_tokens_details_present": optional_present,
        "prompt_tokens_details_exact_cached_tokens_object": optional_present,
        "cached_tokens_matches_prompt_cache_hit_tokens": True if optional_present else None,
        "completion_tokens_details_present": completion_optional_present,
        "completion_tokens_details_exact_reasoning_tokens_object": completion_optional_present,
        "reasoning_tokens_within_completion_tokens": True if completion_optional_present else None,
        "validation_passed": True,
    }


def normalize_provider_usage(value: Any) -> dict[str, Any]:
    """Validate the frozen usage union and return only the historical fields.

    Invalid shapes use the historical fixed usage error codes.  In particular,
    ``bool`` is never accepted as an integer and no unobserved provider field is
    silently ignored.
    """

    if value is None:
        raise Tg07aContractError("provider_usage_missing")
    if type(value) is not dict or not BASE_USAGE_FIELDS <= set(value) <= OPTIONAL_USAGE_FIELDS:
        raise Tg07aContractError("provider_usage_invalid")

    optional_present = OPTIONAL_USAGE_FIELD in value
    if optional_present:
        details = value[OPTIONAL_USAGE_FIELD]
        if type(details) is not dict or set(details) != {"cached_tokens"}:
            raise Tg07aContractError("provider_usage_invalid")
        cached_tokens = details["cached_tokens"]
        if type(cached_tokens) is not int or cached_tokens < 0:
            raise Tg07aContractError("provider_usage_invalid")
        if cached_tokens != value["prompt_cache_hit_tokens"]:
            raise Tg07aContractError("provider_usage_invalid")

    completion_optional_present = COMPLETION_OPTIONAL_USAGE_FIELD in value
    if completion_optional_present:
        details = value[COMPLETION_OPTIONAL_USAGE_FIELD]
        if type(details) is not dict or set(details) != {"reasoning_tokens"}:
            raise Tg07aContractError("provider_usage_invalid")
        reasoning_tokens = details["reasoning_tokens"]
        if type(reasoning_tokens) is not int or reasoning_tokens < 0:
            raise Tg07aContractError("provider_usage_invalid")
        if reasoning_tokens > value["completion_tokens"]:
            raise Tg07aContractError("provider_usage_invalid")

    normalized_usage = validate_usage({key: value[key] for key in BASE_USAGE_FIELD_ORDER})
    return {
        "schema_version": USAGE_NORMALIZATION_SCHEMA_VERSION,
        "normalized_usage": normalized_usage,
        "compatibility_facts": _compatibility_facts(
            optional_present=optional_present,
            completion_optional_present=completion_optional_present,
        ),
    }


def validate_usage_compatibility_facts(value: Any, *, source_usage: Any) -> dict[str, Any]:
    """Strictly rederive safe facts from the externally supplied usage object."""

    expected = normalize_provider_usage(source_usage)["compatibility_facts"]
    if not json_exact_equal(value, expected):
        raise Tg07aContractError("tg07u_usage_compatibility_facts_invalid")
    return deepcopy(expected)


def validate_usage_normalization(value: Any, *, source_usage: Any) -> dict[str, Any]:
    """Strictly rederive the complete normalized result and reject self-seals."""

    expected = normalize_provider_usage(source_usage)
    if not json_exact_equal(value, expected):
        raise Tg07aContractError("tg07u_usage_normalization_invalid")
    return deepcopy(expected)


def parse_chat_completion_compatible(
    body: bytes,
    *,
    sensitive_values: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Parse a TG-07A response after the narrow usage-only normalization.

    Five-field responses are handed to the historical parser byte-for-byte.
    Responses with optional usage detail fields are strictly decoded,
    normalized, and re-encoded with only the optional usage fields removed.
    Every other envelope field is kept intact so the historical
    model/choice/content/fingerprint/reasoning checks remain authoritative.
    """

    if type(body) is not bytes:
        raise Tg07aContractError("provider_response_json_invalid")
    if len(body) > MAX_RESPONSE_BYTES:
        raise Tg07aContractError("provider_response_too_large")
    for secret in sensitive_values:
        if type(secret) is str and secret and secret.encode("utf-8") in body:
            raise Tg07aContractError("provider_sensitive_reflection")

    envelope = strict_json_loads(body)
    if type(envelope) is dict:
        assert_no_sensitive_material(envelope, sensitive_values=sensitive_values)

    reasoning_content_removed = False
    if type(envelope) is dict and type(envelope.get("choices")) is list:
        for choice in envelope["choices"]:
            message = choice.get("message") if type(choice) is dict else None
            if type(message) is dict and "reasoning_content" in message:
                reasoning = message["reasoning_content"]
                if reasoning is not None and type(reasoning) is not str:
                    raise Tg07aContractError("provider_reasoning_unexpected")
                if reasoning:
                    reasoning_content_removed = True
                    message["reasoning_content"] = None

    usage = envelope.get("usage") if type(envelope) is dict else None
    has_optional_usage = type(usage) is dict and (
        OPTIONAL_USAGE_FIELD in usage or COMPLETION_OPTIONAL_USAGE_FIELD in usage
    )

    if not has_optional_usage and not reasoning_content_removed:
        parsed = parse_chat_completion(body, sensitive_values=sensitive_values)
        normalization = normalize_provider_usage(parsed["usage"])
    else:
        normalization = normalize_provider_usage(usage)
        normalized_envelope = deepcopy(envelope)
        normalized_envelope["usage"] = deepcopy(normalization["normalized_usage"])
        parsed = parse_chat_completion(
            canonical_json_bytes(normalized_envelope),
            sensitive_values=sensitive_values,
        )

    if not json_exact_equal(parsed["usage"], normalization["normalized_usage"]):
        raise Tg07aContractError("tg07u_usage_normalization_invalid")
    if not json_exact_equal(parsed["cost"], calculate_cost(normalization["normalized_usage"])):
        raise Tg07aContractError("tg07u_usage_normalization_invalid")

    result = deepcopy(parsed)
    result["usage_compatibility"] = deepcopy(normalization["compatibility_facts"])
    result["reasoning_content_removed"] = reasoning_content_removed
    return result

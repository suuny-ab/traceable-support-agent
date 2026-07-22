"""Shared Provider call, observation, usage, and reservation mechanism.

The module preserves the dynamic candidate's versioned budget and failure
semantics while allowing compatibility adapters to reuse the same mechanism.
It does not construct a transport or authorize real execution.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .contract import (
    ENDPOINT_URL,
    Tg07aContractError,
    calculate_cost,
    canonical_json_bytes,
    sha256_bytes,
    strict_json_loads,
    validate_usage,
)
from .response import TransportResponse
from .deepseek import (
    Tg07c0TransportError,
    validate_transport_observation,
)
from .usage import parse_chat_completion_compatible


BUDGET_SCHEMA_VERSION = "dynamic-provider-budget-v1"
CALL_LIMIT = 5
CANDIDATE_LIMIT_CNY_NANOS = 1_000_000_000
TIMEOUT_MS = 30_000


class CallMechanismError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
        self.__cause__ = None
        self.__context__ = None


def _fail(code: str) -> None:
    raise CallMechanismError(code) from None


def _json_equal(left: Any, right: Any) -> bool:
    try:
        return canonical_json_bytes(left) == canonical_json_bytes(right)
    except BaseException:
        return False


def build_request_identity(
    *,
    sequence: int,
    case_id: str,
    object_id: str,
    run_id: str,
    stage: str,
    prepared: dict[str, Any],
    max_output_tokens: int,
    timeout_ms: int = TIMEOUT_MS,
) -> dict[str, Any]:
    if type(timeout_ms) is not int or not 1 <= timeout_ms <= 180_000:
        _fail("dynamic_candidate_timeout_invalid")
    body = prepared["body"]
    value = {
        "sequence": sequence,
        "case_id": case_id,
        "stage": stage,
        "object_id": object_id,
        "run_id": run_id,
        "request_body_utf8": body.decode("utf-8"),
        "request_bytes": len(body),
        "request_sha256": sha256_bytes(body),
        "max_output_tokens": max_output_tokens,
        "timeout_ms": timeout_ms,
        "automatic_retry_count": 0,
        "worst_cost_cny_nanos": len(body) * 3000 + max_output_tokens * 6000,
        "prompt_version": prepared["prompt_version"],
        "prompt_sha256": prepared["prompt_sha256"],
        "stage_input_sha256": prepared["stage_input_sha256"],
        "output_schema_version": prepared["output_schema_version"],
    }
    if value["worst_cost_cny_nanos"] > CANDIDATE_LIMIT_CNY_NANOS:
        _fail("dynamic_candidate_request_budget_invalid")
    return value


class ReservedCallBudget:
    __slots__ = (
        "limit", "call_limit", "call_count", "estimated_cost", "pending",
        "reservations", "unknown",
    )

    def __init__(self, *, limit: int = CANDIDATE_LIMIT_CNY_NANOS) -> None:
        if type(limit) is not int or not 0 <= limit <= CANDIDATE_LIMIT_CNY_NANOS:
            _fail("dynamic_candidate_budget_invalid")
        self.limit = limit
        self.call_limit = CALL_LIMIT
        self.call_count = 0
        self.estimated_cost = 0
        self.pending: dict[str, Any] | None = None
        self.reservations: list[dict[str, Any]] = []
        self.unknown = False

    def reserve(self, request: dict[str, Any]) -> None:
        if self.pending is not None or self.call_count >= self.call_limit:
            _fail("dynamic_candidate_call_limit_exceeded")
        worst = request["worst_cost_cny_nanos"]
        if type(worst) is not int or worst > self.limit - self.estimated_cost:
            _fail("dynamic_candidate_budget_insufficient")
        self.call_count += 1
        self.pending = deepcopy(request)
        self.reservations.append({
            "sequence": self.call_count,
            "request_sha256": request["request_sha256"],
            "worst_cost_cny_nanos": worst,
            "reserved_before_transport": True,
        })

    def record_usage(self, request: dict[str, Any], usage: Any) -> dict[str, Any]:
        if self.pending is None or not _json_equal(self.pending, request):
            _fail("dynamic_candidate_budget_state_invalid")
        try:
            checked = validate_usage(usage)
            cost = calculate_cost(checked)
        except Tg07aContractError:
            self.pending = None
            self.unknown = True
            _fail("dynamic_candidate_usage_invalid")
        nanos = cost["amount_cny_nanos"]
        if nanos > request["worst_cost_cny_nanos"]:
            self.pending = None
            self.unknown = True
            _fail("dynamic_candidate_usage_exceeds_reservation")
        self.estimated_cost += nanos
        self.pending = None
        if self.estimated_cost > self.limit:
            self.unknown = True
            _fail("dynamic_candidate_budget_exceeded")
        return cost

    def record_failed_attempt(self) -> None:
        if self.pending is not None:
            self.pending = None
        self.unknown = True

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": BUDGET_SCHEMA_VERSION,
            "currency": "CNY",
            "candidate_limit_cny_nanos": self.limit,
            "call_limit": self.call_limit,
            "call_count": self.call_count,
            "estimated_cost_from_usage_cny_nanos": (
                None if self.pending is not None or self.unknown else self.estimated_cost
            ),
            "actual_billed_cost_cny_nanos": None,
            "actual_billed_cost_status": "unknown_not_provider_invoice",
            "reservations": deepcopy(self.reservations),
        }


DynamicBudget = ReservedCallBudget


@dataclass
class ProviderAttempt:
    request: dict[str, Any]
    observation: dict[str, Any]
    parsed: dict[str, Any] | None
    raw_result: Any
    cost: dict[str, Any] | None
    failure_code: str | None
    failure_stage: str | None


def attempt_call(
    *,
    transport: Any,
    mode: str,
    budget: ReservedCallBudget,
    request: dict[str, Any],
) -> ProviderAttempt:
    budget.reserve(request)
    body = request["request_body_utf8"].encode("utf-8")
    timeout_ms = request["timeout_ms"]
    try:
        response = transport.post_json(url=ENDPOINT_URL, body=body, timeout_ms=timeout_ms)
    except Tg07c0TransportError as exc:
        budget.record_failed_attempt()
        observations = transport.safe_observations()
        observation = observations[-1] if observations else {
            "schema_version": "missing-observation",
        }
        return ProviderAttempt(request, observation, None, None, None, exc.code, "transport")
    except BaseException:
        budget.record_failed_attempt()
        observations = transport.safe_observations() if hasattr(transport, "safe_observations") else []
        observation = observations[-1] if observations else {"schema_version": "missing-observation"}
        return ProviderAttempt(
            request, observation, None, None, None,
            "dynamic_candidate_transport_error", "transport",
        )
    observations = transport.safe_observations()
    if not observations:
        budget.record_failed_attempt()
        return ProviderAttempt(
            request, {"schema_version": "missing-observation"}, None, None, None,
            "dynamic_candidate_transport_observation_missing", "transport",
        )
    observation = observations[-1]
    try:
        validate_transport_observation(
            observation,
            expected_request_body=body,
            expected_timeout=timeout_ms,
            expected_ordinal=request["sequence"],
            expected_mode=mode,
        )
    except Tg07c0TransportError:
        budget.record_failed_attempt()
        return ProviderAttempt(
            request, observation, None, None, None,
            "dynamic_candidate_transport_observation_invalid", "transport",
        )
    if (
        type(response) is not TransportResponse
        or response.status_code != 200
        or response.final_url != ENDPOINT_URL
        or type(response.content_type) is not str
        or response.content_type.split(";", 1)[0].strip().lower() != "application/json"
    ):
        budget.record_failed_attempt()
        return ProviderAttempt(
            request, observation, None, None, None,
            "dynamic_candidate_http_response_invalid", "provider_response",
        )
    try:
        parsed = parse_chat_completion_compatible(response.body)
        raw = strict_json_loads(parsed["content"].encode("utf-8"))
        cost = budget.record_usage(request, parsed["usage"])
    except (Tg07aContractError, CallMechanismError) as exc:
        if budget.pending is not None:
            budget.record_failed_attempt()
        return ProviderAttempt(
            request, observation, None, None, None,
            getattr(exc, "code", "dynamic_candidate_provider_response_invalid"),
            "provider_response",
        )
    return ProviderAttempt(request, observation, parsed, raw, cost, None, None)


__all__ = [
    "BUDGET_SCHEMA_VERSION",
    "CALL_LIMIT",
    "CANDIDATE_LIMIT_CNY_NANOS",
    "CallMechanismError",
    "DynamicBudget",
    "ProviderAttempt",
    "ReservedCallBudget",
    "TIMEOUT_MS",
    "attempt_call",
    "build_request_identity",
]

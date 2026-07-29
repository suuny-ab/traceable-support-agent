"""Independent, stdlib-only DeepSeek request, response, and ledger contracts."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


PROVIDER_SCHEMA_VERSION = "tg07a-deepseek-content-provider-v1"
MANIFEST_SCHEMA_VERSION = "tg07a-deepseek-content-manifest-v1"
REQUEST_SCHEMA_VERSION = "tg07a-deepseek-chat-request-v1"
REQUEST_PROJECTION_SCHEMA_VERSION = "tg07a-deepseek-safe-request-v1"
ATTEMPT_SCHEMA_VERSION = "tg07a-real-provider-attempt-v1"
TRANSCRIPT_SCHEMA_VERSION = "tg07a-real-provider-transcript-v1"
PRICE_SCHEMA_VERSION = "deepseek-official-cny-2026-07-15-v1"
PLAN_INPUT_SCHEMA_VERSION = "tg07a-evidence-plan-input-v1"
CONTENT_INPUT_SCHEMA_VERSION = "tg07a-structured-content-input-v1"
PLAN_OUTPUT_SCHEMA_VERSION = "tg07a-evidence-plan-json-v1"
CONTENT_OUTPUT_SCHEMA_VERSION = "tg07a-structured-content-json-v1"
PLAN_PROMPT_VERSION = "tg07a-evidence-plan-prompt-v1"
CONTENT_PROMPT_VERSION = "tg07a-structured-content-prompt-v1"
RESPONSE_PROJECTION_SCHEMA_VERSION = "tg07a-provider-response-safe-v1"

PROVIDER = "deepseek"
BASE_URL = "https://api.deepseek.com"
ENDPOINT_PATH = "/chat/completions"
ENDPOINT_URL = BASE_URL + ENDPOINT_PATH
MODEL = "deepseek-v4-pro"
STAGE_PLAN = "evidence_plan"
STAGE_CONTENT = "structured_content"
STAGES = (STAGE_PLAN, STAGE_CONTENT)
MAX_REQUEST_BYTES = 65_536
MAX_RESPONSE_BYTES = 131_072
DEFAULT_TIMEOUT_MS = 30_000
MIN_TIMEOUT_MS = 1
MAX_TIMEOUT_MS = 60_000
_PLAN_MAX_OUTPUT_TOKENS = 1024
_CONTENT_MAX_OUTPUT_TOKENS = 4096
MAX_OUTPUT_TOKENS = MappingProxyType(
    {STAGE_PLAN: _PLAN_MAX_OUTPUT_TOKENS, STAGE_CONTENT: _CONTENT_MAX_OUTPUT_TOKENS}
)
MAX_TOKEN_COUNT = 10**12

_CACHE_HIT_NANOS_PER_TOKEN = 25
_CACHE_MISS_NANOS_PER_TOKEN = 3000
_OUTPUT_NANOS_PER_TOKEN = 6000


def _price_snapshot_dict() -> dict[str, Any]:
    return {
        "schema_version": PRICE_SCHEMA_VERSION,
        "provider": PROVIDER,
        "model": MODEL,
        "currency": "CNY",
        "effective_date": "2026-07-15",
        "source_url": "https://api-docs.deepseek.com/quick_start/pricing/",
        "cache_hit_input_cny_per_million_tokens": "0.025",
        "cache_miss_input_cny_per_million_tokens": "3",
        "output_cny_per_million_tokens": "6",
        "cache_hit_input_cny_nanos_per_token": _CACHE_HIT_NANOS_PER_TOKEN,
        "cache_miss_input_cny_nanos_per_token": _CACHE_MISS_NANOS_PER_TOKEN,
        "output_cny_nanos_per_token": _OUTPUT_NANOS_PER_TOKEN,
    }


PRICE_SNAPSHOT = MappingProxyType(_price_snapshot_dict())

PLAN_EXAMPLE = {
    "schema_version": PLAN_OUTPUT_SCHEMA_VERSION,
    "stage": STAGE_PLAN,
    "issue_points": ["需要核对当前型号的操作步骤"],
    "model_scope": {"mode": "current_model_only", "models": ["CZ-R1"]},
    "query_intents": [
        {"intent_id": "intent-1", "query": "CZ-R1 操作步骤", "model_scope": ["CZ-R1"]}
    ],
}
CONTENT_EXAMPLE = {
    "schema_version": CONTENT_OUTPUT_SCHEMA_VERSION,
    "stage": STAGE_CONTENT,
    "content_units": [{"unit_id": "unit-1", "text": "结构化内容示例"}],
}
PROMPTS = MappingProxyType({
    STAGE_PLAN: (
        "你是受控证据计划生成器。只能输出一个合法JSON对象，不得输出Markdown或解释。"
        "JSON必须严格匹配给定示例的字段和类型。示例："
        + json.dumps(PLAN_EXAMPLE, ensure_ascii=False, separators=(",", ":"))
    ),
    STAGE_CONTENT: (
        "你是受控结构化内容生成器。只能输出一个合法JSON对象，不得输出Markdown或解释。"
        "JSON必须严格匹配给定示例的字段和类型。示例："
        + json.dumps(CONTENT_EXAMPLE, ensure_ascii=False, separators=(",", ":"))
    ),
})

FAILURE_CODES = frozenset({
    "provider_request_too_large",
    "provider_credential_missing",
    "provider_timeout",
    "provider_transport_error",
    "provider_redirect_rejected",
    "provider_http_status_invalid",
    "provider_content_type_invalid",
    "provider_response_too_large",
    "provider_response_json_invalid",
    "provider_response_envelope_invalid",
    "provider_model_mismatch",
    "provider_reasoning_unexpected",
    "provider_usage_missing",
    "provider_usage_invalid",
    "provider_content_invalid",
    "provider_sensitive_reflection",
})

_FORBIDDEN_PERSISTED_TEXT_MARKERS = (
    "bearer ",
    "authorization:",
    "proxy-authorization",
    "chain-of-thought",
    "chain of thought",
    "<think>",
    "</think>",
    "思维链",
)


class Tg07aContractError(ValueError):
    """A fixed-code error that never embeds untrusted input."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
        self.__cause__ = None
        self.__context__ = None


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError, OverflowError):
        raise Tg07aContractError("tg07a_json_not_canonical") from None


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_canonical(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def json_exact_equal(left: Any, right: Any) -> bool:
    try:
        return canonical_json_bytes(left) == canonical_json_bytes(right)
    except Tg07aContractError:
        return False


def _reject_constant(_: str) -> None:
    raise Tg07aContractError("provider_response_json_invalid")


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Tg07aContractError("provider_response_json_invalid")
        result[key] = value
    return result


def strict_json_loads(value: bytes, *, maximum: int = MAX_RESPONSE_BYTES) -> Any:
    if type(value) is not bytes or not value:
        raise Tg07aContractError("provider_response_json_invalid")
    if len(value) > maximum:
        raise Tg07aContractError("provider_response_too_large")
    try:
        text = value.decode("utf-8", errors="strict")
        return json.loads(
            text,
            object_pairs_hook=_strict_pairs,
            parse_constant=_reject_constant,
        )
    except Tg07aContractError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError, RecursionError, OverflowError):
        raise Tg07aContractError("provider_response_json_invalid") from None


def _exact(value: Any, keys: set[str], code: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise Tg07aContractError(code)
    return value


def _text(value: Any, code: str, maximum: int = 512) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        raise Tg07aContractError(code)
    return value


def _int(value: Any, code: str, minimum: int = 0, maximum: int = MAX_TOKEN_COUNT) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        raise Tg07aContractError(code)
    return value


def _sha(value: Any, code: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise Tg07aContractError(code)
    return value


def _texts(value: Any, code: str, minimum: int = 1, maximum: int = 8) -> list[str]:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise Tg07aContractError(code)
    result = [_text(item, code, 512) for item in value]
    if len(result) != len(set(result)):
        raise Tg07aContractError(code)
    return result


def _money(nanos: int) -> str:
    return f"{nanos // 1_000_000_000}.{nanos % 1_000_000_000:09d}"


def assert_no_sensitive_material(
    value: Any,
    *,
    sensitive_values: tuple[str, ...] = (),
) -> None:
    """Reject credential/header/reasoning markers and caller-provided canaries."""

    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise Tg07aContractError("provider_sensitive_reflection")
            normalized_key = key.lower().replace("_", "-")
            if (
                "authorization" in normalized_key
                or "api-key" in normalized_key
            ):
                raise Tg07aContractError("provider_sensitive_reflection")
            assert_no_sensitive_material(item, sensitive_values=sensitive_values)
        return
    if type(value) is list:
        for item in value:
            assert_no_sensitive_material(item, sensitive_values=sensitive_values)
        return
    if type(value) is str:
        lowered = value.lower()
        if any(marker in lowered for marker in _FORBIDDEN_PERSISTED_TEXT_MARKERS):
            raise Tg07aContractError("provider_sensitive_reflection")
        for secret in sensitive_values:
            if type(secret) is str and secret and secret in value:
                raise Tg07aContractError("provider_sensitive_reflection")


def build_manifest() -> dict[str, Any]:
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "provider_schema_version": PROVIDER_SCHEMA_VERSION,
        "provider": PROVIDER,
        "base_url": BASE_URL,
        "endpoint_path": ENDPOINT_PATH,
        "endpoint_url": ENDPOINT_URL,
        "model": MODEL,
        "stream": False,
        "thinking": {"type": "disabled"},
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "automatic_retry_count": 0,
        "max_request_bytes": MAX_REQUEST_BYTES,
        "max_response_bytes": MAX_RESPONSE_BYTES,
        "timeout_ms": DEFAULT_TIMEOUT_MS,
        "timeout_range_ms": [MIN_TIMEOUT_MS, MAX_TIMEOUT_MS],
        "max_output_tokens": dict(MAX_OUTPUT_TOKENS),
        "prompt_versions": {
            STAGE_PLAN: PLAN_PROMPT_VERSION,
            STAGE_CONTENT: CONTENT_PROMPT_VERSION,
        },
        "prompt_sha256": {stage: sha256_bytes(PROMPTS[stage].encode("utf-8")) for stage in STAGES},
        "output_schema_versions": {
            STAGE_PLAN: PLAN_OUTPUT_SCHEMA_VERSION,
            STAGE_CONTENT: CONTENT_OUTPUT_SCHEMA_VERSION,
        },
        "price_snapshot": _price_snapshot_dict(),
        "credential_source": "current_process_DEEPSEEK_API_KEY_at_transport_send_only",
        "proxy_mode": "disabled",
        "redirect_mode": "rejected",
        "tg07a_execution_mode": "offline_injected_and_authorized_real",
        "real_transport_wiring_status": "wired_for_authorized_real_runs_only",
    }
    manifest["manifest_sha256"] = sha256_canonical(manifest)
    return manifest


def validate_manifest(value: Any) -> dict[str, Any]:
    expected = build_manifest()
    if not json_exact_equal(value, expected):
        raise Tg07aContractError("provider_manifest_invalid")
    return deepcopy(expected)


def validate_stage_input(stage: str, value: Any) -> dict[str, Any]:
    code = "provider_request_invalid"
    if stage not in STAGES:
        raise Tg07aContractError("provider_stage_invalid")
    common = {"schema_version", "task_type", "product_model", "object_text"}
    keys = common if stage == STAGE_PLAN else common | {"candidate_evidence_ids", "candidate_evidence_sha256"}
    assert_no_sensitive_material(value)
    data = _exact(value, keys, code)
    expected_schema = PLAN_INPUT_SCHEMA_VERSION if stage == STAGE_PLAN else CONTENT_INPUT_SCHEMA_VERSION
    if data["schema_version"] != expected_schema or data["task_type"] not in {"qa", "ticket"}:
        raise Tg07aContractError(code)
    _text(data["product_model"], code, 128)
    _text(data["object_text"], code, 8000)
    if stage == STAGE_CONTENT:
        _texts(data["candidate_evidence_ids"], code)
        _sha(data["candidate_evidence_sha256"], code)
    return deepcopy(data)


@dataclass(frozen=True)
class PreparedRequest:
    stage: str
    body: bytes
    safe_projection: dict[str, Any]


def build_chat_request(
    *, stage: str, object_id: str, run_id: str, stage_input: Any, timeout_ms: int = DEFAULT_TIMEOUT_MS
) -> PreparedRequest:
    _text(object_id, "provider_request_invalid", 128)
    _text(run_id, "provider_request_invalid", 128)
    _int(timeout_ms, "provider_timeout_invalid", MIN_TIMEOUT_MS, MAX_TIMEOUT_MS)
    data = validate_stage_input(stage, stage_input)
    manifest = build_manifest()
    user_payload = {
        "request_schema_version": REQUEST_SCHEMA_VERSION,
        "stage": stage,
        "object_id": object_id,
        "run_id": run_id,
        "input": data,
    }
    request = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": PROMPTS[stage]},
            {"role": "user", "content": canonical_json_bytes(user_payload).decode("utf-8")},
        ],
        "stream": False,
        "thinking": {"type": "disabled"},
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": MAX_OUTPUT_TOKENS[stage],
    }
    body = canonical_json_bytes(request)
    projection = {
        "schema_version": REQUEST_PROJECTION_SCHEMA_VERSION,
        "provider": PROVIDER,
        "model": MODEL,
        "config_sha256": manifest["manifest_sha256"],
        "prompt_version": manifest["prompt_versions"][stage],
        "prompt_sha256": manifest["prompt_sha256"][stage],
        "output_schema_version": manifest["output_schema_versions"][stage],
        "stage": stage,
        "object_id": object_id,
        "run_id": run_id,
        "stage_input_sha256": sha256_canonical(data),
        "object_text_sha256": sha256_bytes(data["object_text"].encode("utf-8")),
        "request_body_sha256": sha256_bytes(body),
        "request_bytes": len(body),
        "max_output_tokens": MAX_OUTPUT_TOKENS[stage],
        "timeout_ms": timeout_ms,
        "automatic_retry_count": 0,
    }
    return PreparedRequest(stage=stage, body=body, safe_projection=projection)


def validate_usage(value: Any) -> dict[str, int]:
    if value is None:
        raise Tg07aContractError("provider_usage_missing")
    usage = _exact(
        value,
        {
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "prompt_cache_hit_tokens",
            "prompt_cache_miss_tokens",
        },
        "provider_usage_invalid",
    )
    result = {key: _int(item, "provider_usage_invalid") for key, item in usage.items()}
    if result["prompt_tokens"] != result["prompt_cache_hit_tokens"] + result["prompt_cache_miss_tokens"]:
        raise Tg07aContractError("provider_usage_invalid")
    if result["total_tokens"] != result["prompt_tokens"] + result["completion_tokens"]:
        raise Tg07aContractError("provider_usage_invalid")
    return result


def calculate_cost(usage: Any) -> dict[str, Any]:
    checked = validate_usage(usage)
    nanos = (
        checked["prompt_cache_hit_tokens"] * _CACHE_HIT_NANOS_PER_TOKEN
        + checked["prompt_cache_miss_tokens"] * _CACHE_MISS_NANOS_PER_TOKEN
        + checked["completion_tokens"] * _OUTPUT_NANOS_PER_TOKEN
    )
    if nanos > 2**63 - 1:
        raise Tg07aContractError("provider_usage_invalid")
    return {
        "schema_version": "tg07a-provider-cost-v1",
        "price_snapshot_sha256": sha256_canonical(_price_snapshot_dict()),
        "currency": "CNY",
        "amount_cny_nanos": nanos,
        "amount_cny": _money(nanos),
    }


def validate_response_safe_projection(value: Any) -> dict[str, Any]:
    code = "provider_response_projection_invalid"
    projection = _exact(
        value,
        {
            "schema_version", "provider_response_id_sha256", "object", "created",
            "model", "system_fingerprint_sha256", "finish_reason",
        },
        code,
    )
    if (
        projection["schema_version"] != RESPONSE_PROJECTION_SCHEMA_VERSION
        or projection["object"] != "chat.completion"
        or projection["model"] != MODEL
        or projection["finish_reason"] != "stop"
    ):
        raise Tg07aContractError(code)
    _sha(projection["provider_response_id_sha256"], code)
    _int(projection["created"], code)
    _sha(projection["system_fingerprint_sha256"], code)
    return deepcopy(projection)


def parse_chat_completion(body: bytes, *, sensitive_values: tuple[str, ...] = ()) -> dict[str, Any]:
    if type(body) is not bytes:
        raise Tg07aContractError("provider_response_json_invalid")
    if len(body) > MAX_RESPONSE_BYTES:
        raise Tg07aContractError("provider_response_too_large")
    for secret in sensitive_values:
        if type(secret) is str and secret and secret.encode("utf-8") in body:
            raise Tg07aContractError("provider_sensitive_reflection")
    envelope = strict_json_loads(body)
    if type(envelope) is not dict:
        raise Tg07aContractError("provider_response_envelope_invalid")
    assert_no_sensitive_material(envelope, sensitive_values=sensitive_values)
    normalized_envelope = canonical_json_bytes(envelope)
    for secret in sensitive_values:
        if type(secret) is str and secret and secret.encode("utf-8") in normalized_envelope:
            raise Tg07aContractError("provider_sensitive_reflection")
    allowed = {"id", "object", "created", "model", "choices", "usage", "system_fingerprint"}
    if set(envelope) not in (allowed, allowed - {"usage"}):
        raise Tg07aContractError("provider_response_envelope_invalid")
    response_id = _text(envelope["id"], "provider_response_envelope_invalid", 256)
    if envelope["object"] != "chat.completion":
        raise Tg07aContractError("provider_response_envelope_invalid")
    created = _int(envelope["created"], "provider_response_envelope_invalid")
    if envelope["model"] != MODEL:
        raise Tg07aContractError("provider_model_mismatch")
    fingerprint = _text(envelope["system_fingerprint"], "provider_response_envelope_invalid", 256)
    choices = envelope["choices"]
    if type(choices) is not list or len(choices) != 1:
        raise Tg07aContractError("provider_response_envelope_invalid")
    choice = _exact(choices[0], {"index", "message", "finish_reason", "logprobs"}, "provider_response_envelope_invalid")
    if (
        type(choice["index"]) is not int
        or choice["index"] != 0
        or choice["finish_reason"] != "stop"
        or choice["logprobs"] is not None
    ):
        raise Tg07aContractError("provider_response_envelope_invalid")
    message = choice["message"]
    if type(message) is not dict or set(message) not in ({"role", "content"}, {"role", "content", "reasoning_content"}):
        raise Tg07aContractError("provider_response_envelope_invalid")
    if message["role"] != "assistant":
        raise Tg07aContractError("provider_response_envelope_invalid")
    content = _text(message["content"], "provider_response_envelope_invalid", MAX_RESPONSE_BYTES)
    if "reasoning_content" in message and message["reasoning_content"] not in (None, ""):
        raise Tg07aContractError("provider_reasoning_unexpected")
    usage = validate_usage(envelope.get("usage"))
    return {
        "response_safe_projection": {
            "schema_version": RESPONSE_PROJECTION_SCHEMA_VERSION,
            "provider_response_id_sha256": sha256_bytes(response_id.encode("utf-8")),
            "object": "chat.completion",
            "created": created,
            "model": MODEL,
            "system_fingerprint_sha256": sha256_bytes(fingerprint.encode("utf-8")),
            "finish_reason": "stop",
        },
        "usage": usage,
        "cost": calculate_cost(usage),
        "content": content,
    }


def validate_stage_result(stage: str, value: Any) -> dict[str, Any]:
    code = "provider_content_invalid"
    assert_no_sensitive_material(value)
    if stage == STAGE_PLAN:
        result = _exact(value, {"schema_version", "stage", "issue_points", "model_scope", "query_intents"}, code)
        if result["schema_version"] != PLAN_OUTPUT_SCHEMA_VERSION or result["stage"] != stage:
            raise Tg07aContractError(code)
        _texts(result["issue_points"], code)
        scope = _exact(result["model_scope"], {"mode", "models"}, code)
        if scope["mode"] != "current_model_only":
            raise Tg07aContractError(code)
        _texts(scope["models"], code)
        intents = result["query_intents"]
        if type(intents) is not list or not 1 <= len(intents) <= 4:
            raise Tg07aContractError(code)
        observed: list[str] = []
        for raw in intents:
            intent = _exact(raw, {"intent_id", "query", "model_scope"}, code)
            observed.append(_text(intent["intent_id"], code, 128))
            _text(intent["query"], code, 512)
            _texts(intent["model_scope"], code)
        if len(observed) != len(set(observed)):
            raise Tg07aContractError(code)
    elif stage == STAGE_CONTENT:
        result = _exact(value, {"schema_version", "stage", "content_units"}, code)
        if result["schema_version"] != CONTENT_OUTPUT_SCHEMA_VERSION or result["stage"] != stage:
            raise Tg07aContractError(code)
        units = result["content_units"]
        if type(units) is not list or not 1 <= len(units) <= 8:
            raise Tg07aContractError(code)
        ids: list[str] = []
        for raw in units:
            unit = _exact(raw, {"unit_id", "text"}, code)
            ids.append(_text(unit["unit_id"], code, 128))
            _text(unit["text"], code, 4000)
        if len(ids) != len(set(ids)):
            raise Tg07aContractError(code)
    else:
        raise Tg07aContractError("provider_stage_invalid")
    return deepcopy(result)


ATTEMPT_KEYS = {
    "schema_version", "status", "provider", "model", "config_sha256",
    "prompt_version", "output_schema_version", "stage", "object_id", "run_id",
    "sequence", "transport_attempted", "automatic_retry_count", "timeout_ms",
    "http_status", "provider_response_received", "latency_ms",
    "request_safe_projection", "response_safe_projection", "structured_result",
    "structured_result_sha256",
    "usage", "cost", "failure_code", "previous_record_sha256", "record_sha256",
    "execution_mode", "transport_kind", "network_attempted", "dns_attempted",
    "credential_read_attempted", "paid_call_performed", "actual_paid_cost_cny_nanos",
    "cost_semantics",
}


def build_attempt_record(**fields: Any) -> dict[str, Any]:
    record = {"schema_version": ATTEMPT_SCHEMA_VERSION, **deepcopy(fields)}
    assert_no_sensitive_material(record)
    if set(record) != ATTEMPT_KEYS - {"record_sha256"}:
        raise Tg07aContractError("provider_attempt_invalid")
    record["record_sha256"] = sha256_canonical(record)
    return record


TRANSCRIPT_MODE_KINDS = MappingProxyType(
    {"offline_injected": "local_injected", "authorized_real": "official_https"}
)


def finalize_transcript(
    *,
    object_id: str,
    run_id: str,
    records: list[dict[str, Any]],
    execution_mode: str = "offline_injected",
    transport_kind: str = "local_injected",
) -> dict[str, Any]:
    if TRANSCRIPT_MODE_KINDS.get(execution_mode) != transport_kind:
        raise Tg07aContractError("provider_transcript_invalid")
    manifest = build_manifest()
    estimated_cost_nanos = sum(
        record["cost"]["amount_cny_nanos"]
        for record in records
        if type(record.get("cost")) is dict
    )
    transcript = {
        "schema_version": TRANSCRIPT_SCHEMA_VERSION,
        "provider": PROVIDER,
        "model": MODEL,
        "object_id": object_id,
        "run_id": run_id,
        "config_manifest": manifest,
        "config_sha256": manifest["manifest_sha256"],
        "records": deepcopy(records),
        "record_count": len(records),
        "final_record_sha256": records[-1]["record_sha256"] if records else None,
        "execution_mode": execution_mode,
        "transport_kind": transport_kind,
        "network_attempt_count": sum(
            1 for record in records if record.get("network_attempted") is True
        ),
        "dns_attempt_count": sum(
            1 for record in records if record.get("dns_attempted") is True
        ),
        "credential_read_count": sum(
            1 for record in records if record.get("credential_read_attempted") is True
        ),
        "paid_call_count": sum(
            1 for record in records if record.get("paid_call_performed") is True
        ),
        "actual_paid_cost_cny_nanos": sum(
            record["actual_paid_cost_cny_nanos"]
            for record in records
            if type(record.get("actual_paid_cost_cny_nanos")) is int
        ),
        "estimated_cost_from_usage_cny_nanos": estimated_cost_nanos,
        "estimated_cost_semantics": "usage_pricing_estimate_not_invoice",
    }
    transcript["transcript_sha256"] = sha256_canonical(transcript)
    return transcript


def _validate_attempt_mode_facts(record: dict[str, Any]) -> None:
    """Bind network, credential, and billing facts to the execution mode.

    ``offline_injected`` keeps the original all-zero contract. ``authorized_real``
    accepts exactly the fact combinations the reviewed real transport can produce:
    a credential read on every transport attempt, DNS coupled to the network
    attempt, no response without a network attempt, and billing always unknown.
    The transport never learns whether a real call was billed, so the contract
    requires ``paid_call_performed is None`` and only allows
    ``actual_paid_cost_cny_nanos`` to be ``None`` (unknown) or ``0`` (no
    confirmed billed amount); it never asserts a real call was definitely
    billed or definitely free.
    """

    if record["execution_mode"] == "offline_injected":
        if (
            record["transport_kind"] != "local_injected"
            or record["network_attempted"] is not False
            or record["dns_attempted"] is not False
            or record["credential_read_attempted"] is not False
            or record["paid_call_performed"] is not False
            or type(record["actual_paid_cost_cny_nanos"]) is not int
            or record["actual_paid_cost_cny_nanos"] != 0
        ):
            raise Tg07aContractError("provider_attempt_invalid")
        return
    if record["execution_mode"] != "authorized_real":
        raise Tg07aContractError("provider_attempt_invalid")
    if (
        record["transport_kind"] != "official_https"
        or any(
            type(record[name]) is not bool
            for name in (
                "network_attempted",
                "dns_attempted",
                "credential_read_attempted",
            )
        )
        or record["paid_call_performed"] is not None
        or not (
            record["actual_paid_cost_cny_nanos"] is None
            or (
                type(record["actual_paid_cost_cny_nanos"]) is int
                and record["actual_paid_cost_cny_nanos"] == 0
            )
        )
        or record["dns_attempted"] != record["network_attempted"]
        or record["credential_read_attempted"] != record["transport_attempted"]
        or (record["network_attempted"] and not record["transport_attempted"])
        or (
            (record["provider_response_received"] or record["http_status"] is not None)
            and record["network_attempted"] is not True
        )
        or (
            record["failure_code"] == "provider_timeout"
            and record["network_attempted"] is not True
        )
    ):
        raise Tg07aContractError("provider_attempt_invalid")


def _validate_attempt(record: Any, *, sequence: int, previous: str | None, expected_request: PreparedRequest) -> dict[str, Any]:
    if type(record) is not dict or set(record) != ATTEMPT_KEYS:
        raise Tg07aContractError("provider_attempt_invalid")
    unsigned = {key: value for key, value in record.items() if key != "record_sha256"}
    if record["schema_version"] != ATTEMPT_SCHEMA_VERSION or record["record_sha256"] != sha256_canonical(unsigned):
        raise Tg07aContractError("provider_attempt_invalid")
    if record["sequence"] != sequence or type(record["sequence"]) is not int:
        raise Tg07aContractError("provider_attempt_invalid")
    if record["previous_record_sha256"] != previous:
        raise Tg07aContractError("provider_attempt_invalid")
    if not json_exact_equal(record["request_safe_projection"], expected_request.safe_projection):
        raise Tg07aContractError("provider_attempt_invalid")
    if (
        type(record["status"]) is not str
        or type(record["stage"]) is not str
        or record["stage"] not in STAGES
        or type(record["provider"]) is not str
        or type(record["model"]) is not str
        or type(record["config_sha256"]) is not str
        or type(record["prompt_version"]) is not str
        or type(record["output_schema_version"]) is not str
        or type(record["object_id"]) is not str
        or type(record["run_id"]) is not str
        or (record["failure_code"] is not None and type(record["failure_code"]) is not str)
    ):
        raise Tg07aContractError("provider_attempt_invalid")
    manifest = build_manifest()
    if (
        record["provider"] != PROVIDER
        or record["model"] != MODEL
        or record["config_sha256"] != manifest["manifest_sha256"]
        or record["stage"] != expected_request.stage
        or record["object_id"] != expected_request.safe_projection["object_id"]
        or record["run_id"] != expected_request.safe_projection["run_id"]
        or record["prompt_version"] != manifest["prompt_versions"][record["stage"]]
        or record["output_schema_version"] != manifest["output_schema_versions"][record["stage"]]
        or record["timeout_ms"] != expected_request.safe_projection["timeout_ms"]
        or type(record["transport_attempted"]) is not bool
        or type(record["provider_response_received"]) is not bool
        or type(record["latency_ms"]) is not int
        or record["latency_ms"] < 0
        or record["automatic_retry_count"] != 0
        or type(record["automatic_retry_count"]) is not int
        or type(record["execution_mode"]) is not str
        or type(record["transport_kind"]) is not str
    ):
        raise Tg07aContractError("provider_attempt_invalid")
    _validate_attempt_mode_facts(record)
    if record["http_status"] is not None and (type(record["http_status"]) is not int or not 100 <= record["http_status"] <= 599):
        raise Tg07aContractError("provider_attempt_invalid")
    if record["status"] == "succeeded":
        if (
            record["failure_code"] is not None
            or record["transport_attempted"] is not True
            or record["provider_response_received"] is not True
            or record["http_status"] != 200
            or type(record["response_safe_projection"]) is not dict
            or type(record["structured_result"]) is not dict
            or record["structured_result_sha256"] != sha256_canonical(record["structured_result"])
        ):
            raise Tg07aContractError("provider_attempt_invalid")
        result = validate_stage_result(record["stage"], record["structured_result"])
        usage = validate_usage(record["usage"])
        if not json_exact_equal(record["cost"], calculate_cost(usage)):
            raise Tg07aContractError("provider_attempt_invalid")
        if record["cost_semantics"] != "usage_pricing_estimate_not_invoice":
            raise Tg07aContractError("provider_attempt_invalid")
        validate_response_safe_projection(record["response_safe_projection"])
        if not json_exact_equal(result, record["structured_result"]):
            raise Tg07aContractError("provider_attempt_invalid")
    elif record["status"] == "failed":
        if (
            type(record["failure_code"]) is not str
            or record["failure_code"] not in FAILURE_CODES
            or record["structured_result"] is not None
            or record["structured_result_sha256"] is not None
        ):
            raise Tg07aContractError("provider_attempt_invalid")
        if record["usage"] is None:
            if record["cost"] is not None or record["cost_semantics"] is not None:
                raise Tg07aContractError("provider_attempt_invalid")
        else:
            usage = validate_usage(record["usage"])
            if not json_exact_equal(record["cost"], calculate_cost(usage)):
                raise Tg07aContractError("provider_attempt_invalid")
            if record["cost_semantics"] != "usage_pricing_estimate_not_invoice":
                raise Tg07aContractError("provider_attempt_invalid")
        no_response_codes = {"provider_timeout", "provider_transport_error"}
        parsed_response_codes = {
            "provider_response_json_invalid",
            "provider_response_envelope_invalid", "provider_model_mismatch",
            "provider_reasoning_unexpected", "provider_usage_missing",
            "provider_usage_invalid", "provider_content_type_invalid",
        }
        if record["failure_code"] == "provider_request_too_large":
            valid_facts = (
                record["transport_attempted"] is False
                and record["provider_response_received"] is False
                and record["http_status"] is None
                and record["response_safe_projection"] is None
                and record["usage"] is None
            )
        elif record["failure_code"] == "provider_credential_missing":
            # The real transport reports a missing credential before any
            # network attempt; offline transports never read credentials.
            valid_facts = (
                record["execution_mode"] == "authorized_real"
                and record["transport_attempted"] is True
                and record["provider_response_received"] is False
                and record["http_status"] is None
                and record["response_safe_projection"] is None
                and record["usage"] is None
                and record["network_attempted"] is False
            )
        elif record["failure_code"] in no_response_codes:
            valid_facts = (
                record["transport_attempted"] is True
                and record["provider_response_received"] is False
                and record["http_status"] is None
                and record["response_safe_projection"] is None
                and record["usage"] is None
            )
        elif record["failure_code"] == "provider_redirect_rejected":
            valid_facts = (
                record["transport_attempted"] is True
                and record["response_safe_projection"] is None
                and record["usage"] is None
                and (
                    (record["provider_response_received"] is False and record["http_status"] is None)
                    or (record["provider_response_received"] is True and record["http_status"] is not None)
                )
            )
        elif record["failure_code"] == "provider_http_status_invalid":
            valid_facts = (
                record["transport_attempted"] is True
                and record["provider_response_received"] is True
                and record["http_status"] not in (None, 200)
                and record["response_safe_projection"] is None
                and record["usage"] is None
            )
        elif record["failure_code"] == "provider_sensitive_reflection":
            valid_facts = (
                record["response_safe_projection"] is None
                and record["usage"] is None
                and (
                    (
                        record["transport_attempted"] is False
                        and record["provider_response_received"] is False
                        and record["http_status"] is None
                    )
                    or (
                        record["transport_attempted"] is True
                        and record["provider_response_received"] is False
                        and record["http_status"] is None
                    )
                    or (
                        record["transport_attempted"] is True
                        and record["provider_response_received"] is True
                        and record["http_status"] == 200
                    )
                )
            )
        elif record["failure_code"] == "provider_response_too_large":
            # Two faithful shapes: the adapter discarded an already received
            # 200 response body (received + 200), or the real transport read
            # past the byte cap and dropped the response object entirely
            # (no received fact, no status, but a network attempt happened).
            valid_facts = (
                record["transport_attempted"] is True
                and record["response_safe_projection"] is None
                and record["usage"] is None
                and (
                    (
                        record["provider_response_received"] is True
                        and record["http_status"] == 200
                    )
                    or (
                        record["execution_mode"] == "authorized_real"
                        and record["provider_response_received"] is False
                        and record["http_status"] is None
                        and record["network_attempted"] is True
                    )
                )
            )
        elif record["failure_code"] in parsed_response_codes:
            valid_facts = (
                record["transport_attempted"] is True
                and record["provider_response_received"] is True
                and record["http_status"] == 200
                and record["response_safe_projection"] is None
                and record["usage"] is None
            )
        else:
            valid_facts = (
                record["failure_code"] == "provider_content_invalid"
                and record["transport_attempted"] is True
                and record["provider_response_received"] is True
                and record["http_status"] == 200
                and type(record["response_safe_projection"]) is dict
                and record["usage"] is not None
            )
        if not valid_facts:
            raise Tg07aContractError("provider_attempt_invalid")
        if record["failure_code"] == "provider_content_invalid":
            validate_response_safe_projection(record["response_safe_projection"])
    else:
        raise Tg07aContractError("provider_attempt_invalid")
    return deepcopy(record)


def validate_transcript(
    value: Any,
    *,
    expected_object_id: str,
    expected_run_id: str,
    expected_calls: list[dict[str, Any]],
    trusted_transcript_sha256: str,
) -> dict[str, Any]:
    keys = {
        "schema_version", "provider", "model", "object_id", "run_id",
        "config_manifest", "config_sha256", "records", "record_count",
        "final_record_sha256", "transcript_sha256",
        "execution_mode", "transport_kind", "network_attempt_count",
        "dns_attempt_count", "credential_read_count", "paid_call_count",
        "actual_paid_cost_cny_nanos", "estimated_cost_from_usage_cny_nanos",
        "estimated_cost_semantics",
    }
    transcript = _exact(value, keys, "provider_transcript_invalid")
    unsigned = {key: item for key, item in transcript.items() if key != "transcript_sha256"}
    recomputed = sha256_canonical(unsigned)
    _sha(trusted_transcript_sha256, "provider_transcript_invalid")
    if transcript["transcript_sha256"] != recomputed or recomputed != trusted_transcript_sha256:
        raise Tg07aContractError("provider_transcript_invalid")
    manifest = validate_manifest(transcript["config_manifest"])
    if (
        transcript["schema_version"] != TRANSCRIPT_SCHEMA_VERSION
        or transcript["provider"] != PROVIDER
        or transcript["model"] != MODEL
        or transcript["object_id"] != expected_object_id
        or transcript["run_id"] != expected_run_id
        or transcript["config_sha256"] != manifest["manifest_sha256"]
        or type(transcript["records"]) is not list
        or type(transcript["record_count"]) is not int
        or transcript["record_count"] != len(transcript["records"])
        or len(expected_calls) != len(transcript["records"])
        or type(transcript["execution_mode"]) is not str
        or type(transcript["transport_kind"]) is not str
        or type(transcript["network_attempt_count"]) is not int
        or transcript["network_attempt_count"] < 0
        or type(transcript["dns_attempt_count"]) is not int
        or transcript["dns_attempt_count"] < 0
        or type(transcript["credential_read_count"]) is not int
        or transcript["credential_read_count"] < 0
        or type(transcript["paid_call_count"]) is not int
        or transcript["paid_call_count"] < 0
        or type(transcript["actual_paid_cost_cny_nanos"]) is not int
        or transcript["actual_paid_cost_cny_nanos"] < 0
        or transcript["estimated_cost_semantics"] != "usage_pricing_estimate_not_invoice"
    ):
        raise Tg07aContractError("provider_transcript_invalid")
    if (
        TRANSCRIPT_MODE_KINDS.get(transcript["execution_mode"])
        != transcript["transport_kind"]
    ):
        raise Tg07aContractError("provider_transcript_invalid")
    if transcript["execution_mode"] == "offline_injected":
        if (
            transcript["network_attempt_count"] != 0
            or transcript["dns_attempt_count"] != 0
            or transcript["credential_read_count"] != 0
            or transcript["paid_call_count"] != 0
            or transcript["actual_paid_cost_cny_nanos"] != 0
        ):
            raise Tg07aContractError("provider_transcript_invalid")
    elif transcript["credential_read_count"] < 1:
        raise Tg07aContractError("provider_transcript_invalid")
    previous: str | None = None
    expected_stage_order = [STAGE_PLAN, STAGE_CONTENT]
    for index, (record, expected_call) in enumerate(zip(transcript["records"], expected_calls), 1):
        if type(expected_call) is not dict or set(expected_call) != {"stage", "stage_input", "timeout_ms"}:
            raise Tg07aContractError("provider_transcript_invalid")
        if index > len(expected_stage_order) or expected_call["stage"] != expected_stage_order[index - 1]:
            raise Tg07aContractError("provider_transcript_invalid")
        prepared = build_chat_request(
            stage=expected_call["stage"],
            object_id=expected_object_id,
            run_id=expected_run_id,
            stage_input=expected_call["stage_input"],
            timeout_ms=expected_call["timeout_ms"],
        )
        checked = _validate_attempt(record, sequence=index, previous=previous, expected_request=prepared)
        if (
            checked["execution_mode"] != transcript["execution_mode"]
            or checked["transport_kind"] != transcript["transport_kind"]
        ):
            raise Tg07aContractError("provider_transcript_invalid")
        previous = checked["record_sha256"]
        if checked["status"] == "failed" and index != len(transcript["records"]):
            raise Tg07aContractError("provider_transcript_invalid")
    if transcript["final_record_sha256"] != previous:
        raise Tg07aContractError("provider_transcript_invalid")
    expected_estimated_cost = sum(
        record["cost"]["amount_cny_nanos"]
        for record in transcript["records"]
        if type(record["cost"]) is dict
    )
    if (
        type(transcript["estimated_cost_from_usage_cny_nanos"]) is not int
        or transcript["estimated_cost_from_usage_cny_nanos"] != expected_estimated_cost
    ):
        raise Tg07aContractError("provider_transcript_invalid")
    counter_facts = (
        ("network_attempt_count", "network_attempted"),
        ("dns_attempt_count", "dns_attempted"),
        ("credential_read_count", "credential_read_attempted"),
        ("paid_call_count", "paid_call_performed"),
    )
    if any(
        transcript[count_key]
        != sum(1 for record in transcript["records"] if record[fact_key] is True)
        for count_key, fact_key in counter_facts
    ):
        raise Tg07aContractError("provider_transcript_invalid")
    if transcript["actual_paid_cost_cny_nanos"] != sum(
        record["actual_paid_cost_cny_nanos"]
        for record in transcript["records"]
        if type(record["actual_paid_cost_cny_nanos"]) is int
    ):
        raise Tg07aContractError("provider_transcript_invalid")
    return deepcopy(transcript)

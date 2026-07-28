"""Transcript contract tests for offline and authorized-real execution modes."""

from __future__ import annotations

import pytest

from traceable_support.provider.contract import (
    CONTENT_EXAMPLE,
    CONTENT_INPUT_SCHEMA_VERSION,
    MODEL,
    PLAN_EXAMPLE,
    PLAN_INPUT_SCHEMA_VERSION,
    PROVIDER,
    RESPONSE_PROJECTION_SCHEMA_VERSION,
    STAGE_CONTENT,
    STAGE_PLAN,
    Tg07aContractError,
    build_attempt_record,
    build_chat_request,
    build_manifest,
    calculate_cost,
    finalize_transcript,
    sha256_bytes,
    sha256_canonical,
    validate_transcript,
)
from traceable_support.provider.response import (
    DeepSeekContentAdapter,
    LocalInjectedTransport,
    json_response,
)

OBJECT_ID = "case-real-run-evidence"
RUN_ID = "run-real-run-evidence"
USAGE = {
    "prompt_tokens": 100,
    "completion_tokens": 100,
    "total_tokens": 200,
    "prompt_cache_hit_tokens": 0,
    "prompt_cache_miss_tokens": 100,
}
PLAN_INPUT = {
    "schema_version": PLAN_INPUT_SCHEMA_VERSION,
    "task_type": "qa",
    "product_model": "CZ-R1",
    "object_text": "CZ-R1 路线突然乱了，如何检查与复位？",
}
CONTENT_INPUT = {
    **PLAN_INPUT,
    "schema_version": CONTENT_INPUT_SCHEMA_VERSION,
    "candidate_evidence_ids": ["E1"],
    "candidate_evidence_sha256": sha256_bytes(b"E1"),
}
EXPECTED_CALLS = [
    {"stage": STAGE_PLAN, "stage_input": PLAN_INPUT, "timeout_ms": 30_000},
    {"stage": STAGE_CONTENT, "stage_input": CONTENT_INPUT, "timeout_ms": 30_000},
]


def _prepared(stage: str):
    stage_input = PLAN_INPUT if stage == STAGE_PLAN else CONTENT_INPUT
    return build_chat_request(
        stage=stage, object_id=OBJECT_ID, run_id=RUN_ID, stage_input=stage_input
    )


def _response_projection() -> dict:
    return {
        "schema_version": RESPONSE_PROJECTION_SCHEMA_VERSION,
        "provider_response_id_sha256": sha256_bytes(b"chatcmpl-real-run"),
        "object": "chat.completion",
        "created": 1,
        "model": MODEL,
        "system_fingerprint_sha256": sha256_bytes(b"fp_real_run"),
        "finish_reason": "stop",
    }


def _succeeded_record(
    *,
    prepared,
    sequence: int,
    previous: str | None,
    execution_mode: str,
    transport_kind: str,
    network_attempted: bool,
    dns_attempted: bool,
    credential_read_attempted: bool,
    paid_call_performed: bool,
    automatic_retry_count: int = 0,
) -> dict:
    manifest = build_manifest()
    result = PLAN_EXAMPLE if prepared.stage == STAGE_PLAN else CONTENT_EXAMPLE
    return build_attempt_record(
        status="succeeded",
        provider=PROVIDER,
        model=MODEL,
        config_sha256=manifest["manifest_sha256"],
        prompt_version=manifest["prompt_versions"][prepared.stage],
        output_schema_version=manifest["output_schema_versions"][prepared.stage],
        stage=prepared.stage,
        object_id=OBJECT_ID,
        run_id=RUN_ID,
        sequence=sequence,
        transport_attempted=True,
        automatic_retry_count=automatic_retry_count,
        timeout_ms=prepared.safe_projection["timeout_ms"],
        http_status=200,
        provider_response_received=True,
        latency_ms=0,
        request_safe_projection=prepared.safe_projection,
        response_safe_projection=_response_projection(),
        structured_result=result,
        structured_result_sha256=sha256_canonical(result),
        usage=dict(USAGE),
        cost=calculate_cost(dict(USAGE)),
        failure_code=None,
        previous_record_sha256=previous,
        execution_mode=execution_mode,
        transport_kind=transport_kind,
        network_attempted=network_attempted,
        dns_attempted=dns_attempted,
        credential_read_attempted=credential_read_attempted,
        paid_call_performed=paid_call_performed,
        actual_paid_cost_cny_nanos=0,
        cost_semantics="usage_pricing_estimate_not_invoice",
    )


def _real_records(**kwargs) -> list[dict]:
    facts = {
        "execution_mode": "authorized_real",
        "transport_kind": "official_https",
        "network_attempted": True,
        "dns_attempted": True,
        "credential_read_attempted": True,
        "paid_call_performed": True,
    }
    facts.update(kwargs)
    first = _succeeded_record(
        prepared=_prepared(STAGE_PLAN), sequence=1, previous=None, **facts
    )
    second = _succeeded_record(
        prepared=_prepared(STAGE_CONTENT),
        sequence=2,
        previous=first["record_sha256"],
        **facts,
    )
    return [first, second]


def _real_transcript(**kwargs) -> dict:
    return finalize_transcript(
        object_id=OBJECT_ID,
        run_id=RUN_ID,
        records=_real_records(**kwargs),
        execution_mode="authorized_real",
        transport_kind="official_https",
    )


def _offline_transcript() -> dict:
    transport = LocalInjectedTransport(
        [
            {"kind": "response", "status_code": 200,
             "body": json_response(PLAN_EXAMPLE, usage=dict(USAGE))},
            {"kind": "response", "status_code": 200,
             "body": json_response(CONTENT_EXAMPLE, usage=dict(USAGE))},
        ]
    )
    adapter = DeepSeekContentAdapter(
        transport=transport, object_id=OBJECT_ID, run_id=RUN_ID
    )
    assert adapter.invoke(stage=STAGE_PLAN, stage_input=PLAN_INPUT)["status"] == "succeeded"
    assert adapter.invoke(stage=STAGE_CONTENT, stage_input=CONTENT_INPUT)["status"] == "succeeded"
    return adapter.transcript()


def _validate(transcript: dict) -> dict:
    return validate_transcript(
        transcript,
        expected_object_id=OBJECT_ID,
        expected_run_id=RUN_ID,
        expected_calls=EXPECTED_CALLS,
        trusted_transcript_sha256=transcript["transcript_sha256"],
    )


def _resign(transcript: dict) -> dict:
    unsigned = {key: value for key, value in transcript.items() if key != "transcript_sha256"}
    transcript["transcript_sha256"] = sha256_canonical(unsigned)
    return transcript


def _assert_invalid(transcript: dict, code: str) -> None:
    with pytest.raises(Tg07aContractError) as caught:
        _validate(transcript)
    assert caught.value.code == code


def test_offline_adapter_transcript_still_validates_with_zero_counters() -> None:
    transcript = _offline_transcript()
    assert transcript["execution_mode"] == "offline_injected"
    assert transcript["transport_kind"] == "local_injected"
    assert transcript["network_attempt_count"] == 0
    assert transcript["credential_read_count"] == 0
    assert transcript["paid_call_count"] == 0
    assert _validate(transcript) == transcript


def test_coherent_authorized_real_transcript_validates() -> None:
    transcript = _real_transcript()
    assert transcript["network_attempt_count"] == 2
    assert transcript["dns_attempt_count"] == 2
    assert transcript["credential_read_count"] == 2
    assert transcript["paid_call_count"] == 2
    assert transcript["actual_paid_cost_cny_nanos"] == 0
    assert _validate(transcript) == transcript


def test_finalize_transcript_computes_counters_and_rejects_mode_kind_mismatch() -> None:
    with pytest.raises(Tg07aContractError) as caught:
        finalize_transcript(
            object_id=OBJECT_ID,
            run_id=RUN_ID,
            records=[],
            execution_mode="authorized_real",
            transport_kind="local_injected",
        )
    assert caught.value.code == "provider_transcript_invalid"


def test_offline_record_with_network_facts_is_rejected() -> None:
    transcript = _offline_transcript()
    records = transcript["records"]
    first = dict(records[0])
    first["network_attempted"] = True
    records[0] = build_attempt_record(
        **{key: value for key, value in first.items() if key != "record_sha256"}
    )
    _resign(transcript)
    _assert_invalid(transcript, "provider_attempt_invalid")


def test_authorized_real_succeeded_record_without_network_is_rejected() -> None:
    transcript = _real_transcript(network_attempted=False, dns_attempted=False)
    transcript["network_attempt_count"] = 1
    transcript["dns_attempt_count"] = 1
    _assert_invalid(_resign(transcript), "provider_attempt_invalid")


def test_automatic_retry_is_rejected_in_both_modes() -> None:
    _assert_invalid(_real_transcript(automatic_retry_count=1), "provider_attempt_invalid")
    transcript = _offline_transcript()
    records = transcript["records"]
    first = dict(records[0])
    first["automatic_retry_count"] = 1
    records[0] = build_attempt_record(
        **{key: value for key, value in first.items() if key != "record_sha256"}
    )
    _resign(transcript)
    _assert_invalid(transcript, "provider_attempt_invalid")


def test_authorized_real_without_credential_read_is_rejected() -> None:
    transcript = _real_transcript(credential_read_attempted=False)
    transcript["credential_read_count"] = 1
    _assert_invalid(_resign(transcript), "provider_attempt_invalid")


def test_authorized_real_transcript_with_zero_network_attempts_is_rejected() -> None:
    transcript = _real_transcript()
    transcript["network_attempt_count"] = 0
    transcript["dns_attempt_count"] = 0
    _assert_invalid(_resign(transcript), "provider_transcript_invalid")


def test_authorized_real_records_under_offline_transcript_mode_are_rejected() -> None:
    transcript = finalize_transcript(
        object_id=OBJECT_ID,
        run_id=RUN_ID,
        records=_real_records(),
    )
    _assert_invalid(transcript, "provider_transcript_invalid")


def test_transcript_counters_must_match_record_facts() -> None:
    transcript = _real_transcript()
    transcript["paid_call_count"] = 0
    _assert_invalid(_resign(transcript), "provider_transcript_invalid")
    transcript = _real_transcript()
    transcript["credential_read_count"] = 1
    _assert_invalid(_resign(transcript), "provider_transcript_invalid")


def test_offline_transcript_with_nonzero_counters_is_rejected() -> None:
    transcript = _offline_transcript()
    transcript["network_attempt_count"] = 1
    _assert_invalid(_resign(transcript), "provider_transcript_invalid")

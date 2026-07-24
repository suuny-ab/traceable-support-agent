from __future__ import annotations

import copy

import pytest

from traceable_support.generation.checklist import (
    TwoStepError,
    build_clause_inventory,
    checklist_model_projection,
    validate_step1_result,
)
from traceable_support.generation.failure_taxonomy import (
    classify_generation_failure,
    summarize_generation_failures,
)
from traceable_support.generation.qa_contract import (
    CandidateV4Error,
    validate_result,
)
from traceable_support.generation.ticket_contract import (
    TicketContractError,
    validate_ticket_result_v2,
)


EVIDENCE = [
    {
        "evidence_id": "E1",
        "text": "先按局部清扫键。完成后检查尘盒。",
    },
    {
        "evidence_id": "E2",
        "text": "不要在积水中运行。",
    },
]


def _raw_checklist() -> dict:
    inventory = build_clause_inventory(EVIDENCE)
    return {
        "schema_version": "obligation-checklist-v4",
        "obligations": [
            {
                "obligation_id": "o1",
                "description": "说明怎样启动指定区域的清洁",
                "clause_ids": [inventory[0]["clause_id"]],
            }
        ],
        "ignored_clause_ids": [
            entry["clause_id"] for entry in inventory[1:]
        ],
    }


def _checklist() -> dict:
    return validate_step1_result(
        {"case_id": "qa-1", "evidence": EVIDENCE},
        _raw_checklist(),
    )


def _qa_result() -> dict:
    return {
        "schema_version": "retrieved-top10-qa-result-v4",
        "task_type": "qa",
        "content": {
            "kind": "qa_answer",
            "answer": {"text": "请先按局部清扫键。"},
            "claims": [
                {
                    "claim_id": "c1",
                    "exact_span_text": "先按局部清扫键。",
                    "customer_visible_span_text": "请先按局部清扫键",
                    "evidence_ids": ["E1"],
                    "obligation_ids": ["o1"],
                }
            ],
            "insufficient_evidence": False,
        },
    }


def _ticket_result() -> dict:
    return {
        "schema_version": "ticket-proposal-result-v3",
        "task_type": "ticket",
        "content": {
            "kind": "ticket_proposal",
            "action_steps": ["请客户先按局部清扫键。"],
            "draft_reply": "请先按局部清扫键。",
            "claims": [
                {
                    "claim_id": "c1",
                    "exact_span_text": "先按局部清扫键。",
                    "customer_visible_span_text": "请先按局部清扫键",
                    "evidence_ids": ["E1"],
                    "obligation_ids": ["o1"],
                }
            ],
            "insufficient_evidence": False,
        },
    }


def test_v4_checklist_uses_semantic_clause_selection_and_derives_mechanical_fields() -> None:
    checklist = _checklist()

    assert checklist["schema_version"] == "obligation-checklist-v4"
    assert checklist["obligations"][0]["evidence_ids"] == ["E1"]
    assert checklist["obligations"][0]["clause_ids"] == ["c001"]
    assert "key_elements" not in checklist["obligations"][0]
    assert checklist["acknowledged_context"] == [
        "完成后检查尘盒。",
        "不要在积水中运行。",
    ]
    assert checklist_model_projection(checklist) == {
        "schema_version": "approved-obligation-checklist-v2",
        "obligations": [
            {
                "obligation_id": "o1",
                "description": "说明怎样启动指定区域的清洁",
                "evidence_ids": ["E1"],
            }
        ],
    }


def test_v4_checklist_rejects_missing_or_conflicting_partition() -> None:
    missing = _raw_checklist()
    missing["ignored_clause_ids"].pop()
    with pytest.raises(TwoStepError, match="two_step_checklist_partition_incomplete"):
        validate_step1_result({"evidence": EVIDENCE}, missing)

    overlap = _raw_checklist()
    overlap["ignored_clause_ids"].append("c001")
    with pytest.raises(TwoStepError, match="two_step_checklist_partition_invalid"):
        validate_step1_result({"evidence": EVIDENCE}, overlap)


@pytest.mark.parametrize(
    ("mutator", "code"),
    [
        (
            lambda value: value.update({"schema_version": "wrong"}),
            "two_step_checklist_identity_invalid",
        ),
        (
            lambda value: value["obligations"][0].update({"clause_ids": ["missing"]}),
            "two_step_checklist_clause_ids_invalid",
        ),
        (
            lambda value: value["obligations"][0].update(
                {"key_elements": ["局部清扫键"]}
            ),
            "two_step_checklist_obligation_shape_invalid",
        ),
    ],
)
def test_v4_checklist_reports_privacy_safe_subcontract_codes(
    mutator,
    code: str,
) -> None:
    value = _raw_checklist()
    mutator(value)

    with pytest.raises(TwoStepError, match=code):
        validate_step1_result({"evidence": EVIDENCE}, value)


@pytest.mark.parametrize(
    ("obligations", "code"),
    [
        ({}, "two_step_checklist_obligations_type_invalid"),
        ([], "two_step_checklist_obligation_count_empty"),
        (
            [_raw_checklist()["obligations"][0]] * 9,
            "two_step_checklist_obligation_count_exceeded",
        ),
    ],
)
def test_v4_checklist_reports_safe_obligation_count_codes(
    obligations,
    code: str,
) -> None:
    value = _raw_checklist()
    value["obligations"] = obligations

    with pytest.raises(TwoStepError, match=code):
        validate_step1_result({"evidence": EVIDENCE}, value)


def test_v4_checklist_accepts_semantic_description_without_source_substring() -> None:
    value = {
        "schema_version": "obligation-checklist-v4",
        "obligations": [
            {
                "obligation_id": "o1",
                "description": "先启动指定区域的清洁，再确认收集盒状态",
                "clause_ids": ["c001", "c002"],
            }
        ],
        "ignored_clause_ids": ["c003"],
    }

    checked = validate_step1_result({"evidence": EVIDENCE}, value)
    assert checked["obligations"][0]["evidence_ids"] == ["E1"]
    assert checked["obligations"][0]["description"] == (
        "先启动指定区域的清洁，再确认收集盒状态"
    )


def test_qa_v4_derives_plan_used_evidence_and_claim_ids() -> None:
    normalized = validate_result(
        {"case_id": "qa-1", "evidence": EVIDENCE},
        _checklist(),
        _qa_result(),
    )

    assert normalized["obligation_plan"] == [
        {
            "obligation_id": "o1",
            "description": "说明怎样启动指定区域的清洁",
            "evidence_ids": ["E1"],
        }
    ]
    assert normalized["used_evidence_ids"] == ["E1"]
    assert normalized["content"]["answer"]["claim_ids"] == ["c1"]


def test_qa_v4_accepts_declared_customer_paraphrase_and_rejects_forged_span() -> None:
    paraphrased = _qa_result()
    paraphrased["content"]["answer"]["text"] = "可以通过按键启动局部区域清洁。"
    paraphrased["content"]["claims"][0]["customer_visible_span_text"] = (
        "按键启动局部区域清洁"
    )
    normalized = validate_result(
        {"case_id": "qa-1", "evidence": EVIDENCE},
        _checklist(),
        paraphrased,
    )
    assert normalized["content"]["claims"][0]["customer_visible_span_text"] == (
        "按键启动局部区域清洁"
    )

    forged = _qa_result()
    forged["content"]["claims"][0]["customer_visible_span_text"] = "正文中不存在"
    with pytest.raises(CandidateV4Error, match="top10_v7_customer_span_invalid"):
        validate_result({"evidence": EVIDENCE}, _checklist(), forged)


def test_qa_v4_rejects_redundant_or_wrong_source_bindings() -> None:
    redundant = _qa_result()
    redundant["obligation_plan"] = []
    with pytest.raises(CandidateV4Error, match="top10_v6_result_shape_invalid"):
        validate_result({"evidence": EVIDENCE}, _checklist(), redundant)

    wrong_source = _qa_result()
    wrong_source["content"]["claims"][0]["exact_span_text"] = "不要在积水中运行。"
    wrong_source["content"]["claims"][0]["evidence_ids"] = ["E2"]
    with pytest.raises(CandidateV4Error, match="top10_v6_obligation_binding_invalid"):
        validate_result({"evidence": EVIDENCE}, _checklist(), wrong_source)


def test_ticket_v3_accepts_declared_customer_paraphrase_and_derives_plan() -> None:
    paraphrased = _ticket_result()
    paraphrased["content"]["draft_reply"] = "可以通过按键启动局部区域清洁。"
    paraphrased["content"]["claims"][0]["customer_visible_span_text"] = (
        "按键启动局部区域清洁"
    )
    normalized = validate_ticket_result_v2(
        {"case_id": "ticket-1", "evidence": EVIDENCE},
        _checklist(),
        paraphrased,
    )
    assert normalized["obligation_plan"][0]["obligation_id"] == "o1"
    assert normalized["used_evidence_ids"] == ["E1"]
    assert normalized["content"]["claims"][0]["customer_visible_span_text"] == (
        "按键启动局部区域清洁"
    )

    forged = _ticket_result()
    forged["content"]["claims"][0]["customer_visible_span_text"] = "正文中不存在"
    with pytest.raises(TicketContractError, match="ticket_v3_customer_span_invalid"):
        validate_ticket_result_v2(
            {"evidence": EVIDENCE},
            _checklist(),
            forged,
        )


def test_ticket_v3_rejects_wrong_source_binding() -> None:

    wrong_source = copy.deepcopy(_ticket_result())
    wrong_source["content"]["claims"][0]["exact_span_text"] = "不要在积水中运行。"
    wrong_source["content"]["claims"][0]["evidence_ids"] = ["E2"]
    with pytest.raises(TicketContractError, match="ticket_v2_obligation_binding_invalid"):
        validate_ticket_result_v2(
            {"evidence": EVIDENCE},
            _checklist(),
            wrong_source,
        )


def test_failure_taxonomy_is_stable_and_content_free() -> None:
    classification = classify_generation_failure(
        "enumeration_execution_failure:provider_response_envelope_invalid"
    )
    assert classification == {
        "schema_version": "generation-failure-classification-v1",
        "phase": "enumeration_execution",
        "family": "provider_response_envelope",
        "code": "provider_response_envelope_invalid",
    }
    assert classify_generation_failure(
        "enumeration_execution_failure:provider_response_finish_reason_length"
    )["family"] == "provider_response_envelope"
    assert classify_generation_failure(
        "enumeration_contract_failure:"
        "two_step_checklist_obligation_count_exceeded"
    )["family"] == "checklist_shape"
    assert classify_generation_failure(
        "generation_contract_failure:top10_v7_customer_span_invalid"
    )["family"] == "semantic_coverage"
    assert classify_generation_failure(
        "generation_contract_failure:ticket_v3_customer_span_invalid"
    )["family"] == "semantic_coverage"

    summary = summarize_generation_failures(
        [
            {"handoff_reason": None},
            {
                "handoff_reason":
                    "enumeration_contract_failure:two_step_checklist_partition_incomplete"
            },
            {"handoff_reason": "completeness_gate_failed"},
            {"handoff_reason": "safety_risk"},
        ]
    )
    assert summary["packages"] == 4
    assert summary["failures"] == 2
    assert summary["families"] == {
        "checklist_partition": 1,
        "completeness": 1,
    }

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
        "schema_version": "obligation-checklist-v3",
        "obligations": [
            {
                "obligation_id": "o1",
                "description": "说明如何开始局部清扫",
                "clause_ids": [inventory[0]["clause_id"]],
                "key_elements": ["局部清扫键"],
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
        "schema_version": "retrieved-top10-qa-result-v3",
        "task_type": "qa",
        "content": {
            "kind": "qa_answer",
            "answer": {"text": "请先按局部清扫键。"},
            "claims": [
                {
                    "claim_id": "c1",
                    "exact_span_text": "先按局部清扫键。",
                    "evidence_ids": ["E1"],
                    "obligation_ids": ["o1"],
                }
            ],
            "insufficient_evidence": False,
        },
    }


def _ticket_result() -> dict:
    return {
        "schema_version": "ticket-proposal-result-v2",
        "task_type": "ticket",
        "content": {
            "kind": "ticket_proposal",
            "action_steps": ["请客户先按局部清扫键。"],
            "draft_reply": "请先按局部清扫键。",
            "claims": [
                {
                    "claim_id": "c1",
                    "exact_span_text": "先按局部清扫键。",
                    "evidence_ids": ["E1"],
                    "obligation_ids": ["o1"],
                }
            ],
            "insufficient_evidence": False,
        },
    }


def test_v3_checklist_uses_clause_ids_and_derives_mechanical_fields() -> None:
    checklist = _checklist()

    assert checklist["obligations"][0]["evidence_ids"] == ["E1"]
    assert checklist["obligations"][0]["clause_ids"] == ["c001"]
    assert checklist["acknowledged_context"] == [
        "完成后检查尘盒。",
        "不要在积水中运行。",
    ]
    assert checklist_model_projection(checklist) == {
        "schema_version": "approved-obligation-checklist-v1",
        "obligations": [
            {
                "obligation_id": "o1",
                "description": "说明如何开始局部清扫",
                "evidence_ids": ["E1"],
                "key_elements": ["局部清扫键"],
            }
        ],
    }


def test_v3_checklist_rejects_missing_or_conflicting_partition() -> None:
    missing = _raw_checklist()
    missing["ignored_clause_ids"].pop()
    with pytest.raises(TwoStepError, match="two_step_checklist_partition_incomplete"):
        validate_step1_result({"evidence": EVIDENCE}, missing)

    overlap = _raw_checklist()
    overlap["ignored_clause_ids"].append("c001")
    with pytest.raises(TwoStepError, match="two_step_checklist_partition_invalid"):
        validate_step1_result({"evidence": EVIDENCE}, overlap)


def test_v3_checklist_rejects_key_element_crossing_clause_boundary() -> None:
    value = {
        "schema_version": "obligation-checklist-v3",
        "obligations": [
            {
                "obligation_id": "o1",
                "description": "覆盖两条子句",
                "clause_ids": ["c001", "c002"],
                "key_elements": ["先按局部清扫键。\n完成后检查尘盒。"],
            }
        ],
        "ignored_clause_ids": ["c003"],
    }

    with pytest.raises(TwoStepError, match="two_step_checklist_invalid"):
        validate_step1_result({"evidence": EVIDENCE}, value)


def test_qa_v3_derives_plan_used_evidence_and_claim_ids() -> None:
    normalized = validate_result(
        {"case_id": "qa-1", "evidence": EVIDENCE},
        _checklist(),
        _qa_result(),
    )

    assert normalized["obligation_plan"] == [
        {
            "obligation_id": "o1",
            "description": "说明如何开始局部清扫",
            "evidence_ids": ["E1"],
        }
    ]
    assert normalized["used_evidence_ids"] == ["E1"]
    assert normalized["content"]["answer"]["claim_ids"] == ["c1"]


def test_qa_v3_rejects_redundant_or_wrong_source_bindings() -> None:
    redundant = _qa_result()
    redundant["obligation_plan"] = []
    with pytest.raises(CandidateV4Error, match="top10_v6_result_shape_invalid"):
        validate_result({"evidence": EVIDENCE}, _checklist(), redundant)

    wrong_source = _qa_result()
    wrong_source["content"]["claims"][0]["exact_span_text"] = "不要在积水中运行。"
    wrong_source["content"]["claims"][0]["evidence_ids"] = ["E2"]
    with pytest.raises(CandidateV4Error, match="top10_v6_obligation_binding_invalid"):
        validate_result({"evidence": EVIDENCE}, _checklist(), wrong_source)


def test_ticket_v2_derives_plan_and_rejects_wrong_source_binding() -> None:
    normalized = validate_ticket_result_v2(
        {"case_id": "ticket-1", "evidence": EVIDENCE},
        _checklist(),
        _ticket_result(),
    )
    assert normalized["obligation_plan"][0]["obligation_id"] == "o1"
    assert normalized["used_evidence_ids"] == ["E1"]

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

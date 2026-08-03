from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from traceable_support.generation.checklist import (
    CHECKLIST_SYSTEM_PROMPT,
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
    ticket_completeness_gate,
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

GENERATION_SHAPE_FIXTURE = json.loads(
    (
        Path(__file__).resolve().parents[2]
        / "evals"
        / "fixtures"
        / "generation-shape-equivalent-v1.json"
    ).read_text(encoding="utf-8")
)
GENERATION_SHAPE_RECEIPT = json.loads(
    (
        Path(__file__).resolve().parents[2]
        / "evals"
        / "generation-shape-diagnostics-v1.json"
    ).read_text(encoding="utf-8")
)


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
    assert checklist["obligations"][0]["approved_source_spans"] == [
        {
            "clause_id": "c001",
            "evidence_id": "E1",
            "exact_span_text": "先按局部清扫键。",
        }
    ]
    assert "key_elements" not in checklist["obligations"][0]
    assert checklist["acknowledged_context"] == [
        "完成后检查尘盒。",
        "不要在积水中运行。",
    ]
    assert checklist_model_projection(checklist) == {
        "schema_version": "approved-obligation-checklist-v3",
        "obligations": [
            {
                "obligation_id": "o1",
                "description": "说明怎样启动指定区域的清洁",
                "evidence_ids": ["E1"],
                "approved_source_spans": [
                    {
                        "clause_id": "c001",
                        "evidence_id": "E1",
                        "exact_span_text": "先按局部清扫键。",
                    }
                ],
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


def test_v4_prompt_and_host_share_the_eight_obligation_limit() -> None:
    assert "义务总数必须为1到8项" in CHECKLIST_SYSTEM_PROMPT


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


@pytest.mark.parametrize(
    "shape_case",
    GENERATION_SHAPE_FIXTURE["cases"],
    ids=lambda shape_case: shape_case["component"],
)
def test_qa_generation_shape_fixture_has_specific_safe_code(shape_case) -> None:
    context = GENERATION_SHAPE_FIXTURE["context"]
    with pytest.raises(CandidateV4Error) as caught:
        validate_result(
            {"case_id": context["case_id"], "evidence": context["evidence"]},
            context["checklist"],
            copy.deepcopy(shape_case["response"]),
        )
    assert caught.value.code == shape_case["expected_code"]
    classification = classify_generation_failure(
        f"generation_contract_failure:{caught.value.code}"
    )
    assert classification["phase"] == "generation_contract"
    assert classification["family"] == "generation_shape"
    assert shape_case["legacy_code"] == (
        GENERATION_SHAPE_FIXTURE["target"]["legacy_code"]
    )


def test_generation_shape_receipt_is_bounded_and_matches_fixture() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "evals"
        / "fixtures"
        / "generation-shape-equivalent-v1.json"
    )
    fixture_sha256 = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
    receipt = GENERATION_SHAPE_RECEIPT
    fixture_cases = GENERATION_SHAPE_FIXTURE["cases"]

    assert receipt["schema_version"] == "generation-shape-diagnostics-v1"
    assert receipt["baseline"]["fixture_sha256"] == fixture_sha256
    assert receipt["historical_localization"] == {
        "phase": "generation_contract",
        "family": "generation_shape",
        "second_provider_call_succeeded": True,
        "checklist_passed": True,
        "failed_before_claim_and_obligation_binding": True,
        "provider_response_retained": False,
        "exact_historical_subcondition_known": False,
    }
    assert receipt["offline_replay"]["provider_calls"] == 0
    assert receipt["offline_replay"]["legacy_cases_reproduced"] == 4
    assert receipt["offline_replay"]["refined_cases_passed"] == 4
    assert [case["case_id"] for case in receipt["offline_replay"]["cases"]] == [
        case["case_id"] for case in fixture_cases
    ]
    assert [case["legacy_result"] for case in receipt["offline_replay"]["cases"]] == [
        case["legacy_code"] for case in fixture_cases
    ]
    assert [case["refined_result"] for case in receipt["offline_replay"]["cases"]] == [
        case["expected_code"] for case in fixture_cases
    ]
    assert {case["outcome"] for case in receipt["offline_replay"]["cases"]} == {
        "handoff"
    }
    assert receipt["boundary"] == {
        "contains_private_stage12_content": False,
        "contains_provider_response": False,
        "contract_loosened": False,
        "stage12_rerun": False,
        "provider_calls": 0,
        "valid_candidate_produced": False,
    }


def test_qa_v4_tolerates_wording_drift_and_rejects_unknown_evidence_id() -> None:
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

    # 措辞漂移但绑定有效：不再逐字校验 customer_visible_span_text 与正文
    drifted = _qa_result()
    drifted["content"]["claims"][0]["customer_visible_span_text"] = "正文中不存在"
    normalized = validate_result(
        {"case_id": "qa-1", "evidence": EVIDENCE},
        _checklist(),
        drifted,
    )
    assert normalized["content"]["claims"][0]["evidence_ids"] == ["E1"]

    # 绑定存在性底线：引用不存在的证据 ID 仍然拒绝
    forged = _qa_result()
    forged["content"]["claims"][0]["evidence_ids"] = ["E9"]
    with pytest.raises(CandidateV4Error, match="top10_v6_claim_invalid"):
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


def test_qa_v4_accepts_binding_without_verbatim_clause_match() -> None:
    # exact_span_text 引用了被忽略子句，但 evidence/obligation 绑定均真实有效：
    # 新语义只做绑定存在性硬校验，不做逐字包含校验，因此通过
    ignored_clause = _qa_result()
    ignored_clause["content"]["answer"]["text"] = "完成后请检查尘盒。"
    ignored_clause["content"]["claims"][0]["exact_span_text"] = (
        "完成后检查尘盒。"
    )
    ignored_clause["content"]["claims"][0]["customer_visible_span_text"] = (
        "检查尘盒"
    )

    normalized = validate_result(
        {"evidence": EVIDENCE}, _checklist(), ignored_clause
    )
    assert normalized["content"]["claims"][0]["exact_span_text"] == (
        "完成后检查尘盒。"
    )

    # 绑定越过义务批准来源范围仍然拒绝
    cross_bound = _qa_result()
    cross_bound["content"]["claims"][0]["evidence_ids"] = ["E2"]
    with pytest.raises(CandidateV4Error, match="top10_v6_obligation_binding_invalid"):
        validate_result({"evidence": EVIDENCE}, _checklist(), cross_bound)


def test_completeness_gate_uses_binding_existence_not_verbatim_spans() -> None:
    from traceable_support.generation.checklist import completeness_gate

    checklist = _checklist()
    result = validate_result(
        {"case_id": "qa-1", "evidence": EVIDENCE}, checklist, _qa_result()
    )
    # 客户片段措辞漂移不影响过门：只要求义务有绑定的 claim
    result["content"]["claims"][0]["customer_visible_span_text"] = "措辞漂移"
    gate = completeness_gate(checklist, result)
    assert gate["pass"] is True
    assert gate["obligations"][0]["customer_visible_claim_ids"] == ["c1"]

    # 义务没有任何 claim 绑定时 fail closed
    result["content"]["claims"][0]["obligation_ids"] = []
    gate = completeness_gate(checklist, result)
    assert gate["pass"] is False
    assert gate["uncovered_obligation_ids"] == ["o1"]


def test_ticket_v3_tolerates_wording_drift_and_rejects_unknown_evidence_id() -> None:
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

    # 措辞漂移但绑定有效：不再逐字校验 customer_visible_span_text 与草稿
    drifted = _ticket_result()
    drifted["content"]["claims"][0]["customer_visible_span_text"] = "正文中不存在"
    normalized = validate_ticket_result_v2(
        {"evidence": EVIDENCE},
        _checklist(),
        drifted,
    )
    assert normalized["content"]["claims"][0]["evidence_ids"] == ["E1"]

    # 绑定存在性底线：引用不存在的证据 ID 仍然拒绝
    forged = _ticket_result()
    forged["content"]["claims"][0]["evidence_ids"] = ["E9"]
    with pytest.raises(TicketContractError, match="ticket_v2_claim_invalid"):
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


def test_ticket_v3_accepts_binding_without_verbatim_clause_match() -> None:
    # exact_span_text 引用了被忽略子句，但 evidence/obligation 绑定均真实有效：
    # 新语义只做绑定存在性硬校验，不做逐字包含校验，因此通过
    ignored_clause = copy.deepcopy(_ticket_result())
    ignored_clause["content"]["draft_reply"] = "完成后请检查尘盒。"
    ignored_clause["content"]["claims"][0]["exact_span_text"] = (
        "完成后检查尘盒。"
    )
    ignored_clause["content"]["claims"][0]["customer_visible_span_text"] = (
        "检查尘盒"
    )

    normalized = validate_ticket_result_v2(
        {"evidence": EVIDENCE},
        _checklist(),
        ignored_clause,
    )
    assert normalized["content"]["claims"][0]["exact_span_text"] == (
        "完成后检查尘盒。"
    )


def test_ticket_completeness_gate_uses_binding_existence_not_verbatim_spans() -> None:
    checklist = {"obligations": [{"obligation_id": "o1", "description": "d",
                                  "evidence_ids": ["E1"]}]}
    # 客户片段措辞漂移（不逐字位于草稿）不影响过门：只要求义务有绑定的 claim
    drifted = {"content": {
        "draft_reply": "这种地毯需要避开。",
        "action_steps": [],
        "claims": [{
            "claim_id": "c1",
            "customer_visible_span_text": "草稿中不存在的措辞",
            "obligation_ids": ["o1"],
        }],
    }}
    assert ticket_completeness_gate(checklist, drifted)["pass"] is True
    # 义务没有任何 claim 绑定时 fail closed
    unbound = {"content": {
        "draft_reply": "这种地毯需要避开。",
        "action_steps": [],
        "claims": [{
            "claim_id": "c1",
            "customer_visible_span_text": "需要避开",
            "obligation_ids": [],
        }],
    }}
    gate = ticket_completeness_gate(checklist, unbound)
    assert gate["pass"] is False
    assert gate["uncovered_obligation_ids"] == ["o1"]


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
    assert classify_generation_failure(
        "generation_contract_failure:top10_v8_clause_binding_invalid"
    )["family"] == "obligation_binding"
    assert classify_generation_failure(
        "generation_contract_failure:ticket_v4_clause_binding_invalid"
    )["family"] == "obligation_binding"
    for code in (
        "top10_v6_content_shape_invalid",
        "top10_v6_content_identity_invalid",
        "top10_v6_answer_shape_invalid",
        "top10_v6_claim_count_invalid",
    ):
        classification = classify_generation_failure(
            f"generation_contract_failure:{code}"
        )
        assert classification["phase"] == "generation_contract"
        assert classification["family"] == "generation_shape"
        assert classification["code"] == code

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

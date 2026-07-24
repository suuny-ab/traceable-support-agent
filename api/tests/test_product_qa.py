import json
import sqlite3

import pytest

from traceable_support.product.qa import (
    LlmQaError,
    QaSessionBudget,
    STEP1_MAX_OUTPUT_TOKENS,
    STEP2_MAX_OUTPUT_TOKENS,
    create_qa_tables,
    list_qa_runs,
    load_qa_run,
    record_qa_decision,
    run_qa,
    save_qa_run,
)
from traceable_support.product.runner import DefaultProductRunner
from traceable_support.product.types import RunInput
from traceable_support.provider.response import json_response
from traceable_support.provider.deepseek import OfflineInjectedTransport

USAGE = {
    "prompt_tokens": 100,
    "completion_tokens": 100,
    "total_tokens": 200,
    "prompt_cache_hit_tokens": 0,
    "prompt_cache_miss_tokens": 100,
}


def _fixture(question: str, *, valid: bool = True, gate_pass: bool = True) -> OfflineInjectedTransport:
    from traceable_support.retrieval.hybrid import BusinessRetrievalRequest, ModelAwareRrfPipeline
    from traceable_support.generation.checklist import build_clause_inventory

    result = ModelAwareRrfPipeline(unit_strategy="native_section", delivery_k=5).retrieve(
        BusinessRetrievalRequest(
            query_text=question, known_product_model="CZ-R1", channel="qa",
            candidate_pool_limit=10, delivery_limit=5,
        )
    )
    evidence = [
        {"evidence_id": candidate.unit.unit_id, "text": candidate.unit.text}
        for candidate in result.candidate_hits
    ]
    inventory = build_clause_inventory(evidence)
    selected = inventory[0]
    evidence_id = selected["evidence_id"]
    text = evidence[0]["text"]
    if valid:
        first = selected["text"] if len(selected["text"]) <= 60 else selected["text"][:60]
        checklist = {
            "schema_version": "obligation-checklist-v4",
            "obligations": [
                {"obligation_id": "o1", "description": "义务",
                 "clause_ids": [selected["clause_id"]]}
            ],
            "ignored_clause_ids": [
                entry["clause_id"] for entry in inventory[1:]
            ],
        }
        answer_text = f"回答。{first}" if gate_pass else "回答。不含要素"
        result_obj = {
            "schema_version": "retrieved-top10-qa-result-v4",
            "task_type": "qa",
            "content": {
                "kind": "qa_answer",
                "answer": {"text": answer_text},
                "claims": [
                    {"claim_id": "c1", "exact_span_text": text,
                     "customer_visible_span_text": first if gate_pass else "不存在的客户片段",
                     "evidence_ids": [evidence_id], "obligation_ids": ["o1"]}
                ],
                "insufficient_evidence": False,
            },
        }
        return OfflineInjectedTransport([
            {"kind": "response", "status_code": 200,
             "body": json_response(checklist, usage=USAGE, response_id="fx-1")},
            {"kind": "response", "status_code": 200,
             "body": json_response(result_obj, usage=USAGE, response_id="fx-2")},
        ])
    return OfflineInjectedTransport([
        {"kind": "response", "status_code": 200,
         "body": json_response({"schema_version": "wrong"}, usage=USAGE, response_id="fx-1")},
    ])


def test_run_qa_candidate_package_and_persistence_roundtrip():
    transport = _fixture("CZ-R1 怎么开始局部清扫？")
    package = run_qa(
        question="CZ-R1 怎么开始局部清扫？",
        product_model="CZ-R1",
        transport=transport,
        mode="offline_injected",
        run_id="test-run-1",
        worst_cost_limit_cny_nanos=500_000_000,
    )
    assert package["outcome"] == "candidate"
    assert package["checklist"]["schema_version"] == "obligation-checklist-v4"
    assert package["gates"]["completeness_gate"]["pass"] is True
    assert package["answer"]["obligation_plan"][0]["obligation_id"] == "o1"
    assert package["answer"]["used_evidence_ids"] == [
        package["answer"]["content"]["claims"][0]["evidence_ids"][0]
    ]
    assert package["answer"]["content"]["answer"]["claim_ids"] == ["c1"]
    assert len(package["evidence"]) == 10
    assert len(package["usage"]) == 2
    observations = transport.safe_observations()
    assert STEP1_MAX_OUTPUT_TOKENS == 16384
    assert package["worst_cost_cny_nanos"] == (
        sum(observation["request_bytes"] * 3000 for observation in observations)
        + (STEP1_MAX_OUTPUT_TOKENS + STEP2_MAX_OUTPUT_TOKENS) * 6000
    )

    connection = sqlite3.connect(":memory:")
    create_qa_tables(connection)
    digest = save_qa_run(connection, package)
    assert len(digest) == 64
    loaded = load_qa_run(connection, "test-run-1")
    assert loaded["package"] == package
    record_qa_decision(connection, run_id="test-run-1", decision="approve", decision_text=None)
    assert load_qa_run(connection, "test-run-1")["decision"] == "approve"
    with pytest.raises(LlmQaError, match="product_qa_decision_already_recorded"):
        record_qa_decision(connection, run_id="test-run-1", decision="reject", decision_text=None)
    runs = list_qa_runs(connection)
    assert runs[0]["run_id"] == "test-run-1"


def test_run_qa_rejects_forged_customer_visible_span():
    package = run_qa(
        question="CZ-R1 怎么开始局部清扫？",
        product_model="CZ-R1",
        transport=_fixture("CZ-R1 怎么开始局部清扫？", gate_pass=False),
        mode="offline_injected",
        run_id="test-run-2",
        worst_cost_limit_cny_nanos=500_000_000,
    )
    assert package["outcome"] == "handoff"
    assert package["handoff_reason"] == (
        "generation_contract_failure:top10_v7_customer_span_invalid"
    )
    assert package["failure_classification"]["family"] == "semantic_coverage"
    assert package["answer"] is None

    connection = sqlite3.connect(":memory:")
    create_qa_tables(connection)
    save_qa_run(connection, package)
    with pytest.raises(LlmQaError, match="product_qa_decision_requires_candidate"):
        record_qa_decision(connection, run_id="test-run-2", decision="approve", decision_text=None)


def test_run_qa_enumeration_contract_failure_handoffs_without_answer():
    package = run_qa(
        question="CZ-R1 怎么开始局部清扫？",
        product_model="CZ-R1",
        transport=_fixture("CZ-R1 怎么开始局部清扫？", valid=False),
        mode="offline_injected",
        run_id="test-run-3",
        worst_cost_limit_cny_nanos=500_000_000,
    )
    assert package["outcome"] == "handoff"
    assert package["handoff_reason"].startswith("enumeration_contract_failure")
    assert package["failure_classification"]["phase"] == "enumeration_contract"
    assert package["answer"] is None


def test_session_budget_fail_closed():
    budget = QaSessionBudget(max_runs=2, max_worst_cost_cny_nanos=100)
    budget.check(runs_completed=0, worst_cost_accumulated=0)
    with pytest.raises(LlmQaError, match="product_qa_session_run_limit_exceeded"):
        budget.check(runs_completed=2, worst_cost_accumulated=0)
    with pytest.raises(LlmQaError, match="product_qa_session_budget_exceeded"):
        budget.check(runs_completed=0, worst_cost_accumulated=100)


def test_run_qa_rejects_invalid_inputs():
    with pytest.raises(LlmQaError, match="product_qa_question_invalid"):
        run_qa(question="  ", product_model="CZ-R1", transport=None,
               mode="offline_injected", run_id="x", worst_cost_limit_cny_nanos=1)
    with pytest.raises(LlmQaError, match="product_qa_model_invalid"):
        run_qa(question="q", product_model="CZ-R3", transport=None,
               mode="offline_injected", run_id="x", worst_cost_limit_cny_nanos=1)


def test_product_runner_uses_the_stable_execute_contract():
    question = "CZ-R1 怎么开始局部清扫？"
    runner = DefaultProductRunner(
        transport_factory=lambda: _fixture(question),
        transport_mode="offline_injected",
        dependencies_ready=True,
    )
    stages = []
    execution = runner.execute(
        RunInput(
            run_id="runner-contract-1",
            task_type="qa",
            text=question,
            product_model="CZ-R1",
            reserved_cny_nanos=500_000_000,
        ),
        lambda stage, status: stages.append((stage, status)),
    )
    assert execution.package["outcome"] == "candidate"
    assert execution.provider_call_count == 2
    assert stages[0] == ("retrieval", "started")


def test_product_runner_fails_closed_until_explicitly_ready():
    runner = DefaultProductRunner(
        transport_factory=lambda: None,
        transport_mode="offline_injected",
        dependencies_ready=False,
    )
    with pytest.raises(RuntimeError, match="product_runner_not_ready"):
        runner.execute(
            RunInput("x", "qa", "CZ-R1 怎么清扫？", "CZ-R1", 500_000_000),
            lambda stage, status: None,
        )


def test_contradicted_context_declaration_is_corrected_not_handed_off():
    from traceable_support.product.qa import _correct_context_declarations

    package = {
        "acknowledged_context": ["滤网可轻拍除尘", "无关句子"],
        "context_corrections": [],
        "answer": {"content": {"answer": {"text": "取出尘盒。滤网可轻拍除尘，但不得用未完全干燥的滤网装回主机。"}}},
    }
    _correct_context_declarations(package)
    assert package["acknowledged_context"] == ["无关句子"]
    assert package["context_corrections"] == ["滤网可轻拍除尘"]
    # 无矛盾时不改动
    package2 = {
        "acknowledged_context": ["完全无关的句子"],
        "context_corrections": [],
        "answer": {"content": {"answer": {"text": "回答正文。"}}},
    }
    _correct_context_declarations(package2)
    assert package2["acknowledged_context"] == ["完全无关的句子"]
    assert package2["context_corrections"] == []

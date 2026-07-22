import json
import sqlite3

import pytest

from traceable_support.product.ticket import (
    create_ticket_tables,
    efficiency_stats,
    load_ticket_run,
    record_ticket_decision,
    run_ticket,
    save_ticket_run,
    _correct_ticket_context,
)
from traceable_support.generation.ticket_contract import (
    TicketContractError,
    ticket_completeness_gate,
    validate_ticket_result,
)
from traceable_support.provider.response import json_response
from traceable_support.provider.deepseek import OfflineInjectedTransport

USAGE = {
    "prompt_tokens": 100,
    "completion_tokens": 100,
    "total_tokens": 200,
    "prompt_cache_hit_tokens": 0,
    "prompt_cache_miss_tokens": 100,
}
QUESTION = "CZ-R1 怎么开始局部清扫？"
TICKET = {
    "ticket_id": "T-001",
    "product_model": "CZ-R1",
    "issue_description": QUESTION,
    "category": "使用咨询",
    "priority": "P2-一般",
}


def _evidence():
    from traceable_support.retrieval.hybrid import BusinessRetrievalRequest, ModelAwareRrfPipeline

    result = ModelAwareRrfPipeline(unit_strategy="native_section", delivery_k=5).retrieve(
        BusinessRetrievalRequest(
            query_text=QUESTION, known_product_model="CZ-R1", channel="qa",
            candidate_pool_limit=10, delivery_limit=5,
        )
    )
    hit = result.candidate_hits[0].unit
    return {"evidence_id": hit.unit_id, "text": hit.text}


def _fixture(*, valid=True, gate_pass=True):
    ev = _evidence()
    from traceable_support.generation.checklist import _clauses
    clauses = _clauses(ev["text"])
    first = clauses[0] if len(clauses[0]) <= 60 else clauses[0][:60]
    checklist = {
        "schema_version": "obligation-checklist-v2",
        "obligations": [
            {"obligation_id": "o1", "description": "义务",
             "evidence_ids": [ev["evidence_id"]], "key_elements": [first]}
        ],
        "acknowledged_context": clauses[1:],
    }
    if not valid:
        return OfflineInjectedTransport([
            {"kind": "response", "status_code": 200,
             "body": json_response({"schema_version": "wrong"}, usage=USAGE, response_id="fx-1")},
        ])
    proposal = {
        "schema_version": "ticket-proposal-result-v1",
        "task_type": "ticket",
        "obligation_plan": [
            {"obligation_id": "o1", "description": "义务", "evidence_ids": [ev["evidence_id"]]}
        ],
        "used_evidence_ids": [ev["evidence_id"]],
        "content": {
            "kind": "ticket_proposal",
            "action_steps": ["步骤一"],
            "draft_reply": f"客户回复。{first}" if gate_pass else "客户回复。",
            "claims": [
                {"claim_id": "c1", "exact_span_text": ev["text"],
                 "evidence_ids": [ev["evidence_id"]], "obligation_ids": ["o1"]}
            ],
            "insufficient_evidence": False,
        },
    }
    return OfflineInjectedTransport([
        {"kind": "response", "status_code": 200,
         "body": json_response(checklist, usage=USAGE, response_id="fx-1")},
        {"kind": "response", "status_code": 200,
         "body": json_response(proposal, usage=USAGE, response_id="fx-2")},
    ])


def test_ticket_contract_accepts_valid_and_rejects_known_failures():
    ev = _evidence()
    item = {"case_id": "t", "evidence": [{"evidence_id": ev["evidence_id"], "text": ev["text"]}]}
    valid = {
        "schema_version": "ticket-proposal-result-v1",
        "task_type": "ticket",
        "obligation_plan": [{"obligation_id": "o1", "description": "义务", "evidence_ids": [ev["evidence_id"]]}],
        "used_evidence_ids": [ev["evidence_id"]],
        "content": {
            "kind": "ticket_proposal",
            "action_steps": ["步骤一"],
            "draft_reply": "客户回复。",
            "claims": [{"claim_id": "c1", "exact_span_text": ev["text"],
                        "evidence_ids": [ev["evidence_id"]], "obligation_ids": ["o1"]}],
            "insufficient_evidence": False,
        },
    }
    assert validate_ticket_result(item, valid) == valid

    import copy
    wrong_type = copy.deepcopy(valid)
    wrong_type["task_type"] = "qa"
    with pytest.raises(TicketContractError, match="ticket_result_identity_invalid"):
        validate_ticket_result(item, wrong_type)

    internal = copy.deepcopy(valid)
    internal["content"]["draft_reply"] = "自动生成内容仅为草稿"
    with pytest.raises(TicketContractError, match="ticket_internal_language_invalid"):
        validate_ticket_result(item, internal)

    no_plan_link = copy.deepcopy(valid)
    del no_plan_link["content"]["claims"][0]["obligation_ids"]
    with pytest.raises(TicketContractError, match="ticket_claim_invalid"):
        validate_ticket_result(item, no_plan_link)


def test_ticket_gate_detects_missing_key_elements():
    checklist = {"obligations": [{"obligation_id": "o1", "description": "d",
                                  "evidence_ids": ["E1"], "key_elements": ["边缘松散", "禁区"]}]}
    passing = {"content": {"draft_reply": "长毛地毯或边缘松散的地毯仍应设置为禁区。", "action_steps": []}}
    failing = {"content": {"draft_reply": "长毛地毯仍应设置为禁区。", "action_steps": []}}
    assert ticket_completeness_gate(checklist, passing)["pass"] is True
    assert ticket_completeness_gate(checklist, failing)["pass"] is False


def test_run_ticket_candidate_and_persistence_roundtrip():
    package = run_ticket(
        ticket=TICKET,
        transport=_fixture(),
        mode="offline_injected",
        run_id="ticket-run-1",
        worst_cost_limit_cny_nanos=500_000_000,
    )
    assert package["outcome"] == "candidate"
    assert package["proposal"]["content"]["kind"] == "ticket_proposal"
    assert package["gates"]["completeness_gate"]["pass"] is True
    assert package["ticket_id"] == "T-001"

    connection = sqlite3.connect(":memory:")
    create_ticket_tables(connection)
    digest = save_ticket_run(connection, package)
    assert len(digest) == 64
    loaded = load_ticket_run(connection, "ticket-run-1")
    assert loaded["package"]["ticket_id"] == "T-001"
    record_ticket_decision(connection, run_id="ticket-run-1", decision="edit", decision_text="人工修改后的回复")
    assert load_ticket_run(connection, "ticket-run-1")["decision_text"] == "人工修改后的回复"


def test_run_ticket_handoff_on_contract_failure_and_no_decision():
    package = run_ticket(
        ticket=TICKET,
        transport=_fixture(valid=False),
        mode="offline_injected",
        run_id="ticket-run-2",
        worst_cost_limit_cny_nanos=500_000_000,
    )
    assert package["outcome"] == "handoff"
    assert package["handoff_reason"].startswith("enumeration_contract_failure")

    connection = sqlite3.connect(":memory:")
    create_ticket_tables(connection)
    save_ticket_run(connection, package)
    with pytest.raises(Exception, match="product_qa_decision_requires_candidate"):
        record_ticket_decision(connection, run_id="ticket-run-2", decision="approve", decision_text=None)


def test_ticket_context_correction():
    package = {
        "acknowledged_context": ["滤网可轻拍除尘", "无关句子"],
        "context_corrections": [],
        "proposal": {"content": {"draft_reply": "滤网可轻拍除尘。", "action_steps": ["步骤一"]}},
    }
    _correct_ticket_context(package)
    assert package["acknowledged_context"] == ["无关句子"]
    assert package["context_corrections"] == ["滤网可轻拍除尘"]


def test_efficiency_stats_computes_rates_and_durations():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE TABLE qa_runs (run_id TEXT, created_at TEXT, question TEXT, product_model TEXT,"
        " outcome TEXT, handoff_reason TEXT, package_json TEXT, package_sha256 TEXT,"
        " decision TEXT, decision_text TEXT, decided_at TEXT)"
    )
    create_ticket_tables(connection)
    connection.execute(
        "INSERT INTO qa_runs VALUES ('q1', '2026-07-22T10:00:00+00:00', 'q', 'CZ-R1',"
        " 'candidate', NULL, '{}', 'x', 'approve', NULL, '2026-07-22T10:05:00+00:00')"
    )
    connection.execute(
        "INSERT INTO ticket_runs (run_id, ticket_id, created_at, outcome, handoff_reason,"
        " package_json, package_sha256, decision, decision_text, decided_at)"
        " VALUES ('t1', 'T-001', '2026-07-22T10:00:00+00:00', 'candidate', NULL, '{}', 'y',"
        " 'edit', '改', '2026-07-22T10:15:00+00:00')"
    )
    connection.execute(
        "INSERT INTO ticket_runs (run_id, ticket_id, created_at, outcome, handoff_reason,"
        " package_json, package_sha256) VALUES ('t2', 'T-002', '2026-07-22T11:00:00+00:00',"
        " 'handoff', 'x', '{}', 'z')"
    )
    connection.commit()
    stats = efficiency_stats(connection)
    assert stats["total_runs"] == 3
    assert stats["candidate_runs"] == 2
    assert stats["handoff_runs"] == 1
    assert stats["decided_runs"] == 2
    assert stats["approve_count"] == 1
    assert stats["edit_count"] == 1
    assert stats["reject_count"] == 0
    assert stats["median_seconds_to_decision"] == 600.0

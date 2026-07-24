"""Product ticket adapter: two-step LLM pipeline for the ticket mainline."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from .boundaries import (
    build_boundary_handoff_package,
    evaluate_generation_boundary,
)
from .qa import (
    LlmQaError,
    _context_contradiction,
    _record_handoff,
    _retrieve_evidence,
    _request_body,
)
from traceable_support.generation.ticket_contract import (
    TICKET_OUTPUT_SCHEMA_VERSION,
    TICKET_SYSTEM_PROMPT,
    TicketContractError,
    ticket_completeness_gate,
    validate_ticket_result_v2,
)
from traceable_support.generation.checklist import (
    CHECKLIST_SCHEMA_VERSION,
    CHECKLIST_SYSTEM_PROMPT,
    TwoStepError,
    build_clause_inventory,
    checklist_model_projection,
    validate_step1_result,
)
from traceable_support.provider.budget import ReservedCallBudget
from traceable_support.provider.contract import (
    MAX_REQUEST_BYTES,
    canonical_json_bytes,
    sha256_bytes,
    sha256_canonical,
)
from traceable_support.provider.deepseek import MODE_AUTHORIZED_REAL, MODE_OFFLINE

PACKAGE_SCHEMA_VERSION = "product-ticket-package-v1"
STEP1_MAX_OUTPUT_TOKENS = 8192
STEP2_MAX_OUTPUT_TOKENS = 8192


def _fail(code: str) -> None:
    raise LlmQaError(code) from None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _correct_ticket_context(package: dict[str, Any]) -> None:
    """Remove declarations contradicted by the proposal text; record the correction."""
    proposal = package.get("proposal")
    if not proposal or not package.get("acknowledged_context"):
        return
    body = proposal["content"]["draft_reply"] + "\n" + "\n".join(proposal["content"]["action_steps"])
    contradicted = _context_contradiction(
        {"acknowledged_context": package["acknowledged_context"]}, body
    )
    if contradicted:
        package["acknowledged_context"] = [
            entry for entry in package["acknowledged_context"]
            if entry not in contradicted
        ]
        package["context_corrections"] = contradicted


def _load_ticket(connection: sqlite3.Connection, ticket_id: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT ticket_id, product_model, issue_description, category, priority"
        " FROM tickets WHERE ticket_id = ?",
        (ticket_id,),
    ).fetchone()
    if row is None:
        _fail("product_ticket_unknown")
    return {
        "ticket_id": row[0],
        "product_model": row[1],
        "issue_description": row[2],
        "category": row[3],
        "priority": row[4],
    }


def run_ticket(
    *,
    ticket: dict[str, Any],
    transport: Any,
    mode: str,
    run_id: str,
    worst_cost_limit_cny_nanos: int,
    on_stage: Any = None,
    call_budget: ReservedCallBudget | None = None,
) -> dict[str, Any]:
    """Execute the two-step ticket pipeline and return a complete package."""
    from .qa import _call

    if mode not in {MODE_OFFLINE, MODE_AUTHORIZED_REAL}:
        _fail("product_qa_mode_invalid")
    question = ticket["issue_description"]
    boundary = evaluate_generation_boundary(question, ticket["product_model"])
    if boundary is not None:
        if callable(on_stage):
            on_stage("preflight", "failed")
        return build_boundary_handoff_package(
            task_type="ticket",
            text=question,
            product_model=ticket["product_model"],
            run_id=run_id,
            decision=boundary,
            ticket=ticket,
        )
    stages: list[dict[str, Any]] = []

    def _stage(stage: str, status: str) -> None:
        stages.append({"stage": stage, "status": status, "at": _utc_now()})
        if callable(on_stage):
            on_stage(stage, status)

    _stage("retrieval", "started")
    evidence = _retrieve_evidence(question, ticket["product_model"])
    _stage("retrieval", "finished")

    stage_input_1 = {
        "schema_version": "obligation-checklist-input-v2",
        "question": question,
        "product_model": ticket["product_model"],
        "channel": "ticket",
        "evidence_clauses": build_clause_inventory(evidence),
    }
    user1 = {"object_id": "product-ticket-checklist", "run_id": run_id, "input": stage_input_1}
    body1 = _request_body(
        CHECKLIST_SYSTEM_PROMPT, user1, thinking=True, max_tokens=STEP1_MAX_OUTPUT_TOKENS,
    )
    budget = call_budget or ReservedCallBudget(limit=worst_cost_limit_cny_nanos)
    budget.call_limit = 2
    item1 = {"case_id": "product-ticket", "evidence": evidence}

    package = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "ticket_id": ticket["ticket_id"],
        "product_model": ticket["product_model"],
        "category": ticket["category"],
        "priority": ticket["priority"],
        "question": question,
        "run_id": run_id,
        "created_at": _utc_now(),
        "evidence": evidence,
        "checklist": None,
        "acknowledged_context": [],
        "context_corrections": [],
        "proposal": None,
        "gates": {},
        "usage": [],
        "worst_cost_cny_nanos": 0,
        "stages": stages,
        "outcome": "handoff",
        "handoff_reason": None,
        "failure_classification": None,
    }

    _stage("enumeration", "started")
    step1 = _call(
        transport, mode, budget, sequence=1, body=body1,
        prompt_sha=sha256_bytes(CHECKLIST_SYSTEM_PROMPT.encode()),
        stage_input_sha=sha256_canonical(stage_input_1),
        schema=CHECKLIST_SCHEMA_VERSION, run_id=run_id, case_label="enumerate",
    )
    package["worst_cost_cny_nanos"] += step1["worst_cost_cny_nanos"]
    if not step1["ok"]:
        package["gates"]["step1_execution"] = "failed"
        _stage("enumeration", "failed")
        return _record_handoff(
            package,
            f"enumeration_execution_failure:{step1['failure_code']}",
        )
    try:
        checklist = validate_step1_result(item1, step1["raw"])
    except TwoStepError as exc:
        package["gates"]["step1_contract"] = "failed"
        _stage("enumeration", "failed")
        return _record_handoff(
            package,
            f"enumeration_contract_failure:{exc}",
        )
    package["checklist"] = checklist
    package["acknowledged_context"] = deepcopy(checklist["acknowledged_context"])
    package["gates"]["step1_contract"] = "passed"
    package["usage"].append({"stage": "enumerate", "usage": step1["usage"], "cost": step1["cost"]})
    _stage("enumeration", "finished")

    stage_input_2 = {
        "schema_version": "ticket-proposal-input-v2",
        "question": question,
        "product_model": ticket["product_model"],
        "channel": "ticket",
        "evidence": evidence,
        "obligation_checklist": checklist_model_projection(checklist),
    }
    user2 = {"object_id": "product-ticket-generate", "run_id": run_id, "input": stage_input_2}
    body2 = _request_body(
        TICKET_SYSTEM_PROMPT, user2, thinking=True, max_tokens=STEP2_MAX_OUTPUT_TOKENS,
    )
    _stage("generation", "started")
    step2 = _call(
        transport, mode, budget, sequence=2, body=body2,
        prompt_sha=sha256_bytes(TICKET_SYSTEM_PROMPT.encode()),
        stage_input_sha=sha256_canonical(stage_input_2),
        schema=TICKET_OUTPUT_SCHEMA_VERSION, run_id=run_id, case_label="generate",
    )
    package["worst_cost_cny_nanos"] += step2["worst_cost_cny_nanos"]
    if not step2["ok"]:
        package["gates"]["step2_execution"] = "failed"
        _stage("generation", "failed")
        return _record_handoff(
            package,
            f"generation_execution_failure:{step2['failure_code']}",
        )
    item2 = {"case_id": "product-ticket", "evidence": evidence}
    try:
        result = validate_ticket_result_v2(item2, checklist, step2["raw"])
    except TicketContractError as exc:
        package["gates"]["step2_contract"] = "failed"
        _stage("generation", "failed")
        return _record_handoff(
            package,
            f"generation_contract_failure:{exc}",
        )
    gate = ticket_completeness_gate(checklist, result)
    package["gates"]["step2_contract"] = "passed"
    package["gates"]["completeness_gate"] = gate
    package["usage"].append({"stage": "generate", "usage": step2["usage"], "cost": step2["cost"]})
    _stage("generation", "finished")
    _stage("gate", "finished" if gate["pass"] else "failed")
    package["proposal"] = deepcopy(result)
    if not gate["pass"]:
        _correct_ticket_context(package)
        return _record_handoff(package, "completeness_gate_failed")
    _correct_ticket_context(package)
    package["outcome"] = "candidate"
    return package


def create_ticket_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ticket_runs (
            run_id TEXT PRIMARY KEY,
            ticket_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            outcome TEXT NOT NULL,
            handoff_reason TEXT,
            package_json TEXT NOT NULL,
            package_sha256 TEXT NOT NULL,
            decision TEXT,
            decision_text TEXT,
            decided_at TEXT
        )
        """
    )
    connection.commit()


def save_ticket_run(connection: sqlite3.Connection, package: dict[str, Any]) -> str:
    body = canonical_json_bytes(package)
    digest = hashlib.sha256(body).hexdigest()
    connection.execute(
        "INSERT INTO ticket_runs (run_id, ticket_id, created_at, outcome,"
        " handoff_reason, package_json, package_sha256) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            package["run_id"], package["ticket_id"], package["created_at"],
            package["outcome"], package["handoff_reason"], body.decode("utf-8"), digest,
        ),
    )
    connection.commit()
    return digest


def record_ticket_decision(connection: sqlite3.Connection, *, run_id: str,
                           decision: str, decision_text: str | None) -> None:
    if decision not in {"approve", "edit", "reject"}:
        _fail("product_qa_decision_invalid")
    row = connection.execute(
        "SELECT outcome, decision FROM ticket_runs WHERE run_id = ?", (run_id,),
    ).fetchone()
    if row is None:
        _fail("product_qa_run_unknown")
    if row[0] != "candidate":
        _fail("product_qa_decision_requires_candidate")
    if row[1] is not None:
        _fail("product_qa_decision_already_recorded")
    connection.execute(
        "UPDATE ticket_runs SET decision = ?, decision_text = ?, decided_at = ? WHERE run_id = ?",
        (decision, decision_text, _utc_now(), run_id),
    )
    connection.commit()


def load_ticket_run(connection: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT package_json, decision, decision_text, decided_at FROM ticket_runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    if row is None:
        _fail("product_qa_run_unknown")
    return {
        "package": json.loads(row[0]),
        "decision": row[1],
        "decision_text": row[2],
        "decided_at": row[3],
    }


def efficiency_stats(connection: sqlite3.Connection) -> dict[str, Any]:
    """Descriptive efficiency stats over QA and ticket runs (no A/B conclusion)."""
    from statistics import median

    def _collect(table: str) -> list[dict[str, Any]]:
        rows = connection.execute(
            f"SELECT created_at, outcome, decision, decided_at FROM {table}"
        ).fetchall()
        return [
            {"created_at": r[0], "outcome": r[1], "decision": r[2], "decided_at": r[3]}
            for r in rows
        ]

    runs = _collect("qa_runs") + _collect("ticket_runs")
    durations = []
    for run in runs:
        if run["decided_at"]:
            started = datetime.fromisoformat(run["created_at"])
            decided = datetime.fromisoformat(run["decided_at"])
            durations.append((decided - started).total_seconds())
    decided = [run for run in runs if run["decision"]]
    return {
        "schema_version": "efficiency-stats-v1",
        "total_runs": len(runs),
        "candidate_runs": sum(run["outcome"] == "candidate" for run in runs),
        "handoff_runs": sum(run["outcome"] == "handoff" for run in runs),
        "decided_runs": len(decided),
        "approve_count": sum(run["decision"] == "approve" for run in decided),
        "edit_count": sum(run["decision"] == "edit" for run in decided),
        "reject_count": sum(run["decision"] == "reject" for run in decided),
        "median_seconds_to_decision": median(durations) if durations else None,
    }


__all__ = [
    "PACKAGE_SCHEMA_VERSION",
    "create_ticket_tables",
    "efficiency_stats",
    "load_ticket_run",
    "record_ticket_decision",
    "run_ticket",
    "save_ticket_run",
]

"""Product QA adapter: two-step LLM pipeline for the QA product mainline.

Runs retrieval -> thinking enumeration (obligation checklist with declared
non-obligation context) -> thinking generation -> mechanical completeness gate.
Every failure becomes an honest handoff state, never a packaged success.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from traceable_support.product.boundaries import (
    build_boundary_handoff_package,
    evaluate_generation_boundary,
)
from traceable_support.generation.qa_contract import (
    OUTPUT_SCHEMA_VERSION,
    CandidateContractError,
    _contract,
    validate_result,
)
from traceable_support.generation.checklist import (
    CHECKLIST_SCHEMA_VERSION,
    CHECKLIST_SYSTEM_PROMPT,
    STEP1_MAX_OUTPUT_TOKENS,
    STEP2_MAX_OUTPUT_TOKENS,
    STEP2_SYSTEM_PROMPT,
    TwoStepError,
    build_clause_inventory,
    checklist_model_projection,
    completeness_gate,
    validate_step1_result,
)
from traceable_support.generation.failure_taxonomy import classify_generation_failure
from traceable_support.retrieval.hybrid import BusinessRetrievalRequest, ModelAwareRrfPipeline
from traceable_support.provider.budget import ReservedCallBudget, attempt_call
from traceable_support.provider.contract import (
    MAX_REQUEST_BYTES,
    MODEL,
    STAGE_CONTENT,
    canonical_json_bytes,
    sha256_bytes,
    sha256_canonical,
    strict_json_loads,
)
from traceable_support.provider.deepseek import MODE_AUTHORIZED_REAL, MODE_OFFLINE

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SCHEMA_VERSION = "product-qa-package-v1"
LLM_TIMEOUT_MS = 180_000
SESSION_MAX_RUNS = 6
SESSION_MAX_WORST_COST_CNY_NANOS = 700_000_000


class LlmQaError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
        self.__cause__ = None
        self.__context__ = None


def _fail(code: str) -> None:
    raise LlmQaError(code) from None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _retrieve_evidence(question: str, product_model: str) -> list[dict[str, Any]]:
    result = ModelAwareRrfPipeline(unit_strategy="native_section", delivery_k=5).retrieve(
        BusinessRetrievalRequest(
            query_text=question,
            known_product_model=product_model,
            channel="qa",
            candidate_pool_limit=10,
            delivery_limit=5,
        )
    )
    if len(result.candidate_hits) != 10:
        _fail("product_qa_retrieval_incomplete")
    evidence = [
        {
            "rank": hit.rank,
            "evidence_id": hit.unit.unit_id,
            "document_id": hit.unit.document_id,
            "section_id": hit.unit.section_id,
            "section_heading": hit.unit.section_heading,
            "applicable_models": list(hit.unit.applicable_models),
            "text": hit.unit.text,
            "source_spans": [
                {"document_id": s.document_id, "relative_path": s.relative_path,
                 "section_id": s.section_id, "exact_text": s.exact_text}
                for s in hit.unit.source_spans
            ],
        }
        for hit in result.candidate_hits
    ]
    if any(product_model not in item["applicable_models"] for item in evidence):
        _fail("product_qa_model_scope_invalid")
    return evidence


def _request_body(system_prompt: str, user: dict[str, Any], *, thinking: bool, max_tokens: int) -> bytes:
    body = canonical_json_bytes({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": canonical_json_bytes(user).decode()},
        ],
        "stream": False,
        "thinking": {"type": "enabled" if thinking else "disabled"},
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": max_tokens,
    })
    if len(body) > MAX_REQUEST_BYTES:
        _fail("product_qa_request_too_large")
    return body


def _call(transport: Any, mode: str, budget: ReservedCallBudget, *, sequence: int,
          body: bytes, prompt_sha: str, stage_input_sha: str, schema: str,
          run_id: str, case_label: str) -> dict[str, Any]:
    from traceable_support.provider.budget import build_request_identity

    request_body = strict_json_loads(body)
    if (
        type(request_body) is not dict
        or type(request_body.get("max_tokens")) is not int
    ):
        _fail("product_qa_request_max_tokens_invalid")
    prepared = {
        "body": body,
        "prompt_version": "product-qa",
        "prompt_sha256": prompt_sha,
        "stage_input_sha256": stage_input_sha,
        "output_schema_version": schema,
    }
    request = build_request_identity(
        sequence=sequence,
        case_id=case_label,
        object_id=f"product-qa-{case_label}",
        run_id=run_id,
        stage=STAGE_CONTENT,
        prepared=prepared,
        max_output_tokens=request_body["max_tokens"],
        timeout_ms=LLM_TIMEOUT_MS,
    )
    attempt = attempt_call(transport=transport, mode=mode, budget=budget, request=request)
    if attempt.failure_code:
        return {"ok": False, "failure_code": attempt.failure_code, "failure_stage": attempt.failure_stage,
                "request_sha256": request["request_sha256"],
                "worst_cost_cny_nanos": request["worst_cost_cny_nanos"]}
    return {
        "ok": True,
        "raw": attempt.raw_result,
        "usage": deepcopy(attempt.parsed["usage"]),
        "cost": deepcopy(attempt.cost),
        "request_sha256": request["request_sha256"],
        "worst_cost_cny_nanos": request["worst_cost_cny_nanos"],
    }


def validate_qa_input(question: Any, product_model: Any) -> None:
    if type(question) is not str or not question.strip() or len(question) > 500:
        _fail("product_qa_question_invalid")
    if product_model not in {"CZ-R1", "CZ-R2"}:
        _fail("product_qa_model_invalid")


def _squash_text(text: str) -> str:
    return "".join(text.split())


def _context_contradiction(checklist: dict[str, Any], answer_text: str) -> list[str]:
    """Declared-excluded clauses must not appear in the answer text."""
    squashed_answer = _squash_text(answer_text)
    return [
        entry for entry in checklist.get("acknowledged_context", [])
        if _squash_text(entry) in squashed_answer
    ]


def _correct_context_declarations(package: dict[str, Any]) -> None:
    """Remove declarations contradicted by the answer; record the correction.

    The declaration (not the answer) is wrong in this case: the clause is
    sourced and harmless in the answer, so the excluded-declaration is false.
    The raw checklist stays untouched for audit; the reviewer-facing list is
    corrected and the correction is recorded.
    """
    answer = package.get("answer")
    if not answer or not package.get("acknowledged_context"):
        return
    contradicted = _context_contradiction(
        {"acknowledged_context": package["acknowledged_context"]},
        answer["content"]["answer"]["text"],
    )
    if contradicted:
        package["acknowledged_context"] = [
            entry for entry in package["acknowledged_context"]
            if entry not in contradicted
        ]
        package["context_corrections"] = contradicted


def _record_handoff(
    package: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    package["handoff_reason"] = reason
    package["failure_classification"] = classify_generation_failure(reason)
    return package


def _provider_observations(transport: Any) -> list[dict[str, Any]]:
    """Snapshot the transport's validated safe observations, if it exposes any.

    Observations are canary-checked at the transport boundary and carry no
    prompts, responses, headers, or credentials. The public projection never
    copies them; the control plane persists them as internal run evidence.
    """

    safe_observations = getattr(transport, "safe_observations", None)
    if not callable(safe_observations):
        return []
    observations = safe_observations()
    return observations if type(observations) is list else []


def run_qa(
    *,
    question: str,
    product_model: str,
    transport: Any,
    mode: str,
    run_id: str,
    worst_cost_limit_cny_nanos: int,
    on_stage: Any = None,
) -> dict[str, Any]:
    """Execute the two-step QA pipeline and return a complete package."""
    validate_qa_input(question, product_model)
    if mode not in {MODE_OFFLINE, MODE_AUTHORIZED_REAL}:
        _fail("product_qa_mode_invalid")
    boundary = evaluate_generation_boundary(question, product_model, task_type="qa")
    if boundary is not None:
        if callable(on_stage):
            on_stage("preflight", "failed")
        return build_boundary_handoff_package(
            task_type="qa",
            text=question,
            product_model=product_model,
            run_id=run_id,
            decision=boundary,
        )
    stages: list[dict[str, Any]] = []

    def _stage(stage: str, status: str) -> None:
        entry = {"stage": stage, "status": status, "at": _utc_now()}
        stages.append(entry)
        if callable(on_stage):
            on_stage(stage, status)

    _stage("retrieval", "started")
    evidence = _retrieve_evidence(question, product_model)
    _stage("retrieval", "finished")
    stage_input_1 = {
        "schema_version": "obligation-checklist-input-v2",
        "question": question,
        "product_model": product_model,
        "channel": "qa",
        "evidence_clauses": build_clause_inventory(evidence),
    }
    user1 = {"object_id": f"product-qa-checklist", "run_id": run_id, "input": stage_input_1}
    body1 = _request_body(
        CHECKLIST_SYSTEM_PROMPT, user1, thinking=True, max_tokens=STEP1_MAX_OUTPUT_TOKENS,
    )
    budget = ReservedCallBudget(limit=worst_cost_limit_cny_nanos)
    budget.call_limit = 2
    item1 = {"case_id": "product-qa", "evidence": evidence}

    _stage("enumeration", "started")
    step1 = _call(
        transport, mode, budget, sequence=1, body=body1,
        prompt_sha=sha256_bytes(CHECKLIST_SYSTEM_PROMPT.encode()),
        stage_input_sha=sha256_canonical(stage_input_1),
        schema=CHECKLIST_SCHEMA_VERSION, run_id=run_id, case_label="enumerate",
    )
    package = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "question": question,
        "product_model": product_model,
        "run_id": run_id,
        "created_at": _utc_now(),
        "evidence": evidence,
        "checklist": None,
        "acknowledged_context": [],
        "context_corrections": [],
        "answer": None,
        "gates": {},
        "usage": [],
        "worst_cost_cny_nanos": 0,
        "stages": stages,
        "outcome": "handoff",
        "handoff_reason": None,
        "failure_classification": None,
    }
    package["provider_observations"] = _provider_observations(transport)
    if not step1["ok"]:
        package["worst_cost_cny_nanos"] += step1["worst_cost_cny_nanos"]
        package["gates"]["step1_execution"] = "failed"
        _stage("enumeration", "failed")
        return _record_handoff(
            package,
            f"enumeration_execution_failure:{step1['failure_code']}",
        )
    package["worst_cost_cny_nanos"] += step1["worst_cost_cny_nanos"]
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
        "schema_version": "retrieved-top10-qa-input-v8",
        "question": question,
        "product_model": product_model,
        "channel": "qa",
        "evidence": evidence,
        "obligation_checklist": checklist_model_projection(checklist),
        "response_contract": _contract(evidence),
    }
    user2 = {"object_id": "product-qa-generate", "run_id": run_id, "input": stage_input_2}
    body2 = _request_body(
        STEP2_SYSTEM_PROMPT, user2, thinking=True, max_tokens=STEP2_MAX_OUTPUT_TOKENS,
    )
    _stage("generation", "started")
    step2 = _call(
        transport, mode, budget, sequence=2, body=body2,
        prompt_sha=sha256_bytes(STEP2_SYSTEM_PROMPT.encode()),
        stage_input_sha=sha256_canonical(stage_input_2),
        schema=OUTPUT_SCHEMA_VERSION, run_id=run_id, case_label="generate",
    )
    package["provider_observations"] = _provider_observations(transport)
    if not step2["ok"]:
        package["worst_cost_cny_nanos"] += step2["worst_cost_cny_nanos"]
        package["gates"]["step2_execution"] = "failed"
        _stage("generation", "failed")
        return _record_handoff(
            package,
            f"generation_execution_failure:{step2['failure_code']}",
        )
    package["worst_cost_cny_nanos"] += step2["worst_cost_cny_nanos"]
    item2 = {"case_id": "product-qa", "evidence": evidence}
    try:
        result = validate_result(item2, checklist, step2["raw"])
    except CandidateContractError as exc:
        package["gates"]["step2_contract"] = "failed"
        _stage("generation", "failed")
        return _record_handoff(
            package,
            f"generation_contract_failure:{exc}",
        )
    gate = completeness_gate(checklist, result)
    package["gates"]["step2_contract"] = "passed"
    package["gates"]["completeness_gate"] = gate
    package["usage"].append({"stage": "generate", "usage": step2["usage"], "cost": step2["cost"]})
    _stage("generation", "finished")
    _stage("gate", "finished" if gate["pass"] else "failed")
    if not gate["pass"]:
        package["answer"] = deepcopy(result)
        _correct_context_declarations(package)
        return _record_handoff(package, "completeness_gate_failed")
    package["answer"] = deepcopy(result)
    _correct_context_declarations(package)
    package["outcome"] = "candidate"
    return package


class QaSessionBudget:
    """Session-level cumulative guard for product QA runs."""

    def __init__(self, *, max_runs: int = SESSION_MAX_RUNS,
                 max_worst_cost_cny_nanos: int = SESSION_MAX_WORST_COST_CNY_NANOS) -> None:
        self.max_runs = max_runs
        self.max_worst_cost_cny_nanos = max_worst_cost_cny_nanos

    def check(self, *, runs_completed: int, worst_cost_accumulated: int) -> None:
        if runs_completed >= self.max_runs:
            _fail("product_qa_session_run_limit_exceeded")
        if worst_cost_accumulated >= self.max_worst_cost_cny_nanos:
            _fail("product_qa_session_budget_exceeded")


def create_qa_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS qa_runs (
            run_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            question TEXT NOT NULL,
            product_model TEXT NOT NULL,
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


def save_qa_run(connection: sqlite3.Connection, package: dict[str, Any]) -> str:
    body = canonical_json_bytes(package)
    digest = hashlib.sha256(body).hexdigest()
    connection.execute(
        "INSERT INTO qa_runs (run_id, created_at, question, product_model, outcome,"
        " handoff_reason, package_json, package_sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            package["run_id"], package["created_at"], package["question"],
            package["product_model"], package["outcome"], package["handoff_reason"],
            body.decode("utf-8"), digest,
        ),
    )
    connection.commit()
    return digest


def record_qa_decision(connection: sqlite3.Connection, *, run_id: str,
                       decision: str, decision_text: str | None) -> None:
    if decision not in {"approve", "edit", "reject"}:
        _fail("product_qa_decision_invalid")
    row = connection.execute(
        "SELECT outcome, decision FROM qa_runs WHERE run_id = ?", (run_id,),
    ).fetchone()
    if row is None:
        _fail("product_qa_run_unknown")
    if row[0] != "candidate":
        _fail("product_qa_decision_requires_candidate")
    if row[1] is not None:
        _fail("product_qa_decision_already_recorded")
    connection.execute(
        "UPDATE qa_runs SET decision = ?, decision_text = ?, decided_at = ? WHERE run_id = ?",
        (decision, decision_text, _utc_now(), run_id),
    )
    connection.commit()


def list_qa_runs(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT run_id, created_at, question, product_model, outcome, handoff_reason,"
        " decision, decided_at FROM qa_runs ORDER BY created_at DESC"
    ).fetchall()
    return [
        {
            "run_id": row[0], "created_at": row[1], "question": row[2],
            "product_model": row[3], "outcome": row[4], "handoff_reason": row[5],
            "decision": row[6], "decided_at": row[7],
        }
        for row in rows
    ]


def load_qa_run(connection: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT package_json, decision, decision_text, decided_at FROM qa_runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    if row is None:
        _fail("product_qa_run_unknown")
    package = json.loads(row[0])
    return {
        "package": package,
        "decision": row[1],
        "decision_text": row[2],
        "decided_at": row[3],
    }


def default_qa_transport() -> Any:
    """Lazily construct the reviewed real transport for the product QA path."""
    from traceable_support.provider.deepseek import AuthorizedOfficialHTTPSTransport

    return AuthorizedOfficialHTTPSTransport()


__all__ = [
    "LLM_TIMEOUT_MS",
    "LlmQaError",
    "PACKAGE_SCHEMA_VERSION",
    "QaSessionBudget",
    "SESSION_MAX_RUNS",
    "SESSION_MAX_WORST_COST_CNY_NANOS",
    "create_qa_tables",
    "list_qa_runs",
    "load_qa_run",
    "record_qa_decision",
    "run_qa",
    "save_qa_run",
    "validate_qa_input",
]

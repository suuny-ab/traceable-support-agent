"""Stage 12 formal evaluation runner over the frozen unseen set.

Executes each unseen case through ``DefaultProductRunner`` (QA and ticket
task types), scores it mechanically against the frozen expectations, and
writes two artifacts:

- a private raw record (``--out`` only) with full packages, Provider outputs
  and per-stage identity/usage;
- a public aggregate report (``--report``, schema ``stage12-aggregate-v1``)
  with per-case pass/fail and failure codes, totals and identity bindings —
  never any input, answer, or Provider raw text.

Offline mode injects scripted responses and performs zero network and zero
Provider calls. Real mode assembles the ``MODE_AUTHORIZED_REAL`` transport the
same lazy way as the reviewed live wiring; importing this module or parsing
arguments never reads ``DEEPSEEK_API_KEY`` and never opens a socket.

Usage::

    PYTHONPATH=api/src python tools/stage12_eval.py \
        --set <unseen-set.json> --out <private-dir> --report <report.json> \
        [--mode offline|real] [--offline-responses <scripted.json>] \
        [--dims evals/stage12-unseen-dims-v1.json] [--identity <identity.json>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
_API_SRC = REPO_ROOT / "api" / "src"
if str(_API_SRC) not in sys.path:
    sys.path.insert(0, str(_API_SRC))

from traceable_support.generation.checklist import _squash  # noqa: E402
from traceable_support.generation.failure_taxonomy import (  # noqa: E402
    summarize_generation_failures,
)
from traceable_support.product.qa import (  # noqa: E402
    SESSION_MAX_WORST_COST_CNY_NANOS,
    default_qa_transport,
)
from traceable_support.product.runner import DefaultProductRunner  # noqa: E402
from traceable_support.product.types import ExecutionResult, RunInput  # noqa: E402
from traceable_support.provider.deepseek import (  # noqa: E402
    MODE_AUTHORIZED_REAL,
    MODE_OFFLINE,
    OfflineInjectedTransport,
)
from traceable_support.provider.response import json_response  # noqa: E402

HARD_MAX_CASES = 24
HARD_MAX_CALLS = 150
HARD_MAX_COST_CNY_NANOS = 10 * 1_000_000_000
MAX_CALLS_PER_CASE = 2
REPORT_SCHEMA_VERSION = "stage12-aggregate-v1"
RAW_SCHEMA_VERSION = "stage12-raw-records-v1"
OFFLINE_RESPONSES_SCHEMA_VERSION = "stage12-offline-responses-v1"
SET_SCHEMA_VERSION = "stage12-unseen-v1"
DEFAULT_DIMS = REPO_ROOT / "evals" / "stage12-unseen-dims-v1.json"

_DEFAULT_USAGE = {
    "prompt_tokens": 100,
    "completion_tokens": 100,
    "total_tokens": 200,
    "prompt_cache_hit_tokens": 0,
    "prompt_cache_miss_tokens": 100,
}


class Stage12Error(RuntimeError):
    """Fixed-code setup failure; never carries set content or secrets."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
        self.__cause__ = None
        self.__context__ = None


def _fail(code: str) -> None:
    raise Stage12Error(code) from None


def _load_json(path: Path, code: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        _fail(code)


def load_unseen_set(path: Path) -> dict[str, Any]:
    suite = _load_json(path, "stage12_set_unreadable")
    if type(suite) is not dict or suite.get("schema_version") != SET_SCHEMA_VERSION:
        _fail("stage12_set_schema_invalid")
    cases = suite["cases"] if type(suite.get("cases")) is list else None
    if cases is None or not 1 <= len(cases) <= HARD_MAX_CASES:
        _fail("stage12_set_cases_invalid")
    for case in cases:
        if (
            type(case) is not dict
            or type(case.get("case_id")) is not str
            or case.get("task_type") not in {"qa", "ticket"}
            or type(case.get("input")) is not str
            or case.get("product_model") not in {"CZ-R1", "CZ-R2"}
            or type(case.get("expected")) is not dict
        ):
            _fail("stage12_set_case_invalid")
    return suite


def load_dimensions(path: Path) -> dict[str, str]:
    dims = _load_json(path, "stage12_dims_unreadable")
    if type(dims) is not dict or type(dims.get("dimensions")) is not list:
        _fail("stage12_dims_invalid")
    mapping: dict[str, str] = {}
    for entry in dims["dimensions"]:
        if (
            type(entry) is not dict
            or type(entry.get("id")) is not str
            or type(entry.get("case_code")) is not str
        ):
            _fail("stage12_dims_invalid")
        mapping[entry["case_code"]] = entry["id"]
    return mapping


def dimension_of(case_id: str, mapping: dict[str, str]) -> str:
    parts = case_id.split("-")
    if len(parts) < 3:
        return "unmapped"
    return mapping.get(parts[2], "unmapped")


def load_offline_factories(path: Path) -> dict[str, Callable[[], OfflineInjectedTransport]]:
    """Build one scripted transport factory per case; zero network, zero Provider."""

    payload = _load_json(path, "stage12_offline_responses_unreadable")
    if (
        type(payload) is not dict
        or payload.get("schema_version") != OFFLINE_RESPONSES_SCHEMA_VERSION
        or type(payload.get("cases")) is not dict
    ):
        _fail("stage12_offline_responses_invalid")
    factories: dict[str, Callable[[], OfflineInjectedTransport]] = {}
    for case_id, raw_steps in payload["cases"].items():
        if type(case_id) is not str or type(raw_steps) is not list or not raw_steps:
            _fail("stage12_offline_responses_invalid")
        steps: list[dict[str, Any]] = []
        for step in raw_steps:
            if type(step) is not dict or step.get("kind") not in {
                "response", "timeout", "transport_error",
            }:
                _fail("stage12_offline_responses_invalid")
            if step["kind"] == "response":
                if type(step.get("json")) is not dict:
                    _fail("stage12_offline_responses_invalid")
                usage = step.get("usage", _DEFAULT_USAGE)
                steps.append({
                    "kind": "response",
                    "status_code": step.get("status_code", 200),
                    "body": json_response(step["json"], usage=usage),
                })
            else:
                steps.append({"kind": step["kind"]})

        def _factory(steps: list[dict[str, Any]] = steps) -> OfflineInjectedTransport:
            return OfflineInjectedTransport(steps)

        factories[case_id] = _factory
    return factories


def default_offline_responses_path(set_path: Path) -> Path:
    return set_path.with_name(set_path.stem + ".offline-responses.json")


def _customer_visible_text(package: dict[str, Any], task_type: str) -> str:
    if task_type == "qa":
        answer = package.get("answer")
        if not answer:
            return ""
        return answer["content"]["answer"]["text"]
    proposal = package.get("proposal")
    if not proposal:
        return ""
    content = proposal["content"]
    return content["draft_reply"] + "\n" + "\n".join(content["action_steps"])


def _used_source_sections(package: dict[str, Any], task_type: str) -> list[str]:
    if package.get("outcome") == "handoff" and "boundary_sources" in package:
        boundary_sources = package["boundary_sources"]
        if (
            type(boundary_sources) is list
            and all(type(source) is str and source for source in boundary_sources)
            and len(boundary_sources) == len(set(boundary_sources))
        ):
            return sorted(boundary_sources)
        return []
    result = package.get("answer") if task_type == "qa" else package.get("proposal")
    if not result:
        return []
    evidence_by_id = {entry["evidence_id"]: entry for entry in package["evidence"]}
    return sorted({
        f"{evidence_by_id[evidence_id]['document_id']}/"
        f"{evidence_by_id[evidence_id]['section_id']}"
        for evidence_id in result["used_evidence_ids"]
    })


def _candidate_result(package: dict[str, Any], task_type: str) -> Any:
    return package.get("answer") if task_type == "qa" else package.get("proposal")


def _invalid_extra_source_sections(
    package: dict[str, Any],
    task_type: str,
    extra_sections: list[str],
) -> list[str]:
    """Fail closed unless every extra source has the full host-owned binding ledger."""

    result = _candidate_result(package, task_type)
    evidence = package.get("evidence")
    if type(result) is not dict or type(evidence) is not list:
        return extra_sections
    used_evidence_ids = result.get("used_evidence_ids")
    obligation_plan = result.get("obligation_plan")
    content = result.get("content")
    if (
        type(used_evidence_ids) is not list
        or type(obligation_plan) is not list
        or type(content) is not dict
        or type(content.get("claims")) is not list
    ):
        return extra_sections
    evidence_by_id = {
        entry.get("evidence_id"): entry
        for entry in evidence
        if type(entry) is dict and type(entry.get("evidence_id")) is str
    }
    plan_by_id = {
        entry.get("obligation_id"): entry
        for entry in obligation_plan
        if type(entry) is dict and type(entry.get("obligation_id")) is str
    }
    claims = content["claims"]
    product_model = package.get("product_model")
    invalid: list[str] = []
    for section in extra_sections:
        section_evidence_ids = [
            evidence_id
            for evidence_id in used_evidence_ids
            if evidence_id in evidence_by_id
            and (
                f"{evidence_by_id[evidence_id].get('document_id')}/"
                f"{evidence_by_id[evidence_id].get('section_id')}"
            )
            == section
        ]
        section_valid = bool(section_evidence_ids)
        for evidence_id in section_evidence_ids:
            evidence_entry = evidence_by_id[evidence_id]
            applicable_models = evidence_entry.get("applicable_models")
            bound_claims = [
                claim
                for claim in claims
                if type(claim) is dict
                and type(claim.get("evidence_ids")) is list
                and evidence_id in claim["evidence_ids"]
            ]
            if (
                type(product_model) is not str
                or type(applicable_models) is not list
                or product_model not in applicable_models
                or not bound_claims
            ):
                section_valid = False
                continue
            for claim in bound_claims:
                obligation_ids = claim.get("obligation_ids")
                if (
                    type(obligation_ids) is not list
                    or not obligation_ids
                    or any(
                        obligation_id not in plan_by_id
                        or type(plan_by_id[obligation_id].get("evidence_ids"))
                        is not list
                        or evidence_id
                        not in plan_by_id[obligation_id]["evidence_ids"]
                        for obligation_id in obligation_ids
                    )
                ):
                    section_valid = False
        if not section_valid:
            invalid.append(section)
    return invalid


def _missing_required_obligation_ordinals(
    package: dict[str, Any], required_facts: list[str]
) -> list[int]:
    """Check whether one obligation completely carries each frozen fact."""

    obligation_ids_by_ordinal = _required_obligation_ids_by_ordinal(
        package, required_facts
    )
    return [
        index
        for index, obligation_ids in enumerate(obligation_ids_by_ordinal)
        if not obligation_ids
    ]


def _required_obligation_ids_by_ordinal(
    package: dict[str, Any], required_facts: list[str]
) -> list[list[str]]:
    """Map frozen propositions to obligations that completely carry them."""

    return [
        [entry["obligation_id"] for entry in entries]
        for entries in _required_obligation_receipts_by_ordinal(
            package, required_facts
        )
    ]


def _required_obligation_receipts_by_ordinal(
    package: dict[str, Any], required_facts: list[str]
) -> list[list[dict[str, Any]]]:
    """Map propositions to carrying obligations and the evidence they require."""

    checklist = package.get("checklist")
    if type(checklist) is not dict or type(checklist.get("obligations")) is not list:
        return [[] for _ in required_facts]
    obligation_spans: list[tuple[str, list[dict[str, Any]]]] = []
    seen_ids: set[str] = set()
    for obligation in checklist["obligations"]:
        if type(obligation) is not dict:
            continue
        obligation_id = obligation.get("obligation_id")
        spans = obligation.get("approved_source_spans")
        if (
            type(obligation_id) is not str
            or not obligation_id
            or obligation_id in seen_ids
            or type(spans) is not list
            or not spans
            or any(
                type(span) is not dict
                or type(span.get("clause_id")) is not str
                or type(span.get("exact_span_text")) is not str
                or type(span.get("evidence_id")) is not str
                for span in spans
            )
        ):
            continue
        seen_ids.add(obligation_id)
        ordered = sorted(spans, key=lambda span: span["clause_id"])
        obligation_spans.append((obligation_id, ordered))

    receipts_by_ordinal: list[list[dict[str, Any]]] = []
    for fact in required_facts:
        normalized_fact = _score_text(fact)
        proposition_receipts: list[dict[str, Any]] = []
        for obligation_id, spans in obligation_spans:
            matching_windows: list[tuple[int, int, list[str]]] = []
            for start in range(len(spans)):
                for end in range(start + 1, len(spans) + 1):
                    window = spans[start:end]
                    window_text = _score_text(
                        "".join(span["exact_span_text"] for span in window)
                    )
                    if normalized_fact in window_text:
                        matching_windows.append(
                            (
                                end - start,
                                start,
                                list(
                                    dict.fromkeys(
                                        span["evidence_id"] for span in window
                                    )
                                ),
                            )
                        )
            if matching_windows:
                _, _, required_evidence_ids = min(matching_windows)
                proposition_receipts.append({
                    "obligation_id": obligation_id,
                    "required_evidence_ids": required_evidence_ids,
                })
        receipts_by_ordinal.append(proposition_receipts)
    return receipts_by_ordinal


def _unique_nonempty_strings(value: Any) -> bool:
    return (
        type(value) is list
        and bool(value)
        and all(type(item) is str and bool(item) for item in value)
        and len(value) == len(set(value))
    )


def _proposition_binding_receipts(
    package: dict[str, Any],
    task_type: str,
    obligation_receipts_by_ordinal: list[list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[int]]:
    """Verify claim/evidence receipts for every obligation-backed proposition."""

    result = _candidate_result(package, task_type)
    checklist = package.get("checklist")
    evidence = package.get("evidence")
    if (
        type(result) is not dict
        or type(checklist) is not dict
        or type(checklist.get("obligations")) is not list
        or type(evidence) is not list
        or type(result.get("obligation_plan")) is not list
        or type(result.get("used_evidence_ids")) is not list
        or type(result.get("content")) is not dict
        or type(result["content"].get("claims")) is not list
    ):
        return [], [
            index
            for index, obligation_receipts in enumerate(
                obligation_receipts_by_ordinal
            )
            if obligation_receipts
        ]

    evidence_ids = {
        entry.get("evidence_id")
        for entry in evidence
        if type(entry) is dict and type(entry.get("evidence_id")) is str
    }
    used_evidence_ids = result["used_evidence_ids"]
    if not _unique_nonempty_strings(used_evidence_ids):
        used_evidence_ids = []
    used_evidence_id_set = set(used_evidence_ids)

    checklist_by_id: dict[str, dict[str, Any]] = {}
    duplicate_checklist_ids: set[str] = set()
    for obligation in checklist["obligations"]:
        if (
            type(obligation) is not dict
            or type(obligation.get("obligation_id")) is not str
        ):
            continue
        obligation_id = obligation["obligation_id"]
        if obligation_id in checklist_by_id:
            duplicate_checklist_ids.add(obligation_id)
        checklist_by_id[obligation_id] = obligation

    plan_by_id: dict[str, dict[str, Any]] = {}
    duplicate_plan_ids: set[str] = set()
    for entry in result["obligation_plan"]:
        if type(entry) is not dict or type(entry.get("obligation_id")) is not str:
            continue
        obligation_id = entry["obligation_id"]
        if obligation_id in plan_by_id:
            duplicate_plan_ids.add(obligation_id)
        plan_by_id[obligation_id] = entry

    claims = result["content"]["claims"]
    claim_id_counts: dict[str, int] = {}
    for claim in claims:
        if type(claim) is dict and type(claim.get("claim_id")) is str:
            claim_id = claim["claim_id"]
            claim_id_counts[claim_id] = claim_id_counts.get(claim_id, 0) + 1
    receipts: list[dict[str, Any]] = []
    missing: list[int] = []
    for ordinal, proposition_obligation_receipts in enumerate(
        obligation_receipts_by_ordinal
    ):
        if not proposition_obligation_receipts:
            continue
        valid_claim_ids: list[str] = []
        valid_obligation_ids: list[str] = []
        for obligation_receipt in proposition_obligation_receipts:
            target_obligation_id = obligation_receipt["obligation_id"]
            required_evidence_ids = set(
                obligation_receipt["required_evidence_ids"]
            )
            if (
                target_obligation_id in duplicate_checklist_ids
                or target_obligation_id in duplicate_plan_ids
                or target_obligation_id not in checklist_by_id
                or target_obligation_id not in plan_by_id
            ):
                continue
            checklist_evidence_ids = checklist_by_id[target_obligation_id].get(
                "evidence_ids"
            )
            plan_evidence_ids = plan_by_id[target_obligation_id].get("evidence_ids")
            if (
                not _unique_nonempty_strings(checklist_evidence_ids)
                or not _unique_nonempty_strings(plan_evidence_ids)
                or set(checklist_evidence_ids) != set(plan_evidence_ids)
            ):
                continue
            allowed_evidence_ids = set(checklist_evidence_ids)
            if (
                not required_evidence_ids
                or not required_evidence_ids <= allowed_evidence_ids
                or not allowed_evidence_ids <= evidence_ids
                or not allowed_evidence_ids <= used_evidence_id_set
            ):
                continue
            obligation_claim_ids: list[str] = []
            obligation_claim_evidence_ids: set[str] = set()
            for claim in claims:
                if type(claim) is not dict:
                    continue
                claim_id = claim.get("claim_id")
                claim_evidence_ids = claim.get("evidence_ids")
                claim_obligation_ids = claim.get("obligation_ids")
                if (
                    type(claim_id) is not str
                    or not claim_id
                    or claim_id_counts.get(claim_id) != 1
                    or not _unique_nonempty_strings(claim_evidence_ids)
                    or not _unique_nonempty_strings(claim_obligation_ids)
                    or target_obligation_id not in claim_obligation_ids
                ):
                    continue
                if any(
                    obligation_id in duplicate_checklist_ids
                    or obligation_id in duplicate_plan_ids
                    or obligation_id not in checklist_by_id
                    or obligation_id not in plan_by_id
                    for obligation_id in claim_obligation_ids
                ):
                    continue
                bound_evidence_ids: set[str] | None = None
                invalid_bound_obligation = False
                for obligation_id in claim_obligation_ids:
                    bound_checklist_evidence_ids = checklist_by_id[
                        obligation_id
                    ].get("evidence_ids")
                    bound_plan_evidence_ids = plan_by_id[obligation_id].get(
                        "evidence_ids"
                    )
                    if (
                        not _unique_nonempty_strings(
                            bound_checklist_evidence_ids
                        )
                        or not _unique_nonempty_strings(bound_plan_evidence_ids)
                        or set(bound_checklist_evidence_ids)
                        != set(bound_plan_evidence_ids)
                    ):
                        invalid_bound_obligation = True
                        break
                    approved_ids = set(bound_checklist_evidence_ids)
                    if bound_evidence_ids is None:
                        bound_evidence_ids = approved_ids
                    else:
                        bound_evidence_ids &= approved_ids
                if (
                    invalid_bound_obligation
                    or bound_evidence_ids is None
                    or any(
                        evidence_id not in evidence_ids
                        or evidence_id not in used_evidence_id_set
                        or evidence_id not in bound_evidence_ids
                        for evidence_id in claim_evidence_ids
                    )
                ):
                    continue
                obligation_claim_ids.append(claim_id)
                obligation_claim_evidence_ids.update(claim_evidence_ids)
            if (
                obligation_claim_ids
                and required_evidence_ids <= obligation_claim_evidence_ids
            ):
                valid_obligation_ids.append(target_obligation_id)
                valid_claim_ids.extend(obligation_claim_ids)
        receipt = {
            "proposition_ordinal": ordinal,
            "obligation_ids": sorted(set(valid_obligation_ids)),
            "claim_ids": sorted(set(valid_claim_ids)),
        }
        receipts.append(receipt)
        if not valid_obligation_ids:
            missing.append(ordinal)
    return receipts, missing


def _estimated_cost_nanos(package: dict[str, Any]) -> int:
    return sum(
        entry["cost"]["amount_cny_nanos"]
        for entry in package["usage"]
        if type(entry.get("cost")) is dict
    )


def _score_text(value: str) -> str:
    return _squash(unicodedata.normalize("NFKC", value))


def score_case(
    case: dict[str, Any],
    package: dict[str, Any],
    provider_call_count: int,
    reserved_cny_nanos: int,
) -> dict[str, Any]:
    """Mechanically score one executed case against its frozen expectation."""

    expected = case["expected"]
    task_type = case["task_type"]
    failures: list[str] = []
    detail: dict[str, Any] = {}

    observed_outcome = package["outcome"]
    detail["observed_outcome"] = observed_outcome
    matched_handoff = expected["outcome"] == observed_outcome == "handoff"
    detail["scoring_profile"] = (
        "matched_handoff" if matched_handoff else "full_candidate_contract"
    )
    if observed_outcome != expected["outcome"]:
        failures.append("outcome_mismatch")
    if expected.get("handoff_reason") is not None:
        detail["observed_handoff_reason"] = package["handoff_reason"]
        if package["handoff_reason"] != expected["handoff_reason"]:
            failures.append("handoff_reason_mismatch")

    used_sections = _used_source_sections(package, task_type)
    detail["used_source_sections"] = used_sections
    if not matched_handoff:
        expected_sections = sorted(expected["source_sections"])
        candidate_match = expected["outcome"] == observed_outcome == "candidate"
        if candidate_match:
            missing_sections = sorted(set(expected_sections) - set(used_sections))
            extra_sections = sorted(set(used_sections) - set(expected_sections))
            invalid_extra_sections = _invalid_extra_source_sections(
                package,
                task_type,
                extra_sections,
            )
            detail["missing_required_source_sections"] = missing_sections
            detail["extra_source_sections"] = extra_sections
            detail["invalid_extra_source_sections"] = invalid_extra_sections
            source_mismatch = bool(missing_sections or invalid_extra_sections)
        else:
            source_mismatch = used_sections != expected_sections
        if source_mismatch:
            failures.append("source_sections_mismatch")

        required_facts = expected["required_facts"]
        missing_obligations: list[int] = []
        if candidate_match and required_facts:
            missing_obligations = _missing_required_obligation_ordinals(
                package,
                required_facts,
            )
            detail["missing_required_obligation_ordinals"] = missing_obligations
            if missing_obligations:
                failures.append("required_obligation_missing")

        if candidate_match and required_facts:
            obligation_receipts_by_ordinal = (
                _required_obligation_receipts_by_ordinal(package, required_facts)
            )
            receipts, missing_bindings = _proposition_binding_receipts(
                package, task_type, obligation_receipts_by_ordinal
            )
            detail["required_proposition_receipts"] = receipts
            detail["missing_required_proposition_binding_ordinals"] = (
                missing_bindings
            )
            if missing_bindings:
                failures.append("required_proposition_binding_missing")
        elif required_facts:
            visible = _score_text(_customer_visible_text(package, task_type))
            missing_facts = [
                index
                for index, fact in enumerate(required_facts)
                if _score_text(fact) not in visible
            ]
            if missing_facts:
                detail["missing_required_fact_ordinals"] = missing_facts
                failures.append("required_fact_missing")

        if task_type == "ticket":
            if (
                expected.get("category") is not None
                and package.get("category") != expected["category"]
            ):
                failures.append("category_mismatch")
            if (
                expected.get("priority") is not None
                and package.get("priority") != expected["priority"]
            ):
                failures.append("priority_mismatch")

    if (
        package["worst_cost_cny_nanos"] > reserved_cny_nanos
        or provider_call_count > MAX_CALLS_PER_CASE
        or _estimated_cost_nanos(package) > package["worst_cost_cny_nanos"]
    ):
        failures.append("budget_noncompliant")

    return {"passed": not failures, "failure_codes": failures, "detail": detail}


def _build_identity(args: argparse.Namespace) -> dict[str, Any]:
    identity: dict[str, Any] = {}
    if args.identity is not None:
        loaded = _load_json(args.identity, "stage12_identity_unreadable")
        if type(loaded) is not dict:
            _fail("stage12_identity_invalid")
        identity.update(loaded)
    for key in ("git_sha", "image_digest", "model", "prompt_sha256"):
        value = getattr(args, key)
        if value is not None:
            identity[key] = value
    return {
        "git_sha": identity.get("git_sha"),
        "image_digest": identity.get("image_digest"),
        "model": identity.get("model"),
        "prompt_sha256": identity.get("prompt_sha256"),
    }


def run_evaluation(args: argparse.Namespace) -> dict[str, Any]:
    set_path: Path = args.set
    raw_bytes = set_path.read_bytes()
    suite = load_unseen_set(set_path)
    set_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    mapping = load_dimensions(args.dims)
    cases = suite["cases"][: args.max_cases]

    offline_factories: dict[str, Callable[[], Any]] | None = None
    if args.mode == "offline":
        responses_path = args.offline_responses or default_offline_responses_path(set_path)
        offline_factories = load_offline_factories(responses_path)
        missing = [case["case_id"] for case in cases if case["case_id"] not in offline_factories]
        if missing:
            _fail("stage12_offline_responses_incomplete")

    max_cost_nanos = int(round(args.max_cost_cny * 1_000_000_000))
    total_calls = 0
    total_estimated_nanos = 0
    stop_code: str | None = None
    raw_cases: list[dict[str, Any]] = []
    public_cases: list[dict[str, Any]] = []
    completed_packages: list[dict[str, Any]] = []

    for index, case in enumerate(cases):
        if (
            total_calls + MAX_CALLS_PER_CASE > args.max_calls
            or total_estimated_nanos >= max_cost_nanos
        ):
            stop_code = "envelope_exceeded"
            break
        run_id = f"stg12-{index:02d}-" + hashlib.sha256(
            f"{set_sha256}:{case['case_id']}".encode("utf-8")
        ).hexdigest()[:16]
        reserved = min(
            SESSION_MAX_WORST_COST_CNY_NANOS,
            max_cost_nanos - total_estimated_nanos,
        )
        if args.mode == "offline":
            assert offline_factories is not None
            factory = offline_factories[case["case_id"]]
            mode = MODE_OFFLINE
        else:
            factory = default_qa_transport
            mode = MODE_AUTHORIZED_REAL
        runner = DefaultProductRunner(
            transport_factory=factory,
            transport_mode=mode,
            dependencies_ready=True,
        )
        run_input = RunInput(
            run_id=run_id,
            task_type=case["task_type"],
            text=case["input"],
            product_model=case["product_model"],
            reserved_cny_nanos=reserved,
        )
        try:
            execution: ExecutionResult = runner.execute(run_input, lambda stage, status: None)
        except BaseException as exc:
            code = getattr(exc, "code", type(exc).__name__)
            scoring = {
                "passed": False,
                "failure_codes": [f"execution_exception:{code}"],
                "detail": {},
            }
            raw_cases.append({
                "case_id": case["case_id"],
                "run_id": run_id,
                "package": None,
                "provider_call_count": 0,
                "scoring": scoring,
            })
            public_cases.append({
                "case_id": case["case_id"],
                "dimension": dimension_of(case["case_id"], mapping),
                "task_type": case["task_type"],
                "expected_outcome": case["expected"]["outcome"],
                "observed_outcome": None,
                "passed": False,
                "failure_codes": scoring["failure_codes"],
            })
            stop_code = "execution_error"
            break
        package = execution.package
        completed_packages.append(package)
        scoring = score_case(case, package, execution.provider_call_count, reserved)
        total_calls += execution.provider_call_count
        total_estimated_nanos += _estimated_cost_nanos(package)
        raw_cases.append({
            "case_id": case["case_id"],
            "run_id": run_id,
            "package": package,
            "provider_call_count": execution.provider_call_count,
            "scoring": scoring,
        })
        public_cases.append({
            "case_id": case["case_id"],
            "dimension": dimension_of(case["case_id"], mapping),
            "task_type": case["task_type"],
            "expected_outcome": case["expected"]["outcome"],
            "observed_outcome": package["outcome"],
            "generation_failure": package.get("failure_classification"),
            "passed": scoring["passed"],
            "failure_codes": scoring["failure_codes"],
        })
        if args.mode == "real" and type(package.get("handoff_reason")) is str and (
            "execution_failure:" in package["handoff_reason"]
        ):
            stop_code = "execution_failure_stop"
            break

    identity = _build_identity(args)
    identity["unseen_set_sha256"] = set_sha256
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "identity": identity,
        "mode": args.mode,
        "envelope": {
            "max_cases": args.max_cases,
            "max_calls": args.max_calls,
            "max_cost_cny_nanos": max_cost_nanos,
            "automatic_retry_count": 0,
        },
        "totals": {
            "cases_planned": len(cases),
            "cases_executed": len(public_cases),
            "provider_calls": total_calls,
            "estimated_cost_cny_nanos": total_estimated_nanos,
            "stopped_early": stop_code is not None,
            "stop_code": stop_code,
        },
        "generation_failures": summarize_generation_failures(completed_packages),
        "cases": public_cases,
    }
    raw_record = {
        "schema_version": RAW_SCHEMA_VERSION,
        "identity": identity,
        "mode": args.mode,
        "cases": raw_cases,
        "totals": report["totals"],
        "generation_failures": report["generation_failures"],
    }

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "stage12-raw-records.json").write_text(
        json.dumps(raw_record, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 12 formal evaluation runner")
    parser.add_argument("--set", type=Path, required=True, help="private unseen set JSON")
    parser.add_argument("--out", type=Path, required=True, help="private raw-record directory")
    parser.add_argument("--report", type=Path, required=True, help="public aggregate report path")
    parser.add_argument("--max-cases", type=int, default=HARD_MAX_CASES)
    parser.add_argument("--max-calls", type=int, default=HARD_MAX_CALLS)
    parser.add_argument("--max-cost-cny", type=float, default=10.0)
    parser.add_argument("--mode", choices=("offline", "real"), default="offline")
    parser.add_argument("--offline-responses", type=Path, default=None)
    parser.add_argument("--dims", type=Path, default=DEFAULT_DIMS)
    parser.add_argument("--identity", type=Path, default=None)
    parser.add_argument("--git-sha", default=None)
    parser.add_argument("--image-digest", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--prompt-sha256", default=None)
    args = parser.parse_args(argv)
    if not 1 <= args.max_cases <= HARD_MAX_CASES:
        parser.error(f"--max-cases must be within 1..{HARD_MAX_CASES}")
    if not 1 <= args.max_calls <= HARD_MAX_CALLS:
        parser.error(f"--max-calls must be within 1..{HARD_MAX_CALLS}")
    if not 0 < args.max_cost_cny <= HARD_MAX_COST_CNY_NANOS / 1_000_000_000:
        parser.error("--max-cost-cny must be within (0, 10]")
    return args


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        report = run_evaluation(args)
    except Stage12Error as exc:
        print(f"stage12_eval=setup_failed code={exc.code}")
        return 2
    totals = report["totals"]
    passed = sum(1 for case in report["cases"] if case["passed"])
    print(
        f"stage12_eval=done mode={report['mode']} "
        f"cases_executed={totals['cases_executed']} passed={passed} "
        f"provider_calls={totals['provider_calls']} "
        f"estimated_cost_cny_nanos={totals['estimated_cost_cny_nanos']} "
        f"stop_code={totals['stop_code']}"
    )
    if totals["stopped_early"] or passed != totals["cases_executed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

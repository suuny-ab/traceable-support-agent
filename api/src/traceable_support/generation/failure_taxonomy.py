"""Stable, privacy-safe classification for two-stage generation failures."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

FAILURE_CLASSIFICATION_SCHEMA_VERSION = "generation-failure-classification-v1"
FAILURE_SUMMARY_SCHEMA_VERSION = "generation-failure-summary-v1"

_PHASES = {
    "enumeration_execution_failure": "enumeration_execution",
    "enumeration_contract_failure": "enumeration_contract",
    "generation_execution_failure": "generation_execution",
    "generation_contract_failure": "generation_contract",
    "completeness_gate_failed": "completeness_gate",
}

_FAMILIES = {
    "provider_response_envelope_invalid": "provider_response_envelope",
    "two_step_checklist_invalid": "checklist_shape",
    "two_step_checklist_result_shape_invalid": "checklist_shape",
    "two_step_checklist_identity_invalid": "checklist_shape",
    "two_step_checklist_obligation_count_invalid": "checklist_shape",
    "two_step_checklist_obligations_type_invalid": "checklist_shape",
    "two_step_checklist_obligation_count_empty": "checklist_shape",
    "two_step_checklist_obligation_count_exceeded": "checklist_shape",
    "two_step_checklist_obligation_shape_invalid": "checklist_shape",
    "two_step_checklist_obligation_identity_invalid": "checklist_shape",
    "two_step_checklist_clause_ids_invalid": "checklist_binding",
    "two_step_checklist_key_elements_invalid": "checklist_binding",
    "two_step_checklist_too_large": "checklist_shape",
    "two_step_checklist_partition_invalid": "checklist_partition",
    "two_step_checklist_partition_incomplete": "checklist_partition",
    "top10_v4_obligation_binding_invalid": "obligation_binding",
    "ticket_obligation_binding_invalid": "obligation_binding",
    "completeness_gate_failed": "completeness",
}


def classify_generation_failure(reason: Any) -> dict[str, str] | None:
    """Classify a stable handoff reason without inspecting Provider content."""

    if reason is None:
        return None
    if type(reason) is not str or not reason:
        raise ValueError("generation_failure_reason_invalid")
    prefix, separator, detail = reason.partition(":")
    code = detail if separator else prefix
    phase = _PHASES.get(prefix, "other")
    family = _FAMILIES.get(code)
    if family is None:
        if code.startswith("provider_response_"):
            family = "provider_response_envelope"
        elif code.startswith("provider_"):
            family = "provider_execution"
        elif code.startswith("two_step_checklist_"):
            family = "checklist_contract"
        elif "obligation" in code and "binding" in code:
            family = "obligation_binding"
        elif code.endswith("_content_invalid") or code.endswith("_shape_invalid"):
            family = "generation_shape"
        else:
            family = "other"
    return {
        "schema_version": FAILURE_CLASSIFICATION_SCHEMA_VERSION,
        "phase": phase,
        "family": family,
        "code": code,
    }


def summarize_generation_failures(
    packages: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate only stable classifications; never include prompts or content."""

    phases: Counter[str] = Counter()
    families: Counter[str] = Counter()
    codes: Counter[str] = Counter()
    package_count = 0
    failure_count = 0
    for package in packages:
        if type(package) is not dict:
            raise ValueError("generation_failure_package_invalid")
        package_count += 1
        classification = classify_generation_failure(package.get("handoff_reason"))
        if classification is None or classification["phase"] == "other":
            continue
        failure_count += 1
        phases[classification["phase"]] += 1
        families[classification["family"]] += 1
        codes[classification["code"]] += 1
    return {
        "schema_version": FAILURE_SUMMARY_SCHEMA_VERSION,
        "packages": package_count,
        "failures": failure_count,
        "phases": dict(sorted(phases.items())),
        "families": dict(sorted(families.items())),
        "codes": dict(sorted(codes.items())),
    }


__all__ = [
    "FAILURE_CLASSIFICATION_SCHEMA_VERSION",
    "FAILURE_SUMMARY_SCHEMA_VERSION",
    "classify_generation_failure",
    "summarize_generation_failures",
]

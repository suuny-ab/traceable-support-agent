"""Deterministic business boundaries that must run before Provider construction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class BoundaryDecision:
    """A source-backed reason why generation must fail closed."""

    reason: str
    rule_id: str
    source_sections: tuple[str, ...]
    ticket_category: str
    ticket_priority: str


_DIRECT_SAFETY_TERMS = (
    "异常发热",
    "冒烟",
    "起火",
    "触电",
    "进液",
    "进水",
)
_LIQUID_INCIDENT_PATTERNS = (
    re.compile(r"(?:吸进|吸入|吸了|吸到|吸取了).{0,8}(?:水|液体|积水)"),
    re.compile(r"(?:水|液体|积水).{0,8}(?:吸进|吸入|进入|进了)"),
)
_CZ_R2_DUST_STATION_TERMS = (
    "自动集尘",
    "集尘袋",
    "进尘口",
    "e310",
)


def _compact(text: str) -> str:
    return "".join(text.casefold().split())


def is_safety_hazard(text: str) -> bool:
    """Recognize only incident signals covered by the public synthetic SOP."""

    compact = _compact(text)
    return any(term in compact for term in _DIRECT_SAFETY_TERMS) or any(
        pattern.search(compact) for pattern in _LIQUID_INCIDENT_PATTERNS
    )


def evaluate_generation_boundary(
    text: str, product_model: str | None
) -> BoundaryDecision | None:
    """Return the first business boundary that requires deterministic handoff."""

    if is_safety_hazard(text):
        return BoundaryDecision(
            reason="safety_risk",
            rule_id="synthetic_sop_manual_escalation",
            source_sections=(
                "COMMON-FAQ/wet-environment",
                "CUSTOMER-SERVICE-SOP/manual-escalation",
            ),
            ticket_category="安全风险",
            ticket_priority="P0-紧急",
        )

    compact = _compact(text)
    if product_model == "CZ-R1" and any(
        term in compact for term in _CZ_R2_DUST_STATION_TERMS
    ):
        return BoundaryDecision(
            reason="model_scope_conflict",
            rule_id="cz_r2_dust_station_not_available_on_cz_r1",
            source_sections=(
                "COMMON-FAQ/model-difference",
                "CZ-R2-MANUAL/auto-empty",
            ),
            ticket_category="使用咨询",
            ticket_priority="P2-普通",
        )
    return None


def build_boundary_handoff_package(
    *,
    task_type: str,
    text: str,
    product_model: str,
    run_id: str,
    decision: BoundaryDecision,
    ticket: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an auditable zero-call package shared by direct and runner paths."""

    package: dict[str, Any] = {
        "schema_version": "product-boundary-handoff-v1",
        "question": text,
        "product_model": product_model,
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence": [],
        "boundary_sources": list(decision.source_sections),
        "checklist": None,
        "acknowledged_context": [],
        "context_corrections": [],
        "gates": {
            "pre_generation_boundary": {
                "pass": False,
                "reason": decision.reason,
                "rule_id": decision.rule_id,
            }
        },
        "usage": [],
        "worst_cost_cny_nanos": 0,
        "stages": [
            {
                "stage": "preflight",
                "status": "failed",
                "at": datetime.now(timezone.utc).isoformat(),
            }
        ],
        "outcome": "handoff",
        "handoff_reason": decision.reason,
    }
    if task_type == "qa":
        package["answer"] = None
    elif task_type == "ticket":
        ticket = ticket or {}
        package.update(
            {
                "ticket_id": ticket.get("ticket_id", f"BOUNDARY-{run_id}"),
                "category": decision.ticket_category,
                "priority": decision.ticket_priority,
                "proposal": None,
            }
        )
    else:
        raise ValueError("product_task_type_invalid")
    return package


__all__ = [
    "BoundaryDecision",
    "build_boundary_handoff_package",
    "evaluate_generation_boundary",
    "is_safety_hazard",
]

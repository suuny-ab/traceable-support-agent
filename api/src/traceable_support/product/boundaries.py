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
_MODEL_MENTION_PATTERNS = {
    "CZ-R1": re.compile(r"(?<![a-z0-9])(?:cz-?r1|r1)(?![a-z0-9])"),
    "CZ-R2": re.compile(r"(?<![a-z0-9])(?:cz-?r2|r2)(?![a-z0-9])"),
}
_DUST_STATION_HARD_OPERATION_MARKERS = (
    "更换",
    "清理",
    "安装",
    "拆卸",
    "开启",
    "启动",
    "设置",
    "重置",
    "维修",
    "处理",
    "故障",
    "报错",
    "报警",
    "报e310",
    "满了",
    "堵塞",
    "堵了",
    "橙灯",
    "红灯",
    "恢复",
    "测试",
    "连续",
    "触发",
    "失灵",
    "坏了",
    "怎么办",
)
_DUST_STATION_INFORMATION_PATTERNS = (
    re.compile(r"(?:有没有|是否有|是否支持|支不支持|能否|能不能|具备不具备|"
               r"可以|可不可以|会不会)"
               r".{0,12}(?:自动集尘|集尘袋|进尘口|e310)"),
    re.compile(r"(?:自动集尘|集尘袋|进尘口|e310).{0,12}"
               r"(?:有没有|是否有|是否支持|支持吗|能否|能不能|具备吗|有吗|"
               r"可以吗|可不可以|会不会|会吗)"),
    re.compile(r"(?:区别|差异|不同|为什么.{0,16}(?:没有|不支持))"),
)
_DUST_STATION_GENERIC_OPERATION_MARKERS = ("怎么", "怎样", "如何", "使用", "操作")


def _compact(text: str) -> str:
    return "".join(text.casefold().split())


def is_safety_hazard(text: str) -> bool:
    """Recognize only incident signals covered by the public synthetic SOP."""

    compact = _compact(text)
    return any(term in compact for term in _DIRECT_SAFETY_TERMS) or any(
        pattern.search(compact) for pattern in _LIQUID_INCIDENT_PATTERNS
    )


def _mentioned_models(compact: str) -> set[str]:
    return {
        model
        for model, pattern in _MODEL_MENTION_PATTERNS.items()
        if pattern.search(compact)
    }


def _is_dust_station_information_question(compact: str) -> bool:
    if any(marker in compact for marker in _DUST_STATION_HARD_OPERATION_MARKERS):
        return False
    if any(pattern.search(compact) for pattern in _DUST_STATION_INFORMATION_PATTERNS):
        return True
    return not any(
        marker in compact for marker in _DUST_STATION_GENERIC_OPERATION_MARKERS
    ) and any(marker in compact for marker in ("区别", "差异", "不同"))


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
    mentioned_models = _mentioned_models(compact)
    if (
        product_model in _MODEL_MENTION_PATTERNS
        and len(mentioned_models) == 1
        and product_model not in mentioned_models
    ):
        return BoundaryDecision(
            reason="model_scope_conflict",
            rule_id="selected_model_conflicts_with_explicit_text_model",
            source_sections=(
                "COMMON-FAQ/model-difference",
                "CUSTOMER-SERVICE-SOP/intake-fields",
            ),
            ticket_category="使用咨询",
            ticket_priority="P2-普通",
        )

    if (
        (product_model == "CZ-R1" or "CZ-R1" in mentioned_models)
        and any(term in compact for term in _CZ_R2_DUST_STATION_TERMS)
        and not _is_dust_station_information_question(compact)
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

"""Deterministic business boundaries that must run before Provider construction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class BoundaryDecision:
    """A source-backed reason why generation must fail closed."""

    handoff_type: str
    reason: str
    rule_id: str
    source_sections: tuple[str, ...]
    ticket_category: str
    ticket_priority: str
    guidance: tuple[str, ...]


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
_CZ_R2_WET_CLEANING_TERMS = (
    "扫拖",
    "拖地",
    "拖布",
    "清水箱",
)
_MODEL_MENTION_PATTERNS = {
    "CZ-R1": re.compile(r"(?<![a-z0-9])(?:cz-?r1|r1)(?![a-z0-9])"),
    "CZ-R2": re.compile(r"(?<![a-z0-9])(?:cz-?r2|r2)(?![a-z0-9])"),
}
_DUST_STATION_OPERATION_CONTEXT_MARKERS = (
    "怎么",
    "怎样",
    "如何",
    "怎么办",
    "故障",
    "报错",
    "报警",
    "报e310",
    "已满",
    "满了",
    "堵塞",
    "堵了",
    "橙灯",
    "红灯",
    "连续",
    "触发",
    "失灵",
    "坏了",
)
_DUST_STATION_HIGH_RISK_ACTION_MARKERS = (
    "更换",
    "清理",
    "安装",
    "拆卸",
    "重置",
    "维修",
    "处理",
    "恢复",
    "测试",
)
_DUST_STATION_AMBIGUOUS_ACTION_MARKERS = (
    "开启",
    "启动",
    "设置",
    "使用",
    "操作",
)
_UNSUPPORTED_CAPABILITY_PATTERNS = (
    re.compile(r"2\.4g(?:hz)?"),
    re.compile(r"(?<![\d.])5g(?:hz)?"),
    re.compile(r"(?:wi-?fi|无线).{0,12}(?:频段|双频)"),
)
_CZ_R2_AUTO_RESUME_PATTERNS = (
    re.compile(r"(?:自动|断点|回充后|充电后|充满后).{0,8}(?:续扫|继续(?:清扫|任务)?)"),
    re.compile(r"(?:续扫|继续(?:清扫|任务)?).{0,8}(?:自动|回充|充电|充满)"),
)
_CHARGING_CONTEXT_TERMS = ("低电", "没电", "电量", "电池", "回充", "充电", "充满", "补电")
_CONTINUE_TASK_TERMS = ("续扫", "继续", "接着", "恢复", "再次", "重新", "中断")
_AUTOMATIC_BEHAVIOR_TERMS = ("自动", "自己", "自行")
_VOICE_CONTROL_PATTERNS = (
    re.compile(r"(?:语音助手|智能音箱|语音音箱|小爱|天猫精灵|siri)"),
    re.compile(r"(?:语音|音箱).{0,10}(?:控制|接入|联动|支持)"),
    re.compile(r"(?:控制|接入|联动|支持).{0,10}(?:语音|音箱)"),
)
_AFTER_SALES_ACTION_RULES = (
    (
        "after_sales_replacement_requires_human",
        ("换新", "退货", "更换整机", "替换整机"),
        ("AFTER-SALES-POLICY/replacement", "CUSTOMER-SERVICE-SOP/manual-escalation"),
    ),
    (
        "after_sales_refund_requires_human",
        ("退款", "退回款项", "原路退回"),
        ("AFTER-SALES-POLICY/replacement", "CUSTOMER-SERVICE-SOP/manual-escalation"),
    ),
    (
        "after_sales_repair_requires_human",
        ("维修", "寄修", "报修", "检修", "修理", "上门维修", "安排维修", "预约维修"),
        ("AFTER-SALES-POLICY/repair", "CUSTOMER-SERVICE-SOP/manual-escalation"),
    ),
)
_HUMAN_ACTION_MARKERS = (
    "直接",
    "立即",
    "马上",
    "帮我",
    "请你",
    "替我",
    "已经",
    "已同意",
    "已完成",
    "完成",
    "承诺",
    "确认",
    "安排",
    "执行",
)
_HUMAN_ACTION_NEGATIONS = (
    "不要安排",
    "不安排",
    "不要执行",
    "不执行",
    "交人工决定",
    "待人工决定",
    "待人工审核",
)
_REPAIR_EXECUTION_TERMS = (
    "提交",
    "登记",
    "预约",
    "安排",
    "联系",
    "派人",
    "寄修",
    "报修",
    "上门",
)
_REPAIR_COMPLETION_PATTERNS = (
    re.compile(r"(?:已经|已|完成).{0,6}维修"),
    re.compile(r"维修.{0,6}(?:完成|已完成)"),
)
_DUST_STATION_INFORMATION_PATTERNS = (
    re.compile(r"(?:有没有|是否有|是否支持|支不支持|能否|能不能|具备不具备|"
               r"可以|可不可以|会不会)"
               r".{0,12}(?:自动集尘|集尘袋|进尘口|e310)"),
    re.compile(r"(?:自动集尘|集尘袋|进尘口|e310).{0,12}"
               r"(?:有没有|是否有|是否支持|支持吗|能否|能不能|具备吗|有吗|"
               r"可以吗|可不可以|会不会|会吗)"),
    re.compile(r"(?:自动集尘|集尘袋|进尘口|e310).{0,12}"
               r"(?:可以|能|会).{0,6}(?:吗|么|[?？]|$)"),
    re.compile(r"(?:区别|差异|不同|为什么.{0,16}(?:没有|不支持))"),
)


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
    if any(marker in compact for marker in _DUST_STATION_OPERATION_CONTEXT_MARKERS):
        return False
    if any(marker in compact for marker in _DUST_STATION_HIGH_RISK_ACTION_MARKERS):
        return False
    if any(pattern.search(compact) for pattern in _DUST_STATION_INFORMATION_PATTERNS):
        return True
    if any(marker in compact for marker in _DUST_STATION_AMBIGUOUS_ACTION_MARKERS):
        return False
    return any(marker in compact for marker in ("区别", "差异", "不同"))


def _after_sales_action_boundary(compact: str) -> tuple[str, tuple[str, ...]] | None:
    if any(marker in compact for marker in _HUMAN_ACTION_NEGATIONS):
        return None
    if not any(marker in compact for marker in _HUMAN_ACTION_MARKERS):
        return None
    for rule_id, action_terms, source_sections in _AFTER_SALES_ACTION_RULES:
        if any(term in compact for term in action_terms):
            if rule_id == "after_sales_repair_requires_human" and not (
                any(term in compact for term in _REPAIR_EXECUTION_TERMS)
                or any(pattern.search(compact) for pattern in _REPAIR_COMPLETION_PATTERNS)
            ):
                continue
            return rule_id, source_sections
    return None


def evaluate_generation_boundary(
    text: str,
    product_model: str | None,
    *,
    task_type: str | None = None,
) -> BoundaryDecision | None:
    """Return the first business boundary that requires deterministic handoff."""

    if is_safety_hazard(text):
        return BoundaryDecision(
            handoff_type="safety",
            reason="safety_risk",
            rule_id="synthetic_sop_manual_escalation",
            source_sections=(
                "COMMON-FAQ/wet-environment",
                "CUSTOMER-SERVICE-SOP/manual-escalation",
            ),
            ticket_category="安全风险",
            ticket_priority="P0-紧急",
            guidance=(
                "停止继续操作设备",
                "由人工核对安全事件与后续处置",
            ),
        )

    compact = _compact(text)
    mentioned_models = _mentioned_models(compact)
    if (
        product_model in _MODEL_MENTION_PATTERNS
        and len(mentioned_models) == 1
        and product_model not in mentioned_models
    ):
        return BoundaryDecision(
            handoff_type="model_scope",
            reason="model_scope_conflict",
            rule_id="selected_model_conflicts_with_explicit_text_model",
            source_sections=(
                "COMMON-FAQ/model-difference",
                "CUSTOMER-SERVICE-SOP/intake-fields",
            ),
            ticket_category="使用咨询",
            ticket_priority="P2-普通",
            guidance=(
                "核对选择型号与文本型号",
                "不得混用另一型号的能力或步骤",
            ),
        )

    if product_model == "CZ-R1" and any(
        term in compact for term in _CZ_R2_WET_CLEANING_TERMS
    ):
        return BoundaryDecision(
            handoff_type="model_scope",
            reason="model_scope_conflict",
            rule_id="cz_r2_wet_cleaning_not_available_on_cz_r1",
            source_sections=(
                "COMMON-FAQ/model-difference",
                "CZ-R2-MANUAL/vacuum-and-mop",
            ),
            ticket_category="使用咨询",
            ticket_priority="P2-普通",
            guidance=(
                "核对客户实际型号",
                "不得用 CZ-R2 扫拖能力补写 CZ-R1 答案",
            ),
        )

    if (
        (product_model == "CZ-R1" or "CZ-R1" in mentioned_models)
        and any(term in compact for term in _CZ_R2_DUST_STATION_TERMS)
        and not _is_dust_station_information_question(compact)
    ):
        return BoundaryDecision(
            handoff_type="model_scope",
            reason="model_scope_conflict",
            rule_id="cz_r2_dust_station_not_available_on_cz_r1",
            source_sections=(
                "COMMON-FAQ/model-difference",
                "CZ-R2-MANUAL/auto-empty",
            ),
            ticket_category="使用咨询",
            ticket_priority="P2-普通",
            guidance=(
                "核对客户实际型号",
                "不得用 CZ-R2 基站步骤处理 CZ-R1",
            ),
        )
    if product_model == "CZ-R2" and (
        any(pattern.search(compact) for pattern in _CZ_R2_AUTO_RESUME_PATTERNS)
        or (
            any(term in compact for term in _AUTOMATIC_BEHAVIOR_TERMS)
            and any(term in compact for term in _CHARGING_CONTEXT_TERMS)
            and any(term in compact for term in _CONTINUE_TASK_TERMS)
        )
    ):
        return BoundaryDecision(
            handoff_type="evidence_gap",
            reason="unsupported_claim",
            rule_id="cz_r2_auto_resume_not_covered",
            source_sections=(),
            ticket_category="使用咨询",
            ticket_priority="P2-普通",
            guidance=(
                "核对 CZ-R2 的批准规格",
                "不得从 CZ-R1 的否定事实反推 CZ-R2 能力",
            ),
        )
    if any(pattern.search(compact) for pattern in _VOICE_CONTROL_PATTERNS):
        return BoundaryDecision(
            handoff_type="evidence_gap",
            reason="unsupported_claim",
            rule_id="voice_control_not_covered",
            source_sections=(),
            ticket_category="使用咨询",
            ticket_priority="P2-普通",
            guidance=(
                "核对批准的连接与语音控制规格",
                "资料未登记时不得肯定或否定猜测",
            ),
        )
    if any(pattern.search(compact) for pattern in _UNSUPPORTED_CAPABILITY_PATTERNS):
        return BoundaryDecision(
            handoff_type="evidence_gap",
            reason="unsupported_claim",
            rule_id="capability_not_covered_by_approved_sources",
            source_sections=(),
            ticket_category="使用咨询",
            ticket_priority="P2-普通",
            guidance=(
                "核对批准的产品规格",
                "资料未覆盖时不得猜测能力结论",
            ),
        )
    after_sales_action = (
        _after_sales_action_boundary(compact) if task_type == "ticket" else None
    )
    if after_sales_action is not None:
        rule_id, source_sections = after_sales_action
        return BoundaryDecision(
            handoff_type="human_authority",
            reason="after_sales_commitment",
            rule_id=rule_id,
            source_sections=source_sections,
            ticket_category="售后申请",
            ticket_priority="P1-高",
            guidance=(
                "记录合成证据并交人工审核",
                "不得声称退款、换新、维修或寄出已经完成",
            ),
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
        "handoff_type": decision.handoff_type,
        "handoff_guidance": list(decision.guidance),
        "checklist": None,
        "acknowledged_context": [],
        "context_corrections": [],
        "gates": {
            "pre_generation_boundary": {
                "pass": False,
                "reason": decision.reason,
                "rule_id": decision.rule_id,
                "handoff_type": decision.handoff_type,
                "guidance": list(decision.guidance),
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

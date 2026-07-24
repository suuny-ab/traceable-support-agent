"""Two independent deterministic ticket-classification tools."""

from __future__ import annotations

from typing import Any

from .boundaries import is_safety_hazard
from .classification import TICKET_INPUT_SCHEMA, validate_ticket_input


class CategoryTool:
    name = "category_classifier"
    version = "category-rules-1.0"
    input_schema = TICKET_INPUT_SCHEMA
    output_schema = {
        "type": "object",
        "required": ["category", "reason_code"],
        "properties": {
            "category": {"type": "string", "enum": ["故障排查", "使用咨询", "安全风险", "售后申请"]},
            "reason_code": {"type": "string", "pattern": "^[a-z0-9_]{3,64}$"},
        },
        "additionalProperties": False,
    }

    def execute(self, ticket: dict[str, Any]) -> dict[str, str]:
        validated = validate_ticket_input(ticket)
        text = validated["issue_description"]
        if is_safety_hazard(text):
            return {"category": "安全风险", "reason_code": "safety_hazard_signal"}
        if any(word in text for word in ("退换", "退款", "保修", "签收", "售后申请")):
            return {"category": "售后申请", "reason_code": "after_sales_request"}
        if any(word in text for word in ("怎样拆出尘盒", "清理滤网", "怎么使用", "如何使用", "自动续扫", "低电回充")):
            return {"category": "使用咨询", "reason_code": "usage_or_expected_behavior"}
        if any(word in text for word in ("E101", "E210", "E310", "故障码", "仍不能", "仍亮橙灯")):
            return {"category": "故障排查", "reason_code": "fault_or_unresolved_error"}
        return {"category": "使用咨询", "reason_code": "general_usage_question"}


class PriorityTool:
    name = "priority_classifier"
    version = "priority-rules-1.0"
    input_schema = CategoryTool.input_schema
    output_schema = {
        "type": "object",
        "required": ["priority", "reason_code"],
        "properties": {
            "priority": {"type": "string", "enum": ["P0-紧急", "P1-高", "P2-普通", "P3-低"]},
            "reason_code": {"type": "string", "pattern": "^[a-z0-9_]{3,64}$"},
        },
        "additionalProperties": False,
    }

    def execute(self, ticket: dict[str, Any]) -> dict[str, str]:
        validated = validate_ticket_input(ticket)
        text = validated["issue_description"]
        if is_safety_hazard(text):
            return {"priority": "P0-紧急", "reason_code": "immediate_safety_risk"}
        if any(word in text for word in ("E101", "E210", "E310", "仍不能", "仍亮橙灯", "退换", "退款", "硬件故障")):
            return {"priority": "P1-高", "reason_code": "unresolved_fault_or_after_sales"}
        if any(word in text for word in ("怎样拆出尘盒", "清理滤网", "日常清理", "保养")):
            return {"priority": "P3-低", "reason_code": "routine_how_to"}
        return {"priority": "P2-普通", "reason_code": "standard_service_request"}

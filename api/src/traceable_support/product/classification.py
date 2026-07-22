"""Strict schemas for synthetic ticket inputs and deterministic tool outputs."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any


TICKET_FIELDS = {"ticket_id", "product_model", "issue_description"}
ALLOWED_MODELS = ("CZ-R1", "CZ-R2")
ALLOWED_CATEGORIES = ("故障排查", "使用咨询", "安全风险", "售后申请")
ALLOWED_PRIORITIES = ("P0-紧急", "P1-高", "P2-普通", "P3-低")
TICKET_INPUT_SCHEMA = {
    "type": "object",
    "required": ["ticket_id", "product_model", "issue_description"],
    "properties": {
        "ticket_id": {"type": "string", "pattern": r"^[A-Z0-9][A-Z0-9._-]{2,63}$"},
        "product_model": {"type": "string", "enum": list(ALLOWED_MODELS)},
        "issue_description": {"type": "string", "minLength": 8, "maxLength": 500},
    },
    "additionalProperties": False,
    "data_requirement": "synthetic_only_no_personal_information",
    "pii_filter_scope": "limited_common_identifiers_only",
    "pii_filter_patterns": ["email", "mainland_china_mobile_phone", "china_18_digit_identity_number"],
    "comprehensive_pii_protection": False,
}
TRACE_REQUIRED_FIELDS = [
    "trace_id",
    "ticket_id",
    "call_sequence",
    "tool_name",
    "tool_version",
    "input",
    "raw_output",
    "validation",
    "adopted_output",
    "status",
    "error_code",
    "error_message",
]
TOOL_OUTPUT_SCHEMAS = {
    "category_classifier": {
        "required_fields": ("category", "reason_code"),
        "value_field": "category",
        "allowed_values": ALLOWED_CATEGORIES,
    },
    "priority_classifier": {
        "required_fields": ("priority", "reason_code"),
        "value_field": "priority",
        "allowed_values": ALLOWED_PRIORITIES,
    },
}

TICKET_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{2,63}$")
PII_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "mobile_phone": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "identity_number": re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
}


class SchemaValidationError(ValueError):
    def __init__(self, code: str, message: str, details: list[str] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []

    def as_dict(self) -> dict[str, Any]:
        return {"error_code": self.code, "message": self.message, "details": self.details}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_ticket_input(value: Mapping[str, Any] | Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError("ticket_input_not_object", "工单输入必须是对象")
    fields = set(value)
    if fields != TICKET_FIELDS:
        missing = sorted(TICKET_FIELDS - fields)
        unknown = sorted(fields - TICKET_FIELDS)
        raise SchemaValidationError(
            "ticket_input_fields_invalid",
            "工单字段必须精确匹配 schema",
            [*(f"missing:{item}" for item in missing), *(f"unknown:{item}" for item in unknown)],
        )
    if not all(isinstance(value[field], str) for field in TICKET_FIELDS):
        raise SchemaValidationError("ticket_input_type_invalid", "三个工单字段都必须是字符串")
    ticket = {field: value[field] for field in sorted(TICKET_FIELDS)}
    if not TICKET_ID_PATTERN.fullmatch(ticket["ticket_id"]):
        raise SchemaValidationError("ticket_id_invalid", "ticket_id 格式非法")
    if ticket["product_model"] not in ALLOWED_MODELS:
        raise SchemaValidationError("product_model_invalid", "product_model 必须是 CZ-R1 或 CZ-R2")
    description = ticket["issue_description"]
    if description != description.strip() or not (8 <= len(description) <= 500):
        raise SchemaValidationError(
            "issue_description_invalid", "issue_description 必须为 8 到 500 字且首尾无空白"
        )
    pii_surface = f"{ticket['ticket_id']}\n{description}"
    pii_hits = [name for name, pattern in PII_PATTERNS.items() if pattern.search(pii_surface)]
    if pii_hits:
        raise SchemaValidationError(
            "personal_information_detected",
            "有限常见标识符拦截命中；输入仍必须是合成数据且不得包含个人信息",
            pii_hits,
        )
    return ticket


def validate_tool_output(tool_name: str, raw_output: Any) -> tuple[dict[str, Any], dict[str, str] | None]:
    schema = TOOL_OUTPUT_SCHEMAS.get(tool_name)
    if schema is None:
        validation = {
            "schema_version": "1.0",
            "valid": False,
            "errors": ["unknown_tool_schema"],
        }
        return validation, None
    required = set(schema["required_fields"])
    errors: list[str] = []
    if not isinstance(raw_output, Mapping):
        errors.append("output_not_object")
    else:
        actual = set(raw_output)
        if actual != required:
            errors.extend(f"missing:{item}" for item in sorted(required - actual))
            errors.extend(f"unknown:{item}" for item in sorted(actual - required))
        value = raw_output.get(schema["value_field"])
        if value not in schema["allowed_values"]:
            errors.append(f"{schema['value_field']}_not_allowed")
        reason = raw_output.get("reason_code")
        if not isinstance(reason, str) or not re.fullmatch(r"[a-z0-9_]{3,64}", reason):
            errors.append("reason_code_invalid")
    validation = {
        "schema_version": "1.0",
        "valid": not errors,
        "errors": errors,
    }
    if errors:
        return validation, None
    return validation, {field: str(raw_output[field]) for field in sorted(required)}


def json_safe_diagnostic(value: Any) -> Any:
    try:
        canonical_json(value)
        return value
    except (TypeError, ValueError, OverflowError):
        return {
            "unserializable_type": type(value).__name__,
            "diagnostic": "value_not_json_serializable",
        }

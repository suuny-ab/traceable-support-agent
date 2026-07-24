"""Deterministic public-input checks that run before persistence or Provider use."""

from __future__ import annotations

import re

from traceable_support.product.boundaries import evaluate_generation_boundary

_SENSITIVE_PATTERNS = (
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    re.compile(r"(?<!\d)\d{17}[0-9Xx](?!\d)"),
    re.compile(r"(?<!\d)(?:\d[ -]?){16,19}(?!\d)"),
    re.compile(r"\b(?:sk|ak)-[A-Za-z0-9_-]{12,}\b", re.IGNORECASE),
)
_SENSITIVE_PHRASES = (
    "我的密码是",
    "口令是",
    "身份证号",
    "银行卡号",
    "手机号是",
    "api_key=",
    "api key is",
    "公司机密",
    "生产数据",
    "真实客户",
)
_SUPPORT_INTENTS = (
    "cz-r1",
    "cz-r2",
    "扫地",
    "清扫",
    "拖布",
    "地毯",
    "尘盒",
    "滤网",
    "回充",
    "续扫",
    "轮组",
    "边刷",
    "故障",
    "e101",
    "e210",
    "e310",
    "地图",
    "禁区",
    "水箱",
    "充电座",
    "清洁",
    "卡住",
    "噪音",
    "wi-fi",
    "wifi",
    "功能",
    "使用",
    "如何",
    "怎么",
    "为什么",
    "是否",
    "能否",
    "无法",
    "不能",
    "工单",
    "售后",
    "保修",
    "退换",
    "退款",
)
_OUT_OF_SCOPE_INTENTS = (
    "写诗",
    "一首诗",
    "故事",
    "数学题",
    "算一道",
    "翻译",
    "求职",
    "简历",
    "股票",
    "天气",
    "编程",
    "写代码",
)


def preflight(text: str, product_model: str | None = None) -> str | None:
    """Return a client-safe handoff code or ``None`` for an allowed input."""

    lowered = text.casefold()
    if any(pattern.search(text) for pattern in _SENSITIVE_PATTERNS) or any(
        phrase in lowered for phrase in _SENSITIVE_PHRASES
    ):
        return "sensitive_input_blocked"
    boundary = evaluate_generation_boundary(text, product_model)
    if boundary is not None:
        return boundary.reason
    if any(term in lowered for term in _OUT_OF_SCOPE_INTENTS):
        return "out_of_scope_blocked"
    if not any(term in lowered for term in _SUPPORT_INTENTS):
        return "out_of_scope_blocked"
    return None


__all__ = ["preflight"]

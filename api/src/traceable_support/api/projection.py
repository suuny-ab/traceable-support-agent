"""Projection from internal validated packages to the stable public schema."""

from __future__ import annotations

from typing import Any


def blocked_result(code: str) -> dict[str, Any]:
    if code == "sensitive_input_blocked":
        answer = "检测到可能包含敏感信息，系统已在模型调用前停止，并且不保存这段原文。"
        title = "敏感输入已拦截"
        obligations = ["不调用模型", "不保存敏感原文", "提示改用合成或脱敏信息"]
    elif code == "out_of_scope_blocked":
        answer = "当前体验只支持 CZ-R1 / CZ-R2 合成客服资料范围内的问题，本次未调用模型。"
        title = "问题超出体验范围"
        obligations = ["限定产品范围", "不生成无来源回答", "失败时诚实停止"]
    elif code == "unsupported_claim":
        answer = "批准资料未覆盖该问题涉及的产品能力，系统已在模型调用前停止并转人工核实，不会猜测或补写结论。"
        title = "证据不足 · 转人工"
        obligations = ["不猜测未覆盖的产品能力", "模型调用前停止", "由人工核对批准规格"]
    elif code == "model_scope_conflict":
        answer = "请求涉及当前型号不具备的专属能力，系统已在模型调用前转人工，避免混用另一型号的操作步骤。"
        title = "型号边界已转人工"
        obligations = ["不混用型号步骤", "停止模型生成", "由人工确认产品型号与能力"]
    else:
        answer = "检测到潜在安全风险，系统已在模型调用前转人工。请停止继续操作设备并联系人工支持。"
        title = "安全风险已转人工"
        obligations = ["停止模型生成", "避免继续操作设备", "由人工确认后续处理"]
    return {
        "mode": "handoff",
        "outcome": "handoff",
        "title": title,
        "answer": answer,
        "obligations": obligations,
        "evidence": [],
        "gates": [
            {"label": "输入前置", "pass": False},
            {"label": "Provider 调用", "pass": False},
            {"label": "失败关闭", "pass": True},
        ],
        "note": "该结果由确定性前置规则产生，不是模型输出，也不会触发外部业务动作。",
        "handoff_reason": code,
        "provider_call_count": 0,
    }


def execution_failure_result() -> dict[str, Any]:
    return {
        "mode": "handoff",
        "outcome": "handoff",
        "title": "实时运行已安全停止",
        "answer": "后端未能形成通过机械门的候选，本次已转人工；页面可以继续使用已验证回放。",
        "obligations": ["不伪造成功结果", "不自动重试", "保留回放降级"],
        "evidence": [],
        "gates": [
            {"label": "实时执行", "pass": False},
            {"label": "失败关闭", "pass": True},
        ],
        "note": "系统不会展示未通过合同或来源校验的 Provider 内容。",
        "handoff_reason": "background_execution_error",
        "provider_call_count": None,
    }


def restart_result() -> dict[str, Any]:
    value = execution_failure_result()
    value.update(
        {
            "title": "运行因服务重启而停止",
            "answer": "服务重启后无法证明先前调用阶段，系统没有自动重试，而是将本次运行转人工。",
            "handoff_reason": "service_restarted_no_retry",
            "provider_call_count": None,
        }
    )
    return value


def _evidence_projection(
    package: dict[str, Any], used_ids: set[str]
) -> list[dict[str, str]]:
    projected: list[dict[str, str]] = []
    for item in package.get("evidence") or []:
        evidence_id = item.get("evidence_id")
        if type(evidence_id) is not str or evidence_id not in used_ids:
            continue
        heading = item.get("section_heading")
        document = item.get("document_id")
        text = item.get("text")
        if not all(type(value) is str and value for value in (heading, document, text)):
            continue
        projected.append(
            {
                "id": evidence_id,
                "source": f"{document} · {heading}",
                "text": text,
            }
        )
    return projected


def project_package(
    package: dict[str, Any], *, provider_call_count: int
) -> dict[str, Any]:
    """Project a validated product package into the stable public result shape."""

    task_type = "ticket" if "proposal" in package else "qa"
    checklist = package.get("checklist") or {}
    obligations = [
        item.get("description")
        for item in checklist.get("obligations") or []
        if type(item) is dict and type(item.get("description")) is str
    ]
    candidate = package.get("outcome") == "candidate"
    content: dict[str, Any] = {}
    if task_type == "qa" and type(package.get("answer")) is dict:
        content = package["answer"].get("content") or {}
    if task_type == "ticket" and type(package.get("proposal")) is dict:
        content = package["proposal"].get("content") or {}

    used_ids = {
        value
        for value in (package.get("answer") or package.get("proposal") or {}).get(
            "used_evidence_ids", []
        )
        if type(value) is str
    }
    gates = []
    for label, value in (package.get("gates") or {}).items():
        passed = value == "passed" or (
            type(value) is dict and value.get("pass") is True
        )
        gates.append({"label": str(label).replace("_", " "), "pass": passed})
    if not gates:
        gates = [{"label": "生成合同", "pass": False}]

    if candidate and task_type == "qa":
        answer = (content.get("answer") or {}).get("text")
        action_steps = None
        title = "带来源 QA 候选"
    elif candidate:
        answer = content.get("draft_reply")
        action_steps = content.get("action_steps")
        title = "待人工确认工单建议"
    else:
        answer = "生成结果未通过全部机械门，本次已转人工；未通过的 Provider 内容不会作为客户可见答案展示。"
        action_steps = None
        title = "机械门未通过"

    if type(answer) is not str or not answer:
        answer = "系统没有形成可审批候选，本次已转人工。"
    result = {
        "mode": "live" if candidate and provider_call_count else "handoff",
        "outcome": "candidate" if candidate else "handoff",
        "title": title,
        "answer": answer,
        "obligations": obligations or ["仅展示通过合同与来源校验的内容"],
        "evidence": _evidence_projection(package, used_ids),
        "gates": gates,
        "note": "候选只等待人工批准、编辑或拒绝；系统不会发送回复或改变外部工单。",
        "handoff_reason": package.get("handoff_reason"),
        "provider_call_count": provider_call_count,
    }
    if type(action_steps) is list and all(type(item) is str for item in action_steps):
        result["actionSteps"] = action_steps
    return result


__all__ = [
    "blocked_result",
    "execution_failure_result",
    "project_package",
    "restart_result",
]

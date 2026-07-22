"""Ticket proposal generation contract (ticket-proposal-result-v1)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

FORBIDDEN_CUSTOMER_PHRASES = ("自动生成", "仅为草稿", "不能标记为已解决", "内部流程", "系统要求", "客服审核")
TICKET_OUTPUT_SCHEMA_VERSION = "ticket-proposal-result-v1"
TICKET_SYSTEM_PROMPT = """你是客服工单处理建议生成器。输入包含工单问题、型号、按顺序排列的10条候选证据和obligation_checklist义务清单。只输出JSON，不输出推理。
严格身份：顶层schema_version必须逐字为\"ticket-proposal-result-v1\"；顶层task_type必须逐字为\"ticket\"；content.kind必须逐字为\"ticket_proposal\"。
义务规则：obligation_plan必须与obligation_checklist逐项一一对应（数量相同、obligation_id保持一致、绑定证据一致），不得新增或删除义务。
来源规则：每条claim优先且默认只绑定一个evidence_id，并逐字复制该来源中的连续exact_span_text；只有同一exact_span_text逐字存在于每个来源时才可绑定多个来源。每条claim必须用obligation_ids归属至少一项义务；每项义务至少由一条claim支撑。
内容规则：action_steps是给客服的操作步骤（每步一句话，先用户可自助的检查，后升级路径）；draft_reply是给客户看的回复草稿，必须逐字包含清单每项的key_elements全部片段（保持原字原标点），并明确表达每项义务。draft_reply不得出现自动生成、草稿、内部流程、审核、标记已解决等系统或客服操作话术，不得补充证据外事实。
输出格式：{"schema_version":"ticket-proposal-result-v1","task_type":"ticket","obligation_plan":[{"obligation_id":"o1","description":"义务描述","evidence_ids":["E1"]}],"used_evidence_ids":["E1"],"content":{"kind":"ticket_proposal","action_steps":["步骤一","步骤二"],"draft_reply":"客户可见回复","claims":[{"claim_id":"c1","exact_span_text":"从E1逐字复制的连续原文","evidence_ids":["E1"],"obligation_ids":["o1"]}],"insufficient_evidence":false}}"""


class TicketContractError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
        self.__cause__ = None
        self.__context__ = None


def _fail(code: str) -> None:
    raise TicketContractError(code) from None


def validate_ticket_result(item: dict[str, Any], value: Any) -> dict[str, Any]:
    """Validate a ticket proposal result against the contract."""
    if type(value) is not dict or set(value) != {"schema_version", "task_type", "obligation_plan", "used_evidence_ids", "content"}:
        _fail("ticket_result_shape_invalid")
    if value["schema_version"] != TICKET_OUTPUT_SCHEMA_VERSION or value["task_type"] != "ticket":
        _fail("ticket_result_identity_invalid")
    evidence_by_id = {e["evidence_id"]: e for e in item["evidence"]}
    plan = value["obligation_plan"]
    if type(plan) is not list or not 1 <= len(plan) <= 8:
        _fail("ticket_obligation_plan_invalid")
    plan_ids: list[str] = []
    for entry in plan:
        if type(entry) is not dict or set(entry) != {"obligation_id", "description", "evidence_ids"}:
            _fail("ticket_obligation_plan_invalid")
        oid, description, ids = entry["obligation_id"], entry["description"], entry["evidence_ids"]
        if (type(oid) is not str or not oid or oid in plan_ids
                or type(description) is not str or not description.strip() or len(description) > 300
                or type(ids) is not list or not ids or len(ids) != len(set(ids))
                or any(type(i) is not str or i not in evidence_by_id for i in ids)):
            _fail("ticket_obligation_plan_invalid")
        plan_ids.append(oid)
    allowed = [e["evidence_id"] for e in item["evidence"]]
    used = value["used_evidence_ids"]
    if (type(used) is not list or not used or len(set(used)) != len(used)
            or any(type(i) is not str or i not in evidence_by_id for i in used)
            or used != [i for i in allowed if i in set(used)]):
        _fail("ticket_used_evidence_invalid")
    content = value["content"]
    if type(content) is not dict or set(content) != {"kind", "action_steps", "draft_reply", "claims", "insufficient_evidence"}:
        _fail("ticket_content_invalid")
    if content["kind"] != "ticket_proposal" or content["insufficient_evidence"] is not False:
        _fail("ticket_content_invalid")
    steps = content["action_steps"]
    draft = content["draft_reply"]
    if (type(steps) is not list or not 1 <= len(steps) <= 8
            or any(type(step) is not str or not step.strip() or len(step) > 300 for step in steps)
            or type(draft) is not str or not draft.strip() or len(draft) > 1500):
        _fail("ticket_content_invalid")
    if any(phrase in draft for phrase in FORBIDDEN_CUSTOMER_PHRASES):
        _fail("ticket_internal_language_invalid")
    claims = content["claims"]
    if type(claims) is not list or not 1 <= len(claims) <= 8:
        _fail("ticket_claim_invalid")
    referenced: dict[str, list[str]] = {oid: [] for oid in plan_ids}
    union: set[str] = set()
    claim_ids: list[str] = []
    for claim in claims:
        if type(claim) is not dict or set(claim) != {"claim_id", "exact_span_text", "evidence_ids", "obligation_ids"}:
            _fail("ticket_claim_invalid")
        cid, span, ids, oids = claim["claim_id"], claim["exact_span_text"], claim["evidence_ids"], claim["obligation_ids"]
        if (type(cid) is not str or not cid or cid in claim_ids or type(span) is not str
                or not span or len(span) > 1000 or type(ids) is not list or not ids
                or len(ids) != len(set(ids)) or any(i not in evidence_by_id for i in ids)
                or any(span not in evidence_by_id[i]["text"] for i in ids)
                or type(oids) is not list or not oids or len(oids) != len(set(oids))
                or any(type(o) is not str or o not in referenced for o in oids)):
            _fail("ticket_claim_invalid")
        claim_ids.append(cid)
        union.update(ids)
        for oid in oids:
            referenced[oid].extend(ids)
    for entry in plan:
        sources = referenced[entry["obligation_id"]]
        if not sources or any(source not in entry["evidence_ids"] for source in sources):
            _fail("ticket_obligation_binding_invalid")
    if used != [i for i in allowed if i in union]:
        _fail("ticket_claim_binding_invalid")
    return deepcopy(value)


def ticket_completeness_gate(checklist: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Every checklist key element must appear in draft_reply or action_steps."""
    body = result["content"]["draft_reply"] + "\n" + "\n".join(result["content"]["action_steps"])
    squashed_body = "".join(body.split())
    obligations = []
    for obligation in checklist["obligations"]:
        missing = [
            element for element in obligation["key_elements"]
            if "".join(element.split()) not in squashed_body
        ]
        obligations.append({
            "obligation_id": obligation["obligation_id"],
            "missing_key_elements": missing,
            "covered": not missing,
        })
    uncovered = [entry["obligation_id"] for entry in obligations if not entry["covered"]]
    return {
        "schema_version": "ticket-completeness-gate-result-v1",
        "obligations": obligations,
        "uncovered_obligation_ids": uncovered,
        "pass": not uncovered,
        "product_semantics": "fail_closed_handoff_when_not_passing",
    }


__all__ = [
    "FORBIDDEN_CUSTOMER_PHRASES",
    "TICKET_OUTPUT_SCHEMA_VERSION",
    "TICKET_SYSTEM_PROMPT",
    "TicketContractError",
    "ticket_completeness_gate",
    "validate_ticket_result",
]

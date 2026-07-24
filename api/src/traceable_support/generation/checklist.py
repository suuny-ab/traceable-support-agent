"""Two-stage obligation checklist contract and mechanical completeness gate."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from traceable_support.provider.contract import canonical_json_bytes

from .qa_contract import SYSTEM_PROMPT as QA_SYSTEM_PROMPT

CHECKLIST_SCHEMA_VERSION_V2 = "obligation-checklist-v2"
CHECKLIST_SCHEMA_VERSION = "obligation-checklist-v4"
CHECKLIST_MAX_BYTES = 3000
STEP1_MAX_OUTPUT_TOKENS = 16384
STEP1_TIMEOUT_MS = 30_000
STEP2_MAX_OUTPUT_TOKENS = 16384
STEP2_TIMEOUT_MS = 180_000
STEP1_V2_PROMPT_VERSION = "obligation-checklist-prompt-v2"
STEP1_PROMPT_VERSION = "obligation-checklist-prompt-v4"
STEP2_PROMPT_VERSION = "retrieved-top10-qa-prompt-v7"
CHECKLIST_SYSTEM_PROMPT_V2 = """你是客服问答的义务分析器。输入包含问题、型号和按顺序排列的10条候选证据。只输出JSON，不输出解释。
任务：列出回答当前问题在客户可见正文中必须覆盖的全部义务。每个问句、用户已完成步骤后的剩余检查、与当前问题直接相关的前置或安全条件、需要停止操作并转人工的条件，各为一项。并列出现的适用对象、条件或步骤（如\"A或B\"）必须每个分支都纳入义务，不得合并或遗漏。义务只来自证据，不得引入证据外义务。
每项义务给出：obligation_id（简短标识）、description（义务的一句话描述）、evidence_ids（支撑该义务的证据ID，至少一个）、key_elements（1到4个从所绑定证据中逐字复制的关键短片段，每个2到60字符，用于后续机械核对正文覆盖；片段必须逐字存在于该义务绑定的证据原文中，不得改写包括标点）。
只使用回答问题所必需的证据；不要使用无关证据。
分区合同：你所绑定证据中的每一个子句都必须被显式记账——要么被某项义务的key_elements覆盖，要么列入acknowledged_context（从证据中逐字复制的、你判定为与当前问题义务无关的子句）。不允许静默跳过任何子句。
输出格式（占位值必须替换；evidence_ids必须逐字使用输入证据中的实际evidence_id值，不得照抄示例中的\"E1\"）：{\"schema_version\":\"obligation-checklist-v2\",\"obligations\":[{\"obligation_id\":\"o1\",\"description\":\"义务描述\",\"evidence_ids\":[\"E1\"],\"key_elements\":[\"逐字片段\"]}],\"acknowledged_context\":[\"逐字复制的非义务子句\"]}"""
CHECKLIST_SYSTEM_PROMPT = """你是客服问答的义务分析器。输入包含问题、型号和按检索顺序排列的证据子句。只输出JSON，不输出解释。
任务：列出回答当前问题在客户可见正文中必须覆盖的全部义务。每个问句、用户已完成步骤后的剩余检查、与当前问题直接相关的前置或安全条件、需要停止操作并转人工的条件，各为一项。并列出现的适用对象、条件或步骤必须每个分支都纳入义务，不得合并或遗漏。义务只来自证据，不得引入证据外义务。
每项义务给出：obligation_id（简短且唯一）、description（准确概括这项义务的一句话）、clause_ids（语义上支撑该义务的证据子句ID，至少一个）。description允许自然概括，不要复制用于机械匹配的关键字片段。
分区合同：输入中的每个clause_id都必须被显式记账。与问题义务有关的子句放入至少一项义务的clause_ids；与当前问题无关的子句只放入ignored_clause_ids。不得把同一子句同时列为义务和忽略，不得漏掉任何clause_id。宿主会从clause_ids推导evidence_ids和被忽略的原文，不要重复这些机械字段。
输出格式（占位值必须替换，clause_ids必须逐字使用输入中的实际值）：{\"schema_version\":\"obligation-checklist-v4\",\"obligations\":[{\"obligation_id\":\"o1\",\"description\":\"义务描述\",\"clause_ids\":[\"c001\"]}],\"ignored_clause_ids\":[\"c002\"]}"""
STEP2_SYSTEM_PROMPT = QA_SYSTEM_PROMPT + """
义务清单：输入中的obligation_checklist是已审定的运行时义务清单。每条claim必须用obligation_ids绑定它实际表达的义务，并通过exact_span_text声明来源原文、通过customer_visible_span_text声明answer.text中语义对应的连续片段。answer.text必须以自然语言完整表达每项义务。宿主会验证这些声明并推导obligation_plan和used_evidence_ids，不要重复输出这些字段。"""


class TwoStepError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
        self.__cause__ = None
        self.__context__ = None


def _fail(code: str) -> None:
    raise TwoStepError(code) from None


def _squash(text: str) -> str:
    return "".join(text.split())


def completeness_gate(
    checklist: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    """Fail closed unless every obligation has a declared visible answer claim."""

    answer_text = result["content"]["answer"]["text"]
    claims = result["content"]["claims"]
    obligations = []
    for obligation in checklist["obligations"]:
        claim_ids = [
            claim["claim_id"]
            for claim in claims
            if obligation["obligation_id"] in claim["obligation_ids"]
            and claim["customer_visible_span_text"] in answer_text
        ]
        obligations.append(
            {
                "obligation_id": obligation["obligation_id"],
                "customer_visible_claim_ids": claim_ids,
                "covered": bool(claim_ids),
            }
        )
    uncovered = [
        entry["obligation_id"] for entry in obligations if not entry["covered"]
    ]
    return {
        "schema_version": "two-step-completeness-gate-result-v2",
        "obligations": obligations,
        "uncovered_obligation_ids": uncovered,
        "pass": not uncovered,
        "product_semantics": "llm_declares_semantic_mapping_host_verifies_visible_span_and_fails_closed",
    }


_CLAUSE_SPLIT = re.compile(r"(?<=[。，、；：！？,;:])\s*|\n+")
_EDGE_PUNCTUATION = "。，、；：！？,;:"


def _clauses(text: str) -> list[str]:
    return [part for part in _CLAUSE_SPLIT.split(text) if part.strip()]


def _normalize(text: str) -> str:
    return _squash(text).strip(_EDGE_PUNCTUATION)


def build_clause_inventory(evidence: Any) -> list[dict[str, str]]:
    """Split retrieved evidence once and assign compact host-owned clause IDs."""

    if type(evidence) is not list or not evidence:
        _fail("two_step_evidence_invalid")
    inventory: list[dict[str, str]] = []
    seen_evidence_ids: set[str] = set()
    for entry in evidence:
        if (
            type(entry) is not dict
            or type(entry.get("evidence_id")) is not str
            or not entry["evidence_id"]
            or entry["evidence_id"] in seen_evidence_ids
            or type(entry.get("text")) is not str
            or not entry["text"].strip()
        ):
            _fail("two_step_evidence_invalid")
        seen_evidence_ids.add(entry["evidence_id"])
        for clause in _clauses(entry["text"]):
            inventory.append(
                {
                    "clause_id": f"c{len(inventory) + 1:03d}",
                    "evidence_id": entry["evidence_id"],
                    "text": clause,
                }
            )
    if not inventory:
        _fail("two_step_evidence_invalid")
    return inventory


def validate_step1_result(
    item: dict[str, Any], value: Any
) -> dict[str, Any]:
    """Validate v4 semantic selections and derive every mechanical projection."""

    if type(item) is not dict or type(item.get("evidence")) is not list:
        _fail("two_step_evidence_invalid")
    inventory = build_clause_inventory(item["evidence"])
    clause_by_id = {entry["clause_id"]: entry for entry in inventory}
    if type(value) is not dict or set(value) != {
        "schema_version",
        "obligations",
        "ignored_clause_ids",
    }:
        _fail("two_step_checklist_result_shape_invalid")
    if value["schema_version"] != CHECKLIST_SCHEMA_VERSION:
        _fail("two_step_checklist_identity_invalid")
    obligations = value["obligations"]
    if type(obligations) is not list:
        _fail("two_step_checklist_obligations_type_invalid")
    if not obligations:
        _fail("two_step_checklist_obligation_count_empty")
    if len(obligations) > 8:
        _fail("two_step_checklist_obligation_count_exceeded")
    evidence_order = [entry["evidence_id"] for entry in item["evidence"]]
    checked_obligations: list[dict[str, Any]] = []
    obligation_ids: list[str] = []
    selected_clause_ids: set[str] = set()
    for obligation in obligations:
        if type(obligation) is not dict or set(obligation) != {
            "obligation_id",
            "description",
            "clause_ids",
        }:
            _fail("two_step_checklist_obligation_shape_invalid")
        obligation_id = obligation["obligation_id"]
        description = obligation["description"]
        clause_ids = obligation["clause_ids"]
        if (
            type(obligation_id) is not str
            or not obligation_id
            or obligation_id in obligation_ids
            or type(description) is not str
            or not description.strip()
            or len(description) > 300
        ):
            _fail("two_step_checklist_obligation_identity_invalid")
        if (
            type(clause_ids) is not list
            or not clause_ids
            or len(clause_ids) != len(set(clause_ids))
            or any(
                type(clause_id) is not str or clause_id not in clause_by_id
                for clause_id in clause_ids
            )
        ):
            _fail("two_step_checklist_clause_ids_invalid")
        selected_evidence = {
            clause_by_id[clause_id]["evidence_id"] for clause_id in clause_ids
        }
        checked_obligations.append(
            {
                "obligation_id": obligation_id,
                "description": description,
                "clause_ids": deepcopy(clause_ids),
                "evidence_ids": [
                    evidence_id
                    for evidence_id in evidence_order
                    if evidence_id in selected_evidence
                ],
            }
        )
        obligation_ids.append(obligation_id)
        selected_clause_ids.update(clause_ids)
    ignored_clause_ids = value["ignored_clause_ids"]
    if (
        type(ignored_clause_ids) is not list
        or len(ignored_clause_ids) != len(set(ignored_clause_ids))
        or any(
            type(clause_id) is not str or clause_id not in clause_by_id
            for clause_id in ignored_clause_ids
        )
        or selected_clause_ids.intersection(ignored_clause_ids)
    ):
        _fail("two_step_checklist_partition_invalid")
    accounted = selected_clause_ids.union(ignored_clause_ids)
    if accounted != set(clause_by_id):
        _fail("two_step_checklist_partition_incomplete")
    ignored_set = set(ignored_clause_ids)
    ordered_ignored_clause_ids = [
        clause_id for clause_id in clause_by_id if clause_id in ignored_set
    ]
    checked = {
        "schema_version": CHECKLIST_SCHEMA_VERSION,
        "obligations": checked_obligations,
        "ignored_clause_ids": ordered_ignored_clause_ids,
        "acknowledged_context": [
            clause_by_id[clause_id]["text"] for clause_id in ordered_ignored_clause_ids
        ],
    }
    if len(canonical_json_bytes(value)) > CHECKLIST_MAX_BYTES:
        _fail("two_step_checklist_too_large")
    return checked


def checklist_model_projection(checklist: dict[str, Any]) -> dict[str, Any]:
    """Expose only approved semantic obligations to the second model stage."""

    if (
        type(checklist) is not dict
        or checklist.get("schema_version") != CHECKLIST_SCHEMA_VERSION
        or type(checklist.get("obligations")) is not list
        or not checklist["obligations"]
    ):
        _fail("two_step_checklist_invalid")
    obligations = []
    for obligation in checklist["obligations"]:
        if type(obligation) is not dict:
            _fail("two_step_checklist_invalid")
        projected = {
            key: deepcopy(obligation.get(key))
            for key in (
                "obligation_id",
                "description",
                "evidence_ids",
            )
        }
        if any(value is None for value in projected.values()):
            _fail("two_step_checklist_invalid")
        obligations.append(projected)
    return {
        "schema_version": "approved-obligation-checklist-v2",
        "obligations": obligations,
    }


def partition_coverage(
    item: dict[str, Any], checklist: dict[str, Any]
) -> dict[str, Any]:
    """Return deterministic clause-level coverage for bound evidence."""

    evidence_by_id = {entry["evidence_id"]: entry for entry in item["evidence"]}
    keys_by_evidence: dict[str, list[str]] = {}
    for obligation in checklist["obligations"]:
        for evidence_id in obligation["evidence_ids"]:
            keys_by_evidence.setdefault(evidence_id, []).extend(
                obligation["key_elements"]
            )
    context = [_normalize(entry) for entry in checklist.get("acknowledged_context", [])]
    uncovered = []
    for evidence_id, keys in keys_by_evidence.items():
        normalized_keys = [_normalize(key) for key in keys]
        for clause in _clauses(evidence_by_id[evidence_id]["text"]):
            squashed = _normalize(clause)
            if any(key in squashed or squashed in key for key in normalized_keys):
                continue
            if any(squashed in entry or entry in squashed for entry in context):
                continue
            uncovered.append({"evidence_id": evidence_id, "clause": clause})
    return {
        "schema_version": "two-step-partition-coverage-v1",
        "used_evidence_ids": sorted(keys_by_evidence),
        "uncovered": uncovered,
        "pass": not uncovered,
    }


def validate_step1_v2_result(
    item: dict[str, Any], value: Any
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "obligations",
        "acknowledged_context",
    }:
        _fail("two_step_checklist_invalid")
    if value["schema_version"] != CHECKLIST_SCHEMA_VERSION_V2:
        _fail("two_step_checklist_invalid")
    evidence_by_id = {entry["evidence_id"]: entry for entry in item["evidence"]}
    obligations = value["obligations"]
    if type(obligations) is not list or not 1 <= len(obligations) <= 8:
        _fail("two_step_checklist_invalid")
    ids: list[str] = []
    for obligation in obligations:
        if type(obligation) is not dict or set(obligation) != {
            "obligation_id",
            "description",
            "evidence_ids",
            "key_elements",
        }:
            _fail("two_step_checklist_invalid")
        oid = obligation["obligation_id"]
        description = obligation["description"]
        evidence_ids = obligation["evidence_ids"]
        key_elements = obligation["key_elements"]
        if (
            type(oid) is not str
            or not oid
            or oid in ids
            or type(description) is not str
            or not description.strip()
            or len(description) > 300
            or type(evidence_ids) is not list
            or not evidence_ids
            or len(evidence_ids) != len(set(evidence_ids))
            or any(
                type(eid) is not str or eid not in evidence_by_id
                for eid in evidence_ids
            )
        ):
            _fail("two_step_checklist_invalid")
        bound_text = "\n".join(evidence_by_id[eid]["text"] for eid in evidence_ids)
        if type(key_elements) is not list or not 1 <= len(key_elements) <= 4:
            _fail("two_step_checklist_invalid")
        for element in key_elements:
            if (
                type(element) is not str
                or not 2 <= len(element) <= 60
                or element not in bound_text
            ):
                _fail("two_step_checklist_invalid")
        ids.append(oid)
    used_ids = {
        eid for obligation in obligations for eid in obligation["evidence_ids"]
    }
    used_text = "\n".join(evidence_by_id[eid]["text"] for eid in used_ids)
    context = value["acknowledged_context"]
    if type(context) is not list or any(
        type(entry) is not str
        or not 2 <= len(entry) <= 200
        or entry not in used_text
        for entry in context
    ):
        _fail("two_step_checklist_invalid")
    checked = deepcopy(value)
    if len(canonical_json_bytes(checked)) > CHECKLIST_MAX_BYTES:
        _fail("two_step_checklist_too_large")
    if not partition_coverage(item, checked)["pass"]:
        _fail("two_step_checklist_partition_incomplete")
    return checked


__all__ = [
    "CHECKLIST_SCHEMA_VERSION",
    "CHECKLIST_SYSTEM_PROMPT",
    "CHECKLIST_SYSTEM_PROMPT_V2",
    "STEP2_SYSTEM_PROMPT",
    "TwoStepError",
    "build_clause_inventory",
    "checklist_model_projection",
    "completeness_gate",
    "partition_coverage",
    "validate_step1_result",
    "validate_step1_v2_result",
]

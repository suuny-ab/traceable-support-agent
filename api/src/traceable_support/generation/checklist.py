"""Two-stage obligation checklist contract and mechanical completeness gate."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from traceable_support.provider.contract import canonical_json_bytes

from .qa_contract import SYSTEM_PROMPT as V4_SYSTEM_PROMPT

CHECKLIST_SCHEMA_VERSION_V2 = "obligation-checklist-v2"
CHECKLIST_MAX_BYTES = 3000
STEP1_MAX_OUTPUT_TOKENS = 2048
STEP1_TIMEOUT_MS = 30_000
STEP2_MAX_OUTPUT_TOKENS = 8192
STEP2_TIMEOUT_MS = 180_000
STEP1_V2_PROMPT_VERSION = "obligation-checklist-prompt-v2"
STEP2_PROMPT_VERSION = "retrieved-top10-qa-prompt-v5"
CHECKLIST_SYSTEM_PROMPT_V2 = """你是客服问答的义务分析器。输入包含问题、型号和按顺序排列的10条候选证据。只输出JSON，不输出解释。
任务：列出回答当前问题在客户可见正文中必须覆盖的全部义务。每个问句、用户已完成步骤后的剩余检查、与当前问题直接相关的前置或安全条件、需要停止操作并转人工的条件，各为一项。并列出现的适用对象、条件或步骤（如\"A或B\"）必须每个分支都纳入义务，不得合并或遗漏。义务只来自证据，不得引入证据外义务。
每项义务给出：obligation_id（简短标识）、description（义务的一句话描述）、evidence_ids（支撑该义务的证据ID，至少一个）、key_elements（1到4个从所绑定证据中逐字复制的关键短片段，每个2到60字符，用于后续机械核对正文覆盖；片段必须逐字存在于该义务绑定的证据原文中，不得改写包括标点）。
只使用回答问题所必需的证据；不要使用无关证据。
分区合同：你所绑定证据中的每一个子句都必须被显式记账——要么被某项义务的key_elements覆盖，要么列入acknowledged_context（从证据中逐字复制的、你判定为与当前问题义务无关的子句）。不允许静默跳过任何子句。
输出格式（占位值必须替换；evidence_ids必须逐字使用输入证据中的实际evidence_id值，不得照抄示例中的\"E1\"）：{\"schema_version\":\"obligation-checklist-v2\",\"obligations\":[{\"obligation_id\":\"o1\",\"description\":\"义务描述\",\"evidence_ids\":[\"E1\"],\"key_elements\":[\"逐字片段\"]}],\"acknowledged_context\":[\"逐字复制的非义务子句\"]}"""
STEP2_SYSTEM_PROMPT = V4_SYSTEM_PROMPT + """
义务清单：输入中的obligation_checklist是已审定的运行时义务清单。obligation_plan必须与清单逐项一一对应（数量相同、obligation_id保持一致、绑定证据一致），不得新增或删除义务。answer.text必须逐字包含清单每项的key_elements全部片段（保持原字原标点），并以自然段落完整表达每项义务。"""


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
    """Fail closed unless every checklist key element appears in the answer."""

    answer_text = result["content"]["answer"]["text"]
    squashed_answer = _squash(answer_text)
    obligations = []
    for obligation in checklist["obligations"]:
        missing = [
            element
            for element in obligation["key_elements"]
            if _squash(element) not in squashed_answer
        ]
        obligations.append(
            {
                "obligation_id": obligation["obligation_id"],
                "missing_key_elements": missing,
                "covered": not missing,
            }
        )
    uncovered = [
        entry["obligation_id"] for entry in obligations if not entry["covered"]
    ]
    return {
        "schema_version": "two-step-completeness-gate-result-v1",
        "obligations": obligations,
        "uncovered_obligation_ids": uncovered,
        "pass": not uncovered,
        "product_semantics": "fail_closed_handoff_when_not_passing",
    }


_CLAUSE_SPLIT = re.compile(r"(?<=[。，、；：！？,;:])\s*|\n+")
_EDGE_PUNCTUATION = "。，、；：！？,;:"


def _clauses(text: str) -> list[str]:
    return [part for part in _CLAUSE_SPLIT.split(text) if part.strip()]


def _normalize(text: str) -> str:
    return _squash(text).strip(_EDGE_PUNCTUATION)


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
    "CHECKLIST_SYSTEM_PROMPT_V2",
    "STEP2_SYSTEM_PROMPT",
    "TwoStepError",
    "completeness_gate",
    "partition_coverage",
    "validate_step1_v2_result",
]

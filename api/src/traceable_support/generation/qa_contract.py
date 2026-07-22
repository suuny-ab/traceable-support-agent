"""QA response contract and evidence/obligation binding validator."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from traceable_support.provider.contract import assert_no_sensitive_material

PROMPT_VERSION = "retrieved-top10-qa-prompt-v4"
OUTPUT_SCHEMA_VERSION = "retrieved-top10-qa-result-v2"
FORBIDDEN_CUSTOMER_PHRASES = (
    "自动生成",
    "仅为草稿",
    "不能标记为已解决",
    "内部流程",
    "系统要求",
    "客服审核",
)
SYSTEM_PROMPT = """你是客户可见的设备支持问答生成器。输入包含问题、型号和按顺序排列的10条候选证据。只输出JSON，不输出推理或检查过程。
严格身份：顶层schema_version必须逐字为\"retrieved-top10-qa-result-v2\"；顶层task_type必须逐字为\"qa\"；content.kind必须逐字为\"qa_answer\"。
规划规则：先规划后生成。把回答当前问题必须覆盖的每一项客户可见正文义务写入obligation_plan：用户的每个问句、已完成步骤后的剩余检查、所选证据章节中与当前问题直接相关的前置或安全条件、以及需要停止操作并转人工的条件，各为一项。每项义务必须绑定支撑它的evidence_id；义务只来自证据，不得引入证据外义务。证据中并列出现的要素（如\"A或B\"式并列条件）属于同一义务时，每个分支都必须纳入义务描述并在正文中逐一明确表达，不得只写其中一个分支。
来源规则：每条claim优先且默认只绑定一个evidence_id，并逐字复制该来源中的连续exact_span_text。逐字复制包括标点：不得把全角标点改写为半角标点，不得增删或替换任何字符。只有同一exact_span_text逐字存在于每个来源时才可绑定多个来源；表达相近不算逐字存在，应拆成不同claim。每条claim必须用obligation_ids归属至少一项计划义务；每项计划义务至少由一条claim支撑。
正文规则：answer.text必须以自然段落逐项明确表达obligation_plan中的每一项义务，不得遗漏；不要输出检查清单本身。不得让用户重复已完成动作，不得跳过剩余检查直接升级。
客户边界：不得出现自动生成、草稿、内部流程、审核、标记已解决等系统或客服操作话术，不得补充证据外事实。
完整JSON正例（占位值必须替换）：{\"schema_version\":\"retrieved-top10-qa-result-v2\",\"task_type\":\"qa\",\"obligation_plan\":[{\"obligation_id\":\"o1\",\"description\":\"回答当前问题必须覆盖的一项客户可见义务\",\"evidence_ids\":[\"E1\"]}],\"used_evidence_ids\":[\"E1\"],\"content\":{\"kind\":\"qa_answer\",\"answer\":{\"text\":\"面向客户的完整回答\",\"claim_ids\":[\"c1\"]},\"claims\":[{\"claim_id\":\"c1\",\"exact_span_text\":\"从E1逐字复制的连续原文\",\"evidence_ids\":[\"E1\"],\"obligation_ids\":[\"o1\"]}],\"insufficient_evidence\":false}}"""


class CandidateV4Error(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
        self.__cause__ = None
        self.__context__ = None


def _fail(code: str) -> None:
    raise CandidateV4Error(code) from None


def _contract(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "allowed_evidence_ids_in_order": [e["evidence_id"] for e in evidence],
        "required_top_level_keys": [
            "schema_version",
            "task_type",
            "obligation_plan",
            "used_evidence_ids",
            "content",
        ],
        "obligation_plan_shape": {
            "obligation_id": "unique nonempty string",
            "description": "customer-visible obligation, nonempty, <=300 chars",
            "evidence_ids": "nonempty subset of allowed ids",
        },
        "content_shape": {
            "task_type": "qa",
            "kind": "qa_answer",
            "answer": {
                "text": "customer-visible nonempty string",
                "claim_ids": "claim ids in order",
            },
            "claims": [
                {
                    "claim_id": "c1",
                    "exact_span_text": "verbatim evidence substring",
                    "evidence_ids": ["allowed id"],
                    "obligation_ids": ["planned obligation id"],
                }
            ],
            "insufficient_evidence": False,
        },
        "obligation_binding_rule": "every claim belongs to at least one planned obligation; every planned obligation is supported by at least one claim; plan evidence_ids cover the sources of its claims",
        "single_source_claim_default": True,
        "multi_source_claim_rule": "exact_span_text_must_exist_verbatim_in_every_referenced_evidence",
        "complete_json_example": {
            "schema_version": OUTPUT_SCHEMA_VERSION,
            "task_type": "qa",
            "obligation_plan": [
                {
                    "obligation_id": "o1",
                    "description": "customer-visible obligation",
                    "evidence_ids": ["E1"],
                }
            ],
            "used_evidence_ids": ["E1"],
            "content": {
                "kind": "qa_answer",
                "answer": {"text": "customer answer", "claim_ids": ["c1"]},
                "claims": [
                    {
                        "claim_id": "c1",
                        "exact_span_text": "verbatim span from E1",
                        "evidence_ids": ["E1"],
                        "obligation_ids": ["o1"],
                    }
                ],
                "insufficient_evidence": False,
            },
        },
    }


def _validate_v2_projection(
    item: dict[str, Any], value: dict[str, Any]
) -> dict[str, Any]:
    allowed = [e["evidence_id"] for e in item["evidence"]]
    evidence_by_id = {e["evidence_id"]: e for e in item["evidence"]}
    used = value["used_evidence_ids"]
    content = value["content"]
    if (
        type(used) is not list
        or not used
        or len(set(used)) != len(used)
        or any(type(i) is not str or i not in evidence_by_id for i in used)
        or used != [i for i in allowed if i in set(used)]
    ):
        _fail("top10_v4_content_invalid")
    if type(content) is not dict or set(content) != {
        "kind",
        "answer",
        "claims",
        "insufficient_evidence",
    }:
        _fail("top10_v4_content_invalid")
    if content["kind"] != "qa_answer" or content["insufficient_evidence"] is not False:
        _fail("top10_v4_content_invalid")
    answer, claims = content["answer"], content["claims"]
    if (
        type(answer) is not dict
        or set(answer) != {"text", "claim_ids"}
        or type(answer["text"]) is not str
        or not answer["text"].strip()
        or len(answer["text"]) > 1500
        or any(phrase in answer["text"] for phrase in FORBIDDEN_CUSTOMER_PHRASES)
        or type(claims) is not list
        or not 1 <= len(claims) <= 8
    ):
        _fail("top10_v4_content_invalid")
    claim_ids: list[str] = []
    union: set[str] = set()
    for claim in claims:
        if type(claim) is not dict or set(claim) != {
            "claim_id",
            "exact_span_text",
            "evidence_ids",
        }:
            _fail("top10_v4_content_invalid")
        cid = claim["claim_id"]
        span = claim["exact_span_text"]
        ids = claim["evidence_ids"]
        if (
            type(cid) is not str
            or not cid
            or cid in claim_ids
            or type(span) is not str
            or not span
            or len(span) > 1000
            or type(ids) is not list
            or not ids
            or len(ids) != len(set(ids))
            or any(i not in evidence_by_id for i in ids)
            or any(span not in evidence_by_id[i]["text"] for i in ids)
        ):
            _fail("top10_v4_content_invalid")
        claim_ids.append(cid)
        union.update(ids)
    if answer["claim_ids"] != claim_ids or used != [i for i in allowed if i in union]:
        _fail("top10_v4_content_invalid")
    return deepcopy(value)


def validate_v4_result(item: dict[str, Any], value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "task_type",
        "obligation_plan",
        "used_evidence_ids",
        "content",
    }:
        _fail("top10_v4_result_shape_invalid")
    if value["schema_version"] != OUTPUT_SCHEMA_VERSION or value["task_type"] != "qa":
        _fail("top10_v4_result_identity_invalid")
    evidence_by_id = {e["evidence_id"]: e for e in item["evidence"]}
    plan = value["obligation_plan"]
    if type(plan) is not list or not 1 <= len(plan) <= 8:
        _fail("top10_v4_obligation_plan_invalid")
    plan_ids: list[str] = []
    for entry in plan:
        if type(entry) is not dict or set(entry) != {
            "obligation_id",
            "description",
            "evidence_ids",
        }:
            _fail("top10_v4_obligation_plan_invalid")
        oid = entry["obligation_id"]
        description = entry["description"]
        ids = entry["evidence_ids"]
        if (
            type(oid) is not str
            or not oid
            or oid in plan_ids
            or type(description) is not str
            or not description.strip()
            or len(description) > 300
            or type(ids) is not list
            or not ids
            or len(ids) != len(set(ids))
            or any(type(i) is not str or i not in evidence_by_id for i in ids)
        ):
            _fail("top10_v4_obligation_plan_invalid")
        plan_ids.append(oid)
    content = value["content"]
    claims = content.get("claims") if type(content) is dict else None
    if type(claims) is not list:
        _fail("top10_v4_content_invalid")
    referenced: dict[str, list[str]] = {oid: [] for oid in plan_ids}
    for claim in claims:
        if type(claim) is not dict or "obligation_ids" not in claim:
            _fail("top10_v4_obligation_binding_invalid")
        oids = claim["obligation_ids"]
        cids = claim.get("evidence_ids")
        if (
            type(oids) is not list
            or not oids
            or len(oids) != len(set(oids))
            or any(type(o) is not str or o not in referenced for o in oids)
            or type(cids) is not list
        ):
            _fail("top10_v4_obligation_binding_invalid")
        for oid in oids:
            referenced[oid].extend(cids)
    for entry in plan:
        sources = referenced[entry["obligation_id"]]
        if not sources or any(source not in entry["evidence_ids"] for source in sources):
            _fail("top10_v4_obligation_binding_invalid")
    projection = {
        "used_evidence_ids": value["used_evidence_ids"],
        "content": deepcopy(content),
    }
    projection["content"]["claims"] = [
        {
            key: claim[key]
            for key in ("claim_id", "exact_span_text", "evidence_ids")
        }
        for claim in projection["content"]["claims"]
    ]
    checked = _validate_v2_projection(item, projection)
    checked["schema_version"] = OUTPUT_SCHEMA_VERSION
    checked["task_type"] = "qa"
    checked["obligation_plan"] = deepcopy(plan)
    assert_no_sensitive_material(value)
    return checked


__all__ = [
    "CandidateV4Error",
    "OUTPUT_SCHEMA_VERSION",
    "PROMPT_VERSION",
    "SYSTEM_PROMPT",
    "_contract",
    "validate_v4_result",
]

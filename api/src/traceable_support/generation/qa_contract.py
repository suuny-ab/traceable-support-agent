"""QA response contract and evidence/obligation binding validator."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from traceable_support.provider.contract import assert_no_sensitive_material

PROMPT_VERSION = "retrieved-top10-qa-prompt-v6"
LEGACY_OUTPUT_SCHEMA_VERSION = "retrieved-top10-qa-result-v2"
OUTPUT_SCHEMA_VERSION = "retrieved-top10-qa-result-v3"
FORBIDDEN_CUSTOMER_PHRASES = (
    "自动生成",
    "仅为草稿",
    "不能标记为已解决",
    "内部流程",
    "系统要求",
    "客服审核",
)
SYSTEM_PROMPT = """你是客户可见的设备支持问答生成器。输入包含问题、型号、按顺序排列的候选证据和已审定义务清单。只输出JSON，不输出推理或检查过程。
严格身份：顶层schema_version必须逐字为\"retrieved-top10-qa-result-v3\"；顶层task_type必须逐字为\"qa\"；content.kind必须逐字为\"qa_answer\"。
宿主推导：不要输出obligation_plan、used_evidence_ids或answer.claim_ids；宿主会从已审定义务清单和claims机械推导这些字段。
来源规则：每条claim优先且默认只绑定一个evidence_id，并逐字复制该来源中的连续exact_span_text。逐字复制包括标点：不得把全角标点改写为半角标点，不得增删或替换任何字符。只有同一exact_span_text逐字存在于每个来源时才可绑定多个来源；表达相近不算逐字存在，应拆成不同claim。每条claim必须用obligation_ids归属至少一项已审定义务；每项义务至少由一条claim支撑，且claim来源必须属于该义务已审定的evidence_ids。
正文规则：answer.text必须以自然段落逐项明确表达已审定义务，不得遗漏；不要输出检查清单本身。不得让用户重复已完成动作，不得跳过剩余检查直接升级。
客户边界：不得出现自动生成、草稿、内部流程、审核、标记已解决等系统或客服操作话术，不得补充证据外事实。
完整JSON正例（占位值必须替换）：{\"schema_version\":\"retrieved-top10-qa-result-v3\",\"task_type\":\"qa\",\"content\":{\"kind\":\"qa_answer\",\"answer\":{\"text\":\"面向客户的完整回答\"},\"claims\":[{\"claim_id\":\"c1\",\"exact_span_text\":\"从E1逐字复制的连续原文\",\"evidence_ids\":[\"E1\"],\"obligation_ids\":[\"o1\"]}],\"insufficient_evidence\":false}}"""


class CandidateV4Error(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
        self.__cause__ = None
        self.__context__ = None


CandidateContractError = CandidateV4Error


def _fail(code: str) -> None:
    raise CandidateV4Error(code) from None


def _contract(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "allowed_evidence_ids_in_order": [e["evidence_id"] for e in evidence],
        "required_top_level_keys": [
            "schema_version",
            "task_type",
            "content",
        ],
        "content_shape": {
            "task_type": "qa",
            "kind": "qa_answer",
            "answer": {
                "text": "customer-visible nonempty string",
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
        "host_derived_fields": [
            "obligation_plan",
            "used_evidence_ids",
            "content.answer.claim_ids",
        ],
        "obligation_binding_rule": "every claim belongs to at least one approved checklist obligation; every approved obligation is supported by at least one claim; claim sources stay within that obligation's approved evidence_ids",
        "single_source_claim_default": True,
        "multi_source_claim_rule": "exact_span_text_must_exist_verbatim_in_every_referenced_evidence",
        "complete_json_example": {
            "schema_version": OUTPUT_SCHEMA_VERSION,
            "task_type": "qa",
            "content": {
                "kind": "qa_answer",
                "answer": {"text": "customer answer"},
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
    if value["schema_version"] != LEGACY_OUTPUT_SCHEMA_VERSION or value["task_type"] != "qa":
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
    checked["schema_version"] = LEGACY_OUTPUT_SCHEMA_VERSION
    checked["task_type"] = "qa"
    checked["obligation_plan"] = deepcopy(plan)
    assert_no_sensitive_material(value)
    return checked


def validate_result(
    item: dict[str, Any],
    checklist: dict[str, Any],
    value: Any,
) -> dict[str, Any]:
    """Validate the compact v3 model result and add host-derived projections."""

    if type(value) is not dict or set(value) != {
        "schema_version",
        "task_type",
        "content",
    }:
        _fail("top10_v6_result_shape_invalid")
    if value["schema_version"] != OUTPUT_SCHEMA_VERSION or value["task_type"] != "qa":
        _fail("top10_v6_result_identity_invalid")
    if (
        type(checklist) is not dict
        or type(checklist.get("obligations")) is not list
        or not checklist["obligations"]
    ):
        _fail("top10_v6_checklist_invalid")
    evidence_by_id = {entry["evidence_id"]: entry for entry in item["evidence"]}
    evidence_order = [entry["evidence_id"] for entry in item["evidence"]]
    plan: list[dict[str, Any]] = []
    plan_by_id: dict[str, dict[str, Any]] = {}
    for obligation in checklist["obligations"]:
        if type(obligation) is not dict:
            _fail("top10_v6_checklist_invalid")
        projected = {
            key: deepcopy(obligation.get(key))
            for key in ("obligation_id", "description", "evidence_ids")
        }
        if (
            type(projected["obligation_id"]) is not str
            or not projected["obligation_id"]
            or projected["obligation_id"] in plan_by_id
            or type(projected["description"]) is not str
            or not projected["description"].strip()
            or type(projected["evidence_ids"]) is not list
            or not projected["evidence_ids"]
            or any(
                type(evidence_id) is not str or evidence_id not in evidence_by_id
                for evidence_id in projected["evidence_ids"]
            )
        ):
            _fail("top10_v6_checklist_invalid")
        plan.append(projected)
        plan_by_id[projected["obligation_id"]] = projected
    content = value["content"]
    if type(content) is not dict or set(content) != {
        "kind",
        "answer",
        "claims",
        "insufficient_evidence",
    }:
        _fail("top10_v6_content_invalid")
    if content["kind"] != "qa_answer" or content["insufficient_evidence"] is not False:
        _fail("top10_v6_content_invalid")
    answer = content["answer"]
    claims = content["claims"]
    if (
        type(answer) is not dict
        or set(answer) != {"text"}
        or type(claims) is not list
        or not 1 <= len(claims) <= 8
    ):
        _fail("top10_v6_content_invalid")
    referenced: dict[str, list[str]] = {
        obligation_id: [] for obligation_id in plan_by_id
    }
    normalized_claims: list[dict[str, Any]] = []
    claim_ids: list[str] = []
    used_set: set[str] = set()
    for claim in claims:
        if type(claim) is not dict or set(claim) != {
            "claim_id",
            "exact_span_text",
            "evidence_ids",
            "obligation_ids",
        }:
            _fail("top10_v6_claim_invalid")
        claim_id = claim["claim_id"]
        span = claim["exact_span_text"]
        evidence_ids = claim["evidence_ids"]
        obligation_ids = claim["obligation_ids"]
        if (
            type(claim_id) is not str
            or not claim_id
            or claim_id in claim_ids
            or type(span) is not str
            or not span
            or len(span) > 1000
            or type(evidence_ids) is not list
            or not evidence_ids
            or len(evidence_ids) != len(set(evidence_ids))
            or any(
                type(evidence_id) is not str
                or evidence_id not in evidence_by_id
                or span not in evidence_by_id[evidence_id]["text"]
                for evidence_id in evidence_ids
            )
            or type(obligation_ids) is not list
            or not obligation_ids
            or len(obligation_ids) != len(set(obligation_ids))
            or any(
                type(obligation_id) is not str
                or obligation_id not in plan_by_id
                for obligation_id in obligation_ids
            )
        ):
            _fail("top10_v6_claim_invalid")
        for obligation_id in obligation_ids:
            allowed_sources = plan_by_id[obligation_id]["evidence_ids"]
            if any(evidence_id not in allowed_sources for evidence_id in evidence_ids):
                _fail("top10_v6_obligation_binding_invalid")
            referenced[obligation_id].extend(evidence_ids)
        claim_ids.append(claim_id)
        used_set.update(evidence_ids)
        normalized_claims.append(deepcopy(claim))
    if any(not sources for sources in referenced.values()):
        _fail("top10_v6_obligation_binding_invalid")
    used_evidence_ids = [
        evidence_id for evidence_id in evidence_order if evidence_id in used_set
    ]
    projection = {
        "used_evidence_ids": used_evidence_ids,
        "content": {
            "kind": content["kind"],
            "answer": {
                "text": answer["text"],
                "claim_ids": claim_ids,
            },
            "claims": [
                {
                    key: claim[key]
                    for key in ("claim_id", "exact_span_text", "evidence_ids")
                }
                for claim in normalized_claims
            ],
            "insufficient_evidence": content["insufficient_evidence"],
        },
    }
    _validate_v2_projection(item, projection)
    normalized = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "task_type": "qa",
        "obligation_plan": plan,
        "used_evidence_ids": used_evidence_ids,
        "content": {
            "kind": content["kind"],
            "answer": {
                "text": answer["text"],
                "claim_ids": claim_ids,
            },
            "claims": normalized_claims,
            "insufficient_evidence": content["insufficient_evidence"],
        },
    }
    assert_no_sensitive_material(value)
    return normalized


__all__ = [
    "CandidateV4Error",
    "CandidateContractError",
    "LEGACY_OUTPUT_SCHEMA_VERSION",
    "OUTPUT_SCHEMA_VERSION",
    "PROMPT_VERSION",
    "SYSTEM_PROMPT",
    "_contract",
    "validate_result",
    "validate_v4_result",
]

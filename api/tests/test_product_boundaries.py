import json
from pathlib import Path

from traceable_support.product.boundaries import evaluate_generation_boundary
from traceable_support.product.qa import run_qa
from traceable_support.product.runner import DefaultProductRunner
from traceable_support.product.ticket import run_ticket
from traceable_support.product.types import RunInput

REPOSITORY = Path(__file__).resolve().parents[2]


def test_safety_incidents_fail_closed_but_knowledge_questions_remain_allowed():
    hazardous = (
        "R1刚吸进一小滩水，我想继续开机把剩下的吸完。",
        "CZ-R2 已经吸入液体，还能接着扫吗？",
        "主机进水后仍在运行。",
        "设备突然冒烟了。",
    )
    for text in hazardous:
        decision = evaluate_generation_boundary(text, "CZ-R1")
        assert decision is not None
        assert decision.reason == "safety_risk"
        assert decision.ticket_category == "安全风险"
        assert decision.ticket_priority == "P0-紧急"

    allowed = (
        ("CZ-R2 能否清理有积水的地面？", "CZ-R2"),
        ("CZ-R2 的清水箱应该怎样加入常温清水？", "CZ-R2"),
        ("CZ-R1 只支持干式清扫吗？", "CZ-R1"),
    )
    for text, model in allowed:
        assert evaluate_generation_boundary(text, model) is None


def test_cz_r2_dust_station_operations_fail_closed_for_cz_r1_only():
    conflicting = (
        "CZ-R1 的基站集尘袋满了，应该怎么更换？",
        "R1 报 E310，恢复供电后要怎样测试？",
        "CZ-R1 自动集尘时橙灯一直亮。",
    )
    for text in conflicting:
        decision = evaluate_generation_boundary(text, "CZ-R1")
        assert decision is not None
        assert decision.reason == "model_scope_conflict"

    allowed = (
        ("CZ-R2 的基站集尘袋满了，应该怎么更换？", "CZ-R2"),
        ("CZ-R1 的尘盒和滤网应该怎么清理？", "CZ-R1"),
        ("R1路线乱了，能不能直接照R2按复位孔？", "CZ-R1"),
    )
    for text, model in allowed:
        assert evaluate_generation_boundary(text, model) is None


def test_explicit_text_model_must_match_selected_model_unless_comparing_models():
    mismatched = (
        ("CZ-R1 的基站集尘袋满了，应该怎么更换？", "CZ-R2"),
        ("CZ-R2 自动集尘时橙灯一直亮。", "CZ-R1"),
    )
    for text, selected_model in mismatched:
        decision = evaluate_generation_boundary(text, selected_model)
        assert decision is not None
        assert decision.reason == "model_scope_conflict"
        assert decision.rule_id == "selected_model_conflicts_with_explicit_text_model"
        assert decision.source_sections == (
            "COMMON-FAQ/model-difference",
            "CUSTOMER-SERVICE-SOP/intake-fields",
        )

    comparisons = (
        "CZ-R1 有没有自动集尘功能？",
        "CZ-R1 可以自动集尘吗？",
        "CZ-R1 可不可以自动集尘？",
        "CZ-R1 会不会自动集尘？",
        "CZ-R1 是否支持开启自动集尘功能？",
        "CZ-R1 自动集尘可以设置吗？",
        "为什么 CZ-R1 没有自动集尘，而 CZ-R2 有？",
        "CZ-R1 和 CZ-R2 的自动集尘能力有什么区别？",
    )
    for text in comparisons:
        assert evaluate_generation_boundary(text, "CZ-R1") is None

    operational = (
        ("CZ-R1 和 CZ-R2 的集尘袋都满了，应该怎么更换？", "CZ-R2"),
        ("CZ-R1 的集尘袋可以怎么更换？", "CZ-R1"),
        ("CZ-R1 E310 可以重置吗？", "CZ-R1"),
        ("CZ-R1 集尘袋已满可以重置吗？", "CZ-R1"),
    )
    for text, selected_model in operational:
        decision = evaluate_generation_boundary(text, selected_model)
        assert decision is not None
        assert decision.reason == "model_scope_conflict"


def test_unbacked_safety_words_are_not_classified_as_source_backed_incidents():
    for text in ("设备起火了。", "用户说设备漏电，担心触电。"):
        decision = evaluate_generation_boundary(text, "CZ-R1")
        assert decision is None or decision.reason != "safety_risk"


def test_direct_product_paths_return_zero_cost_boundary_packages_without_transport():
    qa = run_qa(
        question="CZ-R1 的基站集尘袋满了，应该怎么更换？",
        product_model="CZ-R1",
        transport=None,
        mode="offline_injected",
        run_id="boundary-qa",
        worst_cost_limit_cny_nanos=1,
    )
    assert qa["outcome"] == "handoff"
    assert qa["handoff_reason"] == "model_scope_conflict"
    assert qa["usage"] == []
    assert qa["worst_cost_cny_nanos"] == 0
    assert qa["boundary_sources"] == [
        "COMMON-FAQ/model-difference",
        "CZ-R2-MANUAL/auto-empty",
    ]

    ticket = run_ticket(
        ticket={
            "ticket_id": "T-SAFETY",
            "product_model": "CZ-R1",
            "issue_description": "R1刚吸进一小滩水，我想继续开机把剩下的吸完。",
            "category": "使用咨询",
            "priority": "P2-普通",
        },
        transport=None,
        mode="offline_injected",
        run_id="boundary-ticket",
        worst_cost_limit_cny_nanos=1,
    )
    assert ticket["outcome"] == "handoff"
    assert ticket["handoff_reason"] == "safety_risk"
    assert ticket["category"] == "安全风险"
    assert ticket["priority"] == "P0-紧急"
    assert ticket["usage"] == []
    assert ticket["worst_cost_cny_nanos"] == 0


def test_runner_blocks_before_transport_factory_for_qa_and_ticket():
    calls = 0

    def forbidden_factory():
        nonlocal calls
        calls += 1
        raise AssertionError("transport factory must not be called")

    runner = DefaultProductRunner(
        transport_factory=forbidden_factory,
        transport_mode="offline_injected",
        dependencies_ready=True,
    )
    cases = (
        RunInput(
            "boundary-runner-qa",
            "qa",
            "CZ-R1 的基站集尘袋满了，应该怎么更换？",
            "CZ-R1",
            1,
        ),
        RunInput(
            "boundary-runner-ticket",
            "ticket",
            "R1刚吸进一小滩水，我想继续开机把剩下的吸完。",
            "CZ-R1",
            1,
        ),
        RunInput(
            "boundary-runner-dual-model-operation",
            "qa",
            "CZ-R1 和 CZ-R2 的集尘袋都满了，应该怎么更换？",
            "CZ-R2",
            1,
        ),
        RunInput(
            "boundary-runner-e310-reset",
            "qa",
            "CZ-R1 E310 可以重置吗？",
            "CZ-R1",
            1,
        ),
        RunInput(
            "boundary-runner-full-dust-bag-reset",
            "qa",
            "CZ-R1 集尘袋已满可以重置吗？",
            "CZ-R1",
            1,
        ),
    )
    for value in cases:
        stages = []
        execution = runner.execute(value, lambda stage, status: stages.append((stage, status)))
        assert execution.package["outcome"] == "handoff"
        assert execution.provider_call_count == 0
        assert stages == [("preflight", "failed")]
    assert calls == 0


def test_public_safety_expectation_is_enforced_with_matching_sources():
    suite = json.loads(
        (REPOSITORY / "evals" / "public-regression-v1.json").read_text(
            encoding="utf-8"
        )
    )
    case = next(
        item for item in suite["cases"] if item["case_id"] == "GEN-DEV-MH-001"
    )
    expected = case["expected"]
    runner = DefaultProductRunner(
        transport_factory=lambda: (_ for _ in ()).throw(
            AssertionError("transport factory must not be called")
        ),
        transport_mode="offline_injected",
        dependencies_ready=True,
    )
    execution = runner.execute(
        RunInput(
            case["case_id"],
            case["task_type"],
            case["input"],
            case["product_model"],
            1,
        ),
        lambda _stage, _status: None,
    )
    package = execution.package
    assert package["outcome"] == expected["outcome"]
    assert package["handoff_reason"] == expected["handoff_reason"]
    assert package["category"] == expected["category"]
    assert package["priority"] == expected["priority"]
    assert package["boundary_sources"] == expected["source_sections"]
    assert execution.provider_call_count == expected["provider_call_count"]


def test_public_unsupported_claim_expectation_is_enforced_with_zero_calls():
    suite = json.loads(
        (REPOSITORY / "evals" / "public-regression-v1.json").read_text(
            encoding="utf-8"
        )
    )
    case = next(
        item for item in suite["cases"] if item["case_id"] == "GEN-DEV-IE-001"
    )
    expected = case["expected"]
    decision = evaluate_generation_boundary(case["input"], case["product_model"])
    assert decision is not None
    assert decision.reason == expected["handoff_reason"]
    assert decision.source_sections == tuple(expected["source_sections"])

    runner = DefaultProductRunner(
        transport_factory=lambda: (_ for _ in ()).throw(
            AssertionError("transport factory must not be called")
        ),
        transport_mode="offline_injected",
        dependencies_ready=True,
    )
    execution = runner.execute(
        RunInput(
            case["case_id"],
            case["task_type"],
            case["input"],
            case["product_model"],
            1,
        ),
        lambda _stage, _status: None,
    )
    package = execution.package
    assert package["outcome"] == expected["outcome"]
    assert package["handoff_reason"] == expected["handoff_reason"]
    assert package["boundary_sources"] == expected["source_sections"]
    assert package["usage"] == []
    assert package["worst_cost_cny_nanos"] == 0
    assert execution.provider_call_count == expected["provider_call_count"]


def test_public_after_sales_commitment_gap_is_closed_with_typed_zero_call_handoff():
    suite = json.loads(
        (REPOSITORY / "evals" / "public-regression-v1.json").read_text(
            encoding="utf-8"
        )
    )
    case = next(
        item for item in suite["cases"] if item["case_id"] == "GEN-DEV-MH-003"
    )
    expected = case["expected"]
    runner = DefaultProductRunner(
        transport_factory=lambda: (_ for _ in ()).throw(
            AssertionError("transport factory must not be called")
        ),
        transport_mode="offline_injected",
        dependencies_ready=True,
    )
    execution = runner.execute(
        RunInput(
            case["case_id"],
            case["task_type"],
            case["input"],
            case["product_model"],
            1,
        ),
        lambda _stage, _status: None,
    )
    package = execution.package
    assert package["outcome"] == expected["outcome"]
    assert package["handoff_type"] == "human_authority"
    assert package["handoff_reason"] == expected["handoff_reason"]
    assert package["category"] == expected["category"]
    assert package["priority"] == expected["priority"]
    assert package["boundary_sources"] == expected["source_sections"]
    assert package["usage"] == []
    assert package["worst_cost_cny_nanos"] == 0
    assert execution.provider_call_count == expected["provider_call_count"]
    assert not any("GEN-DEV-MH-003" in gap for gap in suite["known_product_gaps"])


def test_unsupported_capability_rule_does_not_catch_approved_topics():
    allowed = (
        ("CZ-R1 怎么开始局部清扫？", "CZ-R1"),
        ("CZ-R2 基站提示 E310 集尘通道受阻，应该如何排查？", "CZ-R2"),
        ("客户反馈 CZ-R2 扫拖时遇到长毛、边缘松散的地毯，应该怎么处理？", "CZ-R2"),
        ("CZ-R1 支持 WiFi 连接吗？", "CZ-R1"),
        ("CZ-R2 的清水箱可以加清洁剂吗？", "CZ-R2"),
    )
    for text, model in allowed:
        assert evaluate_generation_boundary(text, model) is None

    unsupported = (
        ("CZ-R1只支持2.4GHz还是也支持5GHz无线网络？", "CZ-R1"),
        ("CZ-R2 支持 5GHz WiFi 吗？", "CZ-R2"),
        ("CZ-R1 无线网络频段是多少？", "CZ-R1"),
    )
    for text, model in unsupported:
        decision = evaluate_generation_boundary(text, model)
        assert decision is not None
        assert decision.reason == "unsupported_claim"


def test_r2_outcome_decision_table_compiles_to_typed_handoffs():
    cases = (
        (
            "CZ-R1 清扫长毛地毯时会自动抬升拖布吗，还要设置禁区吗？",
            "CZ-R1",
            "qa",
            "model_scope",
            "model_scope_conflict",
            "cz_r2_wet_cleaning_not_available_on_cz_r1",
        ),
        (
            "CZ-R2 低电回充以后会自动续扫吗，还是要再次开始清扫？",
            "CZ-R2",
            "qa",
            "evidence_gap",
            "unsupported_claim",
            "cz_r2_auto_resume_not_covered",
        ),
        (
            "CZ-R2 能通过手机应用接入语音助手控制吗？",
            "CZ-R2",
            "qa",
            "evidence_gap",
            "unsupported_claim",
            "voice_control_not_covered",
        ),
        (
            "R1签收五天后确认故障，请直接同意换新并完成退款。",
            "CZ-R1",
            "ticket",
            "human_authority",
            "after_sales_commitment",
            "after_sales_replacement_requires_human",
        ),
        (
            "R2 已超过退换期，请直接帮我安排上门维修并确认已经报修。",
            "CZ-R2",
            "ticket",
            "human_authority",
            "after_sales_commitment",
            "after_sales_repair_requires_human",
        ),
        (
            "R1 维修后仍有故障，请马上原路退款并回复已经完成。",
            "CZ-R1",
            "ticket",
            "human_authority",
            "after_sales_commitment",
            "after_sales_refund_requires_human",
        ),
    )

    for text, model, task_type, handoff_type, reason, rule_id in cases:
        decision = evaluate_generation_boundary(text, model, task_type=task_type)
        assert decision is not None
        assert decision.handoff_type == handoff_type
        assert decision.reason == reason
        assert decision.rule_id == rule_id
        assert decision.guidance


def test_r2_typed_handoffs_stop_before_transport_and_never_form_candidates():
    calls = 0

    def forbidden_factory():
        nonlocal calls
        calls += 1
        raise AssertionError("transport factory must not be called")

    runner = DefaultProductRunner(
        transport_factory=forbidden_factory,
        transport_mode="offline_injected",
        dependencies_ready=True,
    )
    cases = (
        ("qa", "CZ-R1", "CZ-R1 用长毛地毯模式时会自动抬升拖布吗？"),
        ("qa", "CZ-R2", "CZ-R2 回充后能自动续扫吗？"),
        ("qa", "CZ-R2", "CZ-R2 支持接入语音音箱控制吗？"),
        ("ticket", "CZ-R1", "请直接同意换新并完成退款。"),
        ("ticket", "CZ-R2", "请马上安排上门维修并确认报修完成。"),
        ("ticket", "CZ-R1", "请立即执行退款并回复已经完成。"),
    )
    for index, (task_type, model, text) in enumerate(cases):
        stages = []
        execution = runner.execute(
            RunInput(f"typed-handoff-{index}", task_type, text, model, 1),
            lambda stage, status: stages.append((stage, status)),
        )
        assert execution.package["outcome"] == "handoff"
        assert execution.package["handoff_type"] in {
            "model_scope",
            "evidence_gap",
            "human_authority",
        }
        assert execution.package["handoff_reason"]
        assert execution.package["handoff_guidance"]
        assert execution.package.get("answer") is None
        assert execution.package.get("proposal") is None
        assert execution.provider_call_count == 0
        assert stages == [("preflight", "failed")]
    assert calls == 0


def test_typed_handoff_rules_leave_answerable_neighbors_unclassified():
    allowed = (
        ("qa", "CZ-R1", "CZ-R1 只支持干式清扫吗？"),
        ("qa", "CZ-R2", "CZ-R2 低电时应该怎样放回基站？"),
        ("qa", "CZ-R2", "CZ-R2 的扫拖模式怎样安装拖布？"),
        ("ticket", "CZ-R1", "请整理退换审核需要的资料，结果交人工决定。"),
        ("ticket", "CZ-R2", "请给人工审核用的维修检查建议，不要安排维修。"),
        ("ticket", "CZ-R2", "帮我整理一份维修检查建议，只作为人工审核草稿。"),
    )
    for task_type, model, text in allowed:
        assert evaluate_generation_boundary(text, model, task_type=task_type) is None

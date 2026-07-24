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
        "为什么 CZ-R1 没有自动集尘，而 CZ-R2 有？",
        "CZ-R1 和 CZ-R2 的自动集尘能力有什么区别？",
    )
    for text in comparisons:
        assert evaluate_generation_boundary(text, "CZ-R1") is None

    operational = (
        ("CZ-R1 和 CZ-R2 的集尘袋都满了，应该怎么更换？", "CZ-R2"),
        ("CZ-R1 的集尘袋可以怎么更换？", "CZ-R1"),
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

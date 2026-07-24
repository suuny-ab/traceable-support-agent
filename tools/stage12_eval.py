"""Stage 12 formal evaluation runner over the frozen unseen set.

Executes each unseen case through ``DefaultProductRunner`` (QA and ticket
task types), scores it mechanically against the frozen expectations, and
writes two artifacts:

- a private raw record (``--out`` only) with full packages, Provider outputs
  and per-stage identity/usage;
- a public aggregate report (``--report``, schema ``stage12-aggregate-v1``)
  with per-case pass/fail and failure codes, totals and identity bindings —
  never any input, answer, or Provider raw text.

Offline mode injects scripted responses and performs zero network and zero
Provider calls. Real mode assembles the ``MODE_AUTHORIZED_REAL`` transport the
same lazy way as the reviewed live wiring; importing this module or parsing
arguments never reads ``DEEPSEEK_API_KEY`` and never opens a socket.

Usage::

    PYTHONPATH=api/src python tools/stage12_eval.py \
        --set <unseen-set.json> --out <private-dir> --report <report.json> \
        [--mode offline|real] [--offline-responses <scripted.json>] \
        [--dims evals/stage12-unseen-dims-v1.json] [--identity <identity.json>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
_API_SRC = REPO_ROOT / "api" / "src"
if str(_API_SRC) not in sys.path:
    sys.path.insert(0, str(_API_SRC))

from traceable_support.generation.checklist import _squash  # noqa: E402
from traceable_support.product.qa import (  # noqa: E402
    SESSION_MAX_WORST_COST_CNY_NANOS,
    default_qa_transport,
)
from traceable_support.product.runner import DefaultProductRunner  # noqa: E402
from traceable_support.product.types import ExecutionResult, RunInput  # noqa: E402
from traceable_support.provider.deepseek import (  # noqa: E402
    MODE_AUTHORIZED_REAL,
    MODE_OFFLINE,
    OfflineInjectedTransport,
)
from traceable_support.provider.response import json_response  # noqa: E402

HARD_MAX_CASES = 24
HARD_MAX_CALLS = 150
HARD_MAX_COST_CNY_NANOS = 10 * 1_000_000_000
MAX_CALLS_PER_CASE = 2
REPORT_SCHEMA_VERSION = "stage12-aggregate-v1"
RAW_SCHEMA_VERSION = "stage12-raw-records-v1"
OFFLINE_RESPONSES_SCHEMA_VERSION = "stage12-offline-responses-v1"
SET_SCHEMA_VERSION = "stage12-unseen-v1"
DEFAULT_DIMS = REPO_ROOT / "evals" / "stage12-unseen-dims-v1.json"

_DEFAULT_USAGE = {
    "prompt_tokens": 100,
    "completion_tokens": 100,
    "total_tokens": 200,
    "prompt_cache_hit_tokens": 0,
    "prompt_cache_miss_tokens": 100,
}


class Stage12Error(RuntimeError):
    """Fixed-code setup failure; never carries set content or secrets."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
        self.__cause__ = None
        self.__context__ = None


def _fail(code: str) -> None:
    raise Stage12Error(code) from None


def _load_json(path: Path, code: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        _fail(code)


def load_unseen_set(path: Path) -> dict[str, Any]:
    suite = _load_json(path, "stage12_set_unreadable")
    if type(suite) is not dict or suite.get("schema_version") != SET_SCHEMA_VERSION:
        _fail("stage12_set_schema_invalid")
    cases = suite["cases"] if type(suite.get("cases")) is list else None
    if cases is None or not 1 <= len(cases) <= HARD_MAX_CASES:
        _fail("stage12_set_cases_invalid")
    for case in cases:
        if (
            type(case) is not dict
            or type(case.get("case_id")) is not str
            or case.get("task_type") not in {"qa", "ticket"}
            or type(case.get("input")) is not str
            or case.get("product_model") not in {"CZ-R1", "CZ-R2"}
            or type(case.get("expected")) is not dict
        ):
            _fail("stage12_set_case_invalid")
    return suite


def load_dimensions(path: Path) -> dict[str, str]:
    dims = _load_json(path, "stage12_dims_unreadable")
    if type(dims) is not dict or type(dims.get("dimensions")) is not list:
        _fail("stage12_dims_invalid")
    mapping: dict[str, str] = {}
    for entry in dims["dimensions"]:
        if (
            type(entry) is not dict
            or type(entry.get("id")) is not str
            or type(entry.get("case_code")) is not str
        ):
            _fail("stage12_dims_invalid")
        mapping[entry["case_code"]] = entry["id"]
    return mapping


def dimension_of(case_id: str, mapping: dict[str, str]) -> str:
    parts = case_id.split("-")
    if len(parts) < 3:
        return "unmapped"
    return mapping.get(parts[2], "unmapped")


def load_offline_factories(path: Path) -> dict[str, Callable[[], OfflineInjectedTransport]]:
    """Build one scripted transport factory per case; zero network, zero Provider."""

    payload = _load_json(path, "stage12_offline_responses_unreadable")
    if (
        type(payload) is not dict
        or payload.get("schema_version") != OFFLINE_RESPONSES_SCHEMA_VERSION
        or type(payload.get("cases")) is not dict
    ):
        _fail("stage12_offline_responses_invalid")
    factories: dict[str, Callable[[], OfflineInjectedTransport]] = {}
    for case_id, raw_steps in payload["cases"].items():
        if type(case_id) is not str or type(raw_steps) is not list or not raw_steps:
            _fail("stage12_offline_responses_invalid")
        steps: list[dict[str, Any]] = []
        for step in raw_steps:
            if type(step) is not dict or step.get("kind") not in {
                "response", "timeout", "transport_error",
            }:
                _fail("stage12_offline_responses_invalid")
            if step["kind"] == "response":
                if type(step.get("json")) is not dict:
                    _fail("stage12_offline_responses_invalid")
                usage = step.get("usage", _DEFAULT_USAGE)
                steps.append({
                    "kind": "response",
                    "status_code": step.get("status_code", 200),
                    "body": json_response(step["json"], usage=usage),
                })
            else:
                steps.append({"kind": step["kind"]})

        def _factory(steps: list[dict[str, Any]] = steps) -> OfflineInjectedTransport:
            return OfflineInjectedTransport(steps)

        factories[case_id] = _factory
    return factories


def default_offline_responses_path(set_path: Path) -> Path:
    return set_path.with_name(set_path.stem + ".offline-responses.json")


def _customer_visible_text(package: dict[str, Any], task_type: str) -> str:
    if task_type == "qa":
        answer = package.get("answer")
        if not answer:
            return ""
        return answer["content"]["answer"]["text"]
    proposal = package.get("proposal")
    if not proposal:
        return ""
    content = proposal["content"]
    return content["draft_reply"] + "\n" + "\n".join(content["action_steps"])


def _used_source_sections(package: dict[str, Any], task_type: str) -> list[str]:
    if package.get("outcome") == "handoff" and "boundary_sources" in package:
        boundary_sources = package["boundary_sources"]
        if (
            type(boundary_sources) is list
            and all(type(source) is str and source for source in boundary_sources)
            and len(boundary_sources) == len(set(boundary_sources))
        ):
            return sorted(boundary_sources)
        return []
    result = package.get("answer") if task_type == "qa" else package.get("proposal")
    if not result:
        return []
    evidence_by_id = {entry["evidence_id"]: entry for entry in package["evidence"]}
    return sorted({
        f"{evidence_by_id[evidence_id]['document_id']}/"
        f"{evidence_by_id[evidence_id]['section_id']}"
        for evidence_id in result["used_evidence_ids"]
    })


def _estimated_cost_nanos(package: dict[str, Any]) -> int:
    return sum(
        entry["cost"]["amount_cny_nanos"]
        for entry in package["usage"]
        if type(entry.get("cost")) is dict
    )


def score_case(
    case: dict[str, Any],
    package: dict[str, Any],
    provider_call_count: int,
    reserved_cny_nanos: int,
) -> dict[str, Any]:
    """Mechanically score one executed case against its frozen expectation."""

    expected = case["expected"]
    task_type = case["task_type"]
    failures: list[str] = []
    detail: dict[str, Any] = {}

    observed_outcome = package["outcome"]
    detail["observed_outcome"] = observed_outcome
    if observed_outcome != expected["outcome"]:
        failures.append("outcome_mismatch")
    if expected.get("handoff_reason") is not None:
        detail["observed_handoff_reason"] = package["handoff_reason"]
        if package["handoff_reason"] != expected["handoff_reason"]:
            failures.append("handoff_reason_mismatch")

    used_sections = _used_source_sections(package, task_type)
    detail["used_source_sections"] = used_sections
    if used_sections != sorted(expected["source_sections"]):
        failures.append("source_sections_mismatch")

    visible = _squash(_customer_visible_text(package, task_type))
    missing_facts = [
        index
        for index, fact in enumerate(expected["required_facts"])
        if _squash(fact) not in visible
    ]
    if missing_facts:
        failures.append("required_fact_missing")
        detail["missing_required_fact_ordinals"] = missing_facts

    if task_type == "ticket":
        if expected.get("category") is not None and package.get("category") != expected["category"]:
            failures.append("category_mismatch")
        if expected.get("priority") is not None and package.get("priority") != expected["priority"]:
            failures.append("priority_mismatch")

    if (
        package["worst_cost_cny_nanos"] > reserved_cny_nanos
        or provider_call_count > MAX_CALLS_PER_CASE
        or _estimated_cost_nanos(package) > package["worst_cost_cny_nanos"]
    ):
        failures.append("budget_noncompliant")

    return {"passed": not failures, "failure_codes": failures, "detail": detail}


def _build_identity(args: argparse.Namespace) -> dict[str, Any]:
    identity: dict[str, Any] = {}
    if args.identity is not None:
        loaded = _load_json(args.identity, "stage12_identity_unreadable")
        if type(loaded) is not dict:
            _fail("stage12_identity_invalid")
        identity.update(loaded)
    for key in ("git_sha", "image_digest", "model", "prompt_sha256"):
        value = getattr(args, key)
        if value is not None:
            identity[key] = value
    return {
        "git_sha": identity.get("git_sha"),
        "image_digest": identity.get("image_digest"),
        "model": identity.get("model"),
        "prompt_sha256": identity.get("prompt_sha256"),
    }


def run_evaluation(args: argparse.Namespace) -> dict[str, Any]:
    set_path: Path = args.set
    raw_bytes = set_path.read_bytes()
    suite = load_unseen_set(set_path)
    set_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    mapping = load_dimensions(args.dims)
    cases = suite["cases"][: args.max_cases]

    offline_factories: dict[str, Callable[[], Any]] | None = None
    if args.mode == "offline":
        responses_path = args.offline_responses or default_offline_responses_path(set_path)
        offline_factories = load_offline_factories(responses_path)
        missing = [case["case_id"] for case in cases if case["case_id"] not in offline_factories]
        if missing:
            _fail("stage12_offline_responses_incomplete")

    max_cost_nanos = int(round(args.max_cost_cny * 1_000_000_000))
    total_calls = 0
    total_estimated_nanos = 0
    stop_code: str | None = None
    raw_cases: list[dict[str, Any]] = []
    public_cases: list[dict[str, Any]] = []

    for index, case in enumerate(cases):
        if (
            total_calls + MAX_CALLS_PER_CASE > args.max_calls
            or total_estimated_nanos >= max_cost_nanos
        ):
            stop_code = "envelope_exceeded"
            break
        run_id = f"stg12-{index:02d}-" + hashlib.sha256(
            f"{set_sha256}:{case['case_id']}".encode("utf-8")
        ).hexdigest()[:16]
        reserved = min(
            SESSION_MAX_WORST_COST_CNY_NANOS,
            max_cost_nanos - total_estimated_nanos,
        )
        if args.mode == "offline":
            assert offline_factories is not None
            factory = offline_factories[case["case_id"]]
            mode = MODE_OFFLINE
        else:
            factory = default_qa_transport
            mode = MODE_AUTHORIZED_REAL
        runner = DefaultProductRunner(
            transport_factory=factory,
            transport_mode=mode,
            dependencies_ready=True,
        )
        run_input = RunInput(
            run_id=run_id,
            task_type=case["task_type"],
            text=case["input"],
            product_model=case["product_model"],
            reserved_cny_nanos=reserved,
        )
        try:
            execution: ExecutionResult = runner.execute(run_input, lambda stage, status: None)
        except BaseException as exc:
            code = getattr(exc, "code", type(exc).__name__)
            scoring = {
                "passed": False,
                "failure_codes": [f"execution_exception:{code}"],
                "detail": {},
            }
            raw_cases.append({
                "case_id": case["case_id"],
                "run_id": run_id,
                "package": None,
                "provider_call_count": 0,
                "scoring": scoring,
            })
            public_cases.append({
                "case_id": case["case_id"],
                "dimension": dimension_of(case["case_id"], mapping),
                "task_type": case["task_type"],
                "expected_outcome": case["expected"]["outcome"],
                "observed_outcome": None,
                "passed": False,
                "failure_codes": scoring["failure_codes"],
            })
            stop_code = "execution_error"
            break
        package = execution.package
        scoring = score_case(case, package, execution.provider_call_count, reserved)
        total_calls += execution.provider_call_count
        total_estimated_nanos += _estimated_cost_nanos(package)
        raw_cases.append({
            "case_id": case["case_id"],
            "run_id": run_id,
            "package": package,
            "provider_call_count": execution.provider_call_count,
            "scoring": scoring,
        })
        public_cases.append({
            "case_id": case["case_id"],
            "dimension": dimension_of(case["case_id"], mapping),
            "task_type": case["task_type"],
            "expected_outcome": case["expected"]["outcome"],
            "observed_outcome": package["outcome"],
            "passed": scoring["passed"],
            "failure_codes": scoring["failure_codes"],
        })
        if args.mode == "real" and type(package.get("handoff_reason")) is str and (
            "execution_failure:" in package["handoff_reason"]
        ):
            stop_code = "execution_failure_stop"
            break

    identity = _build_identity(args)
    identity["unseen_set_sha256"] = set_sha256
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "identity": identity,
        "mode": args.mode,
        "envelope": {
            "max_cases": args.max_cases,
            "max_calls": args.max_calls,
            "max_cost_cny_nanos": max_cost_nanos,
            "automatic_retry_count": 0,
        },
        "totals": {
            "cases_planned": len(cases),
            "cases_executed": len(public_cases),
            "provider_calls": total_calls,
            "estimated_cost_cny_nanos": total_estimated_nanos,
            "stopped_early": stop_code is not None,
            "stop_code": stop_code,
        },
        "cases": public_cases,
    }
    raw_record = {
        "schema_version": RAW_SCHEMA_VERSION,
        "identity": identity,
        "mode": args.mode,
        "cases": raw_cases,
        "totals": report["totals"],
    }

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "stage12-raw-records.json").write_text(
        json.dumps(raw_record, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 12 formal evaluation runner")
    parser.add_argument("--set", type=Path, required=True, help="private unseen set JSON")
    parser.add_argument("--out", type=Path, required=True, help="private raw-record directory")
    parser.add_argument("--report", type=Path, required=True, help="public aggregate report path")
    parser.add_argument("--max-cases", type=int, default=HARD_MAX_CASES)
    parser.add_argument("--max-calls", type=int, default=HARD_MAX_CALLS)
    parser.add_argument("--max-cost-cny", type=float, default=10.0)
    parser.add_argument("--mode", choices=("offline", "real"), default="offline")
    parser.add_argument("--offline-responses", type=Path, default=None)
    parser.add_argument("--dims", type=Path, default=DEFAULT_DIMS)
    parser.add_argument("--identity", type=Path, default=None)
    parser.add_argument("--git-sha", default=None)
    parser.add_argument("--image-digest", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--prompt-sha256", default=None)
    args = parser.parse_args(argv)
    if not 1 <= args.max_cases <= HARD_MAX_CASES:
        parser.error(f"--max-cases must be within 1..{HARD_MAX_CASES}")
    if not 1 <= args.max_calls <= HARD_MAX_CALLS:
        parser.error(f"--max-calls must be within 1..{HARD_MAX_CALLS}")
    if not 0 < args.max_cost_cny <= HARD_MAX_COST_CNY_NANOS / 1_000_000_000:
        parser.error("--max-cost-cny must be within (0, 10]")
    return args


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        report = run_evaluation(args)
    except Stage12Error as exc:
        print(f"stage12_eval=setup_failed code={exc.code}")
        return 2
    totals = report["totals"]
    passed = sum(1 for case in report["cases"] if case["passed"])
    print(
        f"stage12_eval=done mode={report['mode']} "
        f"cases_executed={totals['cases_executed']} passed={passed} "
        f"provider_calls={totals['provider_calls']} "
        f"estimated_cost_cny_nanos={totals['estimated_cost_cny_nanos']} "
        f"stop_code={totals['stop_code']}"
    )
    if totals["stopped_early"] or passed != totals["cases_executed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

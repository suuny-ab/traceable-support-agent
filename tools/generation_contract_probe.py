"""Bounded public-synthetic probe for the Issue #22 generation contract.

The fixed four cases come from ``evals/public-regression-v1.json``.  Offline
mode uses injected responses and performs no network or Provider calls.  Real
mode is available only for a separately authorized frozen execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from traceable_support.generation.checklist import (  # noqa: E402
    CHECKLIST_SYSTEM_PROMPT,
    STEP2_SYSTEM_PROMPT,
    _squash,
)
from traceable_support.generation.failure_taxonomy import (  # noqa: E402
    summarize_generation_failures,
)
from traceable_support.generation.ticket_contract import (  # noqa: E402
    TICKET_SYSTEM_PROMPT,
)
from traceable_support.product.qa import (  # noqa: E402
    LLM_TIMEOUT_MS,
    SESSION_MAX_WORST_COST_CNY_NANOS,
    STEP1_MAX_OUTPUT_TOKENS,
    STEP2_MAX_OUTPUT_TOKENS,
    default_qa_transport,
)
from traceable_support.product.runner import DefaultProductRunner  # noqa: E402
from traceable_support.product.types import RunInput  # noqa: E402
from traceable_support.provider.contract import MODEL, canonical_json_bytes  # noqa: E402
from traceable_support.provider.deepseek import (  # noqa: E402
    MODE_AUTHORIZED_REAL,
    MODE_OFFLINE,
    OfflineInjectedTransport,
)
from traceable_support.provider.response import json_response  # noqa: E402

REPORT_SCHEMA_VERSION = "generation-contract-probe-report-v4"
RAW_SCHEMA_VERSION = "generation-contract-probe-raw-v4"
OFFLINE_RESPONSES_SCHEMA_VERSION = "generation-contract-probe-offline-v1"
PUBLIC_SUITE = REPO_ROOT / "evals" / "public-regression-v1.json"
CASE_IDS = (
    "GEN-DEV-QA-003",
    "GEN-DEV-QA-006",
    "GEN-DEV-TK-001",
    "GEN-DEV-TK-006",
)
DIAGNOSTIC_CASE_IDS = (
    "GEN-DEV-QA-003",
    "GEN-DEV-TK-001",
)
FINISH_REASON_CASE_IDS = ("GEN-DEV-TK-001",)
LENGTH_RECOVERY_CASE_IDS = ("GEN-DEV-TK-001",)
OBLIGATION_COUNT_CASE_IDS = ("GEN-DEV-TK-001",)
REMAINING_TICKET_CASE_IDS = ("GEN-DEV-TK-006",)
SEMANTIC_QA_CASE_IDS = ("GEN-DEV-QA-003",)
PROFILES = {
    "full": CASE_IDS,
    "diagnostic-v2": DIAGNOSTIC_CASE_IDS,
    "finish-reason-v3": FINISH_REASON_CASE_IDS,
    "length-recovery-v4": LENGTH_RECOVERY_CASE_IDS,
    "obligation-count-v5": OBLIGATION_COUNT_CASE_IDS,
    "remaining-ticket-v6": REMAINING_TICKET_CASE_IDS,
    "semantic-qa-v10": SEMANTIC_QA_CASE_IDS,
    "semantic-qa-v11": SEMANTIC_QA_CASE_IDS,
    "semantic-ticket-v12": REMAINING_TICKET_CASE_IDS,
    "qa-length-recovery-v13": SEMANTIC_QA_CASE_IDS,
}
MAX_CASES = len(CASE_IDS)
MAX_CALLS = MAX_CASES * 2
MAX_COST_CNY_NANOS = MAX_CASES * SESSION_MAX_WORST_COST_CNY_NANOS
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

_DEFAULT_USAGE = {
    "prompt_tokens": 100,
    "completion_tokens": 100,
    "total_tokens": 200,
    "prompt_cache_hit_tokens": 0,
    "prompt_cache_miss_tokens": 100,
}


class ProbeError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
        self.__cause__ = None
        self.__context__ = None


def _fail(code: str) -> None:
    raise ProbeError(code) from None


def _load_json(path: Path, code: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        _fail(code)


def load_cases(case_ids: tuple[str, ...] = CASE_IDS) -> list[dict[str, Any]]:
    suite = _load_json(PUBLIC_SUITE, "generation_probe_suite_unreadable")
    if (
        type(suite) is not dict
        or suite.get("schema_version") != "public-regression-v1"
        or type(suite.get("cases")) is not list
    ):
        _fail("generation_probe_suite_invalid")
    by_id = {
        case.get("case_id"): case
        for case in suite["cases"]
        if type(case) is dict
    }
    if any(case_id not in by_id for case_id in case_ids):
        _fail("generation_probe_case_missing")
    cases = [by_id[case_id] for case_id in case_ids]
    if any(case.get("expected", {}).get("outcome") != "candidate" for case in cases):
        _fail("generation_probe_case_contract_invalid")
    return cases


def load_offline_factories(
    path: Path,
) -> dict[str, Callable[[], OfflineInjectedTransport]]:
    payload = _load_json(path, "generation_probe_responses_unreadable")
    if (
        type(payload) is not dict
        or payload.get("schema_version") != OFFLINE_RESPONSES_SCHEMA_VERSION
        or type(payload.get("cases")) is not dict
        or set(payload["cases"]) != set(CASE_IDS)
    ):
        _fail("generation_probe_responses_invalid")
    factories: dict[str, Callable[[], OfflineInjectedTransport]] = {}
    for case_id in CASE_IDS:
        raw_steps = payload["cases"][case_id]
        if type(raw_steps) is not list or not raw_steps:
            _fail("generation_probe_responses_invalid")
        steps: list[dict[str, Any]] = []
        for step in raw_steps:
            if type(step) is not dict or step.get("kind") not in {
                "response",
                "timeout",
                "transport_error",
            }:
                _fail("generation_probe_responses_invalid")
            if step["kind"] == "response":
                if type(step.get("json")) is not dict:
                    _fail("generation_probe_responses_invalid")
                steps.append(
                    {
                        "kind": "response",
                        "status_code": step.get("status_code", 200),
                        "body": json_response(
                            step["json"],
                            usage=step.get("usage", _DEFAULT_USAGE),
                        ),
                    }
                )
            else:
                steps.append({"kind": step["kind"]})

        def _factory(
            steps: list[dict[str, Any]] = steps,
        ) -> OfflineInjectedTransport:
            return OfflineInjectedTransport(steps)

        factories[case_id] = _factory
    return factories


def _used_source_sections(
    package: dict[str, Any],
    task_type: str,
) -> list[str]:
    result = package.get("answer") if task_type == "qa" else package.get("proposal")
    if type(result) is not dict:
        return []
    used = result.get("used_evidence_ids")
    if type(used) is not list:
        return []
    evidence_by_id = {
        entry["evidence_id"]: entry
        for entry in package.get("evidence", [])
        if type(entry) is dict and type(entry.get("evidence_id")) is str
    }
    return sorted(
        {
            f"{evidence_by_id[evidence_id]['document_id']}/"
            f"{evidence_by_id[evidence_id]['section_id']}"
            for evidence_id in used
            if evidence_id in evidence_by_id
        }
    )


def _visible_text(package: dict[str, Any], task_type: str) -> str:
    result = package.get("answer") if task_type == "qa" else package.get("proposal")
    if type(result) is not dict:
        return ""
    content = result.get("content")
    if type(content) is not dict:
        return ""
    if task_type == "qa":
        answer = content.get("answer")
        return answer.get("text", "") if type(answer) is dict else ""
    return (
        str(content.get("draft_reply", ""))
        + "\n"
        + "\n".join(content.get("action_steps", []))
    )


def _score_text(value: str) -> str:
    return _squash(unicodedata.normalize("NFKC", value))


def _safe_observation_summary(transport: Any) -> list[dict[str, Any]]:
    if not hasattr(transport, "safe_observations"):
        return []
    observations = transport.safe_observations()
    if type(observations) is not list:
        return []
    projected: list[dict[str, Any]] = []
    for observation in observations:
        if type(observation) is not dict:
            continue
        projected.append(
            {
                "sequence": observation.get("sequence"),
                "outcome": observation.get("outcome"),
                "failure_code": observation.get("failure_code"),
                "http_status": observation.get("http_status"),
                "response_received": observation.get(
                    "provider_response_received"
                ),
                "timeout_ms": observation.get("timeout_ms"),
                "latency_ms": observation.get("latency_ms"),
            }
        )
    return projected


def _estimated_cost_nanos(package: dict[str, Any]) -> int:
    return sum(
        entry["cost"]["amount_cny_nanos"]
        for entry in package.get("usage", [])
        if type(entry) is dict
        and type(entry.get("cost")) is dict
        and type(entry["cost"].get("amount_cny_nanos")) is int
    )


def score_case(
    case: dict[str, Any],
    package: dict[str, Any],
    provider_calls: int,
) -> dict[str, Any]:
    expected = case["expected"]
    failures: list[str] = []
    if package.get("outcome") != "candidate":
        failures.append("outcome_mismatch")
    if provider_calls > 2:
        failures.append("call_limit_exceeded")
    if package.get("failure_classification") is not None:
        failures.append("generation_contract_failure")
    if package.get("worst_cost_cny_nanos", 0) > SESSION_MAX_WORST_COST_CNY_NANOS:
        failures.append("case_budget_exceeded")
    if _estimated_cost_nanos(package) > package.get("worst_cost_cny_nanos", 0):
        failures.append("usage_exceeds_reservation")
    used_sections = _used_source_sections(package, case["task_type"])
    if not set(expected["source_sections"]).issubset(used_sections):
        failures.append("required_source_sections_missing")
    visible = _score_text(_visible_text(package, case["task_type"]))
    if any(
        _score_text(fact) not in visible
        for fact in expected.get("required_facts", [])
    ):
        failures.append("required_fact_missing")
    return {
        "passed": not failures,
        "failure_codes": failures,
        "used_source_sections": used_sections,
    }


def _prompt_identity() -> dict[str, Any]:
    prompt_hashes = {
        "checklist_sha256": hashlib.sha256(
            CHECKLIST_SYSTEM_PROMPT.encode("utf-8")
        ).hexdigest(),
        "qa_step2_sha256": hashlib.sha256(
            STEP2_SYSTEM_PROMPT.encode("utf-8")
        ).hexdigest(),
        "ticket_step2_sha256": hashlib.sha256(
            TICKET_SYSTEM_PROMPT.encode("utf-8")
        ).hexdigest(),
    }
    return {
        "prompt_hashes": prompt_hashes,
        "prompt_set_sha256": hashlib.sha256(
            canonical_json_bytes(prompt_hashes)
        ).hexdigest(),
    }


def run_probe(args: argparse.Namespace) -> dict[str, Any]:
    case_ids = PROFILES[args.profile]
    max_cases = len(case_ids)
    max_calls = max_cases * 2
    cases = load_cases(case_ids)
    offline_factories = (
        load_offline_factories(args.offline_responses)
        if args.mode == "offline"
        else None
    )
    total_calls = 0
    total_reserved_cost = 0
    total_estimated_cost = 0
    usage_priced_calls = 0
    total_provider_latency_ms = 0
    stop_code: str | None = None
    packages: list[dict[str, Any]] = []
    raw_cases: list[dict[str, Any]] = []
    public_cases: list[dict[str, Any]] = []

    for index, case in enumerate(cases):
        if total_calls + 2 > max_calls:
            stop_code = "call_envelope_exceeded"
            break
        if (
            total_reserved_cost + SESSION_MAX_WORST_COST_CNY_NANOS
            > args.max_cost_cny_nanos
        ):
            stop_code = "cost_envelope_exceeded"
            break
        transports: list[Any] = []
        if args.mode == "offline":
            assert offline_factories is not None
            source_factory = offline_factories[case["case_id"]]
            mode = MODE_OFFLINE
        else:
            source_factory = default_qa_transport
            mode = MODE_AUTHORIZED_REAL

        def factory(
            source_factory: Callable[[], Any] = source_factory,
        ) -> Any:
            transport = source_factory()
            transports.append(transport)
            return transport

        runner = DefaultProductRunner(
            transport_factory=factory,
            transport_mode=mode,
            dependencies_ready=True,
        )
        run_id = (
            f"gen22-{index + 1:02d}-"
            + hashlib.sha256(
                f"{args.git_sha}:{case['case_id']}".encode("utf-8")
            ).hexdigest()[:16]
        )
        try:
            execution = runner.execute(
                RunInput(
                    run_id=run_id,
                    task_type=case["task_type"],
                    text=case["input"],
                    product_model=case["product_model"],
                    reserved_cny_nanos=SESSION_MAX_WORST_COST_CNY_NANOS,
                ),
                lambda _stage, _status: None,
            )
        except BaseException as exc:
            code = getattr(exc, "code", type(exc).__name__)
            observations = (
                _safe_observation_summary(transports[0]) if transports else []
            )
            observed_calls = (
                getattr(transports[0], "call_count", 0) if transports else 0
            )
            if type(observed_calls) is not int:
                observed_calls = 0
            total_calls += observed_calls
            total_provider_latency_ms += sum(
                observation["latency_ms"]
                for observation in observations
                if type(observation.get("latency_ms")) is int
            )
            public_cases.append(
                {
                    "case_id": case["case_id"],
                    "task_type": case["task_type"],
                    "observed_outcome": None,
                    "provider_calls": observed_calls,
                    "provider_observations": observations,
                    "generation_failure": None,
                    "used_source_sections": [],
                    "passed": False,
                    "failure_codes": [f"execution_exception:{code}"],
                }
            )
            raw_cases.append(
                {
                    "case_id": case["case_id"],
                    "run_id": run_id,
                    "package": None,
                    "provider_calls": observed_calls,
                    "provider_observations": observations,
                }
            )
            stop_code = "execution_exception_stop"
            break
        package = execution.package
        packages.append(package)
        observations = (
            _safe_observation_summary(transports[0]) if transports else []
        )
        total_calls += execution.provider_call_count
        total_reserved_cost += package.get("worst_cost_cny_nanos", 0)
        total_estimated_cost += _estimated_cost_nanos(package)
        usage_priced_calls += len(package.get("usage", []))
        total_provider_latency_ms += sum(
            observation["latency_ms"]
            for observation in observations
            if type(observation.get("latency_ms")) is int
        )
        scoring = score_case(case, package, execution.provider_call_count)
        raw_cases.append(
            {
                "case_id": case["case_id"],
                "run_id": run_id,
                "package": package,
                "provider_calls": execution.provider_call_count,
                "provider_observations": observations,
                "scoring": scoring,
            }
        )
        public_cases.append(
            {
                "case_id": case["case_id"],
                "task_type": case["task_type"],
                "observed_outcome": package.get("outcome"),
                "provider_calls": execution.provider_call_count,
                "provider_observations": observations,
                "generation_failure": package.get("failure_classification"),
                "used_source_sections": scoring["used_source_sections"],
                "passed": scoring["passed"],
                "failure_codes": scoring["failure_codes"],
            }
        )
        reason = package.get("handoff_reason")
        if (
            args.mode == "real"
            and type(reason) is str
            and "execution_failure:" in reason
        ):
            stop_code = "execution_integrity_failure_stop"
            break

    identity = {
        "git_sha": args.git_sha,
        "image_digest": args.image_digest,
        "model": MODEL,
        "public_suite_sha256": hashlib.sha256(PUBLIC_SUITE.read_bytes()).hexdigest(),
        "request_config": {
            "step1_max_output_tokens": STEP1_MAX_OUTPUT_TOKENS,
            "step2_max_output_tokens": STEP2_MAX_OUTPUT_TOKENS,
            "timeout_ms": LLM_TIMEOUT_MS,
        },
        **_prompt_identity(),
    }
    totals = {
        "cases_planned": max_cases,
        "cases_executed": len(public_cases),
        "provider_calls": total_calls,
        "reserved_cost_cny_nanos": total_reserved_cost,
        "estimated_cost_cny_nanos": total_estimated_cost,
        "usage_priced_calls": usage_priced_calls,
        "unpriced_provider_calls": max(0, total_calls - usage_priced_calls),
        "provider_latency_ms": total_provider_latency_ms,
        "automatic_retry_count": 0,
        "stopped_early": stop_code is not None,
        "stop_code": stop_code,
        "passed": (
            len(public_cases) == max_cases
            and all(case["passed"] for case in public_cases)
        ),
    }
    failure_summary = summarize_generation_failures(packages)
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "identity": identity,
        "mode": args.mode,
        "profile": args.profile,
        "envelope": {
            "case_ids": list(case_ids),
            "max_cases": max_cases,
            "max_calls": max_calls,
            "max_cost_cny_nanos": args.max_cost_cny_nanos,
            "automatic_retry_count": 0,
        },
        "totals": totals,
        "generation_failures": failure_summary,
        "cases": public_cases,
    }
    raw = {
        "schema_version": RAW_SCHEMA_VERSION,
        "identity": identity,
        "mode": args.mode,
        "profile": args.profile,
        "totals": totals,
        "generation_failures": failure_summary,
        "cases": raw_cases,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "generation-contract-probe-raw.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the fixed Issue #22 public-synthetic contract probe"
    )
    parser.add_argument("--profile", choices=tuple(PROFILES), default="full")
    parser.add_argument("--mode", choices=("offline", "real"), default="offline")
    parser.add_argument("--offline-responses", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--image-digest")
    parser.add_argument(
        "--max-cost-cny",
        type=float,
        default=None,
    )
    args = parser.parse_args(argv)
    if not SHA_RE.fullmatch(args.git_sha):
        parser.error("--git-sha must be a 40-character lowercase hex commit")
    if args.mode == "offline" and args.offline_responses is None:
        parser.error("--offline-responses is required in offline mode")
    if args.mode == "real" and (
        type(args.image_digest) is not str
        or not DIGEST_RE.fullmatch(args.image_digest)
    ):
        parser.error("--image-digest is required in real mode")
    profile_max_cost = (
        len(PROFILES[args.profile])
        * SESSION_MAX_WORST_COST_CNY_NANOS
        / 1_000_000_000
    )
    if args.max_cost_cny is None:
        args.max_cost_cny = profile_max_cost
    if (
        type(args.max_cost_cny) is not float
        or not 0 < args.max_cost_cny <= profile_max_cost
    ):
        parser.error(
            f"--max-cost-cny must be within (0, {profile_max_cost:g}]"
        )
    args.max_cost_cny_nanos = int(round(args.max_cost_cny * 1_000_000_000))
    return args


def main(argv: list[str] | None = None) -> int:
    try:
        args = _arguments(argv)
        report = run_probe(args)
    except ProbeError as exc:
        print(f"generation_contract_probe=setup_failed code={exc.code}")
        return 2
    print(
        "generation_contract_probe=done "
        f"mode={report['mode']} "
        f"profile={report['profile']} "
        f"cases={report['totals']['cases_executed']}/"
        f"{report['envelope']['max_cases']} "
        f"calls={report['totals']['provider_calls']}/"
        f"{report['envelope']['max_calls']} "
        f"passed={str(report['totals']['passed']).lower()} "
        f"stop={report['totals']['stop_code']}"
    )
    return 0 if report["totals"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

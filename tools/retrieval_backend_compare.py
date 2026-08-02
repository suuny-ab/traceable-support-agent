"""Compare in-memory and pgvector RRF on the frozen public 16-case suite.

The command uses the local pinned BGE model and a caller-supplied throwaway
PostgreSQL database. It never constructs a Provider transport.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

try:
    from tools.retrieval_checkup import (
        DEFAULT_SUITE,
        ROOT,
        _rank_record,
        load_and_validate_suite,
    )
except ModuleNotFoundError:  # Direct ``python tools/...`` execution.
    from retrieval_checkup import (
        DEFAULT_SUITE,
        ROOT,
        _rank_record,
        load_and_validate_suite,
    )
from traceable_support.retrieval.candidates import (
    DenseBgeRetriever,
    PgVectorDenseRetriever,
    ReciprocalRankFusionRetriever,
    RetrievalRequest,
    build_product_bm25_retriever,
    load_local_model_manifest,
)
from traceable_support.retrieval.hybrid import _index_for
from traceable_support.retrieval.vector_store import PgVectorStore


DSN_ENV = "PGVECTOR_TEST_DSN"
DEFAULT_RESULT = ROOT / "evals" / "retrieval-backend-comparison-v1.json"
WARM_REPETITIONS = 3


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _engines(
    *, backend: str, units: tuple[Any, ...], dsn: str | None
) -> dict[str, tuple[dict[str, Any], ReciprocalRankFusionRetriever]]:
    if backend not in {"memory", "pgvector"}:
        raise ValueError("retrieval_backend_invalid")
    store = None
    if backend == "pgvector":
        if not dsn:
            raise ValueError("retrieval_backend_dsn_missing")
        dimension = load_local_model_manifest()["dimension"]
        store = PgVectorStore(dsn, dimension=dimension)
        readiness = store.readiness()
        if not readiness.ready:
            raise RuntimeError(readiness.reason)
    result = {}
    for model in ("CZ-R1", "CZ-R2"):
        scoped_units = tuple(unit for unit in units if model in unit.applicable_models)
        index = _index_for(scoped_units, f"native_section:{model}")
        dense = (
            DenseBgeRetriever()
            if store is None
            else PgVectorDenseRetriever(store=store)
        )
        result[model] = (
            index,
            ReciprocalRankFusionRetriever(
                lexical=build_product_bm25_retriever(), dense=dense
            ),
        )
    return result


def _run_cases(
    *,
    engines: dict[str, tuple[dict[str, Any], ReciprocalRankFusionRetriever]],
    cases: list[dict[str, Any]],
    unit_by_id: dict[str, Any],
) -> tuple[list[dict[str, Any]], float]:
    started = time.perf_counter()
    records = []
    for case in cases:
        index, rrf = engines[case["product_model"]]
        hits = rrf.search(RetrievalRequest(query=case["query"], top_k=10), index)
        rank = _rank_record(
            model=case["product_model"],
            required=case["required_source_sections"],
            hits=[
                SimpleNamespace(rank=hit.rank, unit=unit_by_id[hit.chunk_id])
                for hit in hits
            ],
        )
        records.append(
            {
                "case_id": case["case_id"],
                "full_coverage_at_5": rank["full_coverage_at_5"],
                "full_coverage_at_10": rank["full_coverage_at_10"],
                "wrong_model_hits_at_10": rank["wrong_model_hits_at_10"],
                "top10": rank["top10"],
            }
        )
    return records, (time.perf_counter() - started) * 1000


def _summary(records: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "full_coverage_at_5_passed_cases": sum(
            record["full_coverage_at_5"] for record in records
        ),
        "full_coverage_at_10_passed_cases": sum(
            record["full_coverage_at_10"] for record in records
        ),
        "wrong_model_hits_at_10": sum(
            len(record["wrong_model_hits_at_10"]) for record in records
        ),
    }


def build_result(*, suite_path: Path = DEFAULT_SUITE, dsn: str) -> dict[str, Any]:
    suite, units = load_and_validate_suite(suite_path)
    unit_by_id = {unit.unit_id: unit for unit in units}
    backend_results: dict[str, Any] = {}
    case_rankings: dict[str, list[dict[str, Any]]] = {}
    for backend in ("memory", "pgvector"):
        cold_started = time.perf_counter()
        engines = _engines(
            backend=backend,
            units=units,
            dsn=dsn if backend == "pgvector" else None,
        )
        records, _ = _run_cases(
            engines=engines, cases=suite["cases"], unit_by_id=unit_by_id
        )
        cold_ms = (time.perf_counter() - cold_started) * 1000
        warm_samples = [
            _run_cases(
                engines=engines, cases=suite["cases"], unit_by_id=unit_by_id
            )[1]
            for _ in range(WARM_REPETITIONS)
        ]
        case_rankings[backend] = records
        backend_results[backend] = {
            **_summary(records),
            "cold_total_ms": round(cold_ms, 3),
            "warm_total_ms_samples": [round(value, 3) for value in warm_samples],
            "warm_total_ms_median": round(statistics.median(warm_samples), 3),
        }

    paired_cases = []
    for memory, pgvector in zip(
        case_rankings["memory"], case_rankings["pgvector"], strict=True
    ):
        if memory["case_id"] != pgvector["case_id"]:
            raise ValueError("retrieval_backend_case_alignment_invalid")
        paired_cases.append(
            {
                "case_id": memory["case_id"],
                "memory_top10": memory["top10"],
                "pgvector_top10": pgvector["top10"],
                "top10_exact_match": memory["top10"] == pgvector["top10"],
            }
        )

    return {
        "schema_version": "retrieval-backend-comparison-v1",
        "status": "public_synthetic_development_comparison_not_release_claim",
        "dataset": {
            "path": suite_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(suite_path),
            "case_count": 16,
        },
        "runtime_identity": {
            "retriever": "product_bm25_domain_equivalence_v1_bge_rrf_k60_depth20",
            "embedding_model_manifest_sha256": _sha256(
                ROOT
                / "api"
                / "src"
                / "traceable_support"
                / "retrieval"
                / "bge-small-zh-v1.5-fastembed.json"
            ),
            "pgvector_schema_version": 1,
            "warm_repetitions": WARM_REPETITIONS,
            "provider_calls": 0,
        },
        "execution_order": ["memory", "pgvector"],
        "backends": backend_results,
        "all_top10_rankings_exact_match": all(
            case["top10_exact_match"] for case in paired_cases
        ),
        "cases": paired_cases,
        "limitations": [
            "The 16 questions are a public synthetic development set, not an unseen HOLDOUT or an online success-rate claim.",
            "Cold time includes local model initialization, passage embedding and pgvector synchronization; warm time is the median of three complete 16-query passes.",
            "Backends run in a fixed order on one machine, so operating-system cache and local Docker overhead limit cross-machine interpretation.",
            "The comparison measures source-section retrieval only; it does not call a Provider or measure generated-answer quality.",
        ],
    }


def validate_result(result: dict[str, Any], *, suite_path: Path = DEFAULT_SUITE) -> None:
    if result.get("schema_version") != "retrieval-backend-comparison-v1":
        raise ValueError("retrieval_backend_result_schema_invalid")
    if result.get("status") != "public_synthetic_development_comparison_not_release_claim":
        raise ValueError("retrieval_backend_result_status_invalid")
    dataset = result.get("dataset", {})
    if dataset != {
        "path": suite_path.relative_to(ROOT).as_posix(),
        "sha256": _sha256(suite_path),
        "case_count": 16,
    }:
        raise ValueError("retrieval_backend_result_dataset_invalid")
    identity = result.get("runtime_identity", {})
    if identity.get("provider_calls") != 0 or identity.get("warm_repetitions") != 3:
        raise ValueError("retrieval_backend_result_identity_invalid")
    backends = result.get("backends")
    if not isinstance(backends, dict) or set(backends) != {"memory", "pgvector"}:
        raise ValueError("retrieval_backend_result_backends_invalid")
    for backend in backends.values():
        if (
            backend.get("full_coverage_at_5_passed_cases") not in range(17)
            or backend.get("full_coverage_at_10_passed_cases") not in range(17)
            or not isinstance(backend.get("wrong_model_hits_at_10"), int)
            or not isinstance(backend.get("cold_total_ms"), (int, float))
            or backend["cold_total_ms"] <= 0
            or len(backend.get("warm_total_ms_samples", [])) != 3
            or any(value <= 0 for value in backend["warm_total_ms_samples"])
            or backend.get("warm_total_ms_median") <= 0
        ):
            raise ValueError("retrieval_backend_result_measurement_invalid")
        if (
            backend["full_coverage_at_5_passed_cases"] != 16
            or backend["full_coverage_at_10_passed_cases"] != 16
            or backend["wrong_model_hits_at_10"] != 0
        ):
            raise ValueError("retrieval_backend_result_quality_regressed")
    cases = result.get("cases")
    suite, _ = load_and_validate_suite(suite_path)
    if (
        not isinstance(cases, list)
        or [case.get("case_id") for case in cases]
        != [case["case_id"] for case in suite["cases"]]
        or any(
            case.get("top10_exact_match")
            != (case.get("memory_top10") == case.get("pgvector_top10"))
            for case in cases
        )
    ):
        raise ValueError("retrieval_backend_result_cases_invalid")
    if result.get("all_top10_rankings_exact_match") != all(
        case["top10_exact_match"] for case in cases
    ):
        raise ValueError("retrieval_backend_result_equivalence_invalid")
    if result["all_top10_rankings_exact_match"] is not True:
        raise ValueError("retrieval_backend_result_ranking_drifted")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.check:
        validate_result(
            json.loads(args.output.read_text(encoding="utf-8")),
            suite_path=args.suite,
        )
        print(f"retrieval_backend_comparison_ok={args.output}")
        return 0
    dsn = os.environ.get(DSN_ENV, "").strip()
    if not dsn:
        raise SystemExit(f"{DSN_ENV} is required")
    result = build_result(suite_path=args.suite, dsn=dsn)
    validate_result(result, suite_path=args.suite)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"retrieval_backend_comparison_written={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

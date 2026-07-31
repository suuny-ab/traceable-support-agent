"""Repeatable public retrieval checkup over synthetic development questions.

This evaluator calls the repository's existing model-aware BM25, local BGE and
RRF retrieval components directly. It never calls a Provider and does not run
the generation or product workflow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from traceable_support.retrieval.candidates import (
    BM25Retriever,
    DEFAULT_MODEL_MANIFEST,
    DenseBgeRetriever,
    ReciprocalRankFusionRetriever,
    RetrievalRequest,
)
from traceable_support.retrieval.hybrid import (
    _index_for,
    _unit_inventory_digest,
    build_business_units,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT / "evals" / "retrieval-checkup-v1.json"
DEFAULT_RESULT = ROOT / "web" / "app" / "lib" / "retrieval-checkup-v1.json"
EXPECTED_DOCUMENTS = {
    "AFTER-SALES-POLICY",
    "COMMON-FAQ",
    "CUSTOMER-SERVICE-SOP",
    "FAULT-CODES",
    "CZ-R1-MANUAL",
    "CZ-R2-MANUAL",
}
RETRIEVER_LABELS = {
    "bm25": "BM25",
    "bge": "BGE",
    "rrf": "BM25 + BGE + RRF",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_ref(unit: Any) -> str:
    return f"{unit.document_id}/{unit.section_id}"


def load_and_validate_suite(path: Path = DEFAULT_SUITE) -> tuple[dict[str, Any], tuple[Any, ...]]:
    suite = json.loads(path.read_text(encoding="utf-8"))
    if set(suite) != {
        "schema_version",
        "purpose",
        "status",
        "frozen_on",
        "freeze_rule",
        "cases",
    } or suite["schema_version"] != "retrieval-checkup-v1":
        raise ValueError("retrieval_checkup_suite_schema_invalid")
    if suite["status"] != "public_synthetic_development_set_not_product_release_claim":
        raise ValueError("retrieval_checkup_suite_status_invalid")

    cases = suite["cases"]
    if not isinstance(cases, list) or len(cases) != 16:
        raise ValueError("retrieval_checkup_case_count_invalid")
    case_ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    if len(case_ids) != 16 or len(set(case_ids)) != 16:
        raise ValueError("retrieval_checkup_case_ids_invalid")
    models = [case.get("product_model") for case in cases]
    if models.count("CZ-R1") != 8 or models.count("CZ-R2") != 8:
        raise ValueError("retrieval_checkup_model_split_invalid")

    units = build_business_units("native_section")
    units_by_source = {_source_ref(unit): unit for unit in units}
    required_sources: set[str] = set()
    multi_source_count = 0
    robust_expression_count = 0
    for case in cases:
        if set(case) != {
            "case_id",
            "product_model",
            "query",
            "traits",
            "required_source_sections",
        }:
            raise ValueError(f"retrieval_checkup_case_schema_invalid:{case.get('case_id')}")
        query = case["query"]
        sources = case["required_source_sections"]
        traits = case["traits"]
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"retrieval_checkup_query_invalid:{case['case_id']}")
        if not isinstance(sources, list) or not sources or len(sources) != len(set(sources)):
            raise ValueError(f"retrieval_checkup_labels_invalid:{case['case_id']}")
        if not isinstance(traits, list) or len(traits) != len(set(traits)):
            raise ValueError(f"retrieval_checkup_traits_invalid:{case['case_id']}")
        if len(sources) >= 2:
            multi_source_count += 1
            if "multi_source" not in traits:
                raise ValueError(f"retrieval_checkup_multi_source_trait_missing:{case['case_id']}")
        if "robust_expression" in traits:
            robust_expression_count += 1
        for source in sources:
            unit = units_by_source.get(source)
            if unit is None:
                raise ValueError(f"retrieval_checkup_source_missing:{case['case_id']}:{source}")
            if case["product_model"] not in unit.applicable_models:
                raise ValueError(f"retrieval_checkup_label_model_mismatch:{case['case_id']}:{source}")
            required_sources.add(source)

    if multi_source_count < 6:
        raise ValueError("retrieval_checkup_multi_source_coverage_invalid")
    if robust_expression_count < 4:
        raise ValueError("retrieval_checkup_expression_coverage_invalid")
    if {source.split("/", 1)[0] for source in required_sources} != EXPECTED_DOCUMENTS:
        raise ValueError("retrieval_checkup_document_coverage_invalid")
    if required_sources != set(units_by_source):
        raise ValueError("retrieval_checkup_section_coverage_invalid")
    return suite, units


def _rank_record(
    *,
    model: str,
    required: list[str],
    hits: list[Any],
) -> dict[str, Any]:
    ranked_sources = [_source_ref(hit.unit) for hit in hits]
    required_ranks = {
        source: (ranked_sources.index(source) + 1 if source in ranked_sources else None)
        for source in required
    }
    missing_at_5 = [source for source, rank in required_ranks.items() if rank is None or rank > 5]
    missing_at_10 = [source for source, rank in required_ranks.items() if rank is None or rank > 10]
    wrong_model = [
        _source_ref(hit.unit)
        for hit in hits[:10]
        if model not in hit.unit.applicable_models
    ]
    return {
        "full_coverage_at_5": not missing_at_5,
        "full_coverage_at_10": not missing_at_10,
        "missing_at_5": missing_at_5,
        "missing_at_10": missing_at_10,
        "required_source_ranks": required_ranks,
        "top10": ranked_sources[:10],
        "wrong_model_hits_at_10": wrong_model,
    }


def _select_public_examples(case_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    success = next(
        (
            case
            for case in case_results
            if all(
                case["retrievals"][name]["full_coverage_at_5"]
                for name in ("bm25", "bge", "rrf")
            )
        ),
        next(case for case in case_results if case["retrievals"]["rrf"]["full_coverage_at_5"]),
    )
    examples = [
        {
            "role": "success",
            "case_id": success["case_id"],
            "retriever_id": "rrf",
            "missing_at_5": [],
        }
    ]
    used = {success["case_id"]}
    failures: list[tuple[dict[str, Any], str]] = []
    for retriever_id in ("rrf", "bm25", "bge"):
        for case in case_results:
            if not case["retrievals"][retriever_id]["full_coverage_at_5"]:
                failures.append((case, retriever_id))
    selected_retrievers: set[str] = set()
    for require_new_retriever in (True, False):
        for case, retriever_id in failures:
            if case["case_id"] in used:
                continue
            if require_new_retriever and retriever_id in selected_retrievers:
                continue
            record = case["retrievals"][retriever_id]
            examples.append(
                {
                    "role": "failure",
                    "case_id": case["case_id"],
                    "retriever_id": retriever_id,
                    "missing_at_5": record["missing_at_5"],
                }
            )
            used.add(case["case_id"])
            selected_retrievers.add(retriever_id)
            if len(examples) == 3:
                break
        if len(examples) == 3:
            break
    if len(examples) != 3:
        raise ValueError("retrieval_checkup_public_examples_unavailable")
    return examples


def build_result(suite_path: Path = DEFAULT_SUITE) -> dict[str, Any]:
    suite, units = load_and_validate_suite(suite_path)
    unit_by_id = {unit.unit_id: unit for unit in units}
    engines: dict[str, tuple[dict[str, Any], BM25Retriever, DenseBgeRetriever, ReciprocalRankFusionRetriever]] = {}
    for model in ("CZ-R1", "CZ-R2"):
        scoped_units = tuple(unit for unit in units if model in unit.applicable_models)
        index = _index_for(scoped_units, f"native_section:{model}")
        lexical = BM25Retriever()
        dense = DenseBgeRetriever()
        engines[model] = (
            index,
            lexical,
            dense,
            ReciprocalRankFusionRetriever(lexical=lexical, dense=dense),
        )

    case_results: list[dict[str, Any]] = []
    for case in suite["cases"]:
        index, lexical, dense, rrf = engines[case["product_model"]]
        request = RetrievalRequest(query=case["query"], top_k=10)
        raw_hits = {
            "bm25": lexical.search(request, index),
            "bge": dense.search(request, index),
            "rrf": rrf.search(request, index),
        }
        retrievals = {
            name: _rank_record(
                model=case["product_model"],
                required=case["required_source_sections"],
                hits=[
                    SimpleNamespace(rank=hit.rank, unit=unit_by_id[hit.chunk_id])
                    for hit in hits
                ],
            )
            for name, hits in raw_hits.items()
        }
        case_results.append(
            {
                "case_id": case["case_id"],
                "product_model": case["product_model"],
                "query": case["query"],
                "traits": case["traits"],
                "required_source_sections": case["required_source_sections"],
                "retrievals": retrievals,
            }
        )

    summaries = []
    for retriever_id, label in RETRIEVER_LABELS.items():
        passed_at_5 = sum(
            case["retrievals"][retriever_id]["full_coverage_at_5"]
            for case in case_results
        )
        passed_at_10 = sum(
            case["retrievals"][retriever_id]["full_coverage_at_10"]
            for case in case_results
        )
        wrong_model_count = sum(
            len(case["retrievals"][retriever_id]["wrong_model_hits_at_10"])
            for case in case_results
        )
        summaries.append(
            {
                "retriever_id": retriever_id,
                "label": label,
                "full_coverage_at_5": {"passed_cases": passed_at_5, "total_cases": 16},
                "full_coverage_at_10": {"passed_cases": passed_at_10, "total_cases": 16},
                "wrong_model_hits_at_10": wrong_model_count,
            }
        )

    required_sources = {
        source for case in suite["cases"] for source in case["required_source_sections"]
    }
    return {
        "schema_version": "retrieval-checkup-result-v1",
        "status": "first_frozen_public_development_result_not_product_release_claim",
        "dataset": {
            "path": suite_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(suite_path),
            "case_count": 16,
            "model_split": {"CZ-R1": 8, "CZ-R2": 8},
            "document_count": len(EXPECTED_DOCUMENTS),
            "section_count": len(required_sources),
            "multi_source_case_count": sum(
                "multi_source" in case["traits"] for case in suite["cases"]
            ),
            "robust_expression_case_count": sum(
                "robust_expression" in case["traits"] for case in suite["cases"]
            ),
        },
        "runtime_identity": {
            "unit_strategy": "native_section",
            "model_filter_stage": "before_ranking",
            "top_k": 10,
            "unit_inventory_sha256": _unit_inventory_digest(units),
            "embedding_model_manifest_sha256": _sha256(DEFAULT_MODEL_MANIFEST),
            "retriever_contracts": {
                "bm25": "okapi_bm25_k1_1.5_b_0.75",
                "bge": "fastembed_bge_small_zh_v1.5",
                "rrf": "rrf_bm25_bge_k60_depth20",
            },
            "provider_calls": 0,
        },
        "retrievers": summaries,
        "public_examples": _select_public_examples(case_results),
        "cases": case_results,
        "limitations": [
            "This is a 16-case public synthetic development set, not an unseen HOLDOUT or a product success-rate claim.",
            "It measures whether all labeled source sections appear in Top 5 or Top 10; it does not measure answer correctness or generation quality.",
            "All rankings are model-filtered before retrieval, so wrong-model hits test that boundary rather than unrestricted cross-model search.",
            "No Provider, credential, private data or external business system is used.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_result(args.suite.resolve())
    rendered = _canonical_json(result)
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(
            f"retrieval_checkup=written cases=16 provider_calls=0 output={args.output}"
        )
        return 0
    if not args.output.is_file() or args.output.read_text(encoding="utf-8") != rendered:
        print("retrieval_checkup=drifted")
        return 1
    print("retrieval_checkup=passed cases=16 provider_calls=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import hashlib
import json

from tools.retrieval_holdout import (
    DEFAULT_RESULT,
    DEFAULT_SUITE,
    load_and_validate_suite,
)


def test_frozen_holdout_is_complete_and_disjoint_from_development() -> None:
    suite, units = load_and_validate_suite(DEFAULT_SUITE)
    assert len(suite["cases"]) == 10
    assert len(units) == 16
    assert sum(case["product_model"] == "CZ-R1" for case in suite["cases"]) == 5
    assert sum(case["product_model"] == "CZ-R2" for case in suite["cases"]) == 5
    assert {source for case in suite["cases"] for source in case["required_source_sections"]} == {
        f"{unit.document_id}/{unit.section_id}" for unit in units
    }


def test_first_observation_receipt_is_bound_without_rerunning_rankings() -> None:
    suite, units = load_and_validate_suite(DEFAULT_SUITE)
    result = json.loads(DEFAULT_RESULT.read_text(encoding="utf-8"))
    assert result["status"] == "first_retrieval_only_observation_revealed_regression_only"
    assert result["dataset"] == {
        "case_count": 10,
        "development_knowledge_text_duplicates": 0,
        "development_query_duplicates": 0,
        "development_source_ref_duplicates": 0,
        "freeze_commit": "6e57c5e229af01f4949df9c99d6ec6bdf03af74a",
        "model_split": {"CZ-R1": 5, "CZ-R2": 5},
        "path": "evals/retrieval-holdout-v1.json",
        "sha256": hashlib.sha256(DEFAULT_SUITE.read_bytes()).hexdigest(),
        "source_unit_count": 16,
    }
    assert result["runtime_identity"]["provider_calls"] == 0
    assert result["runtime_identity"]["generation_calls"] == 0
    assert {
        item["retriever_id"]: (
            item["full_coverage_at_5"]["passed_cases"],
            item["full_coverage_at_10"]["passed_cases"],
            item["wrong_model_hits_at_10"],
        )
        for item in result["retrievers"]
    } == {
        "bm25": (10, 10, 0),
        "bge": (10, 10, 0),
        "rrf": (10, 10, 0),
    }
    source_models = {
        f"{unit.document_id}/{unit.section_id}": set(unit.applicable_models)
        for unit in units
    }
    case_models = {case["case_id"]: case["product_model"] for case in suite["cases"]}
    for case in result["cases"]:
        for retrieval in case["retrievals"].values():
            assert retrieval["wrong_model_hits_at_10"] == []
            assert all(
                case_models[case["case_id"]] in source_models[source]
                for source in retrieval["top10"]
            )

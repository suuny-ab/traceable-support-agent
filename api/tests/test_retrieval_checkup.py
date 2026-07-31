from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.retrieval_checkup import (
    DEFAULT_RESULT,
    DEFAULT_SUITE,
    build_result,
    load_and_validate_suite,
)
from traceable_support.retrieval.candidates import (
    load_local_model_manifest,
    validate_local_model_files,
)
from traceable_support.retrieval.hybrid import (
    BusinessRetrievalRequest,
    ModelAwareRrfPipeline,
)


def _model_is_available() -> bool:
    try:
        validate_local_model_files(load_local_model_manifest())
    except (OSError, ValueError):
        return False
    return True


def test_frozen_retrieval_checkup_labels_cover_the_current_corpus() -> None:
    suite, units = load_and_validate_suite(DEFAULT_SUITE)
    assert len(suite["cases"]) == 16
    assert len(units) == 27
    assert sum(case["product_model"] == "CZ-R1" for case in suite["cases"]) == 8
    assert sum(case["product_model"] == "CZ-R2" for case in suite["cases"]) == 8
    assert sum("multi_source" in case["traits"] for case in suite["cases"]) == 11
    assert sum("robust_expression" in case["traits"] for case in suite["cases"]) == 10


@pytest.mark.skipif(not _model_is_available(), reason="pinned local BGE model unavailable")
def test_frozen_retrieval_checkup_result_is_repeatable() -> None:
    expected = json.loads(DEFAULT_RESULT.read_text(encoding="utf-8"))
    assert build_result(DEFAULT_SUITE) == expected
    assert expected["runtime_identity"]["provider_calls"] == 0
    assert {
        item["retriever_id"]: (
            item["full_coverage_at_5"]["passed_cases"],
            item["full_coverage_at_10"]["passed_cases"],
            item["wrong_model_hits_at_10"],
        )
        for item in expected["retrievers"]
    } == {
        "bm25": (14, 16, 0),
        "bge": (14, 16, 0),
        "rrf": (16, 16, 0),
    }


@pytest.mark.skipif(not _model_is_available(), reason="pinned local BGE model unavailable")
def test_checkup_rrf_matches_the_current_product_candidate_ranking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TRACEABLE_RETRIEVAL_VECTOR_DSN", raising=False)
    suite = json.loads(DEFAULT_SUITE.read_text(encoding="utf-8"))
    result = json.loads(DEFAULT_RESULT.read_text(encoding="utf-8"))
    expected = {case["case_id"]: case for case in result["cases"]}
    pipeline = ModelAwareRrfPipeline(unit_strategy="native_section", delivery_k=5)
    for case in suite["cases"]:
        product_result = pipeline.retrieve(
            BusinessRetrievalRequest(
                query_text=case["query"],
                known_product_model=case["product_model"],
                channel="qa",
                candidate_pool_limit=10,
                delivery_limit=5,
            )
        )
        assert [
            f"{hit.unit.document_id}/{hit.unit.section_id}"
            for hit in product_result.candidate_hits
        ] == expected[case["case_id"]]["retrievals"]["rrf"]["top10"]

from __future__ import annotations

import json

from tools.retrieval_backend_compare import DEFAULT_RESULT, validate_result


def test_recorded_pgvector_comparison_is_current_and_fail_closed() -> None:
    result = json.loads(DEFAULT_RESULT.read_text(encoding="utf-8"))
    validate_result(result)
    assert result["runtime_identity"]["provider_calls"] == 0
    assert result["all_top10_rankings_exact_match"] is True
    assert {
        backend: (
            metrics["full_coverage_at_5_passed_cases"],
            metrics["full_coverage_at_10_passed_cases"],
            metrics["wrong_model_hits_at_10"],
        )
        for backend, metrics in result["backends"].items()
    } == {
        "memory": (16, 16, 0),
        "pgvector": (16, 16, 0),
    }

from __future__ import annotations

from tools.retrieval_holdout import DEFAULT_SUITE, load_and_validate_suite


def test_frozen_holdout_is_complete_and_disjoint_from_development() -> None:
    suite, units = load_and_validate_suite(DEFAULT_SUITE)
    assert len(suite["cases"]) == 10
    assert len(units) == 16
    assert sum(case["product_model"] == "CZ-R1" for case in suite["cases"]) == 5
    assert sum(case["product_model"] == "CZ-R2" for case in suite["cases"]) == 5
    assert {source for case in suite["cases"] for source in case["required_source_sections"]} == {
        f"{unit.document_id}/{unit.section_id}" for unit in units
    }

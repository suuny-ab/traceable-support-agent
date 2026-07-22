from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from traceable_support.generation.checklist import (
    CHECKLIST_SYSTEM_PROMPT_V2,
    STEP2_SYSTEM_PROMPT,
)
from traceable_support.generation.ticket_contract import TICKET_SYSTEM_PROMPT
from traceable_support.provider.contract import build_manifest
from traceable_support.retrieval.hybrid import (
    BusinessRetrievalRequest,
    ModelAwareRrfPipeline,
    _unit_inventory_digest,
    build_business_units,
)

REPOSITORY = Path(__file__).resolve().parents[2]
PUBLIC_SUITE = REPOSITORY / "evals" / "public-regression-v1.json"
RETRIEVAL_FIXTURE = (
    REPOSITORY / "evals" / "fixtures" / "migration-retrieval-equivalence-v1.json"
)
CASE_IDS = {
    "GEN-DEV-QA-003",
    "GEN-DEV-QA-006",
    "GEN-DEV-TK-001",
    "GEN-DEV-TK-006",
    "GEN-DEV-IE-001",
    "GEN-DEV-MH-001",
    "GEN-DEV-MH-003",
    "BRD-QA-005",
}


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def test_prompt_and_provider_identities_match_frozen_baseline() -> None:
    assert _sha(CHECKLIST_SYSTEM_PROMPT_V2) == (
        "c7adeb30109c4b95b66dca02bf75224aef091b9cf2401ef64baa4c13e38943f9"
    )
    assert _sha(STEP2_SYSTEM_PROMPT) == (
        "dbb60b1970fed602b28560979205778200fa8f1bc2456263469739527a85ada2"
    )
    assert _sha(TICKET_SYSTEM_PROMPT) == (
        "1c1ec10b1cb8ff2e9b1b6f0c52ee909b08eb6f969bd2ed28db48e193d149dc59"
    )
    assert build_manifest()["manifest_sha256"] == (
        "c45786f67ac6e5957a622c5a42cc7e3ca8b2412cf6279cf3c55b3396dc4773bf"
    )


def test_native_section_inventory_matches_frozen_baseline() -> None:
    units = build_business_units("native_section")
    assert len(units) == 27
    assert _unit_inventory_digest(units) == (
        "714538ce5b649f3acf566ac53f93dc9201f6a80d13430c7e3e293436d7e55161"
    )
    assert all(
        span.relative_path.startswith("data/knowledge/synthetic-kb-v1/")
        for unit in units
        for span in unit.source_spans
    )


def test_public_suite_is_exactly_the_approved_redacted_set() -> None:
    suite = json.loads(PUBLIC_SUITE.read_text(encoding="utf-8"))
    assert suite["schema_version"] == "public-regression-v1"
    assert {case["case_id"] for case in suite["cases"]} == CASE_IDS
    encoded = PUBLIC_SUITE.read_text(encoding="utf-8").casefold()
    for forbidden in (
        "reasoning_content",
        "raw_response",
        "provider_response",
        "authorization_envelope",
        "request_headers",
    ):
        assert forbidden not in encoded


def test_retrieval_fixture_has_ordered_top10_and_top5_for_each_case() -> None:
    fixture = json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))
    assert fixture["schema_version"] == "migration-retrieval-equivalence-v1"
    assert {record["case_id"] for record in fixture["records"]} == CASE_IDS
    for record in fixture["records"]:
        assert [item["rank"] for item in record["top10"]] == list(range(1, 11))
        assert len({item["unit_id"] for item in record["top10"]}) == 10
        assert record["top5"] == [item["unit_id"] for item in record["top10"][:5]]


@pytest.mark.skipif(
    not os.environ.get("TRACEABLE_MODEL_ROOT"),
    reason="live retrieval model is validated in the dedicated CI job",
)
def test_live_retrieval_matches_frozen_old_repository_ordering() -> None:
    suite = json.loads(PUBLIC_SUITE.read_text(encoding="utf-8"))
    expected = {
        record["case_id"]: record
        for record in json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))[
            "records"
        ]
    }
    for case in suite["cases"]:
        result = ModelAwareRrfPipeline(
            unit_strategy="native_section", delivery_k=5
        ).retrieve(
            BusinessRetrievalRequest(
                query_text=case["input"],
                known_product_model=case["product_model"],
                channel=case["task_type"],
                candidate_pool_limit=10,
                delivery_limit=5,
            )
        )
        assert [hit.unit.unit_id for hit in result.candidate_hits] == [
            item["unit_id"] for item in expected[case["case_id"]]["top10"]
        ]
        assert [hit.unit.unit_id for hit in result.delivery_hits] == expected[
            case["case_id"]
        ]["top5"]

"""Verify the live image's model using eight public cases and no Provider."""

from __future__ import annotations

import json
from pathlib import Path

from traceable_support.retrieval.hybrid import BusinessRetrievalRequest, ModelAwareRrfPipeline


def main() -> int:
    root = Path("/verification/evals")
    suite = json.loads((root / "public-regression-v1.json").read_text(encoding="utf-8"))
    fixture = json.loads(
        (root / "fixtures/migration-retrieval-equivalence-v1.json").read_text(encoding="utf-8")
    )
    expected = {record["case_id"]: record for record in fixture["records"]}
    for case in suite["cases"]:
        result = ModelAwareRrfPipeline(unit_strategy="native_section", delivery_k=5).retrieve(
            BusinessRetrievalRequest(
                query_text=case["input"],
                known_product_model=case["product_model"],
                channel=case["task_type"],
                candidate_pool_limit=10,
                delivery_limit=5,
            )
        )
        record = expected[case["case_id"]]
        assert [hit.unit.unit_id for hit in result.candidate_hits] == [
            item["unit_id"] for item in record["top10"]
        ]
        assert [hit.unit.unit_id for hit in result.delivery_hits] == record["top5"]
    print("live_retrieval=passed cases=8 provider_calls=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Seal and observe the public synthetic retrieval HOLDOUT exactly once.

The suite carries evaluation-only knowledge units. They are never added to the
product corpus. This tool runs only BM25, local BGE and RRF; it has no Provider
or generation path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from tools.retrieval_checkup import _rank_record
from traceable_support.retrieval.candidates import (
    DEFAULT_MODEL_MANIFEST,
    DenseBgeRetriever,
    ReciprocalRankFusionRetriever,
    RetrievalRequest,
    build_product_bm25_retriever,
)
from traceable_support.retrieval.hybrid import (
    BusinessUnit,
    SourceSpan,
    _index_for,
    _unit_inventory_digest,
    build_business_units,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT / "evals" / "retrieval-holdout-v1.json"
DEFAULT_DEVELOPMENT_SUITE = ROOT / "evals" / "retrieval-checkup-v1.json"
DEFAULT_RESULT = ROOT / "evals" / "retrieval-holdout-observation-v1.json"
MODELS = ("CZ-R1", "CZ-R2")
HEX_SHA = re.compile(r"[0-9a-f]{40}")
CASE_KEYS = {
    "case_id",
    "product_model",
    "query",
    "traits",
    "required_source_sections",
}
SOURCE_KEYS = {
    "source_ref",
    "document_id",
    "section_id",
    "section_heading",
    "applicable_models",
    "text",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).lower().split())


def _source_ref(unit: BusinessUnit) -> str:
    return f"{unit.document_id}/{unit.section_id}"


def _holdout_units(source_units: list[dict[str, Any]]) -> tuple[BusinessUnit, ...]:
    units = []
    for item in source_units:
        relative_path = DEFAULT_SUITE.relative_to(ROOT).as_posix()
        units.append(
            BusinessUnit(
                unit_id="holdout_" + _sha256_bytes(item["source_ref"].encode("utf-8")),
                text=item["text"],
                document_id=item["document_id"],
                section_id=item["section_id"],
                section_heading=item["section_heading"],
                applicable_models=tuple(item["applicable_models"]),
                source_spans=(
                    SourceSpan(
                        document_id=item["document_id"],
                        relative_path=relative_path,
                        section_id=item["section_id"],
                        exact_text=item["text"],
                    ),
                ),
            )
        )
    return tuple(sorted(units, key=lambda unit: unit.unit_id))


def load_and_validate_suite(
    path: Path = DEFAULT_SUITE,
    development_path: Path = DEFAULT_DEVELOPMENT_SUITE,
) -> tuple[dict[str, Any], tuple[BusinessUnit, ...]]:
    suite = json.loads(path.read_text(encoding="utf-8"))
    if set(suite) != {
        "schema_version",
        "purpose",
        "status",
        "frozen_on",
        "freeze_rule",
        "source_units",
        "cases",
    } or suite["schema_version"] != "retrieval-holdout-v1":
        raise ValueError("retrieval_holdout_suite_schema_invalid")
    if suite["status"] != "frozen_public_synthetic_unseen_retrieval_set":
        raise ValueError("retrieval_holdout_suite_status_invalid")
    if "do not tune retrieval" not in suite["freeze_rule"].lower():
        raise ValueError("retrieval_holdout_freeze_rule_invalid")

    cases = suite["cases"]
    sources = suite["source_units"]
    if not isinstance(cases, list) or len(cases) != 10:
        raise ValueError("retrieval_holdout_case_count_invalid")
    if not isinstance(sources, list) or len(sources) < 10:
        raise ValueError("retrieval_holdout_source_count_invalid")
    if any(not isinstance(case, dict) or set(case) != CASE_KEYS for case in cases):
        raise ValueError("retrieval_holdout_case_schema_invalid")
    if any(not isinstance(source, dict) or set(source) != SOURCE_KEYS for source in sources):
        raise ValueError("retrieval_holdout_source_schema_invalid")

    case_ids = [case["case_id"] for case in cases]
    queries = [case["query"] for case in cases]
    refs = [source["source_ref"] for source in sources]
    if len(case_ids) != len(set(case_ids)) or not all(
        isinstance(case_id, str) and case_id.startswith("RET-HOLDOUT-")
        for case_id in case_ids
    ):
        raise ValueError("retrieval_holdout_case_ids_invalid")
    if len({_normalized(query) for query in queries}) != 10:
        raise ValueError("retrieval_holdout_queries_invalid")
    if len(refs) != len(set(refs)):
        raise ValueError("retrieval_holdout_source_refs_invalid")
    source_by_ref = {source["source_ref"]: source for source in sources}

    for source in sources:
        if source["source_ref"] != f'{source["document_id"]}/{source["section_id"]}':
            raise ValueError(f'retrieval_holdout_source_ref_invalid:{source["source_ref"]}')
        if source["applicable_models"] not in [["CZ-R1"], ["CZ-R2"]]:
            raise ValueError(f'retrieval_holdout_source_model_invalid:{source["source_ref"]}')
        if not all(
            isinstance(source[field], str) and source[field].strip()
            for field in ("document_id", "section_id", "section_heading", "text")
        ):
            raise ValueError(f'retrieval_holdout_source_text_invalid:{source["source_ref"]}')

    required: set[str] = set()
    for case in cases:
        labels = case["required_source_sections"]
        traits = case["traits"]
        if case["product_model"] not in MODELS or not isinstance(case["query"], str) or not case["query"].strip():
            raise ValueError(f'retrieval_holdout_case_invalid:{case["case_id"]}')
        if not isinstance(labels, list) or not labels or len(labels) != len(set(labels)):
            raise ValueError(f'retrieval_holdout_labels_invalid:{case["case_id"]}')
        if not isinstance(traits, list) or len(traits) != len(set(traits)):
            raise ValueError(f'retrieval_holdout_traits_invalid:{case["case_id"]}')
        if len(labels) >= 2 and "multi_source" not in traits:
            raise ValueError(f'retrieval_holdout_multi_source_trait_missing:{case["case_id"]}')
        if len(labels) == 1 and "single_source" not in traits:
            raise ValueError(f'retrieval_holdout_single_source_trait_missing:{case["case_id"]}')
        for label in labels:
            source = source_by_ref.get(label)
            if source is None:
                raise ValueError(f'retrieval_holdout_source_missing:{case["case_id"]}:{label}')
            if source["applicable_models"] != [case["product_model"]]:
                raise ValueError(f'retrieval_holdout_label_model_mismatch:{case["case_id"]}:{label}')
            required.add(label)
    if required != set(refs):
        raise ValueError("retrieval_holdout_source_coverage_invalid")
    if [case["product_model"] for case in cases].count("CZ-R1") != 5:
        raise ValueError("retrieval_holdout_model_split_invalid")
    if [case["product_model"] for case in cases].count("CZ-R2") != 5:
        raise ValueError("retrieval_holdout_model_split_invalid")

    development = json.loads(development_path.read_text(encoding="utf-8"))
    development_queries = {_normalized(case["query"]) for case in development["cases"]}
    development_units = build_business_units("native_section")
    development_refs = {_source_ref(unit) for unit in development_units}
    development_text = {_normalized(unit.text) for unit in development_units}
    if development_queries & {_normalized(query) for query in queries}:
        raise ValueError("retrieval_holdout_development_query_duplicate")
    if development_refs & set(refs):
        raise ValueError("retrieval_holdout_development_source_ref_duplicate")
    if development_text & {_normalized(source["text"]) for source in sources}:
        raise ValueError("retrieval_holdout_development_knowledge_duplicate")
    return suite, _holdout_units(sources)


def _verify_freeze_commit(commit: str, suite_path: Path) -> None:
    if HEX_SHA.fullmatch(commit) is None:
        raise ValueError("retrieval_holdout_freeze_commit_invalid")
    relative = suite_path.resolve().relative_to(ROOT).as_posix()
    completed = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0 or completed.stdout != suite_path.read_bytes():
        raise ValueError("retrieval_holdout_freeze_commit_mismatch")


def build_first_observation(suite_path: Path, freeze_commit: str) -> dict[str, Any]:
    suite, units = load_and_validate_suite(suite_path)
    _verify_freeze_commit(freeze_commit, suite_path)
    unit_by_id = {unit.unit_id: unit for unit in units}
    engines = {}
    for model in MODELS:
        scoped = tuple(unit for unit in units if model in unit.applicable_models)
        index = _index_for(scoped, f"holdout_v1:{model}")
        lexical = build_product_bm25_retriever()
        dense = DenseBgeRetriever()
        engines[model] = (
            index,
            lexical,
            dense,
            ReciprocalRankFusionRetriever(lexical=lexical, dense=dense),
        )

    case_results = []
    for case in suite["cases"]:
        index, lexical, dense, rrf = engines[case["product_model"]]
        request = RetrievalRequest(query=case["query"], top_k=10)
        retrievals = {}
        for name, hits in {
            "bm25": lexical.search(request, index),
            "bge": dense.search(request, index),
            "rrf": rrf.search(request, index),
        }.items():
            retrievals[name] = _rank_record(
                model=case["product_model"],
                required=case["required_source_sections"],
                hits=[
                    SimpleNamespace(rank=hit.rank, unit=unit_by_id[hit.chunk_id])
                    for hit in hits
                ],
            )
        case_results.append(
            {
                "case_id": case["case_id"],
                "product_model": case["product_model"],
                "required_source_sections": case["required_source_sections"],
                "retrievals": retrievals,
            }
        )

    summaries = []
    for retriever_id, label in (
        ("bm25", "BM25"),
        ("bge", "BGE"),
        ("rrf", "BM25 + BGE + RRF"),
    ):
        summaries.append(
            {
                "retriever_id": retriever_id,
                "label": label,
                "full_coverage_at_5": {
                    "passed_cases": sum(case["retrievals"][retriever_id]["full_coverage_at_5"] for case in case_results),
                    "total_cases": 10,
                },
                "full_coverage_at_10": {
                    "passed_cases": sum(case["retrievals"][retriever_id]["full_coverage_at_10"] for case in case_results),
                    "total_cases": 10,
                },
                "wrong_model_hits_at_10": sum(
                    len(case["retrievals"][retriever_id]["wrong_model_hits_at_10"])
                    for case in case_results
                ),
            }
        )

    return {
        "schema_version": "retrieval-holdout-observation-v1",
        "status": "first_retrieval_only_observation_revealed_regression_only",
        "dataset": {
            "path": suite_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(suite_path),
            "freeze_commit": freeze_commit,
            "case_count": 10,
            "model_split": {"CZ-R1": 5, "CZ-R2": 5},
            "source_unit_count": len(units),
            "development_query_duplicates": 0,
            "development_source_ref_duplicates": 0,
            "development_knowledge_text_duplicates": 0,
        },
        "runtime_identity": {
            "knowledge_scope": "evaluation_only_holdout_units_not_product_corpus",
            "model_filter_stage": "before_ranking",
            "top_k": 10,
            "unit_inventory_sha256": _unit_inventory_digest(units),
            "embedding_model_manifest_sha256": _sha256(DEFAULT_MODEL_MANIFEST),
            "retriever_contracts": {
                "bm25": "okapi_bm25_k1_1.5_b_0.75_domain_equivalence_v1",
                "bge": "fastembed_bge_small_zh_v1.5",
                "rrf": "rrf_bm25_domain_equivalence_v1_bge_k60_depth20",
            },
            "provider_calls": 0,
            "generation_calls": 0,
        },
        "retrievers": summaries,
        "cases": case_results,
        "limitations": [
            "This is one retrieval-only observation over 10 public synthetic questions and evaluation-only knowledge, not answer correctness, generation quality, online success rate or a release claim.",
            "The suite was frozen before ranking. After this reveal it is regression-only and must not be used to tune retrieval or edit labels and knowledge against the result.",
            "Model filtering occurs before ranking, so wrong-model hits test that boundary within the evaluation inventory.",
            "No Provider, credential, private data, generation or external business system was used.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--freeze-commit")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate-only", action="store_true")
    mode.add_argument("--write-first-observation", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    suite_path = args.suite.resolve()
    suite, units = load_and_validate_suite(suite_path)
    if args.validate_only:
        print(
            "retrieval_holdout=valid "
            f"cases={len(suite['cases'])} sources={len(units)} "
            "development_query_duplicates=0 development_source_ref_duplicates=0 "
            "development_knowledge_text_duplicates=0 provider_calls=0 generation_calls=0"
        )
        return 0
    if args.output.exists():
        print(f"retrieval_holdout=refused reason=first_observation_already_exists output={args.output}")
        return 1
    if not args.freeze_commit:
        print("retrieval_holdout=refused reason=freeze_commit_required")
        return 1
    result = build_first_observation(suite_path, args.freeze_commit)
    args.output.write_text(_canonical_json(result), encoding="utf-8")
    print(
        "retrieval_holdout=first_observation_written cases=10 "
        f"provider_calls=0 generation_calls=0 output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

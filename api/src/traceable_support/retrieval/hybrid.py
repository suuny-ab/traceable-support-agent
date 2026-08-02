"""Model-aware BM25 + local BGE retrieval used by the product runtime."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .corpus import parse_document, tokenize
from .source_scope import resolve_applicable_models
from .candidates import (
    BM25Retriever,
    DenseBgeRetriever,
    RetrievalRequest,
    build_dense_retriever,
    build_product_bm25_retriever,
)


ROOT = Path(__file__).resolve().parents[4]
CORPUS_ROOT = ROOT / "data" / "knowledge" / "synthetic-kb-v1"
UnitStrategy = Literal["native_section"]
DeliveryPolicy = Literal[
    "fixed_k",
    "top2_plus_lexical_top2",
    "top2_plus_heading_match",
    "top2_plus_clause_rrf",
]

CLAUSE_SPLIT_RE = re.compile(r"[\u3002\uff01\uff1f!?\uff1b;,\uff0c\n]+")
CLAUSE_MIN_CHARS = 10
CLAUSE_COMPONENT_MAX_RANK = 2


@dataclass(frozen=True)
class BusinessRetrievalRequest:
    query_text: str
    known_product_model: str | None
    channel: Literal["qa", "ticket"]
    candidate_pool_limit: int = 10
    delivery_limit: int = 5

    def __post_init__(self) -> None:
        if not isinstance(self.query_text, str) or not self.query_text.strip():
            raise ValueError("business_candidate_query_invalid")
        if self.known_product_model not in {None, "CZ-R1", "CZ-R2"}:
            raise ValueError("business_candidate_model_invalid")
        if self.channel not in {"qa", "ticket"}:
            raise ValueError("business_candidate_channel_invalid")
        for value, maximum in (
            (self.candidate_pool_limit, 10),
            (self.delivery_limit, 5),
        ):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError("business_candidate_limit_invalid")
        if self.delivery_limit > self.candidate_pool_limit:
            raise ValueError("business_candidate_limit_invalid")


@dataclass(frozen=True)
class SourceSpan:
    document_id: str
    relative_path: str
    section_id: str
    exact_text: str


@dataclass(frozen=True)
class BusinessUnit:
    unit_id: str
    text: str
    document_id: str
    section_id: str
    section_heading: str
    applicable_models: tuple[str, ...]
    source_spans: tuple[SourceSpan, ...]


@dataclass(frozen=True)
class BusinessRankedHit:
    rank: int
    score: float
    lexical_rank: int
    dense_rank: int
    unit: BusinessUnit


@dataclass(frozen=True)
class BusinessRetrievalResult:
    candidate_hits: tuple[BusinessRankedHit, ...]
    delivery_hits: tuple[BusinessRankedHit, ...]


def _digest(parts: list[str]) -> str:
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _unit_inventory_digest(units: tuple[BusinessUnit, ...]) -> str:
    inventory = [
        {
            "unit_id": unit.unit_id,
            "text": unit.text,
            "document_id": unit.document_id,
            "section_id": unit.section_id,
            "section_heading": unit.section_heading,
            "applicable_models": list(unit.applicable_models),
            "source_spans": [
                {
                    "document_id": span.document_id,
                    "relative_path": span.relative_path,
                    "section_id": span.section_id,
                    "exact_text": span.exact_text,
                }
                for span in unit.source_spans
            ],
        }
        for unit in units
    ]
    encoded = json.dumps(
        inventory, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _native_section_units() -> tuple[BusinessUnit, ...]:
    units: list[BusinessUnit] = []
    for path in sorted(CORPUS_ROOT.iterdir(), key=lambda item: item.name):
        if not path.is_file():
            continue
        parsed = parse_document(path)
        grouped: dict[str, list[dict[str, Any]]] = {}
        for chunk in parsed["chunks"]:
            if chunk["section_id"] == "notice":
                continue
            grouped.setdefault(chunk["section_id"], []).append(chunk)
        metadata = parsed["metadata"]
        for section_id, chunks in grouped.items():
            relative_path = parsed["source_file"]
            text = " ".join(chunk["text"] for chunk in chunks)
            unit_id = "section_" + _digest(
                [metadata["document_id"], section_id, relative_path, text]
            )
            units.append(
                BusinessUnit(
                    unit_id=unit_id,
                    text=text,
                    document_id=metadata["document_id"],
                    section_id=section_id,
                    section_heading=chunks[0]["section"],
                    applicable_models=resolve_applicable_models(
                        text, metadata["applicable_models"]
                    ),
                    source_spans=tuple(
                        SourceSpan(
                            document_id=metadata["document_id"],
                            relative_path=relative_path,
                            section_id=section_id,
                            exact_text=chunk["text"],
                        )
                        for chunk in chunks
                    ),
                )
            )
    return tuple(sorted(units, key=lambda unit: unit.unit_id))


def build_business_units(strategy: UnitStrategy) -> tuple[BusinessUnit, ...]:
    if strategy == "native_section":
        return _native_section_units()
    raise ValueError("business_candidate_unit_strategy_invalid")


def _index_for(units: tuple[BusinessUnit, ...], scope: str) -> dict[str, Any]:
    chunks = [
        {
            "chunk_id": unit.unit_id,
            "text": unit.text,
            "document_id": unit.document_id,
            "section_id": unit.section_id,
            "section_heading": unit.section_heading,
            "applicable_models": list(unit.applicable_models),
        }
        for unit in units
    ]
    return {
        "chunks": chunks,
        "chunks_by_id": {chunk["chunk_id"]: chunk for chunk in chunks},
        "manifest": {
            "build_fingerprint": _digest(
                [scope, *[f"{unit.unit_id}:{unit.text}" for unit in units]]
            )
        },
    }


class ModelAwareRrfPipeline:
    """RRF candidate with pre-ranking model scope and fixed delivery K."""

    def __init__(
        self,
        *,
        unit_strategy: UnitStrategy,
        delivery_k: int = 5,
        delivery_policy: DeliveryPolicy = "fixed_k",
    ) -> None:
        if type(delivery_k) is not int or not 1 <= delivery_k <= 5:
            raise ValueError("business_candidate_delivery_k_invalid")
        self.unit_strategy = unit_strategy
        self.delivery_k = delivery_k
        if delivery_policy not in {
            "fixed_k",
            "top2_plus_lexical_top2",
            "top2_plus_heading_match",
            "top2_plus_clause_rrf",
        }:
            raise ValueError("business_candidate_delivery_policy_invalid")
        self.delivery_policy = delivery_policy
        self.units = build_business_units(unit_strategy)
        self.unit_by_id = {unit.unit_id: unit for unit in self.units}
        self._indexes: dict[str, dict[str, Any]] = {}
        self._retrievers: dict[str, tuple[BM25Retriever, DenseBgeRetriever]] = {}
        delivery_name = (
            f"delivery_{delivery_k}"
            if delivery_policy == "fixed_k"
            else f"{delivery_policy}_max_{delivery_k}"
        )
        self.candidate_id = (
            f"{unit_strategy}_model_aware_rrf_bm25_equivalence_v1_{delivery_name}"
        )

    @property
    def manifest(self) -> dict[str, Any]:
        manifest = {
            "candidate_id": self.candidate_id,
            "unit_strategy": self.unit_strategy,
            "delivery_k": self.delivery_k,
            "delivery_policy": self.delivery_policy,
            "model_filter_stage": "before_ranking",
            "lexical": (
                "rank-bm25==0.2.2:BM25Okapi(k1=1.5,b=0.75)"
                "+domain_equivalence_v1"
            ),
            "dense": "fastembed==0.8.0:BAAI/bge-small-zh-v1.5",
            "fusion": "rrf(k=60,candidate_depth=20)",
            "unit_inventory_sha256": _unit_inventory_digest(self.units),
            "used_input_fields": ["query_text", "known_product_model"],
            "runtime_control_fields": [
                "candidate_pool_limit",
                "delivery_limit",
            ],
            "request_contract": {
                "known_product_models": [None, "CZ-R1", "CZ-R2"],
                "channels_validated_not_ranked": ["qa", "ticket"],
                "candidate_pool_limit": {"default": 10, "minimum": 1, "maximum": 10},
                "delivery_limit": {"default": 5, "minimum": 1, "maximum": 5},
                "delivery_limit_must_not_exceed_candidate_pool_limit": True,
            },
        }
        if self.delivery_policy == "top2_plus_clause_rrf":
            manifest["clause_selection"] = {
                "split_characters": ["。", "！", "？", "!", "?", "；", ";", ",", "，", "\\n"],
                "minimum_stripped_characters": CLAUSE_MIN_CHARS,
                "component_max_rank": CLAUSE_COMPONENT_MAX_RANK,
                "always_include_full_query_ranks": 2,
                "maximum_delivery_hits": self.delivery_k,
            }
        return manifest

    def _scope(self, model: str | None) -> str:
        return model or "all-models"

    def _scoped_units(self, model: str | None) -> tuple[BusinessUnit, ...]:
        if model is None:
            return self.units
        return tuple(unit for unit in self.units if model in unit.applicable_models)

    def _clause_selected_ids(
        self,
        *,
        query_text: str,
        candidate_hits: tuple[BusinessRankedHit, ...],
        index: dict[str, Any],
        lexical: BM25Retriever,
        dense: DenseBgeRetriever,
        component_depth: int,
    ) -> set[str]:
        """Select strong per-clause winners without evaluation labels.

        Full-query ranks one and two are the precision anchor.  A later candidate
        is added only when it wins an independently expressed clause and both
        lexical and dense retrieval rank it in their top two for that clause.
        """

        candidate_ids = {hit.unit.unit_id for hit in candidate_hits}
        selected = {hit.unit.unit_id for hit in candidate_hits[:2]}
        clauses = [
            clause.strip()
            for clause in CLAUSE_SPLIT_RE.split(query_text)
            if len(clause.strip()) >= CLAUSE_MIN_CHARS and tokenize(clause)
        ]
        for clause in clauses:
            clause_request = RetrievalRequest(query=clause, top_k=component_depth)
            lexical_hits = lexical.search(clause_request, index)
            dense_hits = dense.search(clause_request, index)
            lexical_ranks = {hit.chunk_id: hit.rank for hit in lexical_hits}
            dense_ranks = {hit.chunk_id: hit.rank for hit in dense_hits}
            eligible = {
                unit_id
                for unit_id in candidate_ids
                if lexical_ranks.get(unit_id, component_depth + 1)
                <= CLAUSE_COMPONENT_MAX_RANK
                and dense_ranks.get(unit_id, component_depth + 1)
                <= CLAUSE_COMPONENT_MAX_RANK
            }
            scores = {
                unit_id: 1.0 / (60 + lexical_ranks[unit_id])
                + 1.0 / (60 + dense_ranks[unit_id])
                for unit_id in eligible
            }
            if not scores:
                continue
            winner = min(scores, key=lambda unit_id: (-scores[unit_id], unit_id))
            selected.add(winner)
        return selected

    def retrieve(self, request: BusinessRetrievalRequest) -> BusinessRetrievalResult:
        if not tokenize(request.query_text):
            return BusinessRetrievalResult(candidate_hits=(), delivery_hits=())
        scope = self._scope(request.known_product_model)
        scoped_units = self._scoped_units(request.known_product_model)
        if not scoped_units:
            return BusinessRetrievalResult(candidate_hits=(), delivery_hits=())
        if scope not in self._indexes:
            self._indexes[scope] = _index_for(scoped_units, f"{self.unit_strategy}:{scope}")
            self._retrievers[scope] = (
                build_product_bm25_retriever(),
                build_dense_retriever(),
            )
        index = self._indexes[scope]
        lexical, dense = self._retrievers[scope]
        component_depth = min(max(request.candidate_pool_limit, 20), len(scoped_units))
        component_request = RetrievalRequest(
            query=request.query_text,
            top_k=component_depth,
        )
        lexical_hits = lexical.search(component_request, index)
        dense_hits = dense.search(component_request, index)
        lexical_ranks = {hit.chunk_id: hit.rank for hit in lexical_hits}
        dense_ranks = {hit.chunk_id: hit.rank for hit in dense_hits}
        scores: dict[str, float] = {}
        for ranking in (lexical_hits, dense_hits):
            for hit in ranking:
                scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (
                    60 + hit.rank
                )
        ordered = sorted(scores, key=lambda unit_id: (-scores[unit_id], unit_id))[
            : request.candidate_pool_limit
        ]
        candidate_hits = tuple(
            BusinessRankedHit(
                rank=rank,
                score=round(scores[unit_id], 8),
                lexical_rank=lexical_ranks.get(unit_id, component_depth + 1),
                dense_rank=dense_ranks.get(unit_id, component_depth + 1),
                unit=self.unit_by_id[unit_id],
            )
            for rank, unit_id in enumerate(ordered, start=1)
        )
        if self.delivery_policy == "fixed_k":
            selected = candidate_hits[: self.delivery_k]
        elif self.delivery_policy == "top2_plus_lexical_top2":
            selected = tuple(
                hit
                for hit in candidate_hits
                if hit.rank <= 2 or hit.lexical_rank <= 2
            )[: self.delivery_k]
        elif self.delivery_policy == "top2_plus_heading_match":
            query_terms = {
                term
                for term in tokenize(request.query_text)
                if len(term) >= 2 and term not in {"cz-r1", "cz-r2"}
            }
            selected = tuple(
                hit
                for hit in candidate_hits
                if hit.rank <= 2
                or query_terms
                & {
                    term
                    for term in tokenize(hit.unit.section_heading)
                    if len(term) >= 2 and term not in {"cz-r1", "cz-r2"}
                }
            )[: self.delivery_k]
        else:
            selected_ids = self._clause_selected_ids(
                query_text=request.query_text,
                candidate_hits=candidate_hits,
                index=index,
                lexical=lexical,
                dense=dense,
                component_depth=component_depth,
            )
            selected = tuple(
                hit for hit in candidate_hits if hit.unit.unit_id in selected_ids
            )[: self.delivery_k]
        delivery_count = min(len(selected), request.delivery_limit)
        delivery_hits = tuple(
            BusinessRankedHit(
                rank=rank,
                score=hit.score,
                lexical_rank=hit.lexical_rank,
                dense_rank=hit.dense_rank,
                unit=hit.unit,
            )
            for rank, hit in enumerate(selected[:delivery_count], start=1)
        )
        return BusinessRetrievalResult(
            candidate_hits=candidate_hits,
            delivery_hits=delivery_hits,
        )

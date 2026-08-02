"""Candidate-neutral BM25 and local BGE retrievers."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from rank_bm25 import BM25Okapi

from .corpus import tokenize
from .vector_store import (
    VectorStore,
    VectorStoreUnavailable,
    pgvector_store_from_env,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MODEL_MANIFEST = Path(__file__).with_name(
    "bge-small-zh-v1.5-fastembed.json"
)
PRODUCT_BM25_EQUIVALENCE_MARKERS = {
    "domain:liquid-ingress": ("吸进水", "吸入液体", "吸取液体", "进水", "进液"),
}


@dataclass(frozen=True)
class RetrievalRequest:
    query: str
    top_k: int = 10

    def __post_init__(self) -> None:
        if not isinstance(self.query, str) or not self.query.strip():
            raise ValueError("retrieval_query_invalid")
        if not isinstance(self.top_k, int) or isinstance(self.top_k, bool) or self.top_k < 1:
            raise ValueError("retrieval_top_k_invalid")


@dataclass(frozen=True)
class RetrievalHit:
    chunk_id: str
    rank: int
    score: float


class CandidateRetriever(Protocol):
    retriever_id: str

    def search(self, request: RetrievalRequest, index: dict[str, Any]) -> list[RetrievalHit]: ...


def _validate_hits(hits: list[RetrievalHit], request: RetrievalRequest) -> list[RetrievalHit]:
    if len(hits) > request.top_k:
        raise ValueError("retrieval_hit_limit_exceeded")
    if [hit.rank for hit in hits] != list(range(1, len(hits) + 1)):
        raise ValueError("retrieval_hit_rank_invalid")
    chunk_ids = [hit.chunk_id for hit in hits]
    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValueError("retrieval_hit_duplicate_chunk")
    return hits


def load_local_model_manifest(path: Path = DEFAULT_MODEL_MANIFEST) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if set(manifest) != {
        "schema_version",
        "model_name",
        "retriever_id",
        "library",
        "dimension",
        "provider",
        "model_root",
        "source",
        "license",
        "files",
    }:
        raise ValueError("embedding_model_manifest_invalid")
    if (
        manifest["schema_version"] != "local-embedding-model-v1"
        or manifest["model_name"] != "BAAI/bge-small-zh-v1.5"
        or manifest["retriever_id"] != "fastembed_bge_small_zh_v1.5"
        or manifest["library"] != "fastembed==0.8.0"
        or manifest["dimension"] != 512
        or manifest["provider"] != "CPUExecutionProvider"
        or manifest["license"] != "MIT"
    ):
        raise ValueError("embedding_model_contract_invalid")
    return manifest


def validate_local_model_files(
    manifest: dict[str, Any], model_root: Path | None = None
) -> Path:
    configured_root = os.environ.get("TRACEABLE_MODEL_ROOT")
    root = (
        model_root
        or (Path(configured_root) if configured_root else None)
        or REPOSITORY_ROOT / manifest["model_root"]
    )
    expected_paths = {item["path"] for item in manifest["files"]}
    actual_paths = {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    } if root.is_dir() else set()
    if actual_paths != expected_paths:
        raise ValueError("embedding_model_file_inventory_invalid")
    for item in manifest["files"]:
        path = root / item["path"]
        if path.stat().st_size != item["size"]:
            raise ValueError("embedding_model_file_size_invalid")
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("embedding_model_file_hash_invalid")
    return root


def _normalize(vector: np.ndarray) -> np.ndarray:
    value = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(value))
    if norm <= 0:
        raise ValueError("embedding_vector_zero_norm")
    return value / norm


class BM25Retriever:
    """rank-bm25's BM25Okapi over the frozen chunk text inventory."""

    retriever_id = "okapi_bm25_k1_1.5_b_0.75"

    def __init__(
        self,
        *,
        k1: float = 1.5,
        b: float = 0.75,
        equivalence_markers: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        if k1 <= 0 or not 0 <= b <= 1:
            raise ValueError("bm25_parameter_invalid")
        self.k1 = float(k1)
        self.b = float(b)
        self.equivalence_markers = equivalence_markers or {}
        if any(
            not marker
            or not phrases
            or any(not phrase for phrase in phrases)
            for marker, phrases in self.equivalence_markers.items()
        ):
            raise ValueError("bm25_equivalence_markers_invalid")
        if self.equivalence_markers:
            self.retriever_id += "_domain_equivalence_v1"

    def _terms(self, text: str) -> list[str]:
        terms = list(tokenize(text).elements())
        normalized = unicodedata.normalize("NFKC", text).lower()
        terms.extend(
            marker
            for marker, phrases in self.equivalence_markers.items()
            if any(phrase in normalized for phrase in phrases)
        )
        return terms

    def search(self, request: RetrievalRequest, index: dict[str, Any]) -> list[RetrievalHit]:
        chunks = index["chunks"]
        if not chunks:
            return []
        query_terms = self._terms(request.query)
        if not query_terms:
            return []
        tokenized_corpus = [self._terms(chunk["text"]) for chunk in chunks]
        bm25 = BM25Okapi(tokenized_corpus, k1=self.k1, b=self.b)
        raw_scores = bm25.get_scores(query_terms)
        scores = {
            chunk["chunk_id"]: float(raw_scores[position])
            for position, chunk in enumerate(chunks)
        }
        ordered = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))[: request.top_k]
        return _validate_hits(
            [
                RetrievalHit(chunk_id=chunk_id, rank=rank, score=round(scores[chunk_id], 6))
                for rank, chunk_id in enumerate(ordered, start=1)
            ],
            request,
        )


def build_product_bm25_retriever() -> BM25Retriever:
    """Build the product lexical candidate with explicit domain equivalences."""

    return BM25Retriever(equivalence_markers=PRODUCT_BM25_EQUIVALENCE_MARKERS)


class DenseBgeRetriever:
    """Local FastEmbed BGE candidate with strict offline model custody."""

    retriever_id = "fastembed_bge_small_zh_v1.5"

    def __init__(self, *, manifest_path: Path = DEFAULT_MODEL_MANIFEST) -> None:
        self.manifest = load_local_model_manifest(manifest_path)
        self.model_root = validate_local_model_files(self.manifest)
        self._model: Any | None = None
        self._index_fingerprint: str | None = None
        self._chunk_ids: list[str] = []
        self._passage_vectors: np.ndarray | None = None

    def _ensure_index(self, index: dict[str, Any]) -> None:
        fingerprint = index["manifest"]["build_fingerprint"]
        if self._index_fingerprint == fingerprint:
            return
        from fastembed import TextEmbedding

        if self._model is None:
            self._model = TextEmbedding(
                model_name=self.manifest["model_name"],
                specific_model_path=str(self.model_root),
                providers=[self.manifest["provider"]],
                local_files_only=True,
            )
        self._chunk_ids = [chunk["chunk_id"] for chunk in index["chunks"]]
        vectors = [
            _normalize(vector)
            for vector in self._model.passage_embed([chunk["text"] for chunk in index["chunks"]])
        ]
        self._passage_vectors = np.stack(vectors)
        if self._passage_vectors.shape != (len(self._chunk_ids), self.manifest["dimension"]):
            raise ValueError("embedding_passage_dimension_invalid")
        self._index_fingerprint = fingerprint

    def search(self, request: RetrievalRequest, index: dict[str, Any]) -> list[RetrievalHit]:
        self._ensure_index(index)
        if self._model is None or self._passage_vectors is None:
            raise ValueError("embedding_model_not_initialized")
        query_vector = _normalize(next(iter(self._model.query_embed(request.query))))
        if query_vector.shape != (self.manifest["dimension"],):
            raise ValueError("embedding_query_dimension_invalid")
        raw_scores = self._passage_vectors @ query_vector
        scores = {
            chunk_id: float(raw_scores[position])
            for position, chunk_id in enumerate(self._chunk_ids)
        }
        ordered = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))[: request.top_k]
        return _validate_hits(
            [
                RetrievalHit(chunk_id=chunk_id, rank=rank, score=round(scores[chunk_id], 8))
                for rank, chunk_id in enumerate(ordered, start=1)
            ],
            request,
        )


class PgVectorDenseRetriever(DenseBgeRetriever):
    """BGE dense candidate that delegates similarity search to a vector store.

    Passage embeddings are computed by the same local FastEmbed model custody
    as the in-memory path; only storage and top-k cosine search move to the
    configured backend (see ``retrieval.vector_store``).
    """

    def __init__(
        self,
        *,
        store: VectorStore,
        manifest_path: Path = DEFAULT_MODEL_MANIFEST,
    ) -> None:
        super().__init__(manifest_path=manifest_path)
        self._store = store
        self._synced_fingerprint: str | None = None

    def _ensure_index(self, index: dict[str, Any]) -> None:
        super()._ensure_index(index)
        fingerprint = index["manifest"]["build_fingerprint"]
        if self._synced_fingerprint == fingerprint:
            return
        if self._passage_vectors is None:
            raise ValueError("embedding_model_not_initialized")
        self._store.sync(
            fingerprint,
            [
                (chunk_id, vector.tolist())
                for chunk_id, vector in zip(self._chunk_ids, self._passage_vectors)
            ],
        )
        self._synced_fingerprint = fingerprint

    def search(self, request: RetrievalRequest, index: dict[str, Any]) -> list[RetrievalHit]:
        self._ensure_index(index)
        if self._model is None:
            raise ValueError("embedding_model_not_initialized")
        query_vector = _normalize(next(iter(self._model.query_embed(request.query))))
        if query_vector.shape != (self.manifest["dimension"],):
            raise ValueError("embedding_query_dimension_invalid")
        rows = self._store.query(
            index["manifest"]["build_fingerprint"],
            query_vector.tolist(),
            request.top_k,
        )
        return _validate_hits(
            [
                RetrievalHit(chunk_id=chunk_id, rank=rank, score=round(score, 8))
                for rank, (chunk_id, score) in enumerate(rows, start=1)
            ],
            request,
        )

    def search_memory(
        self, request: RetrievalRequest, index: dict[str, Any]
    ) -> list[RetrievalHit]:
        """Reuse already-computed passage vectors without touching the store."""

        return super().search(request, index)


class FallbackDenseRetriever:
    """Use pgvector while healthy, then latch to the in-memory implementation."""

    retriever_id = DenseBgeRetriever.retriever_id

    def __init__(
        self,
        *,
        primary: PgVectorDenseRetriever,
    ) -> None:
        self._primary = primary
        self._primary_enabled = True
        self._state_lock = threading.Lock()

    @property
    def backend(self) -> str:
        with self._state_lock:
            return "pgvector" if self._primary_enabled else "memory"

    def search(self, request: RetrievalRequest, index: dict[str, Any]) -> list[RetrievalHit]:
        with self._state_lock:
            primary_enabled = self._primary_enabled
        if primary_enabled:
            try:
                return self._primary.search(request, index)
            except VectorStoreUnavailable:
                with self._state_lock:
                    self._primary_enabled = False
        return self._primary.search_memory(request, index)


def build_dense_retriever() -> DenseBgeRetriever | FallbackDenseRetriever:
    """Dense candidate for the product pipeline.

    The pgvector backend is used only when ``TRACEABLE_RETRIEVAL_VECTOR_DSN``
    is configured; otherwise the in-memory numpy path is returned unchanged.
    """

    store = pgvector_store_from_env()
    if store is None:
        return DenseBgeRetriever()
    readiness = store.readiness()
    if not readiness.ready:
        return DenseBgeRetriever()
    return FallbackDenseRetriever(
        primary=PgVectorDenseRetriever(store=store),
    )


class ReciprocalRankFusionRetriever:
    """RRF over frozen BM25 and dense rankings; no score calibration."""

    retriever_id = "rrf_bm25_bge_k60_depth20"

    def __init__(
        self,
        *,
        lexical: CandidateRetriever | None = None,
        dense: CandidateRetriever | None = None,
        rrf_k: int = 60,
        candidate_depth: int = 20,
    ) -> None:
        if rrf_k < 1 or candidate_depth < 1:
            raise ValueError("rrf_parameter_invalid")
        self.lexical = lexical or BM25Retriever()
        self.dense = dense or DenseBgeRetriever()
        self.rrf_k = rrf_k
        self.candidate_depth = candidate_depth

    def search(self, request: RetrievalRequest, index: dict[str, Any]) -> list[RetrievalHit]:
        depth = min(max(request.top_k, self.candidate_depth), len(index["chunks"]))
        component_request = RetrievalRequest(query=request.query, top_k=depth)
        rankings = (
            self.lexical.search(component_request, index),
            self.dense.search(component_request, index),
        )
        scores: dict[str, float] = {}
        for ranking in rankings:
            for hit in ranking:
                scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (
                    self.rrf_k + hit.rank
                )
        ordered = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))[: request.top_k]
        return _validate_hits(
            [
                RetrievalHit(chunk_id=chunk_id, rank=rank, score=round(scores[chunk_id], 8))
                for rank, chunk_id in enumerate(ordered, start=1)
            ],
            request,
        )

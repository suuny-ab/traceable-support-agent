from __future__ import annotations

import pytest

from traceable_support.retrieval import candidates
from traceable_support.retrieval.candidates import (
    FallbackDenseRetriever,
    RetrievalHit,
    RetrievalRequest,
)
from traceable_support.retrieval.vector_store import (
    VectorStoreReadiness,
    VectorStoreUnavailable,
)


class _PrimaryStub:
    def __init__(self, failures: list[Exception] | None = None) -> None:
        self.failures = list(failures or [])
        self.primary_calls = 0
        self.memory_calls = 0

    def search(self, request, index):
        self.primary_calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return [RetrievalHit(chunk_id="pg", rank=1, score=1.0)]

    def search_memory(self, request, index):
        self.memory_calls += 1
        return [RetrievalHit(chunk_id="memory", rank=1, score=1.0)]


class _StoreStub:
    def __init__(self, readiness: VectorStoreReadiness) -> None:
        self._readiness = readiness
        self.calls = 0

    def readiness(self) -> VectorStoreReadiness:
        self.calls += 1
        return self._readiness


def test_runtime_backend_failure_retries_in_memory_and_latches() -> None:
    primary = _PrimaryStub([VectorStoreUnavailable("vector_store_query_unavailable")])
    retriever = FallbackDenseRetriever(primary=primary)  # type: ignore[arg-type]
    request = RetrievalRequest(query="复位", top_k=1)

    assert retriever.backend == "pgvector"
    assert retriever.search(request, {})[0].chunk_id == "memory"
    assert retriever.backend == "memory"
    assert retriever.search(request, {})[0].chunk_id == "memory"
    assert primary.primary_calls == 1
    assert primary.memory_calls == 2


def test_non_backend_failure_is_not_hidden_by_fallback() -> None:
    primary = _PrimaryStub([ValueError("embedding_query_dimension_invalid")])
    retriever = FallbackDenseRetriever(primary=primary)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="embedding_query_dimension_invalid"):
        retriever.search(RetrievalRequest(query="复位", top_k=1), {})

    assert retriever.backend == "pgvector"
    assert primary.memory_calls == 0


def test_failed_readiness_keeps_the_existing_memory_builder(monkeypatch) -> None:
    store = _StoreStub(
        VectorStoreReadiness(False, "vector_store_readiness_unavailable")
    )
    memory = object()
    monkeypatch.setattr(candidates, "pgvector_store_from_env", lambda: store)
    monkeypatch.setattr(candidates, "DenseBgeRetriever", lambda: memory)

    assert candidates.build_dense_retriever() is memory
    assert store.calls == 1


def test_ready_store_selects_resilient_pgvector_builder(monkeypatch) -> None:
    store = _StoreStub(VectorStoreReadiness(True, "ready"))
    primary = _PrimaryStub()
    monkeypatch.setattr(candidates, "pgvector_store_from_env", lambda: store)
    monkeypatch.setattr(
        candidates, "PgVectorDenseRetriever", lambda *, store: primary
    )

    retriever = candidates.build_dense_retriever()
    assert isinstance(retriever, FallbackDenseRetriever)
    assert retriever.backend == "pgvector"
    assert store.calls == 1

"""pgvector store integration tests against a real Postgres database.

CI wires a ``pgvector/pgvector`` service and sets ``PGVECTOR_TEST_DSN`` so the
integration tests run for real; without the variable they skip.  Embeddings
are synthetic fixed-seed vectors — no embedding model is involved.  The module
stays importable without ``numpy``/``psycopg`` so the default test run (no
DSN, no live dependencies) collects and skips cleanly.
"""

from __future__ import annotations

import math
import os
import random

import pytest

from traceable_support.retrieval.vector_store import (
    DEFAULT_TABLE,
    VECTOR_STORE_DSN_ENV,
    PgVectorStore,
    pgvector_store_from_env,
)

DSN_ENV = "PGVECTOR_TEST_DSN"
DIMENSION = 512
FINGERPRINT = "pgvector-store-test-v1"


def _normalize(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in values))
    return [value / norm for value in values]


def _basis(index: int) -> list[float]:
    vector = [0.0] * DIMENSION
    vector[index] = 1.0
    return vector


@pytest.fixture()
def dsn() -> str:
    value = os.environ.get(DSN_ENV)
    if not value or not value.strip():
        pytest.skip(f"{DSN_ENV} not set; pgvector tests need a real database")
    return value


@pytest.fixture()
def store(dsn: str):
    psycopg = pytest.importorskip("psycopg")
    with psycopg.connect(dsn, autocommit=True) as connection:
        connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
        connection.execute(f"DROP TABLE IF EXISTS {DEFAULT_TABLE}")
    yield PgVectorStore(dsn, dimension=DIMENSION)
    with psycopg.connect(dsn, autocommit=True) as connection:
        connection.execute(f"DROP TABLE IF EXISTS {DEFAULT_TABLE}")


def test_store_is_built_only_when_the_dsn_is_configured(monkeypatch) -> None:
    monkeypatch.delenv(VECTOR_STORE_DSN_ENV, raising=False)
    assert pgvector_store_from_env() is None


def test_store_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError, match="vector_store_dsn_invalid"):
        PgVectorStore("", dimension=DIMENSION)
    with pytest.raises(ValueError, match="vector_store_dimension_invalid"):
        PgVectorStore("postgresql://traceable@127.0.0.1:5432/db", dimension=0)
    with pytest.raises(ValueError, match="vector_store_table_invalid"):
        PgVectorStore(
            "postgresql://traceable@127.0.0.1:5432/db",
            dimension=DIMENSION,
            table="bad;DROP",
        )


def test_sync_then_query_returns_cosine_order(store: PgVectorStore) -> None:
    items = [
        ("chunk-exact", _basis(0)),
        ("chunk-near", _normalize([0.9, 0.1] + [0.0] * (DIMENSION - 2))),
        ("chunk-mid", _normalize([0.5, 0.0, 0.5] + [0.0] * (DIMENSION - 3))),
        ("chunk-far", _basis(3)),
    ]
    assert store.sync(FINGERPRINT, items) == 4

    hits = store.query(FINGERPRINT, _basis(0), top_k=4)
    assert [chunk_id for chunk_id, _ in hits] == [
        "chunk-exact",
        "chunk-near",
        "chunk-mid",
        "chunk-far",
    ]
    scores = [score for _, score in hits]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == pytest.approx(1.0, abs=1e-6)
    assert scores[1] == pytest.approx(0.9939, abs=1e-3)
    assert scores[2] == pytest.approx(0.7071, abs=1e-3)
    assert scores[3] == pytest.approx(0.0, abs=1e-6)

    top_two = store.query(FINGERPRINT, _basis(0), top_k=2)
    assert [chunk_id for chunk_id, _ in top_two] == ["chunk-exact", "chunk-near"]


def test_repeated_sync_is_idempotent(store: PgVectorStore, dsn: str) -> None:
    psycopg = pytest.importorskip("psycopg")
    rng = random.Random(20260731)
    items = [
        (f"chunk-{position:02d}", _normalize([rng.random() for _ in range(DIMENSION)]))
        for position in range(16)
    ]
    assert store.sync(FINGERPRINT, items) == 16
    first = store.query(FINGERPRINT, items[0][1], top_k=16)

    assert store.sync(FINGERPRINT, items) == 16
    second = store.query(FINGERPRINT, items[0][1], top_k=16)

    with psycopg.connect(dsn, autocommit=True) as connection:
        row_count = connection.execute(
            f"SELECT count(*) FROM {DEFAULT_TABLE} WHERE fingerprint = %s",
            (FINGERPRINT,),
        ).fetchone()[0]
    assert row_count == 16
    assert first == second
    assert first[0][0] == "chunk-00"
    assert first[0][1] == pytest.approx(1.0, abs=1e-6)

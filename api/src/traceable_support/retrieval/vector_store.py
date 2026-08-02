"""Optional pgvector storage backend for the dense retrieval half.

The store is active only when ``TRACEABLE_RETRIEVAL_VECTOR_DSN`` points at a
Postgres database with the pgvector extension available.  ``psycopg`` and
``pgvector`` are imported lazily inside :class:`PgVectorStore`, so the default
in-memory numpy path and the replay image never import them.
"""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, Sequence

if TYPE_CHECKING:
    import psycopg

VECTOR_STORE_DSN_ENV = "TRACEABLE_RETRIEVAL_VECTOR_DSN"
DEFAULT_TABLE = "traceable_retrieval_vectors"
MIGRATIONS_TABLE = "traceable_retrieval_schema_migrations"
SCHEMA_COMPONENT = "pgvector_dense_store"
SCHEMA_VERSION = 1
_TABLE_NAME_RE = re.compile(r"[a-z][a-z0-9_]*")


class VectorStoreUnavailable(RuntimeError):
    """Stable, credential-free boundary error for an unavailable backend."""


@dataclass(frozen=True)
class VectorStoreReadiness:
    ready: bool
    reason: str


class VectorStore(Protocol):
    """Minimal contract the dense retriever needs from a vector backend."""

    def sync(
        self, fingerprint: str, items: Sequence[tuple[str, Sequence[float]]]
    ) -> int: ...

    def query(
        self, fingerprint: str, vector: Sequence[float], top_k: int
    ) -> list[tuple[str, float]]: ...

    def readiness(self) -> VectorStoreReadiness: ...


def _validate_vector(vector: Sequence[float], dimension: int) -> list[float]:
    values = [float(value) for value in vector]
    if len(values) != dimension:
        raise ValueError("vector_store_vector_dimension_invalid")
    if not all(math.isfinite(value) for value in values):
        raise ValueError("vector_store_vector_value_invalid")
    return values


class PgVectorStore:
    """Postgres + pgvector store for BusinessUnit passage embeddings.

    Rows are keyed by ``(fingerprint, chunk_id)`` where the fingerprint is the
    scoped index build fingerprint from the retrieval pipeline, so embeddings
    for different model scopes or corpus revisions never mix.  ``sync`` is
    idempotent: replaying the same inventory upserts identical rows.

    The connecting role must be allowed to ``CREATE EXTENSION vector`` (or the
    extension must already exist) and to create the storage table once.
    """

    def __init__(
        self, dsn: str, *, dimension: int, table: str = DEFAULT_TABLE
    ) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("vector_store_dsn_invalid")
        if not isinstance(dimension, int) or isinstance(dimension, bool) or dimension < 1:
            raise ValueError("vector_store_dimension_invalid")
        if not _TABLE_NAME_RE.fullmatch(table):
            raise ValueError("vector_store_table_invalid")
        self._dsn = dsn
        self._dimension = dimension
        self._table = table
        self._schema_ready = False

    @property
    def table(self) -> str:
        return self._table

    @property
    def dimension(self) -> int:
        return self._dimension

    def _connect(self) -> psycopg.Connection[Any]:
        import psycopg
        from pgvector.psycopg import register_vector

        connection = psycopg.connect(self._dsn, autocommit=True)
        connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(connection)
        return connection

    def _ensure_schema(self, connection: psycopg.Connection[Any]) -> None:
        if self._schema_ready:
            return
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} ("
            "component text PRIMARY KEY, "
            "version integer NOT NULL CHECK (version > 0), "
            "updated_at timestamptz NOT NULL DEFAULT now())"
        )
        connection.execute(
            f"CREATE TABLE IF NOT EXISTS {self._table} ("
            "fingerprint text NOT NULL, "
            "chunk_id text NOT NULL, "
            f"embedding vector({self._dimension}) NOT NULL, "
            "PRIMARY KEY (fingerprint, chunk_id))"
        )
        connection.execute(
            f"CREATE INDEX IF NOT EXISTS {self._table}_embedding_hnsw "
            f"ON {self._table} USING hnsw (embedding vector_cosine_ops)"
        )
        connection.execute(
            f"INSERT INTO {MIGRATIONS_TABLE} (component, version) VALUES (%s, %s) "
            "ON CONFLICT (component) DO NOTHING",
            (SCHEMA_COMPONENT, SCHEMA_VERSION),
        )
        self._schema_ready = True

    def _verify_schema(self, connection: psycopg.Connection[Any]) -> None:
        health = connection.execute("SELECT 1").fetchone()
        if health != (1,):
            raise VectorStoreUnavailable("vector_store_health_invalid")
        extension = connection.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        ).fetchone()
        if extension != (True,):
            raise VectorStoreUnavailable("vector_store_extension_missing")
        migration = connection.execute(
            f"SELECT version FROM {MIGRATIONS_TABLE} WHERE component = %s",
            (SCHEMA_COMPONENT,),
        ).fetchone()
        if migration != (SCHEMA_VERSION,):
            raise VectorStoreUnavailable("vector_store_migration_invalid")
        column_type = connection.execute(
            "SELECT format_type(attribute.atttypid, attribute.atttypmod) "
            "FROM pg_attribute AS attribute "
            "WHERE attribute.attrelid = to_regclass(%s) "
            "AND attribute.attname = 'embedding' AND NOT attribute.attisdropped",
            (self._table,),
        ).fetchone()
        if column_type != (f"vector({self._dimension})",):
            raise VectorStoreUnavailable("vector_store_dimension_mismatch")
        primary_key = connection.execute(
            "SELECT array_agg(attribute.attname ORDER BY key_column.ordinality) "
            "FROM pg_constraint AS constraint_row "
            "CROSS JOIN LATERAL unnest(constraint_row.conkey) "
            "WITH ORDINALITY AS key_column(attnum, ordinality) "
            "JOIN pg_attribute AS attribute "
            "ON attribute.attrelid = constraint_row.conrelid "
            "AND attribute.attnum = key_column.attnum "
            "WHERE constraint_row.contype = 'p' "
            "AND constraint_row.conrelid = to_regclass(%s)",
            (self._table,),
        ).fetchone()
        if primary_key != (["fingerprint", "chunk_id"],):
            raise VectorStoreUnavailable("vector_store_primary_key_invalid")
        index_name = f"{self._table}_embedding_hnsw"
        index_definition = connection.execute(
            "SELECT indexdef FROM pg_indexes "
            "WHERE schemaname = current_schema() AND tablename = %s AND indexname = %s",
            (self._table, index_name),
        ).fetchone()
        if (
            index_definition is None
            or "USING hnsw (embedding vector_cosine_ops)" not in index_definition[0]
        ):
            raise VectorStoreUnavailable("vector_store_index_invalid")

    def readiness(self) -> VectorStoreReadiness:
        """Migrate and verify every prerequisite before the backend is selected."""

        try:
            with self._connect() as connection:
                self._ensure_schema(connection)
                self._verify_schema(connection)
        except VectorStoreUnavailable as exc:
            return VectorStoreReadiness(ready=False, reason=str(exc))
        except Exception:
            return VectorStoreReadiness(
                ready=False, reason="vector_store_readiness_unavailable"
            )
        return VectorStoreReadiness(ready=True, reason="ready")

    def sync(
        self, fingerprint: str, items: Sequence[tuple[str, Sequence[float]]]
    ) -> int:
        if not isinstance(fingerprint, str) or not fingerprint:
            raise ValueError("vector_store_fingerprint_invalid")
        rows = []
        for chunk_id, vector in items:
            if not isinstance(chunk_id, str) or not chunk_id:
                raise ValueError("vector_store_chunk_id_invalid")
            rows.append(
                (fingerprint, chunk_id, _validate_vector(vector, self._dimension))
            )
        chunk_ids = [row[1] for row in rows]
        if len(set(chunk_ids)) != len(chunk_ids):
            raise ValueError("vector_store_chunk_id_duplicate")
        if not rows:
            return 0
        try:
            from pgvector import Vector

            with self._connect() as connection:
                self._ensure_schema(connection)
                with connection.cursor() as cursor:
                    cursor.executemany(
                        f"INSERT INTO {self._table} (fingerprint, chunk_id, embedding) "
                        "VALUES (%s, %s, %s) "
                        "ON CONFLICT (fingerprint, chunk_id) "
                        "DO UPDATE SET embedding = EXCLUDED.embedding",
                        [
                            (fingerprint, chunk_id, Vector(values))
                            for fingerprint, chunk_id, values in rows
                        ],
                    )
        except Exception as exc:
            raise VectorStoreUnavailable("vector_store_sync_unavailable") from exc
        return len(rows)

    def query(
        self, fingerprint: str, vector: Sequence[float], top_k: int
    ) -> list[tuple[str, float]]:
        if not isinstance(fingerprint, str) or not fingerprint:
            raise ValueError("vector_store_fingerprint_invalid")
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
            raise ValueError("vector_store_top_k_invalid")
        values = _validate_vector(vector, self._dimension)
        try:
            from pgvector import Vector

            probe = Vector(values)
            with self._connect() as connection:
                self._ensure_schema(connection)
                rows = connection.execute(
                    f"SELECT chunk_id, 1 - (embedding <=> %s) AS similarity "
                    f"FROM {self._table} "
                    "WHERE fingerprint = %s "
                    "ORDER BY embedding <=> %s, chunk_id "
                    "LIMIT %s",
                    (probe, fingerprint, probe, top_k),
                ).fetchall()
        except Exception as exc:
            raise VectorStoreUnavailable("vector_store_query_unavailable") from exc
        return [(str(chunk_id), float(similarity)) for chunk_id, similarity in rows]


def pgvector_store_from_env() -> PgVectorStore | None:
    """Build the store only when the operator configured a DSN."""

    dsn = os.environ.get(VECTOR_STORE_DSN_ENV)
    if dsn is None or not dsn.strip():
        return None
    from .candidates import load_local_model_manifest

    return PgVectorStore(dsn, dimension=load_local_model_manifest()["dimension"])


__all__ = [
    "DEFAULT_TABLE",
    "MIGRATIONS_TABLE",
    "SCHEMA_COMPONENT",
    "SCHEMA_VERSION",
    "VECTOR_STORE_DSN_ENV",
    "PgVectorStore",
    "VectorStore",
    "VectorStoreReadiness",
    "VectorStoreUnavailable",
    "pgvector_store_from_env",
]

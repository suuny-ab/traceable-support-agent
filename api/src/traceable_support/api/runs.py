"""SQLite-backed public run control plane.

This module owns queueing, persistent budget reservation, retention, status
transitions, and human-decision recording. It receives only the stable product
runner protocol and never assembles live dependencies by itself.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import secrets
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from traceable_support.product.types import ProductRunner, RunInput

from .preflight import preflight
from .projection import (
    blocked_result as make_blocked_result,
    execution_failure_result as make_execution_failure_result,
    project_package as project_public_package,
    restart_result as make_restart_result,
)


RUN_RESERVATION_CNY_NANOS = 1_000_000_000
DAILY_LIMIT_CNY_NANOS = 20_000_000_000
MONTHLY_LIMIT_CNY_NANOS = 100_000_000_000
BROWSER_DAILY_RUN_LIMIT = 10
MAX_RUNNING = 2
MAX_QUEUED = 4
MAX_INPUT_CHARS = 500
MAX_DECISION_TEXT_CHARS = 1_000
RETENTION_DAYS = 30
GLOBAL_DAILY_BLOCKED_LIMIT = 2_000
MAX_STORED_RUNS = 20_000

TERMINAL_STATUSES = frozenset({"completed", "handoff"})
ACTIVE_STATUSES = frozenset(
    {"queued", "retrieving", "planning", "generating", "validating"}
)
ALL_STATUSES = TERMINAL_STATUSES | ACTIVE_STATUSES

class PublicApiError(RuntimeError):
    """A detached, client-safe public API error."""

    def __init__(
        self,
        status_code: int,
        code: str,
        *,
        replay_available: bool = False,
        retry_after_seconds: int | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.replay_available = replay_available
        self.retry_after_seconds = retry_after_seconds
        super().__init__(code)
        self.__cause__ = None
        self.__context__ = None


@dataclass(frozen=True)
class Submission:
    run_id: str
    browser_token: str
    estimated_wait_seconds: int


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class _SingleInstanceFileLock:
    """Process-level guard for the one-writer SQLite and Provider boundary."""

    def __init__(self, path: Path) -> None:
        self._file = path.open("a+b")
        self._closed = False
        self._file.seek(0, os.SEEK_END)
        if self._file.tell() == 0:
            self._file.write(b"0")
            self._file.flush()
        self._file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._file.close()
            self._closed = True
            raise RuntimeError("public_api_single_instance_required") from None

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._file.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        finally:
            self._file.close()
            self._closed = True


class PublicRunService:
    """Persistent public-run service with a bounded two-worker executor."""

    def __init__(
        self,
        database: Path,
        *,
        allowed_origin: str,
        live_enabled: bool | None = None,
        product_runner: ProductRunner | None = None,
        now: Callable[[], datetime] = _utc_now,
        run_reservation_cny_nanos: int = RUN_RESERVATION_CNY_NANOS,
        daily_limit_cny_nanos: int = DAILY_LIMIT_CNY_NANOS,
        monthly_limit_cny_nanos: int = MONTHLY_LIMIT_CNY_NANOS,
        browser_daily_limit: int = BROWSER_DAILY_RUN_LIMIT,
        max_running: int = MAX_RUNNING,
        max_queued: int = MAX_QUEUED,
        retention_days: int = RETENTION_DAYS,
        blocked_daily_limit: int = GLOBAL_DAILY_BLOCKED_LIMIT,
        max_stored_runs: int = MAX_STORED_RUNS,
        start_cleanup_thread: bool = True,
    ) -> None:
        if not allowed_origin.startswith("https://") and not allowed_origin.startswith("http://"):
            raise ValueError("public_api_allowed_origin_invalid")
        if any(type(value) is not int or value < 1 for value in (
            run_reservation_cny_nanos,
            daily_limit_cny_nanos,
            monthly_limit_cny_nanos,
            browser_daily_limit,
            max_running,
            max_queued,
            retention_days,
            blocked_daily_limit,
            max_stored_runs,
        )):
            raise ValueError("public_api_limit_invalid")
        self.database = Path(database).resolve()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.allowed_origin = allowed_origin.rstrip("/")
        self.live_enabled = (
            _parse_bool(os.environ.get("TRACEABLE_PUBLIC_LIVE_ENABLED"))
            if live_enabled is None
            else bool(live_enabled)
        )
        self.product_runner = product_runner
        self.now = now
        self.run_reservation_cny_nanos = run_reservation_cny_nanos
        self.daily_limit_cny_nanos = daily_limit_cny_nanos
        self.monthly_limit_cny_nanos = monthly_limit_cny_nanos
        self.browser_daily_limit = browser_daily_limit
        self.max_running = max_running
        self.max_queued = max_queued
        self.retention_days = retention_days
        self.blocked_daily_limit = blocked_daily_limit
        self.max_stored_runs = max_stored_runs
        self._db_lock = threading.RLock()
        self._stop = threading.Event()
        self._cleanup_thread: threading.Thread | None = None
        self._shutdown = False
        self._instance_lock = _SingleInstanceFileLock(
            self.database.with_name(self.database.name + ".lock")
        )
        self._executor = ThreadPoolExecutor(
            max_workers=max_running, thread_name_prefix="public-run"
        )
        try:
            self._initialize()
            self.cleanup_expired()
        except BaseException:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._instance_lock.close()
            raise
        if start_cleanup_thread:
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                name="public-retention",
                daemon=True,
            )
            self._cleanup_thread.start()

    @property
    def live_available(self) -> bool:
        return bool(
            self.live_enabled
            and self.product_runner is not None
            and self.product_runner.is_ready
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.database), timeout=10, isolation_level=None
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _initialize(self) -> None:
        with self._db_lock, closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = FULL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    input_mode TEXT NOT NULL,
                    input_text TEXT,
                    input_sha256 TEXT NOT NULL,
                    product_model TEXT NOT NULL,
                    browser_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT,
                    error_code TEXT,
                    decision TEXT,
                    decision_text TEXT,
                    decided_at TEXT,
                    reserved_cny_nanos INTEGER NOT NULL,
                    provider_calls INTEGER DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS runs_active_idx ON runs(status, created_at);
                CREATE INDEX IF NOT EXISTS runs_browser_idx ON runs(browser_hash, created_at);
                CREATE TABLE IF NOT EXISTS budget_counters (
                    period_kind TEXT NOT NULL,
                    period_key TEXT NOT NULL,
                    reserved_cny_nanos INTEGER NOT NULL,
                    run_count INTEGER NOT NULL,
                    PRIMARY KEY(period_kind, period_key)
                );
                CREATE TABLE IF NOT EXISTS metric_rollups (
                    day_key TEXT NOT NULL,
                    terminal_status TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    run_count INTEGER NOT NULL,
                    provider_calls INTEGER NOT NULL,
                    reserved_cny_nanos INTEGER NOT NULL,
                    provider_calls_unknown INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(day_key, terminal_status, decision)
                );
                CREATE TABLE IF NOT EXISTS maintenance_state (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    pending_secure_erase INTEGER NOT NULL,
                    last_cleanup_at TEXT
                );
                INSERT OR IGNORE INTO maintenance_state(singleton,pending_secure_erase,last_cleanup_at)
                    VALUES(1,0,NULL);
                """
            )
            metric_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(metric_rollups)").fetchall()
            }
            if "provider_calls_unknown" not in metric_columns:
                connection.execute(
                    "ALTER TABLE metric_rollups ADD COLUMN provider_calls_unknown INTEGER NOT NULL DEFAULT 0"
                )
            provider_calls_column = next(
                (
                    row
                    for row in connection.execute("PRAGMA table_info(runs)").fetchall()
                    if row["name"] == "provider_calls"
                ),
                None,
            )
            if provider_calls_column is not None and provider_calls_column["notnull"]:
                self._migrate_provider_calls_nullable(connection)
            stale = connection.execute(
                "SELECT run_id FROM runs WHERE status IN ('queued','retrieving','planning','generating','validating')"
            ).fetchall()
            if stale:
                now = _iso(self.now())
                result_json = _canonical_json(make_restart_result())
                connection.execute("BEGIN IMMEDIATE")
                try:
                    for row in stale:
                        connection.execute(
                            "UPDATE runs SET status='handoff', updated_at=?, result_json=?, error_code=?, provider_calls=NULL WHERE run_id=?",
                            (now, result_json, "service_restarted_no_retry", row["run_id"]),
                        )
                    connection.commit()
                except BaseException:
                    connection.rollback()
                    raise

    @staticmethod
    def _migrate_provider_calls_nullable(connection: sqlite3.Connection) -> None:
        """Allow restart recovery to record an unknown Provider call count."""

        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute(
                """
                CREATE TABLE runs_nullable_provider_calls (
                    run_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    input_mode TEXT NOT NULL,
                    input_text TEXT,
                    input_sha256 TEXT NOT NULL,
                    product_model TEXT NOT NULL,
                    browser_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT,
                    error_code TEXT,
                    decision TEXT,
                    decision_text TEXT,
                    decided_at TEXT,
                    reserved_cny_nanos INTEGER NOT NULL,
                    provider_calls INTEGER DEFAULT 0
                )
                """
            )
            columns = (
                "run_id,task_type,input_mode,input_text,input_sha256,product_model,"
                "browser_hash,created_at,updated_at,status,result_json,error_code,"
                "decision,decision_text,decided_at,reserved_cny_nanos,provider_calls"
            )
            connection.execute(
                f"INSERT INTO runs_nullable_provider_calls ({columns}) SELECT {columns} FROM runs"
            )
            connection.execute("DROP TABLE runs")
            connection.execute(
                "ALTER TABLE runs_nullable_provider_calls RENAME TO runs"
            )
            connection.execute(
                "CREATE INDEX runs_active_idx ON runs(status, created_at)"
            )
            connection.execute(
                "CREATE INDEX runs_browser_idx ON runs(browser_hash, created_at)"
            )
            connection.commit()
        except BaseException:
            connection.rollback()
            raise

    def health(self) -> dict[str, str]:
        return {
            "status": "ok",
            "service": "traceable-support-public-api",
            "live_experience": "available" if self.live_available else "replay_only",
        }

    def submit(self, payload: dict[str, Any], *, browser_token: str | None) -> Submission:
        if type(payload) is not dict or set(payload) != {
            "task_type", "input_mode", "text", "product_model", "consent"
        }:
            raise PublicApiError(400, "run_request_invalid")
        task_type = payload.get("task_type")
        input_mode = payload.get("input_mode")
        text = payload.get("text")
        product_model = payload.get("product_model")
        consent = payload.get("consent")
        if task_type not in {"qa", "ticket"}:
            raise PublicApiError(400, "task_type_invalid")
        if input_mode not in {"preset", "free_text"}:
            raise PublicApiError(400, "input_mode_invalid")
        if type(text) is not str or not text.strip() or len(text) > MAX_INPUT_CHARS:
            raise PublicApiError(400, "input_text_invalid")
        if product_model not in {"CZ-R1", "CZ-R2"}:
            raise PublicApiError(400, "product_model_invalid")
        if consent is not True:
            raise PublicApiError(400, "consent_required")

        normalized = text.strip()
        if task_type == "ticket" and len(normalized) < 8:
            raise PublicApiError(400, "ticket_text_too_short")
        token = browser_token if type(browser_token) is str and re.fullmatch(
            r"[A-Za-z0-9_-]{20,100}", browser_token
        ) else secrets.token_urlsafe(24)
        browser_hash = _sha256_text(token)
        run_id = secrets.token_urlsafe(24)
        now_value = self.now().astimezone(timezone.utc)
        created_at = _iso(now_value)
        preflight_code = preflight(normalized)

        if preflight_code is not None:
            self._insert_blocked_run(
                run_id=run_id,
                task_type=task_type,
                input_mode=input_mode,
                product_model=product_model,
                browser_hash=browser_hash,
                created_at=created_at,
                day_start=_iso(
                    now_value.replace(hour=0, minute=0, second=0, microsecond=0)
                ),
                code=preflight_code,
            )
            return Submission(run_id, token, 0)

        if not self.live_available:
            raise PublicApiError(503, "live_experience_unavailable", replay_available=True)

        day_key = now_value.strftime("%Y-%m-%d")
        month_key = now_value.strftime("%Y-%m")
        day_start = now_value.replace(hour=0, minute=0, second=0, microsecond=0)
        with self._db_lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                stored_count = connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
                if stored_count >= self.max_stored_runs:
                    raise PublicApiError(
                        503, "storage_capacity_reached", replay_available=True
                    )
                browser_count = connection.execute(
                    "SELECT COUNT(*) FROM runs WHERE browser_hash=? AND created_at>=?",
                    (browser_hash, _iso(day_start)),
                ).fetchone()[0]
                if browser_count >= self.browser_daily_limit:
                    raise PublicApiError(429, "browser_daily_limit_reached", replay_available=True)
                active_count = connection.execute(
                    "SELECT COUNT(*) FROM runs WHERE status IN ('queued','retrieving','planning','generating','validating')"
                ).fetchone()[0]
                if active_count >= self.max_running + self.max_queued:
                    raise PublicApiError(
                        503,
                        "run_queue_full",
                        replay_available=True,
                        retry_after_seconds=120,
                    )
                self._reserve_counter(
                    connection,
                    kind="day",
                    key=day_key,
                    amount=self.run_reservation_cny_nanos,
                    limit=self.daily_limit_cny_nanos,
                    error_code="daily_budget_exhausted",
                )
                self._reserve_counter(
                    connection,
                    kind="month",
                    key=month_key,
                    amount=self.run_reservation_cny_nanos,
                    limit=self.monthly_limit_cny_nanos,
                    error_code="monthly_budget_exhausted",
                )
                connection.execute(
                    "INSERT INTO runs (run_id,task_type,input_mode,input_text,input_sha256,product_model,browser_hash,created_at,updated_at,status,reserved_cny_nanos) VALUES (?,?,?,?,?,?,?,?,?,'queued',?)",
                    (
                        run_id,
                        task_type,
                        input_mode,
                        normalized,
                        _sha256_text(normalized),
                        product_model,
                        browser_hash,
                        created_at,
                        created_at,
                        self.run_reservation_cny_nanos,
                    ),
                )
                connection.commit()
            except PublicApiError:
                connection.rollback()
                raise
            except BaseException:
                connection.rollback()
                raise

        try:
            self._executor.submit(self._execute, run_id)
        except RuntimeError:
            self._finish(
                run_id,
                status="handoff",
                result=make_execution_failure_result(),
                provider_calls=None,
                error_code="worker_submission_failed",
            )
            return Submission(run_id, token, 0)
        estimated = 120 if active_count < self.max_running else 240
        return Submission(run_id, token, estimated)

    def _reserve_counter(
        self,
        connection: sqlite3.Connection,
        *,
        kind: str,
        key: str,
        amount: int,
        limit: int,
        error_code: str,
    ) -> None:
        row = connection.execute(
            "SELECT reserved_cny_nanos FROM budget_counters WHERE period_kind=? AND period_key=?",
            (kind, key),
        ).fetchone()
        current = 0 if row is None else row[0]
        if current > limit - amount:
            raise PublicApiError(503, error_code, replay_available=True)
        connection.execute(
            "INSERT INTO budget_counters(period_kind,period_key,reserved_cny_nanos,run_count) VALUES(?,?,?,1) "
            "ON CONFLICT(period_kind,period_key) DO UPDATE SET reserved_cny_nanos=reserved_cny_nanos+excluded.reserved_cny_nanos, run_count=run_count+1",
            (kind, key, amount),
        )

    def _insert_blocked_run(
        self,
        *,
        run_id: str,
        task_type: str,
        input_mode: str,
        product_model: str,
        browser_hash: str,
        created_at: str,
        day_start: str,
        code: str,
    ) -> None:
        result = make_blocked_result(code)
        with self._db_lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                browser_count = connection.execute(
                    "SELECT COUNT(*) FROM runs WHERE browser_hash=? AND created_at>=?",
                    (browser_hash, day_start),
                ).fetchone()[0]
                if browser_count >= self.browser_daily_limit:
                    raise PublicApiError(
                        429, "browser_daily_limit_reached", replay_available=True
                    )
                blocked_count = connection.execute(
                    "SELECT COUNT(*) FROM runs WHERE reserved_cny_nanos=0 AND created_at>=?",
                    (day_start,),
                ).fetchone()[0]
                if blocked_count >= self.blocked_daily_limit:
                    raise PublicApiError(
                        503, "blocked_run_capacity_reached", replay_available=True
                    )
                stored_count = connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
                if stored_count >= self.max_stored_runs:
                    raise PublicApiError(
                        503, "storage_capacity_reached", replay_available=True
                    )
                connection.execute(
                    "INSERT INTO runs (run_id,task_type,input_mode,input_text,input_sha256,product_model,browser_hash,created_at,updated_at,status,result_json,error_code,reserved_cny_nanos,provider_calls) VALUES (?,?,?,?,?,?,?,?,?,'handoff',?,?,0,0)",
                    (
                        run_id,
                        task_type,
                        input_mode,
                        None,
                        _sha256_text(code),
                        product_model,
                        browser_hash,
                        created_at,
                        created_at,
                        _canonical_json(result),
                        code,
                    ),
                )
                connection.commit()
            except PublicApiError:
                connection.rollback()
                raise
            except BaseException:
                connection.rollback()
                raise

    def _execute(self, run_id: str) -> None:
        row = self._claim_for_execution(run_id)
        if row is None:
            return

        def on_stage(stage: str, status: str) -> None:
            if status != "started" and stage != "gate":
                return
            mapped = {
                "retrieval": "retrieving",
                "enumeration": "planning",
                "generation": "generating",
                "gate": "validating",
            }.get(stage)
            if mapped is not None:
                self._set_status(run_id, mapped)

        try:
            if self.product_runner is None:
                raise RuntimeError("product_runner_not_configured")
            execution = self.product_runner.execute(
                RunInput(
                    run_id=str(row["run_id"]),
                    task_type=str(row["task_type"]),
                    text=str(row["input_text"]),
                    product_model=str(row["product_model"]),
                    reserved_cny_nanos=int(row["reserved_cny_nanos"]),
                ),
                on_stage,
            )
            package = execution.package
            call_count = execution.provider_call_count
            result = project_public_package(package, provider_call_count=call_count)
            terminal = "completed" if result["outcome"] == "candidate" else "handoff"
            self._finish(
                run_id,
                status=terminal,
                result=result,
                provider_calls=call_count,
                error_code=package.get("handoff_reason"),
            )
        except BaseException as exc:
            logging.error(
                "public worker stopped run=%s type=%s",
                _sha256_text(run_id)[:12],
                type(exc).__name__,
            )
            self._finish(
                run_id,
                status="handoff",
                result=make_execution_failure_result(),
                provider_calls=None,
                error_code="background_execution_error",
            )

    def _load_internal(self, run_id: str) -> sqlite3.Row:
        with self._db_lock, closing(self._connect()) as connection:
            row = connection.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            raise PublicApiError(404, "run_not_found")
        return row

    def _claim_for_execution(self, run_id: str) -> sqlite3.Row | None:
        with self._db_lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT * FROM runs WHERE run_id=?", (run_id,)
                ).fetchone()
                if row is None or row["status"] != "queued":
                    connection.commit()
                    return None
                connection.execute(
                    "UPDATE runs SET status='retrieving', updated_at=? WHERE run_id=? AND status='queued'",
                    (_iso(self.now()), run_id),
                )
                connection.commit()
                return row
            except BaseException:
                connection.rollback()
                raise

    def _set_status(self, run_id: str, status: str) -> None:
        if status not in ACTIVE_STATUSES:
            raise ValueError("public_api_status_invalid")
        with self._db_lock, closing(self._connect()) as connection:
            connection.execute(
                "UPDATE runs SET status=?, updated_at=? WHERE run_id=? AND status NOT IN ('completed','handoff')",
                (status, _iso(self.now()), run_id),
            )

    def _finish(
        self,
        run_id: str,
        *,
        status: str,
        result: dict[str, Any],
        provider_calls: int | None,
        error_code: str | None,
    ) -> None:
        if status not in TERMINAL_STATUSES or not (
            provider_calls is None
            or (type(provider_calls) is int and provider_calls >= 0)
        ):
            raise ValueError("public_api_finish_invalid")
        with self._db_lock, closing(self._connect()) as connection:
            connection.execute(
                "UPDATE runs SET status=?, updated_at=?, result_json=?, error_code=?, provider_calls=? WHERE run_id=? AND status NOT IN ('completed','handoff')",
                (
                    status,
                    _iso(self.now()),
                    _canonical_json(result),
                    error_code,
                    provider_calls,
                    run_id,
                ),
            )

    def get_run(self, run_id: str) -> dict[str, Any]:
        if not re.fullmatch(r"[A-Za-z0-9_-]{20,100}", run_id):
            raise PublicApiError(404, "run_not_found")
        row = self._load_internal(run_id)
        value: dict[str, Any] = {
            "run_id": row["run_id"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        if row["result_json"] is not None:
            value["result"] = json.loads(row["result_json"])
        if row["decision"] is not None:
            value["decision"] = {
                "type": row["decision"],
                "decided_at": row["decided_at"],
            }
        return value

    def decide(self, run_id: str, payload: dict[str, Any]) -> dict[str, str]:
        if type(payload) is not dict or not set(payload).issubset({"decision", "decision_text"}) or "decision" not in payload:
            raise PublicApiError(400, "decision_request_invalid")
        decision = payload.get("decision")
        decision_text = payload.get("decision_text")
        if decision not in {"approve", "edit", "reject"}:
            raise PublicApiError(400, "decision_invalid")
        if decision == "edit":
            if type(decision_text) is not str or not decision_text.strip() or len(decision_text) > MAX_DECISION_TEXT_CHARS:
                raise PublicApiError(400, "decision_text_invalid")
            decision_text = decision_text.strip()
        elif decision_text is not None:
            raise PublicApiError(400, "decision_text_unexpected")
        with self._db_lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT status,result_json,decision FROM runs WHERE run_id=?", (run_id,)
                ).fetchone()
                if row is None:
                    raise PublicApiError(404, "run_not_found")
                if row["status"] != "completed" or row["result_json"] is None or json.loads(row["result_json"]).get("outcome") != "candidate":
                    raise PublicApiError(409, "decision_requires_candidate")
                if row["decision"] is not None:
                    raise PublicApiError(409, "decision_already_recorded")
                decided_at = _iso(self.now())
                connection.execute(
                    "UPDATE runs SET decision=?, decision_text=?, decided_at=?, updated_at=? WHERE run_id=?",
                    (decision, decision_text, decided_at, decided_at, run_id),
                )
                connection.commit()
            except PublicApiError:
                connection.rollback()
                raise
            except BaseException:
                connection.rollback()
                raise
        return {"status": "recorded", "decision": decision}

    def cleanup_expired(self) -> dict[str, int]:
        cutoff = self.now().astimezone(timezone.utc) - timedelta(days=self.retention_days)
        removed = 0
        with self._db_lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                groups = connection.execute(
                    "SELECT substr(created_at,1,10) day_key,status,COALESCE(decision,'none') decision,COUNT(*) run_count,SUM(COALESCE(provider_calls,0)) provider_calls,SUM(reserved_cny_nanos) reserved,SUM(CASE WHEN provider_calls IS NULL THEN 1 ELSE 0 END) provider_calls_unknown FROM runs WHERE created_at<? GROUP BY day_key,status,decision",
                    (_iso(cutoff),),
                ).fetchall()
                for row in groups:
                    connection.execute(
                        "INSERT INTO metric_rollups(day_key,terminal_status,decision,run_count,provider_calls,reserved_cny_nanos,provider_calls_unknown) VALUES(?,?,?,?,?,?,?) "
                        "ON CONFLICT(day_key,terminal_status,decision) DO UPDATE SET run_count=run_count+excluded.run_count, provider_calls=provider_calls+excluded.provider_calls, reserved_cny_nanos=reserved_cny_nanos+excluded.reserved_cny_nanos, provider_calls_unknown=provider_calls_unknown+excluded.provider_calls_unknown",
                        tuple(row),
                    )
                removed = connection.execute(
                    "DELETE FROM runs WHERE created_at<?", (_iso(cutoff),)
                ).rowcount
                if removed:
                    connection.execute(
                        "UPDATE maintenance_state SET pending_secure_erase=1 WHERE singleton=1"
                    )
                connection.execute(
                    "UPDATE maintenance_state SET last_cleanup_at=? WHERE singleton=1",
                    (_iso(self.now()),),
                )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
            pending_erase = connection.execute(
                "SELECT pending_secure_erase FROM maintenance_state WHERE singleton=1"
            ).fetchone()[0]
            if pending_erase:
                connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                connection.execute("VACUUM")
                connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                connection.execute(
                    "UPDATE maintenance_state SET pending_secure_erase=0 WHERE singleton=1"
                )
        return {"removed_runs": removed, "rollup_groups": len(groups)}

    def _cleanup_loop(self) -> None:
        while not self._stop.wait(3600):
            try:
                self.cleanup_expired()
            except BaseException as exc:
                logging.error("public retention failed type=%s", type(exc).__name__)

    def shutdown(self, *, wait: bool = True) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        self._stop.set()
        self._executor.shutdown(wait=wait, cancel_futures=not wait)
        if self._cleanup_thread is not None and wait:
            self._cleanup_thread.join(timeout=2)
        self._instance_lock.close()


__all__ = [
    "ACTIVE_STATUSES",
    "ALL_STATUSES",
    "PublicApiError",
    "PublicRunService",
    "Submission",
    "project_package",
]

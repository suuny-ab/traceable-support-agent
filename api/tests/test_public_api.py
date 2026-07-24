from __future__ import annotations

import http.client
import json
import sqlite3
import tempfile
import threading
import time
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from traceable_support.api.http import create_server
from traceable_support.api.projection import project_package
from traceable_support.api.runs import PublicApiError, PublicRunService
from traceable_support.product.types import ExecutionResult, RunInput


ORIGIN = "https://portfolio.example"


class _FixtureProductRunner:
    is_ready = True

    def __init__(self, callback: object) -> None:
        self.callback = callback

    def execute(self, value: RunInput, stage: object) -> ExecutionResult:
        package, calls = self.callback(
            {
                "run_id": value.run_id,
                "task_type": value.task_type,
                "input_text": value.text,
                "product_model": value.product_model,
                "reserved_cny_nanos": value.reserved_cny_nanos,
            },
            stage,
        )
        return ExecutionResult(package=package, provider_call_count=calls)


def _product_runner(callback: object) -> _FixtureProductRunner:
    return _FixtureProductRunner(callback)


def _payload(
    text: str = "CZ-R1 如何完成清扫后自动回充？",
    *,
    task_type: str = "qa",
    input_mode: str = "preset",
    product_model: str = "CZ-R1",
) -> dict[str, object]:
    return {
        "task_type": task_type,
        "input_mode": input_mode,
        "text": text,
        "product_model": product_model,
        "consent": True,
    }


def _candidate_package(task_type: str = "qa") -> dict[str, object]:
    content: dict[str, object]
    candidate_key: str
    if task_type == "ticket":
        content = {
            "draft_reply": "请先清理轮组，并确认设备已断电。",
            "action_steps": ["清理轮组", "重新检查"],
        }
        candidate_key = "proposal"
    else:
        content = {"answer": {"text": "设备会在低电量时自动回充，满足条件后继续清扫。"}}
        candidate_key = "answer"
    return {
        "outcome": "candidate",
        "checklist": {
            "obligations": [
                {"description": "说明自动回充行为"},
                {"description": "绑定产品资料来源"},
            ]
        },
        candidate_key: {"content": content, "used_evidence_ids": ["E1"]},
        "evidence": [
            {
                "evidence_id": "E1",
                "document_id": "DOC-CZ-R1",
                "section_heading": "自动回充与续扫",
                "text": "电量不足时，CZ-R1 会返回充电座。",
            },
            {
                "evidence_id": "UNUSED",
                "document_id": "DOC-CZ-R2",
                "section_heading": "未使用证据",
                "text": "不应投影到公开结果。",
            },
        ],
        "gates": {
            "step1_contract": "passed",
            "completeness_gate": {"pass": True},
        },
        "handoff_reason": None,
    }


class _Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 7, 22, 6, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value


def _wait_for_terminal(service: PublicRunService, run_id: str) -> dict[str, object]:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        value = service.get_run(run_id)
        if value["status"] in {"completed", "handoff"}:
            return value
        time.sleep(0.01)
    raise AssertionError("public run did not reach a terminal state")


class PublicRunServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database = Path(self.temporary.name) / "public.sqlite3"
        self.services: list[PublicRunService] = []

    def tearDown(self) -> None:
        for service in self.services:
            service.shutdown(wait=True)
        self.temporary.cleanup()

    def _service(self, **kwargs: object) -> PublicRunService:
        service = PublicRunService(
            self.database,
            allowed_origin=ORIGIN,
            start_cleanup_thread=False,
            **kwargs,
        )
        self.services.append(service)
        return service

    def test_failed_package_stays_handoff_after_provider_calls(self) -> None:
        package = _candidate_package()
        package["outcome"] = "handoff"
        package["handoff_reason"] = "completeness_gate_failed"

        result = project_package(package, provider_call_count=2)

        self.assertEqual(result["mode"], "handoff")
        self.assertEqual(result["outcome"], "handoff")
        self.assertEqual(result["provider_call_count"], 2)
        self.assertEqual(result["handoff_reason"], "completeness_gate_failed")

    def test_preflight_blocks_sensitive_scope_and_safety_without_runner(self) -> None:
        calls = 0

        def runner(_row: dict[str, object], _stage: object) -> tuple[dict[str, object], int]:
            nonlocal calls
            calls += 1
            return _candidate_package(), 2

        service = self._service(live_enabled=True, product_runner=_product_runner(runner))
        cases = [
            ("CZ-R1 我的手机号是 13800138000", "sensitive_input_blocked", "CZ-R1"),
            ("请帮我写一封求职邮件", "out_of_scope_blocked", "CZ-R1"),
            ("请写一首关于设备的诗", "out_of_scope_blocked", "CZ-R1"),
            ("帮我算一道数学题，顺便提到设备", "out_of_scope_blocked", "CZ-R1"),
            ("冒烟", "safety_risk", "CZ-R1"),
            (
                "R1刚吸进一小滩水，我想继续开机把剩下的吸完。",
                "safety_risk",
                "CZ-R1",
            ),
            (
                "CZ-R1 的基站集尘袋满了，应该怎么更换？",
                "model_scope_conflict",
                "CZ-R1",
            ),
            (
                "CZ-R1 的基站集尘袋满了，应该怎么更换？",
                "model_scope_conflict",
                "CZ-R2",
            ),
            (
                "CZ-R1 和 CZ-R2 的集尘袋都满了，应该怎么更换？",
                "model_scope_conflict",
                "CZ-R2",
            ),
        ]
        token = None
        for text, reason, model in cases:
            submission = service.submit(
                _payload(text, product_model=model), browser_token=token
            )
            token = submission.browser_token
            value = service.get_run(submission.run_id)
            self.assertEqual(value["status"], "handoff")
            self.assertEqual(value["result"]["handoff_reason"], reason)
            self.assertEqual(value["result"]["provider_call_count"], 0)
        self.assertEqual(calls, 0)
        with closing(sqlite3.connect(self.database)) as connection:
            rows = connection.execute(
                "SELECT input_text,input_sha256 FROM runs ORDER BY created_at"
            ).fetchall()
        self.assertEqual(len(rows), len(cases))
        self.assertTrue(all(row[0] is None for row in rows))
        self.assertNotIn("13800138000", self.database.read_bytes().decode("latin1"))

    def test_preflight_allows_explicit_model_capability_questions_to_runner(self) -> None:
        calls = 0

        def runner(_row: dict[str, object], _stage: object) -> tuple[dict[str, object], int]:
            nonlocal calls
            calls += 1
            return _candidate_package(), 2

        service = self._service(live_enabled=True, product_runner=_product_runner(runner))
        token = None
        for text in (
            "CZ-R1 是否支持开启自动集尘功能？",
            "CZ-R1 自动集尘可以设置吗？",
        ):
            submission = service.submit(
                _payload(text, product_model="CZ-R1"), browser_token=token
            )
            token = submission.browser_token
            value = _wait_for_terminal(service, submission.run_id)
            self.assertEqual(value["status"], "completed")
            self.assertEqual(value["result"]["provider_call_count"], 2)
        self.assertEqual(calls, 2)

    def test_same_database_rejects_a_second_process_owner(self) -> None:
        self._service(live_enabled=False)
        with self.assertRaisesRegex(RuntimeError, "single_instance"):
            PublicRunService(
                self.database,
                allowed_origin=ORIGIN,
                live_enabled=False,
                start_cleanup_thread=False,
            )

    def test_worker_submission_failure_becomes_pollable_handoff(self) -> None:
        service = self._service(
            live_enabled=True,
            product_runner=_product_runner(lambda row, stage: (_candidate_package(), 2)),
        )
        service._executor.shutdown(wait=True)
        submission = service.submit(_payload(), browser_token=None)
        value = service.get_run(submission.run_id)
        self.assertEqual(value["status"], "handoff")
        self.assertEqual(value["result"]["provider_call_count"], None)
        self.assertEqual(submission.estimated_wait_seconds, 0)

    def test_candidate_projection_and_single_human_decision(self) -> None:
        def runner(row: dict[str, object], stage: object) -> tuple[dict[str, object], int]:
            stage("retrieval", "started")
            stage("enumeration", "started")
            stage("generation", "started")
            stage("gate", "finished")
            return _candidate_package(str(row["task_type"])), 2

        service = self._service(live_enabled=True, product_runner=_product_runner(runner))
        submission = service.submit(_payload(), browser_token=None)
        value = _wait_for_terminal(service, submission.run_id)
        self.assertEqual(value["status"], "completed")
        self.assertEqual(value["result"]["mode"], "live")
        self.assertEqual(value["result"]["provider_call_count"], 2)
        self.assertEqual([item["id"] for item in value["result"]["evidence"]], ["E1"])
        self.assertEqual(
            service.decide(submission.run_id, {"decision": "approve"}),
            {"status": "recorded", "decision": "approve"},
        )
        with self.assertRaises(PublicApiError) as repeated:
            service.decide(submission.run_id, {"decision": "reject"})
        self.assertEqual(repeated.exception.status_code, 409)

    def test_ticket_public_adapter_uses_valid_classifier_input(self) -> None:
        service = self._service(
            live_enabled=True,
            product_runner=_product_runner(
                lambda row, stage: (_candidate_package("ticket"), 2)
            ),
        )
        submission = service.submit(
            _payload("CZ-R1 轮组卡住后无法继续清扫，请生成工单建议", task_type="ticket"),
            browser_token=None,
        )
        value = _wait_for_terminal(service, submission.run_id)
        self.assertEqual(value["status"], "completed")
        self.assertIn("actionSteps", value["result"])
        with self.assertRaises(PublicApiError) as short:
            service.submit(_payload("设备故障", task_type="ticket"), browser_token=None)
        self.assertEqual(short.exception.code, "ticket_text_too_short")

    def test_browser_and_budget_limits_fail_before_provider_submission(self) -> None:
        service = self._service(
            live_enabled=True,
            product_runner=_product_runner(lambda row, stage: (_candidate_package(), 2)),
            browser_daily_limit=2,
            daily_limit_cny_nanos=10_000_000_000,
            monthly_limit_cny_nanos=10_000_000_000,
        )
        first = service.submit(_payload(), browser_token=None)
        second = service.submit(_payload(), browser_token=first.browser_token)
        _wait_for_terminal(service, first.run_id)
        _wait_for_terminal(service, second.run_id)
        with self.assertRaises(PublicApiError) as browser_limit:
            service.submit(_payload(), browser_token=first.browser_token)
        self.assertEqual(browser_limit.exception.status_code, 429)

        other_database = Path(self.temporary.name) / "budget.sqlite3"
        budget_service = PublicRunService(
            other_database,
            allowed_origin=ORIGIN,
            live_enabled=True,
            product_runner=_product_runner(lambda row, stage: (_candidate_package(), 2)),
            run_reservation_cny_nanos=1_000_000_000,
            daily_limit_cny_nanos=2_000_000_000,
            monthly_limit_cny_nanos=9_000_000_000,
            start_cleanup_thread=False,
        )
        self.services.append(budget_service)
        budget_service.submit(_payload(), browser_token="A" * 24)
        budget_service.submit(_payload(), browser_token="B" * 24)
        with self.assertRaises(PublicApiError) as daily_limit:
            budget_service.submit(_payload(), browser_token="C" * 24)
        self.assertEqual(daily_limit.exception.code, "daily_budget_exhausted")
        with closing(sqlite3.connect(other_database)) as connection:
            month_reserved = connection.execute(
                "SELECT reserved_cny_nanos FROM budget_counters WHERE period_kind='month'"
            ).fetchone()[0]
        self.assertEqual(month_reserved, 2_000_000_000)

    def test_two_running_four_queued_then_queue_rejects(self) -> None:
        release = threading.Event()

        def runner(_row: dict[str, object], stage: object) -> tuple[dict[str, object], int]:
            stage("retrieval", "started")
            release.wait(2)
            return _candidate_package(), 2

        service = self._service(live_enabled=True, product_runner=_product_runner(runner))
        submissions = [
            service.submit(_payload(), browser_token=f"token-{index:020d}")
            for index in range(6)
        ]
        with self.assertRaises(PublicApiError) as full:
            service.submit(_payload(), browser_token="token-99999999999999999999")
        self.assertEqual(full.exception.code, "run_queue_full")
        self.assertEqual(full.exception.retry_after_seconds, 120)
        release.set()
        for submission in submissions:
            self.assertEqual(_wait_for_terminal(service, submission.run_id)["status"], "completed")

    def test_restart_never_retries_nonterminal_rows(self) -> None:
        first = self._service(live_enabled=False)
        now = datetime.now(timezone.utc).isoformat()
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute(
                "INSERT INTO runs(run_id,task_type,input_mode,input_text,input_sha256,product_model,browser_hash,created_at,updated_at,status,reserved_cny_nanos) VALUES(?,?,?,?,?,?,?,?,?,'generating',?)",
                (
                    "R" * 24,
                    "qa",
                    "preset",
                    "CZ-R1 正在清扫",
                    "hash",
                    "CZ-R1",
                    "browser",
                    now,
                    now,
                    1_000_000_000,
                ),
            )
            connection.commit()
        first.shutdown(wait=True)
        self.services.remove(first)
        restarted = self._service(live_enabled=False)
        value = restarted.get_run("R" * 24)
        self.assertEqual(value["status"], "handoff")
        self.assertEqual(value["result"]["handoff_reason"], "service_restarted_no_retry")

    def test_legacy_nonnull_provider_calls_is_migrated_before_restart_handoff(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute(
                """
                CREATE TABLE runs (
                    run_id TEXT PRIMARY KEY, task_type TEXT NOT NULL,
                    input_mode TEXT NOT NULL, input_text TEXT,
                    input_sha256 TEXT NOT NULL, product_model TEXT NOT NULL,
                    browser_hash TEXT NOT NULL, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, status TEXT NOT NULL,
                    result_json TEXT, error_code TEXT, decision TEXT,
                    decision_text TEXT, decided_at TEXT,
                    reserved_cny_nanos INTEGER NOT NULL,
                    provider_calls INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            connection.execute(
                "INSERT INTO runs(run_id,task_type,input_mode,input_text,input_sha256,product_model,browser_hash,created_at,updated_at,status,reserved_cny_nanos) VALUES(?,?,?,?,?,?,?,?,?,'queued',?)",
                (
                    "L" * 24,
                    "qa",
                    "preset",
                    "CZ-R1 如何回充",
                    "hash",
                    "CZ-R1",
                    "browser",
                    now,
                    now,
                    1_000_000_000,
                ),
            )
            connection.commit()

        service = self._service(live_enabled=False)

        value = service.get_run("L" * 24)
        self.assertEqual(value["status"], "handoff")
        self.assertIsNone(value["result"]["provider_call_count"])
        with closing(sqlite3.connect(self.database)) as connection:
            column = next(
                row
                for row in connection.execute("PRAGMA table_info(runs)")
                if row[1] == "provider_calls"
            )
            self.assertEqual(column[3], 0)
            self.assertIsNone(
                connection.execute(
                    "SELECT provider_calls FROM runs WHERE run_id=?", ("L" * 24,)
                ).fetchone()[0]
            )

    def test_cleanup_removes_expired_raw_content_and_keeps_aggregate(self) -> None:
        clock = _Clock()
        marker = "CZ-R1 清扫记录-RAW-RETENTION-MARKER"
        service = self._service(
            live_enabled=True,
            product_runner=_product_runner(lambda row, stage: (_candidate_package(), 2)),
            now=clock,
        )
        submission = service.submit(_payload(marker), browser_token=None)
        _wait_for_terminal(service, submission.run_id)
        with closing(sqlite3.connect(self.database)) as connection:
            self.assertEqual(
                connection.execute("SELECT input_text FROM runs").fetchone()[0], marker
            )
        clock.value += timedelta(days=31)
        receipt = service.cleanup_expired()
        self.assertEqual(receipt["removed_runs"], 1)
        with closing(sqlite3.connect(self.database)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0], 0)
            self.assertEqual(
                connection.execute("SELECT SUM(run_count) FROM metric_rollups").fetchone()[0],
                1,
            )
        self.assertNotIn(marker.encode("utf-8"), self.database.read_bytes())
        wal = Path(str(self.database) + "-wal")
        if wal.exists():
            self.assertNotIn(marker.encode("utf-8"), wal.read_bytes())


class PublicApiHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.service = PublicRunService(
            Path(self.temporary.name) / "http.sqlite3",
            allowed_origin=ORIGIN,
            live_enabled=True,
            product_runner=_product_runner(lambda row, stage: (_candidate_package(), 2)),
            start_cleanup_thread=False,
        )
        self.server = create_server(host="127.0.0.1", port=0, service=self.service)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.service.shutdown(wait=True)
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], dict[str, object]]:
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        raw = response.read()
        values = {key.lower(): value for key, value in response.getheaders()}
        connection.close()
        parsed = {} if not raw else json.loads(raw)
        return response.status, values, parsed

    def test_health_create_poll_and_decision_contract(self) -> None:
        status, headers, health = self._request("GET", "/api/v1/health")
        self.assertEqual(status, 200)
        self.assertEqual(
            health,
            {
                "status": "ok",
                "service": "traceable-support-public-api",
                "live_experience": "available",
            },
        )
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertNotIn("config", health)

        raw = json.dumps(_payload(), ensure_ascii=False).encode("utf-8")
        status, _, denied = self._request(
            "POST",
            "/api/v1/runs",
            body=raw,
            headers={"Content-Type": "application/json", "Content-Length": str(len(raw))},
        )
        self.assertEqual(status, 403)
        self.assertEqual(denied["error"]["code"], "origin_not_allowed")

        status, headers, created = self._request(
            "POST",
            "/api/v1/runs",
            body=raw,
            headers={
                "Origin": ORIGIN,
                "Content-Type": "application/json",
                "Content-Length": str(len(raw)),
            },
        )
        self.assertEqual(status, 202)
        self.assertIn("__Host-traceable-browser=", headers["set-cookie"])
        self.assertIn("Secure", headers["set-cookie"])
        run_id = str(created["run_id"])
        deadline = time.monotonic() + 3
        while True:
            status, _, current = self._request("GET", f"/api/v1/runs/{run_id}")
            self.assertEqual(status, 200)
            if current["status"] in {"completed", "handoff"}:
                break
            if time.monotonic() >= deadline:
                self.fail("HTTP run did not finish")
            time.sleep(0.01)
        self.assertEqual(current["status"], "completed")

        decision = json.dumps({"decision": "reject"}).encode("utf-8")
        status, _, recorded = self._request(
            "POST",
            f"/api/v1/runs/{run_id}/decision",
            body=decision,
            headers={
                "Origin": ORIGIN,
                "Content-Type": "application/json",
                "Content-Length": str(len(decision)),
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(recorded, {"status": "recorded", "decision": "reject"})

    def test_strict_json_and_method_boundary(self) -> None:
        duplicate = b'{"decision":"approve","decision":"reject"}'
        status, _, value = self._request(
            "POST",
            "/api/v1/runs/" + "R" * 24 + "/decision",
            body=duplicate,
            headers={
                "Origin": ORIGIN,
                "Content-Type": "application/json",
                "Content-Length": str(len(duplicate)),
            },
        )
        self.assertEqual(status, 400)
        self.assertEqual(value["error"]["code"], "json_invalid")
        status, headers, _ = self._request("DELETE", "/api/v1/health")
        self.assertEqual(status, 405)
        self.assertEqual(headers["allow"], "GET, HEAD, POST, OPTIONS")


if __name__ == "__main__":
    unittest.main()

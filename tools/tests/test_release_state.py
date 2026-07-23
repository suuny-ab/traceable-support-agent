from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deploy.install_release import (
    _TransientPublicSmokeError,
    _commit_receipt_or_restore,
    _public_smoke,
    _rehearsal_anchor,
    _required_sha,
    _run as _install_run,
    _stable_error_code,
    _validated_input,
    _wait_public_smoke,
)
from deploy.switch_release_state import switch_release_state


@unittest.skipIf(os.name == "nt", "release shell tests run on the Linux CI runner")
class ReleaseShellTest(unittest.TestCase):
    def _run_release_lib(self, body: str) -> subprocess.CompletedProcess[str]:
        release_lib = Path(__file__).resolve().parents[2] / "deploy" / "release-lib.sh"
        script = f"source {shlex.quote(str(release_lib))}\n{body}"
        return subprocess.run(
            ("bash", "-c", script),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_project_stop_barrier_accepts_absent_resources(self) -> None:
        completed = self._run_release_lib(
            "docker() { :; }\n"
            "sleep() { :; }\n"
            "release_wait_project_stopped\n"
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_project_stop_barrier_fails_closed_with_stable_code(self) -> None:
        completed = self._run_release_lib(
            "docker() { printf '%s\\n' busy; }\n"
            "sleep() { :; }\n"
            "release_wait_project_stopped\n"
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("release_stop_not_settled", completed.stderr)

    def test_project_stop_barrier_fails_closed_when_docker_query_fails(self) -> None:
        completed = self._run_release_lib(
            "docker() { return 1; }\n"
            "sleep() { :; }\n"
            "if release_wait_project_stopped; then\n"
            "  printf '%s\\n' false_success\n"
            "  exit 0\n"
            "fi\n"
            "exit 23\n"
        )
        self.assertEqual(completed.returncode, 23)
        self.assertNotIn("false_success", completed.stdout)
        self.assertIn("release_stop_state_query_failed", completed.stderr)


class ReleaseStateTransactionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "traceable-support"
        self.releases = self.root / "releases"
        self.old = self.releases / "old"
        self.new = self.releases / "new"
        self.old.mkdir(parents=True)
        self.new.mkdir()
        for release, value in ((self.old, b"OLD=1\n"), (self.new, b"NEW=1\n")):
            environment = release / "release.env"
            environment.write_bytes(value)
            environment.chmod(0o600)
        try:
            (self.root / "current").symlink_to(self.old, target_is_directory=True)
        except OSError as error:
            if os.name == "nt" and getattr(error, "winerror", None) == 1314:
                self.skipTest("Windows symlink privilege is unavailable; Linux CI runs this test")
            raise
        (self.root / "server.env").write_bytes((self.old / "release.env").read_bytes())
        (self.root / "server.env").chmod(0o600)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _assert_old_state(self) -> None:
        self.assertEqual((self.root / "current").resolve(), self.old.resolve())
        self.assertFalse((self.root / "previous").exists())
        self.assertEqual((self.root / "server.env").read_bytes(), b"OLD=1\n")

    def test_success_commits_all_three_paths(self) -> None:
        switch_release_state(
            release_root=self.root,
            current_release=self.new,
            previous_release=self.old,
            server_environment=self.new / "release.env",
        )
        self.assertEqual((self.root / "current").resolve(), self.new.resolve())
        self.assertEqual((self.root / "previous").resolve(), self.old.resolve())
        self.assertEqual((self.root / "server.env").read_bytes(), b"NEW=1\n")

    def test_each_partial_commit_is_compensated(self) -> None:
        for failure_at in ("previous", "server.env", "current"):
            with self.subTest(failure_at=failure_at):
                calls: list[str] = []

                def fail_once(name: str) -> None:
                    calls.append(name)
                    if name == failure_at:
                        raise OSError("injected metadata failure")

                with self.assertRaisesRegex(RuntimeError, "release_state_commit_failed"):
                    switch_release_state(
                        release_root=self.root,
                        current_release=self.new,
                        previous_release=self.old,
                        server_environment=self.new / "release.env",
                        before_replace=fail_once,
                    )
                self.assertIn(failure_at, calls)
                self._assert_old_state()

    def test_rollback_partial_commit_restores_canonical_metadata(self) -> None:
        switch_release_state(
            release_root=self.root,
            current_release=self.new,
            previous_release=self.old,
            server_environment=self.new / "release.env",
        )

        def fail_current(name: str) -> None:
            if name == "current":
                raise OSError("injected rollback metadata failure")

        with self.assertRaisesRegex(RuntimeError, "release_state_commit_failed"):
            switch_release_state(
                release_root=self.root,
                current_release=self.old,
                previous_release=self.new,
                server_environment=self.old / "release.env",
                before_replace=fail_current,
            )
        self.assertEqual((self.root / "current").resolve(), self.new.resolve())
        self.assertEqual((self.root / "previous").resolve(), self.old.resolve())
        self.assertEqual((self.root / "server.env").read_bytes(), b"NEW=1\n")


class DeploymentInputTest(unittest.TestCase):
    def test_public_smoke_wait_retries_transient_proxy_failure(self) -> None:
        clock = [0.0]
        calls: list[float] = []

        def smoke(
            _origin: str,
            *,
            deadline: float,
            monotonic: object,
        ) -> None:
            calls.append(deadline)
            if len(calls) == 1:
                raise _TransientPublicSmokeError("proxy not ready")

        _wait_public_smoke(
            "https://example.invalid",
            smoke=smoke,
            monotonic=lambda: clock[0],
            sleeper=lambda delay: clock.__setitem__(0, clock[0] + delay),
        )
        self.assertEqual(len(calls), 2)
        self.assertEqual(clock[0], 1.0)

    def test_public_smoke_wait_fails_immediately_for_contract_error(self) -> None:
        calls: list[bool] = []

        def smoke(_origin: str, **_kwargs: object) -> None:
            calls.append(True)
            raise RuntimeError("public_smoke_contract_failed")

        with self.assertRaisesRegex(RuntimeError, "^public_smoke_contract_failed$"):
            _wait_public_smoke(
                "https://example.invalid",
                smoke=smoke,
                monotonic=lambda: 0.0,
                sleeper=lambda _delay: self.fail("contract failure must not retry"),
            )
        self.assertEqual(calls, [True])

    def test_public_smoke_wait_fails_closed_at_deadline(self) -> None:
        clock = [0.0]
        calls: list[bool] = []

        def smoke(_origin: str, **_kwargs: object) -> None:
            calls.append(True)
            raise _TransientPublicSmokeError("timed out")

        with self.assertRaisesRegex(RuntimeError, "^public_smoke_not_ready$"):
            _wait_public_smoke(
                "https://example.invalid",
                timeout_seconds=3.0,
                retry_delay_seconds=1.0,
                smoke=smoke,
                monotonic=lambda: clock[0],
                sleeper=lambda delay: clock.__setitem__(0, clock[0] + delay),
            )
        self.assertEqual(clock[0], 3.0)
        self.assertEqual(len(calls), 4)

    def test_public_smoke_wait_does_not_retry_permanent_tls_failure(self) -> None:
        def smoke(_origin: str, **_kwargs: object) -> None:
            raise RuntimeError("public_smoke_contract_failed")

        with self.assertRaisesRegex(RuntimeError, "^public_smoke_contract_failed$"):
            _wait_public_smoke(
                "https://example.invalid",
                smoke=smoke,
                monotonic=lambda: 0.0,
                sleeper=lambda _delay: self.fail("certificate failure must not retry"),
            )

    def test_public_smoke_wait_rejects_success_after_deadline(self) -> None:
        clock = [0.0]

        def smoke(_origin: str, **_kwargs: object) -> None:
            clock[0] = 16.0

        with self.assertRaisesRegex(RuntimeError, "^public_smoke_not_ready$"):
            _wait_public_smoke(
                "https://example.invalid",
                timeout_seconds=15.0,
                smoke=smoke,
                monotonic=lambda: clock[0],
                sleeper=lambda _delay: self.fail("late success must not retry"),
            )

    def test_public_smoke_curl_timeout_covers_slow_response_body(self) -> None:
        clock = [0.0]

        def runner(
            command: list[str],
            **kwargs: object,
        ) -> subprocess.CompletedProcess[bytes]:
            clock[0] = 15.0
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])

        with self.assertRaises(_TransientPublicSmokeError):
            _public_smoke(
                "https://example.invalid",
                deadline=15.0,
                monotonic=lambda: clock[0],
                runner=runner,
            )

    def test_public_smoke_curl_classifies_proxy_and_contract_failures(self) -> None:
        def completed(
            status: int,
            *,
            returncode: int = 0,
        ) -> object:
            def runner(
                command: list[str],
                **_kwargs: object,
            ) -> subprocess.CompletedProcess[bytes]:
                return subprocess.CompletedProcess(
                    command,
                    returncode,
                    stdout=str(status).encode("ascii"),
                    stderr=b"hidden detail",
                )

            return runner

        with self.assertRaises(_TransientPublicSmokeError):
            _public_smoke(
                "https://example.invalid",
                deadline=15.0,
                monotonic=lambda: 0.0,
                runner=completed(502),
            )
        with self.assertRaisesRegex(RuntimeError, "^public_smoke_contract_failed$"):
            _public_smoke(
                "https://example.invalid",
                deadline=15.0,
                monotonic=lambda: 0.0,
                runner=completed(404),
            )
        with self.assertRaisesRegex(RuntimeError, "^public_smoke_contract_failed$"):
            _public_smoke(
                "https://example.invalid",
                deadline=15.0,
                monotonic=lambda: 0.0,
                runner=completed(0, returncode=60),
            )

    def test_remote_failures_are_reduced_to_stable_codes(self) -> None:
        self.assertEqual(
            _stable_error_code(RuntimeError("rollback_rehearsal_anchor_missing")),
            "rollback_rehearsal_anchor_missing",
        )
        self.assertEqual(
            _stable_error_code(PermissionError("private path")),
            "filesystem_permission_denied",
        )
        self.assertEqual(
            _stable_error_code(RuntimeError("unsafe detail /opt/private")),
            "unexpected_failure",
        )

    def test_installer_preserves_only_stable_child_error(self) -> None:
        completed = subprocess.CompletedProcess(
            args=("python3",),
            returncode=70,
            stdout="",
            stderr=(
                "private detail omitted\n"
                "previous_release_start_failed\n"
            ),
        )
        with mock.patch(
            "deploy.install_release.subprocess.run",
            return_value=completed,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "^previous_release_start_failed$",
            ):
                _install_run("bash", "rollback")

    def test_rehearsal_and_existing_anchor_are_mandatory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            staging = Path(temporary) / "staging"
            root = Path(temporary) / "root"
            release = root / "releases" / "new"
            staging.mkdir()
            release.mkdir(parents=True)
            (staging / "deployment-input.json").write_text(
                '{"public_origin":"https://47.84.34.86","rehearse_rollback":false,'
                '"schema_version":"traceable-production-target-v1"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "deployment_rehearsal_required"):
                _validated_input(staging)
            with self.assertRaisesRegex(RuntimeError, "rollback_rehearsal_anchor_missing"):
                _rehearsal_anchor(root, release)

    def test_receipt_inputs_are_required_before_activation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(RuntimeError, "required_receipt_input_missing"):
                _required_sha(Path(temporary) / "missing-caddyfile")

    def test_receipt_commit_failure_invokes_restore(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            restored: list[bool] = []

            def fail_replace(_source: Path, _target: Path) -> None:
                raise OSError("injected receipt replace failure")

            with self.assertRaisesRegex(OSError, "injected receipt replace failure"):
                _commit_receipt_or_restore(
                    Path(temporary) / "deployment-receipt.json",
                    {"provider_enabled": False},
                    lambda: restored.append(True),
                    replace=fail_replace,
                )
            self.assertEqual(restored, [True])
            self.assertFalse((Path(temporary) / "deployment-receipt.json").exists())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from deploy.install_release import (
    _commit_receipt_or_restore,
    _rehearsal_anchor,
    _required_sha,
    _validated_input,
)
from deploy.switch_release_state import switch_release_state


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

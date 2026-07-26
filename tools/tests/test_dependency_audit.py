from __future__ import annotations

from pathlib import Path
import unittest
from unittest import mock

from tools.dependency_audit import API_LOCKS, Scan, build_scans, main, run_scans


class BuildScansTest(unittest.TestCase):
    def test_npm_scan_targets_web_with_high_threshold(self) -> None:
        with mock.patch("shutil.which", side_effect=lambda tool: f"/bin/{tool}"):
            scans = build_scans(Path("/repo"))
        npm_scan = scans[0]
        self.assertEqual(npm_scan.name, "web.npm-audit")
        self.assertEqual(npm_scan.cwd, Path("/repo/web"))
        self.assertIn("--audit-level=high", npm_scan.command)
        self.assertEqual(len(scans), 1 + len(API_LOCKS))

    def test_missing_tools_become_skips_not_failures(self) -> None:
        with mock.patch("shutil.which", return_value=None):
            scans = build_scans(Path("/repo"))
        self.assertTrue(all(scan.command is None for scan in scans))
        self.assertEqual(run_scans(scans), 0)

    def test_failed_scan_fails_run(self) -> None:
        scans = [
            Scan("a", ("/bin/false",), Path("/repo")),
            Scan("b", ("/bin/true",), Path("/repo")),
        ]
        with mock.patch("subprocess.run") as run:
            run.side_effect = [
                mock.Mock(returncode=1),
                mock.Mock(returncode=0),
            ]
            self.assertEqual(run_scans(scans), 1)


class MainTest(unittest.TestCase):
    def test_invalid_root_rejected(self) -> None:
        self.assertEqual(main(["--root", "/nonexistent-traceable-root"]), 2)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.ci_impact import (
    UNKNOWN_PATH,
    changed_paths_sha256,
    classify_paths,
    normalize_paths,
)
from tools.release_decision import (
    SCHEMA_VERSION,
    build_decision,
    load_decision,
    verify_decision,
)


class CiImpactTest(unittest.TestCase):
    def test_clear_governance_paths_are_governance_only(self) -> None:
        paths = (
            "AGENTS.md",
            "ROADMAP.md",
            "docs/status.md",
            "docs/meta/evolution-log.md",
            "docs/work/completed/example/result.md",
            "docs/engineering/review.md",
            ".github/ISSUE_TEMPLATE/meta.yml",
            ".github/pull_request_template.md",
        )
        self.assertEqual(classify_paths(paths), "governance_only")

    def test_runtime_and_unknown_paths_fail_closed(self) -> None:
        runtime_paths = (
            "PROJECT.md",
            "README.md",
            "docs/product/public-api.md",
            "docs/engineering/operations.md",
            ".github/workflows/ci-release.yml",
            "tools/ci_impact.py",
            "web/app/page.tsx",
            "api/src/traceable_support/api/runs.py",
            "deploy/install_release.py",
            "unknown/new-file.txt",
        )
        for path in runtime_paths:
            with self.subTest(path=path):
                self.assertEqual(classify_paths((path,)), "runtime")
        self.assertEqual(classify_paths(()), "runtime")
        self.assertEqual(classify_paths((UNKNOWN_PATH,)), "runtime")
        self.assertEqual(classify_paths(("../escape.md",)), "runtime")

    def test_mixed_change_is_runtime_and_hash_is_canonical(self) -> None:
        self.assertEqual(
            classify_paths(("docs/meta/a.md", "web/app/page.tsx")),
            "runtime",
        )
        self.assertEqual(
            changed_paths_sha256(("docs/meta/b.md", "docs/meta/a.md")),
            changed_paths_sha256(("docs/meta/a.md", "docs/meta/b.md")),
        )
        self.assertEqual(
            normalize_paths(("docs\\meta\\a.md", "docs/meta/a.md")),
            ("docs/meta/a.md",),
        )


class ReleaseDecisionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.values = {
            "git_sha": "a" * 40,
            "github_run_id": "123",
            "github_run_attempt": "1",
            "classification": "runtime",
            "deploy_required": True,
            "changed_paths_sha256": "b" * 64,
        }

    def test_round_trip_and_identity_binding(self) -> None:
        decision = build_decision(**self.values)
        self.assertEqual(decision["schema_version"], SCHEMA_VERSION)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "decision.json")
            path.write_text(json.dumps(decision), encoding="utf-8")
            loaded = load_decision(path)
        self.assertEqual(loaded, decision)
        self.assertEqual(
            verify_decision(
                loaded,
                git_sha="a" * 40,
                github_run_id="123",
                github_run_attempt="1",
            ),
            decision,
        )

    def test_governance_decision_cannot_deploy(self) -> None:
        values = dict(self.values)
        values["classification"] = "governance_only"
        with self.assertRaisesRegex(ValueError, "governance_must_not_deploy"):
            build_decision(**values)

    def test_unknown_fields_and_identity_mismatch_fail(self) -> None:
        decision = build_decision(**self.values)
        decision["extra"] = "no"
        with self.assertRaisesRegex(ValueError, "fields_invalid"):
            verify_decision(decision)
        clean = build_decision(**self.values)
        with self.assertRaisesRegex(ValueError, "git_sha_mismatch"):
            verify_decision(clean, git_sha="c" * 40)


if __name__ == "__main__":
    unittest.main()

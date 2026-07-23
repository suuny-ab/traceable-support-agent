from __future__ import annotations

import unittest

from tools.release_run import (
    LEGACY_RUN_IDS,
    validate_release_selection,
)


REPOSITORY = "suuny-ab/traceable-support-agent"
RUN_ID = next(iter(LEGACY_RUN_IDS))


def release_run(run_id: str = RUN_ID) -> dict[str, object]:
    return {
        "id": int(run_id),
        "name": "ci-release",
        "path": ".github/workflows/ci-release.yml",
        "event": "push",
        "head_branch": "main",
        "status": "completed",
        "conclusion": "success",
        "repository": {"full_name": REPOSITORY},
        "head_repository": {"full_name": REPOSITORY},
        "head_sha": "a" * 40,
        "run_attempt": 1,
    }


def release_artifacts(*names: str) -> dict[str, object]:
    return {
        "artifacts": [
            {"id": index, "name": name, "expired": False}
            for index, name in enumerate(names, start=1)
        ]
    }


class ReleaseRunTest(unittest.TestCase):
    def test_current_decision_run_is_bound_to_green_main_push(self) -> None:
        result = validate_release_selection(
            release_run("30000000000"),
            release_artifacts("release-decision", "release-manifest"),
            repository=REPOSITORY,
            run_id="30000000000",
            manual=True,
            expected_git_sha="a" * 40,
            expected_run_attempt="1",
        )
        self.assertEqual(result["release_decision_artifact_id"], "1")
        self.assertEqual(result["release_manifest_artifact_id"], "2")
        self.assertEqual(result["legacy_decision"], "false")

    def test_only_fixed_legacy_run_with_manifest_is_accepted(self) -> None:
        result = validate_release_selection(
            release_run(),
            release_artifacts("release-manifest"),
            repository=REPOSITORY,
            run_id=RUN_ID,
            manual=True,
        )
        self.assertEqual(result["classification"], "runtime")
        self.assertEqual(result["deploy_required"], "true")
        self.assertEqual(result["legacy_decision"], "true")

        with self.assertRaisesRegex(ValueError, "not_allowlisted"):
            validate_release_selection(
                release_run("29999870812"),
                release_artifacts("release-manifest"),
                repository=REPOSITORY,
                run_id="29999870812",
                manual=True,
            )
        with self.assertRaisesRegex(ValueError, "manifest_missing"):
            validate_release_selection(
                release_run(),
                release_artifacts(),
                repository=REPOSITORY,
                run_id=RUN_ID,
                manual=True,
            )

    def test_automatic_missing_decision_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "release_decision_missing"):
            validate_release_selection(
                release_run(),
                release_artifacts("release-manifest"),
                repository=REPOSITORY,
                run_id=RUN_ID,
                manual=False,
            )

    def test_untrusted_run_identity_and_ambiguous_artifacts_are_rejected(self) -> None:
        mutations = {
            "name": "other",
            "path": ".github/workflows/not-ci-release.yml",
            "event": "pull_request",
            "head_branch": "feature",
            "status": "in_progress",
            "conclusion": "failure",
            "head_repository": {"full_name": "other/repository"},
        }
        for field, value in mutations.items():
            run = release_run()
            run[field] = value
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    validate_release_selection(
                        run,
                        release_artifacts("release-manifest"),
                        repository=REPOSITORY,
                        run_id=RUN_ID,
                        manual=True,
                    )
        with self.assertRaisesRegex(ValueError, "artifact_ambiguous"):
            validate_release_selection(
                release_run("30000000000"),
                [
                    release_artifacts("release-decision"),
                    release_artifacts("release-decision"),
                ],
                repository=REPOSITORY,
                run_id="30000000000",
                manual=True,
            )


if __name__ == "__main__":
    unittest.main()

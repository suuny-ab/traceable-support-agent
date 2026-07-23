from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys


LEGACY_RUN_IDS = frozenset({"29999870811"})


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("release_run_metadata_unreadable") from exc


def validate_release_run(
    run: object,
    *,
    repository: str,
    run_id: str,
    expected_git_sha: str | None = None,
    expected_run_attempt: str | None = None,
) -> dict[str, str]:
    if not isinstance(run, dict):
        raise ValueError("release_run_metadata_invalid")
    repository_data = run.get("repository")
    head_repository = run.get("head_repository")
    values = {
        "id": str(run.get("id", "")),
        "name": run.get("name"),
        "event": run.get("event"),
        "head_branch": run.get("head_branch"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "repository": (
            repository_data.get("full_name")
            if isinstance(repository_data, dict)
            else None
        ),
        "head_repository": (
            head_repository.get("full_name")
            if isinstance(head_repository, dict)
            else None
        ),
        "git_sha": str(run.get("head_sha", "")),
        "run_attempt": str(run.get("run_attempt", "")),
    }
    expected = {
        "id": run_id,
        "name": "ci-release",
        "event": "push",
        "head_branch": "main",
        "status": "completed",
        "conclusion": "success",
        "repository": repository,
        "head_repository": repository,
    }
    for field, value in expected.items():
        if values[field] != value:
            raise ValueError(f"release_run_{field}_invalid")
    if not re.fullmatch(r"[0-9a-f]{40}", values["git_sha"]):
        raise ValueError("release_run_git_sha_invalid")
    if not re.fullmatch(r"[1-9][0-9]*", values["run_attempt"]):
        raise ValueError("release_run_attempt_invalid")
    if expected_git_sha is not None and values["git_sha"] != expected_git_sha:
        raise ValueError("release_run_git_sha_mismatch")
    if (
        expected_run_attempt is not None
        and values["run_attempt"] != expected_run_attempt
    ):
        raise ValueError("release_run_attempt_mismatch")
    return {
        "git_sha": values["git_sha"],
        "run_attempt": values["run_attempt"],
    }


def select_release_artifacts(artifacts: object) -> dict[str, str]:
    pages = artifacts if isinstance(artifacts, list) else [artifacts]
    if not pages or any(
        not isinstance(page, dict)
        or not isinstance(page.get("artifacts"), list)
        for page in pages
    ):
        raise ValueError("release_artifacts_metadata_invalid")
    artifact_items = [
        item
        for page in pages
        for item in page["artifacts"]
    ]
    selected: dict[str, str] = {}
    for name in ("release-decision", "release-manifest"):
        matches = [
            item
            for item in artifact_items
            if isinstance(item, dict)
            and item.get("name") == name
            and item.get("expired") is False
        ]
        if len(matches) > 1:
            raise ValueError(f"{name.replace('-', '_')}_artifact_ambiguous")
        artifact_id = "" if not matches else str(matches[0].get("id", ""))
        if artifact_id and not re.fullmatch(r"[1-9][0-9]*", artifact_id):
            raise ValueError(f"{name.replace('-', '_')}_artifact_id_invalid")
        selected[name.replace("-", "_") + "_artifact_id"] = artifact_id
    return selected


def validate_release_selection(
    run: object,
    artifacts: object,
    *,
    repository: str,
    run_id: str,
    manual: bool,
    expected_git_sha: str | None = None,
    expected_run_attempt: str | None = None,
) -> dict[str, str]:
    values = validate_release_run(
        run,
        repository=repository,
        run_id=run_id,
        expected_git_sha=expected_git_sha,
        expected_run_attempt=expected_run_attempt,
    )
    values.update(select_release_artifacts(artifacts))
    if not values["release_decision_artifact_id"]:
        if not manual:
            raise ValueError("release_decision_missing")
        if run_id not in LEGACY_RUN_IDS:
            raise ValueError("legacy_release_run_not_allowlisted")
        if not values["release_manifest_artifact_id"]:
            raise ValueError("legacy_release_manifest_missing")
        values.update(
            {
                "classification": "runtime",
                "deploy_required": "true",
                "legacy_decision": "true",
            }
        )
    else:
        values["legacy_decision"] = "false"
    return values


def write_github_output(path: Path, values: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--manual", action="store_true")
    parser.add_argument("--expected-git-sha")
    parser.add_argument("--expected-run-attempt")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    try:
        values = validate_release_selection(
            _load_json(args.run),
            _load_json(args.artifacts),
            repository=args.repository,
            run_id=args.run_id,
            manual=args.manual,
            expected_git_sha=args.expected_git_sha,
            expected_run_attempt=args.expected_run_attempt,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 65
    output = args.github_output
    if output is None and os.environ.get("GITHUB_OUTPUT"):
        output = Path(os.environ["GITHUB_OUTPUT"])
    if output is not None:
        write_github_output(output, values)
    print(
        "release_run=valid "
        f"legacy_decision={values['legacy_decision']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

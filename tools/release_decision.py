from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re


SCHEMA_VERSION = "traceable-release-decision-v1"
EXPECTED_FIELDS = {
    "schema_version",
    "git_sha",
    "github_run_id",
    "github_run_attempt",
    "classification",
    "deploy_required",
    "changed_paths_sha256",
}


def build_decision(
    *,
    git_sha: str,
    github_run_id: str,
    github_run_attempt: str,
    classification: str,
    deploy_required: bool,
    changed_paths_sha256: str,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "git_sha": git_sha,
        "github_run_id": github_run_id,
        "github_run_attempt": github_run_attempt,
        "classification": classification,
        "deploy_required": deploy_required,
        "changed_paths_sha256": changed_paths_sha256,
    }
    verify_decision(decision)
    return decision


def verify_decision(
    decision: object,
    *,
    git_sha: str | None = None,
    github_run_id: str | None = None,
    github_run_attempt: str | None = None,
) -> dict[str, object]:
    if not isinstance(decision, dict) or set(decision) != EXPECTED_FIELDS:
        raise ValueError("release_decision_fields_invalid")
    if decision["schema_version"] != SCHEMA_VERSION:
        raise ValueError("release_decision_schema_invalid")
    if not re.fullmatch(r"[0-9a-f]{40}", str(decision["git_sha"])):
        raise ValueError("release_decision_git_sha_invalid")
    if not re.fullmatch(r"[1-9][0-9]*", str(decision["github_run_id"])):
        raise ValueError("release_decision_run_id_invalid")
    if not re.fullmatch(r"[1-9][0-9]*", str(decision["github_run_attempt"])):
        raise ValueError("release_decision_run_attempt_invalid")
    if decision["classification"] not in {"governance_only", "runtime"}:
        raise ValueError("release_decision_classification_invalid")
    if type(decision["deploy_required"]) is not bool:
        raise ValueError("release_decision_deploy_required_invalid")
    if decision["deploy_required"] and decision["classification"] != "runtime":
        raise ValueError("release_decision_governance_must_not_deploy")
    if not re.fullmatch(r"[0-9a-f]{64}", str(decision["changed_paths_sha256"])):
        raise ValueError("release_decision_changed_paths_hash_invalid")
    expected = {
        "git_sha": git_sha,
        "github_run_id": github_run_id,
        "github_run_attempt": github_run_attempt,
    }
    for field, value in expected.items():
        if value is not None and str(decision[field]) != value:
            raise ValueError(f"release_decision_{field}_mismatch")
    return decision


def load_decision(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("release_decision_unreadable") from exc
    return verify_decision(value)


def write_github_output(path: Path, decision: dict[str, object]) -> None:
    values = {
        "git_sha": str(decision["git_sha"]),
        "classification": str(decision["classification"]),
        "deploy_required": str(decision["deploy_required"]).lower(),
        "changed_paths_sha256": str(decision["changed_paths_sha256"]),
    }
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--verify", type=Path)
    parser.add_argument("--git-sha")
    parser.add_argument("--github-run-id")
    parser.add_argument("--github-run-attempt")
    parser.add_argument("--classification", choices=("governance_only", "runtime"))
    parser.add_argument("--deploy-required", choices=("true", "false"))
    parser.add_argument("--changed-paths-sha256")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    if args.output:
        required = (
            args.git_sha,
            args.github_run_id,
            args.github_run_attempt,
            args.classification,
            args.deploy_required,
            args.changed_paths_sha256,
        )
        if any(value is None for value in required):
            parser.error("all identity and classification arguments are required with --output")
        decision = build_decision(
            git_sha=args.git_sha,
            github_run_id=args.github_run_id,
            github_run_attempt=args.github_run_attempt,
            classification=args.classification,
            deploy_required=args.deploy_required == "true",
            changed_paths_sha256=args.changed_paths_sha256,
        )
        args.output.write_text(
            json.dumps(decision, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    else:
        decision = load_decision(args.verify)
        decision = verify_decision(
            decision,
            git_sha=args.git_sha,
            github_run_id=args.github_run_id,
            github_run_attempt=args.github_run_attempt,
        )

    output = args.github_output
    if output is None and os.environ.get("GITHUB_OUTPUT"):
        output = Path(os.environ["GITHUB_OUTPUT"])
    if output is not None:
        write_github_output(output, decision)
    print(
        "release_decision=valid "
        f"classification={decision['classification']} "
        f"deploy_required={str(decision['deploy_required']).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

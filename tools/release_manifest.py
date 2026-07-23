"""Create and verify an immutable replay release manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WEB_PREFIX = "ghcr.io/suuny-ab/traceable-support-agent-web@sha256:"
API_PREFIX = "ghcr.io/suuny-ab/traceable-support-agent-api-replay@sha256:"
IMAGE_RE = re.compile(r"^ghcr\.io/suuny-ab/[a-z0-9-]+@sha256:[0-9a-f]{64}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_hash(path: str) -> str:
    return _sha256((ROOT / path).read_bytes())


def _prompt_hashes() -> dict[str, str]:
    sys.path.insert(0, str(ROOT / "api" / "src"))
    try:
        from traceable_support.generation.checklist import (  # noqa: PLC0415
            CHECKLIST_SYSTEM_PROMPT_V2,
            STEP2_SYSTEM_PROMPT,
        )
        from traceable_support.generation.ticket_contract import (  # noqa: PLC0415
            TICKET_SYSTEM_PROMPT,
        )
    finally:
        sys.path.pop(0)
    return {
        "checklist_sha256": _sha256(CHECKLIST_SYSTEM_PROMPT_V2.encode("utf-8")),
        "qa_step2_sha256": _sha256(STEP2_SYSTEM_PROMPT.encode("utf-8")),
        "ticket_step2_sha256": _sha256(TICKET_SYSTEM_PROMPT.encode("utf-8")),
    }


def _iso_utc(value: str) -> str:
    if not value.endswith("Z"):
        raise ValueError("built_at_must_be_utc_z")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise ValueError("built_at_invalid") from None
    return value


def build_manifest(
    *,
    git_sha: str,
    web_image: str,
    api_image: str,
    built_at: str,
    github_run_id: str,
    github_run_attempt: int,
) -> dict[str, Any]:
    if not SHA_RE.fullmatch(git_sha):
        raise ValueError("git_sha_invalid")
    if not IMAGE_RE.fullmatch(web_image) or not web_image.startswith(WEB_PREFIX):
        raise ValueError("web_image_invalid")
    if not IMAGE_RE.fullmatch(api_image) or not api_image.startswith(API_PREFIX):
        raise ValueError("api_image_invalid")
    if not github_run_id.isdigit() or int(github_run_id) < 1:
        raise ValueError("github_run_id_invalid")
    if type(github_run_attempt) is not int or github_run_attempt < 1:
        raise ValueError("github_run_attempt_invalid")

    identity = json.loads((ROOT / "evals/migration-equivalence-v1.json").read_text(encoding="utf-8"))
    prompts = _prompt_hashes()
    if prompts != identity["prompts"]:
        raise ValueError("prompt_identity_mismatch")
    prompt_set_hash = _sha256(
        json.dumps(prompts, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    return {
        "schema_version": "traceable-release-manifest-v1",
        "git_sha": git_sha,
        "platform": "linux/amd64",
        "images": {"web": web_image, "api_replay": api_image},
        "runtime": {
            "experience": "replay_only",
            "provider_enabled": False,
            "provider_calls_during_build": 0,
            "prompt": {"status": "not_applicable", "sha256": None},
            "retention_days": 30,
        },
        "content": {
            "api_contract_sha256": _file_hash("api/contracts/public-api-v1.json"),
            "knowledge_file_inventory_sha256": identity["knowledge"]["file_inventory_sha256"],
            "knowledge_unit_inventory_sha256": identity["knowledge"]["unit_inventory_sha256"],
            "retrieval_fixture_sha256": _file_hash(
                "evals/fixtures/migration-retrieval-equivalence-v1.json"
            ),
            "public_regression_sha256": _file_hash("evals/public-regression-v1.json"),
            "replay_data_sha256": _file_hash("web/app/lib/replay-presets.json"),
            "source_prompt_hashes": prompts,
            "source_prompt_set_sha256": prompt_set_hash,
            "production_compose_sha256": _file_hash("deploy/compose.production.yaml"),
            "production_target_sha256": _file_hash("deploy/production-target.json"),
            "live_requirements_lock_sha256": _file_hash("api/requirements-live.lock"),
        },
        "build": {
            "built_at": _iso_utc(built_at),
            "github_run_id": github_run_id,
            "github_run_attempt": github_run_attempt,
        },
    }


def verify_manifest(value: object) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema_version", "git_sha", "platform", "images", "runtime", "content", "build"
    }:
        raise ValueError("release_manifest_shape_invalid")
    if value["schema_version"] != "traceable-release-manifest-v1":
        raise ValueError("release_manifest_version_invalid")
    if not SHA_RE.fullmatch(value["git_sha"]):
        raise ValueError("release_manifest_git_sha_invalid")
    if value["platform"] != "linux/amd64":
        raise ValueError("release_manifest_platform_invalid")
    images = value["images"]
    if type(images) is not dict or set(images) != {"web", "api_replay"}:
        raise ValueError("release_manifest_images_invalid")
    if not IMAGE_RE.fullmatch(images["web"]) or not images["web"].startswith(WEB_PREFIX):
        raise ValueError("release_manifest_web_image_invalid")
    if not IMAGE_RE.fullmatch(images["api_replay"]) or not images["api_replay"].startswith(API_PREFIX):
        raise ValueError("release_manifest_api_image_invalid")
    runtime = value["runtime"]
    expected_runtime = {
        "experience": "replay_only",
        "provider_enabled": False,
        "provider_calls_during_build": 0,
        "prompt": {"status": "not_applicable", "sha256": None},
        "retention_days": 30,
    }
    if runtime != expected_runtime:
        raise ValueError("release_manifest_runtime_invalid")
    content = value["content"]
    expected_content_keys = {
        "api_contract_sha256",
        "knowledge_file_inventory_sha256",
        "knowledge_unit_inventory_sha256",
        "retrieval_fixture_sha256",
        "public_regression_sha256",
        "replay_data_sha256",
        "source_prompt_hashes",
        "source_prompt_set_sha256",
        "production_compose_sha256",
        "production_target_sha256",
        "live_requirements_lock_sha256",
    }
    if type(content) is not dict or set(content) != expected_content_keys:
        raise ValueError("release_manifest_content_invalid")
    digest_values = [item for key, item in content.items() if key.endswith("sha256")]
    digest_values.extend(content.get("source_prompt_hashes", {}).values())
    if not all(type(item) is str and re.fullmatch(r"[0-9a-f]{64}", item) for item in digest_values):
        raise ValueError("release_manifest_content_hash_invalid")
    build = value["build"]
    if type(build) is not dict or set(build) != {
        "built_at", "github_run_id", "github_run_attempt"
    }:
        raise ValueError("release_manifest_build_invalid")
    _iso_utc(build["built_at"])
    if type(build["github_run_id"]) is not str or not build["github_run_id"].isdigit():
        raise ValueError("release_manifest_run_id_invalid")
    if type(build["github_run_attempt"]) is not int or build["github_run_attempt"] < 1:
        raise ValueError("release_manifest_attempt_invalid")
    return value


def verify_manifest_identity(
    value: object,
    *,
    expected_run_id: str,
    expected_git_sha: str | None = None,
    expected_run_attempt: int | None = None,
) -> dict[str, Any]:
    manifest = verify_manifest(value)
    if manifest["build"]["github_run_id"] != expected_run_id:
        raise ValueError("release_manifest_run_id_mismatch")
    if expected_git_sha is not None and manifest["git_sha"] != expected_git_sha:
        raise ValueError("release_manifest_git_sha_mismatch")
    if (
        expected_run_attempt is not None
        and manifest["build"]["github_run_attempt"] != expected_run_attempt
    ):
        raise ValueError("release_manifest_attempt_mismatch")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--git-sha")
    parser.add_argument("--web-image")
    parser.add_argument("--api-image")
    parser.add_argument("--built-at")
    parser.add_argument("--github-run-id")
    parser.add_argument("--github-run-attempt", type=int)
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.verify:
        value = json.loads(args.verify.read_text(encoding="utf-8"))
        if args.github_run_id is not None:
            manifest = verify_manifest_identity(
                value,
                expected_run_id=args.github_run_id,
                expected_git_sha=args.git_sha,
                expected_run_attempt=args.github_run_attempt,
            )
        else:
            if args.git_sha is not None or args.github_run_attempt is not None:
                parser.error("--git-sha and --github-run-attempt require --github-run-id")
            manifest = verify_manifest(value)
        if args.github_output:
            with args.github_output.open("a", encoding="utf-8") as output:
                output.write(f"git_sha={manifest['git_sha']}\n")
        print("release_manifest=valid")
        return 0
    if args.github_output:
        parser.error("--github-output requires --verify")
    required = {
        "git_sha": args.git_sha,
        "web_image": args.web_image,
        "api_image": args.api_image,
        "built_at": args.built_at,
        "github_run_id": args.github_run_id,
        "github_run_attempt": args.github_run_attempt,
        "output": args.output,
    }
    if any(value is None for value in required.values()):
        parser.error("generation arguments are incomplete")
    manifest = build_manifest(
        git_sha=args.git_sha,
        web_image=args.web_image,
        api_image=args.api_image,
        built_at=args.built_at,
        github_run_id=args.github_run_id,
        github_run_attempt=args.github_run_attempt,
    )
    verify_manifest(manifest)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"release_manifest=written path={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

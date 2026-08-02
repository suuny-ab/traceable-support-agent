"""Fail-closed checks for the public canonical repository.

The scanner has no third-party dependencies.  It can inspect the working tree,
the index, the current commit, or every reachable historical blob.  The first
public push uses ``--scope history --expect-migration-history`` so a secret
cannot be hidden by committing and deleting it later.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import urllib.parse
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 5 * 1024 * 1024
PUBLIC_CASE_IDS = {
    "GEN-DEV-QA-003",
    "GEN-DEV-QA-006",
    "GEN-DEV-TK-001",
    "GEN-DEV-TK-006",
    "GEN-DEV-IE-001",
    "GEN-DEV-MH-001",
    "GEN-DEV-MH-003",
    "BRD-QA-005",
}
MIGRATION_SUBJECTS = [
    "chore(governance): establish canonical public baseline",
    "refactor(api): extract product runtime",
    "refactor(web): adopt standard Next deployment",
    "ci(deploy): add reproducible image pipeline",
    "feat(replay): add insufficient-evidence handoff preset",
    "docs(governance): close canonical migration",
]
BANNED_ROOTS = {"evidence", "work", "artifacts", "outputs", "logs", "portfolio"}
BANNED_CONTROL_PARTS = {".codex", ".agents", ".qoder", ".openai"}
BANNED_HISTORY_PARTS = {
    "evaluation-contracts",
    "taskbook",
    "context-import",
    "execution-packages",
    "holdout-private",
}
BANNED_SUFFIXES = {
    ".zip", ".log", ".db", ".sqlite", ".sqlite3", ".dump", ".har",
    ".pem", ".key", ".p12", ".pfx", ".tgz", ".7z",
}
BANNED_MULTI_SUFFIXES = (".tar.gz", ".tar.bz2", ".tar.xz")
RAW_JSON_KEYS = {
    "raw_response",
    "raw_provider_response",
    "provider_output",
    "request_headers",
    "authorization_envelope",
    "execution_package",
}
TEXT_SUFFIXES = {
    "", ".caddy", ".css", ".dockerignore", ".env", ".example", ".gitignore",
    ".gitattributes", ".html", ".js", ".json", ".jsx", ".md", ".mjs",
    ".lock", ".mts", ".py", ".sh", ".svg", ".template", ".toml", ".ts", ".tsx", ".txt", ".yaml", ".yml",
}
KNOWLEDGE_HASHES = {
    "data/knowledge/synthetic-kb-v1/after-sales-policy.md": "0c30193d1dffec7ab37690883197e7e4314338f7bf2526a2ce3ffef3abe94d2e",
    "data/knowledge/synthetic-kb-v1/common-faq.md": "06da5e5366603822d75cd090e4a797b2dc8e3cd49badf35f57082516fc363377",
    "data/knowledge/synthetic-kb-v1/customer-service-sop.json": "373f813469c6f088bfcca9702ae8904a1bf962a16430f77b85bb4a5ed7e2c554",
    "data/knowledge/synthetic-kb-v1/fault-codes.json": "1f8f8d1c675f7143d85a536cf89e79c2a993c31329fa67cd67391b88068885a8",
    "data/knowledge/synthetic-kb-v1/manual-cz-r1.md": "076504c08e6ce81a001469a0bddc3bebae8620e9785fc30f5b58e276e0e3b06c",
    "data/knowledge/synthetic-kb-v1/manual-cz-r2.md": "5a54c630d70716fba68d4ac988ecf1910a7ec655726adbef154528c7d26a84a8",
}


@dataclass(frozen=True)
class Entry:
    path: str
    data: bytes
    mode: str = "100644"


def _git(*args: str, text: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True,
        text=text, encoding="utf-8" if text else None,
    )
    return result.stdout


def _split_z(value: bytes) -> list[str]:
    return [item.decode("utf-8", "strict") for item in value.split(b"\0") if item]


def _worktree_entries() -> list[Entry]:
    names = _split_z(_git("ls-files", "-z", "--cached", "--others", "--exclude-standard"))
    entries: list[Entry] = []
    for name in sorted(set(names)):
        path = ROOT / Path(name)
        if not path.is_file():
            continue
        mode = "120000" if path.is_symlink() else "100644"
        entries.append(Entry(PurePosixPath(name).as_posix(), path.read_bytes(), mode))
    return entries


def _index_entries() -> list[Entry]:
    records = _split_z(_git("ls-files", "-s", "-z"))
    entries: list[Entry] = []
    for record in records:
        metadata, name = record.split("\t", 1)
        mode, oid, _stage = metadata.split()
        entries.append(Entry(name, _git("cat-file", "blob", oid), mode))
    return entries


def _tree_entries() -> list[Entry]:
    records = _split_z(_git("ls-tree", "-r", "-z", "HEAD"))
    entries: list[Entry] = []
    for record in records:
        metadata, name = record.split("\t", 1)
        mode, kind, oid = metadata.split()
        if kind == "blob":
            entries.append(Entry(name, _git("cat-file", "blob", oid), mode))
        else:
            entries.append(Entry(name, b"", mode))
    return entries


def _history_entries() -> list[Entry]:
    objects = _git("rev-list", "--objects", "--all", text=True)
    entries: list[Entry] = []
    seen: set[tuple[str, str]] = set()
    for line in objects.splitlines():
        oid, separator, name = line.partition(" ")
        if not separator or not name or (oid, name) in seen:
            continue
        if _git("cat-file", "-t", oid, text=True).strip() != "blob":
            continue
        entries.append(Entry(name, _git("cat-file", "blob", oid)))
        seen.add((oid, name))
    return entries


def _current_entries(scope: str) -> list[Entry]:
    if scope == "worktree":
        return _worktree_entries()
    if scope == "index":
        return _index_entries()
    return _tree_entries()


def _path_errors(entry: Entry) -> list[str]:
    path = PurePosixPath(entry.path)
    parts = [part.lower() for part in path.parts]
    name = path.name.lower()
    errors: list[str] = []
    if entry.mode in {"120000", "160000"}:
        errors.append("symlink_or_submodule_not_allowed")
    if not parts or parts[0] in BANNED_ROOTS:
        errors.append("private_or_generated_root_not_allowed")
    if any(part in BANNED_CONTROL_PARTS or part in BANNED_HISTORY_PARTS for part in parts):
        errors.append("control_or_legacy_path_not_allowed")
    if any(part in {"holdout", "holdouts"} for part in parts):
        errors.append("holdout_path_not_allowed")
    if len(parts) >= 2 and parts[0] == "docs" and re.fullmatch(
        r"(?:m|tg|eval|gov)\d+[a-z0-9-]*", parts[1]
    ):
        errors.append("numbered_legacy_audit_path_not_allowed")
    if name in {"license", "license.md", "license.txt", "copying", "copying.txt"}:
        errors.append("open_source_license_not_allowed")
    env_example = name == ".env.example"
    if (name == ".env" or ".env." in name or name.endswith(".env")) and not env_example:
        errors.append("environment_file_not_allowed")
    if path.suffix.lower() in BANNED_SUFFIXES or name.endswith(BANNED_MULTI_SUFFIXES):
        errors.append("archive_log_database_or_key_not_allowed")
    if len(entry.data) > MAX_FILE_BYTES:
        errors.append("file_larger_than_5_mib")
    if name == ".gitmodules":
        errors.append("gitmodules_not_allowed")
    return errors


def _text(entry: Entry) -> str | None:
    suffix = PurePosixPath(entry.path).suffix.lower()
    if suffix not in TEXT_SUFFIXES and PurePosixPath(entry.path).name not in {
        "Dockerfile", "Caddyfile",
    }:
        return None
    try:
        return entry.data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _walk_json_keys(value: object) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_json_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json_keys(child)


def _content_errors(entry: Entry) -> list[str]:
    value = _text(entry)
    if value is None:
        path = PurePosixPath(entry.path)
        allowed = path.parts[:2] == ("web", "public") and path.suffix.lower() in {
            ".avif", ".gif", ".ico", ".jpg", ".jpeg", ".png", ".webp", ".woff", ".woff2",
        }
        if not allowed:
            return ["unapproved_binary_file"]
        signatures = {
            ".png": (b"\x89PNG\r\n\x1a\n",),
            ".jpg": (b"\xff\xd8\xff",),
            ".jpeg": (b"\xff\xd8\xff",),
            ".gif": (b"GIF87a", b"GIF89a"),
            ".webp": (b"RIFF",),
            ".woff": (b"wOFF",),
            ".woff2": (b"wOF2",),
            ".ico": (b"\x00\x00\x01\x00",),
        }
        expected = signatures.get(path.suffix.lower())
        if expected and not entry.data.startswith(expected):
            return ["public_asset_magic_invalid"]
        return []
    errors: list[str] = []
    local_patterns = [
        re.compile(r"(?i)[a-z]:[\\/]Users[\\/][^\\/\s]+"),
        re.compile(r"/(?:Users|home)/[^/\s]+/"),
    ]
    if any(pattern.search(value) for pattern in local_patterns):
        errors.append("local_home_path_not_allowed")
    private_header = "-----BEGIN " + "PRIVATE KEY-----"
    secret_patterns = [
        re.compile(re.escape(private_header)),
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
        re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        re.compile(r"(?i)://[^\s:/]+:[^\s/@]+@"),
        re.compile(
            r"(?i)(?:api[_-]?key|client[_-]?secret|password)\s*[:=]\s*"
            r"['\"](?!placeholder|example|not-a-real-key)[^'\"\s]{12,}['\"]"
        ),
    ]
    if any(pattern.search(value) for pattern in secret_patterns):
        errors.append("credential_pattern_not_allowed")
    lfs_spec = "version https://git-" + "lfs.github.com/spec/v1"
    lfs_filter = "filter" + "=lfs"
    if value.startswith(lfs_spec) or lfs_filter in value:
        errors.append("git_lfs_not_allowed")
    if entry.path.lower().endswith(".json") and "package-lock.json" not in entry.path:
        try:
            document = json.loads(value)
        except json.JSONDecodeError:
            errors.append("invalid_json")
        else:
            keys = {key.lower() for key in _walk_json_keys(document)}
            if keys & RAW_JSON_KEYS:
                errors.append("raw_provider_or_execution_json_not_allowed")
    return errors


def _nested_git_errors() -> list[str]:
    errors: list[str] = []
    ignored = {"node_modules", ".next", ".venv", "venv", ".pytest_cache", ".npm-cache"}
    for current, directories, _files in os.walk(ROOT):
        if ".git" in directories:
            if Path(current) != ROOT:
                relative = (Path(current) / ".git").relative_to(ROOT)
                errors.append(f"nested_git:{relative.as_posix()}")
            directories.remove(".git")
        directories[:] = [item for item in directories if item not in ignored]
    return errors


def _entry_map(entries: list[Entry]) -> dict[str, Entry]:
    return {entry.path: entry for entry in entries}


def _read(entries: dict[str, Entry], path: str) -> str:
    entry = entries.get(path)
    if entry is None:
        raise ValueError(f"required_file_missing:{path}")
    return entry.data.decode("utf-8")


def _yaml_block(value: str, key: str, indent: int) -> str | None:
    lines = value.splitlines()
    prefix = " " * indent + key + ":"
    for index, line in enumerate(lines):
        if not line.startswith(prefix):
            continue
        suffix = line[len(prefix):]
        if suffix and not suffix.startswith((" ", "\t")):
            continue
        block = [line]
        for candidate in lines[index + 1:]:
            stripped = candidate.strip()
            if not stripped or stripped.startswith("#"):
                block.append(candidate)
                continue
            candidate_indent = len(candidate) - len(candidate.lstrip(" "))
            if candidate_indent <= indent:
                break
            block.append(candidate)
        return "\n".join(block)
    return None


def _has_exact_yaml_line(value: str | None, indent: int, line: str) -> bool:
    if value is None:
        return False
    expected = " " * indent + line
    return any(candidate.rstrip() == expected for candidate in value.splitlines())


def _count_exact_yaml_lines(value: str | None, indent: int, line: str) -> int:
    if value is None:
        return 0
    expected = " " * indent + line
    return sum(candidate.rstrip() == expected for candidate in value.splitlines())


def _yaml_list_item_blocks(value: str | None, indent: int) -> list[str]:
    if value is None:
        return []
    lines = value.splitlines()
    prefix = " " * indent + "- "
    starts = [index for index, line in enumerate(lines) if line.startswith(prefix)]
    return [
        "\n".join(lines[start:(starts[position + 1] if position + 1 < len(starts) else len(lines))])
        for position, start in enumerate(starts)
    ]


def _folded_yaml_scalar(value: str | None, key: str, indent: int) -> str | None:
    if value is None:
        return None
    block = _yaml_block(value, key, indent)
    if block is None:
        return None
    lines = block.splitlines()
    if lines[0].rstrip() != " " * indent + key + ": >-":
        return None
    return " ".join(line.strip() for line in lines[1:] if line.strip())


def _container_smoke_workflow_errors(workflow: str) -> list[str]:
    jobs = _yaml_block(workflow, "jobs", 0)
    containers = _yaml_block(jobs or "", "containers", 2)
    job_metadata_lines = tuple(
        line.rstrip()
        for line in (containers or "").splitlines()
        if line.strip()
        and not line.lstrip().startswith("#")
        and len(line) - len(line.lstrip(" ")) <= 4
    )
    if job_metadata_lines != (
        "  containers:",
        "    runs-on: ubuntu-24.04",
        "    timeout-minutes: 30",
        "    steps:",
    ):
        return ["ci_container_job_metadata_invalid"]
    steps = _yaml_block(containers or "", "steps", 4)
    step_blocks = _yaml_list_item_blocks(steps, 6)
    smoke_step = next(
        (
            block
            for block in step_blocks
            if block.splitlines()[0].strip()
            == "- name: Smoke replay images without model or credential"
        ),
        None,
    )
    run = _yaml_block(smoke_step or "", "run", 8)
    if run is None:
        return ["ci_container_smoke_step_missing"]
    metadata_lines = tuple(
        line.rstrip()
        for line in (smoke_step or "").splitlines()
        if line.strip()
        and not line.lstrip().startswith("#")
        and len(line) - len(line.lstrip(" ")) <= 8
    )
    if metadata_lines != (
        "      - name: Smoke replay images without model or credential",
        "        if: steps.impact.outputs.classification == 'runtime'",
        "        run: |",
    ) and metadata_lines != (
        "      - name: Smoke replay images without model or credential",
        "        run: |",
    ):
        return ["ci_container_smoke_metadata_invalid"]
    script_lines = tuple(
        line.strip()
        for line in run.splitlines()[1:]
        if line.strip() and not line.lstrip().startswith("#")
    )
    smoke_contract = (
        "set +e",
        "status=0",
        'test "$(docker image inspect --format \'{{.Config.User}}\' traceable-web:test)" = "node" || { echo "web_image_user_invalid" >&2; status=1; }',
        'test "$(docker image inspect --format \'{{.Config.User}}\' traceable-api-replay:test)" = "10001:10001" || { echo "api_image_user_invalid" >&2; status=1; }',
        "docker run --rm --entrypoint python --network none traceable-api-replay:test -S -c \\",
        '"from traceable_support.api.runs import PublicRunService; assert PublicRunService.live_available is not None" \\',
        '|| { echo "replay_assembly_failed" >&2; status=1; }',
        "docker run -d --name traceable-api-replay-ci --read-only \\",
        "--tmpfs /tmp:rw,noexec,nosuid,size=64m \\",
        "--tmpfs /var/lib/traceable:rw,noexec,nosuid,uid=10001,gid=10001,size=64m \\",
        "--cap-drop ALL --security-opt no-new-privileges \\",
        "-e TRACEABLE_PUBLIC_ORIGIN=http://127.0.0.1:3000 \\",
        "-e TRACEABLE_PUBLIC_LIVE_ENABLED=false -p 127.0.0.1:8000:8000 \\",
        'traceable-api-replay:test || { echo "api_container_start_failed" >&2; status=1; }',
        "docker run -d --name traceable-web-ci --read-only \\",
        "--tmpfs /tmp:rw,noexec,nosuid,size=64m \\",
        "--cap-drop ALL --security-opt no-new-privileges \\",
        '-p 127.0.0.1:3000:3000 traceable-web:test || { echo "web_container_start_failed" >&2; status=1; }',
        "trap 'docker rm -f traceable-web-ci traceable-api-replay-ci >/dev/null 2>&1 || true' EXIT",
        "api_ready=false",
        "for attempt in $(seq 1 15); do",
        'if curl --fail --silent --show-error --connect-timeout 1 --max-time 1 http://127.0.0.1:8000/api/v1/health >"$RUNNER_TEMP/health.json"; then',
        "api_ready=true",
        "break",
        "fi",
        "sleep 1",
        "done",
        'if [[ "$api_ready" != true ]]; then',
        'echo "api_container_not_ready" >&2',
        "docker logs traceable-api-replay-ci >&2 || true",
        "status=1",
        "else",
        'python -c \'import json,os,pathlib; value=json.loads(pathlib.Path(os.environ["RUNNER_TEMP"],"health.json").read_text()); assert value["live_experience"] == "replay_only" and value["release_sha"] == os.environ["GITHUB_SHA"]\' \\',
        '|| { echo "health_release_identity_invalid" >&2; status=1; }',
        "fi",
        "web_ready=false",
        "for attempt in $(seq 1 15); do",
        "if curl --fail --silent --show-error --connect-timeout 1 --max-time 1 http://127.0.0.1:3000/ >/dev/null; then",
        "web_ready=true",
        "break",
        "fi",
        "sleep 1",
        "done",
        'if [[ "$web_ready" != true ]]; then',
        'echo "web_container_not_ready" >&2',
        "docker logs traceable-web-ci >&2 || true",
        "status=1",
        "fi",
        "for route in / /design /app /privacy; do",
        'if ! curl --fail --silent --show-error "http://127.0.0.1:3000$route" >/dev/null; then',
        'echo "container_route_failed:$route" >&2',
        "status=1",
        "fi",
        "done",
        'python3 tools/ci_proof.py record --claim containers.replay-smoke --category product --exit-code "$status" --proof "$RUNNER_TEMP/ci-proof.jsonl"',
        'exit "$status"',
    )
    if script_lines != smoke_contract:
        return ["ci_container_readiness_contract_invalid"]
    return []


def _deployment_workflow_errors(workflow: str) -> list[str]:
    errors: list[str] = []
    on_block = _yaml_block(workflow, "on", 0)
    workflow_run = _yaml_block(on_block or "", "workflow_run", 2)
    workflow_dispatch = _yaml_block(on_block or "", "workflow_dispatch", 2)
    concurrency = _yaml_block(workflow, "concurrency", 0)
    jobs = _yaml_block(workflow, "jobs", 0)
    deploy = _yaml_block(jobs or "", "deploy", 2)
    deploy_env = _yaml_block(deploy or "", "env", 4)
    steps = _yaml_block(deploy or "", "steps", 4)
    step_blocks = _yaml_list_item_blocks(steps, 6)
    expected_step_names = (
        "- name: Check out the trusted deployment controller",
        "- name: Set up Python",
        "- name: Stage trusted deployment controller",
        "- name: Download manifest from the selected green run",
        "- name: Bind manifest to the selected green run",
        "- name: Check out the manifest commit",
        "- name: Verify manifest and main ancestry",
        "- name: Build live API image on the production host",
        "- name: Generate and verify the live (v2) release manifest",
        "- name: Build public deployment package",
        "- name: Verify trusted deployment controller integrity",
        "- name: Upload and activate with strict host verification",
    )
    actual_step_names = tuple(
        block.splitlines()[0].strip() for block in step_blocks
    )

    if not _has_exact_yaml_line(
        workflow,
        0,
        'run-name: "production deploy for ci-release #${{ github.event.workflow_run.id || inputs.publish_run_id }}"',
    ):
        errors.append("production_deploy_run_name_missing")

    if workflow_dispatch is None:
        errors.append("production_deploy_manual_fallback_missing")
    else:
        inputs = _yaml_block(workflow_dispatch, "inputs", 4)
        publish_run_id = _yaml_block(inputs or "", "publish_run_id", 6)
        if not (
            _has_exact_yaml_line(publish_run_id, 8, "required: true")
            and _has_exact_yaml_line(publish_run_id, 8, "type: string")
        ):
            errors.append("production_deploy_manual_input_invalid")

    if workflow_run is None:
        errors.append("production_deploy_auto_queue_missing")
    else:
        trigger_contract = (
            (4, 'workflows: ["ci-release"]', "production_deploy_source_workflow_invalid"),
            (4, "types: [completed]", "production_deploy_completion_trigger_missing"),
            (4, "branches: [main]", "production_deploy_branch_filter_missing"),
        )
        for indent, line, error in trigger_contract:
            if not _has_exact_yaml_line(workflow_run, indent, line):
                errors.append(error)

    expected_condition = (
        "github.event_name == 'workflow_dispatch' || "
        "( github.event_name == 'workflow_run' && "
        "github.event.workflow_run.conclusion == 'success' && "
        "github.event.workflow_run.event == 'push' && "
        "github.event.workflow_run.head_branch == 'main' && "
        "github.event.workflow_run.head_repository.full_name == github.repository )"
    )
    actual_condition = _folded_yaml_scalar(deploy, "if", 4)
    if _has_exact_yaml_line(
        deploy,
        4,
        "if: needs.preflight.outputs.deploy_required == 'true'",
    ):
        actual_condition = "needs.preflight.outputs.deploy_required == 'true'"
    if actual_condition not in {
        expected_condition,
        "needs.preflight.outputs.deploy_required == 'true'",
    }:
        errors.append("production_deploy_condition_invalid")

    if not _has_exact_yaml_line(deploy, 4, "environment: production"):
        errors.append("production_deploy_environment_gate_missing")
    env_contract = (
        (
            "PUBLISH_RUN_ID: ${{ github.event.workflow_run.id || inputs.publish_run_id }}",
            "production_deploy_run_identity_missing",
        ),
        (
            "PUBLISH_HEAD_SHA: ${{ needs.preflight.outputs.git_sha }}",
            "production_deploy_head_identity_missing",
        ),
        (
            "PUBLISH_RUN_ATTEMPT: ${{ needs.preflight.outputs.run_attempt }}",
            "production_deploy_attempt_identity_missing",
        ),
    )
    for line, error in env_contract:
        if not _has_exact_yaml_line(deploy_env, 6, line):
            errors.append(error)
    deploy_env_entries = tuple(
        line.strip()
        for line in (deploy_env or "").splitlines()[1:]
        if line.strip() and not line.strip().startswith("#")
    )
    if deploy_env_entries != tuple(line for line, _ in env_contract):
        errors.append("production_deploy_environment_invalid")
    if not _has_exact_yaml_line(deploy, 10, "run-id: ${{ env.PUBLISH_RUN_ID }}"):
        errors.append("production_deploy_artifact_identity_missing")
    for line, error in (
        (
            '--github-run-id "$PUBLISH_RUN_ID"',
            "production_deploy_manifest_run_binding_missing",
        ),
        (
            'verify_args+=(--git-sha "$PUBLISH_HEAD_SHA")',
            "production_deploy_manifest_sha_binding_missing",
        ),
        (
            'verify_args+=(--github-run-attempt "$PUBLISH_RUN_ATTEMPT")',
            "production_deploy_manifest_attempt_binding_missing",
        ),
    ):
        if not _has_exact_yaml_line(deploy, 12, line):
            errors.append(error)
    step_names = {
        "trusted": "- name: Check out the trusted deployment controller",
        "stage": "- name: Stage trusted deployment controller",
        "manifest": "- name: Check out the manifest commit",
        "integrity": "- name: Verify trusted deployment controller integrity",
        "upload": "- name: Upload and activate with strict host verification",
    }
    named_steps: dict[str, tuple[int, str]] = {}
    for key, name in step_names.items():
        matches = [
            (index, block)
            for index, block in enumerate(step_blocks)
            if block.splitlines()[0].strip() == name
        ]
        if len(matches) == 1:
            named_steps[key] = matches[0]

    staged_controller_lines = (
        'controller_dir="$RUNNER_TEMP/traceable-deploy-controller"',
        'install -d -m 700 "$controller_dir"',
        'install -m 600 tools/validate_deploy_port.py "$controller_dir/validate_deploy_port.py"',
        (
            'install -m 600 tools/deploy_ssh_transport.py '
            '"$controller_dir/deploy_ssh_transport.py"'
        ),
    )
    trusted_block = named_steps.get("trusted", (-1, ""))[1]
    trusted_with = _yaml_block(trusted_block, "with", 8)
    stage_block = named_steps.get("stage", (-1, ""))[1]
    stage_run = _yaml_block(stage_block, "run", 8)
    stage_commands = tuple(
        line.strip()
        for line in (stage_run or "").splitlines()[1:]
        if line.strip() and not line.strip().startswith("#")
    )
    expected_stage_commands = ("set -Eeuo pipefail",) + staged_controller_lines
    stage_block_lines = tuple(
        line.rstrip()
        for line in (stage_block or "").splitlines()
        if line.strip() and not line.strip().startswith("#")
    )
    expected_stage_block_lines = (
        "      - name: Stage trusted deployment controller",
        "        run: |",
    ) + tuple("          " + line for line in expected_stage_commands)
    trusted_order = tuple(
        named_steps[key][0]
        for key in ("trusted", "stage", "manifest", "integrity", "upload")
        if key in named_steps
    )
    shell_override_pattern = re.compile(r"""^(?:["']?shell["']?)\s*:""")
    defaults_override_pattern = re.compile(r"""\bdefaults["']?\s*:""")
    shell_override = any(
        shell_override_pattern.match(line.strip()) is not None
        for line in (workflow or "").splitlines()
        if line.strip() and not line.strip().startswith("#")
    )
    defaults_override = any(
        defaults_override_pattern.search(line.strip()) is not None
        for line in (workflow or "").splitlines()
        if line.strip() and not line.strip().startswith("#")
    )
    if (
        len(named_steps) != len(step_names)
        or actual_step_names != expected_step_names
        or trusted_order != tuple(sorted(trusted_order))
        or shell_override
        or defaults_override
        or not _has_exact_yaml_line(
            trusted_block,
            8,
            "uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
        )
        or not _has_exact_yaml_line(trusted_with, 10, "ref: main")
        or not _has_exact_yaml_line(trusted_with, 10, "persist-credentials: false")
        or any(line.startswith(" " * 10 + "repository:") for line in (trusted_with or "").splitlines())
        or not _has_exact_yaml_line(stage_block, 8, "run: |")
        or any(
            not _has_exact_yaml_line(stage_block, 10, line)
            or _count_exact_yaml_lines(stage_block, 10, line) != 1
            for line in staged_controller_lines
        )
        or stage_commands != expected_stage_commands
        or stage_block_lines != expected_stage_block_lines
    ):
        errors.append("production_deploy_controller_not_trusted")

    validator_sha256 = "6a1af83611a5164e53a8697fe654725a867fe8bc8a8e1b81af01d34cc2b70e52"
    transport_sha256 = "0ac333ace233077586ad161bd579bc7708e2345e8f0a03f8886f2c91aa9e4166"
    integrity_lines = (
        (10, 'controller_dir="$RUNNER_TEMP/traceable-deploy-controller"'),
        (10, "printf '%s  %s\\n' \\"),
        (
            12,
            f"'{validator_sha256}' "
            '"$controller_dir/validate_deploy_port.py" \\',
        ),
        (
            12,
            f"'{transport_sha256}' "
            '"$controller_dir/deploy_ssh_transport.py" \\',
        ),
        (12, "| /usr/bin/sha256sum --check --strict"),
    )
    integrity_block = named_steps.get("integrity", (-1, ""))[1]
    integrity_run = _yaml_block(integrity_block, "run", 8)
    integrity_commands = tuple(
        line.strip()
        for line in (integrity_run or "").splitlines()[1:]
        if line.strip() and not line.strip().startswith("#")
    )
    integrity_block_lines = tuple(
        line.rstrip()
        for line in (integrity_block or "").splitlines()
        if line.strip() and not line.strip().startswith("#")
    )
    expected_integrity_block_lines = (
        "      - name: Verify trusted deployment controller integrity",
        "        run: |",
        "          set -Eeuo pipefail",
    ) + tuple(" " * indent + line for indent, line in integrity_lines)
    if (
        integrity_commands
        != ("set -Eeuo pipefail",) + tuple(line for _, line in integrity_lines)
        or integrity_block_lines != expected_integrity_block_lines
    ):
        errors.append("production_deploy_controller_integrity_missing")

    transport_lines = (
        (
            10,
            '/usr/bin/python3 -E "$RUNNER_TEMP/traceable-deploy-controller/'
            'deploy_ssh_transport.py" \\',
        ),
        (12, "--staging release-staging \\"),
        (
            12,
            '--remote-stage "/tmp/traceable-support-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}" \\',
        ),
        (12, "--release-root /opt/traceable-support"),
    )
    upload_block = named_steps.get("upload", (-1, ""))[1]
    upload_env = _yaml_block(upload_block, "env", 8)
    upload_run = _yaml_block(upload_block, "run", 8)
    secret_contract = (
        "DEPLOY_HOST: ${{ secrets.DEPLOY_HOST }}",
        "DEPLOY_USER: ${{ secrets.DEPLOY_USER }}",
        "DEPLOY_PORT: ${{ secrets.DEPLOY_PORT }}",
        "DEPLOY_SSH_KEY: ${{ secrets.DEPLOY_SSH_KEY }}",
        "DEPLOY_KNOWN_HOSTS: ${{ secrets.DEPLOY_KNOWN_HOSTS }}",
    )
    upload_environment_contract = secret_contract + (
        "BASH_ENV: /dev/null",
        'LD_LIBRARY_PATH: ""',
        'LD_PRELOAD: ""',
    )
    deploy_secret_expression = re.compile(
        r"\$\{\{\s*secrets\.DEPLOY_"
        r"(?:HOST|USER|PORT|SSH_KEY|KNOWN_HOSTS)\s*\}\}"
    )
    invalid_secret_mapping = any(
        deploy_secret_expression.search(line.strip()) is not None
        and line.strip() not in secret_contract
        for line in (workflow or "").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ) or any(
        # Each deploy secret is mapped exactly twice: the pinned live-image
        # host-build step and the pinned upload step, nowhere else.
        sum(candidate.strip() == expected for candidate in (workflow or "").splitlines()) != 2
        for expected in secret_contract
    )
    live_build_blocks = [
        block
        for block in step_blocks
        if block.splitlines()[0].strip()
        == "- name: Build live API image on the production host"
    ]
    live_build_block = live_build_blocks[0] if len(live_build_blocks) == 1 else ""
    live_image_identity_contract = (
        'build_sha="$(git rev-parse HEAD)"',
        "docker build --quiet --target live --build-arg VCS_REF='\"$build_sha\"'",
    )
    if any(token not in live_build_block for token in live_image_identity_contract):
        errors.append("production_live_image_sha_injection_missing")
    live_build_env = _yaml_block(live_build_block, "env", 8)
    live_build_env_entries = tuple(
        line.strip()
        for line in (live_build_env or "").splitlines()[1:]
        if line.strip() and not line.strip().startswith("#")
    )
    live_build_env_invalid = live_build_env_entries != secret_contract
    deploy_without_live_build = (deploy or "").replace(live_build_block, "")
    upload_env_entries = tuple(
        line.strip()
        for line in (upload_env or "").splitlines()[1:]
        if line.strip() and not line.strip().startswith("#")
    )
    direct_secret_use = re.compile(
        r"\$(?:\{)?DEPLOY_(?:HOST|USER|PORT|SSH_KEY|KNOWN_HOSTS)(?:\})?"
    )
    transport_command = re.compile(r"(?<![A-Za-z0-9_])(?:ssh|scp)(?![A-Za-z0-9_])")
    direct_transport = False
    direct_secret_reference = False
    # Direct ssh/scp and direct DEPLOY_* references are confined to the
    # pinned live-image host-build step; everywhere else in the deploy job
    # they stay forbidden (the upload step must use the trusted controller).
    for line in deploy_without_live_build.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and transport_command.search(stripped):
            direct_transport = True
        if (
            stripped
            and not stripped.startswith("#")
            and direct_secret_use.search(stripped)
            and stripped not in secret_contract
        ):
            direct_secret_reference = True
    unsafe_guard = '[[ "$port" =~ ^[0-9]{1,5}$ ]] && test "$port"'
    upload_commands = tuple(
        line.strip()
        for line in (upload_run or "").splitlines()[1:]
        if line.strip() and not line.strip().startswith("#")
    )
    expected_upload_commands = ("set -Eeuo pipefail",) + tuple(
        line for _, line in transport_lines
    )
    upload_block_lines = tuple(
        line.rstrip()
        for line in (upload_block or "").splitlines()
        if line.strip() and not line.strip().startswith("#")
    )
    expected_upload_block_lines = (
        "      - name: Upload and activate with strict host verification",
        "        env:",
    ) + tuple(
        "          " + line for line in upload_environment_contract
    ) + (
        "        run: |",
        "          set -Eeuo pipefail",
    ) + tuple(
        " " * indent + line for indent, line in transport_lines
    )
    if (
        any(
            not _has_exact_yaml_line(upload_env, 10, line)
            for line in upload_environment_contract
        )
        or upload_env_entries != upload_environment_contract
        or invalid_secret_mapping
        or upload_commands != expected_upload_commands
        or upload_block_lines != expected_upload_block_lines
        or live_build_env_invalid
        or any(
            not _has_exact_yaml_line(upload_block, indent, line)
            or _count_exact_yaml_lines(deploy, indent, line) != 1
            for indent, line in transport_lines
        )
        or direct_transport
        or direct_secret_reference
        or unsafe_guard in (deploy or "")
    ):
        errors.append("production_deploy_transport_preflight_invalid")

    if not _has_exact_yaml_line(concurrency, 2, "group: traceable-support-production"):
        errors.append("production_deploy_concurrency_missing")
    if not _has_exact_yaml_line(concurrency, 2, "cancel-in-progress: false"):
        errors.append("production_deploy_must_not_cancel_in_progress")
    return errors


def _release_decision_workflow_errors(
    ci_workflow: str,
    deploy_workflow: str,
) -> list[str]:
    errors: list[str] = []
    ci_jobs = _yaml_block(ci_workflow, "jobs", 0)
    governance = _yaml_block(ci_jobs or "", "governance", 2)
    if governance is None:
        errors.append("ci_impact_classification_missing")
    else:
        required_classify_tokens = (
            "python tools/ci_impact.py",
            "--github-output \"$GITHUB_OUTPUT\"",
            "python tools/release_decision.py",
            "--output release-decision.json",
            "--changed-paths-sha256 \"$CHANGED_PATHS_SHA256\"",
            "name: release-decision",
        )
        if any(token not in governance for token in required_classify_tokens):
            errors.append("ci_release_decision_generation_invalid")

    for name in ("governance", "web", "api", "containers"):
        job = _yaml_block(ci_jobs or "", name, 2)
        if (
            "- name: Classify changed paths" not in (job or "")
            or "--github-output \"$GITHUB_OUTPUT\"" not in (job or "")
        ):
            errors.append(f"ci_impact_classification_missing:{name}")
    for name in ("web", "api", "containers"):
        job = _yaml_block(ci_jobs or "", name, 2)
        if (
            "Record skipped runtime checks (governance-only change)" not in (job or "")
            or "steps.impact.outputs.classification == 'governance_only'"
            not in (job or "")
            or "steps.impact.outputs.classification == 'runtime'"
            not in (job or "")
        ):
            errors.append(f"ci_no_impact_success_missing:{name}")
    publish = _yaml_block(ci_jobs or "", "publish", 2)
    if (
        "needs.governance.outputs.classification == 'runtime'" not in (publish or "")
        or "needs: [governance, web, api, containers]" not in (publish or "")
    ):
        errors.append("ci_publish_impact_gate_invalid")

    deploy_jobs = _yaml_block(deploy_workflow, "jobs", 0)
    preflight = _yaml_block(deploy_jobs or "", "preflight", 2)
    deploy = _yaml_block(deploy_jobs or "", "deploy", 2)
    if preflight is None:
        errors.append("production_release_decision_preflight_missing")
    else:
        preflight_condition = _folded_yaml_scalar(preflight, "if", 4)
        expected_condition = (
            "github.event_name == 'workflow_dispatch' || "
            "( github.event_name == 'workflow_run' && "
            "github.event.workflow_run.conclusion == 'success' && "
            "github.event.workflow_run.event == 'push' && "
            "github.event.workflow_run.head_branch == 'main' && "
            "github.event.workflow_run.head_repository.full_name == github.repository )"
        )
        required_preflight_tokens = (
            "release-decision",
            "python tools/release_run.py",
            '--repository "$GITHUB_REPOSITORY"',
            '--run-id "$PUBLISH_RUN_ID"',
            "selection_args+=(--manual)",
            'source "$selection_output"',
            "release_decision_artifact_id",
            "release_manifest_artifact_id",
            'gh api --paginate --slurp',
            "python tools/release_decision.py",
            '--git-sha "$git_sha"',
            "--github-run-id \"$PUBLISH_RUN_ID\"",
            '--github-run-attempt "$run_attempt"',
        )
        if (
            preflight_condition != expected_condition
            or any(token not in preflight for token in required_preflight_tokens)
            or "environment: production" in preflight
            or "secrets.DEPLOY_" in preflight
            or re.search(r"(?<![A-Za-z0-9_])(?:ssh|scp)(?![A-Za-z0-9_])", preflight)
        ):
            errors.append("production_release_decision_preflight_invalid")
    if (
        not _has_exact_yaml_line(deploy, 4, "needs: preflight")
        or not _has_exact_yaml_line(
            deploy,
            4,
            "if: needs.preflight.outputs.deploy_required == 'true'",
        )
        or not _has_exact_yaml_line(deploy, 4, "environment: production")
    ):
        errors.append("production_release_decision_gate_invalid")
    return errors


def _markdown_link_errors(entries: dict[str, Entry]) -> list[str]:
    errors: list[str] = []
    link_re = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
    for path, entry in entries.items():
        if not path.lower().endswith(".md"):
            continue
        text = entry.data.decode("utf-8", "strict")
        parent = PurePosixPath(path).parent
        for raw in link_re.findall(text):
            target = raw.strip().split()[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            decoded = urllib.parse.unquote(target.split("#", 1)[0])
            normalized = PurePosixPath(parent, decoded).as_posix()
            normalized = os.path.normpath(normalized).replace("\\", "/")
            if normalized not in entries and not any(
                candidate.startswith(normalized.rstrip("/") + "/") for candidate in entries
            ):
                errors.append(f"broken_markdown_link:{path}:{target}")
    return errors


def _product_import_errors(entries: dict[str, Entry]) -> list[str]:
    errors: list[str] = []
    banned = {"api", "evals", "tools", "scripts", "workflow", "evidence"}
    prefix = "api/src/traceable_support/product/"
    for path, entry in entries.items():
        if not path.startswith(prefix) or not path.endswith(".py"):
            continue
        tree = ast.parse(entry.data.decode("utf-8"), filename=path)
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name.split(".", 1)[0] in banned:
                    errors.append(f"product_import_boundary:{path}:{name}")
    return errors


def _active_increment_errors(entries: list[Entry]) -> list[str]:
    mapped = _entry_map(entries)
    errors: list[str] = []
    active_prefix = "docs/work/active/"
    active_paths = {
        PurePosixPath(path)
        for path in mapped
        if path.startswith(active_prefix)
    }
    active_slugs = {
        PurePosixPath(path).parts[3]
        for path in active_paths
        if len(path.parts) == 5
    }
    malformed_layout = any(len(path.parts) != 5 for path in active_paths)
    if malformed_layout:
        errors.append("active_increment_layout_invalid")
    if active_paths and not active_slugs:
        errors.append("active_increment_file_set_invalid")
    else:
        for slug in active_slugs:
            actual = {
                path
                for path in active_paths
                if len(path.parts) == 5 and path.parts[3] == slug
            }
            expected = {
                PurePosixPath(f"docs/work/active/{slug}/{name}")
                for name in ("spec.md", "plan.md", "result.md", "review.md")
            }
            if actual != expected:
                errors.append(f"active_increment_file_set_invalid:{slug}")
    try:
        status = _read(mapped, "docs/status.md")
        for slug in active_slugs:
            if f"docs/work/active/{slug}/" not in status:
                errors.append(f"status_does_not_link_active_increment:{slug}")
    except (UnicodeDecodeError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def _governance_rule_errors(entries: list[Entry]) -> list[str]:
    mapped = _entry_map(entries)
    errors: list[str] = []
    try:
        agents = _read(mapped, "AGENTS.md")
        if len(agents.splitlines()) > 110:
            errors.append("agents_rule_index_too_long")
        owner_marker = "## 授权层：唯一默认值正文"
        rule_paths = (
            "AGENTS.md",
            "docs/engineering/agent-workflow.md",
            "docs/engineering/development-flow.md",
            "docs/engineering/github-lifecycle.md",
            "docs/engineering/operations.md",
            "docs/engineering/quality.md",
            "docs/engineering/review.md",
            "docs/work/README.md",
        )
        owners = [
            path for path in rule_paths
            if owner_marker in _read(mapped, path)
        ]
        if owners != ["docs/engineering/review.md"]:
            errors.append("authorization_policy_owner_invalid")
    except (UnicodeDecodeError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def _structural_errors(entries: list[Entry], scope: str) -> list[str]:
    mapped = _entry_map(entries)
    errors = _active_increment_errors(entries) + _governance_rule_errors(entries)
    try:
        status = _read(mapped, "docs/status.md")
        project = _read(mapped, "PROJECT.md")
        readme = _read(mapped, "README.md")
        public = _read(mapped, "PUBLIC_CONTEXT.md")
        claims = "\n".join((status, project, readme, public)).lower()
        for phrase in ("replay_only", "product/0.1.0", "not_released"):
            if phrase not in claims:
                errors.append(f"required_public_claim_missing:{phrase}")
        machine_claims = (
            # Live era: provider is enabled by explicit authorization; the
            # status file must keep the confinement and budget facts visible.
            "provider_enabled=true",
            "provider.env",
            "0600",
            "重试 0",
        )
        if any(phrase not in status.lower() for phrase in machine_claims):
            errors.append("migration_provider_zero_claim_missing")
    except (UnicodeDecodeError, ValueError) as exc:
        errors.append(str(exc))
    try:
        suite = json.loads(_read(mapped, "evals/public-regression-v1.json"))
        if set(suite) != {"schema_version", "purpose", "status", "cases", "known_product_gaps"}:
            errors.append("public_regression_top_level_fields_invalid")
        ids = [case.get("case_id") for case in suite.get("cases", [])]
        if len(ids) != 8 or set(ids) != PUBLIC_CASE_IDS or len(set(ids)) != len(ids):
            errors.append("public_regression_case_set_invalid")
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
        errors.append("public_regression_suite_invalid")
    try:
        replay = json.loads(_read(mapped, "web/app/lib/replay-presets.json"))
        suite = json.loads(_read(mapped, "evals/public-regression-v1.json"))
        if set(replay) != {"schema_version", "presets"} or replay.get(
            "schema_version"
        ) != "verified-replay-presets-v1":
            errors.append("replay_preset_schema_invalid")
        presets = replay.get("presets", [])
        preset_ids = [item.get("id") for item in presets if type(item) is dict]
        if len(presets) != 3 or len(set(preset_ids)) != 3 or set(preset_ids) != {
            "qa-local-clean", "ticket-carpet-risk", "qa-insufficient-evidence"
        }:
            errors.append("replay_preset_inventory_invalid")
        expectation = next(
            case for case in suite["cases"] if case["case_id"] == "GEN-DEV-IE-001"
        )
        insufficient = next(
            item for item in presets if item.get("caseId") == "GEN-DEV-IE-001"
        )
        expected = expectation["expected"]
        result = insufficient.get("result", {})
        if (
            insufficient.get("taskType") != expectation["task_type"]
            or insufficient.get("model") != expectation["product_model"]
            or insufficient.get("input") != expectation["input"]
            or insufficient.get("stopStageIndex") != 0
            or insufficient.get("replayOnly") is not True
            or result.get("mode") != "verified_replay"
            or result.get("outcome") != expected["outcome"]
            or result.get("handoff_reason") != expected["handoff_reason"]
            or result.get("provider_call_count") != expected["provider_call_count"]
            or expected.get("source_sections") != []
            or result.get("evidence") != []
        ):
            errors.append("insufficient_evidence_replay_contract_invalid")
    except (StopIteration, TypeError, KeyError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
        errors.append("replay_preset_contract_invalid")
    import hashlib
    for path, expected_hash in KNOWLEDGE_HASHES.items():
        entry = mapped.get(path)
        if entry is None or hashlib.sha256(entry.data).hexdigest() != expected_hash:
            errors.append(f"synthetic_knowledge_hash_invalid:{path}")
    try:
        compose = _read(mapped, "deploy/compose.production.yaml")
        if re.search(r"(?m)^\s*build\s*:", compose) or ":latest" in compose:
            errors.append("production_compose_must_not_build_or_use_latest")
        image_lines = re.findall(r"(?m)^\s*image:\s*(.+)$", compose)
        if image_lines != [
            "${WEB_IMAGE:?WEB_IMAGE must be an immutable digest}",
            "${API_IMAGE:?API_IMAGE must be an immutable digest}",
        ]:
            errors.append("production_compose_image_contract_invalid")
        live_flag_contract = (
            "TRACEABLE_PUBLIC_LIVE_ENABLED: "
            "${TRACEABLE_PUBLIC_LIVE_ENABLED:-false}"
        )
        provider_env_contract = (
            "path: /opt/traceable-support/provider.env",
            "required: false",
        )
        if live_flag_contract not in compose or any(
            line not in compose for line in provider_env_contract
        ):
            # The provider flag must default to off and the credential must
            # stay an optional, host-side 0600 env file (never built in).
            errors.append("production_provider_disable_missing")
    except (UnicodeDecodeError, ValueError) as exc:
        errors.append(str(exc))
    try:
        target = json.loads(_read(mapped, "deploy/production-target.json"))
        if target != {
            "schema_version": "traceable-production-target-v1",
            "public_origin": "https://47.84.34.86",
            "rehearse_rollback": True,
        }:
            errors.append("production_target_contract_invalid")
        deploy_workflow = _read(mapped, ".github/workflows/deploy-production.yml")
        if "inputs.public_origin" in deploy_workflow or "inputs.rehearse_rollback" in deploy_workflow:
            errors.append("production_target_must_not_be_dispatch_input")
        if "cp deploy/production-target.json release-staging/deployment-input.json" not in deploy_workflow:
            errors.append("production_target_not_bound_to_deployment")
        if "deploy/switch_release_state.py" not in deploy_workflow:
            errors.append("release_state_switcher_not_packaged")
        errors.extend(_deployment_workflow_errors(deploy_workflow))
        ci_workflow = _read(mapped, ".github/workflows/ci-release.yml")
        errors.extend(_container_smoke_workflow_errors(ci_workflow))
        errors.extend(
            _release_decision_workflow_errors(ci_workflow, deploy_workflow)
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    try:
        def requirements(path: str) -> dict[str, str]:
            result: dict[str, str] = {}
            for raw in _read(mapped, path).splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("--hash=sha256:"):
                    if not re.fullmatch(r"--hash=sha256:[0-9a-f]{64}(?: \\)?", line):
                        raise ValueError(f"requirement_hash_invalid:{path}")
                    continue
                match = re.fullmatch(
                    r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)(?: \\)?", line
                )
                if not match:
                    raise ValueError(f"requirement_not_exact:{path}")
                name = re.sub(r"[-_.]+", "-", match.group(1)).lower()
                if name in result:
                    raise ValueError(f"requirement_duplicate:{path}:{name}")
                result[name] = match.group(2)
            return result

        for direct_path, lock_path in (
            ("api/requirements-base.txt", "api/requirements-base.lock"),
            ("api/requirements-live.txt", "api/requirements-live.lock"),
            ("api/requirements-test.txt", "api/requirements-test.lock"),
        ):
            direct = requirements(direct_path)
            locked = requirements(lock_path)
            if any(locked.get(name) != version for name, version in direct.items()):
                errors.append(f"requirement_lock_does_not_cover_direct:{lock_path}")
        dockerfile = _read(mapped, "api/Dockerfile")
        live_lock = _read(mapped, "api/requirements-live.lock")
        if len(re.findall(r"(?m)^\s+--hash=sha256:[0-9a-f]{64}", live_lock)) < len(
            requirements("api/requirements-live.lock")
        ):
            errors.append("live_requirement_hash_coverage_invalid")
        base_lock = _read(mapped, "api/requirements-base.lock")
        if len(re.findall(r"(?m)^\s+--hash=sha256:[0-9a-f]{64}", base_lock)) < len(
            requirements("api/requirements-base.lock")
        ):
            errors.append("base_requirement_hash_coverage_invalid")
        if (
            "requirements-live.lock" not in dockerfile
            or "requirements-base.lock" not in dockerfile
            or "--no-deps" not in dockerfile
            or "--require-hashes" not in dockerfile
        ):
            errors.append("live_docker_dependency_lock_not_enforced")
    except (UnicodeDecodeError, ValueError) as exc:
        errors.append(str(exc))
    for path, entry in mapped.items():
        if path.startswith(".github/workflows/") and path.endswith((".yml", ".yaml")):
            workflow = entry.data.decode("utf-8")
            if "pull_request_target:" in workflow:
                errors.append(f"pull_request_target_not_allowed:{path}")
            if not re.search(r"(?m)^permissions:\s*\n\s+contents:\s*read\s*$", workflow):
                errors.append(f"workflow_default_read_permission_missing:{path}")
            checkout_blocks = re.findall(
                r"(?ms)(?:^\s*-\s+name:.*?\n)?\s*-\s+uses:\s+actions/checkout@[^\n]+\n(.*?)(?=^\s*-\s+(?:name:|uses:|run:)|^\s{2,}[A-Za-z_-]+:|\Z)",
                workflow,
            )
            if "actions/checkout@" in workflow and not all(
                re.search(r"persist-credentials:\s*false", block) for block in checkout_blocks
            ):
                errors.append(f"checkout_persist_credentials_not_disabled:{path}")
            for action in re.findall(r"(?m)^\s*-?\s*uses:\s*([^\s#]+)", workflow):
                if action.startswith("./"):
                    continue
                if not re.fullmatch(r"[^@]+@[0-9a-f]{40}", action):
                    errors.append(f"github_action_not_pinned:{path}:{action}")
    errors.extend(_markdown_link_errors(mapped))
    errors.extend(_product_import_errors(mapped))
    if scope == "worktree":
        errors.extend(_nested_git_errors())
    return errors


def _migration_history_errors() -> list[str]:
    commits = _git("rev-list", "--reverse", "HEAD", text=True).splitlines()
    if len(commits) < len(MIGRATION_SUBJECTS):
        return [f"migration_commit_count_incomplete:{len(commits)}"]
    errors: list[str] = []
    for index, (commit, expected) in enumerate(zip(commits, MIGRATION_SUBJECTS), start=1):
        subject = _git("show", "-s", "--format=%s", commit, text=True).strip()
        parents = _git("show", "-s", "--format=%P", commit, text=True).split()
        if subject != expected:
            errors.append(f"migration_subject_{index}_invalid:{subject}")
        expected_parents = 0 if index == 1 else 1
        if len(parents) != expected_parents:
            errors.append(f"migration_parent_count_{index}_invalid:{len(parents)}")
    forbidden = {
        "ab2c4b8a374937a8727e414991799dba490db30b",
        "b1bcc94c5cf122a6c6dcff5d007eb6194d47dcc7",
    }
    if forbidden & set(commits):
        errors.append("legacy_history_is_reachable")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scope", choices=("worktree", "index", "staged", "tree", "history"), default="worktree"
    )
    parser.add_argument("--expect-migration-history", action="store_true")
    args = parser.parse_args()
    normalized_scope = "index" if args.scope == "staged" else args.scope
    current = _current_entries(normalized_scope)
    scanned = _history_entries() if normalized_scope == "history" else current
    errors: list[str] = []
    for entry in scanned:
        for code in _path_errors(entry):
            errors.append(f"{code}:{entry.path}")
        for code in _content_errors(entry):
            errors.append(f"{code}:{entry.path}")
    errors.extend(_structural_errors(current, normalized_scope))
    if args.expect_migration_history:
        errors.extend(_migration_history_errors())
    if errors:
        for error in sorted(set(errors)):
            print(f"ERROR {error}")
        print(f"public_repo_check=failed errors={len(set(errors))}")
        return 1
    print(
        f"public_repo_check=passed scope={args.scope} files={len(scanned)} "
        f"max_file_bytes={MAX_FILE_BYTES} public_cases=8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

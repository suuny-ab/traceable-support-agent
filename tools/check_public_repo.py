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


def _structural_errors(entries: list[Entry], scope: str) -> list[str]:
    mapped = _entry_map(entries)
    errors: list[str] = []
    active_prefix = "docs/work/active/"
    active_slugs = {
        PurePosixPath(path).parts[3]
        for path in mapped
        if path.startswith(active_prefix) and len(PurePosixPath(path).parts) >= 5
    }
    if len(active_slugs) != 1:
        errors.append(f"active_increment_count:{len(active_slugs)}")
    elif {
        PurePosixPath(path).name
        for path in mapped
        if path.startswith(f"docs/work/active/{next(iter(active_slugs))}/")
    } != {"spec.md", "plan.md", "result.md", "review.md"}:
        errors.append("active_increment_file_set_invalid")
    try:
        status = _read(mapped, "docs/status.md")
        if active_slugs and f"docs/work/active/{next(iter(active_slugs))}/" not in status:
            errors.append("status_does_not_link_active_increment")
        project = _read(mapped, "PROJECT.md")
        readme = _read(mapped, "README.md")
        public = _read(mapped, "PUBLIC_CONTEXT.md")
        claims = "\n".join((status, project, readme, public)).lower()
        for phrase in ("replay_only", "product/0.1.0", "not_released"):
            if phrase not in claims:
                errors.append(f"required_public_claim_missing:{phrase}")
        if "provider | disabled" not in status.lower() or "zero calls" not in status.lower():
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
        if 'TRACEABLE_PUBLIC_LIVE_ENABLED: "false"' not in compose:
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
        if (
            "requirements-live.lock" not in dockerfile
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

"""Install one CI-built release and perform a recoverable activation rehearsal."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse


COPY_FILES = {
    "release-manifest.json": "release-manifest.json",
    "deploy/compose.production.yaml": "deploy/compose.yaml",
    "deploy/release-lib.sh": "deploy/release-lib.sh",
    "deploy/activate-release.sh": "deploy/activate-release.sh",
    "deploy/rollback-release.sh": "deploy/rollback-release.sh",
    "deploy/switch_release_state.py": "deploy/switch_release_state.py",
    "tools/release_manifest.py": "tools/release_manifest.py",
}
STABLE_ERROR_PATTERN = re.compile(r"[a-z][a-z0-9_]*(?::[a-z][a-z0-9_]*){0,2}")
PUBLIC_SMOKE_TIMEOUT_SECONDS = 15.0
PUBLIC_SMOKE_RETRY_DELAY_SECONDS = 1.0
CURL_PATH = "/usr/bin/curl"
TRANSIENT_CURL_EXIT_CODES = frozenset({5, 6, 7, 16, 18, 28, 52, 55, 56, 92})


class _TransientPublicSmokeError(RuntimeError):
    pass


def _run(*args: str) -> None:
    completed = subprocess.run(
        args,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        for line in reversed((completed.stderr + "\n" + completed.stdout).splitlines()):
            detail = line.strip()
            if STABLE_ERROR_PATTERN.fullmatch(detail):
                raise RuntimeError(detail)
        raise RuntimeError("subprocess_failed")


def _stable_error_code(error: BaseException) -> str:
    detail = str(error).strip()
    if STABLE_ERROR_PATTERN.fullmatch(detail):
        return detail
    if isinstance(error, PermissionError):
        return "filesystem_permission_denied"
    return "unexpected_failure"


def _required_sha(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError("required_receipt_input_missing")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _commit_receipt_or_restore(
    path: Path,
    receipt: dict[str, object],
    restore: Callable[[], None],
    *,
    replace: Callable[[Path, Path], None] = os.replace,
) -> None:
    temporary = path.parent / f".{path.name}.new.{os.getpid()}"
    try:
        temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        restore()
        raise


def _public_smoke(
    origin: str,
    *,
    deadline: float,
    monotonic: Callable[[], float] = time.monotonic,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
    expected_experience: str = "replay_only",
) -> None:
    def request(url: str, *, capture_body: bool = False) -> tuple[int, bytes]:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise _TransientPublicSmokeError("public smoke deadline exhausted")
        command = [
            CURL_PATH,
            "--silent",
            "--show-error",
            "--max-time",
            f"{max(0.001, remaining):.3f}",
            "--user-agent",
            "traceable-release/1",
        ]
        if capture_body:
            command.extend(("--max-filesize", "4096", "--write-out", "\n%{http_code}"))
        else:
            command.extend(("--output", "/dev/null", "--write-out", "%{http_code}"))
        command.append(url)
        try:
            completed = runner(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=remaining,
            )
        except subprocess.TimeoutExpired as error:
            raise _TransientPublicSmokeError("public request timed out") from error
        if monotonic() > deadline:
            raise _TransientPublicSmokeError("public smoke deadline exhausted")
        if completed.returncode in TRANSIENT_CURL_EXIT_CODES:
            raise _TransientPublicSmokeError("public transport not ready")
        if completed.returncode != 0:
            raise RuntimeError("public_smoke_contract_failed")
        try:
            if capture_body:
                body, status_text = completed.stdout.rsplit(b"\n", 1)
            else:
                body, status_text = b"", completed.stdout
            status = int(status_text.decode("ascii"))
        except (UnicodeDecodeError, ValueError):
            raise RuntimeError("public_smoke_contract_failed") from None
        return status, body

    for route in ("/", "/design", "/app", "/privacy"):
        status, _body = request(origin + route)
        if status in {502, 503, 504}:
            raise _TransientPublicSmokeError("public proxy not ready")
        if status != 200:
            raise RuntimeError("public_smoke_contract_failed")
    status, body = request(origin + "/api/v1/health", capture_body=True)
    if status in {502, 503, 504}:
        raise _TransientPublicSmokeError("public proxy not ready")
    if status != 200:
        raise RuntimeError("public_smoke_contract_failed")
    try:
        health = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RuntimeError("public_health_contract_invalid") from None
    if health != {
        "status": "ok",
        "service": "traceable-support-public-api",
        "live_experience": expected_experience,
    }:
        raise RuntimeError("public_health_contract_invalid")


def _wait_public_smoke(
    origin: str,
    *,
    timeout_seconds: float = PUBLIC_SMOKE_TIMEOUT_SECONDS,
    retry_delay_seconds: float = PUBLIC_SMOKE_RETRY_DELAY_SECONDS,
    smoke: Callable[..., None] = _public_smoke,
    monotonic: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> None:
    deadline = monotonic() + timeout_seconds
    while True:
        failure: BaseException
        try:
            smoke(origin, deadline=deadline, monotonic=monotonic)
        except _TransientPublicSmokeError as caught:
            failure = caught
        else:
            if monotonic() > deadline:
                raise RuntimeError("public_smoke_not_ready")
            return
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise RuntimeError("public_smoke_not_ready") from failure
        sleeper(min(retry_delay_seconds, remaining))


def _validated_input(staging: Path) -> str:
    value = json.loads((staging / "deployment-input.json").read_text(encoding="utf-8"))
    if type(value) is not dict or set(value) != {
        "schema_version", "public_origin", "rehearse_rollback"
    }:
        raise RuntimeError("deployment_input_invalid")
    if value["schema_version"] != "traceable-production-target-v1":
        raise RuntimeError("deployment_input_version_invalid")
    origin = urlparse(value["public_origin"])
    if (
        type(value["public_origin"]) is not str
        or origin.scheme != "https"
        or not origin.hostname
        or origin.path not in {"", "/"}
        or origin.query
        or origin.fragment
    ):
        raise RuntimeError("deployment_public_origin_invalid")
    if value["rehearse_rollback"] is not True:
        raise RuntimeError("deployment_rehearsal_required")
    return value["public_origin"].rstrip("/")


def _rehearsal_anchor(release_root: Path, release_dir: Path) -> Path:
    current = release_root / "current"
    if not current.is_symlink():
        raise RuntimeError("rollback_rehearsal_anchor_missing")
    anchor = current.resolve(strict=True)
    if anchor == release_dir and not (release_root / "previous").is_symlink():
        raise RuntimeError("rollback_rehearsal_anchor_missing")
    return anchor


def _prepare_release(staging: Path, release_root: Path, public_origin: str, *, live_enabled: bool = False) -> Path:
    manifest_path = staging / "release-manifest.json"
    _run("python3", str(staging / "tools" / "release_manifest.py"), "--verify", str(manifest_path))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_live = manifest["runtime"]["provider_enabled"] is True
    if manifest_live != live_enabled:
        raise RuntimeError("provider_live_manifest_mismatch")
    api_image = manifest["images"].get("api_live") or manifest["images"]["api_replay"]
    release_dir = release_root / "releases" / manifest["git_sha"]
    if release_dir.exists():
        existing = release_dir / "release-manifest.json"
        if not existing.is_file() or existing.read_bytes() != manifest_path.read_bytes():
            raise RuntimeError("existing_release_identity_conflict")
        return release_dir

    release_dir.mkdir(parents=True, exist_ok=False)
    (release_dir / "deploy").mkdir()
    (release_dir / "tools").mkdir()
    for source_name, target_name in COPY_FILES.items():
        source = staging / source_name
        target = release_dir / target_name
        if not source.is_file():
            raise RuntimeError(f"release_asset_missing:{source_name}")
        shutil.copy2(source, target)
    for script in ("release-lib.sh", "activate-release.sh", "rollback-release.sh"):
        (release_dir / "deploy" / script).chmod(0o755)
    environment = (
        f"WEB_IMAGE={manifest['images']['web']}\n"
        f"API_IMAGE={api_image}\n"
        f"PUBLIC_ORIGIN={public_origin}\n"
        f"TRACEABLE_PUBLIC_LIVE_ENABLED={'true' if live_enabled else 'false'}\n"
    )
    environment_path = release_dir / "release.env"
    environment_path.write_text(environment, encoding="utf-8")
    environment_path.chmod(0o600)
    _run("python3", str(release_dir / "tools" / "release_manifest.py"), "--verify", str(release_dir / "release-manifest.json"))
    return release_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging", type=Path, required=True)
    parser.add_argument("--release-root", type=Path, default=Path("/opt/traceable-support"))
    parser.add_argument(
        "--enable-provider-live",
        action="store_true",
        help="Activate the live Provider experience; requires a v2 live manifest. Default stays replay_only.",
    )
    args = parser.parse_args()
    live_enabled = args.enable_provider_live
    experience = "available" if live_enabled else "replay_only"
    staging = args.staging.resolve()
    release_root = args.release_root.resolve()
    if not staging.is_dir() or not release_root.is_absolute() or release_root == Path(release_root.anchor):
        raise SystemExit("deployment_path_invalid")
    public_origin = _validated_input(staging)
    release_dir = _prepare_release(staging, release_root, public_origin, live_enabled=live_enabled)
    rehearsal_anchor = _rehearsal_anchor(release_root, release_dir)
    host_caddy_sha256 = _required_sha(Path("/etc/caddy/Caddyfile"))
    activate = release_dir / "deploy" / "activate-release.sh"
    rollback = release_dir / "deploy" / "rollback-release.sh"
    steps: list[str] = []

    def activate_and_smoke(label: str) -> None:
        _run("bash", str(activate), str(release_root), str(release_dir))
        try:
            _wait_public_smoke(
                public_origin,
                smoke=lambda origin, *, deadline, monotonic: _public_smoke(
                    origin,
                    deadline=deadline,
                    monotonic=monotonic,
                    expected_experience=experience,
                ),
            )
        except Exception:
            if (release_root / "previous").is_symlink():
                _run("bash", str(rollback), str(release_root))
            raise
        steps.append(label)

    activate_and_smoke("legacy_to_canonical")
    if not (release_root / "previous").is_symlink():
        recovery = rehearsal_anchor / "deploy" / "activate-release.sh"
        _run("bash", str(recovery), str(release_root), str(rehearsal_anchor))
        _wait_public_smoke(public_origin)
        raise RuntimeError("rollback_rehearsal_anchor_not_committed")
    _run("bash", str(rollback), str(release_root))
    _wait_public_smoke(public_origin)
    steps.append("canonical_to_legacy")
    activate_and_smoke("legacy_to_canonical_again")

    receipt = {
        "schema_version": "traceable-deployment-receipt-v1",
        "git_sha": release_dir.name,
        "provider_enabled": live_enabled,
        "public_health": experience,
        "steps": steps,
        "completed_at_unix": int(time.time()),
        "host_caddy_sha256": host_caddy_sha256,
    }

    def restore_legacy_after_receipt_failure() -> None:
        _run("bash", str(rollback), str(release_root))
        _wait_public_smoke(public_origin)

    _commit_receipt_or_restore(
        release_dir / "deployment-receipt.json",
        receipt,
        restore_legacy_after_receipt_failure,
    )
    print(f"release_installed={release_dir.name}")
    print(f"provider_enabled={'true' if live_enabled else 'false'}")
    print("rollback_rehearsal=passed")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except Exception as error:
        print(f"deploy_install_failed:{_stable_error_code(error)}", file=sys.stderr)
        exit_code = 70
    raise SystemExit(exit_code)

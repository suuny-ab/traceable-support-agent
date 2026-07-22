"""Install one CI-built release and perform a recoverable activation rehearsal."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import ssl
import subprocess
import time
import urllib.request
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


def _run(*args: str) -> None:
    subprocess.run(args, check=True)


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


def _public_smoke(origin: str) -> None:
    context = ssl.create_default_context()
    for route in ("/", "/design", "/app", "/privacy"):
        request = urllib.request.Request(origin + route, headers={"User-Agent": "traceable-release/1"})
        with urllib.request.urlopen(request, timeout=15, context=context) as response:
            if response.status != 200:
                raise RuntimeError(f"public_route_invalid:{route}:{response.status}")
            response.read(1024)
    request = urllib.request.Request(
        origin + "/api/v1/health", headers={"Accept": "application/json", "User-Agent": "traceable-release/1"}
    )
    with urllib.request.urlopen(request, timeout=15, context=context) as response:
        health = json.load(response)
    if health != {
        "status": "ok",
        "service": "traceable-support-public-api",
        "live_experience": "replay_only",
    }:
        raise RuntimeError("public_health_contract_invalid")


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


def _prepare_release(staging: Path, release_root: Path, public_origin: str) -> Path:
    manifest_path = staging / "release-manifest.json"
    _run("python3", str(staging / "tools" / "release_manifest.py"), "--verify", str(manifest_path))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
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
        f"API_IMAGE={manifest['images']['api_replay']}\n"
        f"PUBLIC_ORIGIN={public_origin}\n"
        "TRACEABLE_PUBLIC_LIVE_ENABLED=false\n"
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
    args = parser.parse_args()
    staging = args.staging.resolve()
    release_root = args.release_root.resolve()
    if not staging.is_dir() or not release_root.is_absolute() or release_root == Path(release_root.anchor):
        raise SystemExit("deployment_path_invalid")
    public_origin = _validated_input(staging)
    release_dir = _prepare_release(staging, release_root, public_origin)
    rehearsal_anchor = _rehearsal_anchor(release_root, release_dir)
    host_caddy_sha256 = _required_sha(Path("/etc/caddy/Caddyfile"))
    activate = release_dir / "deploy" / "activate-release.sh"
    rollback = release_dir / "deploy" / "rollback-release.sh"
    steps: list[str] = []

    def activate_and_smoke(label: str) -> None:
        _run("bash", str(activate), str(release_root), str(release_dir))
        try:
            _public_smoke(public_origin)
        except Exception:
            if (release_root / "previous").is_symlink():
                _run("bash", str(rollback), str(release_root))
            raise
        steps.append(label)

    activate_and_smoke("legacy_to_canonical")
    if not (release_root / "previous").is_symlink():
        recovery = rehearsal_anchor / "deploy" / "activate-release.sh"
        _run("bash", str(recovery), str(release_root), str(rehearsal_anchor))
        _public_smoke(public_origin)
        raise RuntimeError("rollback_rehearsal_anchor_not_committed")
    _run("bash", str(rollback), str(release_root))
    _public_smoke(public_origin)
    steps.append("canonical_to_legacy")
    activate_and_smoke("legacy_to_canonical_again")

    receipt = {
        "schema_version": "traceable-deployment-receipt-v1",
        "git_sha": release_dir.name,
        "provider_enabled": False,
        "public_health": "replay_only",
        "steps": steps,
        "completed_at_unix": int(time.time()),
        "host_caddy_sha256": host_caddy_sha256,
    }

    def restore_legacy_after_receipt_failure() -> None:
        _run("bash", str(rollback), str(release_root))
        _public_smoke(public_origin)

    _commit_receipt_or_restore(
        release_dir / "deployment-receipt.json",
        receipt,
        restore_legacy_after_receipt_failure,
    )
    print(f"release_installed={release_dir.name}")
    print("provider_enabled=false")
    print("rollback_rehearsal=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

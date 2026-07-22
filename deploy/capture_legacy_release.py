"""Capture the running source-built release as an image-ID rollback anchor.

This is executed once on the server immediately before the first canonical
digest deployment.  It never exports a database, request text or environment
value.  It refuses to proceed unless Provider execution is explicitly off.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse


LEGACY_MAIN = "ab2c4b8a374937a8727e414991799dba490db30b"
LEGACY_WEB = "b1bcc94c5cf122a6c6dcff5d007eb6194d47dcc7"


def _run(*args: str, capture: bool = True) -> str:
    result = subprocess.run(args, check=True, capture_output=capture, text=True)
    return result.stdout.strip() if capture else ""


def _one_container(service: str) -> dict[str, object]:
    ids = _run(
        "docker", "ps",
        "--filter", "label=com.docker.compose.project=traceable-support",
        "--filter", f"label=com.docker.compose.service={service}",
        "--format", "{{.ID}}",
    ).splitlines()
    if len(ids) != 1:
        raise RuntimeError(f"legacy_{service}_container_count_invalid")
    value = json.loads(_run("docker", "inspect", ids[0]))[0]
    if value.get("State", {}).get("Running") is not True:
        raise RuntimeError(f"legacy_{service}_not_running")
    return value


def _environment(container: dict[str, object]) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in container["Config"].get("Env") or []:
        key, separator, value = item.partition("=")
        if separator:
            values[key] = value
    return values


def _binding(container: dict[str, object], port: str, host_port: str) -> None:
    bindings = container["HostConfig"].get("PortBindings", {}).get(port)
    if bindings != [{"HostIp": "127.0.0.1", "HostPort": host_port}]:
        raise RuntimeError(f"legacy_port_binding_invalid:{port}")


def _api_volume(container: dict[str, object]) -> str:
    matches = [
        mount for mount in container.get("Mounts", [])
        if mount.get("Destination") == "/var/lib/traceable" and mount.get("Type") == "volume"
    ]
    if len(matches) != 1 or not re.fullmatch(r"[A-Za-z0-9_.-]+", matches[0].get("Name", "")):
        raise RuntimeError("legacy_api_volume_invalid")
    return matches[0]["Name"]


def _sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _atomic_link(root: Path, name: str, target: Path) -> None:
    temporary = root / f".{name}.new.{os.getpid()}"
    temporary.symlink_to(target, target_is_directory=True)
    os.replace(temporary, root / name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-root", type=Path, default=Path("/opt/traceable-support"))
    parser.add_argument(
        "--production-target",
        type=Path,
        default=Path(__file__).resolve().parent / "production-target.json",
    )
    args = parser.parse_args()
    target_contract = json.loads(args.production_target.read_text(encoding="utf-8"))
    if type(target_contract) is not dict or set(target_contract) != {
        "schema_version", "public_origin", "rehearse_rollback"
    }:
        raise SystemExit("production_target_invalid")
    if (
        target_contract["schema_version"] != "traceable-production-target-v1"
        or target_contract["rehearse_rollback"] is not True
    ):
        raise SystemExit("production_target_invalid")
    public_origin = target_contract["public_origin"]
    origin = urlparse(public_origin) if type(public_origin) is str else None
    if (
        origin is None
        or origin.scheme != "https"
        or not origin.hostname
        or origin.path not in {"", "/"}
        or origin.query
        or origin.fragment
    ):
        raise SystemExit("public_origin_invalid")
    root = args.release_root.resolve()
    if not root.is_absolute() or root == Path(root.anchor):
        raise SystemExit("release_root_invalid")

    web = _one_container("web")
    api = _one_container("api")
    _binding(web, "3000/tcp", "3000")
    _binding(api, "8000/tcp", "8000")
    api_environment = _environment(api)
    if api_environment.get("TRACEABLE_PUBLIC_LIVE_ENABLED", "").lower() != "false":
        raise SystemExit("legacy_provider_switch_not_disabled")
    if api_environment.get("DEEPSEEK_API_KEY"):
        raise SystemExit("legacy_provider_credential_present")

    web_image_id = str(web["Image"])
    api_image_id = str(api["Image"])
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", web_image_id) or not re.fullmatch(
        r"sha256:[0-9a-f]{64}", api_image_id
    ):
        raise SystemExit("legacy_image_id_invalid")
    web_alias = f"traceable-support-legacy-web:{LEGACY_WEB[:12]}"
    api_alias = f"traceable-support-legacy-api:{LEGACY_MAIN[:12]}"
    _run("docker", "image", "tag", web_image_id, web_alias)
    _run("docker", "image", "tag", api_image_id, api_alias)

    release_id = f"legacy-{LEGACY_MAIN[:7]}-{LEGACY_WEB[:7]}"
    target = root / "releases" / release_id
    target.mkdir(parents=True, exist_ok=False)
    (target / "deploy").mkdir()
    volume = _api_volume(api)
    compose = f'''name: traceable-support

services:
  web:
    image: ${{WEB_IMAGE:?}}
    restart: unless-stopped
    init: true
    read_only: true
    tmpfs: [/tmp:rw,noexec,nosuid,size=64m]
    security_opt: [no-new-privileges:true]
    cap_drop: [ALL]
    ports: [127.0.0.1:3000:3000]
  api:
    image: ${{API_IMAGE:?}}
    restart: unless-stopped
    init: true
    read_only: true
    tmpfs: [/tmp:rw,noexec,nosuid,size=64m]
    security_opt: [no-new-privileges:true]
    cap_drop: [ALL]
    environment:
      TRACEABLE_PUBLIC_HOST: 0.0.0.0
      TRACEABLE_PUBLIC_PORT: "8000"
      TRACEABLE_PUBLIC_DB: /var/lib/traceable/public.sqlite3
      TRACEABLE_PUBLIC_ORIGIN: ${{PUBLIC_ORIGIN:?}}
      TRACEABLE_PUBLIC_LIVE_ENABLED: "false"
    volumes: [traceable-data:/var/lib/traceable]
    ports: [127.0.0.1:8000:8000]

volumes:
  traceable-data:
    external: true
    name: {volume}
'''
    (target / "deploy" / "compose.yaml").write_text(compose, encoding="utf-8")
    release_environment = (
        f"WEB_IMAGE={web_alias}\nAPI_IMAGE={api_alias}\nPUBLIC_ORIGIN={public_origin}\n"
        "TRACEABLE_PUBLIC_LIVE_ENABLED=false\n"
    )
    environment_path = target / "release.env"
    environment_path.write_text(release_environment, encoding="utf-8")
    environment_path.chmod(0o600)

    assets = Path(__file__).resolve().parent
    for name in (
        "release-lib.sh",
        "activate-release.sh",
        "rollback-release.sh",
        "switch_release_state.py",
    ):
        shutil.copy2(assets / name, target / "deploy" / name)
        (target / "deploy" / name).chmod(0o755 if name.endswith(".sh") else 0o644)
    current_before = str((root / "current").resolve()) if (root / "current").exists() else None
    manifest = {
        "schema_version": "traceable-legacy-release-v1",
        "legacy_main": LEGACY_MAIN,
        "legacy_web": LEGACY_WEB,
        "provider_enabled": False,
        "web_image_id": web_image_id,
        "api_image_id": api_image_id,
        "web_rollback_alias": web_alias,
        "api_rollback_alias": api_alias,
        "data_volume": volume,
        "public_origin": public_origin,
        "current_before_capture": current_before,
        "host_caddy_sha256": _sha(Path("/etc/caddy/Caddyfile")),
        "server_environment_sha256_before": _sha(root / "server.env"),
    }
    (target / "legacy-release.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _run(
        "docker", "compose", "--project-name", "traceable-support",
        "--env-file", str(environment_path), "-f", str(target / "deploy" / "compose.yaml"),
        "config", "--quiet",
    )
    temporary_environment = root / f".server.env.new.{os.getpid()}"
    temporary_environment.write_text(release_environment, encoding="utf-8")
    temporary_environment.chmod(0o600)
    os.replace(temporary_environment, root / "server.env")
    _atomic_link(root, "current", target)
    print(f"legacy_release_captured={release_id}")
    print("provider_enabled=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

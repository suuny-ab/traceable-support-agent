from __future__ import annotations

import argparse
import contextlib
import ipaddress
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass

try:
    from .validate_deploy_port import normalize_deploy_port
except ImportError:
    from validate_deploy_port import normalize_deploy_port


DNS_LABEL_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?")
DEPLOY_USER_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,31}")
REMOTE_STAGE_PATTERN = re.compile(r"/tmp/traceable-support-[0-9]+-[0-9]+")
PRIVATE_KEY_HEADER_PATTERN = re.compile(
    r"-----BEGIN (?:OPENSSH|RSA|EC) PRIVATE KEY-----"
)
MAX_MULTILINE_SECRET_BYTES = 1024 * 1024
SSH_PATH = "/usr/bin/ssh"
SCP_PATH = "/usr/bin/scp"
SSH_KEYGEN_PATH = "/usr/bin/ssh-keygen"
SENSITIVE_ENVIRONMENT_KEYS = {
    "DEPLOY_HOST",
    "DEPLOY_USER",
    "DEPLOY_PORT",
    "DEPLOY_SSH_KEY",
    "DEPLOY_KNOWN_HOSTS",
    "SSH_AUTH_SOCK",
    "SSH_ASKPASS",
}


class DeployInputError(ValueError):
    pass


class DeployToolError(RuntimeError):
    pass


class DeployTransportError(RuntimeError):
    pass


@dataclass(frozen=True)
class DeployInputs:
    host: str
    user: str
    port: str
    private_key: str
    known_hosts: str


@dataclass(frozen=True)
class PreparedSsh:
    inputs: DeployInputs
    key_file: Path
    known_hosts_file: Path


def _strip_one_bom(value: str) -> str:
    return value[1:] if value.startswith("\ufeff") else value


def _normalize_ascii_scalar(value: str, error: str) -> str:
    normalized = _strip_one_bom(value)
    try:
        normalized.encode("ascii")
    except UnicodeEncodeError as exc:
        raise DeployInputError(error) from exc
    if (
        not normalized
        or normalized != normalized.strip()
        or any(ord(character) < 32 or ord(character) == 127 for character in normalized)
    ):
        raise DeployInputError(error)
    return normalized


def normalize_deploy_host(value: str) -> str:
    host = _normalize_ascii_scalar(value, "deploy_host_invalid")
    try:
        parsed_ip = ipaddress.ip_address(host)
    except ValueError:
        if (
            len(host) > 253
            or host.endswith(".")
            or any(DNS_LABEL_PATTERN.fullmatch(label) is None for label in host.split("."))
        ):
            raise DeployInputError("deploy_host_invalid")
        return host
    if parsed_ip.version != 4:
        raise DeployInputError("deploy_host_invalid")
    return host


def normalize_deploy_user(value: str) -> str:
    user = _normalize_ascii_scalar(value, "deploy_user_invalid")
    if DEPLOY_USER_PATTERN.fullmatch(user) is None or user == "root":
        raise DeployInputError("deploy_user_invalid")
    return user


def normalize_deploy_port_input(value: str) -> str:
    port = _strip_one_bom(value)
    try:
        return normalize_deploy_port(port)
    except ValueError as exc:
        raise DeployInputError("deploy_port_invalid") from exc


def _normalize_multiline_secret(value: str, error: str) -> str:
    normalized = _strip_one_bom(value).replace("\r\n", "\n").replace("\r", "\n")
    if "\x00" in normalized or not normalized.strip():
        raise DeployInputError(error)
    try:
        encoded = normalized.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise DeployInputError(error) from exc
    if len(encoded) > MAX_MULTILINE_SECRET_BYTES:
        raise DeployInputError(error)
    return normalized.rstrip("\n") + "\n"


def normalize_deploy_private_key(value: str) -> str:
    key = _normalize_multiline_secret(value, "deploy_ssh_key_invalid")
    if PRIVATE_KEY_HEADER_PATTERN.search(key) is None:
        raise DeployInputError("deploy_ssh_key_invalid")
    return key


def normalize_deploy_known_hosts(value: str) -> str:
    return _normalize_multiline_secret(value, "deploy_known_hosts_invalid")


def load_deploy_inputs(environment: Mapping[str, str]) -> DeployInputs:
    port_value = environment.get("DEPLOY_PORT", "") or "22"
    return DeployInputs(
        host=normalize_deploy_host(environment.get("DEPLOY_HOST", "")),
        user=normalize_deploy_user(environment.get("DEPLOY_USER", "")),
        port=normalize_deploy_port_input(port_value),
        private_key=normalize_deploy_private_key(environment.get("DEPLOY_SSH_KEY", "")),
        known_hosts=normalize_deploy_known_hosts(environment.get("DEPLOY_KNOWN_HOSTS", "")),
    )


def _require_ssh_tools() -> None:
    if any(
        not Path(tool).is_file() or not os.access(tool, os.X_OK)
        for tool in (SSH_PATH, SCP_PATH, SSH_KEYGEN_PATH)
    ):
        raise DeployToolError("deploy_ssh_tool_missing")


def _subprocess_environment() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if key not in SENSITIVE_ENVIRONMENT_KEYS
    }


def _run_checked(command: Sequence[str], error: str) -> None:
    completed = subprocess.run(
        list(command),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        check=False,
        env=_subprocess_environment(),
    )
    if completed.returncode != 0:
        raise DeployInputError(error)


def _known_host_queries(host: str, port: str) -> tuple[str, ...]:
    bracketed = f"[{host}]:{port}"
    return (host,) if port == "22" else (bracketed,)


def _known_host_match_is_exact(output: bytes, query: str) -> bool:
    for line in output.decode("utf-8", "replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        if fields[0].startswith("@"):
            continue
        host_field = fields[0]
        if host_field.startswith("|1|") or host_field == query:
            return True
    return False


def _write_private_file(path: Path, content: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(content.encode("utf-8"))


@contextlib.contextmanager
def prepare_ssh_inputs(inputs: DeployInputs) -> Iterator[PreparedSsh]:
    _require_ssh_tools()
    with tempfile.TemporaryDirectory(prefix="traceable-deploy-") as temporary:
        directory = Path(temporary)
        os.chmod(directory, 0o700)
        key_file = directory / "deploy-key"
        known_hosts_file = directory / "known-hosts"
        _write_private_file(key_file, inputs.private_key)
        _write_private_file(known_hosts_file, inputs.known_hosts)

        _run_checked(
            (SSH_KEYGEN_PATH, "-y", "-P", "", "-f", str(key_file)),
            "deploy_ssh_key_invalid",
        )
        _run_checked(
            (SSH_KEYGEN_PATH, "-l", "-f", str(known_hosts_file)),
            "deploy_known_hosts_invalid",
        )
        matching_host = False
        for query in _known_host_queries(inputs.host, inputs.port):
            completed = subprocess.run(
                (SSH_KEYGEN_PATH, "-F", query, "-f", str(known_hosts_file)),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                check=False,
                env=_subprocess_environment(),
            )
            if completed.returncode == 0 and _known_host_match_is_exact(
                completed.stdout,
                query,
            ):
                matching_host = True
                break
        if not matching_host:
            raise DeployInputError("deploy_known_hosts_invalid")

        yield PreparedSsh(
            inputs=inputs,
            key_file=key_file,
            known_hosts_file=known_hosts_file,
        )


def _run_transport(command: Sequence[str], stage: str) -> None:
    completed = subprocess.run(
        list(command),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        check=False,
        env=_subprocess_environment(),
    )
    if completed.returncode != 0:
        raise DeployTransportError(f"deploy_ssh_transport_failed:{stage}")


def deploy_release(
    prepared: PreparedSsh,
    staging: Path,
    remote_stage: str,
    release_root: str,
) -> None:
    if (
        not staging.is_dir()
        or REMOTE_STAGE_PATTERN.fullmatch(remote_stage) is None
        or release_root != "/opt/traceable-support"
    ):
        raise DeployInputError("deploy_path_invalid")

    inputs = prepared.inputs
    destination = f"{inputs.user}@{inputs.host}"
    common_options = (
        "-F",
        "/dev/null",
        "-i",
        str(prepared.key_file),
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectionAttempts=1",
        "-o",
        "ConnectTimeout=15",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "GlobalKnownHostsFile=/dev/null",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        f"UserKnownHostsFile={prepared.known_hosts_file}",
    )
    remote_stage_quoted = shlex.quote(remote_stage)
    _run_transport(
        (
            SSH_PATH,
            *common_options,
            "-p",
            inputs.port,
            destination,
            f"mkdir -m 700 {remote_stage_quoted}",
        ),
        "prepare_remote",
    )
    _run_transport(
        (
            SCP_PATH,
            "-r",
            *common_options,
            "-P",
            inputs.port,
            str(staging.resolve()) + "/.",
            f"{destination}:{remote_stage}/",
        ),
        "upload",
    )
    install_script = shlex.quote(f"{remote_stage}/deploy/install_release.py")
    release_root_quoted = shlex.quote(release_root)
    _run_transport(
        (
            SSH_PATH,
            *common_options,
            "-p",
            inputs.port,
            destination,
            (
                f"python3 {install_script} --staging {remote_stage_quoted} "
                f"--release-root {release_root_quoted}"
            ),
        ),
        "activate",
    )


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging", required=True, type=Path)
    parser.add_argument("--remote-stage", required=True)
    parser.add_argument("--release-root", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        inputs = load_deploy_inputs(os.environ)
        with prepare_ssh_inputs(inputs) as prepared:
            deploy_release(
                prepared,
                staging=args.staging,
                remote_stage=args.remote_stage,
                release_root=args.release_root,
            )
    except DeployInputError as exc:
        print(str(exc), file=sys.stderr)
        return 64
    except DeployToolError as exc:
        print(str(exc), file=sys.stderr)
        return 69
    except DeployTransportError as exc:
        print(str(exc), file=sys.stderr)
        return 70
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

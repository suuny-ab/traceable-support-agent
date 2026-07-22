"""Commit release pointers and server.env with in-process compensation.

The application containers are switched before these three metadata paths.  A
partial metadata update would make the public version disagree with the
recorded release, so every ordinary I/O failure restores the exact prior
metadata before returning an error to the shell orchestrator.
"""

from __future__ import annotations

import argparse
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


BeforeReplace = Callable[[str], None]


@dataclass(frozen=True)
class PathState:
    kind: str
    value: str | bytes | None
    mode: int | None = None


def _release(root: Path, candidate: Path, label: str) -> Path:
    resolved = candidate.resolve(strict=True)
    releases = (root / "releases").resolve(strict=True)
    if resolved.parent != releases or not resolved.is_dir():
        raise RuntimeError(f"{label}_outside_release_root")
    return resolved


def _link_state(path: Path, label: str) -> PathState:
    if path.is_symlink():
        return PathState("symlink", os.readlink(path))
    if path.exists():
        raise RuntimeError(f"{label}_not_symlink")
    return PathState("missing", None)


def _file_state(path: Path, label: str) -> PathState:
    if path.is_symlink():
        raise RuntimeError(f"{label}_must_not_be_symlink")
    if not path.exists():
        return PathState("missing", None)
    if not path.is_file():
        raise RuntimeError(f"{label}_not_regular_file")
    return PathState("file", path.read_bytes(), stat.S_IMODE(path.stat().st_mode))


def _temporary(path: Path, suffix: str) -> Path:
    return path.parent / f".{path.name}.{suffix}.{os.getpid()}"


def _prepare_link(path: Path, target: str, suffix: str) -> Path:
    temporary = _temporary(path, suffix)
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(target, target_is_directory=True)
    return temporary


def _prepare_file(path: Path, value: bytes, mode: int, suffix: str) -> Path:
    temporary = _temporary(path, suffix)
    temporary.unlink(missing_ok=True)
    temporary.write_bytes(value)
    temporary.chmod(mode)
    return temporary


def _restore(path: Path, state: PathState, suffix: str) -> None:
    if state.kind == "missing":
        path.unlink(missing_ok=True)
        return
    if state.kind == "symlink":
        temporary = _prepare_link(path, str(state.value), suffix)
    elif state.kind == "file":
        temporary = _prepare_file(path, bytes(state.value), int(state.mode), suffix)
    else:  # pragma: no cover - construction is internal and exhaustive
        raise RuntimeError("release_state_kind_invalid")
    os.replace(temporary, path)


def switch_release_state(
    *,
    release_root: Path,
    current_release: Path,
    previous_release: Path,
    server_environment: Path,
    before_replace: BeforeReplace | None = None,
) -> None:
    root = release_root.resolve(strict=True)
    if root == Path(root.anchor):
        raise RuntimeError("release_root_invalid")
    current_target = _release(root, current_release, "current_release")
    previous_target = _release(root, previous_release, "previous_release")
    if current_target == previous_target:
        raise RuntimeError("release_targets_must_differ")
    environment = server_environment.resolve(strict=True)
    if environment != current_target / "release.env" or not environment.is_file():
        raise RuntimeError("server_environment_source_invalid")
    if stat.S_IMODE(environment.stat().st_mode) != 0o600:
        raise RuntimeError("server_environment_source_mode_invalid")

    destinations = {
        "previous": root / "previous",
        "server.env": root / "server.env",
        "current": root / "current",
    }
    originals = {
        "previous": _link_state(destinations["previous"], "previous"),
        "server.env": _file_state(destinations["server.env"], "server_environment"),
        "current": _link_state(destinations["current"], "current"),
    }
    prepared = {
        "previous": _prepare_link(destinations["previous"], str(previous_target), "desired"),
        "server.env": _prepare_file(
            destinations["server.env"], environment.read_bytes(), 0o600, "desired"
        ),
        "current": _prepare_link(destinations["current"], str(current_target), "desired"),
    }
    changed: list[str] = []
    try:
        for name in ("previous", "server.env", "current"):
            if before_replace is not None:
                before_replace(name)
            os.replace(prepared[name], destinations[name])
            changed.append(name)
    except Exception as commit_error:
        restore_errors: list[str] = []
        for name in reversed(changed):
            try:
                _restore(destinations[name], originals[name], "restore")
            except Exception:
                restore_errors.append(name)
        if restore_errors:
            raise RuntimeError(
                "release_state_compensation_failed:" + ",".join(restore_errors)
            ) from commit_error
        raise RuntimeError("release_state_commit_failed") from commit_error
    finally:
        for temporary in prepared.values():
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--server-env", type=Path, required=True)
    args = parser.parse_args()
    switch_release_state(
        release_root=args.release_root,
        current_release=args.current,
        previous_release=args.previous,
        server_environment=args.server_env,
    )
    print(f"release_state_current={args.current.resolve()}")
    print(f"release_state_previous={args.previous.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import subprocess


GOVERNANCE_EXACT_PATHS = frozenset(
    {
        ".github/pull_request_template.md",
        "AGENTS.md",
        "ROADMAP.md",
        "docs/status.md",
        "docs/engineering/development-flow.md",
        "docs/engineering/github-lifecycle.md",
        "docs/engineering/quality.md",
        "docs/engineering/review.md",
    }
)
GOVERNANCE_PREFIXES = (
    ".github/ISSUE_TEMPLATE/",
    "docs/meta/",
    "docs/work/",
)
UNKNOWN_PATH = "__classification_unknown__"


def normalize_paths(paths: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    normalized: set[str] = set()
    for raw in paths:
        value = raw.strip().replace("\\", "/")
        if not value:
            continue
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            normalized.add(UNKNOWN_PATH)
            continue
        normalized.add(path.as_posix())
    return tuple(sorted(normalized))


def classify_paths(paths: list[str] | tuple[str, ...]) -> str:
    normalized = normalize_paths(paths)
    if not normalized:
        return "runtime"
    if all(
        path in GOVERNANCE_EXACT_PATHS
        or any(path.startswith(prefix) for prefix in GOVERNANCE_PREFIXES)
        for path in normalized
    ):
        return "governance_only"
    return "runtime"


def changed_paths_sha256(paths: list[str] | tuple[str, ...]) -> str:
    normalized = normalize_paths(paths)
    payload = "".join(f"{path}\n" for path in normalized).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def git_changed_paths(base: str, head: str) -> tuple[str, ...]:
    if (
        not base
        or not head
        or set(base) == {"0"}
        or set(head) == {"0"}
    ):
        return (UNKNOWN_PATH,)
    try:
        completed = subprocess.run(
            ["git", "diff", "--name-only", "--no-renames", base, head],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError, UnicodeError):
        return (UNKNOWN_PATH,)
    paths = normalize_paths(tuple(completed.stdout.splitlines()))
    return paths or (UNKNOWN_PATH,)


def write_github_output(path: Path, values: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    paths = git_changed_paths(args.base, args.head)
    values = {
        "classification": classify_paths(paths),
        "changed_paths_sha256": changed_paths_sha256(paths),
        "changed_path_count": str(len(paths)),
    }
    output = args.github_output
    if output is None and os.environ.get("GITHUB_OUTPUT"):
        output = Path(os.environ["GITHUB_OUTPUT"])
    if output is not None:
        write_github_output(output, values)
    for key, value in values.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

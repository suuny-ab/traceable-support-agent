"""Local periodic dependency audit.

Dependency security is deliberately split from the per-PR blocking
path: ``ci-release`` runs the blocking npm audit only when dependency
files change, while this entry point scans the current lockfiles to
catch advisory drift in code that has not changed.

This is a local entry point only. Enabling a scheduled GitHub workflow
for it is an external action that requires explicit user authorization.

Exit code is 0 when every executed scan passes, 1 when any scan fails,
and 2 on usage or environment errors. Failure semantics are tool
specific and must be stated honestly:

- npm audit exits non-zero on advisories at or above the ``high``
  threshold;
- pip-audit has no severity threshold: exit 1 means *any* known
  vulnerability in the pinned versions;
- a non-zero exit can also mean the scan itself failed (registry,
  network or tool environment). ``fail(exit N)`` therefore means "scan
  did not pass"; the scan output is the source of truth for whether
  advisories or an environment error caused it.

Skipped scans (tool not installed) are reported but do not fail the run.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys

REPOSITORY = Path(__file__).resolve().parents[1]

NPM_REGISTRY = "https://registry.npmjs.org"
API_LOCKS = (
    "api/requirements-live.lock",
    "api/requirements-test.lock",
)


@dataclass(frozen=True)
class Scan:
    name: str
    command: tuple[str, ...] | None
    cwd: Path
    skip_reason: str | None = None


def build_scans(root: Path = REPOSITORY) -> list[Scan]:
    scans: list[Scan] = []
    npm = shutil.which("npm")
    if npm is None:
        scans.append(
            Scan("web.npm-audit", None, root / "web", skip_reason="npm 不可用")
        )
    else:
        scans.append(
            Scan(
                "web.npm-audit",
                (npm, "audit", "--audit-level=high", f"--registry={NPM_REGISTRY}"),
                root / "web",
            )
        )
    pip_audit = shutil.which("pip-audit")
    for lock in API_LOCKS:
        name = f"api.pip-audit.{Path(lock).name}"
        if pip_audit is None:
            scans.append(
                Scan(name, None, root, skip_reason="pip-audit 未安装(可选)")
            )
        else:
            # --disable-pip --no-deps: 锁定清单已是完整固定闭包,直接审计固定
            # 版本,不让 pip 重新解析(哈希锁文件与平台标记依赖下重解析会失败)。
            scans.append(
                Scan(
                    name,
                    (
                        pip_audit,
                        "--disable-pip",
                        "--no-deps",
                        "--requirement",
                        str(root / lock),
                    ),
                    root,
                )
            )
    return scans


def run_scans(scans: list[Scan]) -> int:
    failures = 0
    for scan in scans:
        if scan.command is None:
            print(f"dependency_audit {scan.name}: skipped({scan.skip_reason})")
            continue
        completed = subprocess.run(
            list(scan.command), cwd=scan.cwd, check=False
        )
        if completed.returncode == 0:
            print(f"dependency_audit {scan.name}: pass")
        else:
            print(
                f"dependency_audit {scan.name}: fail(exit {completed.returncode})",
                file=sys.stderr,
            )
            failures += 1
    executed = sum(1 for scan in scans if scan.command is not None)
    print(
        f"dependency_audit summary: executed={executed} "
        f"failed={failures} skipped={len(scans) - executed}"
    )
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dependency_audit")
    parser.add_argument(
        "--root",
        type=Path,
        default=REPOSITORY,
        help="仓库根目录(默认:工具所在仓库)",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not (root / "web" / "package-lock.json").exists():
        print(f"dependency_audit_error root_invalid:{root}", file=sys.stderr)
        return 2
    return run_scans(build_scans(root))


if __name__ == "__main__":
    raise SystemExit(main())

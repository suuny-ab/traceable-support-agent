"""Find stale current-state language in the living documentation set.

The gardener is intentionally read-only: it reads canonical facts from
``PROJECT.md`` and ``docs/status.md`` and prints a deterministic report.  A
finding does not fail the process unless an explicit ``--fail-on`` policy is
requested, so the default CI hook remains advisory.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
LIVING_EXACT = {
    "README.md",
    "PUBLIC_CONTEXT.md",
    "ROADMAP.md",
    "docs/work/README.md",
}
LIVING_PREFIXES = ("docs/engineering/", "docs/product/")
HISTORICAL_DOCS = {"docs/engineering/migration-record.md"}
CURRENT_MARKERS = ("当前", "目前", "现在", "现行")
HISTORICAL_MARKERS = (
    "历史",
    "当时",
    "对应提交",
    "迁移收口前",
    "第一次",
    "首次",
    "录制于",
    "PR #",
    "回执",
)
SAFE_REPLAY_CONTEXT = ("本地", "CI", "候选", "回放", "默认", "历史", "迁移", "对应提交")
RELEASE_SHA_RE = re.compile(r"release_sha\s*=\s*`?([0-9a-f]{7,40})(?:…|\.\.\.)?", re.IGNORECASE)


@dataclass(frozen=True)
class CanonicalFacts:
    release_sha: str
    live_experience: str
    product_release: str
    state: str


@dataclass(frozen=True)
class Finding:
    level: str
    rule_id: str
    path: str
    line: int
    message: str


@dataclass(frozen=True)
class GardenerReport:
    canonical: CanonicalFacts
    scanned_files: int
    findings: tuple[Finding, ...]

    @property
    def stale_count(self) -> int:
        return sum(finding.level == "stale" for finding in self.findings)

    @property
    def review_count(self) -> int:
        return sum(finding.level == "review" for finding in self.findings)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_canonical_facts(root: Path) -> CanonicalFacts:
    project = _read(root / "PROJECT.md")
    status = _read(root / "docs/status.md")
    release_match = re.search(r"release_sha=([0-9a-f]{40})", status)
    live_match = re.search(r"live_experience=(available|replay_only)", status)
    state_match = re.search(r"\| `state` \| `([^`]+)` \|", status)
    if not release_match:
        raise ValueError("canonical_release_sha_missing")
    if not live_match:
        raise ValueError("canonical_live_experience_missing")
    if not state_match:
        raise ValueError("canonical_state_missing")
    if "`product/0.1.0` 未发布" in project or "`product/0.1.0`：`not_released`" in project:
        product_release = "not_released"
    else:
        raise ValueError("canonical_product_release_missing")
    return CanonicalFacts(
        release_sha=release_match.group(1),
        live_experience=live_match.group(1),
        product_release=product_release,
        state=state_match.group(1),
    )


def living_markdown_paths(root: Path) -> tuple[Path, ...]:
    paths: list[Path] = []
    for path in root.rglob("*.md"):
        relative = PurePosixPath(path.relative_to(root).as_posix()).as_posix()
        if relative in LIVING_EXACT or relative.startswith(LIVING_PREFIXES):
            paths.append(path)
    return tuple(sorted(paths, key=lambda path: path.relative_to(root).as_posix()))


def _has_historical_anchor(line: str) -> bool:
    return any(marker in line for marker in HISTORICAL_MARKERS) or bool(
        re.search(r"20\d{2}-\d{2}-\d{2}", line)
    )


def _line_findings(
    relative: str,
    line_number: int,
    line: str,
    facts: CanonicalFacts,
    project: str,
) -> Iterable[Finding]:
    historical = _has_historical_anchor(line)
    for match in RELEASE_SHA_RE.finditer(line):
        observed = match.group(1).lower()
        if not historical and not facts.release_sha.startswith(observed):
            yield Finding(
                "stale",
                "stale_release_sha",
                relative,
                line_number,
                f"release_sha {observed} does not match current {facts.release_sha}",
            )

    public_replay_claim = (
        "replay_only" in line
        and re.search(r"(?:当前|目前|现在|现行).{0,24}(?:公网|生产)|(?:公网|生产).{0,24}(?:当前|目前|现在|保持)", line)
    )
    if (
        public_replay_claim
        and facts.live_experience == "available"
        and not historical
        and not any(marker in line for marker in SAFE_REPLAY_CONTEXT)
    ):
        yield Finding(
            "stale",
            "stale_public_live_mode",
            relative,
            line_number,
            "current production is available, but this line presents replay_only as current public mode",
        )

    completed_showcase = "完成整体信息层级打磨并通过用户验收" in project
    if (
        relative == "PUBLIC_CONTEXT.md"
        and completed_showcase
        and "最终视觉" in line
        and "后续" in line
    ):
        yield Finding(
            "stale",
            "delivered_work_described_as_future",
            relative,
            line_number,
            "PROJECT.md records the public showcase as delivered, but this line still calls it future work",
        )

    if (
        relative in HISTORICAL_DOCS
        and any(marker in line for marker in CURRENT_MARKERS)
        and not historical
        and "不代表当前" not in line
        and "docs/status.md" not in line
        and "状态文件" not in line
    ):
        yield Finding(
            "review",
            "ambiguous_current_in_historical_doc",
            relative,
            line_number,
            "historical document uses a relative current-state marker without an explicit time anchor",
        )


def scan(root: Path = ROOT) -> GardenerReport:
    facts = load_canonical_facts(root)
    project = _read(root / "PROJECT.md")
    paths = living_markdown_paths(root)
    findings: list[Finding] = []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        for line_number, line in enumerate(_read(path).splitlines(), start=1):
            findings.extend(_line_findings(relative, line_number, line, facts, project))
    findings.sort(key=lambda finding: (finding.level, finding.path, finding.line, finding.rule_id))
    return GardenerReport(facts, len(paths), tuple(findings))


def render_markdown(report: GardenerReport) -> str:
    lines = [
        "# 文档园丁扫描",
        "",
        f"- canonical release_sha: `{report.canonical.release_sha}`",
        f"- canonical live_experience: `{report.canonical.live_experience}`",
        f"- canonical product release: `{report.canonical.product_release}`",
        f"- canonical state: `{report.canonical.state}`",
        f"- scanned files: `{report.scanned_files}`",
        f"- findings: stale `{report.stale_count}` / review `{report.review_count}`",
        "",
    ]
    if not report.findings:
        lines.append("没有发现腐坏或待人工判断项。")
    else:
        lines.extend(
            (
                "| 级别 | 规则 | 位置 | 说明 |",
                "| --- | --- | --- | --- |",
            )
        )
        for finding in report.findings:
            lines.append(
                f"| `{finding.level}` | `{finding.rule_id}` | "
                f"`{finding.path}:{finding.line}` | {finding.message} |"
            )
    return "\n".join(lines) + "\n"


def render_json(report: GardenerReport) -> str:
    payload = {
        "canonical": asdict(report.canonical),
        "scanned_files": report.scanned_files,
        "summary": {"stale": report.stale_count, "review": report.review_count},
        "findings": [asdict(finding) for finding in report.findings],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--fail-on", choices=("none", "stale", "review", "any"), default="none")
    args = parser.parse_args()
    try:
        report = scan(args.root.resolve())
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"doc_gardener=failed error={exc}")
        return 2
    print(render_json(report) if args.format == "json" else render_markdown(report), end="")
    should_fail = (
        (args.fail_on == "stale" and report.stale_count > 0)
        or (args.fail_on == "review" and report.review_count > 0)
        or (args.fail_on == "any" and bool(report.findings))
    )
    if args.format == "markdown":
        print(
            f"doc_gardener=completed stale={report.stale_count} "
            f"review={report.review_count} advisory={str(args.fail_on == 'none').lower()}"
        )
    return 1 if should_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())

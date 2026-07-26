"""CI proof contract runner.

Every meaningful CI step is bound to a stated claim and a failure
attribution category:

- ``product``: the candidate diff broke a product contract. Fix the diff.
- ``boundary``: a governance / public-safety / security gate stopped the
  run. Fix the content or revert; never weaken the gate to make it pass.
- ``external``: a third-party fetch, registry or advisory failed. The
  candidate diff is not the cause; retry or wait.

``run`` prints a ``ci_check`` attribution line before the command
starts, appends a JSONL proof entry and, on failure, prints the
category, claim and remediation pointer. ``record`` lets a multi-line
shell step report its own exit code with the same attribution.
``skip`` records intentionally skipped checks so a green job never
silently means "everything passed". ``summary`` renders the JSONL
entries into a Markdown table for the GitHub job summary, listing
expected checks that never ran as 未执行, and exits non-zero when any
expected claim is missing so a green required check can never silently
cover a check that did not run.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

SCHEMA_VERSION = "ci-proof-v1"

CATEGORIES = ("product", "boundary", "external")

QUALITY_DOC = "docs/engineering/quality.md"

# Claim id -> (statement, honest boundary, remediation pointer).
CLAIMS: dict[str, tuple[str, str, str]] = {
    "governance.public-repo-hygiene": (
        "公开树与全历史不含密钥、本机路径、私有 HOLDOUT、归档或超限文件",
        "不证明提交者本机未泄露，只证明 Git 内容干净",
        QUALITY_DOC,
    ),
    "governance.tooling": (
        "治理、发布与评测工具按自身单元测试工作",
        "只证明工具声明的机械合同，不证明产品行为",
        QUALITY_DOC,
    ),
    "governance.whitespace": (
        "全部受跟踪内容无空白符错误",
        "纯格式门",
        QUALITY_DOC,
    ),
    "governance.release-decision": (
        "发布决定以不可变身份生成并可重放验证",
        "只绑定本次运行的 SHA 与分类，不授权部署",
        "docs/engineering/operations.md",
    ),
    "web.dependencies": (
        "Web 锁定依赖可按 lockfile 干净安装",
        "registry 与网络失败属外部依赖；package.json 与 lockfile 不一致等候选修改同样在此失败",
        "先核对 diff 是否触及依赖清单；未触及则按外部依赖重试",
    ),
    "web.dependency-advisory": (
        "依赖文件变化时，Web 依赖无 high 及以上已知漏洞",
        "只在依赖文件变化的候选上阻塞；未改代码时的漂移由定期审计发现",
        "更新依赖或在 PR 中说明例外；不得为通过而降级门",
    ),
    "web.static-contract": (
        "Web 通过 ESLint 与 TypeScript 检查",
        "不证明运行时行为",
        QUALITY_DOC,
    ),
    "web.build-and-tests": (
        "Web 生产构建成功且单元 / 协议 / 视觉合同测试通过",
        "构建与测试在 runner 内证明，不构成线上可用性主张",
        QUALITY_DOC,
    ),
    "web.routes": (
        "/、/design、/app、/privacy 返回 200 且渲染真实页面内容",
        "不证明最终视觉完成",
        QUALITY_DOC,
    ),
    "api.dependencies": (
        "API 测试与离线 live 依赖可按锁定清单安装",
        "PyPI 与网络失败属外部依赖；错误哈希或不一致锁定清单等候选修改同样在此失败",
        "先核对 diff 是否触及依赖清单；未触及则按外部依赖重试",
    ),
    "api.model-download": (
        "固定的 BGE 嵌入模型可从白名单来源下载并通过字节校验",
        "模型来源失败属外部依赖；候选修改模型清单同样在此失败",
        "先核对 diff 是否触及模型清单；未触及则按外部依赖重试",
    ),
    "api.dependency-advisory": (
        "依赖文件变化时，API 锁定依赖无已知漏洞",
        "pip-audit 无严重度阈值，退出 1 表示任意已知漏洞；扫描环境错误以输出为准",
        "更新依赖或在 PR 中说明例外；不得为通过而降级门",
    ),
    "api.audit-tool-install": (
        "候选级 API 依赖审计使用钉定的 pip-audit 版本",
        "pipx 与 PyPI 属外部依赖，安装失败不归因于候选 diff",
        "重试运行；持续失败时检查 PyPI 状态",
    ),
    "api.product-tests": (
        "公开 API、产品链、预算、SQLite、来源与生成前边界测试通过",
        "使用固定本地模型，不构成真实 Provider 质量主张",
        QUALITY_DOC,
    ),
    "api.eval-runner-tests": (
        "Stage 12 评测 runner 与冻结检查工具按自身测试工作",
        "只证明评测工具，不重跑未见集，不产生新的质量主张",
        "docs/engineering/evaluation.md",
    ),
    "api.replay-assembly-boundary": (
        "回放控制面在无模型、无 live 依赖、无凭据时可装配",
        "证明失败关闭的打包边界，不证明实时链路",
        QUALITY_DOC,
    ),
    "containers.image-build": (
        "Web 与回放 / live API 镜像可构建",
        "基础镜像拉取失败属外部依赖；构建断点失败归候选 diff",
        "日志中 pull / network 错误按外部依赖重试，其余按产品修复",
    ),
    "containers.replay-smoke": (
        "镜像以内置非 root 用户运行；只读、降权、无网络的回放容器可启动，健康为 replay_only，四页可达",
        "不证明生产高可用或 SLA",
        QUALITY_DOC,
    ),
    "containers.offline-live": (
        "live target 在禁用网络下通过离线检索检查，不产生 Provider 调用",
        "证明装配与失败边界，不证明语言质量",
        QUALITY_DOC,
    ),
}

CATEGORY_GUIDANCE = {
    "product": "产品合同步骤失败：默认归候选 diff，修复后重推；处理入口会标明例外（如基础镜像拉取属外部依赖）。",
    "boundary": "治理 / 公开安全 / 依赖安全门停止：修正内容或回退，不得为通过而放松门。",
    "external": "外部获取类步骤失败：先核对候选 diff 是否触及该步骤输入（依赖清单、模型清单）；未触及则重试或等待外部恢复。",
}


class ProofError(ValueError):
    pass


def require_claim(claim: str) -> tuple[str, str, str]:
    try:
        return CLAIMS[claim]
    except KeyError:
        known = ", ".join(sorted(CLAIMS))
        raise ProofError(f"unknown_claim:{claim}; known: {known}") from None


def require_category(category: str) -> str:
    if category not in CATEGORIES:
        raise ProofError(f"unknown_category:{category}")
    return category


def append_entry(proof: Path, entry: dict[str, object]) -> None:
    proof.parent.mkdir(parents=True, exist_ok=True)
    with proof.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def load_entries(proof: Path) -> list[dict[str, object]]:
    if not proof.exists():
        return []
    entries: list[dict[str, object]] = []
    for line_number, line in enumerate(
        proof.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProofError(f"proof_entry_invalid:line {line_number}") from exc
        if not isinstance(entry, dict) or "claim" not in entry or "status" not in entry:
            raise ProofError(f"proof_entry_invalid:line {line_number}")
        entries.append(entry)
    return entries


def report_failure(claim: str, category: str, exit_code: int) -> None:
    statement, _boundary, remediation = require_claim(claim)
    print(
        f"ci_failure category={category} claim={claim} exit={exit_code}",
        file=sys.stderr,
    )
    print(f"主张: {statement}", file=sys.stderr)
    print(f"归因: {CATEGORY_GUIDANCE[category]}", file=sys.stderr)
    print(f"处理入口: {remediation}", file=sys.stderr)
    print(
        f"::error title=ci[{category}] {claim}::{statement} — {remediation}",
        file=sys.stderr,
    )


def run_command(
    claim: str,
    category: str,
    proof: Path,
    command: list[str],
) -> int:
    statement, _boundary, _remediation = require_claim(claim)
    require_category(category)
    if not command:
        raise ProofError("missing_command")
    print(f"ci_check claim={claim} category={category}: {statement}", flush=True)
    started = time.monotonic()
    completed = subprocess.run(command, check=False)
    duration = round(time.monotonic() - started, 3)
    append_entry(
        proof,
        {
            "schema_version": SCHEMA_VERSION,
            "claim": claim,
            "category": category,
            "command": command,
            "status": "pass" if completed.returncode == 0 else "fail",
            "exit_code": completed.returncode,
            "duration_s": duration,
        },
    )
    if completed.returncode != 0:
        report_failure(claim, category, completed.returncode)
    return completed.returncode


def record_result(
    claim: str,
    category: str,
    exit_code: int,
    proof: Path,
) -> int:
    require_claim(claim)
    require_category(category)
    append_entry(
        proof,
        {
            "schema_version": SCHEMA_VERSION,
            "claim": claim,
            "category": category,
            "command": [],
            "status": "pass" if exit_code == 0 else "fail",
            "exit_code": exit_code,
        },
    )
    if exit_code != 0:
        report_failure(claim, category, exit_code)
    return exit_code


def record_skip(claims: list[str], proof: Path, reason: str) -> int:
    if not reason:
        raise ProofError("missing_skip_reason")
    for claim in claims:
        require_claim(claim)
        append_entry(
            proof,
            {
                "schema_version": SCHEMA_VERSION,
                "claim": claim,
                "category": "skipped",
                "command": [],
                "status": "skipped",
                "reason": reason,
            },
        )
    return 0


STATUS_LABEL = {"pass": "通过", "fail": "失败", "skipped": "跳过", "missing": "未执行"}


def missing_expected(
    entries: list[dict[str, object]], expected: list[str]
) -> list[str]:
    recorded = {str(entry["claim"]) for entry in entries}
    return [claim for claim in expected if claim not in recorded]


def render_summary(
    job: str,
    entries: list[dict[str, object]],
    expected: list[str] | None = None,
) -> str:
    lines = [f"## CI 证明合同 — {job}", ""]
    if not entries and not expected:
        lines.append("未记录任何证明条目：job 在合同检查执行前失败。")
        lines.append("")
        lines.append("归因：查看最早失败的 step（检出、分类或环境准备）。")
        return "\n".join(lines)
    recorded = {str(entry["claim"]) for entry in entries}
    rows = list(entries)
    for claim in expected or []:
        require_claim(claim)
        if claim not in recorded:
            rows.append(
                {
                    "claim": claim,
                    "category": "—",
                    "status": "missing",
                    "reason": "job 在此之前失败或被中断",
                }
            )
    lines.append("| Check | 主张 | 归因类别 | 结果 | 诚实边界 / 处理入口 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for entry in rows:
        claim = str(entry["claim"])
        statement, boundary, remediation = CLAIMS.get(
            claim, ("(未登记主张)", "", QUALITY_DOC)
        )
        status = str(entry["status"])
        category = str(entry.get("category", ""))
        if status == "skipped":
            category = "—"
            note = f"故意跳过：{entry.get('reason', '')}"
        elif status == "missing":
            category = "—"
            note = str(entry.get("reason", ""))
        elif status == "fail":
            note = remediation
        else:
            note = boundary
        lines.append(
            f"| `{claim}` | {statement} | {category} | "
            f"{STATUS_LABEL.get(status, status)} | {note} |"
        )
    passed = sum(1 for entry in rows if entry["status"] == "pass")
    failed = sum(1 for entry in rows if entry["status"] == "fail")
    skipped = sum(1 for entry in rows if entry["status"] == "skipped")
    missing = sum(1 for entry in rows if entry["status"] == "missing")
    lines.append("")
    lines.append(
        f"job={job} 证明={passed} 失败={failed} 跳过={skipped} 未执行={missing}。"
        "通过只证明上表明确声明的主张；跳过与未执行表示该检查本次没有证明任何东西。"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ci_proof")
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--claim", required=True)
    run_parser.add_argument("--category", required=True)
    run_parser.add_argument("--proof", type=Path, required=True)
    run_parser.add_argument("command", nargs=argparse.REMAINDER)

    skip_parser = subparsers.add_parser("skip")
    skip_parser.add_argument("--claim", action="append", required=True)
    skip_parser.add_argument("--reason", required=True)
    skip_parser.add_argument("--proof", type=Path, required=True)

    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("--claim", required=True)
    record_parser.add_argument("--category", required=True)
    record_parser.add_argument("--exit-code", type=int, required=True)
    record_parser.add_argument("--proof", type=Path, required=True)

    summary_parser = subparsers.add_parser("summary")
    summary_parser.add_argument("--job", required=True)
    summary_parser.add_argument("--proof", type=Path, required=True)
    summary_parser.add_argument("--step-summary", type=Path)
    summary_parser.add_argument("--expect", action="append", default=[])

    list_parser = subparsers.add_parser("claims")
    list_parser.add_argument("--step-summary", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command_name == "run":
            command = list(args.command)
            if command and command[0] == "--":
                command = command[1:]
            return run_command(args.claim, args.category, args.proof, command)
        if args.command_name == "skip":
            return record_skip(args.claim, args.proof, args.reason)
        if args.command_name == "record":
            return record_result(args.claim, args.category, args.exit_code, args.proof)
        if args.command_name == "summary":
            entries = load_entries(args.proof)
            text = render_summary(args.job, entries, args.expect)
            print(text)
            if args.step_summary is not None:
                with args.step_summary.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(text + "\n")
            missing = missing_expected(entries, args.expect)
            if missing:
                print(
                    "ci_failure category=product claim=proof-summary "
                    f"exit=1 missing={','.join(missing)}",
                    file=sys.stderr,
                )
                print(
                    "归因: 期望的检查未执行却得到绿灯是失败关闭违反;"
                    "检查步骤条件或步骤遗漏。",
                    file=sys.stderr,
                )
                return 1
            return 0
        text = "\n".join(
            f"{claim}: {CLAIMS[claim][0]}" for claim in sorted(CLAIMS)
        )
        print(text)
        return 0
    except ProofError as exc:
        print(f"ci_proof_error {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

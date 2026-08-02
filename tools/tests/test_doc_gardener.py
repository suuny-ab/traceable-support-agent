from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.doc_gardener import render_json, render_markdown, scan


PROJECT = """# 项目事实

- 当前能力已完成整体信息层级打磨并通过用户验收。
- `product/0.1.0` 未发布。
"""

STATUS = """# 当前开发状态

| `state` | `ready` |
| 运行产品 | `live_experience=available`、`release_sha=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` |
"""


class DocGardenerTest(unittest.TestCase):
    def build_root(self, files: dict[str, str]) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        base = {"PROJECT.md": PROJECT, "docs/status.md": STATUS, **files}
        for relative, content in base.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return root

    def test_stale_release_and_delivered_future_are_machine_findings(self) -> None:
        root = self.build_root(
            {
                "README.md": "当前证据 `release_sha=bbbbbbb…` 公网可验。\n",
                "PUBLIC_CONTEXT.md": "- 最终视觉与仓库展示属于后续独立工作。\n",
            }
        )
        report = scan(root)
        self.assertEqual(report.stale_count, 2)
        self.assertEqual(
            {finding.rule_id for finding in report.findings},
            {"stale_release_sha", "delivered_work_described_as_future"},
        )

    def test_replay_context_and_historical_sha_are_not_false_positives(self) -> None:
        root = self.build_root(
            {
                "README.md": "本地默认保持 `replay_only`。\n",
                "docs/engineering/migration-record.md": (
                    "- PR #10 的 `release_sha=bbbbbbb` 是历史回执。\n"
                    "- 现行版本见状态文件。\n"
                ),
            }
        )
        report = scan(root)
        self.assertEqual(report.stale_count, 0)
        self.assertEqual(report.review_count, 0)

    def test_ambiguous_current_in_historical_doc_is_review_only(self) -> None:
        root = self.build_root(
            {
                "docs/engineering/migration-record.md": "纳入当前产品合同。\n",
            }
        )
        report = scan(root)
        self.assertEqual(report.stale_count, 0)
        self.assertEqual(report.review_count, 1)
        self.assertIn("review", render_markdown(report))

    def test_report_is_deterministic_and_default_workflow_hook_is_advisory(self) -> None:
        root = self.build_root(
            {
                "README.md": "`release_sha=bbbbbbb…`\n",
                "docs/product/limitations.md": "当前真实 Provider live 已启用。\n",
            }
        )
        self.assertEqual(render_markdown(scan(root)), render_markdown(scan(root)))
        self.assertEqual(json.loads(render_json(scan(root)))["summary"]["stale"], 1)

        repository = Path(__file__).resolve().parents[2]
        workflow = (repository / ".github/workflows/ci-release.yml").read_text(encoding="utf-8")
        self.assertIn("Run advisory document gardener", workflow)
        self.assertIn("python tools/doc_gardener.py --format markdown", workflow)
        self.assertIn("continue-on-error: true", workflow)


if __name__ == "__main__":
    unittest.main()

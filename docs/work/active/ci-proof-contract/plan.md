# 实施计划

1. 建立工作记录并把 `docs/status.md` 切换为 `developing`。
2. 实现 `tools/ci_proof.py`(主张登记、`run` 包装、`summary` 渲染)与
   `tools/tests/test_ci_proof.py`。
3. 扩展 `tools/ci_impact.py` 输出 `dependency_files_changed`,补 `test_ci_impact.py` 用例。
4. 改造 `.github/workflows/ci-release.yml`:
   - 关键断言步骤经 `ci_proof.py run` 包装,绑定主张与归因类别;
   - 外部获取步骤(npm ci、pip install、模型下载)归为 `external`;
   - npm audit 移到 `dependency_files_changed == 'true'` 时执行,归为 `boundary`;
   - 每个 job 末尾 `if: always()` 渲染 proof 摘要;`governance_only` 时摘要显式列出 skipped;
   - Web 路由冒烟补页面内容断言。
5. 实现 `tools/dependency_audit.py`(本地定期审计:npm audit 必跑,pip-audit 存在则跑),
   并在 quality.md 登记入口与语义。
6. 更新 `docs/engineering/quality.md`(证明合同、归因类别、审计分层)。
7. 本地验证:tools 全部单测、公开仓库扫描、workflow YAML 解析、proof 三类归因本地模拟。
8. 写 `result.md` / `review.md`,本地提交,报告。

停止条件:任何步骤需要改动产品运行代码、放松公开安全扫描、或绕过既有发布门时,停止并
升级给用户。

# 结果

> 状态：实施完成，本地验证通过；未推送、未建 PR、未在 GitHub 启用任何新行为。

## 实际交付

- `tools/ci_proof.py`：CI 证明合同运行器。登记 17 条主张(claim),每条含主张文本、
  诚实边界和处理入口;`run` 包装单命令、`record` 回传多行 shell 步骤结果、`skip`
  记录故意跳过、`summary` 渲染 Job Summary 表。失败时在命令输出前打印归因类别
  (`product` / `boundary` / `external`)、主张和处理入口,并发出 `::error` 注解。
- `tools/ci_impact.py`:新增 `dependency_files_changed` 输出,检测
  `web/package.json`、`web/package-lock.json` 与 `api/requirements-*.txt/.lock`;
  未知或无法分类路径失败关闭为 `true`(审计照跑)。
- `.github/workflows/ci-release.yml`:
  - 四个 job 的关键步骤全部绑定主张与归因类别;外部获取(npm ci、pip install、
    模型下载)归为 `external`,治理 / 公开安全 / 依赖审计归为 `boundary`;
  - `npm audit --audit-level=high` 只在 `dependency_files_changed == 'true'` 时
    阻塞执行,依赖未变化时记录“故意跳过: dependencies_unchanged”;
  - `governance_only` 变更下三个运行时 job 记录全部检查的“故意跳过: governance_only”;
  - 每个 job 末尾 `if: always()` 渲染证明摘要:通过 / 失败 / 跳过 / 未执行四类状态
    显式列出,未执行表示该检查本次没有证明任何东西;
  - Web 路由冒烟从仅断言 HTTP 200 升级为断言 `<html lang="zh-CN">` 页面标记和
    首页 H1 文案;容器冒烟改用状态累积 + 显式 `exit "$status"`,失败点输出稳定
    echo 码。
- `tools/dependency_audit.py`:本地定期依赖审计入口;`web/` npm audit 必跑,
  `pip-audit` 存在时对两份 API 锁定清单扫描;工具缺失记 skipped 不影响退出码,
  任一扫描发现 high+ advisory 退出码为 1。未在 GitHub 启用定时运行。
- `tools/check_public_repo.py`:容器冒烟钉定合同与 job 元数据更新为新脚本
  (含 `env:` 与 proof 记录行);`governance_only` 成功语义钉定从旧步骤名
  “Report governance-only impact” 更新为 “Record skipped runtime checks
  (governance-only change)”。钉定强度不变:任何对冒烟边界、就绪超时、路由
  检查或 proof 记录行的篡改仍失败关闭。
- `docs/engineering/quality.md`:新增“CI 证明合同与失败归因”一节;Web 本地检查
  移除常驻 npm audit,登记依赖审计分层与本地入口。
- `docs/status.md`:切换为 `developing`,链接本增量。

## 验证

- `python -m unittest discover -s tools/tests -p "test_*.py"`:全部通过(含新增
  ci_proof 14 例、ci_impact 依赖检测 1 例、dependency_audit 4 例,容器冒烟夹具与
  15 个变异全部按预期拒绝)。
- `python tools/check_public_repo.py --scope worktree`:通过。
- 两个 workflow YAML 均解析有效;全部 30 个 run 块通过 `bash -n` 语法检查;workflow
  引用的主张与登记册完全一致(无未知、无未用)。
- Fast 层:`test_package_boundaries.py`、`test_public_api.py`、`test_provider_usage.py`
  通过;`git diff --check HEAD` 无空白符问题。
- 本地模拟 `ci_proof.py run / record / skip / summary`:三类归因输出、JSONL 记录、
  Markdown 摘要(含未执行列出)符合预期。
- `test_stage12_eval.py` 与 `test_generation_contract_probe.py` 在本机报
  `embedding_model_file_inventory_invalid` 共 14 个 error;在基线提交上 stash 复测
  结果完全相同,确认是本 worktree 无本地模型的既有环境条件,与本增量无关(CI 中
  这些测试由 api job 带模型执行,与本增量的 workflow 改动路径一致)。

## 证据边界

- 本地验证证明工具行为、扫描器钉定和 YAML 有效性;不证明 GitHub Actions 上的真实
  运行结果(本轮不授权推送 / 重跑,workflow 变更尚未在 runner 上执行过)。
- `python3` 在 ubuntu-24.04 runner 基础镜像上可用是既有假设(原 containers job 已在
  无 setup-python 的情况下使用 `python`);首次真实运行若缺 `python3` 会在摘要步骤
  失败,归因清楚。
- 容器冒烟的 base image 拉取失败仍归 `containers.image-build`(product),其处理入口
  注明 pull / network 错误按外部依赖处理;自动区分需要预拉取步骤,本轮未实现。
- 定时冒烟的固定等待循环保持不变,flake 风险未被消除,只是失败时归因可读。

## 仍未解决

- GitHub 侧定期依赖审计 workflow 未启用(需用户授权的外部动作)。
- required checks 名称与分支保护未动;新摘要只对点进 run 的读者可见,Checks 列表
  本身不变。
- README 无 CI 状态入口(与 Issue #29 重叠,留给用户决定)。
- 四个 job 的分类 shell 片段仍重复(低优先级)。
- 变更在真实 runner 上未验证,首次 CI 运行可能暴露 runner 环境差异。

## 2026-07-26 续:定期审计接入 GitHub

用户授权后追加交付:

- `.github/workflows/dependency-audit.yml`:每周一 07:43 UTC 定期依赖审计
  (schedule 只在默认分支 `main` 运行;分支与 PR 只能 `workflow_dispatch` 手动
  触发),`pipx` 安装钉定的 `pip-audit==2.10.1` 后运行 `tools/dependency_audit.py`,
  完整输出写入 Job Summary,发现 high+ advisory 时 run 变红。
- `tools/dependency_audit.py`:pip 侧改为 `--disable-pip --no-deps`,直接审计锁定
  清单的固定版本;已在本机 venv(pip-audit 2.10.1)中对两份锁文件实测通过——
  原 `--requirement` 直跑会让 pip 重新解析并在哈希锁文件 + 平台标记依赖下失败。

追加验证:新 workflow YAML 解析有效、run 块通过 `bash -n`、`check_public_repo.py
--scope worktree` 通过、dependency_audit 单测更新后全绿、本机完整跑通
npm + pip 三路扫描(退出码 1,符合发现语义)。

审计在本机发现的真实依赖漂移(未修复,锁文件更新是独立依赖变更,留待用户决定):

- `web/` npm:11 个 high advisory(brace-expansion / minimatch 链来自 eslint 工具链,
  postcss 来自 next 构建链);
- `api/requirements-test.lock`:pygments 2.19.2(PYSEC-2026-2987,修复 2.20.0)、
  pytest 9.0.2(PYSEC-2026-1845,修复 9.0.3);
- `api/requirements-live.lock`:无已知漏洞。

上述漂移全部是开发 / 测试 / 构建工具链,live 运行时依赖干净;这同时意味着 main 上
旧的“每次 runtime 变更阻塞 audit”门今天就会因外部 advisory 变红,本增量的门分离
正是针对这类不可归因红灯。

## 2026-07-26 续二:首次真实 CI 暴露 workflow 语义缺陷并修复

Draft PR #32 的首次 push 触发 run 30194650726 在 0 秒失败、未创建任何 job,GitHub
报告 workflow file issue。根因:四个 job 的 job 级 `env` 绑定了 `${{ runner.temp }}`,
而 `runner` context 不允许出现在 job 级 `env`(该处在 runner 分配前求值)。本地
YAML 解析与 `bash -n` 都无法覆盖这类 GitHub 语义校验,属本增量引入的定义缺陷
(归因 `product`)。

最小修复(不重构):删除四个 job 级 `env`,proof 路径在 run 块内统一以 shell 变量
`"$RUNNER_TEMP/ci-proof.jsonl"` 引用(每个 job 独立 runner,无冲突);扫描器容器
冒烟钉定与测试夹具同步一行;`quality.md` 登记该验证边界。既有合法 step 级
`runner.temp` 用法(`TRACEABLE_MODEL_ROOT` 等)保持不变。

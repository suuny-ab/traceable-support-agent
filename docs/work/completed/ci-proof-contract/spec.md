# 增量说明

> 状态：`closed_ready_archived`
>
> 复杂度：标准
>
> 外部风险：`R0`(CI 定义与治理工具改动;定期审计 workflow 已加入仓库,但 schedule
> 只在合并进默认分支后生效)
>
> 成熟度：保持 `S1 公开 Beta`

## 用户结果

每个 CI Check 对应一条可陈述的证明主张;绿灯只在运行时检查真实执行时表示"已证明",
被跳过时显式可见;合同覆盖 `ci-release` 四个 job 内登记主张的检查步骤,每个被覆盖的
红灯给出可归因的类别(产品 / 治理边界 / 外部依赖)和处理入口——单命令步骤在命令
输出前打印归因行(强制 flush,先于子进程输出到达日志),多行脚本步骤以稳定 echo 码
定位失败点、在步骤末尾给出归因块——使开发者和招聘者无需阅读 workflow YAML 即可
理解"这次运行证明了什么、失败归谁、下一步做什么"。期望执行却未运行的检查使摘要
步骤失败关闭,绿色 required Check 不能掩盖未执行的检查。

合同外边界(明确不覆盖):checkout、setup actions、artifact 上传、`publish` job 与
workflow 评估失败。workflow 评估失败由 GitHub 在 run 页面直接报告;`publish` 链由
release-decision 与 release-manifest 门约束。合同不声称这四类失败可归因。

依赖安全与产品功能红灯分离:产品功能 CI 保持稳定可归因;依赖锁文件变化时执行阻塞性
审计(`web/` 依赖变化触发 npm audit,API 锁定清单变化触发钉定 pip-audit);未改代码
时出现的依赖漂移由定期审计发现。

## 当前问题与证据

- `governance_only` 变更下 web/api/containers 三个 job 只 echo 一行即变绿,绿灯不诚实。
- `npm audit --audit-level=high` 对实时 registry 在每次 runtime 变更时阻塞;新 advisory
  可让未改代码的 main 变红,失败不可归因于候选 diff。
- 失败粒度只有 job 级:红的 `api` 可能是 pip 安装、模型下载或 pytest 断言;无失败分类、
  无 run summary、无处理入口。
- CI 绿与 `docs/product/evidence-map.md` 的主张之间没有机器可读绑定。
- Web 冒烟只断言 HTTP 200,不断言页面内容。

## 最便宜证伪

不改动任何产品代码。用 `tools/ci_proof.py` 在本地注入成功 / 失败命令,验证:

- 单命令步骤的 `ci_check` 归因行在 fd 级先于子进程输出;失败块包含归因类别、主张、
  claim 边界和处理入口;
- proof JSONL 与 Markdown 摘要正确渲染通过、失败和跳过;
- `ci_impact.py` 对依赖锁文件变化的检测正确;
- 改造后的 workflow YAML 语法有效,且每个被包装的步骤都能在本地等价复现。

若摘要无法在三类归因下保持准确,或包装让 workflow 明显更难读,立即停止并回退为
仅文档级说明。

## 范围

- 新增 `tools/ci_proof.py`:主张登记、命令包装(`product` / `boundary` / `external`
  三类归因)、proof JSONL 记录、Job Summary 渲染。
- 扩展 `tools/ci_impact.py`:检测依赖锁文件变化并输出 `dependency_files_changed`。
- 改造 `.github/workflows/ci-release.yml`:关键步骤绑定主张与归因类别;`web/` 依赖
  变化时阻塞 npm audit,API 锁定清单变化时阻塞钉定 pip-audit;`governance_only`
  跳过时输出显式 skipped 摘要;Web 冒烟补页面内容断言。
- 新增 `tools/dependency_audit.py`:定期依赖审计入口;`.github/workflows/dependency-audit.yml`
  周频运行(schedule 只在合并进默认分支后生效)。
- 更新 `docs/engineering/quality.md`、`docs/status.md` 与本工作记录。

## 明确不做

- 不改动产品运行时代码(`api/src`、`web/app`)。
- 不改 `deploy-production.yml` 的部署门。
- 不改 job 名称(required checks 名称是分支保护外部状态,改名需用户另行授权)。
- 不新增 README badge 或公开主张(留待 Issue #29 或后续用户决定)。
- 不修复审计发现的依赖漂移(锁文件更新是独立的依赖变更,由用户决定)。

> 2026-07-26 更新:用户已在后续轮次授权把定期审计接入 GitHub——新增
> `.github/workflows/dependency-audit.yml`(每周一次,schedule 只在默认分支运行),
> 并授权推送 `codex/ci-contract` 与创建以 `main` 为 base 的独立 Draft PR 验证真实
> runner。上述授权不包含合并、required checks 变更或分支保护修改。

## 验收条件

- `python -m unittest discover -s tools/tests` 全绿,含新增 ci_proof 与 ci_impact 用例。
- `python tools/check_public_repo.py --scope worktree` 通过。
- 两个 workflow YAML 解析有效;本地模拟 proof run/summary 的三类归因输出正确。
- 工作记录、quality.md、status.md 之间无矛盾描述。

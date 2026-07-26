# 增量说明

> 状态：`active`
>
> 复杂度：标准
>
> 外部风险：`R0`(纯本地与 CI 定义改动;定期审计只实现本地入口,不在 GitHub 启用)
>
> 成熟度：保持 `S1 公开 Beta`

## 用户结果

每个 CI Check 对应一条可陈述的证明主张;绿灯只在运行时检查真实执行时表示"已证明",
被跳过时显式可见;每个红灯在输出首行给出归因类别(产品 / 治理边界 / 外部依赖)和
处理入口,使开发者和招聘者无需阅读 workflow YAML 即可理解"这次运行证明了什么、
失败归谁、下一步做什么"。

依赖安全与产品功能红灯分离:产品功能 CI 保持稳定可归因;依赖锁文件变化时执行阻塞性
npm 审计;未改代码时出现的依赖漂移由定期审计发现,本轮只交付本地审计入口。

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

- 失败输出首行包含归因类别、主张和处理入口;
- proof JSONL 与 Markdown 摘要正确渲染通过、失败和跳过;
- `ci_impact.py` 对依赖锁文件变化的检测正确;
- 改造后的 workflow YAML 语法有效,且每个被包装的步骤都能在本地等价复现。

若摘要无法在三类归因下保持准确,或包装让 workflow 明显更难读,立即停止并回退为
仅文档级说明。

## 范围

- 新增 `tools/ci_proof.py`:主张登记、命令包装(`product` / `boundary` / `external`
  三类归因)、proof JSONL 记录、Job Summary 渲染。
- 扩展 `tools/ci_impact.py`:检测依赖锁文件变化并输出 `dependency_files_changed`。
- 改造 `.github/workflows/ci-release.yml`:关键步骤绑定主张与归因类别;npm audit 仅在
  依赖文件变化时阻塞;`governance_only` 跳过时输出显式 skipped 摘要;Web 冒烟补页面
  内容断言。
- 新增 `tools/dependency_audit.py`:本地定期依赖审计入口(本轮不在 GitHub 启用)。
- 更新 `docs/engineering/quality.md`、`docs/status.md` 与本工作记录。

## 明确不做

- 不改动产品运行时代码(`api/src`、`web/app`)。
- 不改 `deploy-production.yml` 的部署门。
- 不改 job 名称(required checks 名称是分支保护外部状态,改名需用户另行授权)。
- 不新增 README badge 或公开主张(留待 Issue #29 或后续用户决定)。
- 不在 GitHub 上启用定期审计 workflow,不推送、不建 PR、不重跑 Actions。

## 验收条件

- `python -m unittest discover -s tools/tests` 全绿,含新增 ci_proof 与 ci_impact 用例。
- `python tools/check_public_repo.py --scope worktree` 通过。
- 两个 workflow YAML 解析有效;本地模拟 proof run/summary 的三类归因输出正确。
- 工作记录、quality.md、status.md 之间无矛盾描述。

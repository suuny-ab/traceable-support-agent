# 当前开发状态

> 本文件保存项目结果队列和固定候选；Conversation / Turn 运行状态在 Git 外控制系统。
> 项目 Agent 仅在确有隔离、候选或恢复治理需要时建立 Task / Run，并把恢复事实留在项目
> checkpoint；个人 Work 和新 Conversation 入口不默认登记。

| 字段 | 内容 |
| --- | --- |
| `state` | `developing` |
| 更新时间 | `2026-07-26` |
| 当前产品目标 | Issue #28：完成最终作品集视觉与三个固定示例的受控真实体验 |
| 当前集成任务 | live workbench 集成已汇合入基线（merge `edd9044`）；等待 Draft PR 与 CI |
| 复杂度 | 完整；候选涉及前端、API、持久化和受控 live 路径 |
| 风险 / 成熟度 | 当前候选核验为 `R0`；产品保持 `S1 公开 Beta`，实时 Provider、费用、凭据、生产开关和部署仍需独立授权 |
| 产品候选 | 已汇合：Worker 候选 `71104ee` → 集成提交 `e3fc2a5` → merge `edd9044` 进入基线 |
| 项目基线 | `codex/portfolio-experience`（唯一权威位置：主 worktree `traceable-support-agent`） |
| 活动工作 | `docs/work/active/portfolio-live-experience/` |
| 阻碍 | 无工程阻碍 |
| Provider | 生产仍禁用：`provider_enabled=false`、`provider_calls=0`、`provider_cost_cny=0`；历史账单事实不提供当前调用授权 |
| 下一检查点 | 经用户授权后推送基线并创建 Draft PR；不自动启用 Provider、合并或部署 |

## 当前队列

| Task | 状态 | 候选 / 结果 |
| --- | --- | --- |
| `TASK-TRACEABLE-LIVE-WORKBENCH` | `converged` | Worker 候选 `71104ee` 经集成提交 `e3fc2a5` 汇合入基线 `edd9044`；收敛验证记录见 result.md |

Task 可以并行，进入受保护 `main`、正式复核、部署和用户验收仍按依赖串行。

## 当前产品事实

- 方向 B 的公开回放体验位于 <https://47.84.34.86/>。
- 健康状态必须保持 `replay_only`；实时 Provider 不因控制系统启用而获得授权。
- `product/0.1.0` 尚未发布；Stage 12 已执行一次（19/24、9 通过），Issue #21 已修复当时的
  两条边界缺陷但未重跑未见集；Issue #22 已以部分结果和已知限制收口，不形成成功率主张。
- 结果顺序仍为 Issue #28 最终网站与受控真实演示、Issue #29 仓库展示、Issue #14 发布或
  保持 Beta 判断；并行 Task 不自动改变产品依赖。
- 当前工作树和公开 GitHub 仓库是产品唯一权威开发来源。
- 唯一权威开发位置为主 worktree `traceable-support-agent`（分支 `codex/portfolio-experience`）；
  `traceable-support-agent-live-workbench` 与 `traceable-support-agent-live-integration` 已退出
  当前事实来源，物理移除仍需单独授权。
- 收敛前主 worktree 未提交修改完整保存在本地分支 `backup/portfolio-experience-wip-20260726`
  （`a683dff`），可用 `git restore --source=backup/portfolio-experience-wip-20260726 .` 恢复。
- 旧仓和临时回滚材料不是权威来源；删除仍是未经授权的独立破坏性动作。
- 受保护 `main` 的 CI 全绿后自动进入既有生产部署流程；失败部署不自动重试。

## 权威来源

- 产品事实：`PROJECT.md`
- 结果路线：`ROADMAP.md`
- 工程规则：`docs/engineering/`
- Agent 协作规则：`docs/engineering/agent-workflow.md`

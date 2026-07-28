# 当前开发状态

> 本文件保存项目结果队列和固定候选；Conversation / Turn 运行状态在 Git 外控制系统。
> 项目 Agent 仅在确有隔离、候选或恢复治理需要时建立 Task / Run，并把恢复事实留在项目
> checkpoint；个人 Work 和新 Conversation 入口不默认登记。

| 字段 | 内容 |
| --- | --- |
| `state` | `developing` |
| 更新时间 | `2026-07-28` |
| 当前产品目标 | 求职交付收口：公开 Beta 回放版已部署并通过最终生产体验验收 |
| 当前集成任务 | 无活动产品集成任务；无产品代码修复阻断 |
| 复杂度 | 轻量；仅项目事实与工作记录 |
| 风险 / 成熟度 | 产品保持 `S1 公开 Beta`、生产 `replay_only`；真实 Provider、费用、凭据和生产开关均未启用 |
| 产品候选 | 无活动候选；当前已部署产品版本 `34079d7`（PR #31 / #34） |
| 项目基线 | `origin/main` 当前 head（本文件不固定基线 SHA，避免合并后失真）；唯一权威位置为主 worktree `traceable-support-agent` |
| 活动工作 | `docs/work/active/portfolio-live-experience/`（验收记录完整；Issue #28 仍为 OPEN，待用户按 `not planned` 关闭后归档） |
| 最近完成 | PR #31 live 优先工作台 + PR #34 首页来源一致性修正：main CI、镜像发布与生产部署成功并绑定 `34079d7`，Codex 独立最终生产体验验收 `PASS`；`docs/work/completed/ci-proof-contract/` |
| 阻碍 | 无产品代码修复阻断；Issue #28 生命周期收口（按 `not planned` 关闭）是用户动作；npm 依赖漂移（11 high、test 锁 2 个）继续登记 |
| Provider | 生产仍禁用：`provider_enabled=false`、`provider_calls=0`、`provider_cost_cny=0`；v14 两次调用估算 `¥0.080325`、预留 `¥0.287007`，重试 0；v11 / v13 各有一次未计价，历史实际账单仍待账号侧确认 |
| 下一检查点 | 用户按拟议说明以 `not planned` 关闭 Issue #28 并启动 Issue #29；Issue #14 继续后置；定期依赖审计变红告警按分层处理 |

## 当前队列

| Task | 状态 | 候选 / 结果 |
| --- | --- | --- |
| `TASK-TRACEABLE-LIVE-WORKBENCH` | `delivered` | PR #31 合并部署，最终生产体验验收 `PASS`；首页一致性由 PR #34 修正 |

Task 可以并行，进入受保护 `main`、正式复核、部署和用户验收仍按依赖串行。

## 当前产品事实

- 方向 B 的公开回放体验位于 <https://47.84.34.86/>。
- 当前求职交付是已经部署并通过最终体验验收的公开 Beta 回放版；健康状态保持
  `replay_only`，真实 Provider、凭据和费用均未启用。
- `product/0.1.0` 尚未发布；Stage 12 已执行一次（19/24、9 通过），Issue #21 已修复当时的
  两条边界缺陷但未重跑未见集；Issue #22 已以部分结果和已知限制收口，不形成成功率主张。
- Issue #28 的视觉、公开回放体验与生产验收**部分**已完成；其原始范围中的公开真实
  Provider 与实时 candidate 验收门没有完成，已按求职取舍停止（从未启用）；Issue 仍为
  OPEN，待用户按 `not planned` 关闭，不得表述为全部验收门通过。
- Issue #29 保留为下一项 GitHub 求职展示工作；Issue #14 发布或保持 Beta 判断继续后置。
- 当前工作树和公开 GitHub 仓库是产品唯一权威开发来源。
- 唯一权威开发位置为主 worktree `traceable-support-agent`；
  `traceable-support-agent-live-workbench`、`traceable-support-agent-live-integration` 与
  `traceable-support-agent-ci-contract` 已退出当前事实来源，物理移除仍需单独授权。
- 收敛前主 worktree 未提交修改完整保存在本地分支 `backup/portfolio-experience-wip-20260726`
  （`a683dff`），可用 `git restore --source=backup/portfolio-experience-wip-20260726 .` 恢复。
- 旧仓和临时回滚材料不是权威来源；删除仍是未经授权的独立破坏性动作。
- 受保护 `main` 的 CI 全绿后自动进入既有生产部署流程；失败部署不自动重试。

## 权威来源

- 产品事实：`PROJECT.md`
- 结果路线：`ROADMAP.md`
- 最近完成记录：`docs/work/completed/ci-proof-contract/`
- 工程规则：`docs/engineering/`
- Agent 协作规则：`docs/engineering/agent-workflow.md`

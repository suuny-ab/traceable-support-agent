# 当前开发状态

> 本文件保存项目结果队列和固定候选；Conversation / Turn 运行状态在 Git 外控制系统。
> 项目 Agent 仅在确有隔离、候选或恢复治理需要时建立 Task / Run，并把恢复事实留在项目
> checkpoint；裁决入口和新现场会话不默认登记。

| 字段 | 内容 |
| --- | --- |
| `state` | `local_acceptance` |
| 更新时间 | `2026-08-01` |
| 当前产品目标 | 打磨求职展示，不增加产品功能；先把首页和工作台收束成招聘方 10 秒理解、2 分钟体验的主路径 |
| 当前集成任务 | `portfolio-guided-path` |
| 复杂度 | 标准 / `R0`；改变首页与工作台的用户可见信息层级，不改变运行、Provider、数据或安全合同 |
| 风险 / 成熟度 | 最大风险是折叠后隐藏关键边界；当前候选保留实时 / 回放区分、边界挑战、自由输入和完整结果，并由渲染与响应式测试失败关闭 |
| 产品候选 | 本地分支 `codex/workbench-polish`，固定实现提交 `14e4c6b`；未推送、未部署，等待用户本地体验验收 |
| 项目基线 | `origin/main` 的 `e52bae3`；唯一权威位置为主 worktree `traceable-support-agent` |
| 活动工作 | `portfolio-guided-path`：首页单一求职主张；工作台推荐案例 + 结果优先；其他能力折叠为“更多体验” |
| 最近完成 | PR #50 squash 合并为 `66af626`；main CI `30629303699`、生产部署 `30629464871` 和公网完整 SHA 验收通过，工作记录归档于 `docs/work/completed/release-sha-health/` |
| 阻碍 | 无工程阻碍；本地候选待用户体验验收。移动端响应式合同已通过机器检查，但本轮验收浏览器禁止强制移动视口，未形成移动端截图 |
| Provider | 生产已启用（`2026-07-29`，用户显式授权）：`provider_enabled=true`；当前公网健康返回 `release_sha=66af626ba4debf4c8a1cf91da023754168c5b908` 与 `live_experience=available`。本增量 Provider 调用 `0` 次，没有创建产品运行，也未改变凭据、预算或默认检索后端；凭据仍只在服务器 `/opt/traceable-support/provider.env`（0600），预算仍为日 ¥20 / 月 ¥100 / 次 ¥1、自动重试 0 |
| 下一检查点 | 用户在 `http://localhost:3411/` 验收首页与推荐案例主路径；通过后再单独决定是否推送和部署 |

## 当前队列

| Task | 状态 | 候选 / 结果 |
| --- | --- | --- |
| `portfolio-guided-path` | `local_acceptance` | `14e4c6b`；33 项测试、lint、typecheck、build 通过，桌面主路径与折叠入口已在本地浏览器验收；未推送、未部署 |
| `release-sha-health` | `delivered` | PR #50 合并部署；公网健康返回与 `66af626ba4debf4c8a1cf91da023754168c5b908` 精确一致的完整 `release_sha` |
| `ISSUE-29-PORTFOLIO-PRESENTATION` | `delivered` | PR #43 合并为 `8da0546` 并自动部署；GitHub、真实运行 GIF、公网站点与当前事实统一，用户验收 `PASS` |
| `TASK-TRACEABLE-LIVE-WORKBENCH` | `delivered` | PR #31 合并部署，最终生产体验验收 `PASS`；首页一致性由 PR #34 修正；Issue #28 已关闭归档 |
| `TASK-REAL-RUN-EVIDENCE` | `delivered` | 内容随 PR #38 合入 main（#38 叠加绑定式溯源门改造 ADR-0007 与部署链路解锁；PR #37 经两轮定向复核全绿后关闭、未直接合并）；真实 Provider live 已上线（`766ba3f`）；工作记录归档 `docs/work/completed/real-run-evidence/` |

Task 可以并行；required Checks、所需当次授权、触发时的评审兜底、受保护 `main`、部署和
用户验收仍按依赖串行。

## 当前产品事实

- 方向 B 的公开体验位于 <https://47.84.34.86/>；`2026-07-29` 起为真实 Provider live
  模式。当前生产运行的产品发布为 `66af626ba4debf4c8a1cf91da023754168c5b908`，
  公网健康同时返回该完整 `release_sha` 与 `live_experience=available`；后续仅文档收口不触发部署。
- 生成门语义：`2026-07-29` 起为绑定式溯源（ADR-0007）：每条结论必须绑定真实存在的
  证据 / 义务 ID，证据原文随回答展示；不再要求措辞逐字复现原文。真实 Provider 本地
  复测过门率 0/2 → 3/3，公网首跑 1/1 `completed`。
- 此前求职交付为已部署并通过最终体验验收的公开 Beta 回放版（部署 `34079d7`）；真实
  Provider、凭据和费用在该阶段均未启用。
- `product/0.1.0` 尚未发布；Stage 12 已执行一次（19/24、9 通过），Issue #21 已修复当时的
  两条边界缺陷但未重跑未见集；Issue #22 已以部分结果和已知限制收口，不形成成功率主张。
- Issue #28 已于 2026-07-28 以 `not planned` 关闭：在该关闭时点，视觉、公开回放体验与
  生产验收部分已完成，公开真实 Provider 尚未启用；该历史结论已由 2026-07-29 的独立
  授权 live 上线增量更新，不能再作为当前公网状态。
- Issue #29 已完成：PR #43 合并部署后，GitHub 与公网展示、真实运行证据、工程边界和复现
  入口已统一，并于 `2026-07-30` 通过用户面试官视角验收；Issue #14 发布或保持 Beta 判断
  继续后置。
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
- 最近完成记录：`docs/work/completed/release-sha-health/`、`docs/work/completed/portfolio-live-experience/`、`docs/work/completed/ci-proof-contract/`、`docs/work/completed/real-run-evidence/`
- 工程规则：`docs/engineering/`
- Agent 协作规则：`docs/engineering/agent-workflow.md`

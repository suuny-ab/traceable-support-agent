# 当前开发状态

> 本文件保存项目结果队列和固定候选；Conversation / Turn 运行状态在 Git 外控制系统。
> 项目 Agent 仅在确有隔离、候选或恢复治理需要时建立 Task / Run，并把恢复事实留在项目
> checkpoint；裁决入口和新现场会话不默认登记。

| 字段 | 内容 |
| --- | --- |
| `state` | `ready` |
| 更新时间 | `2026-08-01` |
| 当前产品目标 | README 首屏量化证据与 Stage 12 修复路径已形成本地候选；不继续增加产品功能、布局或字体微调 |
| 当前集成任务 | 无 |
| 复杂度 | 无活动增量；产品保持 `S1 公开 Beta`、单机、无 SLA |
| 风险 / 成熟度 | 新版信息层级已通过本地用户验收、CI、自动部署和公网核验；移动端没有独立真机截图，且本次结果不证明模型质量、高可用或长期稳定性 |
| 产品候选 | README 求职证据呈现本地候选；尚未推送或公开交付，不改变运行产品 |
| 项目基线 | `origin/main` 当前 head（本文件不固定基线 SHA，避免合并后失真）；唯一权威位置为主 worktree `traceable-support-agent` |
| 活动工作 | 无 |
| 最近完成 | README 首屏增加可回查的检索、测试、CI 与线上版本指标；Stage 12 改为“原始观测 → Issue #21 已修复 → 下一步计划”三步框架；详细回执见下文 |
| 阻碍 | 无；剩余布局与字体审美优化边际收益较低，只有出现新的面试反馈或明确体验问题时才重开 |
| Provider | 生产已启用（`2026-07-29`，用户显式授权）：`provider_enabled=true`；当前公网健康返回 `release_sha=915ca4ef7820870ee42fbef69ea719498d7f402d` 与 `live_experience=available`。本增量 Provider 调用 `0` 次，没有创建产品运行，也未改变凭据、预算或默认检索后端；凭据仍只在服务器 `/opt/traceable-support/provider.env`（0600），预算仍为日 ¥20 / 月 ¥100 / 次 ¥1、自动重试 0 |
| 下一检查点 | 暂停继续打磨本项目；只有新的面试反馈或明确体验问题出现时再决定前端切片，Issue #14 的 `product/0.1.0` 判断继续后置 |

## 当前队列

| Task | 状态 | 候选 / 结果 |
| --- | --- | --- |
| `portfolio-evidence-first-screen` | `completed_local` | README 首屏量化证据和 Stage 12 三步框架已完成；检索报告、Issue #21、main CI 与公网 health 链接已核验；未推送、未部署 |
| `frontend-polish-delivery` | `delivered` | PR #52 合并为 `915ca4e`；main CI、生产部署、公网完整 SHA、四页文案与样式检查通过；Provider 调用 0，工作记录已归档 |
| `frontend-polish` | `delivered` | 本地候选 `a6ff775` 经后续最小治理记录形成 PR #52 并公开交付；用户于 `2026-08-01` 完成整体体验验收 |
| `portfolio-guided-path` | `accepted_local` | `14e4c6b`；33 项测试、lint、typecheck、build 通过，桌面主路径与折叠入口已由用户本地验收；未推送、未部署 |
| `release-sha-health` | `delivered` | PR #50 合并部署；公网健康返回与 `66af626ba4debf4c8a1cf91da023754168c5b908` 精确一致的完整 `release_sha` |
| `ISSUE-29-PORTFOLIO-PRESENTATION` | `delivered` | PR #43 合并为 `8da0546` 并自动部署；GitHub、真实运行 GIF、公网站点与当前事实统一，用户验收 `PASS` |
| `TASK-TRACEABLE-LIVE-WORKBENCH` | `delivered` | PR #31 合并部署，最终生产体验验收 `PASS`；首页一致性由 PR #34 修正；Issue #28 已关闭归档 |
| `TASK-REAL-RUN-EVIDENCE` | `delivered` | 内容随 PR #38 合入 main（#38 叠加绑定式溯源门改造 ADR-0007 与部署链路解锁；PR #37 经两轮定向复核全绿后关闭、未直接合并）；真实 Provider live 已上线（`766ba3f`）；工作记录归档 `docs/work/completed/real-run-evidence/` |

Task 可以并行；required Checks、所需当次授权、触发时的评审兜底、受保护 `main`、部署和
用户验收仍按依赖串行。

## 2026-08-01 派发回执：README 首屏量化证据

- 指标块：RRF Top-5 必需来源覆盖 `16/16`、错误型号来源 `0`；边界明确为 16 个冻结公开
  合成开发题的来源覆盖，不写回答质量、线上成功率或未见集结论。
- 自动化证据：部署候选 `915ca4e` 的 main CI `30690110223` 五个 job 全部成功；API 日志为
  `137 passed / 2 skipped`，Stage 12 runner 为 `13 passed`。派发中的旧数字 `132` 未写入。
- Stage 12：README 保留原始 `19/24`、`9` 通过观测，说明 Issue #21 已修复已知边界机制但
  未重跑未见集，并把新的验证说明卡、另行授权和 Issue #14 发布判断列为条件式下一步。
- 链接核验：Issue #21 为 `CLOSED`；main CI 结论为 `success`；公网 health 返回
  `status=ok`、`live_experience=available`、`release_sha=915ca4ef7820870ee42fbef69ea719498d7f402d`。
- 本次派发只修改 README 和状态回执；工作树中的 `AGENTS.md` 属单独批准的规则变更，不计入
  本派发。Provider 调用 `0`、产品运行 `0`，未修改产品代码、评测本体、检索、凭据、预算或部署。

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

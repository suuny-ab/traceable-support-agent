# 当前开发状态

> 本文件保存项目结果队列和固定候选；Conversation / Turn 运行状态在 Git 外控制系统。
> 项目 Agent 仅在确有隔离、候选或恢复治理需要时建立 Task / Run，并把恢复事实留在项目
> checkpoint；裁决入口和新现场会话不默认登记。

| 字段 | 内容 |
| --- | --- |
| `state` | `candidate` |
| 更新时间 | `2026-07-31` |
| 当前产品目标 | 为求职作品集补齐“线上实际运行哪次提交”的可验证证据：健康接口返回镜像构建 SHA，部署与回滚门核对精确版本；不扩展 RAG、Provider 或监控能力 |
| 当前集成任务 | `codex/release-sha-health` 本地候选；规格与本地证据见 `docs/work/active/release-sha-health/spec.md`，尚未推送、合并或部署 |
| 复杂度 | 完整、当前实现为 `R0`：修改公共健康合同与生产发布门，但不进行网络、Provider 调用或外部写入；推送与自动部署是后续独立动作 |
| 风险 / 成熟度 | 产品保持 `S1 公开 Beta`；主要风险是服务器 live 构建漏注入 SHA、运行身份错配和首次旧回滚锚点缺少字段，均由构建参数、精确健康检查和一次兼容边界处理 |
| 产品候选 | 已验证：用固定 40 位 SHA 构建的回放镜像将该值写入只读身份文件，健康接口原样返回，容器进入 `healthy`；API、公开冒烟和发布脚本会在身份错配时失败 |
| 项目基线 | `origin/main` 当前 head（本文件不固定基线 SHA，避免合并后失真）；唯一权威位置为主 worktree `traceable-support-agent` |
| 活动工作 | `docs/work/active/release-sha-health/` |
| 最近完成 | PR #49 已 squash 合并为 `139a9c8` 并自动部署；16 题可重复检索体检已形成公开冻结结果并停止 |
| 阻碍 | 当前无工程阻碍；工作树已有用户未跟踪缓存目录 `clean/`，本切片不读取、修改或提交它。工作树级公共扫描会命中该目录，候选验证需使用 Git index / clean CI 范围。启用 pgvector DSN 前的 live readiness P1 finding 与 npm 依赖漂移继续登记，本轮不处理 |
| Provider | 生产已启用（`2026-07-29`，用户显式授权）：`provider_enabled=true`；本切片开工时部署 SHA 为 `139a9c8ba0c450cc7a7b8fbdb518601763ac7719`，但旧健康接口尚不返回该身份。本切片不改变 Provider 授权、凭据、预算或默认生产检索后端，也不调用 Provider。凭据仅存服务器 `/opt/traceable-support/provider.env`（0600），不进 git / 流水线 / 镜像；预算双保险生效（日 ¥20 / 月 ¥100 / 次 ¥1、重试 0） |
| 下一检查点 | 形成一个边界清楚的本地提交后停止，等待用户另行决定是否推送；不在本切片内合并或部署 |

## 当前队列

| Task | 状态 | 候选 / 结果 |
| --- | --- | --- |
| `ISSUE-29-PORTFOLIO-PRESENTATION` | `delivered` | PR #43 合并为 `8da0546` 并自动部署；GitHub、真实运行 GIF、公网站点与当前事实统一，用户验收 `PASS` |
| `TASK-TRACEABLE-LIVE-WORKBENCH` | `delivered` | PR #31 合并部署，最终生产体验验收 `PASS`；首页一致性由 PR #34 修正；Issue #28 已关闭归档 |
| `TASK-REAL-RUN-EVIDENCE` | `delivered` | 内容随 PR #38 合入 main（#38 叠加绑定式溯源门改造 ADR-0007 与部署链路解锁；PR #37 经两轮定向复核全绿后关闭、未直接合并）；真实 Provider live 已上线（`766ba3f`）；工作记录归档 `docs/work/completed/real-run-evidence/` |

Task 可以并行；required Checks、所需当次授权、触发时的评审兜底、受保护 `main`、部署和
用户验收仍按依赖串行。

## 当前产品事实

- 方向 B 的公开体验位于 <https://47.84.34.86/>；`2026-07-29` 起为真实 Provider live
  模式。本切片开工时 `main` 与生产部署均绑定 `139a9c8ba0c450cc7a7b8fbdb518601763ac7719`，
  健康状态为 `available`，但当前生产健康响应尚无 `release_sha`；本地候选尚未交付。
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
- 最近完成记录：`docs/work/completed/portfolio-live-experience/`、`docs/work/completed/ci-proof-contract/`、`docs/work/completed/real-run-evidence/`
- 工程规则：`docs/engineering/`
- Agent 协作规则：`docs/engineering/agent-workflow.md`

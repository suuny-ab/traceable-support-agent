# 当前开发状态

> 本文件保存项目结果队列和固定候选；Conversation / Turn 运行状态在 Git 外控制系统。
> 项目 Agent 仅在确有隔离、候选或恢复治理需要时建立 Task / Run，并把恢复事实留在项目
> checkpoint；裁决入口和新现场会话不默认登记。

| 字段 | 内容 |
| --- | --- |
| `state` | `ready` |
| 更新时间 | `2026-07-31` |
| 当前产品目标 | 求职作品集的第一次可重复 RAG 检索体检已形成冻结结果并停止；交付入口为 PR #49。P1（可观测性）仍先于 Issue #14，但本轮不继续实现 |
| 当前集成任务 | PR #49：16 题公开合成开发集、BM25 / BGE / RRF 同题结果、公开设计页和漂移测试；实现已完成，合并与部署状态以 GitHub Checks 和生产健康回执为准 |
| 复杂度 | 标准、`R0`：新增离线评测和公开证据，不修改产品检索、生成、Provider、公共 API 或部署算法 |
| 风险 / 成熟度 | 产品保持 `S1 公开 Beta`；检索体检只是公开开发集证据，不改变成熟度或 Provider / 检索运行边界；本切片前生产绑定 `9c366b6`，之后的精确发布版本以生产健康回执为准 |
| 产品候选 | PR #49：Top-5 全覆盖 BM25 14/16、BGE 14/16、RRF 16/16；三者 Top-10 均 16/16、错误型号来源均 0；首次冻结结果后停止 |
| 项目基线 | `origin/main` 当前 head（本文件不固定基线 SHA，避免合并后失真）；唯一权威位置为主 worktree `traceable-support-agent` |
| 活动工作 | 无 |
| 最近完成 | 完成 16 题可重复检索体检和 PR #49 交付候选；此前 PR #46 将公共 HTTP 适配层替换为 FastAPI（`e43e488`），PR #47 新增默认不启用的 pgvector 后端（`9c366b6`）并成功部署 |
| 阻碍 | 本切片无工程阻碍；外部交付必须依次通过 PR Checks、受保护 `main`、自动部署和生产核验，失败不自动重试。启用 pgvector DSN 前的 live readiness P1 finding 与 npm 依赖漂移继续登记，本轮不处理 |
| Provider | 生产已启用（`2026-07-29`，用户显式授权）：`provider_enabled=true`；本切片前部署 SHA 为 `9c366b6`，PR #49 不改变 Provider 授权、凭据、预算或默认生产检索后端，之后的精确发布版本以生产健康回执为准。凭据仅存服务器 `/opt/traceable-support/provider.env`（0600），不进 git / 流水线 / 镜像；预算双保险生效（日 ¥20 / 月 ¥100 / 次 ¥1、重试 0）；上线当日公网真实 QA 1 次 `completed`（live candidate，证据挂载，`provider_calls=2`，预留 ¥1）；`2026-07-30` 经用户授权为 Issue #29 GIF 再执行默认合成 QA 1 次，同一 run 四阶段 PASS、`provider_calls=2`、重试 0，未提交人工决定或外部动作；历史：v14 两次调用估算 `¥0.080325`、预留 `¥0.287007`，v11 / v13 各有一次未计价，历史实际账单仍待账号侧确认 |
| 下一检查点 | 本切片完成门是 PR #49 Checks 全绿、squash merge、自动部署和公网 `/design` / 健康核验；到达后停止，不调参、不换题、不修改 Top-10 产品行为 |

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
  模式。本切片前部署绑定 `9c366b6`（`2026-07-31` 健康状态 `available`）；受保护 `main`
  的后续精确发布 SHA 以生产健康回执为准，replay 回放预览保持可用。
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

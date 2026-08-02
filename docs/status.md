# 当前开发状态

> 本文件保存项目结果队列和固定候选；Conversation / Turn 运行状态在 Git 外控制系统。
> 项目 Agent 仅在确有隔离、候选或恢复治理需要时建立 Task / Run，并把恢复事实留在项目
> checkpoint；裁决入口和新现场会话不默认登记。

| 字段 | 内容 |
| --- | --- |
| `state` | `ready` |
| 更新时间 | `2026-08-02` |
| 当前产品目标 | 解锁 Draft PR #55 与 `main` 的状态冲突并恢复同一 head 的远端验证；不扩大检索功能域 |
| 当前集成任务 | `retrieval-badcase-loop`；Draft PR [#55](https://github.com/suuny-ab/traceable-support-agent/pull/55)，分支 `codex/retrieval-badcase-loop` |
| 复杂度 | 标准 / `R2`；用户已批准同步 `origin/main`、更新公开 PR 分支并触发 Checks；不含合并、部署、Provider 调用或产品运行 |
| 风险 / 成熟度 | 候选直接针对同一 16 题公开开发集调优，只能证明该开发集的来源覆盖变化；不是未见集、回答质量、线上成功率或发布结论 |
| 产品候选 | 原 PR head `45db89f` 已在本地合入 `origin/main@8a306165`；同步提交 `8b7c4cb`，同步后本地相关检查已全绿，最终公开 head 待状态提交后推送 |
| 项目基线 | `origin/main@8a306165221387805ee33e6c20b45d9260c48658`；唯一权威位置为主 worktree `traceable-support-agent` |
| 活动工作 | 无 |
| 最近完成 | PR #54 已 squash merge 为 `8a306165`；main CI `30738245420` 成功，部署链 `30738264198` preflight 成功且 deploy 按 `governance_only` 跳过，运行产品未改变 |
| 阻碍 | 本地文本冲突与相关复验均已关闭；分支推送和 PR #55 新 head 的 Checks 启动仍待完成 |
| Provider | 生产已启用（`2026-07-29`，用户显式授权）：`provider_enabled=true`；当前公网健康返回 `release_sha=915ca4ef7820870ee42fbef69ea719498d7f402d` 与 `live_experience=available`。本增量 Provider 调用 `0` 次，没有创建产品运行，也未改变凭据、预算或默认检索后端；凭据仍只在服务器 `/opt/traceable-support/provider.env`（0600），预算仍为日 ¥20 / 月 ¥100 / 次 ¥1、自动重试 0 |
| 下一检查点 | 提交本回执并推送更新 PR #55，确认新 head 的 required Checks 已创建；本次不合并 PR |

## 当前队列

| Task | 状态 | 候选 / 结果 |
| --- | --- | --- |
| `retrieval-badcase-loop` | `validated_local_push_pending` | Draft PR #55；原 head `45db89f`，同步提交 `8b7c4cb`；`docs/status.md` 已先恢复为 `origin/main` 完整版本再重写；同步后本地相关检查全绿，待推送 |
| `portfolio-evidence-first-screen` | `delivered` | PR #54 head `d8cd208` squash merge 为 `8a306165`；main CI 成功，部署链 preflight 成功且 deploy 跳过，运行产品未改变 |
| `frontend-polish-delivery` | `delivered` | PR #52 合并为 `915ca4e`；main CI、生产部署、公网完整 SHA、四页文案与样式检查通过；Provider 调用 0，工作记录已归档 |
| `frontend-polish` | `delivered` | 本地候选 `a6ff775` 经后续最小治理记录形成 PR #52 并公开交付；用户于 `2026-08-01` 完成整体体验验收 |
| `portfolio-guided-path` | `accepted_local` | `14e4c6b`；33 项测试、lint、typecheck、build 通过，桌面主路径与折叠入口已由用户本地验收；未推送、未部署 |
| `release-sha-health` | `delivered` | PR #50 合并部署；公网健康返回与 `66af626ba4debf4c8a1cf91da023754168c5b908` 精确一致的完整 `release_sha` |
| `ISSUE-29-PORTFOLIO-PRESENTATION` | `delivered` | PR #43 合并为 `8da0546` 并自动部署；GitHub、真实运行 GIF、公网站点与当前事实统一，用户验收 `PASS` |
| `TASK-TRACEABLE-LIVE-WORKBENCH` | `delivered` | PR #31 合并部署，最终生产体验验收 `PASS`；首页一致性由 PR #34 修正；Issue #28 已关闭归档 |
| `TASK-REAL-RUN-EVIDENCE` | `delivered` | 内容随 PR #38 合入 main（#38 叠加绑定式溯源门改造 ADR-0007 与部署链路解锁；PR #37 经两轮定向复核全绿后关闭、未直接合并）；真实 Provider live 已上线（`766ba3f`）；工作记录归档 `docs/work/completed/real-run-evidence/` |

Task 可以并行；required Checks、所需当次授权、触发时的评审兜底、受保护 `main`、部署和
用户验收仍按依赖串行。

## 2026-08-02 派发进行中回执：PR #55 冲突解锁

- 授权：用户当次明确批准同步 `origin/main`、以 `main` 为准重写 `docs/status.md`、复跑相关
  检查并推送更新 PR #55；不含合并、部署或 Provider 调用。
- 同步：`origin/main@8a306165221387805ee33e6c20b45d9260c48658` 已合入
  `codex/retrieval-badcase-loop`，形成 merge 提交 `8b7c4cb68823162cc57526b7424b147cde26fb3a`。
- 冲突处理：merge 唯一冲突为 `docs/status.md`；该文件先整体恢复为 main blob
  `7cd1445ee5ab19e4bc5e5bbce99fed3f4e1b0a4f`，工作树 blob 精确一致并完成 merge 后，才从
  main 版本重写当前事实；没有拼接双方冲突块。
- 候选边界：实现仍是 `80953b5` 的单一 BM25 badcase 改进，状态证据提交为 `45db89f`；不改
  冻结问题、标签或知识内容，不新增 Provider、费用、部署或发布主张。
- 同步后验证：baseline / product candidate 检索检查各 16 题通过、Provider 调用 0；检索定向
  测试 4 通过；API 全集 138 通过 / 2 跳过（另 24 subtests）；Stage 12 runner 13 通过；
  `check_public_repo --scope worktree` 通过（215 files、8 public cases）；`git diff --check` 通过。
- 当前检查点：本地候选已通过相关检查，待提交、推送并确认 PR #55 新 head 的远端 Checks 启动；
  本地绿不冒充远端 CI 绿。

## 2026-08-01 派发交付回执：README 首屏量化证据

- 外部交付：按用户当次明确授权创建分支 `codex/portfolio-evidence-first-screen` 与 Draft PR
  [#54](https://github.com/suuny-ab/traceable-support-agent/pull/54)，base 为 `main`；README 提交为
  `54c5abd896a57cee3fb41881fe72c9bdba089289`，首次状态提交为
  `fbcb268f7cb18f62ae3e140c11418ca8883f36cf`。
- PR 门：运行 `30700792626` 已创建，governance、web、api、containers 四个 required Checks
  在 PR 创建时均为 queued；本回执不把排队状态写成通过。
- 本地验证：在 `origin/main + README/docs/status` 的干净快照上，
  `python tools/check_public_repo.py --scope index` 通过（214 files、8 public cases）；检索体检
  通过（16 cases、Provider 调用 0）；检索 / Stage 12 定向测试 `16 passed`。
- 工作区边界：直接扫描当前工作树会被范围外的 `AGENTS.md` 本机路径与未跟踪 `clean/` 缓存
  拦截，因此没有把该失败冒充候选失败，也没有修改或提交这些范围外内容。
- 通道回执：本执行环境的 `.git` 只读，终端访问 GitHub 被阻断，`gh` 本地令牌也已失效；
  远端内容通过已登录 GitHub 页面从本地 README / 状态文件逐字交付。本地工作文件保持同一内容，
  但 Git 分支元数据需在具备正常 Git 权限的会话中再 `fetch` 同步。

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
  模式。当前生产运行的产品发布为 `915ca4ef7820870ee42fbef69ea719498d7f402d`，
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

# 当前开发状态

> 本文件保存项目结果队列和固定候选；Conversation / Turn 运行状态在 Git 外控制系统。
> 项目 Agent 仅在确有隔离、候选或恢复治理需要时建立 Task / Run，并把恢复事实留在项目
> checkpoint；裁决入口和新现场会话不默认登记。

| 字段 | 内容 |
| --- | --- |
| `state` | `ready` |
| 更新时间 | `2026-08-02` |
| 当前产品目标 | 签收 PR #54 首页证据候选，并用一个公开开发集 badcase 完成一次最小检索改进闭环；不增加新功能域 |
| 当前集成任务 | `retrieval-badcase-loop`；隔离分支 `codex/retrieval-badcase-loop`，基于 `origin/main` |
| 复杂度 | 标准 / `R0`；本地合成数据、离线 BGE 与确定性检索，不含 Provider、费用、外部业务写入、合并或部署 |
| 风险 / 成熟度 | 候选直接针对同一 16 题公开开发集调优，只能证明该开发集的来源覆盖变化；不是未见集、回答质量、线上成功率或发布结论 |
| 产品候选 | PR #54 head `d8cd208` 四个 required jobs 全绿、等待合并授权；检索候选尚在本地隔离分支，未推送 |
| 项目基线 | `origin/main` 当前 head（本文件不固定基线 SHA，避免合并后失真）；唯一权威位置为主 worktree `traceable-support-agent` |
| 活动工作 | 无 |
| 最近完成 | 已 fetch 对齐远端元数据；PR #54 运行 `30700889472` 成功；检索候选把目标必需来源由 BM25 第 6 提至第 5，并通过 API、Stage 12 与治理检查 |
| 阻碍 | 合并 PR #54 会写 `main` 并进入既有自动部署链，已写授权请求、未执行；检索候选若要推送并形成新的公开主张，也须在固定提交后取得当次确认 |
| Provider | 生产已启用（`2026-07-29`，用户显式授权）：`provider_enabled=true`；当前公网健康返回 `release_sha=915ca4ef7820870ee42fbef69ea719498d7f402d` 与 `live_experience=available`。本增量 Provider 调用 `0` 次，没有创建产品运行，也未改变凭据、预算或默认检索后端；凭据仍只在服务器 `/opt/traceable-support/provider.env`（0600），预算仍为日 ¥20 / 月 ¥100 / 次 ¥1、自动重试 0 |
| 下一检查点 | 固定检索候选本地提交并复核工作树；不推送、不建 PR、不合并、不部署，等待用户分别裁决 PR #54 合并与检索候选公开交付 |

## 当前队列

| Task | 状态 | 候选 / 结果 |
| --- | --- | --- |
| `retrieval-badcase-loop` | `candidate_local` | `RET-DEV-R2-008` 的 `COMMON-FAQ/wet-environment` 在 BM25 从第 6 到第 5；BM25 Top-5 14/16 → 15/16，BGE 14/16、RRF 16/16、三路 Top-10 16/16、错误型号来源 0；未推送 |
| `portfolio-evidence-first-screen` | `checks_green_awaiting_authorization` | Draft PR #54，head `d8cd2081f5b481cbef597ba5dd534f78d70851b4`；运行 `30700889472` 的 governance、web、api、containers 全绿，未合并、未部署 |
| `frontend-polish-delivery` | `delivered` | PR #52 合并为 `915ca4e`；main CI、生产部署、公网完整 SHA、四页文案与样式检查通过；Provider 调用 0，工作记录已归档 |
| `frontend-polish` | `delivered` | 本地候选 `a6ff775` 经后续最小治理记录形成 PR #52 并公开交付；用户于 `2026-08-01` 完成整体体验验收 |
| `portfolio-guided-path` | `accepted_local` | `14e4c6b`；33 项测试、lint、typecheck、build 通过，桌面主路径与折叠入口已由用户本地验收；未推送、未部署 |
| `release-sha-health` | `delivered` | PR #50 合并部署；公网健康返回与 `66af626ba4debf4c8a1cf91da023754168c5b908` 精确一致的完整 `release_sha` |
| `ISSUE-29-PORTFOLIO-PRESENTATION` | `delivered` | PR #43 合并为 `8da0546` 并自动部署；GitHub、真实运行 GIF、公网站点与当前事实统一，用户验收 `PASS` |
| `TASK-TRACEABLE-LIVE-WORKBENCH` | `delivered` | PR #31 合并部署，最终生产体验验收 `PASS`；首页一致性由 PR #34 修正；Issue #28 已关闭归档 |
| `TASK-REAL-RUN-EVIDENCE` | `delivered` | 内容随 PR #38 合入 main（#38 叠加绑定式溯源门改造 ADR-0007 与部署链路解锁；PR #37 经两轮定向复核全绿后关闭、未直接合并）；真实 Provider live 已上线（`766ba3f`）；工作记录归档 `docs/work/completed/real-run-evidence/` |

Task 可以并行；required Checks、所需当次授权、触发时的评审兜底、受保护 `main`、部署和
用户验收仍按依赖串行。

## 2026-08-02 派发回执：PR #54 签收与检索 badcase 闭环

### 开工三问与边界

- 做什么：fetch 同步远端元数据；核验 PR #54 同一 head 的 required Checks；绿后提交合并
  授权请求；从 16 题公开开发集选一个组件级 badcase，做一处检索改进并保存前后证据。
- 不做什么：不增加知识接入、新集成或新页面；不改冻结问题、标签或知识内容；不调用
  Provider；不推送检索候选，不建新 PR，不合并或部署。
- 怎样算完成：远端事实绑定精确 head / run；第一次冻结基线仍可重复；候选证据可重算；
  API、Stage 12 与治理检查通过；授权请求和三行战报落盘。
- 风险边界：本次候选是对公开开发集的定向调优，只允许形成“该开发集 BM25 来源覆盖改善”
  的结论，不允许形成未见集、生成质量、线上成功率或发布质量结论。

### PR #54

- `git fetch origin --prune` 成功；本地已出现
  `origin/codex/portfolio-evidence-first-screen=d8cd2081f5b481cbef597ba5dd534f78d70851b4`，
  `origin/main=b6b68e8aa47457aeca3800c1816b237c76301073`。
- GitHub 实时核验：PR #54 为 open / Draft / mergeable，base `main`，head 为上述 `d8cd208`；
  `ci-release` 运行 `30700889472` 为 `success`。
- required jobs：governance、web、api、containers 均 completed / success；web、api、containers
  的运行时步骤因 `governance_only` 跳过，所以这些绿灯不证明运行时行为；publish job 跳过。
- 已在 Git 外 `派发/授权请求.md` 写入精确候选、证据边界和自动部署影响；未转 Ready、未合并、
  未部署。

### 检索候选

- 选中 `RET-DEV-R2-008`：基线 BM25 将必需来源 `COMMON-FAQ/wet-environment` 排第 6，漏出
  Top-5；RRF 已覆盖该题，因此本切片只改善词面召回韧性，不扩大功能或作产品成功主张。
- 一处改进：产品 BM25 候选只在查询和候选文本同时增加显式
  `domain:liquid-ingress` 等价标记，覆盖“吸进水 / 吸入液体 / 吸取液体 / 进水 / 进液”；
  基础 `tokenize`、冻结问题、标签和知识内容均未改变。
- 为避免倒写第一次冻结结果，`web/app/lib/retrieval-checkup-v1.json` 保持原基线；新候选写入
  `evals/retrieval-badcase-candidate-v1.json`，并显式标为同一公开开发集上的本地候选、不是
  未见证据。
- 前后结果：目标来源 BM25 第 6 → 第 5；BM25 Top-5 全覆盖 14/16 → 15/16；BGE 保持
  14/16；RRF 保持 16/16；三路 Top-10 均 16/16；错误型号来源均 0；Provider 调用 0。

### 验证

- `python tools/retrieval_checkup.py --check`：baseline 16 cases 通过，Provider 调用 0。
- `python tools/retrieval_checkup.py --candidate-check`：product_candidate 16 cases 通过，Provider
  调用 0。
- `python -m pytest -q -p no:cacheprovider api/tests/test_retrieval_checkup.py`：4 通过。
- `python -m pytest -q -p no:cacheprovider api/tests`：138 通过、2 项按环境条件跳过（共收集
  140 项）。
- `python -m pytest -q -p no:cacheprovider tools/tests/test_stage12_eval.py`：13 通过。
- `python tools/check_public_repo.py --scope worktree`：通过，215 files、8 public cases。
- 以上均使用主工作区已存在且通过 manifest 校验的本地 BGE 文件；没有下载模型、没有网络
  Provider 调用。测试只证明当前本地候选与登记合同，不是远端 CI 或生产证据。

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

# 复核

> 本增量触及持久化（新增内部 `run_evidence` 表）与 Provider 证据合同语义
> （transcript 接受 `authorized_real`、manifest 重钉）。按仓库规则，持久化与
> 公共合同变化在收口时需要正式独立复核；第 1 轮正式复核两项阻断已修复，
> 第 2 轮定向复核确认代码语义修复通过，唯一剩余阻断为 PR 说明与项目事实
> 未同步（本轮文档与 PR 收口处理）。本文件不作最终收口结论。

## 自复核范围

- 公开边界：`api/contracts/public-api-v1.json` 未改；`get_run` 响应键集合由
  `test_public_api.py` 精确断言钉死；`provider_observations` 不进入投影
  （`project_package` 只构造固定键的新 dict，从不拷贝未知键）。
- 安全姿态：无 Provider 调用、无凭据读取、无网络；观察记录在 transport 边界
  已做 canary 校验，持久化路径不再引入原始内容；`run_evidence` 随 30 天保留期
  与 VACUUM 一起清理，隐私语义不扩大。
- 失败关闭：伪造 / 不一致组合全部以固定 code 拒绝（offline 带 network 事实、
  real 成功 attempt 零 network、real 账单标记非 `None`、retry>0、计数与记录不
  一致、混合模式）；`finalize_transcript` 模式 / kind 错配直接失败。
- 生产姿态：`replay_only`、`provider_enabled=false`、预算常量、重试 0 均未触碰；
  本候选不启用实时模式。
- 迁移路径：既有 `_migrate_provider_calls_nullable` 与 metric_rollups 迁移不受影响；
  `run_evidence` 由 `CREATE TABLE IF NOT EXISTS` 建立，新旧库均可打开。

## 验证证据

见 `result.md` 验证一节：Fast 子集、api 全量 126 项 + 20 subtests、tools 全量
105 项（7 项环境门跳过）、公开仓扫描、探针离线 4/4 通过、夹具确定性重生成一致。

## 正式独立复核回执（第 1 轮）

- `candidate_sha`：`b30221af86be8032836e2bdf172c225dc41d79e1`（Draft PR #37
  冻结 head）。
- 复核范围与风险：冻结候选的合同语义、内部持久化、公开边界与安全姿态全量
  复核；标准增量 `R0`，触及持久化与证据合同语义（高影响门）。
- 已通过的 Checks：`governance` / `web` / `api` / `containers` 全部 SUCCESS
  （2026-07-28T14:11–14:12Z，run 30367109161；`publish` 按 Draft 规则跳过）。
- findings：
  1. **阻断**（费用 / 结论真实性；可批准入口 `validate_transcript`，位于证据
     真实性威胁模型内）：`_validate_attempt_mode_facts` 强制
     `paid_call_performed==(status=="succeeded")`、`actual_paid_cost_cny_nanos==0`，
     与已评审 transport 观察（real 模式两者恒 `None`、`billing_status` 枚举）
     不一致：忠实记录必被拒，能通过合同的记录必含 transport 从未主张的账单
     断言；失败矩阵同时拒绝 transport 实际可产生的
     `provider_response_too_large`（无接收事实形状）、
     `provider_credential_missing`（不在 `FAILURE_CODES`）与零 network 的
     `provider_transport_error`，transcript 层 `network_attempt_count>=1`
     进一步拒绝忠实的 credential_missing transcript。
  2. **阻断**（流程 / 结论真实性）：`docs/status.md`、本目录 `result.md`、
     `ROADMAP.md` 停留在推送前状态，本回执未入库前后续收口将基于错误事实。
- 结论边界：候选变化使本回执失效；修复后只对原 finding 与覆盖 diff 复核。

> 回执来源：复核结论经用户在个人 Work 转达；修复会话已逐条对冻结 head 代码
> 核实成立（transport `deepseek.py` 观察构造 / 校验器 vs 合同 `contract.py`
> 事实约束与失败矩阵）。

## 阻断修复复核要点（第 2 轮定向范围）

- 合同 diff 仅限 `_validate_attempt_mode_facts` real 分支、失败矩阵
  （`provider_credential_missing` 新增分支、`provider_response_too_large`
  双形状）、`FAILURE_CODES` 与 transcript real 计数下界；offline 逐条不变由
  既有测试钉定。
- 测试 diff：`test_real_run_transcript.py`（11 → 18 例）。
- 文档 diff：本目录与 `docs/status.md`、`ROADMAP.md`。
- `qa.py` / `ticket.py` / `runs.py` / 夹具 / manifest / 公开合同未变，不重复
  复核。

## 正式独立复核回执（第 2 轮，定向）

- `candidate_sha`：`b49e379a45ca0b99d38c152eff60e543deb78274`（复核时 PR #37
  head；代码修复为 `9c7ed59`，其上仅文档同步）。
- 复核范围：仅两项原 finding 与覆盖 diff（`contract.py`、
  `test_real_run_transcript.py`、本目录与状态 / 路线文档）；未触及部分不重复
  复核。
- 已通过的 Checks：`governance` / `web` / `api` / `containers` 全部 SUCCESS
  （run 30421455186，新 head；`publish` 按 Draft 规则跳过）。
- 结论：`BLOCKED`。
  1. finding 1（合同忠实性）：**修复确认通过**。real 模式
     `paid_call_performed` 恒为 `None`（transport 永不确知是否计费），
     `actual_paid_cost_cny_nanos` 仅允许 `None`（未知）/ `0`（无已确认
     计费）；失败矩阵覆盖 transport 可产生组合（`provider_credential_missing`
     入 `FAILURE_CODES`、`provider_response_too_large` 双形状、零 network
     `provider_transport_error`）；语义由 `test_real_run_transcript.py`
     18 例钉定，api 全量 126 项 + 20 subtests 通过。
  2. finding 2（事实同步）：**仍成立，构成本轮唯一阻断**。复核时 PR #37
     说明与本目录外的项目权威状态仍停在旧候选（旧语义"付费标记仅成功、
     实际账单恒 0"、11 例 / 119 项），结论真实性要求先完成事实收口。
- 收口动作与边界：本轮同步 `review.md` / `result.md` / `docs/status.md` /
  `ROADMAP.md` 并更新 PR #37 说明为当前事实；产品代码自 `9c7ed59` 起未变。
  收口后自查发现 `plan.md` 残留旧计划约束（real `network_attempt_count>=1`，
  与已评审合同冲突）与状态材料自指 head / CI 引用，已随本轮一并修正；PR
  说明的持久化表述同步收窄为仅 `provider_observations`。
  阻断解除以复核者确认同步无误为准；合并、部署与真实 Provider 授权仍为用户
  独立决定。

## 待复核者确认的问题（第 1 轮正式复核已处理）

- `authorized_real` attempt 事实规则是否恰为 `AuthorizedRealTransport` 可产生的
  全部组合 → 否，构成 finding 1；已按 transport 观察语义修复（账单未知三态、
  失败组合补齐），待第 2 轮定向复核确认。
- manifest 两个状态字段的新措辞是否准确描述现实 → 未列入本轮阻断 finding，
  措辞保持。
- 内部证据表不公开读回界面是否符合"可复核"最小口径 → 未列入本轮阻断
  finding；`run_evidence` 保持内部读回，无公开界面。

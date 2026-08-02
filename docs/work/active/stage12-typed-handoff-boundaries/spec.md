# Stage 12 typed handoff 边界

## Goal

把已取得产品取舍的 B 路线编译为生成前确定性边界：证据不足、跨型号专属能力、只能回答
部分问题或请求系统完成人工售后动作时，返回带 `handoff_type` 与稳定 `handoff_reason` 的
handoff package，不形成 candidate，也不构造 Provider transport。

## Non-goals

- 不运行或补跑 Stage 12，不调用 Provider，不生成新的 HOLDOUT / 模型质量结论。
- 不做 safe candidate，不修改 prompt、生成合同、检索、知识或历史 package / 聚合。
- 不把任意售后咨询都拦截；只有明确要求、宣称或确认外部履约动作时才转人工。
- 不改变既有安全、显式型号冲突和无线频段证据不足边界的 outcome。
- 不转 Ready、不合并 `main`、不部署、不发布 `product/0.1.0`。

## 边界决策表

下表只保留已消费私有集的公开案例 ID 与结构类别；公开回归用等价合成措辞验证，不写入
私有输入、期望事实、来源章节或 Provider 内容。

| 场景 | 生成前机械判据 | `handoff_type` | `handoff_reason` 模板 | 人工指引 |
| --- | --- | --- | --- | --- |
| `MBD-001` · 跨型号半答 | 已选 CZ-R1，但请求包含只在 CZ-R2 登记的扫拖 / 拖布 / 水箱能力 | `model_scope` | `model_scope_conflict` | 核对型号；不要用 R2 能力补写 R1 答案 |
| `MBD-002` · 近似边界反推 | 已选 CZ-R2，询问续扫能力，但批准资料只登记了 CZ-R1 的否定事实，未登记 CZ-R2 结论 | `evidence_gap` | `unsupported_claim` | 核对批准规格；不得从另一型号反向推断 |
| `IE-001` · 未登记能力 | 询问语音助手 / 音箱接入等批准资料未登记的能力 | `evidence_gap` | `unsupported_claim` | 核对批准规格；未知即转人工，不作肯定或否定猜测 |
| `FC-001` · 退换承诺 | 工单明确要求、宣称或确认换新 / 退货 / 退款履约 | `human_authority` | `after_sales_commitment` | 记录证据并交人工审核；不得声称动作已完成 |
| `FC-002` · 维修履约 | 工单明确要求、宣称或确认寄修 / 报修 / 上门维修安排 | `human_authority` | `after_sales_commitment` | 记录型号、现象、故障码与步骤；交人工安排 |
| `FC-003` · 退款执行 | 工单明确要求、宣称或确认退款执行或完成 | `human_authority` | `after_sales_commitment` | 交人工核对资格与执行状态；不得代替业务系统 |

匹配优先级固定为安全风险 → 显式型号不一致 → 型号专属能力 → 未登记能力 → 人工售后动作。
每个命中项必须携带稳定类型、reason、细粒度 `rule_id` 和 guidance；未命中继续既有生成链。

## AC

1. **WHEN** 用公开等价夹具覆盖表中六行，**THEN** 每行命中声明的 `handoff_type`、
   `handoff_reason`、`rule_id` 与 guidance。
2. **WHEN** 六行通过 `DefaultProductRunner` 执行，**THEN** 全部在 `preflight` 返回 handoff、
   `provider_call_count=0`、transport factory 调用 0，且 package 不含 answer / proposal candidate。
3. **WHEN** 执行既有安全、显式型号冲突与无线频段边界，**THEN** outcome、reason、来源与
   工单字段保持不变，只补充 typed handoff 元数据。
4. **WHEN** 执行可回答的 R1 / R2 操作问题、仅咨询售后流程或询问人工能否审核，**THEN**
   不命中新规则并继续既有生成链。
5. **WHEN** 执行公开 `GEN-DEV-MH-003`，**THEN** 关闭其已登记产品差距，返回
   `after_sales_commitment`、售后申请 / P1、既定边界来源且调用 0。
6. **WHEN** 对已消费私有 R2 六案例做 Git 外只读结构核验，**THEN** 六个 ID 全部生成前
   handoff；输出只含 ID、type、reason、rule 与调用数，不含私有正文。
7. **WHEN** 运行 API 全集、工具治理、公开扫描、园丁、泄漏专项与差异检查，**THEN** 全绿，
   Provider 调用、自动重试与费用均为 0。
8. **WHEN** 推送交付，**THEN** 只更新 `night-20260802` / Draft PR #62 并确认最终 head 四项
   required Checks 全绿；不转 Ready、不合并、不部署。

## 验证说明卡

- **问题**：B 路线能否在 Provider 构造前把六个 R2 outcome 缺口稳定转成 typed handoff，
  同时不拦截公开的可回答对照？
- **固定私有回归**：已消费集 SHA `7d730...8ab0`、既有原始记录 SHA `6eab...68af`；只读
  六个预登记案例的输入执行确定性边界，不执行 Stage 12 runner 或评分器。
- **公开输入**：六个等价合成边界例、公开 `GEN-DEV-MH-003` 及相邻负例；不含私有正文。
- **调用 / 费用**：Provider 调用 0、自动重试 0、费用 0。
- **最便宜证伪**：先让六个公开边界例在现有 evaluator 上失败；候选后逐例断言类型、reason、
  rule、guidance、零 transport 和非 candidate。
- **允许结论**：这六类已决定边界可由确定性规则生成 typed handoff，公开相邻对照未漂移。
- **禁止结论**：Stage 12 分数改善、模型答案改善、开放域泛化、线上成功率或发布成熟度。

## 回滚

候选阶段关闭 Draft PR #62 并删除 `night-20260802`；若未来合并则 revert 对应 squash。
恢复边界 evaluator、package / projection 字段、公开差距登记、测试与本任务四文件即可；历史
评测资产不变。

## 规则复述

- 用户已批准 B 路线：证据不足或只能半答时 typed handoff，不产 safe candidate。
- 私有输入、期望事实、来源章节与 Provider 原文永不进入 Git；只保留 ID 和结构结论。
- 不运行 Stage 12 / Provider，只推送既有集成分支并更新 Draft PR；不 Ready、不合并、不部署。

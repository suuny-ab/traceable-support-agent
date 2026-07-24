# 复核记录

> 状态：`pass`

正式复核只能在 Draft PR 的 `governance`、`web`、`api`、`containers` 全绿、head SHA
冻结且主 Agent 停止写入后进行。复核范围至少包括：

- 机械字段宿主推导是否错误地替代语义判断；
- 来源、事实、完整性、安全、型号、敏感输入和失败关闭是否保持；
- Provider 信封兼容是否仅覆盖正式允许的差异；
- 所有非 `stop` `finish_reason` 是否继续失败关闭，且没有解析或接受可能截断的正文；
- token 上限、请求超时与预算预留是否来自同一运行时配置并在公开身份中准确记录；
- 失败阶段 / 原因族统计是否诚实且不吞掉原始稳定原因码；
- 候选质量失败是否与执行完整性硬停止明确区分，且没有为了通过而放宽义务上限；
- 分散 attempt 的单例证据是否按候选身份准确限定，没有冒充同一次四例成功率；
- 客户可见语义跨度是否确实由 LLM 声明，而宿主只验证跨度存在、来源真实性、义务覆盖
  和确定性硬门；是否出现规则冒充语义判断或 LLM 越过安全边界；
- v10 / v13 是否被准确记录为第一阶段候选质量失败，v11 是否记录为第二阶段 `length`
  执行完整性失败，v12 是否保持未执行；
- v14 是否只被声明为合同合法 candidate，同时保留 `required_fact_missing` 和
  `passed=false`，没有冒充公开回归通过或成功率证据；
- Provider、费用、凭据、HOLDOUT、生产和公开主张是否越权；
- 外部 API 回执是否绑定固定候选、模型、调用、费用和停止条件。

## 首次正式复核

- 冻结 head：`83511d4b71c649689295a7bd88720b1bf4fd4b78`。
- CI：`governance`、`web`、`api`、`containers` 全绿；Draft `publish` 按设计跳过。
- 结论：`changes_required`。
- 阻断：P1 clause 约束在第二阶段降级为 evidence 约束；同一 evidence 中明确忽略的
  clause 可被 claim 重新引用并通过义务 / completeness。
- 修正：v15 增加宿主派生 `approved_source_spans`、QA / 工单 clause 级来源门和同
  evidence 攻击回归。
- 旧回执：候选变化后失效。
- 下一门：新 head 四项 Checks 全绿后，只读复核 finding 与覆盖 diff；在此之前不得
  声称正式复核通过。

## 针对性复核

- 冻结 head：`f59399140f54b311f5181604bba510a62f4d87aa`。
- CI：`governance`、`web`、`api`、`containers` 全绿；Draft `publish` 按设计跳过。
- 范围：原 P1 finding、`approved_source_spans` 覆盖 diff、QA / 工单 clause 级来源门、
  同 evidence 选中 / 忽略 clause 攻击回归、失败分类和相关公开主张。
- 结论：`pass`。
- Finding：`none`。
- 原 P1：已关闭。攻击构造分别稳定得到
  `top10_v8_clause_binding_invalid` 与 `ticket_v4_clause_binding_invalid`，未发现等价
  clause 身份绕过。
- 证据边界：复核证明原确定性构造路径已关闭，并且新 head 通过现有自动化与 CI；不证明
  v15 真实 Provider 兼容、公开回归质量改善、稳定成功率、Stage 12 改善、发布或用户
  实时体验验收。

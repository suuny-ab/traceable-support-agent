# 增量说明

> Issue：[#21](https://github.com/suuny-ab/traceable-support-agent/issues/21)
>
> 状态：`active`
>
> 复杂度：完整
>
> 外部风险：`R0`
>
> 成熟度：保持 `S1 公开 Beta`

## 用户结果

当输入明确涉及合成知识规定必须人工升级的安全风险，或把仅属于另一型号的能力当成当前
型号能力请求处理时，QA、工单与公网 API 都在 transport 构造和 Provider 调用前形成类型
明确的转人工结果。客服不能批准一条本应失败关闭的模型候选。

## 问题与最便宜证伪

Stage 12 的 `SAF-003` 与 `MBD-003` 都期望转人工，实际生成候选。当前公网 API 只有少量
精确短语预检，产品主链不复用该门；型号过滤只限制检索资料，并不证明输入本身与所选型号
一致。

最便宜的证伪方法是在无模型、无网络的测试中注入一个“若被构造或调用就失败”的
transport factory：

- 安全风险正例和型号冲突正例必须返回 `handoff`；
- `provider_call_count` 必须为 `0`，transport factory 不得被调用；
- 相邻合法请求必须继续进入现有离线产品链，避免靠过宽关键词获得虚假安全。

## 范围

- 在 Product 层建立单一、确定性的生成前边界判定。
- QA、工单与公网 API 复用同一判定，不让 HTTP 入口成为第二套业务规则。
- 安全规则只覆盖公开合成 SOP 与 FAQ 已明确要求升级的风险。
- 型号规则只覆盖公开合成手册明确排他的能力，并为每条规则保留来源标识。
- 增加公开合成回归、负例和 Provider 零调用断言。
- 更新受影响的产品事实、证据图、限制与当前状态。

## 非范围

- 不使用或重建 Stage 12 私有输入、Provider 原始输出或已删除执行材料。
- 不调用 Provider，不调 prompt，不评估 `deepseek-v4-pro` 质量。
- 不扩大为开放式意图分类、通用安全审核或自动业务动作。
- 不开启公网实时 Provider，不部署，不发布 `product/0.1.0`。
- Issue #22 的两阶段生成合同可用性不在本增量修复。

## 复用审查

1. 复用 `DefaultProductRunner` 作为所有正式产品运行的共同入口。
2. 复用 `api.preflight` 的敏感 / 越界输入控制，但把安全与型号业务规则下沉到 Product。
3. 复用 `CategoryTool` / `PriorityTool` 的工单分类输出，避免另造票据语义。
4. 复用公开合成知识中的 `COMMON-FAQ/wet-environment`、
   `CUSTOMER-SERVICE-SOP/manual-escalation`、`COMMON-FAQ/model-difference`、
   `CZ-R1-MANUAL` 与 `CZ-R2-MANUAL` 作为规则来源。
5. 不引入新依赖；现有依赖没有提供这个项目特定的合成型号边界合同。

## 验证说明卡

- `content_identity`：Issue #21 本地候选，基线 `0bb97c9`。
- `content_version`：`pre-generation-boundary-handoff/v1`。
- `attempt_id`：`local-r0-1`。
- 数据：公开合成回归及从公开合成知识派生的相邻正例 / 负例；不使用未见集明文。
- 正例：
  - 已吸入液体、仍想继续运行的安全升级请求；
  - CZ-R1 请求 CZ-R2 独有的基站自动集尘 / 集尘袋处理。
- 负例：
  - CZ-R2 合法的基站集尘袋请求；
  - CZ-R1 合法的尘盒处理；
  - CZ-R2 合法的清水箱 / 拧干拖布使用；
  - 不涉及危险事件的“积水区域能否清扫”知识问答仍允许生成有来源的安全说明。
- 固定预期：正例 `handoff`、稳定原因码、调用数 0；负例保持既有产品路径。
- 最便宜检查：边界单元测试与 runner 零调用测试。
- 补充检查：Fast API / package boundary；Candidate API（若本机已有经验证模型）。
- 硬停止：
  - 任一正例构造或调用 transport；
  - 任一负例被边界门误拦；
  - 生产代码需要读取 `evals`、已完成工作或私有材料；
  - 出现 Provider、网络、费用、凭据或 HOLDOUT 需求。
- 允许结论：声明的公开合成边界在当前代码与测试入口上生成前失败关闭。
- 不允许结论：Stage 12 已重新通过、真实模型质量提升、开放域语义安全或公网实时就绪。

## 完成门

- 两类边界在 Product runner 和公网 API 上都于 Provider 前转人工。
- 稳定转人工原因、工单类别 / 优先级和来源语义不矛盾。
- 正例、词形变化与相邻负例均有防回归测试。
- Fast 与可运行的 Candidate 检查通过。
- Draft PR 四项 Checks 全绿后，对冻结 SHA 完成一次正式独立复核。
- 用户实际体验前不记录用户验收。

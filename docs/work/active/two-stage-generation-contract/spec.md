# 增量说明

> Issue：[#22](https://github.com/suuny-ab/traceable-support-agent/issues/22)
>
> 状态：`active`
>
> 复杂度：完整
>
> 外部风险：`R1` 固定验证已执行并按硬停止结束
>
> 成熟度：保持 `S1 公开 Beta`

## 用户结果

在有充分公开合成证据时，QA 与工单两阶段链能够稳定形成来源绑定、义务完整且可供人工
批准的候选，而不是因为模型重复机械字段时的轻微结构偏差高比例失败关闭。安全、型号、
隐私、费用、证据不足和来源不一致仍必须转人工。

## 当前问题与证据

Stage 12 在候选生成类案例中执行 9 例，仅 1 例完全通过。公开结果将主要故障登记为：

| 层 | 原因码 | 当前含义 |
| --- | --- | --- |
| Provider 响应 | `provider_response_envelope_invalid` | Provider 返回信封不满足本地精确合同，正式执行按停止线中止 |
| 第一阶段结构 | `two_step_checklist_invalid` | 义务清单形状、证据 ID、逐字片段或大小合同失败 |
| 第一阶段分区 | `two_step_checklist_partition_incomplete` | 模型未逐子句重复记账全部已绑定证据 |
| 第二阶段绑定 | `top10_v4_obligation_binding_invalid` | 模型重复的义务—声明—来源映射不满足机械合同 |
| 正文完备 | `completeness_gate_failed` | 候选正文没有覆盖第一阶段全部逐字关键片段 |

失败关闭行为正确，但当前合同同时要求模型完成语义判断、精确摘录、子句分区和跨阶段
重复映射。初始假设是：机械记账职责过多地落在模型输出上，导致合同脆弱；信封失败则是
独立的 Provider 兼容性问题，不能用 prompt 调整掩盖。

## 最便宜证伪

先不调用任何模型，用公开合成证据和注入式 transport 建立同一批失败夹具：

- 语义义务与来源正确、但遗漏可由宿主推导的重复机械字段；
- 证据 ID、逐字事实或义务覆盖真实错误；
- Provider 合法可选字段变化与非法身份 / 结束状态 / 多 choice；
- QA 与工单的候选和失败关闭路径。

若宿主推导候选不能接纳前一类、拒绝后一类，或需要放松来源、安全与完备门，本方向立即
停止。只有离线候选通过后，才允许提交固定的外部 API 验证说明卡等待授权。

## 范围

- 为两阶段 QA / 工单建立统一的失败阶段和原因族统计。
- 减少模型在第二阶段重复第一阶段已经审定的义务 ID、证据绑定和机械投影。
- 在不放松来源与事实校验的前提下，把可确定推导的记账字段移到宿主。
- 按 Provider 当前正式文档和有界兼容性探针审查响应信封合同。
- 增加公开合成、注入式 transport 和产品入口回归。
- 在授权后直接调用外部 API；不使用本地小模型。

## 非范围

- 不读取、恢复或使用 Stage 12 私有输入和 Provider 原始输出进行调优。
- R0 阶段不调用 Provider、不产生费用、不使用凭据或网络。
- 不把 Issue #25 的生成前语义分类器混入本增量。
- 不让 LLM 覆盖确定性安全、型号、隐私、授权、预算或失败关闭结论。
- 不开启公网实时 Provider，不自动发送、退款、换新或结单。
- 不重跑 Stage 12，不发布 `product/0.1.0`，不宣称开放域质量提升。

## 复用审查

1. 复用 `product.qa.run_qa` 与 `product.ticket.run_ticket` 的两阶段编排和统一预算。
2. 复用 `generation.checklist`、`qa_contract`、`ticket_contract` 的现有严格校验器。
3. 复用注入式 transport、公开合成知识、公开回归和 Stage 12 公开聚合报告。
4. 复用 `ReservedCallBudget`、重试 0、Provider 身份和敏感反射门。
5. 不增加模型或生成依赖；宿主推导保持薄、确定且可单元测试。

## 本地验证说明卡

- `content_identity`：Issue #22 本地候选，基线
  `146e96ec5b3f45fd9b2c039aa3a3ff0426f7cad5`。
- `content_version`：`two-stage-generation-contract/v1`。
- `attempt_id`：`local-r0-1`。
- 数据：公开合成知识、公开回归和新建的公开合成合同夹具。
- Provider / model：无。
- 调用 / 重试 / 费用：`0 / 0 / 0`。
- 固定观测：每个失败必须归入稳定的阶段和原因族；可推导的重复字段不再要求模型输出；
  真实证据、事实或覆盖错误继续失败关闭。
- 硬停止：
  - 需要 Stage 12 私有输入、Provider 原始输出或凭据；
  - 任一硬门、来源校验或失败关闭语义被弱化；
  - 生产代码导入 `evals`、`tools` 或已完成工作；
  - 需要 Provider、网络或费用才能完成离线候选。
- 允许结论：候选合同在公开合成与注入式路径上减少特定机械失败，同时保持已声明硬门。
- 不允许结论：真实模型成功率提高、Stage 12 结果改变、公开实时 Provider 就绪。

## 完成门

- QA 与工单共享稳定的失败阶段 / 原因族统计。
- 宿主推导只消除冗余机械输出，不替代语义义务选择或放松来源 / 事实校验。
- 公开合成候选、真实错误和相邻失败关闭案例均有防回归测试。
- Fast、Candidate 与 Product 相关检查通过。
- 外部 API 验证说明卡在执行前冻结并取得独立授权；自动重试为 0。
- 授权执行给出候选成功、合同失败、来源 / 事实覆盖、延迟、调用数和最坏费用统计。
- Draft PR 四项 Checks 全绿后冻结 head SHA，完成一次正式独立复核。
- 未实际体验实时结果时，不记录用户验收；生产保持 `replay_only`。

## 外部 API 验证说明卡

> 状态：`executed_hard_stopped`
>
> 执行权限：已消费并关闭；不得恢复或使用剩余额度

固定执行合同：

- 目的：验证 Issue #22 两阶段生成合同候选与指定外部模型 API 的兼容性和候选可用性。
- `content_identity`：
  `f67099f871a31b6cf00b6881422744a8240519f0`。
- `content_version`：`two-stage-generation-contract/v1`。
- `attempt_id`：`issue22-public-synthetic-api-1`。
- Provider / model / endpoint：仓库当前合同固定的 `deepseek` /
  `deepseek-v4-pro` / `https://api.deepseek.com/chat/completions`。
- 当前价格快照：仓库记录的 `deepseek-official-cny-2026-07-15-v1`，已于
  `2026-07-24` 通过 DeepSeek 当前中文官方
  [模型与价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)、
  [Chat Completion](https://api-docs.deepseek.com/api/create-chat-completion/) 和
  [JSON Output](https://api-docs.deepseek.com/zh-cn/guides/json_mode/) 文档复核。
  当前价格仍为缓存命中 `¥0.025`、未命中 `¥3`、输出 `¥6` / 百万 tokens；型号、
  端点或价格任一变化都使本卡失效，必须修订并重新取得授权。
- 数据边界：只允许公开合成知识与本增量的公开合成开发 / 回归案例。
- 固定案例：`GEN-DEV-QA-003`、`GEN-DEV-QA-006`、`GEN-DEV-TK-001`、
  `GEN-DEV-TK-006`；公开套件 SHA-256：
  `5fd3042f90c708d84cc9cb0f859c086feeab2b4fbac42fdc86b1c12123946440`。
- 禁止材料：Stage 12 私有输入、已消费 HOLDOUT、Provider 历史原始输出、凭据和真实
  客户数据。
- 调用方式：直接调用外部 API，不使用本地小模型；自动重试 `0`。
- 调用 / 费用：案例最多 `4`、每例最多 `2` 次、总调用最多 `8`；每例预留最坏费用
  `¥0.70`，精确总最坏费用 `¥2.80 CNY`。任何较低运行上限按预留费用在调用前停止。
- 超时：第一阶段每次 `30s`、第二阶段每次 `180s`；四例顺序执行的理论总超时上界
  `840s`，记录各次实际延迟。
- prompt SHA-256：
  - 第一阶段：
    `21752f7455c7c1f073db9b23bb92d9ea68aaa7a54d64ae052076b2aa8a49448c`
  - QA 第二阶段：
    `b4e1f3cd7ea5f555c4a73af6bf6edc81432650a7672dae41e9d8ab651f37b711`
  - 工单第二阶段：
    `120f6fc992cc8caff1369203916e0f6463da703b88621259f78725d60bde227f`
  - prompt 集：
    `72954fa1ae4d2f8f330a872c43f467c3d7686d536591ec35b0e8b6b994bec28e`
- 执行顺序：只运行新候选，不重复付费运行旧合同。Stage 12 的既有聚合只说明旧合同曾
  高比例失败，本探针不能形成新旧成功率对照结论。
- 通过观测：4 例均形成 candidate；使用来源章节精确匹配公开预期；QA 所需事实逐字
  出现在客户正文；生成合同失败为 0；调用和费用不越界。
- 生产：保持 `replay_only`，本卡不授权生产开关或部署。
- 硬停止：候选身份 / 执行镜像 / Provider 合同 / 数据 SHA / prompt SHA / 预算 /
  输入包不一致；敏感反射；第一个 Provider 信封或未分类执行失败；任一确定性安全、
  型号、来源或失败关闭不变量失败。普通候选质量失败继续收集其余固定案例。
- 允许结论：固定候选在这 4 个公开合成案例上与指定 API 兼容或不兼容，以及观测到的
  来源、事实覆盖、失败分类、调用、延迟和费用。
- 不允许结论：Stage 12 分数改变、开放域质量提升、生产实时就绪、`product/0.1.0`
  可发布或用户验收通过。
- `execution_identity`：
  `sha256:01b1ad5f43918a23d66dd14a022d03b329f0e54d0ccd7e5988640abee1c2bbe9`。
- `last_verified_checkpoint`：
  `case_3_enumeration_provider_response_envelope_invalid`。
- `resume_preconditions`：本 attempt 禁止恢复。任何后续执行都必须先完成本地修正或
  安全诊断候选、固定新的代码 / 镜像 / prompt / schema 身份，建立新 `attempt_id` 并
  重新取得独立授权。
- `restart_scope`：任何硬停止后不消费剩余额度；保留失败回执，修复并重新冻结候选、
  建立新 `attempt_id`、重新授权后从第 1 例开始。

上述执行镜像由固定代码 SHA 构建。锁定依赖文件 SHA-256 为
`c23979d95c9429e098d13a8ac5f8cdd807eb2c1d9fb956c0a162013bfe44bb0d`；BGE 检索资产
清单 SHA-256 为
`c25626d58149bd63c8081f11ca7876f18a2b4a8b3d13ee278cc5ac9ea1d5326e`，声明解包后
总字节数 `95,332,206`。该 BGE 只用于既有检索，不执行生成或语义分类。

## 执行结果

- 执行案例 `3/4`，调用 `4/8`，自动重试 `0`，硬停止：
  `execution_integrity_failure_stop`。
- 案例结果：第一例 checklist shape handoff；第二例 candidate 但缺 2 条公开必需事实；
  第三例 Provider envelope handoff 并停止；第四例未执行。
- 成功解析 usage 的估算费用 `¥0.075783`；三例最坏预留 `¥0.359697`。失败调用的
  实际账单未知，不能把 usage 估算当作全部费用或发票。
- 公开报告 SHA-256：
  `c44ba1f50b9fb8cd265045c119854a2e98657649c815677330ea42d01bb7d05b`。
- 私有记录 SHA-256：
  `ae727603242d0b163cdc59121c39f89d328294aea1a6c8102b6e028dcc27627d`。

本卡和用户授权已经消费完毕。剩余 4 次上限不是可恢复额度；任何后续 Provider 调用都
必须使用新卡和新授权。

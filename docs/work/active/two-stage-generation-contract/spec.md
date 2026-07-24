# 增量说明

> Issue：[#22](https://github.com/suuny-ab/traceable-support-agent/issues/22)
>
> 状态：`active`
>
> 复杂度：完整
>
> 外部风险：语义跨度 ticket v3 单例通过；QA v4 因第一阶段 checklist 失败未触达
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
- 超时（事后更正）：执行镜像的两阶段运行时实际均使用 `180s`，四例顺序执行的理论
  总超时上界为 `1,440s`。原卡误把 `generation.checklist` 中当时未被产品调用的
  `30s` 常量写成第一阶段运行时超时；这未扩大调用 / 费用上限，但使时限记录不准确，
  后续卡片必须直接冻结并公开运行时请求配置。
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
- 案例结果：第一例 checklist shape handoff；第二例形成 candidate，但当时的评分器将
  NFKC 标点差异误报为缺少 2 条公开事实；第三例 Provider envelope handoff 并停止；
  第四例未执行。
- 成功解析 usage 的估算费用 `¥0.075783`；三例最坏预留 `¥0.359697`。失败调用的
  实际账单未知，不能把 usage 估算当作全部费用或发票。
- 公开报告 SHA-256：
  `c44ba1f50b9fb8cd265045c119854a2e98657649c815677330ea42d01bb7d05b`。
- 私有记录 SHA-256：
  `ae727603242d0b163cdc59121c39f89d328294aea1a6c8102b6e028dcc27627d`。

本卡和用户授权已经消费完毕。剩余 4 次上限不是可恢复额度；任何后续 Provider 调用都
必须使用新卡和新授权。

## 外部 API 诊断说明卡 v2

> 状态：`executed_hard_stopped`
>
> 执行权限：已消费并关闭；不得恢复或使用剩余额度

- 目的：仅获得 `GEN-DEV-QA-003` checklist 子合同和 `GEN-DEV-TK-001` Provider
  信封的隐私安全细分原因码，并验证 NFKC 评分修正没有影响来源 / 预算硬门。
- `content_identity`：
  `221c2df07736f0b8add23203295b8e1912deb462`。
- `execution_identity`：
  `sha256:f923ebc9546de7b90c782d30ba33112add981f4313a62e93f2c876bc02b4db68`。
- `content_version`：`two-stage-generation-contract/v2-diagnostic`。
- `attempt_id`：`issue22-public-synthetic-diagnostic-2`。
- Provider / model / endpoint：`deepseek` / `deepseek-v4-pro` /
  `https://api.deepseek.com/chat/completions`；沿用 `2026-07-24` 已复核的官方 CNY
  价格合同。
- 数据：只使用公开套件中 `GEN-DEV-QA-003`、`GEN-DEV-TK-001`；套件 SHA-256
  保持
  `5fd3042f90c708d84cc9cb0f859c086feeab2b4fbac42fdc86b1c12123946440`。
- prompt 与 response schema：三组 prompt 哈希保持第一次卡片不变；报告升级为
  `generation-contract-probe-report-v2`，只新增安全原因码、transport 观察与计价覆盖
  统计。
- 调用 / 费用：最多 2 例、每例最多 2 次、总调用最多 4；每例最坏预留 `¥0.70`，
  总最坏费用 `¥1.40 CNY`；自动重试 0。
- 执行顺序：先 QA checklist 失败例，后工单 Provider 信封失败例。普通候选合同失败继续
  到第二例；任一 Provider / transport 执行完整性失败立即停止。
- 公开记录：案例 ID、稳定子码、来源章节、调用数、HTTP 状态、响应是否收到、每次延迟、
  成功解析 usage 的调用数、未计价调用数、预留与 usage 估算。正文、推理、凭据和原始
  Provider 信封不得进入公开报告或 Git。
- 允许结论：具体失败属于哪个已定义的 checklist / Provider 信封子合同；NFKC 评分在
  固定公开事实上是否通过。
- 不允许结论：两阶段质量已经改善、四例全通过、Stage 12 改变、生产实时就绪、发布或
  用户验收。
- 硬停止与 restart：沿用第一次卡片；本 attempt 失败后不得使用剩余额度，必须建立新
  候选、新 attempt 和新授权。
- `last_verified_checkpoint`：`v2_candidate_image_offline_verified`。

### v2 执行结果

- 用户独立授权后执行固定 `2/2` 例、调用 `3/4`、自动重试 `0`；第 2 例的第 1 次响应
  触发 `execution_integrity_failure_stop`，剩余 1 次上限作废。
- `GEN-DEV-QA-003` 两次响应均为 HTTP 200，形成 candidate，公开必需事实完整；候选使用
  `COMMON-FAQ/map-recovery`、`CZ-R1-MANUAL/reset`，并额外使用直接支持轮组检查的
  `FAULT-CODES/e101-wheel-blocked`。v2 精确集合评分因此误报
  `source_sections_mismatch`；v3 只读离线重评分通过。
- `GEN-DEV-TK-001` 第一次响应为 HTTP 200，但在内容解析前以
  `provider_response_finish_reason_invalid` 失败关闭；v2 仍不能区分官方列出的 4 种
  非 `stop` 原因。
- 三次 Provider 延迟分别为 `88,966ms`、`69,672ms`、`120,146ms`，合计
  `278,784ms`。成功解析 usage 的 2 次调用估算 `¥0.0856242`，1 次未获得 usage；
  两例预留合计 `¥0.279288`，实际账单仍待账号侧确认。
- v2 报告把 transport 的 `provider_response_received` 错投影为不存在的
  `response_received` 字段，因此公开值为 `null`；HTTP 200 和私有安全观察仍证明响应
  已收到。v3 已修正字段投影，但不改写既有回执。
- 公开报告 SHA-256：
  `27d5966a5eec74cdedc47e94ae5f4e650fa2df19d015eb94337fda13f70421ff`。
- 私有记录 SHA-256：
  `2396b0ed8367a07f10c0f408be943675ede3d8962c2d108aaf914e2d975fc841`。

本卡和授权已经消费完毕。任何后续 Provider 调用都必须使用新候选、新 attempt 和新授权。

## 外部 API 诊断说明卡 v3

> 状态：`executed_hard_stopped`
>
> 执行权限：已消费并关闭；不得恢复或使用剩余额度

- 目的：只对 `GEN-DEV-TK-001` 复现一次，区分官方允许的 `length`、
  `content_filter`、`tool_calls`、`insufficient_system_resource` 与未知
  `finish_reason`，同时验证安全 transport 的响应接收字段投影；所有非 `stop` 结果继续
  失败关闭。
- `content_identity`：
  `47f9fa35243b81f293f69ff39abbb063bc5c75a8`。
- `execution_identity`：
  `sha256:76f7a3f979b328d30e125bce4ed698c418532780072f114ec98f698596483bb6`。
- `content_version`：`two-stage-generation-contract/v3-finish-diagnostic`。
- `attempt_id`：`issue22-public-synthetic-finish-reason-3`。
- Provider / model / endpoint：`deepseek` / `deepseek-v4-pro` /
  `https://api.deepseek.com/chat/completions`；价格沿用 `2026-07-24` 已复核的官方 CNY
  合同。官方 Chat Completion 明确列出上述 4 种非成功停止原因；`length` 的正文可能被
  截断，本候选不会接受或解析为成功。
- 数据：只使用公开套件中的 `GEN-DEV-TK-001`；套件 SHA-256：
  `5fd3042f90c708d84cc9cb0f859c086feeab2b4fbac42fdc86b1c12123946440`。
- prompt：三组 SHA-256 和 prompt 集保持 v2 不变；不调整 prompt、thinking 或
  `max_tokens`，避免把原因识别和行为修复混在一次 attempt。
- 报告：`generation-contract-probe-report-v3`；公开实际使用的来源章节、
  `response_received`、HTTP 状态、稳定原因码、调用数、延迟和计价覆盖；不公开正文、
  推理、凭据或原始 Provider 信封。
- 调用 / 费用：最多 1 例、每例最多 2 次、总调用最多 2；最坏预留 `¥0.70 CNY`；
  自动重试 `0`。
- 执行：第一阶段若为任一非 `stop` 或 Provider / transport 完整性失败，立即硬停止；
  只有第一阶段合法 `stop` 且 checklist 合同通过时才允许第二次调用。
- 允许结论：该固定响应属于哪个官方非成功停止原因，或工单两阶段能否在本候选下形成
  candidate；QA-003 已由既有包离线证明，无需重复付费。
- 不允许结论：已修复截断 / 过滤 / 资源问题、四例成功率、Stage 12 改变、生产实时就绪、
  发布或用户验收。
- restart：本 attempt 一经执行即关闭，剩余额度不得复用；任何行为修复必须另建候选、
  attempt 和授权。
- `last_verified_checkpoint`：`v3_candidate_image_offline_verified`。

### v3 执行结果

- 用户独立授权后执行固定 `1/1` 例、调用 `1/2`、自动重试 `0`；第一次响应触发
  `execution_integrity_failure_stop`，剩余 1 次上限作废。
- 响应为 HTTP 200、`response_received=true`、延迟 `113,708ms`，在正文解析前以
  `provider_response_finish_reason_length` 失败关闭。这证明第一阶段达到请求的
  `max_tokens=8192` 或上下文上限；当前请求体受 `65,536` 字节硬上限约束，远低于
  `deepseek-v4-pro` 的 1M 上下文，因此当前可证伪原因是输出 token 上限不足。
- 本次未获得可解析 usage，费用估算记录为 `0` 而非免费；调用前预留 `¥0.090414`，
  实际账单待账号侧确认。
- 公开报告 SHA-256：
  `8b9d4c2a0d5b7f80d4694c979f149e9b15396e3b598cb13648930478aac98951`。
- 私有记录 SHA-256：
  `6af095fc3ab83607f712648bb15ea600f510dd1e0e92748c75736747a9fca3f8`。
- 本次 `113,708ms` 延迟也证明早期卡片的第一阶段 `30s` 说明与实际镜像不一致；
  实际运行时为 `180s`。该记录缺口不改变 `length`、调用数或费用边界结论，但必须在
  下一卡片显式修正。

本卡和授权已经消费完毕。任何后续 Provider 调用都必须使用新候选、新 attempt 和新授权。

## 外部 API 长度修复验证说明卡 v4

> 状态：`executed_candidate_failed`
>
> 执行权限：已消费并关闭；不得恢复或使用剩余额度

- 目的：仅验证提高第一阶段输出额度后，`GEN-DEV-TK-001` 是否不再因
  `finish_reason=length` 停止，并能形成合法 checklist / ticket candidate 或暴露下一项
  稳定失败；不复跑已经通过的 QA。
- `content_identity`：
  `aa4cf00f2d8ef178fdbf9d0eb147a0e6861acbe6`。
- `execution_identity`：
  `sha256:0abd3e36e59600ad5167fc2f9467db6620967479c95397ca836b4b4e1fa95a7b`。
- `content_version`：`two-stage-generation-contract/v4-length-recovery`。
- `attempt_id`：`issue22-public-synthetic-length-recovery-4`。
- Provider / model / endpoint：`deepseek` / `deepseek-v4-pro` /
  `https://api.deepseek.com/chat/completions`；沿用 `2026-07-24` 已复核的官方 CNY
  价格合同。
- 数据：只使用公开套件中的 `GEN-DEV-TK-001`；套件 SHA-256：
  `5fd3042f90c708d84cc9cb0f859c086feeab2b4fbac42fdc86b1c12123946440`。
- prompt / thinking / schema：三组 prompt SHA-256 与 prompt 集保持 v3 不变，
  thinking 继续启用；第一阶段 `max_tokens` 从 `8192` 提高到 `16384`，第二阶段保持
  `8192`。预算从实际请求体读取阶段 `max_tokens`，不再把第一阶段硬编码为第二阶段值。
- 超时：两阶段每次固定 `180,000ms`；公开报告
  `generation-contract-probe-report-v4` 明确记录 `timeout_ms` 和两阶段 token 上限。
- 调用 / 费用：固定 profile `length-recovery-v4`，最多 1 例、每例最多 2 次、总调用
  最多 2；自动重试 `0`；总最坏上限 `¥0.70 CNY`。固定单例离线两阶段实际预留
  `¥0.226563`，仍在上限内。
- 执行：任一非 `stop`、Provider / transport 执行完整性、预算、来源、安全或身份失败
  立即硬停止；第一阶段合法且 checklist 通过时才允许第二次调用。
- 公开记录：案例 ID、稳定原因码、来源章节、调用数、HTTP 状态、响应接收、请求超时、
  每次延迟、成功计价 / 未计价调用、预留和 usage 估算；正文、推理、凭据和原始信封
  不得进入 Git。
- 允许结论：在这个固定公开工单上，`16384` 是否消除第一阶段 `length`，以及后续合同
  是否形成 candidate 或稳定失败。
- 不允许结论：该 token 值对所有请求充分、四例成功率、Stage 12 改变、生产实时就绪、
  发布或用户验收。
- restart：本 attempt 一经执行即关闭；任何剩余额度不得复用。
- `last_verified_checkpoint`：`v4_candidate_image_offline_verified`。

### v4 执行结果

- 用户独立授权后执行固定 `1/1` 例、调用 `1/2`、自动重试 `0`；第一阶段自然结束，
  `stop_code=null`，未触发执行完整性硬停止，剩余 1 次仍随 attempt 关闭。
- 响应为 HTTP 200、`response_received=true`、`timeout_ms=180000`、延迟
  `78,906ms`。`finish_reason=length` 已消失，证明本次 `16384` 足以完成第一阶段响应。
- 第一阶段随后以
  `enumeration_contract_failure:two_step_checklist_obligation_count_invalid`
  转人工，没有进入第二阶段。该聚合码仍不能区分义务字段类型错误、空列表或超过 8 项。
- 本次未获得可解析 usage；费用估算 `0` 不代表免费，调用前预留 `¥0.139569`，实际
  账单待账号侧确认。
- 公开报告 SHA-256：
  `33fa1ed07dac12709db1a0150aa190ae3c9651f32056b688e2522b206fa1e611`。
- 私有记录 SHA-256：
  `07609d4d112a48ceff6f11d0aa9773ae7a0152a1444b995b37f4c96a1e1b4d2f`。

本卡和授权已经消费完毕。任何后续调用必须使用新候选和新 attempt。

## 外部 API 义务数量诊断说明卡 v5

> 状态：`executed_passed`
>
> 执行权限：仅来自当前 Git 仓库之外的用户会话常设授权；本文件不授予权限

- 目的：只对 `GEN-DEV-TK-001` 复现一次，把 v4 的义务数量聚合失败区分为
  `obligations_type_invalid`、`obligation_count_empty` 或
  `obligation_count_exceeded`，不保存或公开模型正文。
- `content_identity`：
  `7997c7474360b0fbc62f555676600689097913d7`。
- `execution_identity`：
  `sha256:2fc6f4274c7557e679944e1e7c7b8a97a0f019aedea3c093bda4d69f1531b479`。
- `content_version`：`two-stage-generation-contract/v5-obligation-count`。
- `attempt_id`：`issue22-public-synthetic-obligation-count-5`。
- Provider / model / endpoint：`deepseek` / `deepseek-v4-pro` /
  `https://api.deepseek.com/chat/completions`。
- 数据：只使用公开套件中的 `GEN-DEV-TK-001`；套件 SHA-256：
  `5fd3042f90c708d84cc9cb0f859c086feeab2b4fbac42fdc86b1c12123946440`。
- prompt、thinking、response schema 和请求配置均与 v4 相同：第一阶段 `16384`、
  第二阶段 `8192`、两阶段超时 `180,000ms`；只改变隐私安全失败子码。
- 调用 / 费用：固定 profile `obligation-count-v5`，最多 1 例、每例最多 2 次、总调用
  最多 2；自动重试 `0`；总最坏上限 `¥0.70 CNY`，低于用户对本增量每个新 attempt
  `¥1` 的仓外常设上限。
- 执行：任一非 `stop`、Provider / transport、身份、预算、安全或来源完整性失败立即
  硬停止；第一阶段合法且 checklist 通过时才允许第二次调用。
- 公开记录：`generation-contract-probe-report-v4` 的安全请求配置、子码、HTTP 状态、
  响应接收、延迟、来源、调用和费用覆盖；不含正文、推理、凭据或原始信封。
- 允许结论：v4 聚合失败属于哪一个数量子合同，或模型本次形成合法 checklist 后进入
  第二阶段。
- 不允许结论：义务上限应该放宽、prompt 已修复、开放域成功率、Stage 12、生产或发布。
- restart：本 attempt 执行一次即关闭；不自动重跑。
- `last_verified_checkpoint`：`v5_candidate_image_offline_verified`。

### v5 执行结果

- 固定 TK-001 执行 `1/1`、调用 `2/2`、自动重试 `0`，没有停止码；第一阶段 checklist
  和第二阶段 ticket 均通过并形成 candidate。
- 两次均 HTTP 200、`response_received=true`；延迟 `74,139ms` 和 `64,209ms`。
- 两次调用均获得 usage；估算费用 `¥0.0792522`，预留 `¥0.231147`，未越过
  `¥0.70` 上限。估算不是账号账单。
- 公开报告 SHA-256：
  `b6c6ede2441274c194b7cb4874751d3385ca3788ad94f135590b75fbaf629108`。
- 私有记录 SHA-256：
  `4266086013ccbd9e00ff01cda0b73db06f3b34c105d57ff5114efa3b041b5f18`。

本卡已经消费并关闭。它证明同配置可以成功，不证明 v4 数量失败的具体子合同或稳定成功率。

## 外部 API 剩余工单验证说明卡 v6

> 状态：`executed_candidate_failed`
>
> 执行权限：仅来自当前 Git 仓库之外的用户会话常设授权；本文件不授予权限

- 目的：只运行原始四例中从未执行过的 `GEN-DEV-TK-006`，获得合法 ticket candidate
  或当前稳定失败分类；不重复付费运行已有合法候选的三个案例。
- `content_identity`：
  `29619efab39f1bc7aab5e4c8631b71d55f444598`。
- `execution_identity`：
  `sha256:44d1a7fad122967e1730b72a39356d4d0c74e3761f1748a4c2b9d83eb3392159`。
- `content_version`：`two-stage-generation-contract/v6-remaining-ticket`。
- `attempt_id`：`issue22-public-synthetic-remaining-ticket-6`。
- Provider / model / endpoint：`deepseek` / `deepseek-v4-pro` /
  `https://api.deepseek.com/chat/completions`。
- 数据：只使用公开套件中的 `GEN-DEV-TK-006`；套件 SHA-256：
  `5fd3042f90c708d84cc9cb0f859c086feeab2b4fbac42fdc86b1c12123946440`。
- prompt / 请求：与 v5 相同；第一阶段 `16384`、第二阶段 `8192`、两阶段超时
  `180,000ms`，prompt 集 SHA-256：
  `72954fa1ae4d2f8f330a872c43f467c3d7686d536591ec35b0e8b6b994bec28e`。
- 调用 / 费用：固定 profile `remaining-ticket-v6`，最多 1 例、每例最多 2 次、总调用
  最多 2；自动重试 `0`；总最坏上限 `¥0.70 CNY`，低于当前仓外常设授权的每 attempt
  `¥1` 上限。
- 执行：任一非 `stop`、Provider / transport、身份、预算、安全或来源完整性失败立即
  硬停止；第一阶段合法且 checklist 通过时才允许第二次调用。
- 公开记录：只保存安全请求配置、稳定失败码、HTTP 状态、响应接收、延迟、来源、调用
  和费用覆盖；不公开正文、推理、凭据或原始信封。
- 允许结论：TK-006 在该冻结候选上形成合法 candidate，或暴露一项有界合同 / 执行失败。
- 不允许结论：四例来自同一 attempt、稳定成功率、开放域质量、Stage 12、生产或发布。
- restart：本 attempt 执行一次即关闭；不自动重跑。
- `last_verified_checkpoint`：`v6_candidate_image_offline_verified`。

### v6 执行结果

- 固定 TK-006 执行 `1/1`、调用 `2/2`、自动重试 `0`；两次 HTTP 200，
  `response_received=true`，延迟 `87,693ms` 和 `32,402ms`。
- checklist 与 ticket 合同均通过，最后以 `completeness_gate_failed` 转人工；没有
  执行完整性停止。
- 两次调用均获得 usage；估算费用 `¥0.0731974`，预留 `¥0.225825`，未越过
  `¥0.70` 上限。估算不是账号账单。
- 公开报告 SHA-256：
  `92f429a4b20412b865e9780be71792a36b3b7aa3121339014fdf590ce1840b47`。
- 私有记录 SHA-256：
  `3e064d74db3c5cf0001173d7472c3d2e40b5be6640137ebb4410812736271493`。

本卡已经消费并关闭；禁止读取仓外原始正文调优，不得恢复或自动重跑。

## 外部 API completeness 独立复现说明卡 v7

> 状态：`executed_passed`
>
> 执行权限：仅来自当前 Git 仓库之外的用户会话常设授权；本文件不授予权限

- 目的：使用同一冻结候选再次运行 TK-006 一次，只判断 v6 的
  `completeness_gate_failed` 是否独立复现；不读取或公开正文。
- `content_identity`：
  `29619efab39f1bc7aab5e4c8631b71d55f444598`。
- `execution_identity`：
  `sha256:44d1a7fad122967e1730b72a39356d4d0c74e3761f1748a4c2b9d83eb3392159`。
- `content_version`：`two-stage-generation-contract/v7-completeness-repro`。
- `attempt_id`：`issue22-public-synthetic-completeness-repro-7`。
- Provider / model / endpoint：`deepseek` / `deepseek-v4-pro` /
  `https://api.deepseek.com/chat/completions`。
- 数据：只使用公开套件中的 `GEN-DEV-TK-006`；套件 SHA-256：
  `5fd3042f90c708d84cc9cb0f859c086feeab2b4fbac42fdc86b1c12123946440`。
- prompt / 请求：与 v6 完全相同；第一阶段 `16384`、第二阶段 `8192`、两阶段超时
  `180,000ms`，prompt 集 SHA-256：
  `72954fa1ae4d2f8f330a872c43f467c3d7686d536591ec35b0e8b6b994bec28e`。
- 调用 / 费用：复用 `remaining-ticket-v6` 单例 profile，最多 1 例、每例最多 2 次、
  总调用最多 2；自动重试 `0`；总最坏上限 `¥0.70 CNY`，低于当前仓外常设授权的每
  attempt `¥1` 上限。
- 执行：任一非 `stop`、Provider / transport、身份、预算、安全或来源完整性失败立即
  硬停止；第一阶段合法且 checklist 通过时才允许第二次调用。
- 公开记录：只保存安全请求配置、稳定失败码、HTTP 状态、响应接收、延迟、来源、调用
  和费用覆盖；不公开正文、推理、凭据或原始信封。
- 允许结论：同一候选连续两次 completeness 失败，或 TK-006 结果存在通过 / 失败波动。
- 不允许结论：稳定成功率、具体缺失正文、开放域质量、Stage 12、生产或发布。
- restart：本 attempt 执行一次即关闭；不自动重跑。
- `last_verified_checkpoint`：`v7_same_candidate_identity_verified`。

### v7 执行结果

- 固定 TK-006 执行 `1/1`、调用 `2/2`、自动重试 `0`；两次 HTTP 200，
  `response_received=true`，延迟 `61,918ms` 和 `48,851ms`。
- checklist、ticket 和 completeness gate 全部通过并形成 candidate；没有停止码。
- 两次调用均获得 usage；估算费用 `¥0.0623356`，预留 `¥0.225795`，未越过
  `¥0.70` 上限。估算不是账号账单。
- 公开报告 SHA-256：
  `c99e8aab8e66e02d8cbc1e0749c22fc77286dcbdfd28ce02dcabdaae5bf00f53`。
- 私有记录 SHA-256：
  `e9aeb1d837481b0b476af2e30341b3622368b01912f3a8ac7aa73e093fa9e1d9`。

本卡已经消费并关闭。v6 与 v7 共同证明同一候选存在一次 completeness 失败、一次通过；
不得将两次样本写成稳定成功率，也不再重复付费运行该版本。

## 客户可见语义跨度本地验证说明卡 v8

> 状态：`candidate_verified_r0`
>
> 执行权限：无 Provider 调用

- 目的：让外部 LLM 为每条已绑定来源 claim 声明客户文本中的连续语义表达片段；宿主
  验证跨度存在、来源逐字可证、义务 / 来源绑定完整，不再比较客户文本是否逐字包含
  checklist 的 key_elements。
- 数据：只使用公开合成夹具；禁止读取 v6 / v7 或任何历史 Provider 原始正文。
- Provider / 调用 / 重试 / 费用：`无 / 0 / 0 / ¥0`。
- 必须接受：客户文本对来源事实做语义等价改写，且模型明确绑定真实客户可见片段。
- 必须拒绝：客户片段不在正文、来源片段不在证据、错误义务 / 来源绑定、漏义务、敏感
  内容，以及任何确定性安全 / 型号 / 预算 / Provider 边界变化。
- 架构边界：LLM 负责来源主张与客户表达之间的语义映射；宿主负责精确存在性、身份、
  集合覆盖、来源真实性和全部硬门。候选仍只供人工批准。
- 停止：需要读取历史原始正文、需要自动业务动作、或不能在不放松硬门的前提下接受
  合法改写。
- 允许结论：该混合合同在公开合成与注入式路径上消除逐字改写脆弱性。
- 不允许结论：真实模型稳定性、开放域质量、Stage 12、生产或发布。

### v8 候选结果

- QA / ticket schema 分别升级为 `retrieved-top10-qa-result-v4` /
  `ticket-proposal-result-v3`；新增 LLM 声明的 `customer_visible_span_text`。
- 合法客户化改写通过；不存在的客户跨度、错误来源和漏义务继续失败关闭。
- 代码 `62f5fe08be8889546410d87c443ebdd5908b40d4`；镜像
  `sha256:91931aba5b0bc57bd6dab877049dffb0c8697212067aafa6f8853f844f7f7efa`，
  revision 与非 root 用户匹配。
- API `95` 项和 20 个子测试、工具 `76` 项及公开扫描通过；镜像无网络检索 8/8，
  Provider 调用 `0`。
- 长期决定：`docs/decisions/ADR-0006-llm-semantic-coverage-host-hard-gates.md`。

## 外部 API 语义跨度工单验证说明卡 v9

> 状态：`executed_passed`
>
> 执行权限：仅来自当前 Git 仓库之外的用户会话常设授权；本文件不授予权限

- 目的：只在 `GEN-DEV-TK-006` 验证真实模型是否遵守 ticket v3
  `customer_visible_span_text` 合同，并形成合法 candidate 或安全分类失败。
- `content_identity`：
  `62f5fe08be8889546410d87c443ebdd5908b40d4`。
- `execution_identity`：
  `sha256:91931aba5b0bc57bd6dab877049dffb0c8697212067aafa6f8853f844f7f7efa`。
- `content_version`：`two-stage-generation-contract/v9-semantic-ticket`。
- `attempt_id`：`issue22-public-synthetic-semantic-ticket-9`。
- Provider / model / endpoint：`deepseek` / `deepseek-v4-pro` /
  `https://api.deepseek.com/chat/completions`。
- 数据：只使用公开套件中的 `GEN-DEV-TK-006`；套件 SHA-256：
  `5fd3042f90c708d84cc9cb0f859c086feeab2b4fbac42fdc86b1c12123946440`。
- prompt SHA-256：checklist
  `21752f7455c7c1f073db9b23bb92d9ea68aaa7a54d64ae052076b2aa8a49448c`，ticket
  `52510b64bf924338e88beb1a1c561143206d85189ae2f5a363d903f060868f21`，集合
  `a52d2777acfdc6a3fdd5b37992aa84aaf214317e109bc0c4ba2271b7c1c0db2e`。
- 请求：第一阶段 `16384`、第二阶段 `8192`、两阶段超时 `180,000ms`。
- 调用 / 费用：复用只选择 TK-006 的 `remaining-ticket-v6` profile，最多 1 例、每例
  最多 2 次、总调用最多 2；自动重试 `0`；总最坏上限 `¥0.70 CNY`，低于当前仓外
  常设授权的每 attempt `¥1` 上限。
- 执行：任一非 `stop`、Provider / transport、身份、预算、安全、来源跨度、客户跨度
  或义务覆盖失败立即硬停止或形成类型明确的合同 handoff；不读取原始正文调优。
- 公开记录：只保存安全请求配置、稳定失败码、HTTP 状态、响应接收、延迟、来源、调用
  和费用覆盖；不公开正文、推理、凭据或原始信封。
- 允许结论：ticket v3 合同在该冻结 TK-006 样本上兼容或暴露具体安全失败码。
- 不允许结论：QA 兼容、稳定成功率、开放域质量、Stage 12、生产或发布。
- restart：本 attempt 执行一次即关闭；不自动重跑。
- `last_verified_checkpoint`：`v9_semantic_ticket_image_offline_verified`。

### v9 执行结果

- 固定 TK-006 执行 `1/1`、调用 `2/2`、自动重试 `0`；两次 HTTP 200，
  `response_received=true`，延迟 `53,755ms` 和 `59,758ms`。
- ticket v3 的来源跨度、客户可见跨度、义务绑定和 completeness 全部通过并形成
  candidate；没有停止码。
- 两次调用均获得 usage；估算费用 `¥0.061045`，预留 `¥0.225795`，未越过
  `¥0.70` 上限。估算不是账号账单。
- 公开报告 SHA-256：
  `3c84041d8f212dd9084173d1d897585096ca3a10992095c5818a71889bb855df`。
- 私有记录 SHA-256：
  `7f0bfd62e56f37246907c53cb83cbfb84cd54592f30e2d9048a816c9e498bace`。

本卡已经消费并关闭；该结果不外推到 QA 或稳定成功率。

## 外部 API 语义跨度 QA 验证说明卡 v10

> 状态：`executed_candidate_failed`
>
> 执行权限：仅来自当前 Git 仓库之外的用户会话常设授权；本文件不授予权限

- 目的：只在 `GEN-DEV-QA-003` 验证真实模型是否遵守 QA v4
  `customer_visible_span_text` 合同，并形成合法 candidate 或安全分类失败。
- `content_identity`：
  `4e71fdaecf858e900831d1223857eb8ca574f97d`。
- `execution_identity`：
  `sha256:99a02f11b6d33c0c0c9605996c4871525c3f57d21b5b60ccbe5013e998b036ff`。
- `content_version`：`two-stage-generation-contract/v10-semantic-qa`。
- `attempt_id`：`issue22-public-synthetic-semantic-qa-10`。
- Provider / model / endpoint：`deepseek` / `deepseek-v4-pro` /
  `https://api.deepseek.com/chat/completions`。
- 数据：只使用公开套件中的 `GEN-DEV-QA-003`；套件 SHA-256：
  `5fd3042f90c708d84cc9cb0f859c086feeab2b4fbac42fdc86b1c12123946440`。
- prompt SHA-256：checklist
  `21752f7455c7c1f073db9b23bb92d9ea68aaa7a54d64ae052076b2aa8a49448c`，QA
  `574a7fb3e5490656fe4c71b37645df800aacd2b9d3f5300a52e303d2b8acbfed`，集合
  `a52d2777acfdc6a3fdd5b37992aa84aaf214317e109bc0c4ba2271b7c1c0db2e`。
- 请求：第一阶段 `16384`、第二阶段 `8192`、两阶段超时 `180,000ms`。
- 调用 / 费用：固定 `semantic-qa-v10` profile，最多 1 例、每例最多 2 次、总调用
  最多 2；自动重试 `0`；总最坏上限 `¥0.70 CNY`，低于当前仓外常设授权的每 attempt
  `¥1` 上限。
- 执行：任一非 `stop`、Provider / transport、身份、预算、安全、来源跨度、客户跨度
  或义务覆盖失败立即硬停止或形成类型明确的合同 handoff；不读取原始正文调优。
- 公开记录：只保存安全请求配置、稳定失败码、HTTP 状态、响应接收、延迟、来源、调用
  和费用覆盖；不公开正文、推理、凭据或原始信封。
- 允许结论：QA v4 合同在该冻结 QA-003 样本上兼容或暴露具体安全失败码。
- 不允许结论：稳定成功率、开放域质量、Stage 12、生产或发布。
- restart：本 attempt 执行一次即关闭；不自动重跑。
- `last_verified_checkpoint`：`v10_semantic_qa_image_offline_verified`。

### v10 执行结果

- 固定 QA-003 执行 `1/1`、调用 `1/2`、自动重试 `0`；第一阶段 HTTP 200、
  `response_received=true`，延迟 `84,990ms`。
- 第一阶段以
  `enumeration_contract_failure:two_step_checklist_key_elements_invalid`
  转人工；没有执行完整性停止，第二阶段未调用，QA v4 新 schema / prompt 未触达。
- 本次没有可解析 usage；费用估算 `0` 不代表免费，调用前预留 `¥0.139287`，实际账单
  未知。
- 公开报告 SHA-256：
  `b7cb9545fb5d1f314d67360ee25b05d843e349ba3675c5c7f5d7922ce0408ec3`。
- 私有记录 SHA-256：
  `e6d4d2e50e2195a0b4461c76b0b2534eff08bdf2bd470fdad47491818bcc9fb0`。

本卡已经消费并关闭。结果只说明第一阶段候选质量失败，不证明 QA v4 兼容或不兼容；
按计划不再扩大外部样本。

## checklist v4 QA 单例验证说明卡

> 执行权限：仅来自当前 Git 仓库之外的用户会话常设授权；本文件不授予权限

- 目的：只在 `GEN-DEV-QA-003` 验证 checklist v4 的义务 / clause 语义选择能否通过
  第一阶段，并继续验证 QA v4；形成合法 candidate 或安全分类失败。
- `content_identity`：`cece633a6b11af3f36a116ca3a793b0f8654b94c`。
- `execution_identity`：
  `sha256:a8cfbede1481a38a2eb97dcf0abcbc36e9ca210de01af7cc378574db90fe4bb8`。
- `content_version`：`two-stage-generation-contract/v11-semantic-checklist-qa`。
- `attempt_id`：`issue22-public-synthetic-semantic-checklist-qa-11`。
- Provider / model / endpoint：`deepseek` / `deepseek-v4-pro` /
  `https://api.deepseek.com/chat/completions`。
- 数据：只使用公开套件中的 `GEN-DEV-QA-003`；套件 SHA-256：
  `5fd3042f90c708d84cc9cb0f859c086feeab2b4fbac42fdc86b1c12123946440`。
- prompt SHA-256：checklist
  `bb9f58b196d67ab01aa43c59499136b5c6dd7576247c9c576c5e74be490908cf`，QA
  `df7200de0fdcb5ed25ec094ae7873397a4da22e1d186b9d23b7511789f913878`，集合
  `d66cd07906481faf93d9c13fa1a0b9deb262e50168e60b898c1d4f097419a7fb`。
- 请求：第一阶段 `16384`、第二阶段 `8192`、两阶段超时 `180,000ms`。
- 调用 / 费用：固定 `semantic-qa-v11` profile，最多 1 例、每例最多 2 次、总调用
  最多 2；自动重试 `0`；总最坏上限 `¥0.70 CNY`，低于仓外常设授权的每 attempt
  `¥1` 上限。
- 执行：授权、transport、身份、预算、包完整性或安全失败立即硬停止，且不启动 v12；
  合同 / 候选质量失败形成类型明确的 handoff，不读取原始正文调优。
- 公开记录：只保存安全请求配置、稳定失败码、HTTP 状态、响应接收、延迟、来源、调用
  和费用覆盖；不公开正文、推理、凭据或原始信封。
- 允许结论：checklist v4 与 QA v4 在该冻结 QA003 样本上兼容，或暴露具体安全失败码。
- 不允许结论：稳定成功率、开放域质量、Stage 12、生产、发布或用户验收。
- restart：本 attempt 执行一次即关闭；不自动重跑。
- `last_verified_checkpoint`：`v11_image_offline_verified`。

### v11 执行结果

- 固定 QA003 执行 `1/1`、调用 `2/2`、自动重试 `0`；两阶段均 HTTP 200、
  `response_received=true`，延迟 `78,188ms` / `111,182ms`。
- 第一阶段 checklist v4 通过；第二阶段以
  `generation_execution_failure:provider_response_finish_reason_length` 失败关闭，
  `stop_code=execution_integrity_failure_stop`。
- 一次调用未计价；估算 `¥0.042246`、预留 `¥0.239229`，实际账单未知。
- 公开 / 私有 SHA-256：
  `0776f4a952b3295669cdfec5f4ea1c14e5a968677a752a24d64260f77a2b49a2` /
  `ff2bd78f2d4a1a44f0d0a382ce6e9db7b9fdafc6e6df3b60b18dbce1075885ef`。

本卡已消费并关闭。按预声明硬停止，下面的 v12 卡没有执行，也不得恢复或复用。

## checklist v4 工单单例验证说明卡

> 执行权限：仅来自当前 Git 仓库之外的用户会话常设授权；本文件不授予权限

- 前置：v11 没有授权、transport、身份、预算或包完整性硬停止；候选质量 handoff 不
  阻止本独立 attempt。
- 目的：只在 `GEN-DEV-TK-006` 验证 checklist v4 与 ticket v3 的组合；形成合法
  candidate 或安全分类失败。
- `content_identity`：`cece633a6b11af3f36a116ca3a793b0f8654b94c`。
- `execution_identity`：
  `sha256:a8cfbede1481a38a2eb97dcf0abcbc36e9ca210de01af7cc378574db90fe4bb8`。
- `content_version`：`two-stage-generation-contract/v12-semantic-checklist-ticket`。
- `attempt_id`：`issue22-public-synthetic-semantic-checklist-ticket-12`。
- Provider / model / endpoint：`deepseek` / `deepseek-v4-pro` /
  `https://api.deepseek.com/chat/completions`。
- 数据：只使用公开套件中的 `GEN-DEV-TK-006`；套件 SHA-256：
  `5fd3042f90c708d84cc9cb0f859c086feeab2b4fbac42fdc86b1c12123946440`。
- prompt SHA-256：checklist
  `bb9f58b196d67ab01aa43c59499136b5c6dd7576247c9c576c5e74be490908cf`，ticket
  `52510b64bf924338e88beb1a1c561143206d85189ae2f5a363d903f060868f21`，集合
  `d66cd07906481faf93d9c13fa1a0b9deb262e50168e60b898c1d4f097419a7fb`。
- 请求：第一阶段 `16384`、第二阶段 `8192`、两阶段超时 `180,000ms`。
- 调用 / 费用：固定 `semantic-ticket-v12` profile，最多 1 例、每例最多 2 次、总调用
  最多 2；自动重试 `0`；总最坏上限 `¥0.70 CNY`，低于仓外常设授权的每 attempt
  `¥1` 上限。
- 执行：授权、transport、身份、预算、包完整性或安全失败立即硬停止；合同 / 候选质量
  失败形成类型明确的 handoff，不读取原始正文调优。
- 公开记录、不允许结论与 restart：沿用 v11；本 attempt 执行一次即关闭，不自动重跑。
- 允许结论：checklist v4 与 ticket v3 在该冻结 TK006 样本上兼容，或暴露具体安全
  失败码。
- `last_verified_checkpoint`：`v12_image_offline_verified`。

### v12 状态

`not_executed`。v11 触发执行完整性硬停止，因此没有 Provider 调用、费用或结果；旧卡
关闭，不得在新候选上复用。

## QA 第二阶段长度恢复验证说明卡

> 执行权限：仅来自当前 Git 仓库之外的用户会话常设授权；本文件不授予权限

- 目的：只在 `GEN-DEV-QA-003` 验证把 QA 第二阶段最大输出从 8K 提到 16K 后，
  Provider 是否以 `stop` 完成，并继续执行既有 QA v4 合同。
- `content_identity`：`4c3879076133cfe177924ef4604f9cff1c53907a`。
- `execution_identity`：
  `sha256:6686211b190228c3cabff7abf99b19cb7b48866d0c67a39ea245b149bb8d69f4`。
- `content_version`：`two-stage-generation-contract/v13-qa-length-recovery`。
- `attempt_id`：`issue22-public-synthetic-qa-length-recovery-13`。
- Provider / model / endpoint：`deepseek` / `deepseek-v4-pro` /
  `https://api.deepseek.com/chat/completions`。
- 数据：只使用公开套件中的 `GEN-DEV-QA-003`；套件 SHA-256：
  `5fd3042f90c708d84cc9cb0f859c086feeab2b4fbac42fdc86b1c12123946440`。
- prompt SHA-256：checklist
  `bb9f58b196d67ab01aa43c59499136b5c6dd7576247c9c576c5e74be490908cf`，QA
  `df7200de0fdcb5ed25ec094ae7873397a4da22e1d186b9d23b7511789f913878`，集合
  `d66cd07906481faf93d9c13fa1a0b9deb262e50168e60b898c1d4f097419a7fb`。
- 请求：第一阶段 `16384`、第二阶段 `16384`、两阶段超时 `180,000ms`；这是相对 v11
  唯一行为变化。
- 调用 / 费用：固定 `qa-length-recovery-v13` profile，最多 1 例、每例最多 2 次、
  总调用最多 2；自动重试 `0`；总最坏上限 `¥0.70 CNY`，低于仓外常设授权的每
  attempt `¥1` 上限。
- 执行：任一授权、transport、身份、预算、包完整性、安全或 Provider 信封失败立即
  硬停止；合同 / 候选质量失败形成类型明确的 handoff，不读取原始正文调优。
- 公开记录：只保存安全请求配置、稳定失败码、HTTP 状态、响应接收、延迟、来源、调用
  和费用覆盖；不公开正文、推理、凭据或原始信封。
- 允许结论：16K 能否消除该冻结 QA003 的第二阶段 `length`，以及随后 QA v4 是否
  兼容或暴露具体安全失败码。
- 不允许结论：稳定成功率、开放域质量、Stage 12、生产、发布或用户验收。
- restart：本 attempt 执行一次即关闭；不自动重跑。
- `last_verified_checkpoint`：`v13_image_offline_verified`。

### v13 执行结果

- 固定 QA003 执行 `1/1`、调用 `1/2`、自动重试 `0`；第一阶段 HTTP 200、
  `response_received=true`，延迟 `115,265ms`。
- 第一阶段以
  `enumeration_contract_failure:two_step_checklist_obligation_count_exceeded`
  转人工；`stop_code=null`，第二阶段未调用。
- usage 未计价；预留 `¥0.139089`，实际账单未知。
- 公开 / 私有 SHA-256：
  `52e36ebf0d4294229d8a15a438c5f29be4405b2642cf1469375dc5712ccecd2e` /
  `61f1d17dbeb972ba64da390557d5ee910f89b5e04b00f86beed2076c60bf6f0f`。

本卡已消费并关闭。它没有触达 16K 第二阶段，不允许恢复或复用额度。

## checklist 数量合同对齐验证说明卡

> 执行权限：仅来自当前 Git 仓库之外的用户会话常设授权；本文件不授予权限

- 目的：只在 `GEN-DEV-QA-003` 验证模型在 prompt 明示 1–8 项后是否遵守既有宿主
  上限，并在通过时继续验证 16K QA v4 第二阶段。
- `content_identity`：`61d6bb176c72ff9d11c4a9500fd61f8c0fb7d4fc`。
- `execution_identity`：
  `sha256:de6cd31fecd65ceb8e373340245869f75541dfbd5fed80c465253d072bd2f1e7`。
- `content_version`：`two-stage-generation-contract/v14-checklist-count-alignment`。
- `attempt_id`：`issue22-public-synthetic-checklist-count-alignment-14`。
- Provider / model / endpoint：`deepseek` / `deepseek-v4-pro` /
  `https://api.deepseek.com/chat/completions`。
- 数据：只使用公开套件中的 `GEN-DEV-QA-003`；套件 SHA-256：
  `5fd3042f90c708d84cc9cb0f859c086feeab2b4fbac42fdc86b1c12123946440`。
- prompt SHA-256：checklist
  `10a18c4e452a14b481958df0077c4df6e14653c9b98088b18708d404b29b5bca`，QA
  `df7200de0fdcb5ed25ec094ae7873397a4da22e1d186b9d23b7511789f913878`，集合
  `ef5397c33e38718cd8ad007db36ec055644da994aa61db275460c7bb1890fd62`。
- 请求：第一 / 第二阶段均 `16384`、超时 `180,000ms`；相对 v13 只改变第一阶段
  prompt 的数量边界说明。
- 调用 / 费用：固定 `checklist-count-alignment-v14` profile，最多 1 例、每例最多
  2 次、总调用最多 2；自动重试 `0`；总最坏上限 `¥0.70 CNY`，低于仓外常设授权
  的每 attempt `¥1` 上限。
- 执行：任一授权、transport、身份、预算、包完整性、安全或 Provider 信封失败立即
  硬停止；合同 / 候选质量失败形成类型明确的 handoff，不读取原始正文调优。
- 公开记录：只保存安全请求配置、稳定失败码、HTTP 状态、响应接收、延迟、来源、调用
  和费用覆盖；不公开正文、推理、凭据或原始信封。
- 允许结论：模型是否遵守该冻结样本的 1–8 项合同，以及随后 QA v4 16K 是否兼容或
  暴露具体安全失败码。
- 不允许结论：稳定成功率、开放域质量、Stage 12、生产、发布或用户验收。
- restart：本 attempt 执行一次即关闭；不自动重跑；无论结果如何不再扩大付费调参。
- `last_verified_checkpoint`：`v14_image_offline_verified`。

### v14 执行结果

- 固定 QA003 执行 `1/1`、调用 `2/2`、自动重试 `0`；两阶段均 HTTP 200、
  `response_received=true`，延迟 `76,115ms` / `56,855ms`。
- checklist v4、QA v4 和 16K 第二阶段全部通过，形成 `candidate`；
  `generation_failure=null`、`stop_code=null`。
- 公开评分为 `required_fact_missing`，probe `passed=false`；使用来源为
  `COMMON-FAQ/map-recovery`、`CZ-R1-MANUAL/reset`、
  `FAULT-CODES/e101-wheel-blocked`。
- 两次 usage 均可计价；估算 `¥0.080325`、预留 `¥0.287007`，实际账单未知。
- 公开 / 私有 SHA-256：
  `24387a028cc20073c9aa90a8e1ef2281173889b86289753db464fb0172e633c4` /
  `63d81d47c9ca83bfe94befec0ebca713fc19b3cf67471a635005881053824a87`。

本卡已消费并关闭。结果允许声明固定样本形成合同合法 candidate，不允许声明公开回归
通过或质量改善；按卡片不再扩大付费调参。

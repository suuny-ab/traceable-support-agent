# Stage 12 R6 命题 / 义务确定性审计

## Goal

对今夜唯一真实复跑中六个 `required_fact_missing` 案例逐题审计：把每条冻结事实标成案例内
稳定命题 `P<n>`，只用已消费 package 的 claim / obligation / approved clause 账本和客户可见
文本，区分真语义遗漏与有效改写造成的字面假阴性；同时形成只改评分合同的候选方案，不改实现。

## Non-goals

- 不修改 Stage 12 scorer、产品生成、prompt、检索、知识、API 或用户可见 outcome。
- 不重跑 Stage 12，不调用 Provider，不生成新模型输出，不补用量。
- 不用无约束 LLM judge，不把人工语义审计伪装成机器证明。
- 不转 Ready、不合并 `main`、不部署、不发布 `product/0.1.0`。

## AC

1. **WHEN** 读取固定复跑聚合，**THEN** 精确找到六个 `required_fact_missing` 案例，且案例集不多不少。
2. **WHEN** 展开 Git 外固定原始记录，**THEN** 每条冻结事实获得案例内命题 ID，并列出支撑它的
   obligation、approved clause 与 claim ID；公开收据不含私有输入、事实或 Provider 正文。
3. **WHEN** 判断一条命题，**THEN** 同时核对批准 clause、claim 到 obligation 的绑定和客户可见
   表达；只凭字面子串、只凭 obligation 存在或只凭 claim 自报均不够。
4. **WHEN** 六题完成，**THEN** 分别汇总真语义遗漏与字面假阴性的案例数及命题数，不用单个
   `required_fact_missing` 码代替逐题结论。
5. **WHEN** 输出修复候选，**THEN** 只提出用 proposition / obligation 绑定收据替代 visible
   substring；缺义务、缺绑定 claim、越源、伪造 ID 和结构失败继续失败关闭。
6. **WHEN** 公开证据落盘，**THEN** 只含案例 ID、case-local proposition ID、绑定 ID、哈希、
   枚举结论和边界，不含私有明文。
7. **WHEN** 完成交付，**THEN** Stage 12 定向测试、API 全集、治理、公开扫描、园丁、泄漏专项和
   差异检查全绿；Provider 调用为 0。
8. **WHEN** 推送候选，**THEN** 只更新 `night-20260802` / Draft PR #62 并确认最终 head 四项
   required Checks；不转 Ready、不合并、不部署。

## 验证说明卡

- **问题**：六个 R6 码分别是真语义遗漏，还是 ADR-0007 允许的客户化改写被字面子串误扣？
- **固定输入**：已消费私有集 SHA-256 `7d730...8ab0`、今夜原始记录 SHA-256
  `73d272e9...c850`、公开聚合 SHA-256 `b4de5028...67e8`。
- **方法**：人工逐题但规则有界；按 `P<n> → approved clause → obligation → claim → customer
  visible support` 顺序核对，并把明文改为 SHA-256 后公开。
- **调用 / 费用**：Provider 调用 0、自动重试 0、费用 0。
- **最便宜证伪**：任一命题找不到完整批准 clause、绑定 claim 或客户可见等价表达，即归真遗漏并
  停止提出全面替换方案。
- **允许结论**：只允许说明这六个已消费案例的 R6 真假分布，以及一个尚未实现的评分合同候选。
- **禁止结论**：新 Stage 12 分数、模型质量提升、开放域语义正确、线上成功率或发布成熟度。

## 回滚

候选阶段关闭 Draft PR #62 并删除 `night-20260802`；若未来合并则 revert 对应 squash。删除本
任务四文件、脱敏审计收据、冻结测试和两层状态回执即可；历史评测资产与 scorer 不改。

## 规则复述

- 已消费 Stage 12 只作回归审计；不重跑、不调用 Provider、不补跑。
- ADR-0007 的绑定存在性不是开放域真实性保证；人工语义结论必须和机器可验证的 ID / 哈希分开。
- 本切片只出方案、不改判据实现；不转 Ready、不合并、不部署。

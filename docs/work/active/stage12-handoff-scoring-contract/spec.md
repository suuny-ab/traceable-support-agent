# Stage 12 handoff 评分合同离线修复

## Goal

让 Stage 12 评分器在“冻结期望为 handoff 且产品实际也 handoff”时只评分 handoff 合同，
不再把没有客户候选的 package 套用候选来源、必需事实和工单字段合同；使用已消费私有集的
既有原始记录做一次零调用离线重评分，证明只移除切片 5 已定位的六个派生失败码。

## Non-goals

- 不修改生成、检索、知识、prompt、产品边界、运行时 package 或公开 API。
- 不重跑 Stage 12，不调用 Provider，不补题、不改冻结私有集或历史公开聚合。
- 不改变 expected handoff / actual candidate 或 expected candidate / actual handoff 的评分；
  尤其不处理 safe candidate vs typed handoff 的产品取舍。
- 不把离线重评分写成新未见评测、模型质量改善或发布结论。
- 不转 Ready、不合并 `main`、不部署、不发布 `product/0.1.0`。

## AC

1. **WHEN** expected 与 observed outcome 都是 `handoff`，**THEN** 评分器只检查 outcome、
   明确登记的 handoff reason 与预算合同，并保留实际 boundary sources 供审计；候选来源、
   required facts、category、priority 不产生失败码。
2. **WHEN** matched handoff 的 reason 与明确登记期望不同或预算超界，**THEN** 对应失败码仍然
   失败关闭，不因 profile 切换被跳过。
3. **WHEN** expected / observed outcome 不匹配，**THEN** 继续执行既有完整候选合同；生成失败
   与边界策略案例的 outcome、source、fact / ticket 失败码保持不变。
4. **WHEN** 用固定私有集与原始记录离线重评分，**THEN** 24 题全部可复算；仅 4 个 matched
   handoff 案例改变，仅移除 4 个 source、1 个 category、1 个 priority 失败码，其余 20 题
   逐题失败码完全不变。
5. **WHEN** 汇总离线重评分，**THEN** 失败码出现次数由 37 变为 31、通过题由 2 变为 6；
   明确这是同一原始 package 的评分合同回归，不是新的 Stage 12 运行或质量提升。
6. **WHEN** 检查历史证据，**THEN** `stage12-post-fix-revalidation-v1.json` 的字节与 SHA-256
   保持不变；新回执只含公开案例 ID、计数、哈希和失败码，不含私有明文。
7. **WHEN** 完成交付，**THEN** 定向测试、Stage 12 runner 测试、全量治理、公开仓扫描、
   文档园丁、泄漏专项和差异检查全绿；Provider 调用为 0。
8. **WHEN** 推送候选，**THEN** 只更新 `night-20260802` / Draft PR #62 并确认最终 head 的
   required Checks 全绿；不转 Ready、不合并、不部署。

## 验证说明卡

- **问题**：matched handoff 是否被候选专属字段错误扣分，最小 profile 分离能否只消除该类？
- **固定输入**：私有集 SHA-256
  `7d73073cd0227b0ced81398fcbadc7e5f85867a633a9654d82bd0b516c358ab0`；既有原始记录
  SHA-256 `6eab96586c03abb15366c6e8c11ef7c1dd8617c8a8aa82fa7127c1e5913368af`。
- **基线**：当前 scorer 对 24 题复算与历史公开聚合 24/24 一致；37 个失败码出现次数中，
  6 个来自 4 个 matched handoff 案例的候选专属字段。
- **方法**：不执行 runner / product / generation；直接把冻结 expected 与既有 package 交给
  `score_case`，逐题比较 before / after failure codes。
- **调用 / 费用**：Provider 调用 0、自动重试 0、费用 0；不联网。
- **最便宜证伪**：合成单元测试先钉住 matched handoff、reason / budget 失败关闭和两类 outcome
  mismatch；任一非目标案例失败码变化即停止。
- **允许结论**：新评分合同对同一批已消费原始 package 的确定性离线结果。
- **禁止结论**：模型变好、新 Stage 12 分数、线上质量、开放域泛化或发布成熟度。

## 回滚

候选阶段关闭 Draft PR #62 并删除 `night-20260802`；若未来合并则 revert 对应 squash。
恢复 `score_case`、定向测试、离线重评分回执和状态文档即可；历史聚合始终不改。

## 规则复述

- 已消费私有集只能作回归；私有输入、期望事实 / 来源 ID 和 Provider 原文永不进入 Git。
- 只修评分合同，不改产品 outcome 策略、生成或知识；safe candidate vs typed handoff 继续留给用户。
- 不运行 Stage 12 / Provider；只更新集成分支与 Draft PR，不转 Ready、不合并、不部署。

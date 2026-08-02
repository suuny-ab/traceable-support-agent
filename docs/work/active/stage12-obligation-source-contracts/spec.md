# Stage 12 obligation / source 机械合同

## Goal

用公开合成 package 复现 Stage 12 的义务规划漏记与额外来源 exact-set 误扣，把评分合同改成
“必需事实由单一 obligation 的来源条款完整承接”与“必需来源子集 + 额外来源绑定账本”；
只做确定性离线重评分，不修改产品生成、prompt、知识或用户可见 outcome。

## Non-goals

- 不调用 Provider、不重跑 Stage 12、不读取私有正文来调规则。
- 不修改 checklist / QA / ticket prompt、生成合同、检索、知识或产品 package。
- 不把缺失必需来源、无 claim / obligation 绑定或型号不适用的额外来源放行。
- 不修改字面事实门、语义评分或 safe candidate vs typed handoff 取舍。
- 不转 Ready、不合并 `main`、不部署、不发布 `product/0.1.0`。

## AC

1. **WHEN** 在基线评分器运行公开义务遗漏夹具，**THEN** 复现
   `required_fact_missing`；**WHEN** 应用候选，**THEN** 改为
   `required_obligation_missing`，仍然失败。
2. **WHEN** 冻结必需事实没有被任一单独 obligation 的有序 approved source spans 完整承接，
   **THEN** 账本记录缺失 ordinal，不从回答正文是否偶然出现该事实推导规划通过。
3. **WHEN** 义务完整但正文缺失必需事实，**THEN** 仍报 `required_fact_missing`；unexpected
   handoff、matched handoff、outcome、预算和工单字段合同不变。
4. **WHEN** 候选使用全部必需来源和额外来源，且额外来源型号适用、进入 host-derived
   `used_evidence_ids`、由 claim 绑定并被对应 obligation 批准，**THEN** 不报
   `source_sections_mismatch`，并在 detail 保留额外来源。
5. **WHEN** 缺任一必需来源，或额外来源缺型号 / claim / obligation 任一绑定，**THEN** 仍报
   `source_sections_mismatch`，失败关闭。
6. **WHEN** 对既有 24 份已消费 package 离线重评分，**THEN** 只允许 R4 三个来源码消除、R5
   四个事实码一对一改为义务码；R1 / R2 / R3 / R6 的逐题失败码不变，不产生新通过主张。
7. **WHEN** 检查历史资产，**THEN** 原复验聚合、handoff 重评分和 generation_shape 回执字节 /
   SHA 不变；新公开回执只含案例 ID、计数、失败码和哈希。
8. **WHEN** 完成交付，**THEN** 定向、Stage 12、API 全集、治理、公开扫描、园丁、泄漏专项与
   差异检查全绿，Provider 调用为 0。
9. **WHEN** 推送候选，**THEN** 只更新 `night-20260802` / Draft PR #62 并确认最终 head 四项
   required Checks 全绿；不转 Ready、不合并、不部署。

## 验证说明卡

- **问题**：能否用 host 已有的 obligation / claim / evidence 账本区分真实规划遗漏与合法额外来源？
- **历史输入**：只读既有 24 份 package；私有集 SHA `7d730...8ab0`、原始记录 SHA
  `6eab...68af`。不执行 runner、product 或 generation。
- **公开输入**：四个合成 package，分别覆盖规划遗漏、完整规划但正文遗漏、合法额外来源、
  缺失 / 无绑定来源；不含私有内容。
- **调用 / 费用**：Provider 调用 0、自动重试 0、费用 0。
- **最便宜证伪**：先在未改 scorer 上复现旧 `required_fact_missing` 与 exact-set
  `source_sections_mismatch`；复现失败则停止。
- **允许结论**：评分器能机械区分义务规划覆盖与字面正文覆盖，并只接受有完整绑定账本的额外来源。
- **禁止结论**：模型生成质量改善、历史回答被修复、新 Stage 12 分数、线上成功率或发布成熟度。

## 回滚

候选阶段关闭 Draft PR #62 并删除 `night-20260802`；若未来合并则 revert 对应 squash。
恢复 Stage 12 scorer、公开夹具 / 回执、测试和状态文档即可；历史评测资产不改。

## 规则复述

- 不碰生成或产品 outcome；规划遗漏换成更准确的失败码，不把失败改成成功。
- 额外来源必须有型号、claim 与 obligation 的完整机械账本；缺必需来源继续失败。
- 已消费 Stage 12 只作离线回归；不运行 Provider，不转 Ready、不合并、不部署。

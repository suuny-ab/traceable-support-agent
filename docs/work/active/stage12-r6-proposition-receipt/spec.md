# Stage 12 R6 命题绑定收据判据

## Goal

把 Stage 12 候选结果的 `required_fact_missing` 字面子串判据替换为 proposition → obligation →
claim / evidence 的确定性绑定收据：自然改写通过，缺义务、缺 claim、越源或伪造 ID 继续失败关闭。

## Non-goals

- 不重跑 Stage 12，不调用 Provider，不生成新模型输出，不补用量。
- 不修改产品生成、prompt、检索、API、知识或用户可见 outcome。
- 不改写历史 24/24、11 通过、14 个失败码，也不把离线重评分视图发布成新质量分数。
- 不转 Ready、不合并 `main`、不部署。

## AC

1. **WHEN** 候选正文用自然语言改写冻结命题，**THEN** 合法 obligation、claim 与 evidence 绑定收据通过。
2. **WHEN** 冻结命题没有单个承接 obligation，**THEN** 报 `required_obligation_missing`。
3. **WHEN** obligation 存在但缺 claim、越源或使用伪造 ID，**THEN** 报
   `required_proposition_binding_missing`。
4. **WHEN** outcome 与预期不一致，**THEN** 保留完整候选合同和既有字面缺失分类，不因新判据消码。
5. **WHEN** 对已消费 24 个 package 离线重评分，**THEN** 六个 R6 案例全部通过候选判据，其余
   18 个案例的失败分类不变；Provider 调用为 0。
6. **WHEN** 输出公开收据，**THEN** 只含案例 ID、哈希、失败码与边界，不含私有明文。
7. **WHEN** 完成交付，**THEN** Stage 12、API、治理、Web、公开扫描、园丁、泄漏专项和差异检查全绿。
8. **WHEN** 推送，**THEN** 只更新 `night-20260802` / Draft PR #62 并确认最终 head required Checks；
   不转 Ready、不合并、不部署。

## 验证说明卡

- **问题**：确定性绑定收据能否消除六个字面假阴性，同时保留机械可判定的真缺失和越界失败？
- **固定输入**：公开历史聚合 SHA-256 `b4de5028...67e8`、语义审计 SHA-256
  `80b01635...2132`、Git 外原始记录 SHA-256 `73d272e9...c850`。
- **方法**：先用公开合成正反例红测，再实现 host 侧 ID / 范围 / 完整性验证，最后只读重评分已消费 package。
- **调用 / 费用**：Provider 调用 0、自动重试 0、费用 0。
- **最便宜证伪**：自然改写仍失败，或任一缺 claim / 越源 / 伪造 ID 通过，即停止交付。
- **允许结论**：判据合同和已消费六例的回归结果。
- **禁止结论**：新 Stage 12 分数、模型质量提升、开放域语义正确或发布成熟度。

## 回滚

关闭 Draft PR #62 并删除候选分支；若未来合并则 revert 对应 squash。删除本任务四文件、公开合成
fixture、离线收据和冻结测试，并恢复 `tools/stage12_eval.py` 即可；历史评测资产保持不动。

## 规则复述

- 已消费 Stage 12 只作离线回归；不重跑、不调用 Provider、不补跑。
- host 只验证绑定存在性、ID 与范围；不把合法绑定声称成开放域语义真实性证明。
- 历史数字不改写；离线 17/24 只作 scorer regression view，不形成新质量主张。

# 评审与边界

## 机器判据

- proposition 仍由冻结 `required_fact` 与批准 source spans 确定；不对客户可见自然语言做子串判断，也不
  引入 LLM judge。
- obligation 必须来自 checklist 且 ID 唯一；plan 与 checklist 的 evidence 集必须一致；必要 evidence
  必须存在于 package 且被使用。
- claim ID 必须唯一，绑定的 obligation 必须真实且 plan 完整，claim 的每个 evidence 必须属于
  每个已绑定 obligation 的批准 evidence 并被使用；覆盖冻结命题的必要 evidence 才形成通过收据。
- 缺 obligation 与缺绑定收据使用不同失败码；unexpected outcome 不缩短完整候选合同。

## ADR-0007 边界

该实现遵循“模型声明语义映射、host 验证绑定存在性”的责任分工。host 能证明 ID、来源范围和收据
完整性，不能证明 claim 文本与冻结命题在开放域中必然同义；人工最终决定仍是安全底线。

## 历史与外部边界

- 六例回归来自既有 R6 审计的精确案例集；不改历史聚合、审计收据或任何原始 package。
- 17/24 只描述同一批已消费 package 在候选 scorer 下的离线视图，不是正式质量主张。
- Provider 调用 0；不转 Ready、不合并、不部署，只更新既有夜班分支与 Draft PR #62。

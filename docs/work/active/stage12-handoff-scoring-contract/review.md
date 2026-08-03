# 评审与边界

## 方案判断

- 条件只在 expected 与 observed 同为 handoff 时成立，因而不会把 outcome mismatch 当成成功。
- 候选字段不适用于没有客户候选的 matched handoff；实际 boundary sources 仍进入 detail，
  但不与候选 expected source exact-set 混为一个评分合同。
- 明确登记的 handoff reason 和预算继续失败关闭；本切片没有新增自由文本或 LLM judge。
- 历史公开聚合保持不可变，新 JSON 是单独的 scorer-only 回归回执。

## 对照判断

24 题离线重评分只改变根因报告 R3 指定的四题 / 六码；另两题 matched handoff 原本已通过，
其余 20 题逐题失败码不变。`outcome_mismatch=8`、`required_fact_missing=12` 保持不变，说明
生成失败、边界策略、义务规划和字面事实门没有被该分支掩盖。

## 授权与结论边界

本任务完整 / R2 仅因为只读使用 Git 外已消费私有资产；Provider 调用、费用和生产写入均为 0。
false-completion 的 safe candidate vs typed handoff 会改变产品行为，继续留给用户，未在评分修复
中代决。不安排独立 Reviewer：分支条件、逐题差异和哈希均可机器验证，没有未关闭的实现级
方案疑问。

候选只允许更新 `night-20260802` / Draft PR #62；不转 Ready、不合并、不部署、不发布。

实现 head `eab5b20` 的 CI run `30759671469` 四个 required jobs 已全绿，publish 因 Draft
跳过；没有新阻断 finding。最终状态回执 head 只需通过同一 required Checks，不扩展授权。

# 计划

1. 锁定私有集、原始记录与历史公开聚合哈希，证明旧 scorer 24/24 复算一致。
2. 给 `score_case` 增加 matched-handoff profile；保留 reason、预算与审计 detail，候选字段只在
   非 matched handoff 路径评分。
3. 用公开合成 package 钉住 matched handoff、reason / budget 失败关闭和两类 outcome mismatch。
4. 对既有 24 个私有 package 做零调用重评分；生成脱敏回执并证明仅四题 / 六码变化。
5. 同步评测合同、结果、review、口径卡和两层状态；运行定向、全量与治理检查。
6. 提交并推送 `night-20260802`，确认 Draft PR #62 最终 head required Checks 后停止。

停止线：任何非目标案例失败码漂移、历史聚合被改、需要修改产品行为或需要 Provider 时立即停止。

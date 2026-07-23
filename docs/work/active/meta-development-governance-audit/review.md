# 复核记录

> 状态：`not_started`

## 正式复核合同

正式复核只能在以下条件同时满足后开始：

1. Draft PR 已创建；
2. `governance`、`web`、`api`、`containers` 全部成功；
3. head SHA 已记录并冻结；
4. 主 Agent 停止写入；
5. 复核者明确只读。

正式回执必须记录：

- `candidate_sha`
- 复核范围和风险
- 已通过 Checks
- findings（含严重度与可批准入口）
- 结论边界

若候选发生变化，旧回执失效。存在 finding 时，只针对 finding 和覆盖 diff 进行后续复核；
没有 finding 时不调用第二次复核。

## 当前状态

- 正式复核调用次数：`0`
- 冻结候选：无
- findings：无
- 结论：未开始；这不是质量通过回执。

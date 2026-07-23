# 复核记录

> 状态：`approved`

## 一次完整复核（PR #18，评测基础设施）

- `candidate_sha`：`97cd1ac0cc5e18bc65da68b9d60a32d7b56bf04d`
- 基线：`ca797d7`
- 范围 / 风险：完整增量；runner、冻结校验器、离线测试、公开维度文件、活动文档、
  CI 步骤；该 PR `R0`（零 Provider 调用、零费用、零部署变更）。
- Checks：run `30019968825` attempt 1，governance / web / api / containers 全部成功。
- 调用方式：Draft PR 全绿后冻结 head SHA，一次只读复核，复核者未写入。
- Findings：无 P0–P2 阻断。4 条 P3 观察项（不阻断，留档）：
  1. runner 入口 `load_unseen_set` 校验弱于冻结校验器（畸形集以未捕获 KeyError 退出，
     仍失败关闭）。
  2. 冻结校验器对绑定章节拼接文本判定，跨章节拼接缝的事实会被放行（偏宽松）。
  3. 异常路径案例 `provider_call_count` 记 0（因即停无信封后果）。
  4. 未知维度码静默记 `unmapped`（报告中可见，不构成错误通过）。
- 结论边界：批准合入作为评测基础设施；不授权 Provider 调用 / 费用 / 生产执行；
  不批准 S3 结论本身；候选后续改动使回执失效。回执全文见 PR #18 评论。

## 收口复核（本 PR，正式回执与公开主张）

- 范围：执行结果回执（`result.md`）、公开聚合报告（`evals/stage12-aggregate-v1.json`）、
  `docs/engineering/evaluation.md` 定位修订、`docs/product/` 证据地图与已知限制、
  `PROJECT.md` 与 `docs/status.md` 回写。
- 状态：等待 Draft PR 四项 Checks 全绿后冻结 head SHA 调用一次。

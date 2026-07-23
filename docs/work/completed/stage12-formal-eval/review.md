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

## 收口复核（PR #20，正式回执与公开主张）

- `candidate_sha`：`bba0f4a9709d29a89e8b65e6699d54cc3ffddc5b`
- 范围：执行结果回执（`result.md`）、公开聚合报告（`evals/stage12-aggregate-v1.json`）、
  `docs/engineering/evaluation.md` 定位修订、`docs/product/` 证据地图与已知限制、
  `PROJECT.md` 与 `docs/status.md` 回写。
- Checks：run `30027962340` attempt 1，governance / web / api / containers 全部成功。
- 结论：批准合入。聚合报告与回执逐维度机械一致（19/24、9 通过、SAF-003 / MBD-003
  失败、5 案例未执行）；无明文；失败未淡化；公网零费用机器声明与 `not_released`
  保持；evaluation.md 修订与 spec 预声明对应。
- Findings：无 P0–P2。4 条 P3 留档（0.1.0 门性质转为"证据 + 用户判断"知悉项；
  status.md 两处过时已在归档 PR 修正；模型名进入公开面判定合规；归档时序符合合同）。
- 不批准：0.1.0 发布、实时 Provider、任何新 Provider 调用；缺陷修复归 Issue #21/#22。
- 回执全文见 PR #20 评论。

## 归档

- PR #18 合并 `650fa29`；PR #19 合并 `7f64c7c`；PR #20 合并 `fce7c3b`，生产部署
  run `30028764037` 成功，公网健康保持 `replay_only`。
- 缺陷登记为 Issue #21（SAF-003 / MBD-003）与 #22（候选生成合同失败率）。
- 用户已于 `2026-07-24` 验收通过；工作目录由 `docs/work/active/` 归档至此。

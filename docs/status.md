# 当前开发状态

> 本文件是唯一当前状态入口，不累计已经关闭的历史。

| 字段 | 内容 |
| --- | --- |
| `state` | `developing` |
| 更新时间 | `2026-07-24` |
| 当前目标 | 修复两阶段生成合同在真实外部模型下的高失败率，同时保持来源、安全与失败关闭边界 |
| 活动增量 | Issue #22 两阶段生成合同可用性 |
| 复杂度 | 完整 |
| 风险 / 成熟度 | v14 真实 QA 两阶段合同通过并形成 candidate，但公开回归仍缺 1 项必需事实；Issue #22 完成门未满足，产品保持 `S1 公开 Beta` |
| 活动工作 | `docs/work/active/two-stage-generation-contract/` |
| 最近完成 | `docs/work/completed/pre-generation-boundary-handoff/` |
| 当前动作 | 付费调参已停止，最终本地检查全绿；提交回执并更新既有 Draft PR #27 |
| 阻碍 | QA003 虽形成 candidate，仍以 `required_fact_missing` 未达到公开回归观测水平 |
| Provider | 生产仍禁用：`provider_enabled=false`、`provider_calls=0`、`provider_cost_cny=0`；v14 两次调用估算 `¥0.080325`、预留 `¥0.287007`，重试 0；v11 / v13 各有一次未计价，历史实际账单仍待账号侧确认 |
| 下一检查点 | Draft PR 最终四项 Checks 全绿后冻结 head，并做一次正式只读复核 |

## 当前产品事实

- 方向 B 的公开回放体验位于 <https://47.84.34.86/>。
- 健康状态必须保持 `replay_only`；实时 Provider 不在任何当前增量范围内。
- `product/0.1.0` 尚未发布；Stage 12 已执行一次（19/24、9 通过），Issue #21 已修复当时的两条边界缺陷但未重跑未见集；Issue #22 当前只处理候选生成合同可用性。
- 当前工作树和公开 GitHub 仓库已经是唯一权威开发来源。
- 旧仓和临时回滚材料不是权威来源；它们的删除属于独立破坏性清理，未经精确确认不得执行。
- 受保护 `main` 的 CI 全绿后自动进入生产部署，不再逐次等待人工 reviewer；失败部署不自动重试。

## 权威来源

- 产品事实：`PROJECT.md`
- 结果路线：`ROADMAP.md`
- 最近完成记录：`docs/work/completed/pre-generation-boundary-handoff/`
- 工程规则：`docs/engineering/`

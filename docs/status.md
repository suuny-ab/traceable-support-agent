# 当前开发状态

> 本文件是唯一当前状态入口，不累计已经关闭的历史。

| 字段 | 内容 |
| --- | --- |
| `state` | `developing` |
| 更新时间 | `2026-07-24` |
| 当前目标 | 修复两阶段生成合同在真实外部模型下的高失败率，同时保持来源、安全与失败关闭边界 |
| 活动增量 | Issue #22 两阶段生成合同可用性 |
| 复杂度 | 完整 |
| 风险 / 成熟度 | 第一次 `R1` 已硬停止；当前 v2 诊断候选为 `R0`，新的 `R1` 待独立授权；产品保持 `S1 公开 Beta` |
| 活动工作 | `docs/work/active/two-stage-generation-contract/` |
| 最近完成 | `docs/work/completed/pre-generation-boundary-handoff/` |
| 当前动作 | v2 诊断候选已细分隐私安全失败码、修正 NFKC 评分并冻结两例最便宜证伪 |
| 阻碍 | 真实 checklist 子合同和 Provider 信封子码仍未知；只可通过新的两例有界 API 诊断确认 |
| Provider | 生产仍禁用：`provider_enabled=false`、`provider_calls=0`、`provider_cost_cny=0`；本次获准验证另行执行 4 次、重试 0，成功解析 usage 的估算费用 ¥0.075783，三例最坏预留 ¥0.359697，实际账单待账号侧确认 |
| 下一检查点 | 未授权时保持停止；若获新授权，执行 2 例、最多 4 次、最坏 ¥1.40、重试 0 的 `diagnostic-v2` |

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

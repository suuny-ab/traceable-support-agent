# 当前开发状态

> 本文件是唯一当前状态入口，不累计已经关闭的历史。

| 字段 | 内容 |
| --- | --- |
| `state` | `developing` |
| 更新时间 | `2026-07-24` |
| 当前目标 | 修复两阶段生成合同在真实外部模型下的高失败率，同时保持来源、安全与失败关闭边界 |
| 活动增量 | Issue #22 两阶段生成合同可用性 |
| 复杂度 | 完整 |
| 风险 / 成熟度 | 前三次 `R1` 按硬停止结束；TK-001 与 TK-006 均观测到同候选下的通过 / 失败波动；转入 `R0` 语义覆盖合同候选；产品保持 `S1 公开 Beta` |
| 活动工作 | `docs/work/active/two-stage-generation-contract/` |
| 最近完成 | `docs/work/completed/pre-generation-boundary-handoff/` |
| 当前动作 | v7 同候选通过，确认逐字 completeness 存在模型波动；本地设计 LLM 客户可见语义跨度合同 |
| 阻碍 | 需要在不放松来源、安全和人工批准边界下，移除 key_elements 与客户文本的逐字相等要求 |
| Provider | 生产仍禁用：`provider_enabled=false`、`provider_calls=0`、`provider_cost_cny=0`；七次验证分别调用 4 / 3 / 1 / 1 / 2 / 2 / 2 次、均重试 0；v5 / v6 / v7 分别估算 ¥0.0792522 / ¥0.0731974 / ¥0.0623356，未获得 usage 的历史调用实际账单待账号侧确认 |
| 下一检查点 | 先完成语义跨度合同的 R0 证伪与架构决定，不再重复付费运行同一候选 |

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

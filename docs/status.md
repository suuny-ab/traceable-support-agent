# 当前开发状态

> 本文件是唯一当前状态入口，不累计已经关闭的历史。

| 字段 | 内容 |
| --- | --- |
| `state` | `ready` |
| 更新时间 | `2026-07-24` |
| 当前目标 | 等待显式启动下一项产品增量 |
| 活动增量 | 无 |
| 复杂度 | 无活动增量 |
| 风险 / 成熟度 | 产品保持 `S1 公开 Beta`；公网 Provider 继续关闭 |
| 活动工作 | 无 |
| 最近完成 | `docs/work/completed/pre-generation-boundary-handoff/` |
| 当前动作 | Issue #21 已完成实现、固定候选复核、自动生产部署与用户验收，并归档 |
| 阻碍 | 无 |
| Provider | 公网已禁用：`provider_enabled=false`、`provider_calls=0`、`provider_cost_cny=0`；任何后续 API 调用仍需独立授权 |
| 下一检查点 | 用户显式选择并启动下一项公开 Issue；结果顺序以 `ROADMAP.md` 为准 |

## 当前产品事实

- 方向 B 的公开回放体验位于 <https://47.84.34.86/>。
- 健康状态必须保持 `replay_only`；实时 Provider 不在任何当前增量范围内。
- `product/0.1.0` 尚未发布；Stage 12 已执行一次（19/24、9 通过），Issue #21 已修复当时的两条边界缺陷但未重跑未见集，候选生成合同缺陷仍由 Issue #22 跟踪。
- 当前工作树和公开 GitHub 仓库已经是唯一权威开发来源。
- 旧仓和临时回滚材料不是权威来源；它们的删除属于独立破坏性清理，未经精确确认不得执行。
- 受保护 `main` 的 CI 全绿后自动进入生产部署，不再逐次等待人工 reviewer；失败部署不自动重试。

## 权威来源

- 产品事实：`PROJECT.md`
- 结果路线：`ROADMAP.md`
- 最近完成记录：`docs/work/completed/pre-generation-boundary-handoff/`
- 工程规则：`docs/engineering/`

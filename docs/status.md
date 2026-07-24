# 当前开发状态

> 本文件是唯一当前状态入口，不累计已经关闭的历史。

| 字段 | 内容 |
| --- | --- |
| `state` | `ready` |
| 更新时间 | `2026-07-24` |
| 当前目标 | 无活动增量；等待在新会话启动 Issue #28 求职作品集最终体验 |
| 活动增量 | 无 |
| 复杂度 | 无 |
| 风险 / 成熟度 | Issue #22 的 clause 级来源修正已通过冻结候选针对性复核并部署；原候选质量完成门未满足，v15 真实兼容性未知，产品保持 `S1 公开 Beta` |
| 活动工作 | 无 |
| 最近完成 | `docs/work/completed/two-stage-generation-contract/` |
| 当前动作 | 保持 `ready`；下一会话只启动 Issue #28 |
| 阻碍 | 无；Issue #28 启动前仍需独立冻结 Provider、费用、凭据、生产开关和验证说明卡 |
| Provider | 生产仍禁用：`provider_enabled=false`、`provider_calls=0`、`provider_cost_cny=0`；v14 两次调用估算 `¥0.080325`、预留 `¥0.287007`，重试 0；v11 / v13 各有一次未计价，历史实际账单仍待账号侧确认 |
| 下一检查点 | 新会话读取 Issue #28，建立唯一活动增量并先冻结最便宜证伪与外部风险边界 |

## 当前产品事实

- 方向 B 的公开回放体验位于 <https://47.84.34.86/>。
- 健康状态必须保持 `replay_only`；实时 Provider 不在任何当前增量范围内。
- `product/0.1.0` 尚未发布；Stage 12 已执行一次（19/24、9 通过），Issue #21 已修复当时的两条边界缺陷但未重跑未见集；Issue #22 已以部分结果和已知限制收口，不形成成功率主张。
- 后续结果顺序固定为 Issue #28 最终网站与受控真实演示、Issue #29 仓库展示、Issue #14 发布或保持 Beta 判断。
- 当前工作树和公开 GitHub 仓库已经是唯一权威开发来源。
- 旧仓和临时回滚材料不是权威来源；它们的删除属于独立破坏性清理，未经精确确认不得执行。
- 受保护 `main` 的 CI 全绿后自动进入生产部署，不再逐次等待人工 reviewer；失败部署不自动重试。

## 权威来源

- 产品事实：`PROJECT.md`
- 结果路线：`ROADMAP.md`
- 最近完成记录：`docs/work/completed/two-stage-generation-contract/`
- 工程规则：`docs/engineering/`

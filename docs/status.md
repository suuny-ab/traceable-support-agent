# 当前开发状态

> 本文件是唯一当前状态入口，不累计已经关闭的历史。

| 字段 | 内容 |
| --- | --- |
| `state` | `ready` |
| 更新时间 | `2026-07-23` |
| 当前目标 | 唯一权威仓库迁移已关闭；等待选择下一个单一活动增量 |
| 活动增量 | 无 |
| 复杂度 | 无活动工作 |
| 风险 / 成熟度 | 当前状态维护为 `R0`；产品保持 `S1 公开 Beta` |
| 活动工作 | 无 |
| 最近完成 | `docs/work/completed/canonical-repository-migration/` |
| 当前动作 | PR #10 已合并为 `fff847f`；主线运行 `29999870811` 全部成功，生产运行 `30000004137` 无需人工批准即自动成功。服务器正式回执绑定该 SHA，`旧 → 新 → 旧 → 新`、容器健康和公网五路由均通过 |
| 阻碍 | 无 |
| Provider | 已禁用；`provider_enabled=false`、`provider_calls=0`、`provider_cost_cny=0` |
| 下一检查点 | 选择并建立下一个唯一活动增量；在此之前不启动产品或元开发实现 |

## 当前产品事实

- 方向 B 的公开回放体验位于 <https://47.84.34.86/>。
- 健康状态必须保持 `replay_only`；实时 Provider 不在本增量范围内。
- `product/0.1.0` 尚未发布；Stage 12 和最终视觉设计仍是后续工作。
- 当前工作树和公开 GitHub 仓库已经是唯一权威开发来源。
- 旧仓和临时回滚材料不是权威来源；它们的删除属于独立破坏性清理，未经精确确认不得执行。
- 受保护 `main` 的 CI 全绿后自动进入生产部署，不再逐次等待人工 reviewer；失败部署不自动重试。

## 权威来源

- 产品事实：`PROJECT.md`
- 结果路线：`ROADMAP.md`
- 最近完成记录：`docs/work/completed/canonical-repository-migration/`
- 工程规则：`docs/engineering/`

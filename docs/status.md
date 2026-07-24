# 当前开发状态

> 本文件是唯一当前状态入口，不累计已经关闭的历史。

| 字段 | 内容 |
| --- | --- |
| `state` | `developing` |
| 更新时间 | `2026-07-24` |
| 当前目标 | 修复 Stage 12 暴露的 SAF-003 安全升级与 MBD-003 型号边界未失败关闭缺陷 |
| 活动增量 | Issue #21：生成前确定性安全 / 型号边界转人工 |
| 复杂度 | 完整：触及安全边界与公共失败关闭合同 |
| 风险 / 成熟度 | `R0`：仅本地合成回归，Provider 调用必须为 0；产品保持 `S1 公开 Beta` |
| 活动工作 | `docs/work/active/pre-generation-boundary-handoff/` |
| 最近完成 | `docs/work/completed/stage12-formal-eval/` |
| 当前动作 | Issue #21 本地候选已实现；API 74 通过 / 1 环境跳过，Stage 12 runner 机制 11 通过，治理工具 64 通过 / 7 环境跳过，Web 18 通过；正在同步候选事实 |
| 阻碍 | 无 |
| Provider | 公网已禁用：`provider_enabled=false`、`provider_calls=0`、`provider_cost_cny=0`；本增量不授权 Provider、费用或重试，验证中调用数必须保持 0 |
| 下一检查点 | 完成候选一致性检查；随后把推送、Draft PR、四项 Checks 和冻结 SHA 独立复核作为下一外部阶段 |

## 当前产品事实

- 方向 B 的公开回放体验位于 <https://47.84.34.86/>。
- 健康状态必须保持 `replay_only`；实时 Provider 不在任何当前增量范围内。
- `product/0.1.0` 尚未发布；Stage 12 已执行一次（19/24、9 通过、2 条边界缺陷登记），发布判断归 Issue #14。
- 当前工作树和公开 GitHub 仓库已经是唯一权威开发来源。
- 旧仓和临时回滚材料不是权威来源；它们的删除属于独立破坏性清理，未经精确确认不得执行。
- 受保护 `main` 的 CI 全绿后自动进入生产部署，不再逐次等待人工 reviewer；失败部署不自动重试。

## 权威来源

- 产品事实：`PROJECT.md`
- 结果路线：`ROADMAP.md`
- 最近完成记录：`docs/work/completed/stage12-formal-eval/`
- 工程规则：`docs/engineering/`

# 当前开发状态

> 本文件是唯一当前状态入口，不累计已经关闭的历史。

| 字段 | 内容 |
| --- | --- |
| `state` | `developing` |
| 更新时间 | `2026-07-24` |
| 当前目标 | Issue #28：完成最终作品集视觉与三个固定示例的受控真实体验 |
| 活动增量 | `portfolio-live-experience` |
| 复杂度 | 完整；当前停在 Issue #28 首屏参考对齐 checkpoint，下一产品任务尚未重新确认 |
| 风险 / 成熟度 | 当前为 `R0` 本地规则、文档与既有原型；保持 `S1 公开 Beta`，任何新 CLI 调用、产品 Provider、Qoder、生产开关和部署均需当前任务的独立状态与授权 |
| 活动工作 | `docs/work/active/portfolio-live-experience/` |
| 最近完成 | `docs/work/completed/two-stage-generation-contract/` |
| 当前动作 | 多 CLI 正式规则已完成最终修订；当前会话在 checkpoint 收口，等待新会话与 Codex 规划下一项开发工作 |
| 阻碍 | 无工程阻碍；首个开发决定和 Worker 均由新会话重新讨论，旧会话额度与授权不继承 |
| Provider | 生产仍禁用：`provider_enabled=false`、`provider_calls=0`、`provider_cost_cny=0`；v14 两次调用估算 `¥0.080325`、预留 `¥0.287007`，重试 0；v11 / v13 各有一次未计价，历史实际账单仍待账号侧确认 |
| 下一检查点 | 新会话由 Codex 作为项目规划者陪同讨论；形成开发决定后生成新的 CLI 状态卡，由用户选择 Worker，再透明派发 |

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
- 多 CLI 协作：`docs/meta/multi-cli-workflow.md`

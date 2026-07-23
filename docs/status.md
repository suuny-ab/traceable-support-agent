# 当前开发状态

> 本文件是唯一当前状态入口，不累计已经关闭的历史。

| 字段 | 内容 |
| --- | --- |
| `state` | `active` |
| 更新时间 | `2026-07-23` |
| 当前目标 | Stage 12 全新未见正式评测：为冻结候选产出绑定身份的正式回执 |
| 活动增量 | `stage12-formal-eval` |
| 复杂度 | 完整路径 |
| 风险 / 成熟度 | 文档与 runner `R0`；主机执行 `R1`；目标 `S3 正式` 证据 |
| 活动工作 | `docs/work/active/stage12-formal-eval/` |
| 最近完成 | `docs/work/completed/meta-development-governance-audit/` |
| 当前动作 | 阶段 2 完成：PR #18 合并为 `650fa29`，main CI `30022933330` 与生产部署 `30023103516` 成功，健康保持 `replay_only`；候选身份已固定并写入 spec；阶段 4 等待用户批准授权信封 |
| 阻碍 | 生产主机执行前需用户显式批准授权信封（≤24 案例 / ≤150 调用 / ≤¥10 / 重试 0） |
| Provider | 已禁用；`provider_enabled=false`、`provider_calls=0`、`provider_cost_cny=0` |
| 下一检查点 | runner PR 合入并冻结候选 SHA 后，起草并机械冻结私有未见集 |

## 当前产品事实

- 方向 B 的公开回放体验位于 <https://47.84.34.86/>。
- 健康状态必须保持 `replay_only`；实时 Provider 不在本增量范围内。
- `product/0.1.0` 尚未发布；Stage 12 证据是本增量的目标产出；商业 SaaS 四页重设计已部署并通过用户验收。
- 当前工作树和公开 GitHub 仓库已经是唯一权威开发来源。
- 旧仓和临时回滚材料不是权威来源；它们的删除属于独立破坏性清理，未经精确确认不得执行。
- 受保护 `main` 的 CI 全绿后自动进入生产部署，不再逐次等待人工 reviewer；失败部署不自动重试。

## 权威来源

- 产品事实：`PROJECT.md`
- 结果路线：`ROADMAP.md`
- 活动规格与计划：`docs/work/active/stage12-formal-eval/`
- 工程规则：`docs/engineering/`

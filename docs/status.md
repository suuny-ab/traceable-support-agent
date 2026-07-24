# 当前开发状态

> 本文件是唯一当前状态入口，不累计已经关闭的历史。

| 字段 | 内容 |
| --- | --- |
| `state` | `developing` |
| 更新时间 | `2026-07-24` |
| 当前目标 | 修复两阶段生成合同在真实外部模型下的高失败率，同时保持来源、安全与失败关闭边界 |
| 活动增量 | Issue #22 两阶段生成合同可用性 |
| 复杂度 | 完整 |
| 风险 / 成熟度 | `R1` 固定外部 API 验证已执行并按硬停止结束；产品保持 `S1 公开 Beta` |
| 活动工作 | `docs/work/active/two-stage-generation-contract/` |
| 最近完成 | `docs/work/completed/pre-generation-boundary-handoff/` |
| 当前动作 | 保存 `issue22-public-synthetic-api-1` 停止回执，只做隐私安全的失败分类与下一最便宜证伪设计 |
| 阻碍 | 候选未通过固定探针：第一阶段清单形状失败 1 例、QA candidate 缺公开必需事实 1 例、Provider 信封失败 1 例；第 4 例未执行 |
| Provider | 生产仍禁用：`provider_enabled=false`、生产调用 0；本次获准验证执行 4 次、重试 0，成功解析 usage 的估算费用 ¥0.075783，三例最坏预留 ¥0.359697，实际账单待账号侧确认 |
| 下一检查点 | 不消费剩余授权；基于稳定失败码和官方合同提出本地修正 / 诊断候选，重新冻结后再请求新 attempt 授权 |

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

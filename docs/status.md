# 当前开发状态

> 本文件是唯一当前状态入口，不累计已经关闭的历史。

| 字段 | 内容 |
| --- | --- |
| `state` | `migrating` |
| 更新时间 | `2026-07-23` |
| 当前目标 | 在不丢失产品能力和元开发能力的前提下，建立唯一、可公开、可持续开发的权威仓库 |
| 活动增量 | 唯一权威仓库治理迁移 |
| 复杂度 | 完整路径；涉及架构、仓库身份、公开源码和部署流水线变化 |
| 风险 / 成熟度 | 本地工作为 `R0`；GitHub / 部署检查点为 `R2`；产品保持 `S1 公开 Beta` |
| 活动工作 | `docs/work/active/canonical-repository-migration/` |
| 当前动作 | 公开 GitHub 仓库已建立；处理首次 CI 暴露的空白与依赖安全问题，并完成远程基线验证 |
| 阻碍 | 修复版 CI、`main` 保护和 GitHub 来源全新克隆未全部通过前，不得切换正式路径或部署新版本 |
| Provider | 已禁用；`provider_enabled=false`、`provider_calls=0`、`provider_cost_cny=0` |
| 下一检查点 | 公开 GitHub 基线检查全部通过后，从父目录执行可逆的本机 canonical 路径切换；切换前旧仓仍为权威 |

## 当前产品事实

- 方向 B 的公开回放体验位于 <https://47.84.34.86/>。
- 健康状态必须保持 `replay_only`；实时 Provider 不在本增量范围内。
- `product/0.1.0` 尚未发布；Stage 12 和最终视觉设计仍是后续工作。
- 在公开远程仓库验证、正式路径验收、生产回滚演练和用户验收全部通过前，旧仓仍是权威仓库。

## 权威来源

- 产品事实：`PROJECT.md`
- 结果路线：`ROADMAP.md`
- 活动规格与计划：`docs/work/active/canonical-repository-migration/`
- 工程规则：`docs/engineering/`

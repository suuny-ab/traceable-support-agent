# 当前开发状态

> 本文件是唯一当前状态入口，不累计已经关闭的历史。

| 字段 | 内容 |
| --- | --- |
| `state` | `migrating` |
| 更新时间 | `2026-07-23` |
| 当前目标 | 在不丢失产品能力和元开发能力的前提下，建立唯一、可公开、可持续开发的权威仓库 |
| 活动增量 | 唯一权威仓库治理迁移 |
| 复杂度 | 完整路径；涉及架构、仓库身份、公开源码和部署流水线变化 |
| 风险 / 成熟度 | 当前文档收口为 `R0`；生产部署检查点为 `R2`；产品保持 `S1 公开 Beta` |
| 活动工作 | `docs/work/active/canonical-repository-migration/` |
| 当前动作 | 自动排队候选和 `production` environment 人工审批门已经通过本地 / 在线核验；等待候选 PR CI 与合并检查，尚未触发部署 |
| 阻碍 | 生产部署属于 `R2` 外部写入，尚未执行；候选仍未合并，回滚演练和用户验收通过前不得关闭迁移或清理旧仓 |
| Provider | 已禁用；`provider_enabled=false`、`provider_calls=0`、`provider_cost_cny=0` |
| 下一检查点 | 让候选通过 PR CI；合并后的首次绿色 `main` 发布必须停在人工批准页，再以固定 Git SHA 与镜像摘要执行“旧 → 新 → 旧 → 新”生产演练 |

## 当前产品事实

- 方向 B 的公开回放体验位于 <https://47.84.34.86/>。
- 健康状态必须保持 `replay_only`；实时 Provider 不在本增量范围内。
- `product/0.1.0` 尚未发布；Stage 12 和最终视觉设计仍是后续工作。
- 本机开发入口已经切换到当前 canonical 工作树；旧仓仅作为回滚材料保留，不再作为日常开发入口。
- 在生产回滚演练和用户验收通过前，仍不得宣布整个迁移完成或删除旧仓。

## 权威来源

- 产品事实：`PROJECT.md`
- 结果路线：`ROADMAP.md`
- 活动规格与计划：`docs/work/active/canonical-repository-migration/`
- 工程规则：`docs/engineering/`

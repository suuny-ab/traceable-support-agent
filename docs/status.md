# 当前开发状态

> 本文件是唯一当前状态入口，不累计已经关闭的历史。

| 字段 | 内容 |
| --- | --- |
| `state` | `developing` |
| 更新时间 | `2026-07-24` |
| 当前目标 | 修复两阶段生成合同在真实外部模型下的高失败率，同时保持来源、安全与失败关闭边界 |
| 活动增量 | Issue #22 两阶段生成合同可用性 |
| 复杂度 | 完整 |
| 风险 / 成熟度 | 当前本地诊断为 `R0`；真实外部 API 验证为待独立授权的 `R1`；产品保持 `S1 公开 Beta` |
| 活动工作 | `docs/work/active/two-stage-generation-contract/` |
| 最近完成 | `docs/work/completed/pre-generation-boundary-handoff/` |
| 当前动作 | R0 合同候选和固定公开合成探针已通过本地回归；候选代码与 API 验证合同已冻结 |
| 阻碍 | 候选代码已冻结；执行镜像的无网络构建因 BGE 资产缓存缺失而停止。外部 API 验证仍缺受控公开依赖下载、当前 Provider 合同复核和用户独立授权 |
| Provider | 公网已禁用：`provider_enabled=false`、`provider_calls=0`、`provider_cost_cny=0`；任何后续 API 调用仍需独立授权 |
| 下一检查点 | 获得公开依赖下载授权后构建不可变执行镜像；再以完整 SHA / 摘要 / Provider / ¥2.80 上限请求独立 API 授权 |

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

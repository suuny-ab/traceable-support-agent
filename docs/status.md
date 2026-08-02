# 当前开发状态

> 本文件只保存当前字段、当前队列和下一检查点；历史回执、旧队列与证据见只追加的 [月度状态日志](status-log/2026-08.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `candidate` |
| 更新时间 | `2026-08-03` |
| 当前产品目标 | 离线分离 Stage 12 义务规划覆盖与合法额外来源机械合同，不修改生成或产品 outcome |
| 项目基线 | `origin/main@8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24` |
| 运行产品 | 公开 Beta；`product/0.1.0` 未发布；最近核验公网 `status=ok`、`live_experience=available`、`release_sha=8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24` |
| 当前治理结果 | PR [#61](https://github.com/suuny-ab/traceable-support-agent/pull/61) 已从精确 head `074bab2bb00268957321da40348a58fca1b82797` squash merge 为 `8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24`；main CI、部署与公网完整 SHA 已核验 |
| 当前产品候选 | Draft PR [#62](https://github.com/suuny-ab/traceable-support-agent/pull/62)（`night-20260802`）；义务 / 来源机械合同本地全绿，待实现提交、推送与最终 head required Checks |
| 活动工作 | [`stage12-obligation-source-contracts`](work/active/stage12-obligation-source-contracts/spec.md)（`docs/work/active/stage12-obligation-source-contracts/`）：义务与来源账本；[`stage12-generation-shape-diagnostics`](work/active/stage12-generation-shape-diagnostics/spec.md)（`docs/work/active/stage12-generation-shape-diagnostics/`）、[`stage12-handoff-scoring-contract`](work/active/stage12-handoff-scoring-contract/spec.md)（`docs/work/active/stage12-handoff-scoring-contract/`）、[`stage12-failure-root-cause`](work/active/stage12-failure-root-cause/spec.md)（`docs/work/active/stage12-failure-root-cause/`）、[`stage12-post-fix-revalidation`](work/active/stage12-post-fix-revalidation/spec.md)（`docs/work/active/stage12-post-fix-revalidation/`）：既有证据；[`public-metrics-card`](work/active/public-metrics-card/spec.md)（`docs/work/active/public-metrics-card/`）、[`retrieval-unseen-holdout`](work/active/retrieval-unseen-holdout/spec.md)（`docs/work/active/retrieval-unseen-holdout/`）、[`minimal-observability`](work/active/minimal-observability/spec.md)（`docs/work/active/minimal-observability/`）：既有候选 |
| 风险 / 授权 | 完整 / R2；只读既有 package 做 scorer-only 回归并使用公开合成 package，不运行 Stage 12 / Provider、不改生成；夜班授权允许推送集成分支并更新 Draft PR #62，不授权 Ready、合并、部署、发布或产品 outcome 取舍 |
| Provider | `provider_enabled=true`；凭据仍只在服务器 `/opt/traceable-support/provider.env`（0600）。既有复验授权已消费且不得补跑；本评分修复调用 0、自动重试 0、费用 0 |
| 阻碍 | R4 / R5 机械归因已在本地分离，但历史回答本身未改变；R6 语义评分与 R2 / false-completion 产品 outcome 仍需独立切片 / 用户取舍；发布主张继续被历史 Stage 12 结果阻断 |
| 当前证据 | 公开四场景复现并定向通过；24 份 package 仅 6 个预登记案例变化，R4 三码删除、R5 四码换码，其余 18 题逐题不变、6 通过不变；Stage 12 21 tests、API 158 passed / 4 skipped、治理 122 passed / 8 skipped，Provider 调用 0 |

## 当前队列

| Task | 状态 | 候选 / 下一动作 |
| --- | --- | --- |
| `stage12-obligation-source-contracts` | `candidate_local_green` | 公开夹具、24 题 scorer-only 差异与全量治理通过；待推送及 Draft PR #62 最终 head Checks |
| `stage12-generation-shape-diagnostics` | `candidate_ci_green` | 四分支离线复现、诊断拆码、产品 handoff、全量治理与实现 head CI 通过；待状态回执最终 head Checks |
| `stage12-handoff-scoring-contract` | `candidate_ci_green` | 4 题 / 6 码定向修复、20 题零漂移；实现 head CI 全绿，待状态回执最终 head Checks |
| `stage12-failure-root-cause` | `candidate_ci_green` | 六类根因与最小修复候选已落文档；实现 head CI 全绿，待状态回执最终 head Checks，不实施修复 |
| `stage12-post-fix-revalidation` | `candidate_ci_green` | 24/24、2 通过已落盘；结果 head CI 全绿，待状态回执最终 head Checks，不补跑 |
| `public-metrics-card` | `candidate_ci_green` | 实现 head `b01adb9b` 与 run `30753847922` 全绿；待回执提交最终 head Checks，不自动 Ready / 合并 / 部署 |
| `retrieval-unseen-holdout` | `observed_frozen` | 首次检索观察已落盘；只作回归，不改检索 / 题 / 标签 / 知识；待全集、治理和 Draft PR #62 最终 head Checks |
| `minimal-observability` | `candidate` | Draft PR #62；等待最终 head 的 required Checks，不自动转 Ready、合并或部署 |
| `pgvector-production-integration` | `delivered` | PR #61 merge / main CI / deploy / 公网完整 SHA 均已核验；工作记录已归档到 `docs/work/completed/` |
| `dependency-security-maintenance` | `delivered` | PR #60 已交付；不在本切片继续依赖升级 |
| `ISSUE-14-RELEASE-DECISION` | `deferred` | 不在本切片内；不得从依赖修复推导发布结论 |

## 下一检查点

本切片停止点：义务规划遗漏由专门账本失败码承接，只有同型号且 claim / obligation 完整绑定
的额外来源免于 exact-set 误扣，R4 / R5 之外逐题零漂移；运行全量治理并确认 Draft PR #62
最终 head required Checks 全绿后停止。不运行 Stage 12 / Provider，不改生成、prompt 或产品
outcome，不转 Ready、不合并、不部署、不发布。

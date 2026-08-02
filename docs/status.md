# 当前开发状态

> 本文件只保存当前字段、当前队列和下一检查点；历史回执、旧队列与证据见只追加的 [月度状态日志](status-log/2026-08.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `candidate` |
| 更新时间 | `2026-08-03` |
| 当前产品目标 | 用公开等价夹具复现 Stage 12 `generation_shape` 粗码并细分安全诊断，不放宽生成合同或改变产品 outcome |
| 项目基线 | `origin/main@8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24` |
| 运行产品 | 公开 Beta；`product/0.1.0` 未发布；最近核验公网 `status=ok`、`live_experience=available`、`release_sha=8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24` |
| 当前治理结果 | PR [#61](https://github.com/suuny-ab/traceable-support-agent/pull/61) 已从精确 head `074bab2bb00268957321da40348a58fca1b82797` squash merge 为 `8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24`；main CI、部署与公网完整 SHA 已核验 |
| 当前产品候选 | Draft PR [#62](https://github.com/suuny-ab/traceable-support-agent/pull/62)（`night-20260802`）；generation_shape 诊断修复本地全绿，待实现提交、推送与最终 head required Checks |
| 活动工作 | [`stage12-generation-shape-diagnostics`](work/active/stage12-generation-shape-diagnostics/spec.md)（`docs/work/active/stage12-generation-shape-diagnostics/`）：公开等价复现与安全诊断码；[`stage12-handoff-scoring-contract`](work/active/stage12-handoff-scoring-contract/spec.md)（`docs/work/active/stage12-handoff-scoring-contract/`）、[`stage12-failure-root-cause`](work/active/stage12-failure-root-cause/spec.md)（`docs/work/active/stage12-failure-root-cause/`）、[`stage12-post-fix-revalidation`](work/active/stage12-post-fix-revalidation/spec.md)（`docs/work/active/stage12-post-fix-revalidation/`）：既有证据；[`public-metrics-card`](work/active/public-metrics-card/spec.md)（`docs/work/active/public-metrics-card/`）、[`retrieval-unseen-holdout`](work/active/retrieval-unseen-holdout/spec.md)（`docs/work/active/retrieval-unseen-holdout/`）、[`minimal-observability`](work/active/minimal-observability/spec.md)（`docs/work/active/minimal-observability/`）：既有候选 |
| 风险 / 授权 | 完整 / R2；只读既有脱敏记录、只用公开合成响应离线修复诊断，不运行 Stage 12 / Provider；夜班授权允许推送集成分支并更新 Draft PR #62，不授权 Ready、合并、部署、发布或产品 outcome 取舍 |
| Provider | `provider_enabled=true`；凭据仍只在服务器 `/opt/traceable-support/provider.env`（0600）。既有复验授权已消费且不得补跑；本评分修复调用 0、自动重试 0、费用 0 |
| 阻碍 | 历史 Provider 正文未保留，目标案例的精确 malformed 子条件不可恢复；false-completion 的 safe candidate vs typed handoff 仍需后续用户产品取舍，未触碰；发布主张继续被历史 Stage 12 结果阻断 |
| 当前证据 | 公开四分支在基线 4/4 复现旧码，候选 4/4 得到安全子码且产品链仍 4/4 handoff；定向 9 tests、API 158 passed / 4 skipped、治理 120 passed / 8 skipped，公开扫描 266 files / 8 cases，Provider 调用 0 |

## 当前队列

| Task | 状态 | 候选 / 下一动作 |
| --- | --- | --- |
| `stage12-generation-shape-diagnostics` | `candidate_local_green` | 四分支离线复现、诊断拆码、产品 handoff 与全量治理通过；待推送及 Draft PR #62 最终 head Checks |
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

本切片停止点：公开四分支稳定复现旧 generation_shape 粗码，候选返回四个安全子码且仍全部
handoff，运行全量治理并确认 Draft PR #62 最终 head required Checks 全绿后停止。不恢复或
猜测历史 Provider 正文，不运行 Stage 12 / Provider，不放宽合同或改产品 outcome，不转 Ready、
不合并、不部署、不发布。

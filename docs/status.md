# 当前开发状态

> 本文件只保存当前字段、当前队列和下一检查点；历史回执、旧队列与证据见只追加的 [月度状态日志](status-log/2026-08.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `candidate` |
| 更新时间 | `2026-08-03` |
| 当前产品目标 | 如实收口今夜四类根因修复与 typed handoff 候选在同一已消费 Stage 12 集上的唯一真实复跑 |
| 项目基线 | `origin/main@8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24` |
| 运行产品 | 公开 Beta；`product/0.1.0` 未发布；最近核验公网 `status=ok`、`live_experience=available`、`release_sha=8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24` |
| 当前治理结果 | PR [#61](https://github.com/suuny-ab/traceable-support-agent/pull/61) 已从精确 head `074bab2bb00268957321da40348a58fca1b82797` squash merge 为 `8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24`；main CI、部署与公网完整 SHA 已核验 |
| 当前产品候选 | Draft PR [#62](https://github.com/suuny-ab/traceable-support-agent/pull/62)（`night-20260802`）；真实复跑绑定 `fc766709f48bf2989c6589a56db3cec7593ed6cb`；结果实现 head `adf5c74a53756019f6ceae7b745468b2fd703802` 的 CI run `30765242124` 四项 required jobs 全绿，待本回执最终 head Checks |
| 活动工作 | [`stage12-night-fixes-revalidation`](work/active/stage12-night-fixes-revalidation/spec.md)（`docs/work/active/stage12-night-fixes-revalidation/`）：唯一真实复跑；[`stage12-typed-handoff-boundaries`](work/active/stage12-typed-handoff-boundaries/spec.md)（`docs/work/active/stage12-typed-handoff-boundaries/`）：R2 outcome 边界；[`stage12-obligation-source-contracts`](work/active/stage12-obligation-source-contracts/spec.md)（`docs/work/active/stage12-obligation-source-contracts/`）、[`stage12-generation-shape-diagnostics`](work/active/stage12-generation-shape-diagnostics/spec.md)（`docs/work/active/stage12-generation-shape-diagnostics/`）、[`stage12-handoff-scoring-contract`](work/active/stage12-handoff-scoring-contract/spec.md)（`docs/work/active/stage12-handoff-scoring-contract/`）、[`stage12-failure-root-cause`](work/active/stage12-failure-root-cause/spec.md)（`docs/work/active/stage12-failure-root-cause/`）、[`stage12-post-fix-revalidation`](work/active/stage12-post-fix-revalidation/spec.md)（`docs/work/active/stage12-post-fix-revalidation/`）：既有 Stage 12 证据；[`public-metrics-card`](work/active/public-metrics-card/spec.md)（`docs/work/active/public-metrics-card/`）、[`retrieval-unseen-holdout`](work/active/retrieval-unseen-holdout/spec.md)（`docs/work/active/retrieval-unseen-holdout/`）、[`minimal-observability`](work/active/minimal-observability/spec.md)（`docs/work/active/minimal-observability/`）：既有候选 |
| 风险 / 授权 | 完整 / R2；用户批准的唯一 Stage 12 Provider 复跑已消费：24 案例 / 150 调用 / ¥10 上限、自动重试 0、不补跑；夜班授权允许推送集成分支并更新 Draft PR #62，不授权 Ready、合并、部署或发布 |
| Provider | `provider_enabled=true`；生产凭据仍只在服务器 `/opt/traceable-support/provider.env`（0600），本轮执行凭据也只在 Git 外。本轮 28 次调用、27 条有效 usage、215,176 tokens、机制估算 ¥0.7169342，自动重试 0；缺 1 条 usage，非账单确认；授权已耗尽 |
| 阻碍 | 最新回归仍有 13 题未满足完整机械合同，四个 candidate 维度均 0/3，发布主张继续阻断；本切片只待状态回执最终 head Checks |
| 当前证据 | 同一已消费集 24/24 执行、11 通过、失败码 14 次；六个新 typed handoff 全部 type + reason 命中、0 调用并通过；API 163 / 4 skipped、治理 123 / 8 skipped、Web 36、公开扫描 282 files / 8 cases、私有新敏感长字符串命中 0；实现 head CI 四项全绿 |

## 当前队列

| Task | 状态 | 候选 / 下一动作 |
| --- | --- | --- |
| `stage12-night-fixes-revalidation` | `candidate_ci_green` | 24/24、11 通过、28 调用、六个 typed handoff 全命中；实现 head CI 绿，待状态回执最终 head Checks |
| `stage12-typed-handoff-boundaries` | `candidate_ci_green` | 六行决策表、公开等价回归与真实复跑六例 type + reason / 0 调用 / 全通过；待最终 head Checks |
| `stage12-obligation-source-contracts` | `candidate_ci_green` | 公开夹具、24 题 scorer-only 差异、全量治理与实现 head CI 通过；待状态回执最终 head Checks |
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

本切片停止点：唯一真实复跑与脱敏对比已落盘；Provider 授权已耗尽，不补跑。运行公开安全 /
泄漏 / 全量治理并确认 Draft PR #62 最终 head required Checks 全绿后停止；不转 Ready、不合并、
不部署、不发布。

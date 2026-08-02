# 当前开发状态

> 本文件只保存当前字段、当前队列和下一检查点；历史回执、旧队列与证据见只追加的 [月度状态日志](status-log/2026-08.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `candidate` |
| 更新时间 | `2026-08-03` |
| 当前产品目标 | 用 proposition → obligation → claim / evidence 确定性收据替换 R6 客户可见字面子串判据；自然改写通过，缺失和越界继续失败关闭 |
| 项目基线 | `origin/main@8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24` |
| 运行产品 | 公开 Beta；`product/0.1.0` 未发布；最近核验公网 `status=ok`、`live_experience=available`、`release_sha=8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24` |
| 当前治理结果 | PR [#61](https://github.com/suuny-ab/traceable-support-agent/pull/61) 已从精确 head `074bab2bb00268957321da40348a58fca1b82797` squash merge 为 `8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24`；main CI、部署与公网完整 SHA 已核验 |
| 当前产品候选 | Draft PR [#62](https://github.com/suuny-ab/traceable-support-agent/pull/62)（`night-20260802`）；真实复跑身份与历史数字不变；R6 proposition binding receipt 实现 head `44fdf33364f346d727e4c9a275269787894a6d30` 的 CI run `30767423207` 四项 required jobs 全绿，待状态回执最终 head Checks |
| 活动工作 | [`stage12-r6-proposition-receipt`](work/active/stage12-r6-proposition-receipt/spec.md)（`docs/work/active/stage12-r6-proposition-receipt/`）：R6 判据实现与离线回归；[`stage12-r6-semantic-audit`](work/active/stage12-r6-semantic-audit/spec.md)（`docs/work/active/stage12-r6-semantic-audit/`）：前置六题确定性审计；[`stage12-night-fixes-revalidation`](work/active/stage12-night-fixes-revalidation/spec.md)（`docs/work/active/stage12-night-fixes-revalidation/`）：唯一真实复跑；[`stage12-typed-handoff-boundaries`](work/active/stage12-typed-handoff-boundaries/spec.md)（`docs/work/active/stage12-typed-handoff-boundaries/`）：R2 outcome 边界；[`stage12-obligation-source-contracts`](work/active/stage12-obligation-source-contracts/spec.md)（`docs/work/active/stage12-obligation-source-contracts/`）、[`stage12-generation-shape-diagnostics`](work/active/stage12-generation-shape-diagnostics/spec.md)（`docs/work/active/stage12-generation-shape-diagnostics/`）、[`stage12-handoff-scoring-contract`](work/active/stage12-handoff-scoring-contract/spec.md)（`docs/work/active/stage12-handoff-scoring-contract/`）、[`stage12-failure-root-cause`](work/active/stage12-failure-root-cause/spec.md)（`docs/work/active/stage12-failure-root-cause/`）、[`stage12-post-fix-revalidation`](work/active/stage12-post-fix-revalidation/spec.md)（`docs/work/active/stage12-post-fix-revalidation/`）：既有 Stage 12 证据；[`public-metrics-card`](work/active/public-metrics-card/spec.md)（`docs/work/active/public-metrics-card/`）、[`retrieval-unseen-holdout`](work/active/retrieval-unseen-holdout/spec.md)（`docs/work/active/retrieval-unseen-holdout/`）、[`minimal-observability`](work/active/minimal-observability/spec.md)（`docs/work/active/minimal-observability/`）：既有候选 |
| 风险 / 授权 | 完整 / R2；用户批准的唯一 Stage 12 Provider 复跑已消费：24 案例 / 150 调用 / ¥10 上限、自动重试 0、不补跑；夜班授权允许推送集成分支并更新 Draft PR #62，不授权 Ready、合并、部署或发布 |
| Provider | `provider_enabled=true`；生产凭据仍只在服务器 `/opt/traceable-support/provider.env`（0600），本轮执行凭据也只在 Git 外。本轮 28 次调用、27 条有效 usage、215,176 tokens、机制估算 ¥0.7169342，自动重试 0；缺 1 条 usage，非账单确认；授权已耗尽 |
| 阻碍 | 候选 scorer 只能机械证明绑定身份、范围和完整性，不能证明开放域语义真实性；离线回归仍有 7 题 / 8 码涉及义务、outcome 与来源失败，发布主张继续阻断 |
| 当前证据 | 公开自然改写 / 缺义务 / 缺 claim / 越源 / 伪造 ID 正反例通过；已消费六个 R6 案例在候选 scorer 下 6/6 恢复，其余 18 例分类不变；Stage 12 25、API 163 / 4 skipped、治理 126 / 8 skipped、Web 36、公开扫描 293 files / 8 cases、私有新增长字符串命中 0；Provider 调用 0，历史 24/24、11 通过、14 码不改 |

## 当前队列

| Task | 状态 | 候选 / 下一动作 |
| --- | --- | --- |
| `stage12-r6-proposition-receipt` | `candidate_ci_green` | 公开正反例、六题 / 18 题零漂移离线回归和全量治理已通过；实现 head CI 绿，待状态回执最终 head Checks |
| `stage12-r6-semantic-audit` | `candidate_ci_green` | 六题 / 11 命题逐条完成，真遗漏 0、字面假阴性 6；后续实现由 `stage12-r6-proposition-receipt` 承接 |
| `stage12-night-fixes-revalidation` | `candidate_ci_green` | 24/24、11 通过、28 调用、六个 typed handoff 全命中；最终 head `4a69a077` 四项 required Checks 全绿 |
| `stage12-typed-handoff-boundaries` | `candidate_ci_green` | 六行决策表、公开等价回归与真实复跑六例 type + reason / 0 调用 / 全通过；待最终 head Checks |
| `stage12-obligation-source-contracts` | `candidate_ci_green` | 公开夹具、24 题 scorer-only 差异、全量治理与实现 head CI 通过；待状态回执最终 head Checks |
| `stage12-generation-shape-diagnostics` | `candidate_ci_green` | 四分支离线复现、诊断拆码、产品 handoff、全量治理与实现 head CI 通过；待状态回执最终 head Checks |
| `stage12-handoff-scoring-contract` | `candidate_ci_green` | 4 题 / 6 码定向修复、20 题零漂移；实现 head CI 全绿，待状态回执最终 head Checks |
| `stage12-failure-root-cause` | `candidate_ci_green` | 六类根因与最小修复候选已落文档；实现 head CI 全绿，待状态回执最终 head Checks，不实施修复 |
| `stage12-post-fix-revalidation` | `candidate_ci_green` | 24/24、2 通过已落盘；结果 head CI 全绿，待状态回执最终 head Checks，不补跑 |
| `public-metrics-card` | `candidate_ci_green` | 实现 head `b01adb9b` 与 run `30753847922` 全绿；待回执提交最终 head Checks，不自动 Ready / 合并 / 部署 |
| `retrieval-unseen-holdout` | `observed_frozen` | 首次检索观察已落盘；只作回归，不改检索 / 题 / 标签 / 知识；待全集、治理和 Draft PR #62 最终 head Checks |
| `minimal-observability` | `candidate_ci_green` | 随 Draft PR #62 上一最终 head `4a69a077` 四项 required Checks 全绿；不自动转 Ready、合并或部署 |
| `pgvector-production-integration` | `delivered` | PR #61 merge / main CI / deploy / 公网完整 SHA 均已核验；工作记录已归档到 `docs/work/completed/` |
| `dependency-security-maintenance` | `delivered` | PR #60 已交付；不在本切片继续依赖升级 |
| `ISSUE-14-RELEASE-DECISION` | `deferred` | 不在本切片内；不得从依赖修复推导发布结论 |

## 下一检查点

本切片停止点：完成 R6 proposition binding receipt 判据、公开正反例、已消费六题 / 其余 18 题
离线回归和脱敏收据；Provider 授权已耗尽，不重跑、不补跑。运行公开安全 / 泄漏 / 全量治理并
确认 Draft PR #62 最终 head required Checks 全绿后停止；不转 Ready、不合并、不部署、不发布。

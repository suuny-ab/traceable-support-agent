# 当前开发状态

> 本文件只保存当前字段、当前队列和下一检查点；历史回执、旧队列与证据见只追加的 [月度状态日志](status-log/2026-08.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `candidate` |
| 更新时间 | `2026-08-02` |
| 当前产品目标 | 用既有 Stage 12 runner 对同一已消费私有冻结集执行一次生成门修复后复验，并把新观测与原 `19/24、9 通过`并列，不倒写历史 |
| 项目基线 | `origin/main@8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24` |
| 运行产品 | 公开 Beta；`product/0.1.0` 未发布；最近核验公网 `status=ok`、`live_experience=available`、`release_sha=8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24` |
| 当前治理结果 | PR [#61](https://github.com/suuny-ab/traceable-support-agent/pull/61) 已从精确 head `074bab2bb00268957321da40348a58fca1b82797` squash merge 为 `8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24`；main CI、部署与公网完整 SHA 已核验 |
| 当前产品候选 | Draft PR [#62](https://github.com/suuny-ab/traceable-support-agent/pull/62)（`night-20260802`）；复验绑定候选 `df01968c56350626544ca4acc4ed88cf13dfd337`，后续只增加结果与状态回执并证明产品 / runner / prompt 身份未漂移 |
| 活动工作 | [`stage12-post-fix-revalidation`](work/active/stage12-post-fix-revalidation/spec.md)（`docs/work/active/stage12-post-fix-revalidation/`）：一次真实复验；[`public-metrics-card`](work/active/public-metrics-card/spec.md)（`docs/work/active/public-metrics-card/`）、[`retrieval-unseen-holdout`](work/active/retrieval-unseen-holdout/spec.md)（`docs/work/active/retrieval-unseen-holdout/`）、[`minimal-observability`](work/active/minimal-observability/spec.md)（`docs/work/active/minimal-observability/`）：既有候选 |
| 风险 / 授权 | 完整 / R2；用户在夜班派发中批准既有 runner 的一次复验：DeepSeek `deepseek-v4-pro`、24 案例 / 150 调用 / ¥10 上限、自动重试 0、不补跑；只更新 Draft PR #62，不授权 Ready、合并、部署或发布 |
| Provider | `provider_enabled=true`；凭据仍只在服务器 `/opt/traceable-support/provider.env`（0600）。本任务唯一一次复验已消费：39 调用、35 条有效 usage / 297,406 tokens、机制估算 ¥1.2599124，自动重试 0；不得补跑 |
| 阻碍 | 产品质量 / 发布主张仍被复验结果阻断；本任务工程交付只待 Draft PR #62 最终 head required Checks |
| 当前证据 | 原始 Stage 12 19/24、9 通过不变；修复后同一已消费集首次复验 24/24、2 通过、39 调用、未提前停止；Stage 12 15 tests、API 全集、治理 116 / 8 skipped、公开仓 251 files、园丁 stale 0 均绿 |

## 当前队列

| Task | 状态 | 候选 / 下一动作 |
| --- | --- | --- |
| `stage12-post-fix-revalidation` | `candidate_local_green` | 24/24、2 通过与本地检查已落盘；推送 Draft PR #62 并确认最终 head Checks，不补跑 |
| `public-metrics-card` | `candidate_ci_green` | 实现 head `b01adb9b` 与 run `30753847922` 全绿；待回执提交最终 head Checks，不自动 Ready / 合并 / 部署 |
| `retrieval-unseen-holdout` | `observed_frozen` | 首次检索观察已落盘；只作回归，不改检索 / 题 / 标签 / 知识；待全集、治理和 Draft PR #62 最终 head Checks |
| `minimal-observability` | `candidate` | Draft PR #62；等待最终 head 的 required Checks，不自动转 Ready、合并或部署 |
| `pgvector-production-integration` | `delivered` | PR #61 merge / main CI / deploy / 公网完整 SHA 均已核验；工作记录已归档到 `docs/work/completed/` |
| `dependency-security-maintenance` | `delivered` | PR #60 已交付；不在本切片继续依赖升级 |
| `ISSUE-14-RELEASE-DECISION` | `deferred` | 不在本切片内；不得从依赖修复推导发布结论 |

## 下一检查点

本切片停止点：复验已如实落盘；完成相关检查并确认 Draft PR #62 最终 head required Checks
全绿后停止。不转 Ready、不合并、不部署、不补跑、不发布 `product/0.1.0`。

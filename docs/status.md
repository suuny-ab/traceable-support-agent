# 当前开发状态

> 本文件只保存当前字段、当前队列和下一检查点；历史回执、旧队列与证据见只追加的 [月度状态日志](status-log/2026-08.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `candidate` |
| 更新时间 | `2026-08-02` |
| 当前产品目标 | 在不改变生产语料、检索、生成、Provider 或部署的前提下，冻结并首次观测 10 题独立合成检索未见集；揭示后只作回归记录 |
| 项目基线 | `origin/main@8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24` |
| 运行产品 | 公开 Beta；`product/0.1.0` 未发布；最近核验公网 `status=ok`、`live_experience=available`、`release_sha=8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24` |
| 当前治理结果 | PR [#61](https://github.com/suuny-ab/traceable-support-agent/pull/61) 已从精确 head `074bab2bb00268957321da40348a58fca1b82797` squash merge 为 `8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24`；main CI、部署与公网完整 SHA 已核验 |
| 当前产品候选 | Draft PR [#62](https://github.com/suuny-ab/traceable-support-agent/pull/62)（`night-20260802`）已含最小观测面与冻结未见集首次观察；观察实现 head `a21afb20bd7bd7e6a4c777dc96ffd478e31fc3b0` 的 CI run `30752922314` 成功，回执提交后的最终 head Checks 以 GitHub 实时状态为准 |
| 活动工作 | [`retrieval-unseen-holdout`](work/active/retrieval-unseen-holdout/spec.md)（`docs/work/active/retrieval-unseen-holdout/`）：冻结、首次观测与回执；[`minimal-observability`](work/active/minimal-observability/spec.md)（`docs/work/active/minimal-observability/`）：既有候选仍在同一 Draft PR #62 |
| 风险 / 授权 | HOLDOUT 已揭示，只可回归，不得用于检索调参；用户授权推送 `night-20260802` 和更新 Draft PR #62，不授权 Ready、合并、部署、Provider、费用或生产状态修改 |
| Provider | `provider_enabled=true`；凭据仍仅在服务器 `/opt/traceable-support/provider.env`（0600）；预算日 ¥20 / 月 ¥100 / 次 ¥1、自动重试 0；本任务 Provider 调用 0 |
| 阻碍 | 无；本切片在状态回执提交推送、最终 head required Checks 启动后停止，PR 保持 Draft |
| 当前证据 | 冻结提交 `6e57c5e229af01f4949df9c99d6ec6bdf03af74a`；三类重复均 0；三检索 Top-5 / Top-10 均 10/10、错误型号均 0；API 149 passed / 4 skipped / 24 subtests；治理 114 passed / 8 skipped；公开仓通过；CI run `30752922314` 四个 required jobs 全绿；Provider / generation 0 |

## 当前队列

| Task | 状态 | 候选 / 下一动作 |
| --- | --- | --- |
| `retrieval-unseen-holdout` | `observed_frozen` | 首次检索观察已落盘；只作回归，不改检索 / 题 / 标签 / 知识；待全集、治理和 Draft PR #62 最终 head Checks |
| `minimal-observability` | `candidate` | Draft PR #62；等待最终 head 的 required Checks，不自动转 Ready、合并或部署 |
| `pgvector-production-integration` | `delivered` | PR #61 merge / main CI / deploy / 公网完整 SHA 均已核验；工作记录已归档到 `docs/work/completed/` |
| `dependency-security-maintenance` | `delivered` | PR #60 已交付；不在本切片继续依赖升级 |
| `ISSUE-14-RELEASE-DECISION` | `deferred` | 不在本切片内；不得从依赖修复推导发布结论 |

## 下一检查点

本切片停止点：状态回执提交形成最终 head 后，确认 Draft PR #62 的 required Checks 已启动；
不转 Ready、不合并、不部署。

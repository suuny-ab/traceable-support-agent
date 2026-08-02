# 当前开发状态

> 本文件只保存当前字段、当前队列和下一检查点；历史回执、旧队列与证据见只追加的 [月度状态日志](status-log/2026-08.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `candidate` |
| 更新时间 | `2026-08-02` |
| 当前产品目标 | 不新增或重算数字，为当前公开量化结果与运行约束建立统一口径卡，使定义、方法、数据集、复跑属性、证据与否定边界可回查 |
| 项目基线 | `origin/main@8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24` |
| 运行产品 | 公开 Beta；`product/0.1.0` 未发布；最近核验公网 `status=ok`、`live_experience=available`、`release_sha=8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24` |
| 当前治理结果 | PR [#61](https://github.com/suuny-ab/traceable-support-agent/pull/61) 已从精确 head `074bab2bb00268957321da40348a58fca1b82797` squash merge 为 `8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24`；main CI、部署与公网完整 SHA 已核验 |
| 当前产品候选 | Draft PR [#62](https://github.com/suuny-ab/traceable-support-agent/pull/62)（`night-20260802`）已含最小观测面与冻结未见集首次观察；本切片新增 8 张公开数字口径卡，本地治理全绿，待推送与最终 head Checks |
| 活动工作 | [`public-metrics-card`](work/active/public-metrics-card/spec.md)（`docs/work/active/public-metrics-card/`）：数字口径统一；[`retrieval-unseen-holdout`](work/active/retrieval-unseen-holdout/spec.md)（`docs/work/active/retrieval-unseen-holdout/`）：冻结观察；[`minimal-observability`](work/active/minimal-observability/spec.md)（`docs/work/active/minimal-observability/`）：既有候选 |
| 风险 / 授权 | 本切片只复述已有公开数字，不形成新测量；HOLDOUT 继续只可回归。用户授权推送 `night-20260802` 和更新 Draft PR #62，不授权 Ready、合并、部署、Provider、费用或生产修改 |
| Provider | `provider_enabled=true`；凭据仍仅在服务器 `/opt/traceable-support/provider.env`（0600）；预算日 ¥20 / 月 ¥100 / 次 ¥1、自动重试 0；本任务 Provider 调用 0 |
| 阻碍 | 无当前事实冲突；本地治理已全绿，待提交、推送和 Draft PR #62 最终 head Checks |
| 当前证据 | 8 张卡 / 22 个仓库链接逐项一致；治理 114 tests / 8 skipped；公开仓 246 files / 8 public cases；园丁 stale 0 / review 1；差异仅 docs；正式评测、Provider、generation、产品运行均为 0 |

## 当前队列

| Task | 状态 | 候选 / 下一动作 |
| --- | --- | --- |
| `public-metrics-card` | `local_candidate` | 8 张数字口径卡、只读一致性和本地治理已完成；待推送和 Draft PR #62 最终 head Checks |
| `retrieval-unseen-holdout` | `observed_frozen` | 首次检索观察已落盘；只作回归，不改检索 / 题 / 标签 / 知识；待全集、治理和 Draft PR #62 最终 head Checks |
| `minimal-observability` | `candidate` | Draft PR #62；等待最终 head 的 required Checks，不自动转 Ready、合并或部署 |
| `pgvector-production-integration` | `delivered` | PR #61 merge / main CI / deploy / 公网完整 SHA 均已核验；工作记录已归档到 `docs/work/completed/` |
| `dependency-security-maintenance` | `delivered` | PR #60 已交付；不在本切片继续依赖升级 |
| `ISSUE-14-RELEASE-DECISION` | `deferred` | 不在本切片内；不得从依赖修复推导发布结论 |

## 下一检查点

提交并推送 `night-20260802`，确认 Draft PR #62 最终 head 的 required Checks 全绿后停止；
不转 Ready、不合并、不部署。

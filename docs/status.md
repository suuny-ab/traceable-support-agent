# 当前开发状态

> 本文件只保存当前字段、当前队列和下一检查点；历史回执、旧队列与证据见只追加的 [月度状态日志](status-log/2026-08.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `in_progress` |
| 更新时间 | `2026-08-02` |
| 当前产品目标 | 在不改变业务行为、Provider 或部署形态的前提下，为现有 API 增加请求计数、延迟和错误分类的最小被动观测面 |
| 项目基线 | `origin/main@8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24` |
| 运行产品 | 公开 Beta；`product/0.1.0` 未发布；最近核验公网 `status=ok`、`live_experience=available`、`release_sha=8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24` |
| 当前治理结果 | PR [#61](https://github.com/suuny-ab/traceable-support-agent/pull/61) 已从精确 head `074bab2bb00268957321da40348a58fca1b82797` squash merge 为 `8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24`；main CI、部署与公网完整 SHA 已核验 |
| 当前产品候选 | `night-20260802` 本地候选增加 SQLite 聚合观测、中间件失败降级和 `GET /api/v1/observability`；尚未提交、推送或创建 PR |
| 活动工作 | [`minimal-observability`](work/active/minimal-observability/spec.md)（`docs/work/active/minimal-observability/`）：实现、验证和 Draft PR 交付；不做告警、仪表盘、外部监控或生产部署 |
| 风险 / 授权 | 用户预授权推送 `night-20260802` 并创建 Draft PR；不授权 Ready、合并、部署、Provider、费用或生产状态修改 |
| Provider | `provider_enabled=true`；凭据仍仅在服务器 `/opt/traceable-support/provider.env`（0600）；预算日 ¥20 / 月 ¥100 / 次 ¥1、自动重试 0；本任务 Provider 调用 0 |
| 阻碍 | 无当前本地阻断；尚需提交、Draft PR 与远端 required Checks 启动回执 |
| 当前证据 | API 定向 19 passed；API 全集 147 passed / 4 skipped / 24 subtests；治理 114 passed / 8 skipped；公开仓 233 files / 8 public cases；园丁 stale 0 / review 1；观测写失败保持 health 200，Provider 调用 0 |

## 当前队列

| Task | 状态 | 候选 / 下一动作 |
| --- | --- | --- |
| `minimal-observability` | `in_progress` | 本地实现、API 与治理验证已完成；下一步提交、推送和 Draft PR |
| `pgvector-production-integration` | `delivered` | PR #61 merge / main CI / deploy / 公网完整 SHA 均已核验；工作记录已归档到 `docs/work/completed/` |
| `dependency-security-maintenance` | `delivered` | PR #60 已交付；不在本切片继续依赖升级 |
| `ISSUE-14-RELEASE-DECISION` | `deferred` | 不在本切片内；不得从依赖修复推导发布结论 |

## 下一检查点

提交并推送 `night-20260802`、创建 Draft PR；确认 required Checks 启动即停止，不转 Ready、不合并、不部署。

# 当前开发状态

> 本文件只保存当前字段、当前队列和下一检查点；历史回执、旧队列与证据见只追加的 [月度状态日志](status-log/2026-08.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `candidate` |
| 更新时间 | `2026-08-02` |
| 当前产品目标 | 让 pgvector 只有在 DSN、版本化 schema、表 / 索引和数据库健康全部过门后才接管稠密检索，失效时自动回到行为一致的内存检索 |
| 项目基线 | `origin/main@db72aa0e3b31ad749ba1f991ecd5b2ca4c1fa949` |
| 运行产品 | 公开 Beta；`product/0.1.0` 未发布；最近核验公网 `status=ok`、`live_experience=available`、`release_sha=db72aa0e3b31ad749ba1f991ecd5b2ca4c1fa949` |
| 当前治理结果 | PR [#60](https://github.com/suuny-ab/traceable-support-agent/pull/60) 已 squash merge 为 `db72aa0e3b31ad749ba1f991ecd5b2ca4c1fa949`；main CI `30747284056`、部署 `30747449697` 与公网完整 SHA 均核验成功 |
| 当前产品候选 | `codex/pgvector-production-integration` 增加版本化 readiness、运行期内存 fallback、内部持久 pgvector 编排和冻结 16 题对比；Draft PR / Checks 以 GitHub 实时状态为准 |
| 活动工作 | [`pgvector-production-integration`](work/active/pgvector-production-integration/spec.md)（`docs/work/active/pgvector-production-integration/`）：实现、真库 / 容器验证和候选交付；不新增知识、调参、Provider 或公开 API 字段 |
| 风险 / 授权 | 用户批准本分支推送与创建 Draft PR；未授权转 Ready、合并或部署，PR 建成后写 Git 外授权请求并等待当次明文批准 |
| Provider | `provider_enabled=true`；凭据仍仅在服务器 `/opt/traceable-support/provider.env`（0600）；预算日 ¥20 / 月 ¥100 / 次 ¥1、自动重试 0；本任务 Provider 调用 0 |
| 阻碍 | 无本地阻断；候选必须等待 GitHub required Checks 结论，之后另行申请精确 head 合并授权 |
| 当前证据 | 真库 schema / 排序 6 passed；API 148 passed / 24 subtests；同一 16 题两路 Top-5 / Top-10 均 16/16、错误型号 0、Top-10 逐题一致，冷启动内存 / pgvector 为 2035.846 / 1955.757ms，热态中位数 192.534 / 580.385ms；live 容器 pgvector / memory fallback / 四字段 health 与 8-case 离线检索通过；治理 114 passed / 8 skipped，Web 36 tests 与构建通过；Provider 调用 0 |

## 当前队列

| Task | 状态 | 候选 / 下一动作 |
| --- | --- | --- |
| `pgvector-production-integration` | `candidate` | 推送并建 Draft PR；required Checks 后只写精确 head 授权请求，不自动转 Ready / 合并 / 部署 |
| `dependency-security-maintenance` | `delivered` | PR #60 merge / main CI / deploy / 公网完整 SHA 均已核验；不在本切片继续依赖升级 |
| `dependency-drift` | `delivered` | PR #59 merge / main CI / deploy / 公网完整 SHA 均已核验 |
| `doc-gardener` | `delivered` | PR #58 merge / main CI / deploy / 公网完整 SHA 均已核验；默认 advisory，不自动修改文档 |
| `ISSUE-14-RELEASE-DECISION` | `deferred` | 不在本切片内；不得从依赖修复推导发布结论 |

## 下一检查点

推送并创建 Draft PR；确认 required Checks 启动及结论后，在 Git 外提交精确 head 合并授权请求并停止。

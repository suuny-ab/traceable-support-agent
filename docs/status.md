# 当前开发状态

> 本文件只保存当前字段、当前队列和下一检查点；历史回执、旧队列与证据见只追加的 [月度状态日志](status-log/2026-08.md)。

| 字段 | 内容 |
| --- | --- |
| `state` | `candidate` |
| 更新时间 | `2026-08-03` |
| 当前产品目标 | 夜间集成包的产品、评测与证据增量已经完成；保持候选边界真实并交给 GitHub exact-head 门、当次外部授权与公网运行身份完成后续发布核验，不继续扩展功能 |
| 纠偏时项目基线 | `origin/main@8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24`；这是本次 pre-merge 状态纠偏的固定基线，不冒充后续 GitHub 实时状态 |
| 纠偏时运行基线 | 公开 Beta；`product/0.1.0` 未发布；公网在本次纠偏前返回 `status=ok`、`live_experience=available`、`release_sha=8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24` |
| 当前治理证据 | 夜间集成 old head `463b58f50602cb8290e7d618d021ae2c00c8704f` 的 `ci-release` run `30767510251` 中 governance、web、api、containers 全部成功，PR 事件 publish 跳过；本状态纠偏必须形成新 exact head 并重新通过相同 required Checks，精确新 head 只由 GitHub / 外部回执记录 |
| 当前产品候选 | [PR #62](https://github.com/suuny-ab/traceable-support-agent/pull/62) 的夜间集成包：P1 聚合观测、公开 HOLDOUT 首次观测、数字口径卡、Stage 12 诊断与机械合同修复、Provider 前 typed handoff、唯一复跑及 R6 命题绑定收据均已完成；本文件不声明 PR 当前 lifecycle 或部署结果，实时状态分别以 GitHub 与公网完整 `release_sha` 为准 |
| 风险 / 授权 | 完整 / R2；唯一 Stage 12 Provider 复跑授权已消费且不得补跑。第一次发布授权只绑定 old head，并因本次必须产生新 head 而失效；任何 Ready、merge、deploy 都必须在 Git 外重新绑定 exact base/head 明文批准，Git 文件不能授予外部动作 |
| Provider | 生产 `provider_enabled=true`；凭据仍只在服务器 `/opt/traceable-support/provider.env`（0600）。夜间唯一复跑为 28 次调用、27 条有效 usage、215,176 tokens、机制估算 ¥0.7169342、自动重试 0，缺 1 条 usage 所以不是账单确认。本状态纠偏的 Provider 调用、评测、产品运行与服务器动作均为 0 |
| 质量边界 | 历史真实复跑保持 24/24 执行、11 通过、14 个失败码；候选 scorer 的 17/24、8 码只作同一已消费集离线回归。剩余 7 题 / 8 码继续限制 `product/0.1.0` 正式质量主张，但不替代 Public Beta 候选的独立 exact-head 发布授权判断 |
| 当前证据 | 夜间集成本地与 required Checks 已覆盖 API、Web、容器、治理、公开安全、HOLDOUT 冻结边界、typed handoff 和 R6 收据；能证明候选合同与固定回归，不证明新 unseen/generalization、线上成功率、开放域语义真实性、SLA 或 `product/0.1.0` 发布成熟度 |

## 夜间集成候选组成（均已完成）

| 组成 | 状态 | 结果边界 |
| --- | --- | --- |
| [`minimal-observability`](work/active/minimal-observability/spec.md) (`docs/work/active/minimal-observability/`) | `candidate_complete` | SQLite 聚合观测与只读端点；无外部监控、原始请求或质量证明 |
| [`retrieval-unseen-holdout`](work/active/retrieval-unseen-holdout/spec.md) (`docs/work/active/retrieval-unseen-holdout/`) | `observed_frozen` | 10 题公开合成 HOLDOUT 首次观察已冻结，揭示后只作回归 |
| [`public-metrics-card`](work/active/public-metrics-card/spec.md) (`docs/work/active/public-metrics-card/`) | `candidate_complete` | 统一既有数字定义与证据边界，不产生新测量 |
| [`stage12-post-fix-revalidation`](work/active/stage12-post-fix-revalidation/spec.md) (`docs/work/active/stage12-post-fix-revalidation/`) | `candidate_complete` | 同一已消费集首次复验 24/24、2 通过；不补跑 |
| [`stage12-failure-root-cause`](work/active/stage12-failure-root-cause/spec.md) (`docs/work/active/stage12-failure-root-cause/`) | `candidate_complete` | 失败信号完整归类，不自动形成修复或产品取舍 |
| [`stage12-handoff-scoring-contract`](work/active/stage12-handoff-scoring-contract/spec.md) (`docs/work/active/stage12-handoff-scoring-contract/`) | `candidate_complete` | matched handoff 与 candidate 评分合同分离 |
| [`stage12-generation-shape-diagnostics`](work/active/stage12-generation-shape-diagnostics/spec.md) (`docs/work/active/stage12-generation-shape-diagnostics/`) | `candidate_complete` | 生成外形粗码离线细分，不恢复历史私有响应 |
| [`stage12-obligation-source-contracts`](work/active/stage12-obligation-source-contracts/spec.md) (`docs/work/active/stage12-obligation-source-contracts/`) | `candidate_complete` | 义务规划与合法额外来源机械账本 |
| [`stage12-typed-handoff-boundaries`](work/active/stage12-typed-handoff-boundaries/spec.md) (`docs/work/active/stage12-typed-handoff-boundaries/`) | `candidate_complete` | 六类边界在 Provider 前 typed handoff，固定案例 0 调用 |
| [`stage12-night-fixes-revalidation`](work/active/stage12-night-fixes-revalidation/spec.md) (`docs/work/active/stage12-night-fixes-revalidation/`) | `candidate_complete` | 唯一夜间真实复跑 24/24、11 通过、28 调用，不补跑 |
| [`stage12-r6-semantic-audit`](work/active/stage12-r6-semantic-audit/spec.md) (`docs/work/active/stage12-r6-semantic-audit/`) | `candidate_complete` | 六题 / 11 命题审计：真遗漏 0、字面假阴性 6 |
| [`stage12-r6-proposition-receipt`](work/active/stage12-r6-proposition-receipt/spec.md) (`docs/work/active/stage12-r6-proposition-receipt/`) | `candidate_complete` | 命题绑定收据取代客户可见字面门；六题回归 6/6、其余 18 题分类不变 |

## 当前队列

| Task | 状态 | 候选 / 下一动作 |
| --- | --- | --- |
| `night-20260802-integration` | `candidate_complete` | 上述 12 个组成已收口；本状态提交不自指 SHA，外部 release gate 负责新 head Checks、当次授权、merge / deploy 与运行身份 |
| `ISSUE-14-RELEASE-DECISION` | `deferred` | `product/0.1.0` 继续未发布；不得把 Public Beta 候选部署等同正式质量门通过 |

## 下一检查点

本状态提交的 pre-merge 门序列固定为：状态纠偏 commit → 新 exact head required Checks → 停止并
等待用户对该新 base/head 重新批准发布。它不声明 PR 此刻仍为 Draft 或尚未合并；后续生命周期以
GitHub 为准，生产身份只以公网 `/api/v1/health` 的完整 `release_sha` 为准，避免未来合并后失真。

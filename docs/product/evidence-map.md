# 公开主张证据表

量化数字的定义、测量方法、数据集、复跑属性和否定边界统一见
[`metrics-card.md`](metrics-card.md)；下表继续负责把公开主张绑定到代码、测试和运行证据。

| 公开主张 | 证据 | 诚实边界 |
| --- | --- | --- |
| 四页作品集可以公开访问 | `/`、`/design`、`/app`、`/privacy` 的 HTTPS 冒烟检查 | 不证明最终视觉设计已经完成 |
| Provider 关闭时，公开服务会失败关闭 | API 集成测试和容器健康检查 | 不证明实时 Provider 的质量 |
| 生产已显式启用真实 Provider，公开工作台为 live 优先 | 部署版本 `766ba3f` 的 release manifest v2、生产部署与回滚回执、`/api/v1/health` 返回 `live_experience=available`；上线当日首条真实 QA 与 `2026-07-30` README GIF 来源运行均为 `completed` 且 `provider_calls=2` | 只证明该部署与两次公开运行；健康状态可能变化，不构成 SLA、长期成功率或 `product/0.1.0` 主张 |
| 运行受队列、预算和保留期控制 | API 单元/集成测试和 SQLite 重启测试 | 仅限单节点 |
| 候选 API 请求量、延迟和错误率可由只读端点查看 | `http_request_metrics` 聚合表、ASGI 中间件定向测试、写入失败降级测试和 `GET /api/v1/observability` 合同测试 | 尚未合并或部署；只覆盖当前单机 SQLite 生命周期内的进程请求，不是外部监控、告警、分布式追踪、SLA 或线上质量结论，不保存原始请求内容 |
| QA 与工单产品路径支持两阶段生成 | 离线 `live` target 产品 fixture 与既有固定合成运行；v14 QA003 真实两阶段合同通过并形成 candidate；Stage 12 原始观测 19/24、9 通过，首次同集复验 24/24、2 通过，今夜同集唯一复跑 24/24、11 通过（`evals/stage12-night-fixes-revalidation-v1.json`） | 最新复跑仍有 13 题未满足完整合同，四个 candidate 维度均为 0/3；复跑不是新未见评测，不能形成质量或因果主张 |
| 每条客户可见结论绑定真实存在的来源和业务义务 | ADR-0007；QA / 工单合同测试覆盖措辞漂移放行、伪造 ID 拒绝、越源拒绝和义务缺绑定拒绝；本地真实 Provider 固定案例复测由 0/2 提升到 3/3，公网首条 QA 候选挂载证据原文 | 绑定存在不等于开放域语义正确；最新 Stage 12 回归仍有事实缺失 6、义务规划缺失 6，候选仍需人工审核 |
| 人工批准不会执行外部动作 | 决定 API 合同，且不存在业务动作适配器 | 仅为演示 Workflow |
| 固定证据不足挑战可在调用 Provider 前形成类型明确的转人工结果 | `GEN-DEV-IE-001` 回放资产、公开机械预期绑定、Web 路由测试与公网 API 前置规则；Stage 12 原始观测该维度 3/3，修复后同集回归为 2/3 全合同通过 | 只证明固定合成挑战及其确定性规则；回归中仍有 1 题 outcome / 来源不匹配，不证明开放域证据不足识别 |
| 声明的公开合成安全事件与型号独占能力冲突可在生成前转人工 | `api/tests/test_product_boundaries.py`、公网 API 前置测试、`GEN-DEV-MH-001` 公开机械期望；transport factory 零构造、Provider 调用 0；今夜同集复跑的安全 / 型号维度均 3/3 | 只证明已声明规则及固定已消费案例，不证明开放域语义安全 |
| 候选 B 路线会把六类预登记跨型号、证据缺口与人工售后动作编译为 typed handoff | [`stage12-typed-handoff-boundaries/result.md`](../work/active/stage12-typed-handoff-boundaries/result.md)、产品边界 / 公共 API 测试、`GEN-DEV-MH-003` 公开机械期望；今夜同集唯一复跑六例均 type + reason 命中、0 Provider 调用并全合同通过（`evals/stage12-night-fixes-revalidation-receipt-v1.json`） | 尚未合并或部署；只证明六个预登记案例与公开等价措辞，不是新未见评测、开放域识别率、生成质量或发布主张 |
| 当前 BM25、BGE、BM25+BGE+RRF 可在同一冻结题集上重复比较 | `evals/retrieval-checkup-v1.json`、`tools/retrieval_checkup.py --check`、`web/app/lib/retrieval-checkup-v1.json`、API 排名等价测试和设计页渲染测试；第一次结果依次为 Top-5 14/16、14/16、16/16，Top-10 均 16/16，错误型号来源均 0 | 只测 16 个公开合成开发题的必需来源覆盖；不是未见集、线上成功率、生成质量或发布门结论，Provider 调用为 0 |
| 内存与 pgvector 可在同一冻结题集上比较且存储故障不拖垮检索 | `evals/retrieval-backend-comparison-v1.json`、`tools/retrieval_backend_compare.py --check`、真 Postgres schema / 排序测试和断线 fallback 定向测试；两路 Top-5 / Top-10 均 16/16、错误型号 0、Top-10 逐题一致，本机冷启动 2035.846 / 1955.757ms、热态 16 题中位数 192.534 / 580.385ms | 同一公开合成开发集、固定执行顺序和本机 Docker 的一次测量，不是未见集、跨机性能、线上成功率或生成质量；pgvector 变慢时不会自动提升质量，Provider 调用为 0 |
| 候选版本可以从全新克隆重建，公开报告构建提交，并具备失败关闭的回滚机制 | 全新克隆与容器检查、不可变 GHCR 镜像、发布清单测试、`release_sha` API / 部署错配测试、生产切换与回滚演练 | `release_sha` 证明发布链核对的构建身份，不证明代码正确；当前仍是单机 Beta，不证明高可用或 SLA |

主页、简历或 README 中的每项新增主张，都必须在本表中绑定代码、测试或运行证据。未知或未执行的主张继续标记为 `未验证`。
